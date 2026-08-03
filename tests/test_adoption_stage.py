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
from typing import ClassVar

import pytest

from tools.aggregate_results import (
    AggregationError,
    VerificationResults,
    aggregate,
    apply_catalog_adoption,
)
from tools.aggregate_results import (
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
        # OBS-007 crossed the bridge and was promoted. It entered advisory on
        # the assumption that the `f"...: {exc}"` pattern was everywhere; a run
        # over ten servers said otherwise — two of the eight with a retry path
        # fail it, because `raise last_exc` passes and only *wrapping* fails.
        # A check that is narrow and has no false positives has nothing left to
        # prove by not blocking.
        #
        # ARCH-014 took the bridge and was promoted on 2026-08-03. The
        # numbers that put it on advisory were real: of eleven servers, none
        # read `Retry-After`, none spread its backoff, and three had no retry
        # loop at all. Enforced on day one would have been a red portfolio,
        # which is how checks get reverted rather than adopted.
        #
        # The condition it was parked under is now met — all eleven pass. The
        # crossing also sharpened the check: capping *before* jitter (six
        # servers), a "total budget" made of per-operation httpx timeouts (six
        # servers), and a retry that covered status codes but not network
        # errors (one server) are all findings from the adoption run, and all
        # three are now pass-patterns.
        #
        # OPS-006 takes the same bridge. Of 32 portfolio repos, 29 pin no
        # tool version at all — enforced on day one would fail almost the
        # whole portfolio for a property none of them was ever asked to
        # have. Advisory until a run shows the check is cut correctly.
        #
        # OPS-007 likewise. Every repo documents commands and almost none has
        # ever been asked whether they run on the platforms it claims; the one
        # finding behind the check surfaced only because a user said which
        # shell they use. Enforced on day one would fail the portfolio for a
        # property nobody has measured yet — advisory until a run does.
        assert advisory_ids(parse_catalog(CHECKS_DIR)) == [
            "OPS-005",
            "OPS-006",
            "OPS-007",
            "OPS-008",
        ]

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
# The advisory set as the READMEs state it
# ---------------------------------------------------------------------------


class TestReadmesNameTheAdvisorySet:
    """Both READMEs spell the advisory set out by name. Nothing enforced it.

    `advisory_ids` was pinned in the test above and the catalogue counts are
    guarded in `test_readme_counts.py`, but the sentence naming *which* checks
    are advisory sat between the two and belonged to neither. It drifted the
    first time it could: `OPS-007` joined the set, both count lines were pulled
    to 97, and both READMEs went on saying «exactly three … `ARCH-014`,
    `OPS-005` and `OPS-006`».

    That is the one adoption fact a reader takes away without opening a check
    file, and it is the one that decides whether a red finding blocks a
    release. A value nothing enforces drifts — so this enforces it, by name and
    by count, in every language fassung on disk.
    """

    READMES: ClassVar[list[Path]] = sorted(REPO_ROOT.glob("README*.md"))

    def test_readmes_exist(self):
        # Without this, the parametrisation below could run over an empty list
        # — and a test with no cases is green.
        assert self.READMES, "no README*.md found"

    @pytest.mark.parametrize("readme", READMES, ids=lambda p: p.name)
    def test_every_advisory_check_is_named(self, readme: Path):
        expected = advisory_ids(parse_catalog(CHECKS_DIR))
        # The paragraph, not the whole file: `ARCH-014` is mentioned elsewhere
        # for unrelated reasons, and matching the file would pass on that.
        text = readme.read_text(encoding="utf-8")
        marker = "`advisory`:"
        assert marker in text, f"{readme.name}: advisory sentence not found"
        start = text.index(marker)
        paragraph = text[start : text.index("\n", start)]
        missing = [cid for cid in expected if f"`{cid}`" not in paragraph]
        assert not missing, (
            f"{readme.name} does not name {missing} as advisory. "
            f"The catalogue says: {expected}"
        )

    @pytest.mark.parametrize("readme", READMES, ids=lambda p: p.name)
    def test_no_promoted_check_is_still_listed(self, readme: Path):
        # The other direction, and the one a promotion breaks: the sentence
        # naming a check the catalogue no longer holds on the bridge. Adding a
        # check is loud — someone writes the paragraph. Promoting one is quiet:
        # a single frontmatter line moves from `advisory` to `enforced`, and
        # nothing pulls the sentence along. The count word catches it only if
        # the length is noticed too, which is what went wrong the first time.
        catalog = parse_catalog(CHECKS_DIR)
        expected = advisory_ids(catalog)
        text = readme.read_text(encoding="utf-8")
        start = text.index("`advisory`:")
        sentence = text[start : text.index("\n", start)]
        # Past the first period the same sentence deliberately names the checks
        # that *were* promoted. Only the part before it is the bridge.
        listed = sentence.split("`advisory`:", 1)[1].split(".", 1)[0]
        stale = [cid for cid in catalog if cid not in expected and f"`{cid}`" in listed]
        assert not stale, (
            f"{readme.name} still names {stale} as advisory. The catalogue has "
            f"{[(cid, catalog[cid]['adoption']) for cid in stale]}"
        )

    @pytest.mark.parametrize("readme", READMES, ids=lambda p: p.name)
    def test_the_stated_count_matches(self, readme: Path):
        expected = len(advisory_ids(parse_catalog(CHECKS_DIR)))
        words = {
            1: ("one", "ein"),
            2: ("two", "zwei"),
            3: ("three", "drei"),
            4: ("four", "vier"),
            5: ("five", "fünf"),
        }
        assert expected in words, (
            f"{expected} advisory checks — extend the number words in this test"
        )
        text = readme.read_text(encoding="utf-8")
        start = text.index("`advisory`:")
        # Look back far enough to catch «exactly four are» / «genau vier sind».
        window = text[max(0, start - 200) : start]
        assert any(w in window for w in words[expected]), (
            f"{readme.name}: the advisory sentence does not say "
            f"{words[expected]} — the catalogue has {expected}"
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
    FAIL_HIGH: ClassVar[dict[str, str]] = {
        "status": "fail",
        "category": "ARCH",
        "severity": "high",
    }

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
                            # Ein Befund ohne seine Beobachtung ist eine
                            # Meinung — `check_evidence_requirement` weist ihn
                            # seit Neuem zurueck. Die Fixture traegt deshalb
                            # einen Beleg, statt das Gate abzuschalten.
                            "evidence": ["src/server.py:12 — tool name is camelCase"],
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
