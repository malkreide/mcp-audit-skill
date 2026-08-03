"""Tests for the finding carry-forward helper.

The helper exists because this step was hand-rolled twice and went wrong twice,
so the tests are organised around the two real failures rather than around the
function's surface: `test_slugged_source_resolves_to_a_bare_id` and
`test_an_empty_source_is_never_carried_forward` are the ones that matter. If any
test here is ever dropped, it is not those two.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.carry_forward import (
    carry_forward,
    check_id_from_path,
    index_findings,
    main,
    substance,
)

EXPECTED = ["OBS-001", "SEC-009", "SDK-003"]


def _make_run(root: Path, name: str, expected: list[str] | None = None) -> Path:
    run = root / name
    (run / "findings").mkdir(parents=True)
    summary = {"findings": {"expected_ids": list(EXPECTED if expected is None else expected)}}
    (run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return run


def _write(run: Path, filename: str, body: str = "## Finding\n\nreal content\n") -> Path:
    path = run / "findings" / filename
    path.write_text(body, encoding="utf-8")
    return path


# --- filename handling -----------------------------------------------------


class TestNameResolution:
    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("SEC-009.md", "SEC-009"),
            ("SEC-009-session-id-cryptographic-binding.md", "SEC-009"),
            ("SCALE-002-stateful-load-balancing-f-r-sse.md", "SCALE-002"),
            ("audit-report.md", None),
            ("README.md", None),
        ],
    )
    def test_check_id_from_path(self, filename, expected):
        assert check_id_from_path(Path(filename)) == expected

    def test_substance_ignores_whitespace(self, tmp_path):
        empty = tmp_path / "a.md"
        empty.write_text("", encoding="utf-8")
        blank = tmp_path / "b.md"
        blank.write_text("\n\n   \t\n", encoding="utf-8")
        real = tmp_path / "c.md"
        real.write_text("# x\n\nbody\n", encoding="utf-8")
        assert substance(empty) == 0
        assert substance(blank) == 0
        assert substance(real) > 0


# --- the two failures this helper exists for -------------------------------


class TestTheOriginalFailures:
    def test_slugged_source_resolves_to_a_bare_id(self, tmp_path):
        """Failure one: the source named files `<ID>-<slug>.md`.

        The hand-rolled step looked for a bare `<ID>.md`, found nothing, and
        wrote an empty placeholder. Sixteen findings across two runs ended up
        as zero-byte files that the validation gate accepted.
        """
        src = _make_run(tmp_path, "old")
        for cid in EXPECTED:
            _write(src, f"{cid}-some-descriptive-slug.md")
        target = _make_run(tmp_path, "new")

        report = carry_forward(target, [src])

        assert report["complete"] is True
        assert report["missing"] == []
        assert {c["check_id"] for c in report["carried"]} == set(EXPECTED)
        for cid in EXPECTED:
            found = list((target / "findings").glob(f"{cid}*.md"))
            assert found, f"{cid} not carried"
            assert substance(found[0]) > 0

    def test_an_empty_source_is_never_carried_forward(self, tmp_path):
        """Failure two: the residue of failure one became the next run's input.

        A zero-byte file left by the original bug must not be treated as a
        document. It is reported missing — loudly — rather than propagated.
        """
        src = _make_run(tmp_path, "old")
        _write(src, "OBS-001-real.md")
        _write(src, "SEC-009.md", "")  # the residue
        _write(src, "SDK-003.md", "\n \n")  # whitespace-only residue
        target = _make_run(tmp_path, "new")

        report = carry_forward(target, [src])

        assert report["missing"] == ["SDK-003", "SEC-009"]
        assert report["complete"] is False
        assert not (target / "findings" / "SEC-009.md").exists()
        assert [c["check_id"] for c in report["carried"]] == ["OBS-001"]

    def test_a_real_document_beside_the_residue_still_wins(self, tmp_path):
        """Both spellings coexist in real trees, one of them left over empty.

        Indexing has to prefer the substantial file rather than whichever name
        sorts first — otherwise repairing the bug trips over its own leftovers.
        """
        src = _make_run(tmp_path, "old")
        _write(src, "SEC-009.md", "")
        _write(src, "SEC-009-session-id-binding.md", "## Finding\n\nthe real one\n")
        target = _make_run(tmp_path, "new", expected=["SEC-009"])

        report = carry_forward(target, [src])

        assert report["complete"] is True
        assert report["carried"][0]["from"].endswith("SEC-009-session-id-binding.md")


# --- protecting work done for this run -------------------------------------


class TestTargetPrecedence:
    def test_a_hand_written_target_is_not_overwritten(self, tmp_path):
        """A finding rewritten for this run outranks anything carried forward.

        This is the case that made the original bug survive review: two
        hand-written findings had content, so the directory looked complete.
        """
        src = _make_run(tmp_path, "old")
        _write(src, "OBS-001.md", "## Finding\n\nstale wording from last run\n")
        target = _make_run(tmp_path, "new", expected=["OBS-001"])
        _write(target, "OBS-001.md", "## Finding\n\nrewritten for this run\n")

        report = carry_forward(target, [src])

        assert report["kept"] == ["OBS-001"]
        assert report["carried"] == []
        assert "rewritten for this run" in (target / "findings" / "OBS-001.md").read_text()

    def test_a_stub_is_overwritten_in_place_leaving_no_residue(self, tmp_path):
        """Found by running the helper against the real broken run.

        Writing the source's slugged name repaired coverage and left the
        zero-byte `<ID>.md` sitting beside it — twelve of them. The gate passed,
        because it takes the most substantial document per id, so the litter was
        invisible to it. Repairing an artefact must not leave the artefact
        dirty.
        """
        src = _make_run(tmp_path, "old")
        _write(src, "OBS-001-descriptive-slug.md", "## Finding\n\nreal\n")
        target = _make_run(tmp_path, "new", expected=["OBS-001"])
        _write(target, "OBS-001.md", "")

        carry_forward(target, [src])

        files = sorted(p.name for p in (target / "findings").glob("*.md"))
        assert files == ["OBS-001.md"], f"stub not reused, residue left: {files}"
        assert substance(target / "findings" / "OBS-001.md") > 0

    def test_an_empty_target_is_replaced(self, tmp_path):
        """The repair path: a zero-byte target is exactly what needs filling."""
        src = _make_run(tmp_path, "old")
        _write(src, "OBS-001-real.md")
        target = _make_run(tmp_path, "new", expected=["OBS-001"])
        _write(target, "OBS-001.md", "")

        report = carry_forward(target, [src])

        assert [c["check_id"] for c in report["carried"]] == ["OBS-001"]
        assert report["complete"] is True


# --- source ordering, selection, dry run -----------------------------------


class TestSourcesAndSelection:
    def test_first_source_with_a_document_wins(self, tmp_path):
        recent = _make_run(tmp_path, "recent")
        _write(recent, "OBS-001.md", "## Finding\n\nfrom the recent run\n")
        older = _make_run(tmp_path, "older")
        _write(older, "OBS-001.md", "## Finding\n\nfrom the older run\n")
        target = _make_run(tmp_path, "new", expected=["OBS-001"])

        carry_forward(target, [recent, older])

        assert "recent run" in (target / "findings" / "OBS-001.md").read_text()

    def test_a_later_source_fills_what_the_first_lacks(self, tmp_path):
        recent = _make_run(tmp_path, "recent")
        _write(recent, "OBS-001.md")
        older = _make_run(tmp_path, "older")
        _write(older, "SEC-009-slug.md")
        target = _make_run(tmp_path, "new", expected=["OBS-001", "SEC-009"])

        report = carry_forward(target, [recent, older])

        assert report["complete"] is True
        assert {c["check_id"] for c in report["carried"]} == {"OBS-001", "SEC-009"}

    def test_only_restricts_and_reports_unknown_ids(self, tmp_path):
        src = _make_run(tmp_path, "old")
        for cid in EXPECTED:
            _write(src, f"{cid}.md")
        target = _make_run(tmp_path, "new")

        report = carry_forward(target, [src], only=["OBS-001", "NOPE-999"])

        assert [c["check_id"] for c in report["carried"]] == ["OBS-001"]
        assert report["unknown_ids"] == ["NOPE-999"]
        assert report["complete"] is False, "an id that does not exist must not read as success"

    def test_dry_run_writes_nothing(self, tmp_path):
        src = _make_run(tmp_path, "old")
        for cid in EXPECTED:
            _write(src, f"{cid}.md")
        target = _make_run(tmp_path, "new")

        report = carry_forward(target, [src], dry_run=True)

        assert len(report["carried"]) == len(EXPECTED)
        assert list((target / "findings").glob("*.md")) == []

    def test_index_skips_unrecognisable_filenames(self, tmp_path):
        run = _make_run(tmp_path, "old")
        _write(run, "audit-report.md")
        _write(run, "OBS-001.md")
        assert set(index_findings(run / "findings", 1)) == {"OBS-001"}


# --- CLI -------------------------------------------------------------------


class TestCLI:
    def test_exit_zero_when_complete(self, tmp_path, capsys):
        src = _make_run(tmp_path, "old")
        for cid in EXPECTED:
            _write(src, f"{cid}-slug.md")
        target = _make_run(tmp_path, "new")

        code = main([str(target), "--from", str(src)])

        assert code == 0
        assert "carried" in capsys.readouterr().out

    def test_exit_one_when_a_finding_has_no_source(self, tmp_path, capsys):
        """Loud, not silent — the whole point of the helper."""
        src = _make_run(tmp_path, "old")
        _write(src, "OBS-001.md")
        target = _make_run(tmp_path, "new")

        code = main([str(target), "--from", str(src)])

        assert code == 1
        out = capsys.readouterr()
        assert "MISSING" in out.out
        assert "SEC-009" in out.out

    def test_exit_two_without_a_summary(self, tmp_path, capsys):
        target = tmp_path / "new"
        (target / "findings").mkdir(parents=True)
        src = _make_run(tmp_path, "old")

        code = main([str(target), "--from", str(src)])

        assert code == 2
        assert "summary.json" in capsys.readouterr().err

    def test_json_format_is_machine_readable(self, tmp_path, capsys):
        src = _make_run(tmp_path, "old")
        for cid in EXPECTED:
            _write(src, f"{cid}.md")
        target = _make_run(tmp_path, "new")

        main([str(target), "--from", str(src), "--format", "json"])

        payload = json.loads(capsys.readouterr().out)
        assert payload["complete"] is True
        assert payload["expected_count"] == len(EXPECTED)
