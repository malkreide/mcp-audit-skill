# -*- coding: utf-8 -*-
"""Tests for tools/build_report.py — audit-report generation from summary.json."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.aggregate_results import (
    CheckResult,
    VerificationResults,
    aggregate,
)
from tools.build_report import (
    build_report,
    main,
    render_applicability,
    render_executive_summary,
    render_findings_table,
    render_metadata,
    render_profile_snapshot,
    render_remediation_plan,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def srgssr_summary() -> dict:
    """Summary mirroring the srgssr-mcp audit (FAIL+PARTIAL policy)."""
    vr = VerificationResults(
        audit_meta={
            "server_name": "srgssr-mcp",
            "audit_date": "2026-04-30",
            "skill_version": "0.8-test",
            "catalog_version": "2026-04",
            "policy": "fail-or-partial",
        },
        results={
            "ARCH-001": CheckResult("ARCH-001", "pass", "ARCH", "medium"),
            "ARCH-002": CheckResult("ARCH-002", "fail", "ARCH", "medium"),
            "OPS-001": CheckResult("OPS-001", "fail", "OPS", "high"),
            "SEC-021": CheckResult("SEC-021", "partial", "SEC", "medium"),
        },
    )
    return aggregate(vr)


@pytest.fixture
def empty_summary() -> dict:
    """All checks pass — clean audit."""
    vr = VerificationResults(
        audit_meta={"server_name": "perfect-mcp", "audit_date": "2026-05-02"},
        results={
            "ARCH-001": CheckResult("ARCH-001", "pass", "ARCH", "medium"),
            "SEC-001": CheckResult("SEC-001", "pass", "SEC", "high"),
        },
    )
    return aggregate(vr)


@pytest.fixture
def sample_profile() -> dict:
    return {
        "transport": "stdio-only",
        "auth_model": "none",
        "data_class": "Public Open Data",
        "write_capable": False,
        "deployment": ["local-stdio"],
        "tools_make_external_requests": True,
        "data_source": {"is_swiss_open_data": True},
    }


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

class TestExecutiveSummary:
    def test_includes_server_name(self, srgssr_summary):
        out = render_executive_summary(srgssr_summary)
        assert "srgssr-mcp" in out
        assert "Production-Readiness" in out

    def test_blocking_findings_called_out(self, srgssr_summary):
        out = render_executive_summary(srgssr_summary)
        assert "OPS-001" in out  # blocking finding
        assert "NICHT erreicht" in out

    def test_clean_audit_marks_ready(self, empty_summary):
        out = render_executive_summary(empty_summary)
        assert "Production-Readiness:" in out
        assert "YES" in out
        assert "erreicht" in out and "NICHT" not in out


class TestProfileSnapshot:
    def test_renders_known_profile_fields(self, srgssr_summary, sample_profile):
        out = render_profile_snapshot(srgssr_summary, sample_profile)
        assert "stdio-only" in out
        assert "Public Open Data" in out
        assert "is_swiss_open_data" in out

    def test_works_without_profile(self, srgssr_summary):
        out = render_profile_snapshot(srgssr_summary, {})
        assert "srgssr-mcp" in out
        assert "Audit-Datum" in out


class TestApplicability:
    def test_status_table_includes_categories(self, srgssr_summary):
        out = render_applicability(srgssr_summary)
        assert "ARCH" in out
        assert "SEC" in out
        assert "OPS" in out
        assert "Total" in out

    def test_counts_match_summary(self, srgssr_summary):
        out = render_applicability(srgssr_summary)
        bs = srgssr_summary["totals"]["by_status"]
        # Total row uses bold formatting
        assert f"**{bs['pass']}**" in out
        assert f"**{bs['fail']}**" in out


class TestFindingsTable:
    def test_lists_expected_findings(self, srgssr_summary):
        out = render_findings_table(srgssr_summary)
        assert "ARCH-002" in out
        assert "OPS-001" in out
        assert "SEC-021" in out

    def test_severity_sort_high_first(self, srgssr_summary):
        out = render_findings_table(srgssr_summary)
        ops_pos = out.index("OPS-001")
        sec_pos = out.index("SEC-021")
        # OPS-001 is high → should appear before SEC-021 (medium)
        assert ops_pos < sec_pos

    def test_empty_findings_handled(self, empty_summary):
        out = render_findings_table(empty_summary)
        assert "Keine Findings" in out

    def test_policy_disclosed(self, srgssr_summary):
        out = render_findings_table(srgssr_summary)
        assert "fail-or-partial" in out


class TestRemediationPlan:
    def test_lists_findings_in_order(self, srgssr_summary):
        out = render_remediation_plan(srgssr_summary)
        ops_pos = out.index("OPS-001")
        sec_pos = out.index("SEC-021")
        assert ops_pos < sec_pos

    def test_empty_findings_handled(self, empty_summary):
        out = render_remediation_plan(empty_summary)
        assert "Keine Findings" in out


class TestMetadata:
    def test_includes_skill_version(self, srgssr_summary):
        out = render_metadata(srgssr_summary)
        assert "skill_version" in out
        assert "0.8-test" in out


# ---------------------------------------------------------------------------
# End-to-end build
# ---------------------------------------------------------------------------

class TestBuildReport:
    def test_full_report_includes_all_sections(
        self, tmp_path, srgssr_summary, sample_profile,
    ):
        findings_dir = tmp_path / "findings"
        findings_dir.mkdir()
        for cid in srgssr_summary["findings"]["expected_ids"]:
            (findings_dir / f"{cid}-test.md").write_text(
                f"## Finding: {cid}\n\nbody for {cid}\n",
                encoding="utf-8",
            )
        report = build_report(srgssr_summary, sample_profile, findings_dir)
        assert "## 1. Executive Summary" in report
        assert "## 2. Profil-Snapshot" in report
        assert "## 3. Applicability" in report
        assert "## 4. Findings-Übersicht" in report
        assert "## 5. Detail-Findings" in report
        assert "## 6. Remediation-Plan" in report
        assert "## 7. Audit-Metadata" in report
        # All findings embedded by ID
        for cid in srgssr_summary["findings"]["expected_ids"]:
            assert cid in report
            assert f"body for {cid}" in report

    def test_missing_finding_doc_flagged_in_report(
        self, tmp_path, srgssr_summary,
    ):
        findings_dir = tmp_path / "findings"
        findings_dir.mkdir()
        # Persist only one of three expected findings.
        (findings_dir / "ARCH-002-test.md").write_text(
            "## Finding: ARCH-002\n\ndocumented\n", encoding="utf-8",
        )
        report = build_report(srgssr_summary, {}, findings_dir)
        # Missing findings get a warning section
        assert "missing finding doc" in report
        assert "OPS-001" in report
        assert "SEC-021" in report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCli:
    def _setup_audit_dir(
        self,
        tmp_path: Path,
        summary: dict,
        profile: dict | None = None,
    ) -> Path:
        audit_dir = tmp_path / "audit"
        findings_dir = audit_dir / "findings"
        findings_dir.mkdir(parents=True)
        (audit_dir / "summary.json").write_text(
            json.dumps(summary), encoding="utf-8",
        )
        for cid in summary["findings"]["expected_ids"]:
            (findings_dir / f"{cid}-test.md").write_text(
                f"## {cid}\nbody\n", encoding="utf-8",
            )
        if profile:
            (audit_dir / "profile.json").write_text(
                json.dumps(profile), encoding="utf-8",
            )
        return audit_dir

    def test_cli_writes_default_path(self, tmp_path, srgssr_summary):
        audit_dir = self._setup_audit_dir(tmp_path, srgssr_summary)
        rc = main([str(audit_dir)])
        assert rc == 0
        out = audit_dir / "audit-report.md"
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        assert "srgssr-mcp" in text

    def test_cli_with_profile(self, tmp_path, srgssr_summary, sample_profile):
        audit_dir = self._setup_audit_dir(tmp_path, srgssr_summary, sample_profile)
        rc = main([str(audit_dir), "--profile", str(audit_dir / "profile.json")])
        assert rc == 0
        out = (audit_dir / "audit-report.md").read_text(encoding="utf-8")
        assert "stdio-only" in out

    def test_cli_custom_out_path(self, tmp_path, srgssr_summary):
        audit_dir = self._setup_audit_dir(tmp_path, srgssr_summary)
        out_path = tmp_path / "custom.md"
        rc = main([str(audit_dir), "--out", str(out_path)])
        assert rc == 0
        assert out_path.exists()

    def test_cli_missing_summary_returns_two(self, tmp_path):
        rc = main([str(tmp_path)])
        assert rc == 2
