#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append Task-agent run metadata to audit-meta.json.

Closes the audit-trail half of issue #12. Whenever the slash command
delegates check execution to a Task-agent, the agent's tool-use count,
token count, duration, and completion status get logged here. The audit
report and the Notion-Sync can then surface "this audit had to retry
SEC-021 twice" instead of pretending everything was clean.

Schema (audit-meta.json):
    {
      "audit_meta": {
        "server_name": "...",
        "audit_date": "...",
        "skill_version": "..."
      },
      "agent_runs": [
        {
          "run_index": 0,
          "started_at": "2026-05-02T07:15:00+00:00",
          "duration_seconds": 124,
          "tool_uses": 73,
          "tokens": 108100,
          "expected_ids": ["ARCH-001", ...],
          "satisfied_ids": ["ARCH-001", ...],
          "incomplete_ids": ["SEC-021"],
          "status": "ok" | "incomplete" | "empty",
          "retry_of_run_index": null
        },
        ...
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Bootstrap.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402
from tools.verify_raw_outputs import verify_raw_outputs  # noqa: E402


def _classify_run(
    tokens: int,
    incomplete_ids: list[str],
) -> str:
    """Three-state status:
      ok          — every expected ID has a non-empty output
      incomplete  — some IDs missing or below threshold
      empty       — agent returned 0 tokens (silent failure mode from #12)
    """
    if tokens == 0:
        return "empty"
    if incomplete_ids:
        return "incomplete"
    return "ok"


def load_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"audit_meta": {}, "agent_runs": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be an object")
    data.setdefault("audit_meta", {})
    data.setdefault("agent_runs", [])
    if not isinstance(data["agent_runs"], list):
        raise ValueError(f"{path}: agent_runs must be a list")
    return data


def save_meta(path: Path, meta: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def append_run(
    meta: dict[str, Any],
    *,
    tool_uses: int,
    tokens: int,
    duration_seconds: float,
    expected_ids: list[str],
    raw_dir: Path,
    min_bytes: int = 1,
    started_at: datetime | None = None,
    retry_of_run_index: int | None = None,
) -> dict[str, Any]:
    """Append a structured run entry. Returns the entry that was added."""
    started_at = started_at or datetime.now(timezone.utc)
    verify = verify_raw_outputs(raw_dir, expected_ids, min_bytes=min_bytes)
    status = _classify_run(tokens, verify["incomplete_ids"])
    entry = {
        "run_index": len(meta["agent_runs"]),
        "started_at": started_at.isoformat(),
        "duration_seconds": round(float(duration_seconds), 2),
        "tool_uses": int(tool_uses),
        "tokens": int(tokens),
        "expected_ids": list(expected_ids),
        "satisfied_ids": verify["satisfied"],
        "missing_ids": verify["missing"],
        "empty_ids": verify["empty"],
        "incomplete_ids": verify["incomplete_ids"],
        "status": status,
        "retry_of_run_index": retry_of_run_index,
    }
    meta["agent_runs"].append(entry)
    return entry


def summarise(meta: dict[str, Any]) -> dict[str, Any]:
    runs = meta.get("agent_runs", [])
    if not runs:
        return {"runs": 0, "status": "no-runs", "incomplete_ids": []}
    total_tokens = sum(r.get("tokens", 0) for r in runs)
    total_tool_uses = sum(r.get("tool_uses", 0) for r in runs)
    total_duration = sum(r.get("duration_seconds", 0) for r in runs)

    # Build coverage from union of satisfied across all runs (latest wins
    # if an earlier run was incomplete and a later retry filled it).
    satisfied: set[str] = set()
    expected: set[str] = set()
    for r in runs:
        expected.update(r.get("expected_ids", []))
        satisfied.update(r.get("satisfied_ids", []))
    incomplete = sorted(expected - satisfied)
    last = runs[-1]
    overall = "ok" if not incomplete else "incomplete"
    return {
        "runs": len(runs),
        "total_tokens": total_tokens,
        "total_tool_uses": total_tool_uses,
        "total_duration_seconds": round(total_duration, 2),
        "expected_unique_ids": len(expected),
        "satisfied_unique_ids": len(satisfied),
        "incomplete_ids": incomplete,
        "last_run_status": last.get("status"),
        "overall_status": overall,
        "had_retries": any(
            r.get("retry_of_run_index") is not None for r in runs
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_run_log",
        description="Log Task-agent runs to audit-meta.json.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_log = sub.add_parser("log", help="Append a run entry")
    p_log.add_argument(
        "--meta-path",
        required=True,
        help="Path to audit-meta.json (created if missing)",
    )
    p_log.add_argument("--tool-uses", type=int, required=True)
    p_log.add_argument("--tokens", type=int, required=True)
    p_log.add_argument("--duration", type=float, required=True)
    p_log.add_argument(
        "--expected",
        required=True,
        help="Comma-separated expected check IDs",
    )
    p_log.add_argument(
        "--raw-dir",
        required=True,
        help="Directory containing per-check raw output files",
    )
    p_log.add_argument("--min-bytes", type=int, default=1)
    p_log.add_argument(
        "--retry-of",
        type=int,
        default=None,
        help="If this run is a retry, the run_index it retries",
    )

    p_sum = sub.add_parser("summary", help="Print summary of recorded runs")
    p_sum.add_argument("--meta-path", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = _build_parser().parse_args(argv)
    meta_path = Path(args.meta_path)

    if args.cmd == "log":
        meta = load_meta(meta_path)
        ids = [s.strip() for s in args.expected.split(",") if s.strip()]
        entry = append_run(
            meta,
            tool_uses=args.tool_uses,
            tokens=args.tokens,
            duration_seconds=args.duration,
            expected_ids=ids,
            raw_dir=Path(args.raw_dir),
            min_bytes=args.min_bytes,
            retry_of_run_index=args.retry_of,
        )
        save_meta(meta_path, meta)
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        # Exit non-zero on incomplete/empty so the caller can branch.
        return 0 if entry["status"] == "ok" else 1

    if args.cmd == "summary":
        if not meta_path.exists():
            print(f"Error: {meta_path} not found", file=sys.stderr)
            return 2
        meta = load_meta(meta_path)
        summary = summarise(meta)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary.get("overall_status") in ("ok", "no-runs") else 1

    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
