# -*- coding: utf-8 -*-
"""Tests for tools/propose_release.py — semver, CHANGELOG insertion,
production-ready gating, and proposal output structure."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.propose_release import (
    AuditSummary,
    ReleaseError,
    bump_version,
    detect_current_version,
    insert_changelog_entry,
    render_changelog_entry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def audit_dir(tmp_path: Path) -> Path:
    d = tmp_path / "audit"
    d.mkdir()
    summary = {
        "audit_meta": {
            "server_name": "example-mcp",
            "run_id": "2026-05-09T120000-Z-example-mcp",
            "skill_version": "1.0.0",
            "catalog_hash": "abcdef0123456789" * 4,  # 64 chars
            "started_at": "2026-05-09T12:00:00Z",
        },
        "totals": {
            "checks_evaluated": 20,
            "applicable": 20,
            "by_status": {"pass": 18, "fail": 0, "partial": 0, "todo": 2, "n/a": 0},
            "by_severity_among_findings": {"critical": 0, "high": 0,
                                           "medium": 0, "low": 0},
        },
        "findings": {
            "policy": "fail-or-partial",
            "expected_count": 0,
            "expected_ids": [],
            "details": [],
        },
        "production_ready": True,
        "blocking_findings": [],
    }
    (d / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return d


@pytest.fixture
def failing_audit_dir(tmp_path: Path) -> Path:
    d = tmp_path / "audit_fail"
    d.mkdir()
    summary = {
        "audit_meta": {"server_name": "broken-mcp", "run_id": "rid"},
        "totals": {
            "checks_evaluated": 5,
            "applicable": 5,
            "by_status": {"pass": 2, "fail": 3, "partial": 0, "todo": 0, "n/a": 0},
            "by_severity_among_findings": {"critical": 1, "high": 2,
                                           "medium": 0, "low": 0},
        },
        "findings": {"policy": "fail-or-partial", "expected_count": 3,
                     "expected_ids": ["SEC-001", "SEC-002", "SEC-003"],
                     "details": []},
        "production_ready": False,
        "blocking_findings": ["SEC-001", "SEC-002", "SEC-003"],
    }
    (d / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# AuditSummary
# ---------------------------------------------------------------------------

class TestAuditSummary:
    def test_loads_from_dir(self, audit_dir: Path) -> None:
        s = AuditSummary.from_dir(audit_dir)
        assert s.production_ready is True
        assert s.blocking_findings == []
        assert s.server_name == "example-mcp"
        assert s.run_id.startswith("2026-05-09T")

    def test_missing_summary_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ReleaseError, match="summary.json not found"):
            AuditSummary.from_dir(tmp_path)

    def test_meta_overrides_audit_meta(self, audit_dir: Path) -> None:
        # audit-meta.json beats inline audit_meta on overlap.
        (audit_dir / "audit-meta.json").write_text(
            json.dumps({"server_name": "from-meta", "run_id": "from-meta-rid",
                        "skill_version": "9.9.9"}),
            encoding="utf-8",
        )
        s = AuditSummary.from_dir(audit_dir)
        assert s.server_name == "from-meta"
        assert s.skill_version == "9.9.9"


# ---------------------------------------------------------------------------
# Semver bump
# ---------------------------------------------------------------------------

class TestBumpVersion:
    @pytest.mark.parametrize("current,bump,expected", [
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "major", "2.0.0"),
        ("0.0.0", "patch", "0.0.1"),
        ("v1.0.0", "minor", "1.1.0"),  # leading v tolerated
        ("1.0.0-rc1", "patch", "1.0.1"),  # pre-release suffix dropped
    ])
    def test_bumps(self, current: str, bump: str, expected: str) -> None:
        assert bump_version(current, bump) == expected

    def test_invalid_bump(self) -> None:
        with pytest.raises(ReleaseError, match="Invalid bump"):
            bump_version("1.0.0", "bogus")

    def test_non_semver_raises(self) -> None:
        with pytest.raises(ReleaseError, match="not semver-shaped"):
            bump_version("foo.bar", "patch")


# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------

class TestDetectCurrentVersion:
    def test_pyproject_wins(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "1.2.3"\n',
            encoding="utf-8",
        )
        v, src = detect_current_version(tmp_path)
        assert (v, src) == ("1.2.3", "pyproject")

    def test_package_json_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "x", "version": "0.4.0"}),
            encoding="utf-8",
        )
        v, src = detect_current_version(tmp_path)
        assert (v, src) == ("0.4.0", "package")

    def test_none_when_no_metadata(self, tmp_path: Path) -> None:
        v, src = detect_current_version(tmp_path)
        assert src in ("none", "git")  # may pick up git tag if tmp is in a repo

    def test_pyproject_only_inside_project_section(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nversion = "9.9.9"\n[project]\nversion = "1.0.0"\n',
            encoding="utf-8",
        )
        v, _ = detect_current_version(tmp_path)
        assert v == "1.0.0"


# ---------------------------------------------------------------------------
# CHANGELOG rendering / insertion
# ---------------------------------------------------------------------------

class TestChangelog:
    def _summary(self) -> AuditSummary:
        return AuditSummary(
            production_ready=True,
            blocking_findings=[],
            by_status={"pass": 18, "fail": 0, "partial": 0, "todo": 2, "n/a": 0},
            by_severity={},
            server_name="example-mcp",
            run_id="2026-05-09T120000-Z-example-mcp",
            skill_version="1.0.0",
            catalog_hash="abcdef" * 10,
            started_at="2026-05-09T12:00:00Z",
            findings_count=0,
        )

    def test_render_includes_audit_metadata(self) -> None:
        entry = render_changelog_entry("1.2.3", self._summary(),
                                       notes="Added X.", today="2026-05-09")
        assert "## [v1.2.3] — 2026-05-09" in entry
        assert "Added X." in entry
        assert "Production-ready:" in entry
        assert "2026-05-09T120000-Z-example-mcp" in entry
        assert "18 pass" in entry

    def test_render_without_notes(self) -> None:
        entry = render_changelog_entry("0.1.0", self._summary(), None, "2026-01-01")
        assert "## [v0.1.0]" in entry
        assert "### Audit verification" in entry

    def test_insert_new_file(self, tmp_path: Path) -> None:
        path = tmp_path / "CHANGELOG.md"
        new_text, original = insert_changelog_entry(path, "## [v0.1.0]\nfoo\n")
        assert original == ""
        assert "# Changelog" in new_text
        assert "## [v0.1.0]" in new_text

    def test_insert_with_unreleased(self, tmp_path: Path) -> None:
        path = tmp_path / "CHANGELOG.md"
        path.write_text(
            "# Changelog\n\n## [Unreleased]\n\n_no changes_\n\n"
            "## [v0.1.0] — 2026-01-01\n\n- initial\n",
            encoding="utf-8",
        )
        entry = "## [v0.2.0] — 2026-05-09\n\n- new\n"
        new_text, _ = insert_changelog_entry(path, entry)

        # Unreleased preserved, new entry above 0.1.0.
        assert new_text.index("[Unreleased]") < new_text.index("[v0.2.0]")
        assert new_text.index("[v0.2.0]") < new_text.index("[v0.1.0]")

    def test_insert_no_unreleased(self, tmp_path: Path) -> None:
        path = tmp_path / "CHANGELOG.md"
        path.write_text(
            "# Changelog\n\n## [v0.1.0] — 2026-01-01\n\n- initial\n",
            encoding="utf-8",
        )
        entry = "## [v0.2.0] — 2026-05-09\n\n- new\n"
        new_text, _ = insert_changelog_entry(path, entry)
        assert new_text.index("[v0.2.0]") < new_text.index("[v0.1.0]")


# ---------------------------------------------------------------------------
# CLI behaviour: production-ready gating
# ---------------------------------------------------------------------------

PROPOSE_BIN = [sys.executable, "tools/propose_release.py"]


def _run_propose(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(
        PROPOSE_BIN + args,
        cwd=str(Path(__file__).resolve().parent.parent),
        capture_output=True, text=True,
        env={**os.environ, "PYTHONUTF8": "1"},
    )


class TestCli:
    def test_propose_blocks_when_not_ready(self, failing_audit_dir: Path,
                                           tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            '[project]\nversion = "0.1.0"\n', encoding="utf-8",
        )
        result = _run_propose(
            ["propose", str(failing_audit_dir), str(target),
             "--format", "json"],
            cwd=tmp_path,
        )
        assert result.returncode == 2, result.stderr
        out = json.loads(result.stdout)
        assert out["ok"] is False
        assert out["reason"] == "not_production_ready"
        assert "SEC-001" in out["blocking_findings"]

    def test_propose_emits_proposal_when_ready(self, audit_dir: Path,
                                               tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            '[project]\nversion = "0.4.2"\n', encoding="utf-8",
        )
        result = _run_propose(
            ["propose", str(audit_dir), str(target),
             "--format", "json", "--bump", "minor",
             "--today", "2026-05-09"],
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        out = json.loads(result.stdout)
        assert out["ok"] is True
        assert out["current_version"] == "0.4.2"
        assert out["next_version"] == "0.5.0"
        assert "## [v0.5.0]" in out["changelog_entry"]
        # Working tree must be untouched.
        assert not (target / "CHANGELOG.md").exists()

    def test_propose_force_overrides_gating(self, failing_audit_dir: Path,
                                            tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            '[project]\nversion = "0.1.0"\n', encoding="utf-8",
        )
        result = _run_propose(
            ["propose", str(failing_audit_dir), str(target),
             "--format", "json", "--force", "--today", "2026-05-09"],
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
