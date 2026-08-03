"""Tests for `eval_applicability.py diff` — the helper that reported 0 == 0.

The original hand-rolled version compared two applicability sets, found both
empty because the path was wrong, and reported them identical. The subcommand
exists so that comparison is written once and guarded once; these tests pin the
guard, and pin that a *legitimately* empty applicable set still gets an answer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.compare_guard import EmptyComparisonError
from tools.eval_applicability import (
    applicable_ids,
    diff_applicability,
    evaluate_catalog,
    main,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"


def _eval(**flags) -> dict:
    return {
        cid: {"applicable": bool(applicable), "reason": "match", "expression": "always"}
        for cid, applicable in flags.items()
    }


class TestDiffApplicability:
    def test_the_regression_two_empty_evaluations_are_refused(self):
        with pytest.raises(EmptyComparisonError):
            diff_applicability("old", {}, "new", {})

    def test_one_empty_evaluation_is_refused_and_named(self):
        with pytest.raises(EmptyComparisonError) as exc:
            diff_applicability("old", _eval(**{"ARCH-001": True}), "new", {})
        assert "new" in str(exc.value)

    def test_identical_evaluations_are_identical(self):
        left = _eval(**{"ARCH-001": True, "SEC-001": False})
        assert diff_applicability("old", left, "new", dict(left))["identical"] is True

    def test_a_check_added_to_the_catalogue_shows_as_evaluated_only_on_one_side(self):
        report = diff_applicability(
            "old",
            _eval(**{"ARCH-001": True}),
            "new",
            _eval(**{"ARCH-001": True, "SEC-001": True}),
        )
        assert report["evaluated"]["only_in_right"] == ["SEC-001"]
        assert report["identical"] is False

    def test_a_flipped_applicability_is_reported_separately_from_a_new_check(self):
        # These are different events with different fixes; a single
        # applicable-set diff would render them the same way.
        report = diff_applicability(
            "old", _eval(**{"ARCH-001": True}), "new", _eval(**{"ARCH-001": False})
        )
        assert report["evaluated"]["identical"] is True
        assert [c["check_id"] for c in report["changed_applicability"]] == ["ARCH-001"]
        assert report["identical"] is False

    def test_changed_entry_names_both_sides_by_label(self):
        report = diff_applicability(
            "run-a",
            _eval(**{"ARCH-001": True}),
            "run-b",
            _eval(**{"ARCH-001": False}),
        )
        changed = report["changed_applicability"][0]
        assert changed["run-a"]["applicable"] is True
        assert changed["run-b"]["applicable"] is False

    def test_a_profile_matching_nothing_is_a_result_not_an_error(self):
        # An empty *applicable* set is a real state; an empty *evaluated* set
        # is a broken parse. Only the second is refused.
        left = _eval(**{"ARCH-001": False, "SEC-001": False})
        report = diff_applicability("old", left, "new", dict(left))
        assert report["applicable"]["left_count"] == 0
        assert report["identical"] is True

    def test_allow_empty_opts_out_of_the_guard(self):
        report = diff_applicability("old", {}, "new", {}, allow_empty=True)
        assert report["identical"] is True


class TestApplicableIds:
    def test_only_applicable_ids_are_returned_sorted(self):
        ids = applicable_ids(
            _eval(**{"SEC-001": True, "ARCH-001": True, "CH-001": False})
        )
        assert ids == ["ARCH-001", "SEC-001"]


class TestDiffCli:
    def _saved_evaluation(self, tmp_path: Path, name: str) -> Path:
        profile = REPO_ROOT / "portfolio.example.yaml"
        pytest.importorskip("yaml")
        from tools.eval_applicability import _load_profile

        results = evaluate_catalog(_load_profile(profile, None), CHECKS_DIR)
        p = tmp_path / name
        p.write_text(json.dumps(results), encoding="utf-8")
        return p

    def test_identical_sides_exit_0(self, tmp_path: Path, capsys):
        a = self._saved_evaluation(tmp_path, "a.json")
        b = self._saved_evaluation(tmp_path, "b.json")
        assert main(["diff", str(a), str(b)]) == 0

    def test_a_difference_exits_1_so_it_can_gate(self, tmp_path: Path, capsys):
        a = self._saved_evaluation(tmp_path, "a.json")
        data = json.loads(a.read_text(encoding="utf-8"))
        data.pop(sorted(data)[0])
        b = tmp_path / "b.json"
        b.write_text(json.dumps(data), encoding="utf-8")
        assert main(["diff", str(a), str(b)]) == 1

    def test_an_empty_catalog_dir_exits_2_rather_than_reporting_identical(
        self, tmp_path: Path, capsys
    ):
        pytest.importorskip("yaml")
        empty = tmp_path / "empty-checks"
        empty.mkdir()
        profile = str(REPO_ROOT / "portfolio.example.yaml")
        rc = main(
            ["diff", profile, profile, "--checks-dir", str(empty), "--labels", "a,b"]
        )
        assert rc == 2
        assert "refusing to compare" in capsys.readouterr().err

    def test_identical_labels_are_rejected(self, tmp_path: Path, capsys):
        a = self._saved_evaluation(tmp_path, "a.json")
        assert main(["diff", str(a), str(a), "--labels", "same,same"]) == 2

    def test_default_labels_are_the_two_paths(self, tmp_path: Path, capsys):
        a = self._saved_evaluation(tmp_path, "a.json")
        b = self._saved_evaluation(tmp_path, "b.json")
        main(["diff", str(a), str(b)])
        out = json.loads(capsys.readouterr().out)
        assert out["evaluated"]["left_label"] == str(a)
