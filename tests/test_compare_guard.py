"""Tests for tools/compare_guard.py — the refusal to compare nothing.

The behaviour under test is a negative one: the guard's job is to *not*
return an answer. That makes it exactly the kind of code that survives a
refactor with its meaning inverted — `if not items: return identical` reads
almost the same as `if not items: raise` and passes any test that only
checks the happy path. So the empty cases are asserted first and hardest.
"""

from __future__ import annotations

import pytest

from tools.compare_guard import EmptyComparisonError, diff_sets, require_non_empty


class TestRequireNonEmpty:
    def test_non_empty_passes_through_unchanged(self):
        items = ["ARCH-001", "SEC-002"]
        assert require_non_empty("catalogue", items) is items

    @pytest.mark.parametrize("empty", [[], set(), {}, ""])
    def test_every_empty_container_raises(self, empty):
        with pytest.raises(EmptyComparisonError):
            require_non_empty("catalogue", empty)

    def test_message_names_the_side(self):
        with pytest.raises(EmptyComparisonError) as exc:
            require_non_empty("the previous run (2026-05-01)", [])
        assert "the previous run (2026-05-01)" in str(exc.value)
        assert exc.value.label == "the previous run (2026-05-01)"

    def test_hint_is_appended_when_given(self):
        with pytest.raises(EmptyComparisonError) as exc:
            require_non_empty("catalogue", [], hint="Check --checks-dir.")
        assert "Check --checks-dir." in str(exc.value)

    def test_allow_empty_is_the_only_way_through(self):
        assert require_non_empty("catalogue", [], allow_empty=True) == []


class TestDiffSets:
    def test_the_regression_two_empty_sides_are_not_identical(self):
        """The exact shape of the original bug: 0 == 0 reported as identical."""
        with pytest.raises(EmptyComparisonError):
            diff_sets("run-a", [], "run-b", [])

    def test_one_empty_side_also_raises(self):
        with pytest.raises(EmptyComparisonError) as exc:
            diff_sets("run-a", ["ARCH-001"], "run-b", [])
        assert "run-b" in str(exc.value)

    def test_identical_sides_report_identical_with_counts(self):
        report = diff_sets("a", ["X-1", "X-2"], "b", ["X-2", "X-1"])
        assert report["identical"] is True
        assert report["left_count"] == report["right_count"] == 2
        assert report["common"] == ["X-1", "X-2"]

    def test_differences_are_attributed_to_the_right_side(self):
        report = diff_sets("a", ["X-1", "X-2"], "b", ["X-2", "X-3"])
        assert report["identical"] is False
        assert report["only_in_left"] == ["X-1"]
        assert report["only_in_right"] == ["X-3"]
        assert report["common"] == ["X-2"]

    def test_counts_are_reported_so_the_verdict_can_be_checked(self):
        # A reader must be able to see that the comparison had material to
        # work with; the verdict alone cannot distinguish "matched" from
        # "matched nothing".
        report = diff_sets("a", ["X-1"], "b", ["X-1"])
        assert report["left_count"] == 1
        assert report["right_count"] == 1

    def test_allow_empty_opt_in_returns_a_verdict(self):
        report = diff_sets("a", [], "b", [], allow_empty=True)
        assert report["identical"] is True
        assert report["left_count"] == 0
