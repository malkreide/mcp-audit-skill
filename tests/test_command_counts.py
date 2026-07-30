# -*- coding: utf-8 -*-
"""Hält die Kategorienliste im Slash-Command am Katalog fest.

`.claude/commands/audit-mcp.md` nennt in der Einleitung die Kategorien
namentlich. Diese Zeile ist keine Dokumentation, sondern **Instruktion**:
Sie sagt Claude, aus welchen Kategorien der Katalog besteht, bevor
irgendein Check gelesen wird. Steht dort eine unvollständige Liste, läuft
das Audit mit einem zu kleinen Katalogbild los.

Genau das war der Fall. Bis v1.1.0 stand hier «`mcp-audit-skill v0.5.0`-
Katalog (7 Kategorien: ARCH, SDK, SEC, SCALE, OBS, HITL, CH)» — `OPS`
fehlte bereits zu v1.0.0-Zeiten, `FID` und `IDENT` kamen danach dazu.
Drei von zehn Kategorien waren unterschlagen, und nichts hat es gemeldet.

Von allen Doku-Zahlen im Repo ist diese die einzige, deren Fehler das
**Verhalten** ändert statt nur eine Anzeige. Deshalb prüft der Test die
Liste elementweise gegen den Katalog, nicht bloss ihre Länge.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.parse_catalog import category_counts, parse_catalog


REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"
COMMAND = REPO_ROOT / ".claude" / "commands" / "audit-mcp.md"

# «(10 Kategorien: ARCH, SDK, SEC, SCALE, OBS, HITL, CH, OPS, FID, IDENT;»
CATEGORY_LIST = re.compile(
    r"\((?P<count>\d+) Kategorien:\s*(?P<names>[A-Z][A-Z,\s]*[A-Z])\s*;"
)


@pytest.fixture(scope="module")
def catalog():
    return parse_catalog(CHECKS_DIR)


class TestCommandCategoryList:
    def test_category_list_matches_catalog(self, catalog):
        text = COMMAND.read_text(encoding="utf-8")
        matches = list(CATEGORY_LIST.finditer(text))
        assert len(matches) == 1, (
            "Genau eine Kategorienliste im Format «(N Kategorien: A, B, C;» "
            f"erwartet, gefunden: {len(matches)}"
        )
        m = matches[0]
        listed = [n.strip() for n in m.group("names").split(",")]
        expected = set(category_counts(catalog))

        assert len(listed) == len(set(listed)), f"Doppelte Einträge: {listed}"
        assert set(listed) == expected, (
            "Kategorienliste im Slash-Command weicht vom Katalog ab — "
            f"fehlen: {sorted(expected - set(listed))}, "
            f"zuviel: {sorted(set(listed) - expected)}"
        )
        assert int(m.group("count")) == len(expected), (
            f"Der Command nennt {m.group('count')} Kategorien, "
            f"listet aber {len(listed)} und der Katalog hat {len(expected)}"
        )
