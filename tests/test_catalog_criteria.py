"""Holds catalogue prose to what the tooling can actually record or check.

Three failure classes live here. The first two were found in the same audit:

1. **A rule the tooling makes impossible to follow.** `OPS-004` demanded the
   status `not_verified` while `aggregate_results.py` rejected the value, so
   an auditor who obeyed the check got a schema error and wrote `pass` — the
   one outcome `OPS-004` exists to forbid. A criterion that names a status the
   schema does not know is not a strict rule; it is a rule that resolves to its
   opposite.

2. **A criterion precise enough to sound checkable and not precise enough to
   be checked.** `ARCH-011` said deviations must be justified "im README"
   without saying that a justification elsewhere does not count, and a
   deviation documented in `SECURITY.md` was filed as passing on the first
   attempt.

3. **A remediation block that teaches a value the protocol does not define.**
   Remediation is copy-paste surface: whatever stands there ends up in servers.
   `cacheScope` has exactly two legal values, and the portfolio shipped a third
   one from its own template before any criterion asked (ARCH-020, 2026-08).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.aggregate_results import VALID_STATUSES

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"

# Backtick-quoted lowercase identifiers that look like a status verdict.
STATUS_LIKE = re.compile(r"`(not_verified|not-verified|unverified|nicht_geprüft)`")

# The closed value set of `cacheScope` (SEP-2549), and the shapes an assignment
# takes in a remediation snippet: cacheScope: "x" / cacheScope="x" / == "x".
CACHE_SCOPES = frozenset({"public", "private"})
CACHE_SCOPE_VALUE = re.compile(r"cache_?[Ss]cope\s*[:=]{1,2}\s*\"([a-z_]+)\"")


class TestStatusVocabularyIsRecordable:
    def test_not_verified_is_a_status_the_schema_knows(self):
        assert "not_verified" in VALID_STATUSES

    def test_ops_004_still_demands_it(self):
        # If this check ever stops requiring the status, the status may go —
        # but not before, and not silently.
        text = (CHECKS_DIR / "OPS-004.md").read_text(encoding="utf-8")
        assert "not_verified" in text

    @pytest.mark.parametrize(
        "path", sorted(CHECKS_DIR.glob("*.md")), ids=lambda p: p.stem
    )
    def test_no_check_names_an_unrecordable_status(self, path: Path):
        """Any status spelling a check demands must exist in the schema."""
        for match in STATUS_LIKE.finditer(path.read_text(encoding="utf-8")):
            assert match.group(1) in VALID_STATUSES, (
                f"{path.name} names the status `{match.group(1)}`, which "
                f"tools/aggregate_results.py cannot record. Valid: "
                f"{VALID_STATUSES}. A check that demands an unrecordable "
                "status is a check that gets recorded as `pass`."
            )


class TestArch011DeviationJustification:
    @pytest.fixture
    def text(self) -> str:
        return (CHECKS_DIR / "ARCH-011.md").read_text(encoding="utf-8")

    def test_the_criterion_names_the_two_files_that_count(self, text: str):
        criterion = [
            ln for ln in text.splitlines() if ln.startswith("- [ ] Abweichungen")
        ]
        assert len(criterion) == 1, "expected exactly one deviation criterion"
        assert "README.md" in criterion[0] and "README.de.md" in criterion[0]

    def test_the_criterion_says_security_md_does_not_count(self, text: str):
        criterion = next(
            ln for ln in text.splitlines() if ln.startswith("- [ ] Abweichungen")
        )
        assert "SECURITY.md" in criterion, (
            "The criterion must say which files do NOT satisfy it. Without "
            "that, a deviation justified in SECURITY.md reads as passing — "
            "which is how it was first filed."
        )

    def test_the_failure_mode_is_listed_in_common_failures(self, text: str):
        section = text.split("## Common Failures")[1].split("## Remediation")[0]
        assert "SECURITY.md" in section


class TestCacheScopeVocabularyInRemediation:
    """A remediation block is copy-paste surface, so a wrong value there ships.

    SEP-2549 defines exactly two `cacheScope` values, `"public"` and
    `"private"`. A third one is not a cautious value: an intermediary that does
    not know it treats the field as absent, which is *wider* than `"private"`,
    not narrower.

    The portfolio produced that exact failure one layer out —
    `mcp-data-fidelity-skill` shipped `Literal["public", "session"]` in its
    copy-paste template, and no criterion of this catalogue would have reported
    a server built from it (see the ARCH-020 entry in the CHANGELOG). The
    criterion now exists; this test covers the other direction, that the
    catalogue does not itself teach an invalid value.

    Scanned is the `## Remediation` section only, and deliberately so. Anti-
    patterns are *supposed* to appear in Description, Verification and Common
    Failures — ARCH-020 names `"session"` in all three on purpose. Scanning
    those would flag a correct warning as an error, which is the false alarm
    that gets a guard switched off.
    """

    @staticmethod
    def _remediation(text: str) -> str:
        if "## Remediation" not in text:
            return ""
        return text.split("## Remediation")[1].split("\n## ")[0]

    @pytest.mark.parametrize(
        "path", sorted(CHECKS_DIR.glob("*.md")), ids=lambda p: p.stem
    )
    def test_no_remediation_teaches_an_invalid_cache_scope(self, path: Path):
        section = self._remediation(path.read_text(encoding="utf-8"))
        for match in CACHE_SCOPE_VALUE.finditer(section):
            assert match.group(1) in CACHE_SCOPES, (
                f'{path.name} shows `cacheScope: "{match.group(1)}"` in its '
                f"Remediation. SEP-2549 allows only {sorted(CACHE_SCOPES)}. A "
                "remediation block is what people copy — an invented value "
                "reads to an intermediary as no value at all."
            )

    def test_arch_020_states_the_closed_set_in_a_criterion(self):
        """The Description named the two values since v2.0.0 and no criterion
        read them, which is exactly how `"session"` passed. If the criterion
        goes, this guard must go with it — not silently before it."""
        text = (CHECKS_DIR / "ARCH-020.md").read_text(encoding="utf-8")
        criteria = [ln for ln in text.splitlines() if ln.startswith("- [ ] ")]
        hit = [ln for ln in criteria if "SEP-2549" in ln and "cacheScope" in ln]
        assert len(hit) == 1, (
            "ARCH-020 must carry exactly one pass criterion binding cacheScope "
            "to the value set defined by SEP-2549"
        )
        assert '"public"' in hit[0] and '"private"' in hit[0]


class TestArch014SaysWhatAbsenceMeans:
    """An enforced check must not leave a third of the portfolio to reading.

    `ARCH-014` asks what a server retries, how fast and how long. Until
    2026-08-07 it never said what happens when a server retries *nothing*. On
    `advisory` that cost nothing. Since the promotion on 2026-08-03 the verdict
    decides production readiness — and a portfolio run found 15 of 43 servers
    with no retry path at all.

    The criteria pointed both ways. "Wiederholt wird auch bei Netzwerkfehlern
    und Timeouts" reads as a requirement to retry; the other eight are
    vacuously satisfied when nothing retries. Two auditors, two verdicts, same
    server, and nothing in the file to settle it.

    The check now settles it: absence is a `pass`, because every harm it names
    — retry storm, blocklist, load without a recipient, multiplicative
    stacking — presupposes a retry. What that leaves (a transient blip becomes
    a hard tool error) is loud and belongs to a different question.

    Three tests, and the third is the one with teeth: the rule is only safe as
    long as the transport level is counted as a retry path. A server with
    `HTTPTransport(retries=3)` and no loop of its own has the worst possible
    policy — no jitter, no `Retry-After`, no budget, written by nobody — and it
    is exactly the shape the absence rule would wave through if that criterion
    ever went missing.
    """

    @staticmethod
    def _text() -> str:
        return (CHECKS_DIR / "ARCH-014.md").read_text(encoding="utf-8")

    def test_the_check_has_a_section_on_absence(self):
        assert "## Was gilt, wenn gar nicht wiederholt wird" in self._text()

    def test_the_criteria_say_they_presuppose_a_retry(self):
        # Without this sentence the list reads as nine unconditional demands,
        # and the section above it becomes decoration.
        criteria = self._text().split("## Pass Criteria")[1].split("## Common")[0]
        assert "setzen voraus, dass überhaupt wiederholt wird" in criteria

    def test_the_transport_level_still_counts_as_a_retry_path(self):
        # The load-bearing half of the absence rule. If this criterion is ever
        # softened, "no loop" stops meaning "no retries" and the pass above
        # starts covering servers with an unwritten policy.
        criteria = [ln for ln in self._text().splitlines() if ln.startswith("- [ ] ")]
        hit = [ln for ln in criteria if "Transport-Retries" in ln]
        assert len(hit) == 1, (
            "ARCH-014 must carry exactly one pass criterion on transport-level "
            "retries — it is what keeps the absence rule from covering a "
            "server whose retry policy nobody wrote"
        )
        assert "ohne eigene Schleife" in hit[0], (
            "the criterion must say it also applies to a server without its "
            "own loop; that is the case the absence rule would otherwise pass"
        )


class TestFid006CarriesTheFieldNameHalf:
    """A merged check must keep what it absorbed, or the merge is a deletion.

    `DRIFT-007` existed for four days: field-name spelling as part of the
    contract, evidenced by BISTA changing `Schulgemeinde` to `schulgemeinde`
    and taking out four of six datasets while every unit test stayed green. It
    was withdrawn as a separate entry because it shared FID-006's cause, its
    test boundary and its subject — but withdrawing it moved the evidence into
    a file that has no test of its own.

    That is the risk this class exists for. Nothing in the catalogue's other
    guards can tell the difference between "FID-006 covers the spelling half"
    and "FID-006 is back to what it was before the merge": both parse, both
    count as one FID check, both keep the README numbers right. The half would
    disappear silently, and the incident behind it would be uncovered without
    anything turning red.

    Three properties, and the third is the one with teeth: normalising at the
    parse boundary is what makes this more than a rename of DRIFT-007 into a
    reference. Without that criterion the check is back to "confirm the shape",
    which the withdrawal argued was *not* sufficient for a source that changes
    its own spelling.
    """

    @staticmethod
    def _text() -> str:
        return (CHECKS_DIR / "FID-006.md").read_text(encoding="utf-8")

    def test_the_title_names_both_halves(self):
        # The title is what an auditor reads in the manifest and the report.
        # "Antwortstruktur bestätigen" alone sends them looking for a separate
        # check on field names, and there is none any more.
        head = self._text().split("---")[1]
        assert "Feldnamen" in head, (
            "FID-006's frontmatter title must name the field-name half; it is "
            "the only place the withdrawal of DRIFT-007 is visible to someone "
            "reading the manifest"
        )

    def test_the_evidence_that_moved_in_is_still_there(self):
        # A check without its finding is an opinion. This one is the reason
        # the field-name half is `high` and not `medium`.
        text = self._text()
        assert "Schulgemeinde" in text and "schulgemeinde" in text, (
            "the BISTA finding is the evidence for the field-name half; "
            "without it the criteria below rest on nothing"
        )

    def test_normalising_at_the_parse_boundary_is_a_criterion(self):
        # The load-bearing half. Confirming per endpoint gives a server that
        # reads a source with unstable spelling six correct checks that all
        # break on the next change — loudly instead of silently, which is
        # better, but still broken. If this criterion goes, the merge has
        # quietly reduced DRIFT-007 to a cross-reference.
        criteria = [ln for ln in self._text().splitlines() if ln.startswith("- [ ] ")]
        hit = [ln for ln in criteria if "normalisiert" in ln and "genau einer" in ln]
        assert len(hit) == 1, (
            "FID-006 must carry exactly one pass criterion requiring the "
            "spelling to be normalised at a single point when the source does "
            "not hold it stable — confirming alone was what DRIFT-007 argued "
            "is insufficient there"
        )
