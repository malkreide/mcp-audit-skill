# -*- coding: utf-8 -*-
"""Tests for tools/agent_run_log.py — Task-agent run logging."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.agent_run_log import (
    _classify_run,
    append_run,
    load_meta,
    main,
    save_meta,
    summarise,
)


# ---------------------------------------------------------------------------
# Classification logic — locks in the failure-mode taxonomy
# ---------------------------------------------------------------------------

class TestClassifyRun:
    def test_ok_when_tokens_and_no_incomplete(self):
        assert _classify_run(tokens=10000, incomplete_ids=[]) == "ok"

    def test_empty_when_zero_tokens(self):
        # The exact failure mode from issue #12.
        assert _classify_run(tokens=0, incomplete_ids=[]) == "empty"

    def test_empty_takes_precedence_over_incomplete(self):
        # 0 tokens AND missing IDs → still classified as empty
        assert _classify_run(tokens=0, incomplete_ids=["X-1"]) == "empty"

    def test_incomplete_when_tokens_but_missing(self):
        assert _classify_run(tokens=5000, incomplete_ids=["X-1"]) == "incomplete"


# ---------------------------------------------------------------------------
# append_run — fixture-driven scenarios
# ---------------------------------------------------------------------------

class TestAppendRun:
    def _setup_raw(self, tmp_path: Path, present: list[str]) -> Path:
        raw = tmp_path / "raw"
        raw.mkdir()
        for cid in present:
            (raw / f"{cid}.txt").write_text("ok", encoding="utf-8")
        return raw

    def test_ok_run(self, tmp_path):
        raw = self._setup_raw(tmp_path, ["ARCH-001", "SEC-021"])
        meta = {"audit_meta": {}, "agent_runs": []}
        entry = append_run(
            meta,
            tool_uses=44, tokens=85100, duration_seconds=372.3,
            expected_ids=["ARCH-001", "SEC-021"],
            raw_dir=raw,
        )
        assert entry["status"] == "ok"
        assert entry["satisfied_ids"] == ["ARCH-001", "SEC-021"]
        assert entry["incomplete_ids"] == []
        assert meta["agent_runs"][0] is entry

    def test_empty_run_zero_tokens(self, tmp_path):
        # The bug from issue #12: 0 tokens, no files written.
        raw = self._setup_raw(tmp_path, [])
        meta = {"audit_meta": {}, "agent_runs": []}
        entry = append_run(
            meta,
            tool_uses=68, tokens=0, duration_seconds=140,
            expected_ids=["ARCH-001"],
            raw_dir=raw,
        )
        assert entry["status"] == "empty"
        assert entry["incomplete_ids"] == ["ARCH-001"]

    def test_incomplete_partial_coverage(self, tmp_path):
        raw = self._setup_raw(tmp_path, ["ARCH-001"])
        meta = {"audit_meta": {}, "agent_runs": []}
        entry = append_run(
            meta,
            tool_uses=20, tokens=30000, duration_seconds=90,
            expected_ids=["ARCH-001", "SEC-021", "OPS-001"],
            raw_dir=raw,
        )
        assert entry["status"] == "incomplete"
        assert entry["satisfied_ids"] == ["ARCH-001"]
        assert sorted(entry["incomplete_ids"]) == ["OPS-001", "SEC-021"]

    def test_run_index_increments(self, tmp_path):
        raw = self._setup_raw(tmp_path, ["X-1"])
        meta = {"audit_meta": {}, "agent_runs": []}
        e1 = append_run(meta, tool_uses=1, tokens=1, duration_seconds=1,
                        expected_ids=["X-1"], raw_dir=raw)
        e2 = append_run(meta, tool_uses=1, tokens=1, duration_seconds=1,
                        expected_ids=["X-1"], raw_dir=raw)
        assert e1["run_index"] == 0
        assert e2["run_index"] == 1

    def test_retry_link_recorded(self, tmp_path):
        raw = self._setup_raw(tmp_path, ["X-1"])
        meta = {"audit_meta": {}, "agent_runs": []}
        append_run(meta, tool_uses=1, tokens=0, duration_seconds=1,
                   expected_ids=["X-1"], raw_dir=raw)
        retry = append_run(
            meta, tool_uses=2, tokens=5000, duration_seconds=10,
            expected_ids=["X-1"], raw_dir=raw,
            retry_of_run_index=0,
        )
        assert retry["retry_of_run_index"] == 0

    def test_started_at_iso_format(self, tmp_path):
        raw = self._setup_raw(tmp_path, ["X-1"])
        meta = {"audit_meta": {}, "agent_runs": []}
        fixed = datetime(2026, 5, 2, 7, 15, 0, tzinfo=timezone.utc)
        entry = append_run(
            meta, tool_uses=1, tokens=1, duration_seconds=1,
            expected_ids=["X-1"], raw_dir=raw, started_at=fixed,
        )
        assert entry["started_at"] == "2026-05-02T07:15:00+00:00"


# ---------------------------------------------------------------------------
# Persistence + summarise
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_load_missing_file_returns_empty_skeleton(self, tmp_path):
        meta = load_meta(tmp_path / "audit-meta.json")
        assert meta == {"audit_meta": {}, "agent_runs": []}

    def test_save_then_load_round_trip(self, tmp_path):
        path = tmp_path / "audit-meta.json"
        meta = {"audit_meta": {"server_name": "x"}, "agent_runs": [{"a": 1}]}
        save_meta(path, meta)
        loaded = load_meta(path)
        assert loaded == meta

    def test_load_rejects_non_object(self, tmp_path):
        path = tmp_path / "audit-meta.json"
        path.write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="top level must be an object"):
            load_meta(path)


class TestSummarise:
    def test_no_runs(self):
        assert summarise({"audit_meta": {}, "agent_runs": []})["status"] == "no-runs"

    def test_single_ok_run(self, tmp_path):
        raw = tmp_path / "raw"
        raw.mkdir()
        (raw / "X-1.txt").write_text("ok", encoding="utf-8")
        meta = {"audit_meta": {}, "agent_runs": []}
        append_run(meta, tool_uses=10, tokens=5000, duration_seconds=30,
                   expected_ids=["X-1"], raw_dir=raw)
        s = summarise(meta)
        assert s["overall_status"] == "ok"
        assert s["had_retries"] is False
        assert s["expected_unique_ids"] == 1

    def test_retry_completes_coverage(self, tmp_path):
        raw = tmp_path / "raw"
        raw.mkdir()
        meta = {"audit_meta": {}, "agent_runs": []}
        # First run: empty failure
        append_run(meta, tool_uses=10, tokens=0, duration_seconds=30,
                   expected_ids=["X-1"], raw_dir=raw)
        # Now Task-agent retry writes the missing file
        (raw / "X-1.txt").write_text("ok", encoding="utf-8")
        append_run(meta, tool_uses=5, tokens=8000, duration_seconds=20,
                   expected_ids=["X-1"], raw_dir=raw, retry_of_run_index=0)
        s = summarise(meta)
        assert s["overall_status"] == "ok"
        assert s["had_retries"] is True
        assert s["runs"] == 2

    def test_aggregate_arithmetic(self, tmp_path):
        raw = tmp_path / "raw"
        raw.mkdir()
        (raw / "X-1.txt").write_text("ok", encoding="utf-8")
        meta = {"audit_meta": {}, "agent_runs": []}
        append_run(meta, tool_uses=10, tokens=1000, duration_seconds=5,
                   expected_ids=["X-1"], raw_dir=raw)
        append_run(meta, tool_uses=20, tokens=2000, duration_seconds=15,
                   expected_ids=["X-1"], raw_dir=raw)
        s = summarise(meta)
        assert s["total_tokens"] == 3000
        assert s["total_tool_uses"] == 30
        assert s["total_duration_seconds"] == 20.0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCli:
    def _setup(self, tmp_path: Path) -> tuple[Path, Path]:
        raw = tmp_path / "raw"
        raw.mkdir()
        meta = tmp_path / "audit-meta.json"
        return raw, meta

    def test_cli_log_ok_returns_zero(self, tmp_path):
        raw, meta = self._setup(tmp_path)
        (raw / "X-1.txt").write_text("ok", encoding="utf-8")
        rc = main([
            "log",
            "--meta-path", str(meta),
            "--tool-uses", "10",
            "--tokens", "5000",
            "--duration", "30",
            "--expected", "X-1",
            "--raw-dir", str(raw),
        ])
        assert rc == 0
        data = json.loads(meta.read_text(encoding="utf-8"))
        assert data["agent_runs"][0]["status"] == "ok"

    def test_cli_log_empty_returns_one(self, tmp_path):
        raw, meta = self._setup(tmp_path)
        # No files written, 0 tokens → empty status
        rc = main([
            "log",
            "--meta-path", str(meta),
            "--tool-uses", "68",
            "--tokens", "0",
            "--duration", "140",
            "--expected", "X-1",
            "--raw-dir", str(raw),
        ])
        assert rc == 1
        data = json.loads(meta.read_text(encoding="utf-8"))
        assert data["agent_runs"][0]["status"] == "empty"

    def test_cli_log_appends_not_overwrites(self, tmp_path):
        raw, meta = self._setup(tmp_path)
        (raw / "X-1.txt").write_text("ok", encoding="utf-8")
        for _ in range(3):
            main([
                "log",
                "--meta-path", str(meta),
                "--tool-uses", "1", "--tokens", "1", "--duration", "1",
                "--expected", "X-1", "--raw-dir", str(raw),
            ])
        data = json.loads(meta.read_text(encoding="utf-8"))
        assert len(data["agent_runs"]) == 3
        assert [r["run_index"] for r in data["agent_runs"]] == [0, 1, 2]

    def test_cli_log_with_retry_of(self, tmp_path):
        raw, meta = self._setup(tmp_path)
        (raw / "X-1.txt").write_text("ok", encoding="utf-8")
        main([
            "log", "--meta-path", str(meta),
            "--tool-uses", "1", "--tokens", "1", "--duration", "1",
            "--expected", "X-1", "--raw-dir", str(raw),
        ])
        main([
            "log", "--meta-path", str(meta),
            "--tool-uses", "1", "--tokens", "1", "--duration", "1",
            "--expected", "X-1", "--raw-dir", str(raw),
            "--retry-of", "0",
        ])
        data = json.loads(meta.read_text(encoding="utf-8"))
        assert data["agent_runs"][1]["retry_of_run_index"] == 0

    def test_cli_summary(self, tmp_path):
        raw, meta = self._setup(tmp_path)
        (raw / "X-1.txt").write_text("ok", encoding="utf-8")
        main([
            "log", "--meta-path", str(meta),
            "--tool-uses", "1", "--tokens", "1", "--duration", "1",
            "--expected", "X-1", "--raw-dir", str(raw),
        ])
        rc = main(["summary", "--meta-path", str(meta)])
        assert rc == 0

    def test_cli_summary_missing_file_returns_two(self, tmp_path):
        rc = main(["summary", "--meta-path", str(tmp_path / "nope.json")])
        assert rc == 2
