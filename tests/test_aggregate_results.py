# -*- coding: utf-8 -*-
"""Tests for tools/aggregate_results.py — single source of truth for audit
verification results.

The fixtures below recreate the exact inconsistency observed in the first
real audit (srgssr-mcp, 2026-04-30): step 4 reported one set of counts,
step 5 announced 15 finding docs, step 6 reported 6, and the on-disk
findings/ dir held only 6. The tests lock in deterministic behaviour so
that bug cannot recur.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.aggregate_results import (
    AggregationError,
    CheckResult,
    POLICIES,
    VerificationResults,
    ValidationError,
    aggregate,
    extract_check_id_from_finding_filename,
    validate_findings_persistence,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def srgssr_results() -> VerificationResults:
    """Reconstructs the srgssr-mcp audit verification results.

    Numbers come from the published audit report:
      PASS=8, FAIL=6, PARTIAL=9, TODO=3, N/A=7   → 33 applicable
    Plus a few representative IDs per status for assertions.
    """
    rows = []
    rows += [("ARCH-009", "pass", "ARCH", "medium")] * 8  # PASS group
    rows += [
        ("ARCH-002", "fail", "ARCH", "medium"),
        ("ARCH-008", "fail", "ARCH", "medium"),
        ("ARCH-012", "fail", "ARCH", "medium"),
        ("SEC-021", "fail", "SEC", "medium"),
        ("OBS-003", "fail", "OBS", "medium"),
        ("OPS-001", "fail", "OPS", "high"),
    ]
    rows += [
        ("ARCH-001", "partial", "ARCH", "medium"),
        ("ARCH-003", "partial", "ARCH", "medium"),
        ("ARCH-004", "partial", "ARCH", "medium"),
        ("ARCH-007", "partial", "ARCH", "medium"),
        ("ARCH-011", "partial", "ARCH", "medium"),
        ("SEC-004", "partial", "SEC", "medium"),
        ("SEC-018", "partial", "SEC", "medium"),
        ("OPS-002", "partial", "OPS", "medium"),
        ("OPS-003", "partial", "OPS", "medium"),
    ]
    rows += [
        ("CH-007", "todo", "CH", "low"),
        ("HITL-002", "todo", "HITL", "medium"),
        ("SDK-005", "todo", "SDK", "low"),
    ]
    rows += [("SEC-099", "n/a", "SEC", "medium")] * 7  # N/A group

    # Synthetic unique IDs for the duplicates so assertions still work
    # — replace placeholder IDs with cid-N so the result dict has unique keys.
    results: dict[str, CheckResult] = {}
    counters: dict[str, int] = {}
    for base_id, status, category, severity in rows:
        n = counters.get(base_id, 0)
        counters[base_id] = n + 1
        cid = base_id if n == 0 else f"{base_id}-DUP{n}"
        results[cid] = CheckResult(
            check_id=cid,
            status=status,
            category=category,
            severity=severity,
        )
    return VerificationResults(
        audit_meta={
            "server_name": "srgssr-mcp",
            "audit_date": "2026-04-30",
            "skill_version": "test",
            "catalog_version": "2026-04",
        },
        results=results,
    )


@pytest.fixture
def minimal_results() -> VerificationResults:
    """Hand-built tiny fixture for arithmetic verification."""
    return VerificationResults(
        audit_meta={"server_name": "tiny", "audit_date": "2026-05-02"},
        results={
            "ARCH-001": CheckResult("ARCH-001", "pass", "ARCH", "medium"),
            "SEC-001": CheckResult("SEC-001", "fail", "SEC", "critical"),
            "OBS-001": CheckResult("OBS-001", "partial", "OBS", "high"),
            "OPS-001": CheckResult("OPS-001", "todo", "OPS", "low"),
            "CH-001": CheckResult("CH-001", "n/a", "CH", "medium"),
        },
    )


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestSchema:
    def test_valid_result(self):
        r = CheckResult("X-001", "pass", "ARCH", "medium")
        assert r.status == "pass"

    def test_invalid_status_rejected(self):
        with pytest.raises(AggregationError, match="invalid status"):
            CheckResult("X-001", "MAYBE", "ARCH", "medium")

    def test_invalid_severity_rejected(self):
        with pytest.raises(AggregationError, match="invalid severity"):
            CheckResult("X-001", "pass", "ARCH", "showstopper")

    def test_from_dict_round_trip(self, minimal_results):
        as_dict = {
            "audit_meta": minimal_results.audit_meta,
            "results": {
                cid: {
                    "status": r.status,
                    "category": r.category,
                    "severity": r.severity,
                    "evidence": r.evidence,
                    "gaps": r.gaps,
                }
                for cid, r in minimal_results.results.items()
            },
        }
        round_tripped = VerificationResults.from_dict(as_dict)
        assert round_tripped.results.keys() == minimal_results.results.keys()

    def test_from_dict_rejects_non_dict(self):
        with pytest.raises(AggregationError):
            VerificationResults.from_dict([])  # type: ignore[arg-type]

    def test_from_dict_requires_results(self):
        with pytest.raises(AggregationError, match="Missing 'results'"):
            VerificationResults.from_dict({"audit_meta": {}})


# ---------------------------------------------------------------------------
# Aggregation arithmetic — locks in the regression
# ---------------------------------------------------------------------------

class TestAggregateMinimal:
    def test_default_policy_counts(self, minimal_results):
        s = aggregate(minimal_results)
        # 5 total, 4 applicable (excluding n/a)
        assert s["totals"]["checks_evaluated"] == 5
        assert s["totals"]["applicable"] == 4
        assert s["totals"]["by_status"]["pass"] == 1
        assert s["totals"]["by_status"]["fail"] == 1
        assert s["totals"]["by_status"]["partial"] == 1
        assert s["totals"]["by_status"]["todo"] == 1
        assert s["totals"]["by_status"]["n/a"] == 1

    def test_default_policy_findings(self, minimal_results):
        s = aggregate(minimal_results)
        # fail-or-partial → SEC-001 (fail) + OBS-001 (partial) = 2
        assert s["findings"]["expected_count"] == 2
        assert set(s["findings"]["expected_ids"]) == {"SEC-001", "OBS-001"}

    def test_fail_only_policy(self, minimal_results):
        s = aggregate(minimal_results, policy="fail-only")
        assert s["findings"]["expected_count"] == 1
        assert s["findings"]["expected_ids"] == ["SEC-001"]

    def test_needs_attention_policy(self, minimal_results):
        s = aggregate(minimal_results, policy="needs-attention")
        # FAIL + PARTIAL + TODO = 3
        assert s["findings"]["expected_count"] == 3
        assert set(s["findings"]["expected_ids"]) == {
            "SEC-001", "OBS-001", "OPS-001",
        }

    def test_blocking_findings_critical_or_high(self, minimal_results):
        s = aggregate(minimal_results)
        # SEC-001 is fail+critical → blocks production.
        # OBS-001 is partial+high → does NOT block (only fail+blocking blocks).
        assert s["production_ready"] is False
        assert s["blocking_findings"] == ["SEC-001"]

    def test_unknown_policy_rejected(self, minimal_results):
        with pytest.raises(AggregationError, match="Unknown findings policy"):
            aggregate(minimal_results, policy="invent-it")


class TestAggregateSrgssrRegression:
    """The srgssr audit is the regression baseline — its counts MUST be
    deterministic regardless of policy.
    """

    def test_total_status_counts_match_audit_report(self, srgssr_results):
        s = aggregate(srgssr_results)
        bs = s["totals"]["by_status"]
        assert bs["pass"] == 8
        assert bs["fail"] == 6
        assert bs["partial"] == 9
        assert bs["todo"] == 3
        assert bs["n/a"] == 7
        # Sum equals applicable + n/a
        assert sum(bs.values()) == 33

    def test_applicable_count_excludes_na(self, srgssr_results):
        s = aggregate(srgssr_results)
        # 8 + 6 + 9 + 3 = 26 applicable (the audit report's 33 figure
        # included n/a; here we treat 'applicable' as 'evaluated and
        # judged' — n/a means not-judged-because-not-relevant).
        assert s["totals"]["applicable"] == 26

    def test_findings_count_default_policy(self, srgssr_results):
        s = aggregate(srgssr_results)
        # Default = fail-or-partial → 6 + 9 = 15
        # This is the number that Step 5 announced. The bug was that
        # step 6 reported only 6 (fail-only) — the policy must be
        # explicit and consistent across all steps.
        assert s["findings"]["expected_count"] == 15

    def test_findings_count_fail_only(self, srgssr_results):
        s = aggregate(srgssr_results, policy="fail-only")
        # The 6 number from Step 6 of the original audit.
        assert s["findings"]["expected_count"] == 6

    def test_blocking_finding_is_ops_001(self, srgssr_results):
        s = aggregate(srgssr_results)
        assert s["production_ready"] is False
        assert "OPS-001" in s["blocking_findings"]
        # No critical-severity fails in srgssr → only OPS-001 (high) blocks.
        assert s["blocking_findings"] == ["OPS-001"]

    def test_summary_totals_sum_to_evaluated(self, srgssr_results):
        s = aggregate(srgssr_results)
        bs = s["totals"]["by_status"]
        assert sum(bs.values()) == s["totals"]["checks_evaluated"]


# ---------------------------------------------------------------------------
# Validation against on-disk findings/
# ---------------------------------------------------------------------------

class TestValidationAgainstDisk:
    def _write_finding(self, dir: Path, check_id: str, slug: str = "test") -> None:
        dir.mkdir(parents=True, exist_ok=True)
        (dir / f"{check_id}-{slug}.md").write_text(
            f"# {check_id}\nbody\n", encoding="utf-8"
        )

    def test_consistent_set(self, tmp_path, minimal_results):
        s = aggregate(minimal_results)
        for cid in s["findings"]["expected_ids"]:
            self._write_finding(tmp_path, cid)
        report = validate_findings_persistence(s, tmp_path)
        assert report["consistent"] is True
        assert report["missing"] == []
        assert report["unexpected"] == []

    def test_missing_finding_raises(self, tmp_path, minimal_results):
        s = aggregate(minimal_results)
        # write only one of the two expected
        self._write_finding(tmp_path, "SEC-001")
        with pytest.raises(ValidationError, match="missing=\\['OBS-001'\\]"):
            validate_findings_persistence(s, tmp_path)

    def test_unexpected_finding_raises(self, tmp_path, minimal_results):
        s = aggregate(minimal_results)
        for cid in s["findings"]["expected_ids"]:
            self._write_finding(tmp_path, cid)
        # extra finding for a check that should not have one
        self._write_finding(tmp_path, "ARCH-001")
        with pytest.raises(ValidationError, match="unexpected"):
            validate_findings_persistence(s, tmp_path)

    def test_empty_findings_dir(self, tmp_path, minimal_results):
        s = aggregate(minimal_results)
        # tmp_path exists but is empty
        with pytest.raises(ValidationError):
            validate_findings_persistence(s, tmp_path)

    def test_missing_findings_dir(self, tmp_path, minimal_results):
        s = aggregate(minimal_results)
        with pytest.raises(ValidationError):
            validate_findings_persistence(s, tmp_path / "does-not-exist")

    def test_srgssr_default_policy_validation(self, tmp_path, srgssr_results):
        s = aggregate(srgssr_results)
        # Persist all 15 expected findings — should validate clean.
        for cid in s["findings"]["expected_ids"]:
            self._write_finding(tmp_path, cid)
        report = validate_findings_persistence(s, tmp_path)
        assert report["consistent"] is True
        assert report["expected_count"] == 15
        assert report["found_count"] == 15

    def test_srgssr_original_audit_bug_is_caught(self, tmp_path, srgssr_results):
        """In the original audit, only 6 of 15 findings were persisted to
        disk. The validator must fail loudly on that mismatch.
        """
        s = aggregate(srgssr_results)
        # Persist only the 6 FAIL findings — replicating the original bug.
        for cid in s["findings"]["expected_ids"]:
            r = srgssr_results.results[cid]
            if r.status == "fail":
                self._write_finding(tmp_path, cid)
        with pytest.raises(ValidationError) as exc:
            validate_findings_persistence(s, tmp_path)
        # The 9 PARTIAL findings should be reported as missing.
        assert "missing=" in str(exc.value)


class TestFilenameParser:
    def test_arch_id_extracted(self):
        assert extract_check_id_from_finding_filename(
            Path("ARCH-001-tool-naming.md")
        ) == "ARCH-001"

    def test_multi_segment_check_id(self):
        assert extract_check_id_from_finding_filename(
            Path("SEC-021-egress-allowlist.md")
        ) == "SEC-021"

    def test_no_id_in_filename(self):
        assert extract_check_id_from_finding_filename(
            Path("README.md")
        ) is None


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------

class TestCli:
    def _write_results(self, path: Path, vr: VerificationResults) -> None:
        as_dict = {
            "audit_meta": vr.audit_meta,
            "results": {
                cid: {
                    "status": r.status,
                    "category": r.category,
                    "severity": r.severity,
                    "evidence": r.evidence,
                    "gaps": r.gaps,
                }
                for cid, r in vr.results.items()
            },
        }
        path.write_text(json.dumps(as_dict, indent=2), encoding="utf-8")

    def test_aggregate_to_file(self, tmp_path, minimal_results):
        from tools.aggregate_results import main
        results_path = tmp_path / "results.json"
        out_path = tmp_path / "summary.json"
        self._write_results(results_path, minimal_results)
        rc = main(["aggregate", str(results_path), "--out", str(out_path)])
        assert rc == 0
        assert out_path.exists()
        summary = json.loads(out_path.read_text(encoding="utf-8"))
        assert summary["findings"]["expected_count"] == 2

    def test_validate_command_passes(self, tmp_path, minimal_results, capsys):
        from tools.aggregate_results import main
        audit_dir = tmp_path / "audit"
        findings_dir = audit_dir / "findings"
        findings_dir.mkdir(parents=True)
        results_path = audit_dir / "verification-results.json"
        summary_path = audit_dir / "summary.json"
        self._write_results(results_path, minimal_results)
        # Aggregate first
        rc = main(["aggregate", str(results_path), "--out", str(summary_path)])
        assert rc == 0
        # Persist expected findings
        for cid in ("SEC-001", "OBS-001"):
            (findings_dir / f"{cid}-test.md").write_text("body", encoding="utf-8")
        rc = main(["validate", str(audit_dir)])
        assert rc == 0

    def test_validate_command_fails_on_mismatch(self, tmp_path, minimal_results):
        from tools.aggregate_results import main
        audit_dir = tmp_path / "audit"
        findings_dir = audit_dir / "findings"
        findings_dir.mkdir(parents=True)
        results_path = audit_dir / "verification-results.json"
        summary_path = audit_dir / "summary.json"
        self._write_results(results_path, minimal_results)
        main(["aggregate", str(results_path), "--out", str(summary_path)])
        # Persist nothing
        rc = main(["validate", str(audit_dir)])
        assert rc == 1

    def test_expected_findings_command(self, tmp_path, minimal_results, capsys):
        from tools.aggregate_results import main
        results_path = tmp_path / "results.json"
        self._write_results(results_path, minimal_results)
        rc = main(["expected-findings", str(results_path)])
        assert rc == 0
        out = capsys.readouterr().out.strip().splitlines()
        assert set(out) == {"SEC-001", "OBS-001"}
