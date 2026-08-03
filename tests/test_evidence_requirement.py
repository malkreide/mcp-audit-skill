# -*- coding: utf-8 -*-
"""Tests for the evidence gate — `check_evidence_requirement`.

`evidence_required` sat in the frontmatter of all 90 checks and in SKILL.md as
prose from the beginning, and no tool under `tools/` ever read it. A `pass`
with an empty evidence list went through the gate untouched.

That is the same defect as an empty finding document (`finding_substance`),
pointing the direction that ends the conversation: an unevidenced `fail` gets
worked on, an unevidenced `pass` closes the subject and nothing downstream ever
disagrees with it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.aggregate_results import (
    VerificationResults,
    check_evidence_requirement,
    main as aggregate_main,
)
from tools.parse_catalog import DEFAULT_EVIDENCE_REQUIRED, parse_catalog


def _check(dir: Path, cid: str, evidence_required: str | None = "2") -> None:
    fm = [
        f"id: {cid}",
        'title: "x"',
        "category: ARCH",
        "severity: high",
        "applies_when: 'always'",
    ]
    if evidence_required is not None:
        fm.append(f"evidence_required: {evidence_required}")
    (dir / f"{cid}.md").write_text(
        "---\n" + "\n".join(fm) + "\n---\n\nbody\n", encoding="utf-8"
    )


def _results(**per_check: dict) -> VerificationResults:
    return VerificationResults.from_dict(
        {"audit_meta": {"server_name": "s"}, "results": per_check}
    )


def _result(status: str, evidence: list[str] | None = None) -> dict:
    return {
        "status": status,
        "category": "ARCH",
        "severity": "high",
        "evidence": evidence or [],
    }


class TestTheCatalogueFieldIsRead:
    def test_every_shipped_check_declares_a_requirement(self):
        """The field is what this gate stands on; without it there is no gate."""
        catalog = parse_catalog(Path(__file__).resolve().parent.parent / "checks")
        missing = [c for c, fm in catalog.items() if "evidence_required" not in fm]
        assert missing == []

    def test_it_is_an_int_not_the_frontmatter_string(self):
        """Normalised once, so no consumer has to guess between "2" and 2."""
        catalog = parse_catalog(Path(__file__).resolve().parent.parent / "checks")
        assert all(isinstance(fm["evidence_required"], int) for fm in catalog.values())

    def test_a_missing_field_defaults_to_one(self, tmp_path):
        _check(tmp_path, "ARCH-001", evidence_required=None)
        catalog = parse_catalog(tmp_path)
        assert catalog["ARCH-001"]["evidence_required"] == DEFAULT_EVIDENCE_REQUIRED
        assert DEFAULT_EVIDENCE_REQUIRED >= 1, "a default of 0 would be no gate at all"

    def test_a_non_integer_is_a_hard_error(self, tmp_path):
        """A typo must not quietly drop the requirement to nothing."""
        _check(tmp_path, "ARCH-001", evidence_required="lots")
        with pytest.raises(ValueError, match="evidence_required"):
            parse_catalog(tmp_path)

    def test_a_negative_requirement_is_a_hard_error(self, tmp_path):
        _check(tmp_path, "ARCH-001", evidence_required="-1")
        with pytest.raises(ValueError, match="negative"):
            parse_catalog(tmp_path)


class TestWhichStatusesMustShowSomething:
    def test_an_unevidenced_pass_is_the_defect_this_exists_for(self, tmp_path):
        _check(tmp_path, "ARCH-001")
        problems = check_evidence_requirement(
            _results(**{"ARCH-001": _result("pass")}), tmp_path
        )
        assert len(problems) == 1
        assert "not_verified" in problems[0], (
            "the message must name the status the auditor should have used — "
            "OPS-004 has said so in prose since it was written"
        )

    def test_an_unevidenced_fail_is_refused_too(self, tmp_path):
        """A finding without its observation is an opinion."""
        _check(tmp_path, "ARCH-001")
        assert check_evidence_requirement(
            _results(**{"ARCH-001": _result("fail")}), tmp_path
        )

    def test_partial_counts_as_judged(self, tmp_path):
        _check(tmp_path, "ARCH-001")
        assert check_evidence_requirement(
            _results(**{"ARCH-001": _result("partial", ["one"])}), tmp_path
        )

    def test_enough_evidence_passes(self, tmp_path):
        _check(tmp_path, "ARCH-001")
        assert (
            check_evidence_requirement(
                _results(**{"ARCH-001": _result("pass", ["a", "b"])}), tmp_path
            )
            == []
        )

    def test_blank_strings_do_not_count(self, tmp_path):
        """Two spaces are exactly as informative as no entry at all."""
        _check(tmp_path, "ARCH-001")
        assert check_evidence_requirement(
            _results(**{"ARCH-001": _result("pass", ["  ", ""])}), tmp_path
        )

    def test_todo_and_na_claim_nothing_so_they_owe_nothing(self, tmp_path):
        """Demanding observations here would push an auditor to invent some."""
        _check(tmp_path, "ARCH-001")
        _check(tmp_path, "ARCH-002")
        assert (
            check_evidence_requirement(
                _results(
                    **{"ARCH-001": _result("todo"), "ARCH-002": _result("n/a")}
                ),
                tmp_path,
            )
            == []
        )

    def test_not_verified_owes_one_item_not_the_full_count(self, tmp_path):
        """It has no evidence *either way* — but it can always name the attempt.

        Requiring the catalogue's full count would contradict the status;
        requiring nothing would make `not_verified` the way around the gate.
        """
        _check(tmp_path, "ARCH-001", evidence_required="3")
        assert check_evidence_requirement(
            _results(**{"ARCH-001": _result("not_verified")}), tmp_path
        )
        assert (
            check_evidence_requirement(
                _results(
                    **{"ARCH-001": _result("not_verified", ["endpoint unreachable"])}
                ),
                tmp_path,
            )
            == []
        )

    def test_an_id_the_catalogue_does_not_know_is_not_this_gate_s_finding(
        self, tmp_path
    ):
        """`apply_catalog_adoption` already reports those — no double report."""
        _check(tmp_path, "ARCH-001")
        assert (
            check_evidence_requirement(
                _results(**{"GHOST-001": _result("pass")}), tmp_path
            )
            == []
        )


class TestTheCli:
    def _results_file(self, tmp_path: Path, evidence: list[str] | None = None) -> Path:
        p = tmp_path / "verification-results.json"
        p.write_text(
            json.dumps(
                {
                    "audit_meta": {"server_name": "s"},
                    "results": {"ARCH-001": _result("pass", evidence)},
                }
            ),
            encoding="utf-8",
        )
        return p

    def test_aggregate_refuses_and_writes_no_summary(self, tmp_path, capsys):
        """A summary that failed the gate would be read downstream as a pass."""
        checks = tmp_path / "checks"
        checks.mkdir()
        _check(checks, "ARCH-001")
        out = tmp_path / "summary.json"
        rc = aggregate_main(
            [
                "aggregate",
                str(self._results_file(tmp_path)),
                "--checks-dir",
                str(checks),
                "--out",
                str(out),
            ]
        )
        assert rc == 1
        assert not out.exists()
        assert "evidence" in capsys.readouterr().err

    def test_allow_unevidenced_downgrades_to_a_warning_and_says_so(
        self, tmp_path, capsys
    ):
        checks = tmp_path / "checks"
        checks.mkdir()
        _check(checks, "ARCH-001")
        rc = aggregate_main(
            [
                "aggregate",
                str(self._results_file(tmp_path)),
                "--checks-dir",
                str(checks),
                "--allow-unevidenced",
            ]
        )
        captured = capsys.readouterr()
        assert rc == 0
        assert "Warning" in captured.err
        summary = json.loads(captured.out)
        assert summary["evidence_gate"]["enforced"] is False

    def test_without_checks_dir_the_summary_admits_the_gate_did_not_run(
        self, tmp_path, capsys
    ):
        """"Not measured" is not "clean" — the summary has to carry which one."""
        rc = aggregate_main(["aggregate", str(self._results_file(tmp_path))])
        captured = capsys.readouterr()
        assert rc == 0
        summary = json.loads(captured.out)
        assert summary["evidence_gate"]["enforced"] is False
        assert summary["evidence_gate"]["checked_against"] is None
        assert "not enforced" in captured.err

    def test_an_evidenced_run_aggregates_and_records_the_catalogue(
        self, tmp_path, capsys
    ):
        checks = tmp_path / "checks"
        checks.mkdir()
        _check(checks, "ARCH-001")
        rc = aggregate_main(
            [
                "aggregate",
                str(self._results_file(tmp_path, ["src/a.py:1 — x", "tests/b.py:2 — y"])),
                "--checks-dir",
                str(checks),
            ]
        )
        captured = capsys.readouterr()
        assert rc == 0
        summary = json.loads(captured.out)
        assert summary["evidence_gate"] == {
            "enforced": True,
            "checked_against": str(checks),
        }
