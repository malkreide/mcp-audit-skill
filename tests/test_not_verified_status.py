"""Tests for the `not_verified` status.

`OPS-004` has required this status in prose since it was written; the schema
did not know it, so recording it raised an AggregationError and the check was
written down as `pass` instead — the exact outcome OPS-004 forbids. The tests
here pin the two properties that make the status worth having: it is accepted,
and it is never summed into the passes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.aggregate_results import (
    POLICIES,
    VALID_STATUSES,
    AggregationError,
    CheckResult,
    VerificationResults,
    aggregate,
)
from tools.build_report import render_applicability, render_executive_summary


def _results(**statuses: str) -> VerificationResults:
    return VerificationResults(
        audit_meta={"server_name": "demo"},
        results={
            cid: CheckResult(cid, status, cid.split("-")[0], "high")
            for cid, status in statuses.items()
        },
    )


class TestSchemaAcceptsIt:
    def test_not_verified_is_a_valid_status(self):
        assert "not_verified" in VALID_STATUSES
        CheckResult("OPS-004", "not_verified", "OPS", "high")

    def test_a_typo_is_still_rejected(self):
        with pytest.raises(AggregationError):
            CheckResult("OPS-004", "notverified", "OPS", "high")

    def test_it_survives_a_round_trip_through_the_results_file(self, tmp_path: Path):
        p = tmp_path / "verification-results.json"
        p.write_text(
            json.dumps(
                {
                    "results": {
                        "SEC-001": {
                            "status": "not_verified",
                            "category": "SEC",
                            "severity": "high",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        vr = VerificationResults.from_path(p)
        assert vr.results["SEC-001"].status == "not_verified"


class TestCounting:
    def test_it_has_its_own_counter(self):
        s = aggregate(_results(**{"SEC-001": "not_verified"}))
        assert s["totals"]["by_status"]["not_verified"] == 1

    def test_it_is_never_counted_as_a_pass(self):
        s = aggregate(_results(**{"SEC-001": "not_verified", "ARCH-001": "pass"}))
        assert s["totals"]["by_status"]["pass"] == 1
        assert s["totals"]["by_status"]["not_verified"] == 1

    def test_it_counts_as_applicable_unlike_na(self):
        # It was applicable and attempted; only the answer is missing.
        s = aggregate(_results(**{"SEC-001": "not_verified"}))
        assert s["totals"]["applicable"] == 1

    def test_it_is_listed_beside_the_verdict(self):
        s = aggregate(_results(**{"SEC-001": "not_verified"}))
        assert s["not_verified_findings"] == ["SEC-001"]

    def test_it_does_not_veto_the_release(self):
        # An unanswerable check is not a failed one — but see the report test
        # below: the verdict must say it was reached over an unverified set.
        s = aggregate(_results(**{"SEC-001": "not_verified"}))
        assert s["production_ready"] is True

    def test_it_appears_per_category(self):
        s = aggregate(_results(**{"SEC-001": "not_verified"}))
        assert s["totals"]["by_category"]["SEC"]["not_verified"] == 1


class TestPolicies:
    def test_needs_attention_wants_a_finding_doc_for_it(self):
        assert "not_verified" in POLICIES["needs-attention"]
        s = aggregate(_results(**{"SEC-001": "not_verified"}), policy="needs-attention")
        assert s["findings"]["expected_ids"] == ["SEC-001"]

    @pytest.mark.parametrize("policy", ["fail-or-partial", "fail-only"])
    def test_default_policies_do_not_demand_a_finding_doc(self, policy):
        s = aggregate(_results(**{"SEC-001": "not_verified"}), policy=policy)
        assert s["findings"]["expected_ids"] == []


class TestReporting:
    def test_executive_summary_names_the_unverified_checks(self):
        s = aggregate(_results(**{"SEC-001": "not_verified", "ARCH-001": "pass"}))
        out = render_executive_summary(s)
        assert "SEC-001" in out
        assert "nicht verifiziert" in out

    def test_a_green_verdict_says_it_was_reached_over_an_unverified_set(self):
        s = aggregate(_results(**{"SEC-001": "not_verified"}))
        out = render_executive_summary(s)
        assert "Production-Readiness:** YES" in out
        assert "nicht verifizierte Checks" in out

    def test_a_clean_run_gets_no_unverified_noise(self):
        s = aggregate(_results(**{"ARCH-001": "pass"}))
        out = render_executive_summary(s)
        assert "nicht verifiziert" not in out

    def test_applicability_table_has_its_own_column(self):
        s = aggregate(_results(**{"SEC-001": "not_verified", "ARCH-001": "pass"}))
        out = render_applicability(s)
        assert "Not verified" in out
        rows = [ln for ln in out.splitlines() if ln.startswith("|")]
        # Every row, header separator included, must carry the same cell count;
        # a status column added to the header but not to the rows would shift
        # every number one place to the left.
        assert len({ln.count("|") for ln in rows}) == 1
        assert rows[0].count("|") == 8  # 7 columns
        assert "| **Total** | **1** | **0** | **0** | **1** | **0** | **0** |" in out
