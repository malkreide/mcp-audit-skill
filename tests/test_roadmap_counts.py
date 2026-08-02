"""Hält die `Stand:`-Zeile in docs/roadmap.md am Katalog fest.

Anders als `README.md` und `SKILL.md` darf diese Datei **nicht** als
Ganzes gegen den Katalog geprüft werden: Sie zitiert an mehreren Stellen
historische Stände («Der v0.5.0-Katalog mit 68 Checks in 8 Kategorien»,
«+14 Checks aus Anhang-PDF»), die richtig sind und richtig bleiben
sollen. Ein Test über alle Zahlen würde die Historie fälschlich
anmahnen — und wer ihn danach «grün macht», beschädigt sie.

Aktuell zu halten ist genau eine Zeile: die mit `Stand:` beginnende
Kopfzeile. Nur sie wird geprüft.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.parse_catalog import category_counts, parse_catalog

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"
ROADMAP = REPO_ROOT / "docs" / "roadmap.md"

# Stand: **79 Checks in 10 Kategorien.**
STAND_LINE = re.compile(
    r"^Stand:\s*\*\*(?P<checks>\d+) Checks in (?P<categories>\d+) Kategorien"
)


@pytest.fixture(scope="module")
def catalog():
    return parse_catalog(CHECKS_DIR)


class TestRoadmapStandLine:
    def test_stand_line_matches_catalog(self, catalog):
        lines = ROADMAP.read_text(encoding="utf-8").splitlines()
        matches = [m for m in (STAND_LINE.match(line) for line in lines) if m]
        assert len(matches) == 1, (
            "Genau eine `Stand:`-Zeile im Format "
            "«Stand: **NN Checks in NN Kategorien.**» erwartet"
        )
        m = matches[0]
        assert int(m.group("checks")) == len(catalog), (
            f"docs/roadmap.md nennt {m.group('checks')} Checks, "
            f"Katalog hat {len(catalog)}"
        )
        assert int(m.group("categories")) == len(category_counts(catalog)), (
            f"docs/roadmap.md nennt {m.group('categories')} Kategorien, "
            f"Katalog hat {len(category_counts(catalog))}"
        )
