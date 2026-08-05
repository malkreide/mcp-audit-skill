"""Tests for the description-drift issue renderer.

The test that matters is `test_a_failed_fetch_does_not_read_as_all_clear`. The
first version of this escalation had two states — body written or not — and the
four no-body cases would all have closed an open issue on the strength of a
comparison that never happened. That is the bug the third state exists for; if
any test here is ever dropped, it should not be that one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.render_description_issue import (
    DRIFT,
    OK,
    UNCHECKED,
    classify,
    load_result,
    main,
    render_body,
)

DRIFT_RESULT = {
    "repo": "malkreide/mcp-audit-skill",
    "status": "ok",
    "catalog_checks": 96,
    "catalog_categories": 12,
    "description": "… · 93 Checks · 12 Kategorien · MIT",
    "problems": ["Description nennt 93 Checks, Katalog hat 96"],
    "suggestion": "… · 96 Checks · 12 Kategorien · MIT",
    "ok": False,
}

OK_RESULT = {**DRIFT_RESULT, "problems": [], "suggestion": None, "ok": True}


class TestClassification:
    def test_drift_when_the_numbers_disagree(self):
        assert classify(DRIFT_RESULT) == DRIFT

    def test_ok_when_they_agree(self):
        assert classify(OK_RESULT) == OK

    @pytest.mark.parametrize(
        ("label", "result"),
        [
            ("no result at all", None),
            ("fetch failed", {"status": "http 403", "description": None, "ok": False}),
            ("fetch failed but ok true", {"description": None, "ok": True}),
        ],
    )
    def test_a_failed_fetch_does_not_read_as_all_clear(self, label, result):
        """No comparison happened, so neither «drift» nor «ok» is honest.

        `ok: True` alongside `description: None` is included deliberately: the
        state must follow whether a comparison took place, not a flag that could
        be set by a code path that never compared anything.
        """
        assert classify(result) == UNCHECKED, label


class TestLoading:
    def test_a_missing_file_is_unchecked_not_a_crash(self, tmp_path):
        assert load_result(tmp_path / "nope.json") is None

    @pytest.mark.parametrize(
        "content", ["", "   \n", "{not json", "[1, 2, 3]", '"str"']
    )
    def test_unusable_content_collapses_to_none(self, tmp_path, content):
        p = tmp_path / "result.json"
        p.write_text(content, encoding="utf-8")
        assert load_result(p) is None

    def test_a_directory_in_place_of_the_file_is_unchecked(self, tmp_path):
        d = tmp_path / "result.json"
        d.mkdir()
        assert load_result(d) is None


class TestBody:
    def test_the_body_carries_the_ready_made_text(self):
        body = render_body(DRIFT_RESULT)
        assert "96 Checks" in body
        assert "Description nennt 93 Checks, Katalog hat 96" in body
        assert "About" in body, "the human needs to be told where to paste it"

    def test_the_body_says_the_guard_does_not_write(self):
        """Changing repo metadata belongs to a person; the issue must say so."""
        assert "schreibt bewusst nicht" in render_body(DRIFT_RESULT)

    def test_the_body_asks_for_the_workflow_to_be_re_run(self):
        """A repair produces no event, so the issue outlives the fix.

        Observed: the description was corrected and the issue stayed open,
        because editing repo metadata triggers no push and the guard's only
        other event is the Monday cron. The guard does not notice a repair, it
        notices the next occasion. The body has to name the manual trigger —
        and say what it costs to skip it, or it reads as optional.
        """
        body = render_body(DRIFT_RESULT)
        assert "Run workflow" in body, "the button needs its label"
        assert "Actions" in body, "and the tab it lives in"
        assert "repo-description" in body, "and which workflow to pick"
        assert "Montag" in body, "and what waiting instead would cost"


class TestTheInstructionMatchesTheWorkflow:
    """The body sends a person to a button. The button has to exist.

    This is the half a text test cannot cover: `render_body` would happily
    describe a trigger the workflow does not offer, and the reader would find
    out in the Actions tab. Cheap to bind, so bound.
    """

    def test_the_workflow_can_actually_be_dispatched_by_hand(self):
        workflow = (
            Path(__file__).resolve().parent.parent
            / ".github"
            / "workflows"
            / "repo-description.yml"
        )
        assert workflow.is_file(), f"{workflow} fehlt"
        assert "workflow_dispatch:" in workflow.read_text(encoding="utf-8"), (
            "Das Issue verweist auf «Run workflow», aber der Workflow bietet "
            "keinen manuellen Auslöser an."
        )


class TestCLI:
    def _run(self, tmp_path, capsys, payload):
        result = tmp_path / "result.json"
        if payload is not None:
            result.write_text(json.dumps(payload), encoding="utf-8")
        out = tmp_path / "issue-body.md"
        code = main(["--result", str(result), "--out", str(out)])
        return code, capsys.readouterr().out.strip(), out

    def test_drift_prints_drift_and_writes_a_body(self, tmp_path, capsys):
        code, state, out = self._run(tmp_path, capsys, DRIFT_RESULT)
        assert code == 0
        assert state == DRIFT
        assert out.read_text(encoding="utf-8").strip() != ""

    def test_ok_prints_ok_and_writes_an_empty_body(self, tmp_path, capsys):
        _, state, out = self._run(tmp_path, capsys, OK_RESULT)
        assert state == OK
        assert out.read_text(encoding="utf-8") == ""

    def test_unchecked_prints_unchecked(self, tmp_path, capsys):
        _, state, _ = self._run(tmp_path, capsys, None)
        assert state == UNCHECKED

    def test_a_stale_body_is_never_left_behind(self, tmp_path, capsys):
        """The workflow branches on the state word, but `gh` reads the file.

        If a previous run's body survived on disk, an «ok» run that somehow
        reached the create path would post last week's numbers as if they were
        this week's. The file is rewritten unconditionally.
        """
        out = tmp_path / "issue-body.md"
        out.write_text("STALE BODY FROM AN EARLIER RUN\n", encoding="utf-8")
        result = tmp_path / "result.json"
        result.write_text(json.dumps(OK_RESULT), encoding="utf-8")

        main(["--result", str(result), "--out", str(out)])

        assert "STALE" not in out.read_text(encoding="utf-8")
