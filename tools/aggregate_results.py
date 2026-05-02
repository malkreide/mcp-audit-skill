#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single source of truth for audit verification results.

Solves the inconsistency observed in the first real audit (srgssr-mcp,
2026-04-30) where Step 4 / Step 5 / final report each reported different
counts because each step recomputed from a different intermediate.

This module defines:
  - The canonical verification-results JSON schema.
  - The findings-persistence policy: which statuses warrant a finding doc.
  - An aggregator that produces summary.json from verification-results.json.
  - A validator that enforces `findings/*.md` matches the expected set.

Statuses:
  pass     — check fully satisfied
  fail     — check failed; warrants a finding doc
  partial  — partially satisfied; warrants a finding doc by default
  todo     — needs manual review; no judgment yet, no finding doc
  n/a      — not applicable to this profile (rarely persisted explicitly)

Findings persistence policies:
  fail-or-partial  (default)  — FAIL + PARTIAL → finding doc
  fail-only                    — only FAIL → finding doc
  needs-attention              — FAIL + PARTIAL + TODO → finding doc
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# Make `tools.*` importable when this script is invoked directly
# (e.g. `python tools/aggregate_results.py`) and not as part of a package.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402


VALID_STATUSES = ("pass", "fail", "partial", "todo", "n/a")
VALID_SEVERITIES = ("critical", "high", "medium", "low")

POLICIES = {
    "fail-or-partial": ("fail", "partial"),
    "fail-only": ("fail",),
    "needs-attention": ("fail", "partial", "todo"),
}
DEFAULT_POLICY = "fail-or-partial"

BLOCKING_SEVERITIES = ("critical", "high")


class AggregationError(Exception):
    """Base class for schema, aggregation, and validation errors."""


class ValidationError(AggregationError):
    """Raised when persisted findings/ do not match the expected set."""


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    check_id: str
    status: str
    category: str
    severity: str
    evidence: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise AggregationError(
                f"{self.check_id}: invalid status {self.status!r}, "
                f"expected one of {VALID_STATUSES}"
            )
        if self.severity not in VALID_SEVERITIES:
            raise AggregationError(
                f"{self.check_id}: invalid severity {self.severity!r}, "
                f"expected one of {VALID_SEVERITIES}"
            )


@dataclass
class VerificationResults:
    audit_meta: dict[str, Any]
    results: dict[str, CheckResult]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationResults":
        if not isinstance(data, dict):
            raise AggregationError("Top-level results must be a dict")
        if "results" not in data or not isinstance(data["results"], dict):
            raise AggregationError("Missing 'results' object")
        results: dict[str, CheckResult] = {}
        for cid, raw in data["results"].items():
            if not isinstance(raw, dict):
                raise AggregationError(f"{cid}: result must be an object")
            results[cid] = CheckResult(
                check_id=cid,
                status=raw.get("status", ""),
                category=raw.get("category", ""),
                severity=raw.get("severity", ""),
                evidence=list(raw.get("evidence") or []),
                gaps=list(raw.get("gaps") or []),
            )
        return cls(
            audit_meta=dict(data.get("audit_meta") or {}),
            results=results,
        )

    @classmethod
    def from_path(cls, path: Path) -> "VerificationResults":
        text = path.read_text(encoding="utf-8")
        return cls.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(
    vr: VerificationResults,
    policy: str = DEFAULT_POLICY,
) -> dict[str, Any]:
    """Compute the canonical summary from verification results.

    All downstream consumers (audit report, Notion sync, dashboards) must
    read from this output rather than recomputing — this is the bug that
    the inconsistency in the first real audit was caused by.
    """
    if policy not in POLICIES:
        raise AggregationError(
            f"Unknown findings policy {policy!r}; valid: {sorted(POLICIES)}"
        )

    by_status: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    by_severity: dict[str, int] = {s: 0 for s in VALID_SEVERITIES}
    by_category: dict[str, dict[str, int]] = {}

    finding_statuses = POLICIES[policy]
    expected_findings: list[dict[str, Any]] = []
    blocking: list[str] = []

    for cid, r in sorted(vr.results.items()):
        by_status[r.status] = by_status.get(r.status, 0) + 1
        cat = by_category.setdefault(r.category, {s: 0 for s in VALID_STATUSES})
        cat[r.status] = cat.get(r.status, 0) + 1

        if r.status in finding_statuses:
            by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
            expected_findings.append({
                "check_id": cid,
                "category": r.category,
                "severity": r.severity,
                "status": r.status,
            })
            if r.status == "fail" and r.severity in BLOCKING_SEVERITIES:
                blocking.append(cid)

    applicable = sum(
        v for k, v in by_status.items() if k != "n/a"
    )

    summary = {
        "audit_meta": vr.audit_meta,
        "totals": {
            "checks_evaluated": len(vr.results),
            "applicable": applicable,
            "by_status": by_status,
            "by_severity_among_findings": by_severity,
            "by_category": by_category,
        },
        "findings": {
            "policy": policy,
            "policy_statuses": list(finding_statuses),
            "expected_count": len(expected_findings),
            "expected_ids": [f["check_id"] for f in expected_findings],
            "details": expected_findings,
        },
        "production_ready": len(blocking) == 0,
        "blocking_findings": blocking,
    }
    return summary


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def list_finding_files(findings_dir: Path) -> list[Path]:
    if not findings_dir.exists():
        return []
    return sorted(findings_dir.glob("*.md"))


def extract_check_id_from_finding_filename(path: Path) -> str | None:
    """Filenames are conventionally `<CHECK-ID>-<slug>.md`. Returns the
    CHECK-ID prefix if recognisable, else None.
    """
    stem = path.stem
    # Match category prefixes like ARCH-, SEC-, CH-, OBS-, OPS-, SCALE-, SDK-, HITL-
    parts = stem.split("-")
    if len(parts) >= 2 and parts[1].isdigit():
        return f"{parts[0]}-{parts[1]}"
    return None


def validate_findings_persistence(
    summary: dict[str, Any],
    findings_dir: Path,
) -> dict[str, Any]:
    """Compare summary.findings.expected_ids against findings/*.md on disk.

    Returns a structured report. Raises ValidationError if mismatched —
    callers can catch and decide whether to surface as warning or hard fail.
    """
    expected = set(summary["findings"]["expected_ids"])
    files = list_finding_files(findings_dir)
    found: set[str] = set()
    unrecognised: list[str] = []
    for f in files:
        cid = extract_check_id_from_finding_filename(f)
        if cid is None:
            unrecognised.append(f.name)
        else:
            found.add(cid)

    missing = sorted(expected - found)
    unexpected = sorted(found - expected)

    report = {
        "expected_count": len(expected),
        "found_count": len(found),
        "missing": missing,
        "unexpected": unexpected,
        "unrecognised_filenames": unrecognised,
        "consistent": not (missing or unexpected),
    }
    if not report["consistent"]:
        raise ValidationError(
            "Findings on disk don't match summary.expected_ids: "
            f"missing={missing}, unexpected={unexpected}"
        )
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aggregate_results",
        description="Single source of truth for audit verification results.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_agg = sub.add_parser(
        "aggregate",
        help="Compute summary.json from verification-results.json",
    )
    p_agg.add_argument("results", help="Path to verification-results.json")
    p_agg.add_argument(
        "--policy",
        choices=sorted(POLICIES),
        default=DEFAULT_POLICY,
        help=f"Findings persistence policy (default: {DEFAULT_POLICY})",
    )
    p_agg.add_argument(
        "--out",
        default=None,
        help="Write summary.json to this path; otherwise print to stdout",
    )

    p_val = sub.add_parser(
        "validate",
        help="Verify findings/ directory matches summary.expected_ids",
    )
    p_val.add_argument(
        "audit_dir",
        help="Path to audit dir containing summary.json and findings/",
    )
    p_val.add_argument(
        "--summary",
        default=None,
        help="Override summary.json path (default: <audit_dir>/summary.json)",
    )
    p_val.add_argument(
        "--findings-dir",
        default=None,
        help="Override findings dir (default: <audit_dir>/findings)",
    )

    p_exp = sub.add_parser(
        "expected-findings",
        help="List the check IDs that must have a finding doc",
    )
    p_exp.add_argument("results", help="Path to verification-results.json")
    p_exp.add_argument(
        "--policy",
        choices=sorted(POLICIES),
        default=DEFAULT_POLICY,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "aggregate":
        vr = VerificationResults.from_path(Path(args.results))
        summary = aggregate(vr, policy=args.policy)
        text = json.dumps(summary, indent=2, ensure_ascii=False)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    if args.cmd == "validate":
        audit_dir = Path(args.audit_dir)
        summary_path = Path(args.summary) if args.summary else audit_dir / "summary.json"
        findings_dir = (
            Path(args.findings_dir) if args.findings_dir else audit_dir / "findings"
        )
        if not summary_path.exists():
            print(f"Error: {summary_path} not found", file=sys.stderr)
            return 2
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        try:
            report = validate_findings_persistence(summary, findings_dir)
        except ValidationError as e:
            print(json.dumps({"consistent": False, "error": str(e)}, indent=2))
            return 1
        print(json.dumps(report, indent=2))
        return 0

    if args.cmd == "expected-findings":
        vr = VerificationResults.from_path(Path(args.results))
        summary = aggregate(vr, policy=args.policy)
        for cid in summary["findings"]["expected_ids"]:
            print(cid)
        return 0

    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
