# -*- coding: utf-8 -*-
"""Tests for the adoption stage — `advisory` vs `enforced`.

Severity says how bad a violation is. Adoption says whether the catalogue is
yet entitled to hold the portfolio to it. Without the second axis a new check
lands as a red pipeline across 30+ servers on the day it is merged, which is
how checks get reverted rather than adopted.

Two properties matter most and are asserted in both directions:

1. Adding the mechanism changes no existing verdict. Every check that predates
   the field defaults to `enforced` and keeps blocking exactly as before.
2. `advisory` genuinely stops blocking — and the finding is still produced,
   still counted, still carries its severity. A stage that merely hid the
   finding would be worse than no stage at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.aggregate_results import (
    AggregationError,
    VerificationResults,
    aggregate,
    apply_catalog_adoption,
    main as aggregate_main,
)
from tools.build_report import render_executive_summary
from tools.parse_catalog import (
    DEFAULT_ADOPTION,
    VALID_ADOPTIONS,
    adoption_counts,
    advisory_ids,
    parse_catalog,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"


def _check(dir: Path, cid: str, adoption: str | None = None) -> None:
    fm = [
        f"id: {cid}",
        'title: "x"',
        "category: ARCH",
        "severity: high",
        "applies_when: 'always'",
    ]
    if adoption is not None:
        fm.append(f"adoption: {adoption}")
    (dir / f"{cid}.md").write_text(
        "---\n" + "\n".join(fm) + "\n---\n\nbody\n", encoding="utf-8"
    )


def _results(**per_check: dict) -> VerificationResults:
    return VerificationResults.from_dict(
        {
            "audit_meta": {"server_name": "s"},
            "results": per_check,
        }
    )


# ---------------------------------------------------------------------------
# The real catalogue: the mechanism must be a no-op on arrival
# ---------------------------------------------------------------------------


class TestRealCatalogUnchanged:
    def test_every_check_has_a_valid_adoption(self):
        catalog = parse_catalog(CHECKS_DIR)
        for cid, fm in catalog.items():
            assert fm["adoption"] in VALID_ADOPTIONS, cid

    def test_adoption_counts_cover_the_whole_catalogue(self):
        catalog = parse_catalog(CHECKS_DIR)
        counts = adoption_counts(catalog)
        assert set(counts) == set(VALID_ADOPTIONS), "both keys always present"
        assert sum(counts.values()) == len(catalog)

    def test_advisory_set_is_pinned(self):
        # Promoting or demoting a check is a deliberate decision. Pinning the
        # set means it shows up in review rather than in a diff nobody reads —
        # and the CHANGELOG entry is part of making the change, not an
        # afterthought.
        #
        # OPS-005 is the first check to take the documented route: merged
        # advisory, promoted to enforced once a portfolio run shows whether it
        # is cut correctly.
        #
        # DEP-001 and DRIFT-006 entered advisory and were promoted to enforced
        # by a maintainer decision recorded in the CHANGELOG.
        #
        # OBS-007 is the next to take the same route. The `f"...: {exc}"`
        # pattern it rejects is the obvious way to write that line, so the
        # check plausibly fires across much of the portfolio on the day it
        # lands — exactly the situation the bridge exists for.
        assert advisory_ids(parse_catalog(CHECKS_DIR)) == ["OBS-007", "OPS-005"]

    def test_the_mechanism_is_not_a_blanket_demotion(self):
        # An advisory stage is a bridge for a specific new check, not a way to
        # soften the catalogue. If most of it stopped blocking, the stage has
        # become an excuse.
        catalog = parse_catalog(CHECKS_DIR)
        counts = adoption_counts(catalog)
        assert counts["advisory"] <= len(catalog) // 10, (
            f"{counts['advisory']} of {len(catalog)} checks are advisory — "
            "the stage is meant to carry a handful of new checks, not the catalogue"
        )


# ---------------------------------------------------------------------------
# Catalogue parsing
# ---------------------------------------------------------------------------


class TestCatalogParsing:
    def test_absent_field_defaults_to_enforced(self, tmp_path):
        _check(tmp_path, "TST-001")
        assert parse_catalog(tmp_path)["TST-001"]["adoption"] == DEFAULT_ADOPTION
        assert DEFAULT_ADOPTION == "enforced"

    def test_explicit_values_survive(self, tmp_path):
        _check(tmp_path, "TST-001", "advisory")
        _check(tmp_path, "TST-002", "enforced")
        catalog = parse_catalog(tmp_path)
        assert catalog["TST-001"]["adoption"] == "advisory"
        assert catalog["TST-002"]["adoption"] == "enforced"

    def test_typo_is_a_hard_error(self, tmp_path):
        # A typo must never silently demote a check to advisory — that is the
        # quietest possible way to lose one.
        _check(tmp_path, "TST-001", "advisroy")
        with pytest.raises(ValueError, match="invalid adoption"):
            parse_catalog(tmp_path)

    def test_advisory_ids_are_sorted(self, tmp_path):
        _check(tmp_path, "TST-003", "advisory")
        _check(tmp_path, "TST-001", "advisory")
        _check(tmp_path, "TST-002")
        assert advisory_ids(parse_catalog(tmp_path)) == ["TST-001", "TST-003"]


# ---------------------------------------------------------------------------
# Aggregation: the stage has to actually bite
# ---------------------------------------------------------------------------


class TestAggregation:
    FAIL_HIGH = {"status": "fail", "category": "ARCH", "severity": "high"}

    def test_enforced_failure_blocks(self):
        s = aggregate(_results(**{"ARCH-001": dict(self.FAIL_HIGH)}))
        assert s["blocking_findings"] == ["ARCH-001"]
        assert s["advisory_findings"] == []
        assert s["production_ready"] is False

    def test_advisory_failure_does_not_block(self):
        s = aggregate(
            _results(
                **{
                    "ARCH-001": dict(self.FAIL_HIGH, adoption="advisory"),
                }
            )
        )
        assert s["blocking_findings"] == []
        assert s["advisory_findings"] == ["ARCH-001"]
        assert s["production_ready"] is True

    def test_advisory_still_produces_a_finding(self):
        # The stage must not hide the finding — only its veto. A stage that
        # suppressed the report would be worse than no stage.
        s = aggregate(
            _results(
                **{
                    "ARCH-001": dict(self.FAIL_HIGH, adoption="advisory"),
                }
            )
        )
        assert s["findings"]["expected_ids"] == ["ARCH-001"]
        assert s["totals"]["by_severity_among_findings"]["high"] == 1
        assert s["findings"]["details"][0]["adoption"] == "advisory"

    def test_one_enforced_failure_still_blocks_beside_an_advisory_one(self):
        s = aggregate(
            _results(
                **{
                    "ARCH-001": dict(self.FAIL_HIGH, adoption="advisory"),
                    "SEC-001": dict(
                        self.FAIL_HIGH, category="SEC", adoption="enforced"
                    ),
                }
            )
        )
        assert s["blocking_findings"] == ["SEC-001"]
        assert s["advisory_findings"] == ["ARCH-001"]
        assert s["production_ready"] is False

    def test_advisory_below_blocking_severity_is_not_listed(self):
        # advisory_findings means "would have blocked"; a medium never would.
        s = aggregate(
            _results(
                **{
                    "ARCH-001": {
                        "status": "fail",
                        "category": "ARCH",
                        "severity": "medium",
                        "adoption": "advisory",
                    },
                }
            )
        )
        assert s["advisory_findings"] == []
        assert s["findings"]["expected_ids"] == ["ARCH-001"]

    def test_missing_adoption_defaults_to_enforced(self):
        s = aggregate(_results(**{"ARCH-001": dict(self.FAIL_HIGH)}))
        assert s["findings"]["details"][0]["adoption"] == "enforced"

    def test_invalid_adoption_in_results_is_rejected(self):
        with pytest.raises(AggregationError, match="invalid adoption"):
            _results(**{"ARCH-001": dict(self.FAIL_HIGH, adoption="maybe")})

    def test_by_adoption_counts_exclude_not_applicable(self):
        s = aggregate(
            _results(
                **{
                    "ARCH-001": dict(self.FAIL_HIGH),
                    "ARCH-002": {
                        "status": "n/a",
                        "category": "ARCH",
                        "severity": "low",
                    },
                }
            )
        )
        assert s["totals"]["by_adoption"] == {"advisory": 0, "enforced": 1}


# ---------------------------------------------------------------------------
# The catalogue is authoritative
# ---------------------------------------------------------------------------


class TestCatalogIsAuthoritative:
    def test_catalog_overrides_the_results_file(self, tmp_path):
        _check(tmp_path, "ARCH-001", "advisory")
        vr = _results(
            **{
                "ARCH-001": {
                    "status": "fail",
                    "category": "ARCH",
                    "severity": "high",
                    "adoption": "enforced",
                },
            }
        )
        assert apply_catalog_adoption(vr, tmp_path) == []
        assert aggregate(vr)["production_ready"] is True

    def test_unknown_ids_are_reported_and_keep_the_safe_default(self, tmp_path):
        _check(tmp_path, "ARCH-001", "advisory")
        vr = _results(
            **{
                "ARCH-001": {"status": "fail", "category": "ARCH", "severity": "high"},
                "GHOST-001": {"status": "fail", "category": "ARCH", "severity": "high"},
            }
        )
        assert apply_catalog_adoption(vr, tmp_path) == ["GHOST-001"]
        # The unknown one keeps `enforced`, so the verdict errs towards blocking.
        assert aggregate(vr)["blocking_findings"] == ["GHOST-001"]

    def test_cli_checks_dir_changes_the_verdict(self, tmp_path, capsys):
        _check(tmp_path, "ARCH-001", "advisory")
        results = tmp_path / "verification-results.json"
        results.write_text(
            json.dumps(
                {
                    "audit_meta": {"server_name": "s"},
                    "results": {
                        "ARCH-001": {
                            "status": "fail",
                            "category": "ARCH",
                            "severity": "high",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        assert aggregate_main(["aggregate", str(results)]) == 0
        without = json.loads(capsys.readouterr().out)
        assert without["production_ready"] is False

        assert (
            aggregate_main(
                [
                    "aggregate",
                    str(results),
                    "--checks-dir",
                    str(tmp_path),
                ]
            )
            == 0
        )
        with_catalog = json.loads(capsys.readouterr().out)
        assert with_catalog["production_ready"] is True
        assert with_catalog["advisory_findings"] == ["ARCH-001"]


# ---------------------------------------------------------------------------
# The report must not swallow an advisory failure
# ---------------------------------------------------------------------------


class TestReport:
    def _summary(self, **over):
        base = {
            "audit_meta": {"server_name": "s"},
            "totals": {
                "applicable": 1,
                "by_status": {"pass": 0},
                "by_severity_among_findings": {},
            },
            "findings": {"expected_count": 1},
            "production_ready": True,
            "blocking_findings": [],
            "advisory_findings": [],
        }
        base.update(over)
        return base

    def test_green_verdict_names_the_advisory_failures(self):
        text = render_executive_summary(self._summary(advisory_findings=["FID-003"]))
        assert "Production-Readiness: erreicht" in text
        assert "FID-003" in text
        assert "enforced" in text

    def test_green_verdict_without_advisory_stays_terse(self):
        text = render_executive_summary(self._summary())
        assert "advisory" not in text

    def test_red_verdict_still_lists_advisory_separately(self):
        text = render_executive_summary(
            self._summary(
                production_ready=False,
                blocking_findings=["SEC-001"],
                advisory_findings=["FID-003"],
            )
        )
        assert "SEC-001" in text and "FID-003" in text
