# -*- coding: utf-8 -*-
"""Tests for tools/tracker_sync.py — focus on the CSV backend (zero-deps)
and the backend resolver. Notion is exercised only via constructor / env
plumbing; real API calls are not mocked here."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from tools.tracker_sync import (
    CANONICAL_FIELDS,
    CsvBackend,
    NotionBackend,
    TrackerError,
    TrackerRecord,
    get_backend,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# CsvBackend
# ---------------------------------------------------------------------------

class TestCsvBackend:
    def test_creates_file_with_header(self, tmp_path: Path) -> None:
        path = tmp_path / "tracker.csv"
        backend = CsvBackend(path)
        assert backend.list_all() == []
        text = path.read_text(encoding="utf-8")
        for f in CANONICAL_FIELDS:
            assert f in text

    def test_insert_then_read(self, tmp_path: Path) -> None:
        backend = CsvBackend(tmp_path / "t.csv")
        backend.update("server-a", {"audit_status": "In Audit", "findings": 3})

        record = backend.get("server-a")
        assert record is not None
        assert record.audit_status == "In Audit"
        assert record.findings == 3
        assert record.server_name == "server-a"

    def test_update_merges_partial(self, tmp_path: Path) -> None:
        backend = CsvBackend(tmp_path / "t.csv")
        backend.update("srv", {"audit_status": "In Audit", "findings": 5})
        backend.update("srv", {"production_ready": True,
                                "released_version": "1.0.0"})

        record = backend.get("srv")
        assert record is not None
        assert record.audit_status == "In Audit"  # preserved
        assert record.findings == 5  # preserved
        assert record.production_ready is True
        assert record.released_version == "1.0.0"

    def test_unknown_field_raises(self, tmp_path: Path) -> None:
        backend = CsvBackend(tmp_path / "t.csv")
        with pytest.raises(TrackerError, match="Unknown field"):
            backend.update("srv", {"bogus": "x"})

    def test_get_missing_returns_none(self, tmp_path: Path) -> None:
        backend = CsvBackend(tmp_path / "t.csv")
        assert backend.get("nope") is None

    def test_list_all_returns_all_servers(self, tmp_path: Path) -> None:
        backend = CsvBackend(tmp_path / "t.csv")
        backend.update("a", {"findings": 1})
        backend.update("b", {"findings": 2})
        backend.update("c", {"findings": 0, "production_ready": True})

        records = backend.list_all()
        names = sorted(r.server_name for r in records)
        assert names == ["a", "b", "c"]

    def test_round_trip_production_ready_bool(self, tmp_path: Path) -> None:
        backend = CsvBackend(tmp_path / "t.csv")
        backend.update("a", {"production_ready": True})
        backend.update("b", {"production_ready": False})

        assert backend.get("a").production_ready is True
        assert backend.get("b").production_ready is False


# ---------------------------------------------------------------------------
# Backend resolver
# ---------------------------------------------------------------------------

class TestGetBackend:
    def test_default_is_csv(self, monkeypatch: pytest.MonkeyPatch,
                            tmp_path: Path) -> None:
        monkeypatch.delenv("MCP_AUDIT_TRACKER_BACKEND", raising=False)
        monkeypatch.delenv("MCP_AUDIT_TRACKER_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        backend = get_backend(None)
        assert backend.name == "csv"

    def test_explicit_csv_with_path(self, tmp_path: Path) -> None:
        backend = get_backend("csv", csv_path=str(tmp_path / "x.csv"))
        assert backend.name == "csv"
        assert isinstance(backend, CsvBackend)
        assert backend.path == tmp_path / "x.csv"

    def test_csv_path_from_env(self, monkeypatch: pytest.MonkeyPatch,
                               tmp_path: Path) -> None:
        target = tmp_path / "env.csv"
        monkeypatch.setenv("MCP_AUDIT_TRACKER_PATH", str(target))
        backend = get_backend("csv")
        assert isinstance(backend, CsvBackend)
        assert backend.path == target

    def test_notion_requires_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        with pytest.raises(TrackerError, match="NOTION_TOKEN"):
            get_backend("notion")

    def test_notion_constructs_with_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NOTION_TOKEN", "secret_xxx")
        backend = get_backend("notion")
        assert isinstance(backend, NotionBackend)
        assert backend.name == "notion"
        # Default DB id falls back when env not set.
        assert backend.db_id

    def test_unknown_backend_raises(self) -> None:
        with pytest.raises(TrackerError, match="Unknown tracker backend"):
            get_backend("airtable")


# ---------------------------------------------------------------------------
# TrackerRecord
# ---------------------------------------------------------------------------

class TestTrackerRecord:
    def test_to_dict_nonnull_drops_none(self) -> None:
        record = TrackerRecord(
            server_name="a",
            audit_status="In Audit",
            findings=None,
            production_ready=True,
        )
        d = record.to_dict_nonnull()
        assert "findings" not in d
        assert d["server_name"] == "a"
        assert d["audit_status"] == "In Audit"
        assert d["production_ready"] is True


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, "PYTHONUTF8": "1"}
    if env:
        full_env.update(env)
    return subprocess.run(
        ["python3", "tools/tracker_sync.py"] + args,
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, env=full_env,
    )


class TestCli:
    def test_update_set_writes_csv(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "t.csv"
        result = _run([
            "--backend", "csv", "--csv-path", str(csv_path),
            "update", "my-mcp",
            "--set", "audit_status=Released",
            "--set", "findings=0",
            "--set", "production_ready=true",
            "--set", "released_version=1.2.0",
        ])
        assert result.returncode == 0, result.stderr
        out = json.loads(result.stdout)
        assert out["ok"] is True
        assert out["backend"] == "csv"
        assert out["updated"]["released_version"] == "1.2.0"

        # Direct read-back proves persistence.
        backend = CsvBackend(csv_path)
        record = backend.get("my-mcp")
        assert record.released_version == "1.2.0"
        assert record.production_ready is True

    def test_update_from_summary(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "t.csv"
        summary_path = tmp_path / "summary.json"
        summary_path.write_text(json.dumps({
            "audit_meta": {"run_id": "2026-05-09T120000-Z-srv",
                           "started_at": "2026-05-09T12:00:00Z"},
            "findings": {"expected_count": 2},
            "production_ready": False,
        }), encoding="utf-8")

        result = _run([
            "--backend", "csv", "--csv-path", str(csv_path),
            "update", "srv", "--from-summary", str(summary_path),
        ])
        assert result.returncode == 0, result.stderr

        backend = CsvBackend(csv_path)
        record = backend.get("srv")
        assert record.findings == 2
        assert record.production_ready is False
        assert record.last_audit_run == "2026-05-09T120000-Z-srv"
        assert record.last_audit_at == "2026-05-09"

    def test_get_missing_exits_2(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "t.csv"
        result = _run([
            "--backend", "csv", "--csv-path", str(csv_path),
            "get", "ghost",
        ])
        assert result.returncode == 2

    def test_list_empty(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "t.csv"
        result = _run([
            "--backend", "csv", "--csv-path", str(csv_path),
            "list",
        ])
        assert result.returncode == 0
        out = json.loads(result.stdout)
        assert out["count"] == 0
        assert out["records"] == []

    def test_unknown_field_in_set_fails(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "t.csv"
        result = _run([
            "--backend", "csv", "--csv-path", str(csv_path),
            "update", "srv", "--set", "bogus_field=x",
        ])
        assert result.returncode == 1
        assert "Unknown field" in result.stderr
