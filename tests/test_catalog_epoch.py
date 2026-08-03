"""Tests for catalog epochs — when a trend line may be drawn, and when not.

The failure being prevented is a report that writes «30/4/2 → x/y/z» across
two runs measured with different catalogues. The counts are real; the arrow
between them is not. These tests pin the refusal, and pin that the refusal is
*visible* — a broken trend that renders as a missing section is the same
silence in different clothes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.aggregate_results import (
    EmptyComparisonError,
    compare_catalog_epoch,
    main,
)
from tools.build_report import render_trend


def _summary(catalog_hash: str, n: int, **by_status: int) -> dict:
    statuses = {"pass": 0, "fail": 0, "partial": 0, "not_verified": 0, "todo": 0}
    statuses.update(by_status)
    return {
        "audit_meta": {
            "run_id": f"run-{catalog_hash[:4]}",
            "catalog_hash": catalog_hash,
        },
        "totals": {"checks_evaluated": n, "by_status": statuses},
    }


class TestCompareCatalogEpoch:
    def test_same_hash_is_comparable(self):
        epoch = compare_catalog_epoch(
            _summary("a" * 64, 54, **{"pass": 34}),
            _summary("a" * 64, 54, **{"pass": 30}),
        )
        assert epoch["comparable"] is True
        assert epoch["delta_by_status"]["pass"] == 4

    def test_changed_hash_breaks_the_trend(self):
        """The real case: 36 checks against 54, one catalogue apart."""
        epoch = compare_catalog_epoch(
            _summary("b" * 64, 54, **{"pass": 30, "fail": 4, "partial": 2}),
            _summary("a" * 64, 36, **{"pass": 30, "fail": 4, "partial": 2}),
        )
        assert epoch["comparable"] is False
        assert "36" in epoch["reason"] and "54" in epoch["reason"]
        # Identical status counts must NOT be reported as "no change" — they
        # were counted over different catalogues.
        assert "delta_by_status" not in epoch

    def test_missing_current_hash_is_not_treated_as_unchanged(self):
        epoch = compare_catalog_epoch(_summary("", 54), _summary("a" * 64, 54))
        assert epoch["comparable"] is False
        assert "unknown is not the same as unchanged" in epoch["reason"]

    def test_missing_previous_hash_is_not_treated_as_unchanged(self):
        epoch = compare_catalog_epoch(_summary("a" * 64, 54), _summary("", 54))
        assert epoch["comparable"] is False

    def test_both_hashes_missing_is_still_a_refusal(self):
        epoch = compare_catalog_epoch(_summary("", 54), _summary("", 54))
        assert epoch["comparable"] is False

    def test_previous_run_with_zero_checks_is_not_a_baseline(self):
        with pytest.raises(EmptyComparisonError):
            compare_catalog_epoch(_summary("a" * 64, 54), _summary("a" * 64, 0))

    def test_empty_baseline_can_be_opted_into(self):
        epoch = compare_catalog_epoch(
            _summary("a" * 64, 54), _summary("a" * 64, 0), allow_empty=True
        )
        assert epoch["comparable"] is True

    def test_both_epochs_are_recorded_for_the_reader(self):
        epoch = compare_catalog_epoch(_summary("b" * 64, 54), _summary("a" * 64, 36))
        assert epoch["previous_checks_evaluated"] == 36
        assert epoch["checks_evaluated"] == 54
        assert epoch["previous_catalog_hash"].startswith("a")
        assert epoch["catalog_hash"].startswith("b")


class TestRenderTrend:
    def test_broken_epoch_prints_no_status_arrow(self):
        summary = _summary("b" * 64, 54, **{"pass": 30, "fail": 4, "partial": 2})
        summary["catalog_epoch"] = compare_catalog_epoch(
            summary, _summary("a" * 64, 36, **{"pass": 30, "fail": 4, "partial": 2})
        )
        out = render_trend(summary)
        assert "Trendlinie gebrochen" in out
        assert "→" not in out.split("Trendlinie gebrochen")[0]
        # No per-status comparison table when the epochs differ.
        assert "| bestanden |" not in out

    def test_broken_epoch_still_names_both_catalog_states(self):
        summary = _summary("b" * 64, 54)
        summary["catalog_epoch"] = compare_catalog_epoch(
            summary, _summary("a" * 64, 36)
        )
        out = render_trend(summary)
        assert "36" in out and "54" in out
        assert "aaaaaaaaaaaa" in out and "bbbbbbbbbbbb" in out

    def test_comparable_epoch_prints_the_delta_table(self):
        summary = _summary("a" * 64, 54, **{"pass": 34})
        summary["catalog_epoch"] = compare_catalog_epoch(
            summary, _summary("a" * 64, 54, **{"pass": 30})
        )
        out = render_trend(summary)
        assert "| bestanden | 30 | 34 | +4 |" in out

    def test_no_epoch_block_renders_nothing(self):
        assert render_trend(_summary("a" * 64, 54)) == ""


class TestAggregateCli:
    def _results(self, tmp_path: Path) -> Path:
        p = tmp_path / "verification-results.json"
        p.write_text(
            json.dumps(
                {
                    "audit_meta": {"server_name": "demo", "run_id": "now"},
                    "results": {
                        "ARCH-001": {
                            "status": "pass",
                            "category": "ARCH",
                            "severity": "medium",
                            # Ein `pass` ohne Beobachtung kommt seit
                            # `check_evidence_requirement` nicht mehr durch das
                            # Gate — und soll es nicht. Die Fixture traegt
                            # deshalb echte Belege, statt das Gate zu umgehen.
                            "evidence": [
                                "src/server.py:12 — tool decorator with name=…",
                                "tests/test_tools.py:40 — asserts the same name",
                            ],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        return p

    def _catalog(self, tmp_path: Path, name: str, files: list[str]) -> Path:
        d = tmp_path / name
        d.mkdir()
        repo_checks = Path(__file__).resolve().parent.parent / "checks"
        for f in files:
            (d / f).write_text(
                (repo_checks / f).read_text(encoding="utf-8"), encoding="utf-8"
            )
        return d

    def test_checks_dir_pins_the_live_catalog_hash(self, tmp_path: Path):
        results = self._results(tmp_path)
        catalog = self._catalog(tmp_path, "cat", ["ARCH-001.md"])
        out = tmp_path / "summary.json"
        assert (
            main(
                [
                    "aggregate",
                    str(results),
                    "--checks-dir",
                    str(catalog),
                    "--out",
                    str(out),
                ]
            )
            == 0
        )
        summary = json.loads(out.read_text(encoding="utf-8"))
        assert len(summary["audit_meta"]["catalog_hash"]) == 64

    def test_previous_run_dir_is_accepted_as_well_as_a_file(self, tmp_path: Path):
        results = self._results(tmp_path)
        catalog = self._catalog(tmp_path, "cat", ["ARCH-001.md"])
        prev_dir = tmp_path / "prev"
        prev_dir.mkdir()
        assert (
            main(
                [
                    "aggregate",
                    str(results),
                    "--checks-dir",
                    str(catalog),
                    "--out",
                    str(prev_dir / "summary.json"),
                ]
            )
            == 0
        )
        out = tmp_path / "summary.json"
        assert (
            main(
                [
                    "aggregate",
                    str(results),
                    "--checks-dir",
                    str(catalog),
                    "--previous",
                    str(prev_dir),
                    "--out",
                    str(out),
                ]
            )
            == 0
        )
        epoch = json.loads(out.read_text(encoding="utf-8"))["catalog_epoch"]
        assert epoch["comparable"] is True

    def test_a_grown_catalog_breaks_the_epoch(self, tmp_path: Path):
        results = self._results(tmp_path)
        small = self._catalog(tmp_path, "small", ["ARCH-001.md"])
        big = self._catalog(tmp_path, "big", ["ARCH-001.md", "SEC-001.md"])
        prev = tmp_path / "prev.json"
        assert (
            main(
                [
                    "aggregate",
                    str(results),
                    "--checks-dir",
                    str(small),
                    "--out",
                    str(prev),
                ]
            )
            == 0
        )
        out = tmp_path / "summary.json"
        assert (
            main(
                [
                    "aggregate",
                    str(results),
                    "--checks-dir",
                    str(big),
                    "--previous",
                    str(prev),
                    "--out",
                    str(out),
                ]
            )
            == 0
        )
        epoch = json.loads(out.read_text(encoding="utf-8"))["catalog_epoch"]
        assert epoch["comparable"] is False

    def test_missing_previous_summary_is_a_usage_error(self, tmp_path: Path):
        results = self._results(tmp_path)
        assert (
            main(["aggregate", str(results), "--previous", str(tmp_path / "nope.json")])
            == 2
        )
