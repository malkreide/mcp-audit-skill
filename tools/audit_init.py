#!/usr/bin/env python3
"""Initialize an audit run: generate run-id, create output dir, write
initial audit-meta.json.

Closes issue #15. The first real audit had `date +%Y-%m-%d` produce
`2026-04-30` even though the local calendar day was `2026-05-01` (UTC
container drift). The output dir was named `audits/2026-04-30-...`
instead of `2026-05-01-...`. Re-audits on the same day would have
collided in the same directory.

Solution: deterministic run-id with explicit timezone, collision suffix,
and audit-meta.json initialised up-front with skill version + catalog
hash so reproducibility is documented from the start.

Run-ID format: `YYYY-MM-DDTHHMMSS-<offset>-<server>` (ISO-ish, filesystem
safe). Example: `2026-05-02T091245-Z-srgssr-mcp` (Z = UTC).

The audited repo's HEAD SHA is recorded here too, and re-checked at the end
of the run. `catalog_hash` pins what the audit was measured *with*;
`target_sha` pins what it was measured *against*, and only both together make
a run reproducible. Without it, a commit landing mid-audit silently splits the
report: the checks that ran before it describe one tree, the ones after
another, and the report presents the mixture as a single verdict. An audit
whose target moves during the run is not an audit — it is a statement about no
particular revision.

Usage:
    python tools/audit_init.py make-run-id srgssr-mcp [--base-dir audits/] [--now 2026-05-02T09:12:45+00:00]
    python tools/audit_init.py init srgssr-mcp [--base-dir audits/] [--skill-version 1.7.0] [--catalog-dir checks/] [--target-repo ../srgssr-mcp]
    python tools/audit_init.py verify-target audits/<run>/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Bootstrap so tools.* imports work when invoked as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402

_VALID_SERVER_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def _format_offset(dt: datetime) -> str:
    """Render the UTC offset as `Z`, `+HHMM`, or `-HHMM` for filenames."""
    if dt.tzinfo is None:
        raise ValueError(f"datetime is naive (no tzinfo): {dt!r}")
    offset = dt.utcoffset()
    if offset is None:
        raise ValueError(f"datetime has no UTC offset: {dt!r}")
    total_seconds = int(offset.total_seconds())
    if total_seconds == 0:
        return "Z"
    sign = "+" if total_seconds >= 0 else "-"
    abs_seconds = abs(total_seconds)
    hours = abs_seconds // 3600
    minutes = (abs_seconds % 3600) // 60
    return f"{sign}{hours:02d}{minutes:02d}"


def make_run_id(server: str, now: datetime | None = None) -> str:
    """Compute a deterministic run-id with explicit timezone marker.

    Format: `YYYY-MM-DDTHHMMSS-<offset>-<server>`
        offset is `Z` for UTC, `+HHMM` / `-HHMM` otherwise.
    """
    if not server or not _VALID_SERVER_RE.match(server):
        raise ValueError(
            f"server name {server!r} must match {_VALID_SERVER_RE.pattern}"
        )
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("`now` must be timezone-aware")
    offset = _format_offset(now)
    timestamp = now.strftime("%Y-%m-%dT%H%M%S")
    return f"{timestamp}-{offset}-{server}"


def resolve_output_dir(
    server: str,
    base_dir: Path,
    now: datetime | None = None,
) -> tuple[str, Path]:
    """Return (run_id, dir_path) ensuring no collision with existing runs.

    Strategy: same-second collisions (rare but possible in tests/CI) get
    a `-2`, `-3`, ... suffix on the directory name only — the base
    run-id stays identical so audit-meta.json can record the original
    timestamp.
    """
    run_id = make_run_id(server, now=now)
    candidate = base_dir / run_id
    if not candidate.exists():
        return run_id, candidate
    counter = 2
    while True:
        suffixed = base_dir / f"{run_id}-{counter}"
        if not suffixed.exists():
            return run_id, suffixed
        counter += 1


def hash_catalog(catalog_dir: Path) -> str:
    """Stable SHA-256 hash of the catalog markdown files.

    Hashes the sorted concatenation of `<filename>:<content>` for every
    `*.md` plus `MANIFEST.txt`. Used as a versioning fingerprint in
    audit-meta.json so future re-audits can verify they evaluated the
    same checks.
    """
    h = hashlib.sha256()
    files = sorted(catalog_dir.glob("*.md"))
    manifest = catalog_dir / "MANIFEST.txt"
    if manifest.exists():
        files = [*files, manifest]
    for path in sorted(files, key=lambda p: p.name):
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\n--END--\n")
    return h.hexdigest()


class TargetRepoError(Exception):
    """Raised when the audited repo cannot be interrogated for its revision."""


def _git(repo: Path, *args: str) -> str:
    """Run a read-only git command in `repo`, returning stripped stdout."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError) as e:  # pragma: no cover - environment-specific
        raise TargetRepoError(f"cannot run git in {repo}: {e}") from e
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise TargetRepoError(f"git {' '.join(args)} failed in {repo}: {detail}")
    return proc.stdout.strip()


def target_revision(repo: Path) -> dict[str, Any]:
    """The audited repo's current revision, as recorded in audit-meta.json.

    `dirty` is carried alongside the SHA because a clean SHA over a dirty
    worktree describes a tree that exists nowhere but this machine. The audit
    is still valid — auditing uncommitted work is a legitimate thing to do —
    but the report must not imply it examined the commit it names.
    """
    if not repo.is_dir():
        raise TargetRepoError(f"target repo {repo} is not a directory")
    sha = _git(repo, "rev-parse", "HEAD")
    dirty = bool(_git(repo, "status", "--porcelain"))
    try:
        branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    except TargetRepoError:  # pragma: no cover - detached HEAD edge case
        branch = ""
    return {
        "target_repo": str(repo),
        "target_sha": sha,
        "target_dirty": dirty,
        "target_branch": branch,
    }


def build_initial_meta(
    *,
    server: str,
    run_id: str,
    output_dir: Path,
    now: datetime,
    skill_version: str,
    catalog_dir: Path | None = None,
    target_repo: Path | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "audit_meta": {
            "server_name": server,
            "run_id": run_id,
            "started_at": now.isoformat(),
            "timezone_offset": _format_offset(now),
            "skill_version": skill_version,
            "output_dir": str(output_dir),
        },
        "agent_runs": [],
    }
    if catalog_dir is not None and catalog_dir.exists():
        meta["audit_meta"]["catalog_hash"] = hash_catalog(catalog_dir)
        meta["audit_meta"]["catalog_dir"] = str(catalog_dir)
    if target_repo is not None:
        meta["audit_meta"].update(target_revision(target_repo))
    return meta


def verify_target(
    meta: dict[str, Any],
    repo_override: Path | None = None,
) -> dict[str, Any]:
    """Re-read the audited repo's HEAD and compare it with what was recorded.

    Returns a structured report. `unchanged` is only ever true when a SHA was
    recorded at init *and* still matches — an unrecorded target reports
    `recorded: false` and never `unchanged: true`, because "we never looked"
    must not read the same as "it did not move" (`OPS-005`).

    A worktree that was clean at init and is dirty now counts as moved. The
    audit measured committed state and would now be describing something else.
    """
    audit_meta = meta.get("audit_meta", meta) or {}
    recorded_sha = audit_meta.get("target_sha")
    recorded_repo = audit_meta.get("target_repo")
    repo = repo_override or (Path(recorded_repo) if recorded_repo else None)

    report: dict[str, Any] = {
        "recorded": bool(recorded_sha),
        "recorded_sha": recorded_sha or "",
        "recorded_dirty": bool(audit_meta.get("target_dirty", False)),
        "target_repo": str(repo) if repo else "",
        "current_sha": "",
        "current_dirty": False,
        "unchanged": False,
        "reason": "",
    }

    if not recorded_sha:
        report["reason"] = (
            "no target_sha in audit-meta.json — the run never recorded which "
            "revision it audited, so nothing can be verified. Re-run "
            "`audit_init.py init` with --target-repo for future audits."
        )
        return report
    if repo is None:
        report["reason"] = (
            "target_sha recorded but no target_repo; pass --target-repo to say "
            "where to look"
        )
        return report

    current = target_revision(repo)
    report["current_sha"] = current["target_sha"]
    report["current_dirty"] = current["target_dirty"]

    if current["target_sha"] != recorded_sha:
        report["reason"] = (
            f"HEAD moved during the audit: {recorded_sha[:12]} at init, "
            f"{current['target_sha'][:12]} now. The report mixes findings from "
            "two different trees."
        )
        return report
    if current["target_dirty"] and not report["recorded_dirty"]:
        report["reason"] = (
            "HEAD is unchanged but the worktree is now dirty; it was clean at "
            "init. Some checks looked at committed state, later ones at edits "
            "that exist only here."
        )
        return report

    report["unchanged"] = True
    report["reason"] = "target unchanged" + (
        " (dirty at init and still dirty)" if report["recorded_dirty"] else ""
    )
    return report


def init_audit(
    *,
    server: str,
    base_dir: Path,
    skill_version: str = "unspecified",
    catalog_dir: Path | None = None,
    target_repo: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create the audit dir, write the initial audit-meta.json, return
    the metadata that was written.
    """
    now = now or datetime.now(UTC)
    # Interrogate the target before creating anything: a bad --target-repo
    # should not leave an empty run directory behind for someone to wonder at.
    target = target_revision(target_repo) if target_repo is not None else None
    run_id, output_dir = resolve_output_dir(server, base_dir, now=now)
    output_dir.mkdir(parents=True, exist_ok=False)
    meta = build_initial_meta(
        server=server,
        run_id=run_id,
        output_dir=output_dir,
        now=now,
        skill_version=skill_version,
        catalog_dir=catalog_dir,
    )
    if target is not None:
        meta["audit_meta"].update(target)
    meta_path = output_dir / "audit-meta.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "run_id": run_id,
        "output_dir": str(output_dir),
        "meta_path": str(meta_path),
        "audit_meta": meta["audit_meta"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_now(value: str | None) -> datetime | None:
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        # Treat naive input as UTC for predictable behaviour in CI.
        dt = dt.replace(tzinfo=UTC)
    return dt


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="audit_init",
        description="Initialize an audit run with run-id + audit-meta.json.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_id = sub.add_parser(
        "make-run-id",
        help="Compute a run-id without touching the filesystem",
    )
    p_id.add_argument("server")
    p_id.add_argument(
        "--now",
        default=None,
        help="ISO-8601 datetime override (testing). Default: now (UTC)",
    )

    p_init = sub.add_parser(
        "init",
        help="Create audit dir + initial audit-meta.json",
    )
    p_init.add_argument("server")
    p_init.add_argument(
        "--base-dir",
        default="audits",
        help="Parent directory for audit runs (default: audits/)",
    )
    p_init.add_argument(
        "--skill-version",
        default="unspecified",
        help="Skill version string for audit-meta.json",
    )
    p_init.add_argument(
        "--catalog-dir",
        default=None,
        help="Optional catalog dir to hash into audit-meta.json",
    )
    p_init.add_argument(
        "--target-repo",
        default=None,
        help=(
            "Checkout of the server being audited. Its HEAD SHA is recorded so "
            "the end of the run can verify the target did not move"
        ),
    )
    p_init.add_argument(
        "--now",
        default=None,
        help="ISO-8601 datetime override (testing)",
    )

    p_verify = sub.add_parser(
        "verify-target",
        help="Re-check that the audited repo is still at the recorded revision",
    )
    p_verify.add_argument("audit_dir", help="Audit run dir holding audit-meta.json")
    p_verify.add_argument(
        "--meta-path",
        default=None,
        help="Override audit-meta.json path (default: <audit_dir>/audit-meta.json)",
    )
    p_verify.add_argument(
        "--target-repo",
        default=None,
        help="Where the audited repo lives now, if it moved since init",
    )
    p_verify.add_argument(
        "--allow-unrecorded",
        action="store_true",
        help=(
            "Exit 0 when the run recorded no target_sha. Off by default: an "
            "unverifiable run must not read as a verified one"
        ),
    )

    args = parser.parse_args(argv)

    if args.cmd == "make-run-id":
        try:
            run_id = make_run_id(args.server, now=_parse_now(args.now))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        print(run_id)
        return 0

    if args.cmd == "init":
        try:
            result = init_audit(
                server=args.server,
                base_dir=Path(args.base_dir),
                skill_version=args.skill_version,
                catalog_dir=Path(args.catalog_dir) if args.catalog_dir else None,
                target_repo=Path(args.target_repo) if args.target_repo else None,
                now=_parse_now(args.now),
            )
        except (ValueError, TargetRepoError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result["audit_meta"].get("target_dirty"):
            print(
                "Warning: the audited worktree has uncommitted changes; "
                f"{result['audit_meta']['target_sha'][:12]} names a commit this "
                "audit is not purely about.",
                file=sys.stderr,
            )
        return 0

    if args.cmd == "verify-target":
        audit_dir = Path(args.audit_dir)
        meta_path = (
            Path(args.meta_path) if args.meta_path else audit_dir / "audit-meta.json"
        )
        if not meta_path.exists():
            print(f"Error: {meta_path} not found", file=sys.stderr)
            return 2
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error: cannot read {meta_path}: {e}", file=sys.stderr)
            return 2
        try:
            report = verify_target(
                meta,
                repo_override=Path(args.target_repo) if args.target_repo else None,
            )
        except TargetRepoError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if report["unchanged"]:
            return 0
        if not report["recorded"] and args.allow_unrecorded:
            return 0
        return 1

    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
