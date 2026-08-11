#!/usr/bin/env python3
"""Check count claims in hand-written text against a run's `summary.json`.

`build_report.py` takes every number straight from `summary.json`, so the
generated report cannot drift. The numbers that drift are the hand-written
ones: the `SECURITY.md` of an audited repo, a pull-request body, a tracker
card, a chat message. Those are written from memory or from a prediction, and
they outlive the run they describe.

**The failure this exists for is not «wrong total».** It is a composition that
is wrong while the total is right — 30 pass / 4 partial / 2 fail against an
actual 30 / 5 / 1. The sum matches, the sentence reads as confirmed, and the
one finding that moved from `fail` to `partial` disappears. A total-only check
passes that. This one compares per status.

**A text with no recognisable claim is not a pass.** Exiting 0 because nothing
was found would make every renaming of a heading a silent all-clear — the same
failure class the catalogue calls `OPS-005`. No claims found means `unchecked`,
and `unchecked` exits non-zero with a message saying so.

Outcomes (exit code):
  0 — every claim found matches summary.json
  1 — a claim contradicts summary.json, or no claim was found at all
  2 — usage error (missing file, unreadable summary)

Usage:
    python tools/check_reported_numbers.py audits/<run>/summary.json SECURITY.md
    python tools/check_reported_numbers.py <summary> <file>... --format json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Bootstrap so tools.* imports work when invoked as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402

# Status words as they appear in hand-written text, mapped to the key in
# summary["totals"]["by_status"]. German and English both occur in this
# portfolio — the READMEs are bilingual and so are the audit notes.
STATUS_WORDS: dict[str, str] = {
    "pass": "pass",
    "bestanden": "pass",
    "partial": "partial",
    "teilweise": "partial",
    "fail": "fail",
    "fehlgeschlagen": "fail",
    "todo": "todo",
    "not_verified": "not_verified",
    "nicht verifiziert": "not_verified",
}

# «30 pass», «30 bestanden», «4 partial». Deliberately narrow: the number must
# sit directly in front of the status word. Anything looser starts matching
# version numbers and issue references.
#
# The trailing `(?![-\w])` is not cosmetic. Without it «Version 5
# partial-release» reads as «5 partial», because a hyphen satisfies `\b` — a
# false positive found by the counter-probe test, not by review. A tool that
# raises findings out of version strings gets switched off.
_CLAIM = re.compile(
    r"(?<![\w.])(\d{1,4})\s+("
    + "|".join(sorted(STATUS_WORDS, key=len, reverse=True))
    + r")\b(?![-\w])",
    re.IGNORECASE,
)

# «5 Findings», «5 findings dokumentiert» — compared against expected_count.
_FINDINGS = re.compile(r"(?<![\w.])(\d{1,4})\s+Findings?\b", re.IGNORECASE)


def extract_claims(text: str) -> list[dict[str, Any]]:
    """Every count claim in the text, with the status it refers to.

    Whitespace is flattened first: a claim that wraps across a line break is
    still a claim, and `grep` is line-wise. That normalisation is the same one
    SKILL.md §4.1 requires before comparing against prose.
    """
    flat = re.sub(r"\s+", " ", text)
    claims: list[dict[str, Any]] = []
    for match in _CLAIM.finditer(flat):
        claims.append(
            {
                "kind": "status",
                "status": STATUS_WORDS[match.group(2).lower()],
                "claimed": int(match.group(1)),
                "text": match.group(0),
            }
        )
    for match in _FINDINGS.finditer(flat):
        claims.append(
            {
                "kind": "findings",
                "status": None,
                "claimed": int(match.group(1)),
                "text": match.group(0),
            }
        )
    return claims


def actual_for(claim: dict[str, Any], summary: dict[str, Any]) -> int:
    """The measured value a claim should equal."""
    if claim["kind"] == "findings":
        return int(summary.get("findings", {}).get("expected_count", 0))
    by_status = summary.get("totals", {}).get("by_status", {})
    return int(by_status.get(claim["status"], 0))


def check_text(text: str, summary: dict[str, Any], source: str) -> dict[str, Any]:
    """Compare one text against the summary."""
    claims = extract_claims(text)
    mismatches = []
    for claim in claims:
        actual = actual_for(claim, summary)
        if claim["claimed"] != actual:
            mismatches.append({**claim, "actual": actual, "source": source})
    return {
        "source": source,
        "claims_found": len(claims),
        "mismatches": mismatches,
        # No claim found is its own outcome. It is not «all clear»: it means
        # the text was never compared, most likely because a wording changed.
        "checked": bool(claims),
    }


def check_files(summary: dict[str, Any], paths: list[Path]) -> dict[str, Any]:
    reports = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        reports.append(check_text(text, summary, str(path)))
    unchecked = [r["source"] for r in reports if not r["checked"]]
    mismatches = [m for r in reports for m in r["mismatches"]]
    return {
        "files": reports,
        "unchecked": unchecked,
        "mismatches": mismatches,
        "consistent": not mismatches and not unchecked,
    }


def _render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    for source in report["unchecked"]:
        lines.append(
            f"  UNGEPRUEFT {source}: keine Zahlenangabe erkannt. Das ist kein "
            "Bestehen — vermutlich hat sich der Wortlaut geaendert."
        )
    for m in report["mismatches"]:
        label = m["status"] or "findings"
        lines.append(
            f"  ABWEICHUNG  {m['source']}: «{m['text']}» — gemessen sind "
            f"{m['actual']} ({label})"
        )
    if not lines:
        checked = sum(f["claims_found"] for f in report["files"])
        lines.append(
            f"  ok — {checked} Angabe(n) geprueft, alle stimmen mit "
            "summary.json ueberein"
        )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_reported_numbers",
        description="Vergleicht handgeschriebene Zahlenangaben mit summary.json.",
    )
    parser.add_argument("summary", help="Pfad zur summary.json des Laufs")
    parser.add_argument("files", nargs="+", help="Textdateien mit Zahlenangaben")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = _build_parser().parse_args(argv)

    summary_path = Path(args.summary)
    if not summary_path.is_file():
        print(f"Error: {summary_path} nicht gefunden", file=sys.stderr)
        return 2
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: {summary_path} ist kein gueltiges JSON: {exc}", file=sys.stderr)
        return 2

    paths = [Path(f) for f in args.files]
    for path in paths:
        if not path.is_file():
            print(f"Error: {path} nicht gefunden", file=sys.stderr)
            return 2

    report = check_files(summary, paths)

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_render(report))

    return 0 if report["consistent"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
