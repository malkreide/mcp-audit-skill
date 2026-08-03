#!/usr/bin/env python3
"""Carry finding documents forward from earlier audit runs.

A re-audit usually leaves most findings unchanged: the check still fails, for
the same reason, with the same remediation. Rewriting those by hand is waste,
so they get copied from the previous run — and that copy step is where two real
audits went wrong.

**What went wrong, twice.** The step was done by hand both times. Once it looked
for `findings/<ID>.md` while the source run had named the file
`<ID>-<slug>.md`; it found nothing, wrote an empty placeholder meant to be
filled later, and never filled it. Sixteen findings across two runs ended up as
zero-byte files, and the validation gate passed them — it asked whether a file
existed, not whether it said anything. The second time the source run was picked
wrong and the same empty files came back.

Both failures share a shape: a hand-rolled transport step between runs, in a
methodology whose *checks* were fine. Hence this script. Its guarantees:

- **Both naming conventions resolve.** `<ID>.md` and `<ID>-<slug>.md` are the
  same finding; the source may use either and so may the target.
- **An empty source is never a source.** A zero-byte file in an earlier run —
  the residue of exactly this bug — is skipped, not propagated.
- **Nothing empty is ever written.** The failure mode being fixed cannot be
  reintroduced by the tool that fixes it.
- **A hand-written target is never overwritten.** Findings edited for this run
  win over anything carried forward; only an *empty* target is replaced.
- **A missing source is loud.** Exit 1 with the ids named, because a finding
  with no document is the state the gate is supposed to catch.

Outcomes (exit code):
  0 — every expected finding has a non-empty document
  1 — some expected finding has none, or a source was unusable
  2 — usage error (bad arguments, missing dir, unreadable summary)

Usage:
    # carry everything the target run expects, from the previous run
    python tools/carry_forward.py audits/<new-run>/ --from audits/<old-run>/

    # several sources, tried in order (first non-empty wins)
    python tools/carry_forward.py audits/<new>/ \
        --from audits/<prev>/ --from audits/<older>/

    # see what would happen without touching anything
    python tools/carry_forward.py audits/<new>/ --from audits/<prev>/ --dry-run

    # only these ids
    python tools/carry_forward.py audits/<new>/ --from audits/<prev>/ \
        --only OBS-001,OBS-002
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# Bootstrap so tools.* imports work when invoked as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402

DEFAULT_MIN_SUBSTANCE = 1

# `<CATEGORY>-<NUMBER>` optionally followed by `-<slug>`. Both spellings occur
# in real audit trees and mean the same finding.
_ID_FROM_NAME = re.compile(r"^([A-Z]+-\d+)(?:-.*)?$")


def check_id_from_path(path: Path) -> str | None:
    """The check id a finding filename refers to, or None if unrecognisable."""
    m = _ID_FROM_NAME.match(path.stem)
    return m.group(1) if m else None


def substance(path: Path) -> int:
    """Non-whitespace character count, mirroring the validation gate.

    Whitespace is stripped before counting because a file holding a newline is
    exactly as informative as one holding nothing — and the bug this script
    exists to prevent produced both.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    return len("".join(text.split()))


def index_findings(findings_dir: Path, min_substance: int) -> dict[str, Path]:
    """Map check id -> the most substantial document for it in one directory.

    Files below `min_substance` are not indexed at all. That is the point: a
    zero-byte `SEC-009.md` left behind by the original bug must not shadow a
    real `SEC-009-session-id-binding.md` sitting beside it.
    """
    best: dict[str, Path] = {}
    if not findings_dir.is_dir():
        return best
    for path in sorted(findings_dir.glob("*.md")):
        cid = check_id_from_path(path)
        if cid is None:
            continue
        if substance(path) < min_substance:
            continue
        if cid not in best or substance(path) > substance(best[cid]):
            best[cid] = path
    return best


def _findings_dir(run_dir: Path) -> Path:
    return run_dir / "findings"


def _expected_ids(run_dir: Path, summary_path: Path | None = None) -> list[str]:
    path = summary_path or (run_dir / "summary.json")
    summary = json.loads(path.read_text(encoding="utf-8"))
    return list(summary["findings"]["expected_ids"])


def carry_forward(
    target_run: Path,
    sources: list[Path],
    only: list[str] | None = None,
    min_substance: int = DEFAULT_MIN_SUBSTANCE,
    dry_run: bool = False,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Fill the target run's findings/ from earlier runs.

    Sources are tried in the order given; the first one holding a substantial
    document for an id wins. Returns a structured report and writes nothing
    when `dry_run` is set.
    """
    expected = _expected_ids(target_run, summary_path)
    if only:
        wanted = [cid for cid in expected if cid in set(only)]
        unknown = sorted(set(only) - set(expected))
    else:
        wanted, unknown = expected, []

    target_dir = _findings_dir(target_run)
    existing = index_findings(target_dir, min_substance)
    # Empty documents already in the target, by id. These are the residue of the
    # very bug this script fixes, and they are *where* the repair belongs: a
    # carried document overwrites the stub in place rather than landing beside
    # it under the source's slugged name. Measured on the real broken run —
    # writing a new name repaired coverage and left twelve zero-byte files
    # sitting in the directory, which is the artefact hygiene problem one layer
    # down from the one being fixed.
    stubs: dict[str, Path] = {}
    if target_dir.is_dir():
        for path in sorted(target_dir.glob("*.md")):
            cid = check_id_from_path(path)
            if (
                cid is not None
                and cid not in existing
                and substance(path) < min_substance
            ):
                stubs.setdefault(cid, path)
    # Only the indexes are needed downstream; each hit already carries its
    # full source path, so the directory itself is not threaded through.
    indexed_sources = [
        index_findings(_findings_dir(src), min_substance) for src in sources
    ]

    carried: list[dict[str, str]] = []
    kept: list[str] = []
    missing: list[str] = []

    for cid in wanted:
        if cid in existing:
            # Already documented for this run — hand-written content wins over
            # anything an earlier run said.
            kept.append(cid)
            continue
        for index in indexed_sources:
            if cid not in index:
                continue
            source_path = index[cid]
            dest = stubs.get(cid) or (target_dir / source_path.name)
            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy(source_path, dest)
                # The guarantee this script is named for: never leave an empty
                # document behind, not even by a failed copy.
                if substance(dest) < min_substance:
                    dest.unlink(missing_ok=True)
                    continue
            carried.append(
                {
                    "check_id": cid,
                    "from": str(source_path),
                    "to": str(dest),
                    "substance": substance(source_path),
                }
            )
            break
        else:
            missing.append(cid)

    report: dict[str, Any] = {
        "target_run": str(target_run),
        "sources": [str(s) for s in sources],
        "expected_count": len(wanted),
        "carried": carried,
        "kept": sorted(kept),
        "missing": sorted(missing),
        "unknown_ids": unknown,
        "min_substance": min_substance,
        "dry_run": dry_run,
        "complete": not missing and not unknown,
    }
    return report


def _render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    prefix = "would carry" if report["dry_run"] else "carried"
    for item in report["carried"]:
        lines.append(
            f"  {prefix} {item['check_id']:<12} <- {item['from']} ({item['substance']} chars)"
        )
    for cid in report["kept"]:
        lines.append(f"  kept    {cid:<12} (already documented in this run)")
    for cid in report["missing"]:
        lines.append(f"  MISSING {cid:<12} no substantial source in any run given")
    for cid in report["unknown_ids"]:
        lines.append(f"  UNKNOWN {cid:<12} not in this run's expected_ids")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="carry_forward",
        description="Copy unchanged finding documents from earlier audit runs.",
    )
    parser.add_argument("target_run", help="Audit run dir to fill (needs summary.json)")
    parser.add_argument(
        "--from",
        dest="sources",
        action="append",
        required=True,
        metavar="RUN_DIR",
        help="Source audit run dir; repeatable, tried in order",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated check ids to carry (default: all expected)",
    )
    parser.add_argument(
        "--min-substance",
        type=int,
        default=DEFAULT_MIN_SUBSTANCE,
        help=(
            "Minimum non-whitespace characters for a document to count as a "
            "source or as already-present (default: 1)"
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    parser.add_argument("--summary", default=None, help="Override summary.json path")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = _build_parser().parse_args(argv)

    target = Path(args.target_run)
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        return 2

    summary_path = Path(args.summary) if args.summary else target / "summary.json"
    if not summary_path.exists():
        print(
            f"Error: {summary_path} not found — aggregate the run before carrying forward",
            file=sys.stderr,
        )
        return 2

    sources = [Path(s) for s in args.sources]
    for src in sources:
        if not src.is_dir():
            print(f"Error: source {src} is not a directory", file=sys.stderr)
            return 2

    only = [s.strip() for s in args.only.split(",") if s.strip()] if args.only else None

    try:
        report = carry_forward(
            target,
            sources,
            only=only,
            min_substance=args.min_substance,
            dry_run=args.dry_run,
            summary_path=summary_path,
        )
    except (KeyError, json.JSONDecodeError) as e:
        print(
            f"Error: cannot read expected_ids from {summary_path}: {e}", file=sys.stderr
        )
        return 2

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        rendered = _render(report)
        if rendered:
            print(rendered)
        print(
            f"\n{len(report['carried'])} carried, {len(report['kept'])} kept, "
            f"{len(report['missing'])} missing"
            + (" (dry run, nothing written)" if report["dry_run"] else "")
        )
        if report["missing"]:
            print(
                "\nWrite these by hand before validating — a finding without a "
                "document is what the gate is there to catch.",
                file=sys.stderr,
            )

    return 0 if report["complete"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
