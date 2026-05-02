# -*- coding: utf-8 -*-
"""Tests for tools/parse_catalog.py — replaces inline awk/heredoc parsing."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.parse_catalog import (
    REQUIRED_FIELDS,
    category_counts,
    list_check_files,
    main,
    manifest_check,
    parse_catalog,
    severity_counts,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"


# ---------------------------------------------------------------------------
# Real-catalog regression
# ---------------------------------------------------------------------------

class TestRealCatalog:
    def test_count_matches_manifest(self):
        catalog = parse_catalog(CHECKS_DIR)
        assert len(catalog) == 68

    def test_all_required_fields_present(self):
        catalog = parse_catalog(CHECKS_DIR)
        for cid, fm in catalog.items():
            for f in REQUIRED_FIELDS:
                assert fm.get(f), f"{cid}: missing required field {f}"

    def test_manifest_consistent_with_catalog(self):
        report = manifest_check(CHECKS_DIR)
        assert report["consistent"] is True
        assert report["in_manifest_only"] == []
        assert report["in_catalog_only"] == []
        assert report["manifest_count"] == 68
        assert report["catalog_count"] == 68

    def test_category_distribution(self):
        catalog = parse_catalog(CHECKS_DIR)
        counts = category_counts(catalog)
        # Expected per SKILL.md table.
        assert counts == {
            "ARCH": 12,
            "CH": 8,
            "HITL": 5,
            "OBS": 6,
            "OPS": 3,
            "SCALE": 6,
            "SDK": 5,
            "SEC": 23,
        }

    def test_severity_distribution_known_set(self):
        catalog = parse_catalog(CHECKS_DIR)
        counts = severity_counts(catalog)
        # Severities must be a subset of the canonical 4.
        assert set(counts).issubset({"critical", "high", "medium", "low"})
        assert sum(counts.values()) == 68


# ---------------------------------------------------------------------------
# Hermetic fixtures
# ---------------------------------------------------------------------------

def _write_check(dir: Path, fm: str, body: str = "body") -> None:
    path = dir / f"{fm.split('id:')[1].split()[0].strip()}.md"
    path.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")


class TestHermetic:
    def test_two_checks_parse(self, tmp_path):
        _write_check(tmp_path,
            "id: TST-001\n"
            "title: \"Tiny check\"\n"
            "category: ARCH\n"
            "severity: medium\n"
            "applies_when: 'always'"
        )
        _write_check(tmp_path,
            "id: TST-002\n"
            "title: \"Other tiny check\"\n"
            "category: SEC\n"
            "severity: high\n"
            "applies_when: 'transport != \"stdio-only\"'"
        )
        catalog = parse_catalog(tmp_path)
        assert set(catalog) == {"TST-001", "TST-002"}
        assert catalog["TST-002"]["severity"] == "high"

    def test_duplicate_id_rejected(self, tmp_path):
        (tmp_path / "a.md").write_text(
            "---\nid: SAME-001\ntitle: \"a\"\ncategory: ARCH\nseverity: medium\napplies_when: 'always'\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "b.md").write_text(
            "---\nid: SAME-001\ntitle: \"b\"\ncategory: ARCH\nseverity: medium\napplies_when: 'always'\n---\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Duplicate check id"):
            parse_catalog(tmp_path)

    def test_missing_required_field_rejected(self, tmp_path):
        (tmp_path / "x.md").write_text(
            "---\nid: TST-099\ntitle: \"x\"\ncategory: ARCH\nseverity: medium\n---\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="missing required field"):
            parse_catalog(tmp_path)

    def test_manifest_check_detects_orphan_file(self, tmp_path):
        # Catalog has 1, manifest is empty
        _write_check(tmp_path,
            "id: ORPH-001\n"
            "title: \"Orphan\"\n"
            "category: ARCH\n"
            "severity: medium\n"
            "applies_when: 'always'"
        )
        (tmp_path / "MANIFEST.txt").write_text("", encoding="utf-8")
        report = manifest_check(tmp_path)
        assert report["consistent"] is False
        assert report["in_catalog_only"] == ["ORPH-001"]
        assert report["in_manifest_only"] == []

    def test_manifest_check_detects_missing_file(self, tmp_path):
        # Manifest references a check not on disk
        (tmp_path / "MANIFEST.txt").write_text(
            "GHOST-001\n", encoding="utf-8"
        )
        report = manifest_check(tmp_path)
        assert report["consistent"] is False
        assert report["in_manifest_only"] == ["GHOST-001"]

    def test_list_check_files_excludes_manifest(self, tmp_path):
        _write_check(tmp_path,
            "id: TST-010\n"
            "title: \"x\"\n"
            "category: ARCH\n"
            "severity: medium\n"
            "applies_when: 'always'"
        )
        (tmp_path / "MANIFEST.txt").write_text("TST-010\n", encoding="utf-8")
        files = list_check_files(tmp_path)
        # MANIFEST.txt is not a .md, so it isn't picked up.
        assert [p.name for p in files] == ["TST-010.md"]


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------

class TestCli:
    def test_json_format_to_stdout(self, tmp_path, capsys):
        _write_check(tmp_path,
            "id: CLI-001\n"
            "title: \"x\"\n"
            "category: ARCH\n"
            "severity: medium\n"
            "applies_when: 'always'"
        )
        rc = main(["--checks-dir", str(tmp_path), "--format", "json"])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "CLI-001" in data

    def test_json_format_to_file(self, tmp_path):
        _write_check(tmp_path,
            "id: FIL-001\n"
            "title: \"x\"\n"
            "category: ARCH\n"
            "severity: medium\n"
            "applies_when: 'always'"
        )
        out = tmp_path / "catalog.json"
        rc = main([
            "--checks-dir", str(tmp_path),
            "--format", "json",
            "--out", str(out),
        ])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "FIL-001" in data

    def test_manifest_check_consistent_returns_zero(self):
        rc = main(["--checks-dir", str(CHECKS_DIR), "--format", "manifest-check"])
        assert rc == 0

    def test_manifest_check_inconsistent_returns_one(self, tmp_path, capsys):
        # Catalog has one file, manifest is empty → inconsistent.
        _write_check(tmp_path,
            "id: INC-001\n"
            "title: \"x\"\n"
            "category: ARCH\n"
            "severity: medium\n"
            "applies_when: 'always'"
        )
        (tmp_path / "MANIFEST.txt").write_text("", encoding="utf-8")
        rc = main(["--checks-dir", str(tmp_path), "--format", "manifest-check"])
        assert rc == 1

    def test_invalid_dir_returns_two(self, tmp_path):
        rc = main(["--checks-dir", str(tmp_path / "nope"), "--format", "json"])
        assert rc == 2
