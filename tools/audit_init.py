#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

Usage:
    python tools/audit_init.py make-run-id srgssr-mcp [--base-dir audits/] [--now 2026-05-02T09:12:45+00:00]
    python tools/audit_init.py init srgssr-mcp [--base-dir audits/] [--skill-version 0.9] [--catalog-dir checks/]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
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
    now = now or datetime.now(timezone.utc)
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
        files = files + [manifest]
    for path in sorted(files, key=lambda p: p.name):
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\n--END--\n")
    return h.hexdigest()


def build_initial_meta(
    *,
    server: str,
    run_id: str,
    output_dir: Path,
    now: datetime,
    skill_version: str,
    catalog_dir: Path | None = None,
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
    return meta


def init_audit(
    *,
    server: str,
    base_dir: Path,
    skill_version: str = "unspecified",
    catalog_dir: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create the audit dir, write the initial audit-meta.json, return
    the metadata that was written.
    """
    now = now or datetime.now(timezone.utc)
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
        dt = dt.replace(tzinfo=timezone.utc)
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
        "--now",
        default=None,
        help="ISO-8601 datetime override (testing)",
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
                now=_parse_now(args.now),
            )
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
