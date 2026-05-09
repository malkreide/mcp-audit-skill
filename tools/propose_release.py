#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""propose_release.py — Generate a release proposal for an audited MCP server.

Triggered after an audit + remediation loop reaches `production_ready: true`
(no failing critical/high findings). The script:

  1. Reads `summary.json` from an audit run and refuses to proceed if the
     server is not production-ready (or `--force` is passed).
  2. Detects the current version in the target repo (pyproject.toml,
     package.json, or latest git tag) and computes the next version using
     a semver bump (default: patch).
  3. Generates a CHANGELOG entry that records the audit metadata
     (skill version, catalog hash, run-id, findings counts) and any
     user-supplied release notes.
  4. In `propose` mode (default) prints the diff and the suggested
     `git tag` / `gh release` commands without touching the working tree.
  5. In `apply` mode writes the CHANGELOG, creates an annotated git tag,
     and (if `gh` is available) creates a GitHub release.

The script is intentionally conservative: it never pushes, never force-tags,
and always shows what it would do unless `--apply` is set. The slash command
must show the proposal to the user and only call `--apply` after explicit
confirmation.

Usage:
    python tools/propose_release.py propose <audit_dir> <target_repo>
    python tools/propose_release.py apply   <audit_dir> <target_repo> \\
        --bump minor --notes "Fixes confused-deputy and adds OAuth state."
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")
VALID_BUMPS = ("major", "minor", "patch")


class ReleaseError(Exception):
    """Raised on any release-proposal precondition failure."""


# ---------------------------------------------------------------------------
# Summary inspection
# ---------------------------------------------------------------------------

@dataclass
class AuditSummary:
    production_ready: bool
    blocking_findings: list[str]
    by_status: dict[str, int]
    by_severity: dict[str, int]
    server_name: str
    run_id: str
    skill_version: str
    catalog_hash: str
    started_at: str
    findings_count: int

    @classmethod
    def from_dir(cls, audit_dir: Path) -> "AuditSummary":
        summary_path = audit_dir / "summary.json"
        meta_path = audit_dir / "audit-meta.json"
        if not summary_path.exists():
            raise ReleaseError(
                f"summary.json not found at {summary_path}. "
                "Run `tools/aggregate_results.py aggregate` first."
            )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        meta: dict[str, Any] = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))

        audit_meta = summary.get("audit_meta", {}) or {}
        # Prefer audit-meta.json (richer) over inline audit_meta in summary.
        merged = {**audit_meta, **meta}

        return cls(
            production_ready=bool(summary.get("production_ready", False)),
            blocking_findings=list(summary.get("blocking_findings", [])),
            by_status=dict(summary.get("totals", {}).get("by_status", {})),
            by_severity=dict(
                summary.get("totals", {}).get("by_severity_among_findings", {})
            ),
            server_name=str(merged.get("server_name", "")),
            run_id=str(merged.get("run_id", "")),
            skill_version=str(merged.get("skill_version", "")),
            catalog_hash=str(merged.get("catalog_hash", "")),
            started_at=str(merged.get("started_at", "")),
            findings_count=int(summary.get("findings", {}).get("expected_count", 0)),
        )


# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------

def detect_current_version(target_repo: Path) -> tuple[str, str]:
    """Returns (version, source). Source is one of pyproject/package/git/none.

    Resolution order:
      1. pyproject.toml [project] version
      2. package.json "version"
      3. Latest semver-shaped git tag
      4. ("0.0.0", "none") — caller must decide initial version explicitly
    """
    pyproject = target_repo / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        # Minimal parser: avoid pulling tomllib/tomli to keep stdlib-only.
        # Match `version = "x.y.z"` inside [project] section.
        in_project = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_project = stripped == "[project]"
                continue
            if in_project:
                m = re.match(r'^version\s*=\s*"([^"]+)"\s*$', stripped)
                if m:
                    return m.group(1), "pyproject"

    package_json = target_repo / "package.json"
    if package_json.exists():
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8"))
            v = pkg.get("version")
            if isinstance(v, str) and v:
                return v, "package"
        except json.JSONDecodeError:
            pass

    # Git tag fallback.
    try:
        out = subprocess.run(
            ["git", "-C", str(target_repo), "tag", "--list", "--sort=-v:refname"],
            capture_output=True, text=True, check=True,
        )
        for tag in out.stdout.splitlines():
            tag = tag.strip()
            if SEMVER_RE.match(tag):
                # Strip leading 'v' if present so callers get pure semver.
                return tag.lstrip("v"), "git"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return "0.0.0", "none"


def bump_version(current: str, bump: str) -> str:
    if bump not in VALID_BUMPS:
        raise ReleaseError(f"Invalid bump {bump!r}; valid: {VALID_BUMPS}")
    m = SEMVER_RE.match(current)
    if not m:
        raise ReleaseError(
            f"Current version {current!r} is not semver-shaped. "
            "Pass --next-version explicitly to override."
        )
    major, minor, patch = (int(x) for x in m.groups()[:3])
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


# ---------------------------------------------------------------------------
# CHANGELOG generation
# ---------------------------------------------------------------------------

def render_changelog_entry(
    version: str,
    summary: AuditSummary,
    notes: str | None,
    today: str,
) -> str:
    """Returns the markdown block for a new release entry."""
    lines: list[str] = []
    lines.append(f"## [v{version}] — {today}")
    lines.append("")
    if notes:
        lines.append(notes.rstrip())
        lines.append("")

    lines.append("### Audit verification")
    lines.append("")
    lines.append(
        f"- **Production-ready:** "
        f"{'✅ yes' if summary.production_ready else '❌ no'}"
    )
    if summary.run_id:
        lines.append(f"- **Audit run-id:** `{summary.run_id}`")
    if summary.skill_version:
        lines.append(f"- **Skill version:** `{summary.skill_version}`")
    if summary.catalog_hash:
        # Show only first 12 chars; full hash is in audit-meta.json.
        lines.append(f"- **Catalog hash:** `{summary.catalog_hash[:12]}…`")

    by_status = summary.by_status
    pass_n = by_status.get("pass", 0)
    fail_n = by_status.get("fail", 0)
    partial_n = by_status.get("partial", 0)
    todo_n = by_status.get("todo", 0)
    lines.append(
        f"- **Check results:** {pass_n} pass · {fail_n} fail · "
        f"{partial_n} partial · {todo_n} todo"
    )
    if summary.blocking_findings:
        joined = ", ".join(summary.blocking_findings)
        lines.append(f"- **Open blocking findings:** {joined}")
    lines.append("")
    return "\n".join(lines) + "\n"


def insert_changelog_entry(
    changelog_path: Path,
    entry_md: str,
) -> tuple[str, str]:
    """Returns (new_text, original_text). Does not write the file.

    Insertion strategy:
      - If the file doesn't exist: write a minimal Keep-a-Changelog header
        plus the new entry.
      - If it has an `## [Unreleased]` block: insert the new entry right
        after that block, preserving Unreleased.
      - Otherwise: insert at the top, after the first non-heading line.
    """
    if not changelog_path.exists():
        header = (
            "# Changelog\n\n"
            "All notable changes to this project are documented here.\n"
            "Format: [Keep a Changelog](https://keepachangelog.com/).\n\n"
        )
        return header + entry_md, ""

    original = changelog_path.read_text(encoding="utf-8")
    unreleased = re.search(
        r"^## \[Unreleased\][^\n]*\n", original, re.MULTILINE,
    )
    if unreleased:
        # Insert before the next `## [` heading.
        start = unreleased.end()
        next_release = re.search(r"^## \[", original[start:], re.MULTILINE)
        if next_release:
            insertion_at = start + next_release.start()
        else:
            insertion_at = len(original)
        new_text = (
            original[:insertion_at]
            + ("\n" if not original[:insertion_at].endswith("\n\n") else "")
            + entry_md
            + ("\n" if not entry_md.endswith("\n\n") else "")
            + original[insertion_at:]
        )
        return new_text, original

    # No Unreleased: prepend after the H1, if any.
    h1 = re.match(r"^# [^\n]*\n+", original)
    if h1:
        return original[: h1.end()] + entry_md + "\n" + original[h1.end():], original
    return entry_md + "\n" + original, original


# ---------------------------------------------------------------------------
# Apply mode — git + gh
# ---------------------------------------------------------------------------

def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True,
                          capture_output=True, text=True)


def has_gh_cli() -> bool:
    return shutil.which("gh") is not None


def apply_release(
    target_repo: Path,
    version: str,
    changelog_path: Path,
    new_changelog_text: str,
    summary: AuditSummary,
    notes: str | None,
    create_github_release: bool,
) -> dict[str, Any]:
    """Writes CHANGELOG, commits, tags, optionally creates a GH release.

    Never pushes. Returns a dict describing what was done so the caller can
    print it to the user.
    """
    actions: dict[str, Any] = {}

    changelog_path.write_text(new_changelog_text, encoding="utf-8")
    actions["changelog_written"] = str(changelog_path)

    # Stage + commit only the changelog. Other working-tree changes are
    # ignored on purpose — releases are explicit, not silent batch-commits.
    rel = changelog_path.relative_to(target_repo)
    run(["git", "add", str(rel)], cwd=target_repo)
    commit_msg = f"chore(release): v{version}\n\nAudit run: {summary.run_id}"
    try:
        run(["git", "commit", "-m", commit_msg], cwd=target_repo)
        actions["committed"] = True
    except subprocess.CalledProcessError as e:
        # If nothing was staged (e.g. CHANGELOG already had this entry),
        # surface that but continue — the tag is still useful.
        actions["committed"] = False
        actions["commit_error"] = e.stderr.strip() or e.stdout.strip()

    tag = f"v{version}"
    tag_msg = f"Release {tag} — audit-verified production-ready"
    run(["git", "tag", "-a", tag, "-m", tag_msg], cwd=target_repo)
    actions["tag_created"] = tag

    if create_github_release:
        if has_gh_cli():
            release_notes = notes or f"Audit-verified release. Run-ID: {summary.run_id}"
            run([
                "gh", "release", "create", tag,
                "--title", f"Release {tag}",
                "--notes", release_notes,
                "--draft",
            ], cwd=target_repo)
            actions["github_release"] = "draft"
        else:
            actions["github_release"] = "skipped (gh CLI not available)"

    actions["next_steps"] = [
        f"git -C {target_repo} push origin HEAD",
        f"git -C {target_repo} push origin {tag}",
        "Review and publish the draft GitHub release",
    ]
    return actions


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_propose(args: argparse.Namespace) -> int:
    audit_dir = Path(args.audit_dir).resolve()
    target_repo = Path(args.target_repo).resolve()

    summary = AuditSummary.from_dir(audit_dir)

    if not summary.production_ready and not args.force:
        print(json.dumps({
            "ok": False,
            "reason": "not_production_ready",
            "blocking_findings": summary.blocking_findings,
            "by_status": summary.by_status,
            "hint": "Fix the blocking findings or pass --force to override.",
        }, indent=2, ensure_ascii=False))
        return 2

    current_version, source = detect_current_version(target_repo)
    next_version = args.next_version or bump_version(current_version, args.bump)
    today = (
        args.today
        or datetime.now(timezone.utc).date().isoformat()
    )

    entry = render_changelog_entry(next_version, summary, args.notes, today)
    changelog = target_repo / args.changelog
    new_text, _ = insert_changelog_entry(changelog, entry)

    proposal = {
        "ok": True,
        "production_ready": summary.production_ready,
        "current_version": current_version,
        "current_version_source": source,
        "next_version": next_version,
        "bump": args.bump if not args.next_version else "explicit",
        "changelog_path": str(changelog),
        "changelog_entry": entry,
        "tag_command": f"git tag -a v{next_version} -m \"Release v{next_version}\"",
        "release_command": (
            f"gh release create v{next_version} --title \"Release v{next_version}\" "
            f"--notes-file <path> --draft"
        ),
        "audit": {
            "run_id": summary.run_id,
            "skill_version": summary.skill_version,
            "catalog_hash_short": summary.catalog_hash[:12],
            "by_status": summary.by_status,
            "findings_count": summary.findings_count,
        },
    }
    if args.format == "json":
        print(json.dumps(proposal, indent=2, ensure_ascii=False))
    else:
        print(f"Release proposal for {summary.server_name or target_repo.name}")
        print(f"  Current version : {current_version} (from {source})")
        print(f"  Next version    : {next_version}")
        print(f"  Audit run       : {summary.run_id}")
        print(f"  CHANGELOG path  : {changelog}")
        print()
        print("--- proposed CHANGELOG entry ---")
        print(entry)
        print("--- end entry ---")
        print()
        print("To apply, re-run with `apply` and the same flags.")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    audit_dir = Path(args.audit_dir).resolve()
    target_repo = Path(args.target_repo).resolve()

    summary = AuditSummary.from_dir(audit_dir)
    if not summary.production_ready and not args.force:
        print(json.dumps({
            "ok": False,
            "reason": "not_production_ready",
            "blocking_findings": summary.blocking_findings,
        }, indent=2, ensure_ascii=False))
        return 2

    current_version, source = detect_current_version(target_repo)
    next_version = args.next_version or bump_version(current_version, args.bump)
    today = (
        args.today
        or datetime.now(timezone.utc).date().isoformat()
    )

    entry = render_changelog_entry(next_version, summary, args.notes, today)
    changelog = target_repo / args.changelog
    new_text, _ = insert_changelog_entry(changelog, entry)

    actions = apply_release(
        target_repo=target_repo,
        version=next_version,
        changelog_path=changelog,
        new_changelog_text=new_text,
        summary=summary,
        notes=args.notes,
        create_github_release=args.gh_release,
    )
    print(json.dumps({
        "ok": True,
        "version": next_version,
        "current_version": current_version,
        "actions": actions,
    }, indent=2, ensure_ascii=False))
    return 0


def main() -> None:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="propose_release",
        description=(
            "Generate a release proposal for an audited MCP server, "
            "optionally apply it (CHANGELOG + git tag + draft GH release)."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _common(p: argparse.ArgumentParser) -> None:
        p.add_argument("audit_dir", help="Path to the audit run dir (contains summary.json).")
        p.add_argument("target_repo", help="Path to the audited server's git repo.")
        p.add_argument("--bump", choices=VALID_BUMPS, default="patch",
                       help="Semver bump (default: patch).")
        p.add_argument("--next-version", help="Explicit version, overrides --bump.")
        p.add_argument("--changelog", default="CHANGELOG.md",
                       help="CHANGELOG file relative to target_repo.")
        p.add_argument("--notes", help="Free-form release notes (markdown).")
        p.add_argument("--today", help="Override release date (YYYY-MM-DD); for tests.")
        p.add_argument("--force", action="store_true",
                       help="Allow release even if not production_ready.")

    sp = sub.add_parser("propose", help="Print proposal, do not modify anything.")
    _common(sp)
    sp.add_argument("--format", choices=("text", "json"), default="text")
    sp.set_defaults(func=cmd_propose)

    sp = sub.add_parser("apply", help="Write CHANGELOG, commit, tag, draft GH release.")
    _common(sp)
    sp.add_argument("--gh-release", action="store_true",
                    help="Also create a draft GitHub release via gh CLI.")
    sp.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    try:
        sys.exit(args.func(args))
    except ReleaseError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
