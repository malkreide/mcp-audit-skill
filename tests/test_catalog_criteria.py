"""Holds catalogue prose to what the tooling can actually record or check.

Two failure classes live here, both found in the same audit:

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
