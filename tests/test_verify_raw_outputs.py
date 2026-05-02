# -*- coding: utf-8 -*-
"""Tests for tools/verify_raw_outputs.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.verify_raw_outputs import main, verify_raw_outputs


# ---------------------------------------------------------------------------
# Pure verification function
# ---------------------------------------------------------------------------

class TestVerify:
    def _write(self, dir: Path, name: str, content: str = "ok") -> Path:
        path = dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_all_satisfied(self, tmp_path):
        self._write(tmp_path, "ARCH-001.txt", "result")
        self._write(tmp_path, "SEC-021.txt", "result")
        report = verify_raw_outputs(tmp_path, ["ARCH-001", "SEC-021"])
        assert report["consistent"] is True
        assert report["satisfied"] == ["ARCH-001", "SEC-021"]
        assert report["missing"] == []
        assert report["empty"] == []
        assert report["incomplete_ids"] == []

    def test_missing_file(self, tmp_path):
        self._write(tmp_path, "ARCH-001.txt", "ok")
        report = verify_raw_outputs(tmp_path, ["ARCH-001", "MISSING-001"])
        assert report["consistent"] is False
        assert report["missing"] == ["MISSING-001"]
        assert report["incomplete_ids"] == ["MISSING-001"]

    def test_empty_file_below_threshold(self, tmp_path):
        # Silent-failure mode from the original audit: 0-token run writes
        # an empty placeholder file.
        self._write(tmp_path, "ARCH-001.txt", "")
        report = verify_raw_outputs(tmp_path, ["ARCH-001"], min_bytes=1)
        assert report["consistent"] is False
        assert report["empty"] == ["ARCH-001"]
        assert report["incomplete_ids"] == ["ARCH-001"]

    def test_min_bytes_strict(self, tmp_path):
        # File has 5 bytes but threshold is 10
        self._write(tmp_path, "ARCH-001.txt", "abcde")
        report = verify_raw_outputs(tmp_path, ["ARCH-001"], min_bytes=10)
        assert report["consistent"] is False
        assert report["empty"] == ["ARCH-001"]

    def test_mixed_outcomes(self, tmp_path):
        self._write(tmp_path, "ARCH-001.txt", "good")  # satisfied
        self._write(tmp_path, "SEC-021.txt", "")       # empty
        # ARCH-002 not written → missing
        report = verify_raw_outputs(
            tmp_path, ["ARCH-001", "ARCH-002", "SEC-021"]
        )
        assert report["satisfied"] == ["ARCH-001"]
        assert report["missing"] == ["ARCH-002"]
        assert report["empty"] == ["SEC-021"]
        assert report["incomplete_ids"] == ["ARCH-002", "SEC-021"]
        assert report["consistent"] is False

    def test_nonexistent_dir(self, tmp_path):
        report = verify_raw_outputs(
            tmp_path / "missing", ["ARCH-001"]
        )
        assert report["consistent"] is False
        assert "error" in report
        assert report["incomplete_ids"] == ["ARCH-001"]

    def test_custom_suffix(self, tmp_path):
        self._write(tmp_path, "ARCH-001.json", '{"x": 1}')
        report = verify_raw_outputs(
            tmp_path, ["ARCH-001"], suffix=".json"
        )
        assert report["consistent"] is True

    def test_empty_expected_list(self, tmp_path):
        report = verify_raw_outputs(tmp_path, [])
        assert report["consistent"] is True
        assert report["satisfied"] == []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCli:
    def _setup(self, tmp_path: Path, ids_present: list[str]) -> Path:
        raw = tmp_path / "raw"
        raw.mkdir()
        for cid in ids_present:
            (raw / f"{cid}.txt").write_text("data", encoding="utf-8")
        return raw

    def test_cli_all_satisfied_returns_zero(self, tmp_path, capsys):
        raw = self._setup(tmp_path, ["ARCH-001", "SEC-021"])
        rc = main([
            str(raw),
            "--expected-ids", "ARCH-001,SEC-021",
        ])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["consistent"] is True

    def test_cli_incomplete_returns_one(self, tmp_path, capsys):
        raw = self._setup(tmp_path, ["ARCH-001"])
        rc = main([
            str(raw),
            "--expected-ids", "ARCH-001,MISSING-001",
        ])
        assert rc == 1
        out = json.loads(capsys.readouterr().out)
        assert out["incomplete_ids"] == ["MISSING-001"]

    def test_cli_expected_ids_file(self, tmp_path):
        raw = self._setup(tmp_path, ["ARCH-001", "SEC-021"])
        ids_file = tmp_path / "expected.txt"
        ids_file.write_text(
            "# expected ids\nARCH-001\nSEC-021\n# trailing comment\n",
            encoding="utf-8",
        )
        rc = main([
            str(raw),
            "--expected-ids-file", str(ids_file),
        ])
        assert rc == 0

    def test_cli_writes_out_file(self, tmp_path):
        raw = self._setup(tmp_path, ["ARCH-001"])
        out_path = tmp_path / "report.json"
        rc = main([
            str(raw),
            "--expected-ids", "ARCH-001",
            "--out", str(out_path),
        ])
        assert rc == 0
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["consistent"] is True

    def test_cli_min_bytes_flag(self, tmp_path):
        raw = tmp_path / "raw"
        raw.mkdir()
        (raw / "ARCH-001.txt").write_text("xx", encoding="utf-8")
        # 2 bytes, threshold 10 → empty
        rc = main([
            str(raw),
            "--expected-ids", "ARCH-001",
            "--min-bytes", "10",
        ])
        assert rc == 1

    def test_cli_missing_ids_file_returns_two(self, tmp_path):
        raw = tmp_path / "raw"
        raw.mkdir()
        rc = main([
            str(raw),
            "--expected-ids-file", str(tmp_path / "nope.txt"),
        ])
        assert rc == 2
