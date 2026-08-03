#!/usr/bin/env python3
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
  pass          — check fully satisfied, on positive evidence
  fail          — check failed; warrants a finding doc
  partial       — partially satisfied; warrants a finding doc by default
  not_verified  — applicable, attempted, no evidence either way
  todo          — needs manual review; not attempted yet
  n/a           — not applicable to this profile (rarely persisted explicitly)

`not_verified` exists because `OPS-004` has demanded it in prose since it was
written — "a `pass` rests on positive evidence, not on the absence of negative
evidence; otherwise the status is `not_verified`" — while this schema knew no
such value. A status the schema rejects cannot be recorded, so the checks that
rule was written for were being recorded as `pass`: the one outcome `OPS-004`
names as the failure. "Could not be established" now has somewhere to go, and
its own counter, so it is never summed into the passes.

The distinction against `todo` is whether anyone looked. `todo` is work not
started; `not_verified` is work done that produced no answer — a tool that
could not be reached, a behaviour reproducible only in production, a grep whose
pattern cannot be shown to fire when the anti-pattern is present. Only the
second belongs under «Offen» in the report; the first belongs on the to-do list.

Findings persistence policies:
  fail-or-partial  (default)  — FAIL + PARTIAL → finding doc
  fail-only                    — only FAIL → finding doc
  needs-attention              — FAIL + PARTIAL + TODO + NOT_VERIFIED → finding doc
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Make `tools.*` importable when this script is invoked directly
# (e.g. `python tools/aggregate_results.py`) and not as part of a package.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.compare_guard import (  # noqa: E402
    EmptyComparisonError,
    require_non_empty,
)
from tools.parse_catalog import (  # noqa: E402
    DEFAULT_ADOPTION,
    VALID_ADOPTIONS,
    parse_catalog,
)
from tools.path_utils import force_utf8_stdio  # noqa: E402

VALID_STATUSES = ("pass", "fail", "partial", "not_verified", "todo", "n/a")
VALID_SEVERITIES = ("critical", "high", "medium", "low")

POLICIES = {
    "fail-or-partial": ("fail", "partial"),
    "fail-only": ("fail",),
    "needs-attention": ("fail", "partial", "todo", "not_verified"),
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
    adoption: str = DEFAULT_ADOPTION
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
        if self.adoption not in VALID_ADOPTIONS:
            raise AggregationError(
                f"{self.check_id}: invalid adoption {self.adoption!r}, "
                f"expected one of {VALID_ADOPTIONS}"
            )


@dataclass
class VerificationResults:
    audit_meta: dict[str, Any]
    results: dict[str, CheckResult]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationResults:
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
                adoption=raw.get("adoption") or DEFAULT_ADOPTION,
                evidence=list(raw.get("evidence") or []),
                gaps=list(raw.get("gaps") or []),
            )
        return cls(
            audit_meta=dict(data.get("audit_meta") or {}),
            results=results,
        )

    @classmethod
    def from_path(cls, path: Path) -> VerificationResults:
        text = path.read_text(encoding="utf-8")
        return cls.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def apply_catalog_adoption(vr: VerificationResults, checks_dir: Path) -> list[str]:
    """Overwrite each result's adoption stage from the catalogue.

    The catalogue is authoritative. Leaving the stage to whoever wrote
    verification-results.json means a check is enforced or advisory depending
    on whether that step remembered the field — and the failure would be
    silent in the direction that matters, a blocking check quietly demoted.

    Returns the IDs present in the results but absent from the catalogue, so
    the caller can report them rather than let them keep the default.
    """
    catalog = parse_catalog(checks_dir)
    unknown: list[str] = []
    for cid, result in vr.results.items():
        fm = catalog.get(cid)
        if fm is None:
            unknown.append(cid)
            continue
        result.adoption = fm.get("adoption", DEFAULT_ADOPTION)
    return sorted(unknown)


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

    by_status: dict[str, int] = dict.fromkeys(VALID_STATUSES, 0)
    by_severity: dict[str, int] = dict.fromkeys(VALID_SEVERITIES, 0)
    by_category: dict[str, dict[str, int]] = {}

    finding_statuses = POLICIES[policy]
    expected_findings: list[dict[str, Any]] = []
    blocking: list[str] = []
    advisory: list[str] = []
    not_verified: list[str] = []
    by_adoption: dict[str, int] = dict.fromkeys(VALID_ADOPTIONS, 0)

    for cid, r in sorted(vr.results.items()):
        by_status[r.status] = by_status.get(r.status, 0) + 1
        cat = by_category.setdefault(r.category, dict.fromkeys(VALID_STATUSES, 0))
        cat[r.status] = cat.get(r.status, 0) + 1

        if r.status != "n/a":
            by_adoption[r.adoption] = by_adoption.get(r.adoption, 0) + 1

        if r.status == "not_verified":
            not_verified.append(cid)

        if r.status in finding_statuses:
            by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
            expected_findings.append(
                {
                    "check_id": cid,
                    "category": r.category,
                    "severity": r.severity,
                    "status": r.status,
                    "adoption": r.adoption,
                }
            )
            # An advisory check still produces a finding — it is reported,
            # counted and carries the same severity. It just does not veto the
            # release. That is the whole distinction: severity describes the
            # violation, adoption describes whether the catalogue is yet
            # entitled to hold this portfolio to it.
            if r.status == "fail" and r.severity in BLOCKING_SEVERITIES:
                if r.adoption == "enforced":
                    blocking.append(cid)
                else:
                    advisory.append(cid)

    applicable = sum(v for k, v in by_status.items() if k != "n/a")

    summary = {
        "audit_meta": vr.audit_meta,
        "totals": {
            "checks_evaluated": len(vr.results),
            "applicable": applicable,
            "by_status": by_status,
            "by_severity_among_findings": by_severity,
            "by_category": by_category,
            "by_adoption": by_adoption,
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
        # Checks that were attempted and yielded no evidence either way. They
        # do not veto the release — an unanswerable check is not a failed one —
        # but they are listed beside the verdict rather than folded into it,
        # because a green verdict over a large unverified set is a different
        # claim from a green verdict over none, and `OPS-004` requires the
        # reader to be able to tell those apart.
        "not_verified_findings": not_verified,
        # Would have blocked if the check were enforced. Reported separately so
        # a green verdict never hides the fact that an advisory check failed —
        # a promotion candidate is visible before it is promoted, not after it
        # turns the whole portfolio red.
        "advisory_findings": advisory,
    }
    return summary


# ---------------------------------------------------------------------------
# Catalog epochs
# ---------------------------------------------------------------------------


def compare_catalog_epoch(
    summary: dict[str, Any],
    previous: dict[str, Any],
    allow_empty: bool = False,
) -> dict[str, Any]:
    """Decide whether this run's numbers may be compared with the previous run's.

    Two audits of the same server are only a trend if they were measured with
    the same ruler. When the catalogue changes between them — checks added,
    removed, or rewritten — «30 pass / 4 fail / 2 partial → x/y/z» is not a
    delta; it is two different measurements written next to each other with an
    arrow between them. In the run this comes from, the arrow would have spanned
    36 checks against 54, and every number would have been read as movement in
    the server.

    So the comparison is not adjusted or normalised — it is refused. There is no
    correct way to subtract a count taken over one catalogue from a count taken
    over another, and a footnote does not survive being quoted. `comparable`
    false means the report prints the two epochs and no arrow.

    An unknown hash on either side is also `comparable: false`. Not knowing
    whether the ruler changed is not the same as knowing it did not, and the
    safe direction is the one that declines to draw the line.
    """
    meta = summary.get("audit_meta", {}) or {}
    prev_meta = previous.get("audit_meta", {}) or {}

    current_hash = str(meta.get("catalog_hash") or "")
    previous_hash = str(prev_meta.get("catalog_hash") or "")

    current_n = int(summary.get("totals", {}).get("checks_evaluated", 0) or 0)
    previous_n = int(previous.get("totals", {}).get("checks_evaluated", 0) or 0)

    # A previous run that evaluated nothing is not a baseline. Comparing
    # against it yields a delta that is entirely this run's own numbers,
    # presented as change — the same empty-set trap the applicability diff
    # walked into.
    require_non_empty(
        f"the previous run ({prev_meta.get('run_id') or 'unnamed'}) check set",
        range(previous_n),
        hint="It evaluated 0 checks; there is no baseline to compare against.",
        allow_empty=allow_empty,
    )

    epoch: dict[str, Any] = {
        "previous_run_id": str(prev_meta.get("run_id") or ""),
        "previous_catalog_hash": previous_hash,
        "catalog_hash": current_hash,
        "previous_checks_evaluated": previous_n,
        "checks_evaluated": current_n,
        "comparable": False,
        "reason": "",
    }

    if not current_hash or not previous_hash:
        missing = "this run" if not current_hash else "the previous run"
        epoch["reason"] = (
            f"catalog_hash is missing for {missing}, so it cannot be shown that "
            "both audits used the same catalogue. Trend comparison refused — "
            "unknown is not the same as unchanged."
        )
        return epoch

    if current_hash != previous_hash:
        epoch["reason"] = (
            f"catalogue changed between the runs ({previous_hash[:12]} → "
            f"{current_hash[:12]}), {previous_n} checks then against "
            f"{current_n} now. The two runs measured with different rulers; "
            "their counts are not a trend line."
        )
        return epoch

    epoch["comparable"] = True
    epoch["reason"] = f"same catalogue ({current_hash[:12]}) in both runs"
    epoch["delta_by_status"] = {
        status: (
            int(summary.get("totals", {}).get("by_status", {}).get(status, 0))
            - int(previous.get("totals", {}).get("by_status", {}).get(status, 0))
        )
        for status in VALID_STATUSES
    }
    return epoch


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


def finding_substance(path: Path) -> int:
    """Non-whitespace character count of a finding document.

    Whitespace is stripped before counting because a file holding a newline is
    exactly as informative as one holding nothing, and the failure this guards
    against produces both.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    return len("".join(text.split()))


def validate_findings_persistence(
    summary: dict[str, Any],
    findings_dir: Path,
    min_substance: int = 1,
) -> dict[str, Any]:
    """Compare summary.findings.expected_ids against findings/*.md on disk.

    Checks three things, not one: that a file exists per expected id, that no
    unexpected id has a file, and that each file **says something**.

    That third check exists because its absence caused a real false pass. A
    carry-forward step wrote zero-byte placeholders for 16 findings across two
    audit runs — the earlier runs name files `<ID>-<slug>.md` while the script
    looked for a bare `<ID>.md`, found nothing, and created an empty stub it
    never filled. Every one of those directories validated `consistent: true`,
    because existence was the only thing being asked.

    An empty finding document is worse than a missing one. A missing file fails
    this gate; an empty file passed it while telling a reader nothing about a
    finding that is genuinely open — and `SECURITY.md` in the audited repos
    points at these directories as the record of the current open set.

    `min_substance` counts non-whitespace characters and defaults to 1, so the
    default catches only the unambiguous case. Raise it to require more
    (`--min-substance`) when a run should not accept stub findings either;
    deliberately not defaulted higher, because a terse finding is legitimate and
    a guard that cries wolf gets bypassed.

    Returns a structured report. Raises ValidationError if inconsistent —
    callers can catch and decide whether to surface as warning or hard fail.
    """
    expected = set(summary["findings"]["expected_ids"])
    files = list_finding_files(findings_dir)
    found: set[str] = set()
    unrecognised: list[str] = []
    substance: dict[str, int] = {}
    for f in files:
        cid = extract_check_id_from_finding_filename(f)
        if cid is None:
            unrecognised.append(f.name)
        else:
            found.add(cid)
            # Keep the largest when several files map to one id (slugged plus
            # bare), so a stray stub next to a real document does not fail it.
            substance[cid] = max(substance.get(cid, 0), finding_substance(f))

    missing = sorted(expected - found)
    unexpected = sorted(found - expected)
    empty = sorted(
        cid for cid in expected & found if substance.get(cid, 0) < min_substance
    )

    report = {
        "expected_count": len(expected),
        "found_count": len(found),
        "missing": missing,
        "unexpected": unexpected,
        "empty": empty,
        "min_substance": min_substance,
        "unrecognised_filenames": unrecognised,
        "consistent": not (missing or unexpected or empty),
    }
    if not report["consistent"]:
        raise ValidationError(
            "Findings on disk don't match summary.expected_ids: "
            f"missing={missing}, unexpected={unexpected}, "
            f"empty={empty} (below {min_substance} non-whitespace chars)"
        )
    return report


def _validate_target(
    audit_dir: Path,
    report: dict[str, Any],
    repo_override: Path | None = None,
) -> bool:
    """Re-check the audited repo's revision, folding the result into `report`.

    Split three ways on purpose:

    - **Moved** is a hard failure. The findings describe two different trees
      and the report presents them as one.
    - **Unrecorded** is a warning, not a failure. Runs initialised before
      `--target-repo` existed have no SHA to check, and failing them would
      only teach auditors to pass `--skip-target-check` by reflex — which
      would disable the case that matters too.
    - **Unreachable** (repo moved or deleted since init) is a warning as well,
      with the path named, because the auditor is the only one who can say
      where it went.

    The distinction lands in `report["target"]["status"]` either way, so a
    warning is still a written record rather than a line of scrollback.
    """
    from tools.audit_init import TargetRepoError, verify_target

    meta_path = audit_dir / "audit-meta.json"
    if not meta_path.exists():
        report["target"] = {
            "status": "unrecorded",
            "reason": f"{meta_path} not found; nothing pins the audited revision",
        }
        print(f"Warning: {report['target']['reason']}", file=sys.stderr)
        return True

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report["target"] = {"status": "unreadable", "reason": f"{meta_path}: {e}"}
        print(f"Warning: cannot read {meta_path}: {e}", file=sys.stderr)
        return True

    try:
        result = verify_target(meta, repo_override=repo_override)
    except TargetRepoError as e:
        report["target"] = {"status": "unreachable", "reason": str(e)}
        print(f"Warning: cannot verify the audited repo: {e}", file=sys.stderr)
        return True

    if result["unchanged"]:
        result["status"] = "unchanged"
        report["target"] = result
        return True

    if not result["recorded"]:
        result["status"] = "unrecorded"
        report["target"] = result
        print(f"Warning: {result['reason']}", file=sys.stderr)
        return True

    result["status"] = "moved"
    report["target"] = result
    report["consistent"] = False
    print(f"Error: {result['reason']}", file=sys.stderr)
    return False


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
    p_agg.add_argument(
        "--checks-dir",
        default=None,
        help=(
            "Take each check's adoption stage from this catalogue rather than "
            "from the results file. Recommended: the catalogue is authoritative, "
            "and a results file that omits the field silently gets the enforced "
            "default"
        ),
    )
    p_agg.add_argument(
        "--previous",
        default=None,
        metavar="SUMMARY_OR_RUN_DIR",
        help=(
            "Previous run's summary.json (or its run dir) to compare against. "
            "Writes a catalog_epoch block recording whether the two runs share "
            "a catalogue — build_report.py refuses the trend line when they "
            "do not"
        ),
    )
    p_agg.add_argument(
        "--allow-empty-previous",
        action="store_true",
        help="Compare against a previous run that evaluated 0 checks (not a baseline)",
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
    p_val.add_argument(
        "--min-substance",
        type=int,
        default=1,
        help=(
            "Minimum non-whitespace characters a finding document must contain "
            "(default: 1, i.e. reject only empty files). Raise it to reject "
            "stubs as well."
        ),
    )
    p_val.add_argument(
        "--skip-target-check",
        action="store_true",
        help=(
            "Do not re-verify the audited repo's HEAD against the SHA recorded "
            "in audit-meta.json. Only for auditing a tree that is expected to "
            "move, e.g. a live remediation session"
        ),
    )
    p_val.add_argument(
        "--target-repo",
        default=None,
        help="Where the audited repo lives now, if it moved since init",
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
        if args.checks_dir:
            unknown = apply_catalog_adoption(vr, Path(args.checks_dir))
            if unknown:
                # Loud, not fatal: an unknown id keeps the enforced default, so
                # the verdict stays on the safe side — but a result the
                # catalogue does not know about is worth saying out loud.
                print(
                    f"Warning: {len(unknown)} result id(s) not in the catalogue, "
                    f"keeping the {DEFAULT_ADOPTION} default: {', '.join(unknown)}",
                    file=sys.stderr,
                )
        summary = aggregate(vr, policy=args.policy)

        if args.checks_dir:
            # The catalogue on disk is what this run was actually measured
            # with, so it — not a hand-copied field — is what pins the epoch.
            from tools.audit_init import hash_catalog

            live_hash = hash_catalog(Path(args.checks_dir))
            recorded = summary["audit_meta"].get("catalog_hash")
            if recorded and recorded != live_hash:
                # Same class of problem as a moving target SHA, one layer over:
                # the ruler changed mid-run rather than the thing measured.
                print(
                    f"Warning: catalog_hash in the results ({str(recorded)[:12]}) "
                    f"differs from {args.checks_dir} ({live_hash[:12]}) — the "
                    "catalogue changed during the run. Recording the live hash.",
                    file=sys.stderr,
                )
            summary["audit_meta"]["catalog_hash"] = live_hash

        if args.previous:
            prev_path = Path(args.previous)
            if prev_path.is_dir():
                prev_path = prev_path / "summary.json"
            if not prev_path.exists():
                print(f"Error: {prev_path} not found", file=sys.stderr)
                return 2
            try:
                previous = json.loads(prev_path.read_text(encoding="utf-8"))
                epoch = compare_catalog_epoch(
                    summary, previous, allow_empty=args.allow_empty_previous
                )
            except json.JSONDecodeError as e:
                print(f"Error: cannot read {prev_path}: {e}", file=sys.stderr)
                return 2
            except EmptyComparisonError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 2
            epoch["previous_summary"] = str(prev_path)
            summary["catalog_epoch"] = epoch
            if not epoch["comparable"]:
                print(
                    f"Warning: trend line broken — {epoch['reason']}", file=sys.stderr
                )

        text = json.dumps(summary, indent=2, ensure_ascii=False)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    if args.cmd == "validate":
        audit_dir = Path(args.audit_dir)
        summary_path = (
            Path(args.summary) if args.summary else audit_dir / "summary.json"
        )
        findings_dir = (
            Path(args.findings_dir) if args.findings_dir else audit_dir / "findings"
        )
        if not summary_path.exists():
            print(f"Error: {summary_path} not found", file=sys.stderr)
            return 2
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        try:
            report = validate_findings_persistence(
                summary, findings_dir, min_substance=args.min_substance
            )
        except ValidationError as e:
            print(json.dumps({"consistent": False, "error": str(e)}, indent=2))
            return 1

        target_ok = True
        if not args.skip_target_check:
            target_ok = _validate_target(
                audit_dir,
                report,
                repo_override=Path(args.target_repo) if args.target_repo else None,
            )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if target_ok else 1

    if args.cmd == "expected-findings":
        vr = VerificationResults.from_path(Path(args.results))
        summary = aggregate(vr, policy=args.policy)
        for cid in summary["findings"]["expected_ids"]:
            print(cid)
        return 0

    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
