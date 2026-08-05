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
