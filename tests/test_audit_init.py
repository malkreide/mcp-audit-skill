# -*- coding: utf-8 -*-
"""Tests for tools/audit_init.py — run-id + audit-meta initialization."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools.audit_init import (
    _format_offset,
    build_initial_meta,
    hash_catalog,
    init_audit,
    main,
    make_run_id,
    resolve_output_dir,
)


# ---------------------------------------------------------------------------
# Run-ID format
# ---------------------------------------------------------------------------

class TestMakeRunId:
    def test_utc_uses_z_suffix(self):
        now = datetime(2026, 5, 2, 9, 12, 45, tzinfo=timezone.utc)
        assert make_run_id("srgssr-mcp", now) == "2026-05-02T091245-Z-srgssr-mcp"

    def test_positive_offset_uses_plus_hhmm(self):
        tz = timezone(timedelta(hours=2))  # CEST
        now = datetime(2026, 5, 2, 11, 12, 45, tzinfo=tz)
        assert make_run_id("srgssr-mcp", now) == "2026-05-02T111245-+0200-srgssr-mcp"

    def test_negative_offset_uses_minus_hhmm(self):
        tz = timezone(timedelta(hours=-5, minutes=-30))
        now = datetime(2026, 5, 2, 4, 12, 45, tzinfo=tz)
        assert make_run_id("srgssr-mcp", now) == "2026-05-02T041245--0530-srgssr-mcp"

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            make_run_id("x", datetime(2026, 5, 2))

    def test_invalid_server_name_rejected(self):
        with pytest.raises(ValueError, match="must match"):
            make_run_id("has spaces", datetime.now(timezone.utc))

    def test_server_name_with_digits_dashes_underscores_ok(self):
        now = datetime(2026, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        assert "valid-name_123" in make_run_id("valid-name_123", now)

    def test_empty_server_name_rejected(self):
        with pytest.raises(ValueError):
            make_run_id("", datetime.now(timezone.utc))


class TestFormatOffset:
    def test_utc(self):
        assert _format_offset(datetime(2026, 5, 2, tzinfo=timezone.utc)) == "Z"

    def test_zero_offset_named_zone(self):
        # explicit zero offset still renders as Z
        tz = timezone(timedelta(0), name="UTC")
        assert _format_offset(datetime(2026, 5, 2, tzinfo=tz)) == "Z"

    def test_naive_rejected(self):
        with pytest.raises(ValueError):
            _format_offset(datetime(2026, 5, 2))


# ---------------------------------------------------------------------------
# Collision avoidance
# ---------------------------------------------------------------------------

class TestResolveOutputDir:
    def test_first_run_no_suffix(self, tmp_path):
        now = datetime(2026, 5, 2, 9, 0, 0, tzinfo=timezone.utc)
        run_id, path = resolve_output_dir("srgssr-mcp", tmp_path, now=now)
        assert path.name == "2026-05-02T090000-Z-srgssr-mcp"

    def test_second_run_same_second_gets_suffix(self, tmp_path):
        now = datetime(2026, 5, 2, 9, 0, 0, tzinfo=timezone.utc)
        run_id, path1 = resolve_output_dir("srgssr-mcp", tmp_path, now=now)
        path1.mkdir()
        run_id_2, path2 = resolve_output_dir("srgssr-mcp", tmp_path, now=now)
        # Run-id is identical (same second); only directory suffix changes.
        assert run_id_2 == run_id
        assert path2.name.endswith("-2")

    def test_third_run_continues_suffix_chain(self, tmp_path):
        now = datetime(2026, 5, 2, 9, 0, 0, tzinfo=timezone.utc)
        for _ in range(3):
            _, p = resolve_output_dir("srgssr-mcp", tmp_path, now=now)
            p.mkdir()
        run_id_4, path4 = resolve_output_dir("srgssr-mcp", tmp_path, now=now)
        assert path4.name.endswith("-4")


# ---------------------------------------------------------------------------
# Catalog hashing
# ---------------------------------------------------------------------------

class TestHashCatalog:
    def test_deterministic(self, tmp_path):
        (tmp_path / "ARCH-001.md").write_text("a\n", encoding="utf-8")
        (tmp_path / "MANIFEST.txt").write_text("ARCH-001\n", encoding="utf-8")
        h1 = hash_catalog(tmp_path)
        h2 = hash_catalog(tmp_path)
        assert h1 == h2
        assert len(h1) == 64

    def test_changes_when_file_changes(self, tmp_path):
        (tmp_path / "ARCH-001.md").write_text("a\n", encoding="utf-8")
        h1 = hash_catalog(tmp_path)
        (tmp_path / "ARCH-001.md").write_text("a-modified\n", encoding="utf-8")
        h2 = hash_catalog(tmp_path)
        assert h1 != h2

    def test_changes_when_file_added(self, tmp_path):
        (tmp_path / "ARCH-001.md").write_text("a\n", encoding="utf-8")
        h1 = hash_catalog(tmp_path)
        (tmp_path / "ARCH-002.md").write_text("b\n", encoding="utf-8")
        h2 = hash_catalog(tmp_path)
        assert h1 != h2


# ---------------------------------------------------------------------------
# Initial meta
# ---------------------------------------------------------------------------

class TestBuildInitialMeta:
    def test_required_fields_set(self, tmp_path):
        now = datetime(2026, 5, 2, 9, 0, 0, tzinfo=timezone.utc)
        meta = build_initial_meta(
            server="srgssr-mcp",
            run_id="2026-05-02T090000-Z-srgssr-mcp",
            output_dir=tmp_path,
            now=now,
            skill_version="0.9.0",
        )
        am = meta["audit_meta"]
        assert am["server_name"] == "srgssr-mcp"
        assert am["started_at"] == "2026-05-02T09:00:00+00:00"
        assert am["timezone_offset"] == "Z"
        assert am["skill_version"] == "0.9.0"
        assert meta["agent_runs"] == []

    def test_catalog_hash_included_when_dir_exists(self, tmp_path):
        catalog = tmp_path / "checks"
        catalog.mkdir()
        (catalog / "X-001.md").write_text("body", encoding="utf-8")
        now = datetime(2026, 5, 2, tzinfo=timezone.utc)
        meta = build_initial_meta(
            server="x",
            run_id="2026-05-02T000000-Z-x",
            output_dir=tmp_path,
            now=now,
            skill_version="0.9",
            catalog_dir=catalog,
        )
        assert "catalog_hash" in meta["audit_meta"]
        assert len(meta["audit_meta"]["catalog_hash"]) == 64


# ---------------------------------------------------------------------------
# init_audit end-to-end
# ---------------------------------------------------------------------------

class TestInitAudit:
    def test_creates_dir_and_meta(self, tmp_path):
        now = datetime(2026, 5, 2, 9, 0, 0, tzinfo=timezone.utc)
        result = init_audit(
            server="srgssr-mcp",
            base_dir=tmp_path,
            skill_version="0.9.0",
            now=now,
        )
        out_dir = Path(result["output_dir"])
        assert out_dir.is_dir()
        meta_path = out_dir / "audit-meta.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["audit_meta"]["server_name"] == "srgssr-mcp"

    def test_collision_creates_suffixed_dir(self, tmp_path):
        now = datetime(2026, 5, 2, 9, 0, 0, tzinfo=timezone.utc)
        r1 = init_audit(server="x", base_dir=tmp_path, now=now)
        r2 = init_audit(server="x", base_dir=tmp_path, now=now)
        assert r1["output_dir"] != r2["output_dir"]
        assert r2["output_dir"].endswith("-2")
        # But the run_id (logical identifier) stays the same.
        assert r1["run_id"] == r2["run_id"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCli:
    def test_make_run_id_returns_zero(self, capsys):
        rc = main(["make-run-id", "srgssr-mcp", "--now", "2026-05-02T09:00:00+00:00"])
        assert rc == 0
        assert capsys.readouterr().out.strip() == "2026-05-02T090000-Z-srgssr-mcp"

    def test_invalid_server_name_returns_two(self):
        rc = main(["make-run-id", "has spaces"])
        assert rc == 2

    def test_init_creates_dir_and_emits_json(self, tmp_path, capsys):
        rc = main([
            "init", "srgssr-mcp",
            "--base-dir", str(tmp_path),
            "--skill-version", "0.9",
            "--now", "2026-05-02T09:00:00+00:00",
        ])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["run_id"] == "2026-05-02T090000-Z-srgssr-mcp"
        assert Path(out["output_dir"]).is_dir()

    def test_init_naive_datetime_treated_as_utc(self, tmp_path, capsys):
        # Naive datetime input is upgraded to UTC for predictability.
        rc = main([
            "init", "x",
            "--base-dir", str(tmp_path),
            "--now", "2026-05-02T09:00:00",
        ])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert "Z" in out["run_id"]
