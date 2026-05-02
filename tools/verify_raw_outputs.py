#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify raw/ output completeness after Task-agent execution.

Solves the silent-failure problem from issue #12: in the first real audit,
a Task-agent returned `Done (68 tool uses · 0 tokens · 2m 20s)` — meaning
the agent returned no actual output — and the skill didn't notice. With
this verifier, Step 4 has a concrete gate after every Task-agent run.

Outcomes (exit code):
  0 — all expected IDs have non-empty output files
  1 — some IDs are missing or have empty output files
  2 — usage error (bad arguments, missing dir)

Usage:
    python tools/verify_raw_outputs.py raw/ \
        --expected-ids ARCH-001,ARCH-002,SEC-021

    python tools/verify_raw_outputs.py raw/ \
        --expected-ids-file expected.txt

    python tools/verify_raw_outputs.py raw/ \
        --expected-ids-file expected.txt \
        --min-bytes 10  # threshold for "non-empty"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Bootstrap so tools.* imports work when invoked as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402


DEFAULT_MIN_BYTES = 1
DEFAULT_FILE_SUFFIX = ".txt"


def verify_raw_outputs(
    raw_dir: Path,
    expected_ids: list[str],
    min_bytes: int = DEFAULT_MIN_BYTES,
    suffix: str = DEFAULT_FILE_SUFFIX,
) -> dict[str, Any]:
    """Compare expected check-IDs against persisted raw/ output files.

    A check-ID is considered "satisfied" iff the file `<raw_dir>/<id><suffix>`
    exists AND is at least `min_bytes` bytes long. The byte-size threshold
    catches the original silent-failure mode where Task-agent returns 0
    tokens and writes empty placeholder files.

    Returns a structured report:
        {
          "expected": [...],
          "satisfied": [...],
          "missing": [...],
          "empty": [...],   # exists but below min_bytes
          "consistent": bool,
          "incomplete_ids": [...],  # missing + empty, ready to retry
        }
    """
    if not raw_dir.exists():
        return {
            "expected": list(expected_ids),
            "satisfied": [],
            "missing": list(expected_ids),
            "empty": [],
            "consistent": False,
            "incomplete_ids": list(expected_ids),
            "error": f"raw_dir {raw_dir} does not exist",
        }

    satisfied: list[str] = []
    missing: list[str] = []
    empty: list[str] = []
    for cid in expected_ids:
        path = raw_dir / f"{cid}{suffix}"
        if not path.exists():
            missing.append(cid)
            continue
        try:
            size = path.stat().st_size
        except OSError:
            missing.append(cid)
            continue
        if size < min_bytes:
            empty.append(cid)
            continue
        satisfied.append(cid)

    incomplete = missing + empty
    return {
        "expected": list(expected_ids),
        "satisfied": satisfied,
        "missing": missing,
        "empty": empty,
        "consistent": not incomplete,
        "incomplete_ids": incomplete,
    }


def _load_expected_ids(path: Path) -> list[str]:
    """One ID per line; skip blanks and comments."""
    ids: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        ids.append(s)
    return ids


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="verify_raw_outputs",
        description=(
            "Verify that Task-agent runs persisted output for every "
            "expected check ID. Exit 0=ok, 1=incomplete, 2=usage error."
        ),
    )
    parser.add_argument(
        "raw_dir",
        help="Directory of per-check raw output files",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--expected-ids",
        help="Comma-separated list of expected check IDs",
    )
    group.add_argument(
        "--expected-ids-file",
        help="Path to a file with one expected check ID per line",
    )
    parser.add_argument(
        "--suffix",
        default=DEFAULT_FILE_SUFFIX,
        help=f"File suffix (default: {DEFAULT_FILE_SUFFIX!r})",
    )
    parser.add_argument(
        "--min-bytes",
        type=int,
        default=DEFAULT_MIN_BYTES,
        help=(
            "Minimum file size to count as non-empty. Catches the "
            "0-token-Task-agent failure mode (default: 1)"
        ),
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Write JSON report to this path; otherwise print to stdout",
    )
    args = parser.parse_args(argv)

    if args.expected_ids:
        ids = [s.strip() for s in args.expected_ids.split(",") if s.strip()]
    else:
        ids_file = Path(args.expected_ids_file)
        if not ids_file.exists():
            print(f"Error: {ids_file} not found", file=sys.stderr)
            return 2
        ids = _load_expected_ids(ids_file)

    if not ids:
        print("Error: no expected IDs given", file=sys.stderr)
        return 2

    raw_dir = Path(args.raw_dir)
    if not raw_dir.exists():
        # We still produce a structured report; CLI also exits non-zero.
        report = verify_raw_outputs(raw_dir, ids, args.min_bytes, args.suffix)
    else:
        report = verify_raw_outputs(raw_dir, ids, args.min_bytes, args.suffix)

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    return 0 if report["consistent"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
