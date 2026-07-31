# -*- coding: utf-8 -*-
"""Hält die Zahlen in README.md am Katalog fest.

Die Katalog-Zählungen leben an drei Orten: `checks/MANIFEST.txt`, den
Lock-Tests in `test_parse_catalog.py` und der Prosa/den Tabellen in
`README.md`. Die ersten beiden prüft CI seit je — die dritte war bis
hierher ungesichert, und genau dort ist beim Hinzufügen von `IDENT` die
Aktualisierung ausgeblieben. Ein Wert, den nichts erzwingt, driftet.

Dieser Test liest die Zahlen aus README.md und vergleicht sie gegen den
tatsächlichen Katalog. Er prüft:

1. Badge und Alt-Text (`Checks-NN`)
2. Prosa-Erwähnungen (`NN Checks`, `NN Kategorien`) ausserhalb von Tabellen
3. die Kategorien-Tabelle — Anzahl **und** Severity-Profil pro Kategorie
4. die Total-Zeile derselben Tabelle
5. die Layer-Zeilen der Provenance-Tabelle (`N Checks (`XYZ-*`)`)

Nicht geprüft werden die beiden PDF-Zeilen der Provenance-Tabelle
(«54 Checks (v0.1–v0.4)», «14 Checks (v0.5)»): Sie beschreiben die
historische Herkunft, nicht den aktuellen Bestand, und überlappen mit den
Layer-Zeilen — ihre Summe ergibt bewusst nicht das Total.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pytest

from tools.parse_catalog import category_counts, parse_catalog, severity_counts


REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"
README = REPO_ROOT / "README.md"

# Platzhalter für «keine Checks dieser Severity» in den Tabellen.
DASH = "—"


@pytest.fixture(scope="module")
def readme_lines() -> list[str]:
    return README.read_text(encoding="utf-8").splitlines()


@pytest.fixture(scope="module")
def catalog():
    return parse_catalog(CHECKS_DIR)


def _severity_by_category(catalog) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for fm in catalog.values():
        out[fm["category"]][fm["severity"]] += 1
    return {cat: dict(sev) for cat, sev in out.items()}


def _parse_severity_profile(cell: str) -> dict[str, int]:
    """«2 critical · 3 high · 7 medium» -> {'critical': 2, 'high': 3, ...}

    `—` steht für eine Severity ohne Checks und wird — wie eine ganz
    fehlende Angabe — als Null gelesen.
    """
    parsed: dict[str, int] = {}
    for token in cell.split("·"):
        token = token.strip().strip("*").strip()
        if not token or token == DASH:
            continue
        m = re.fullmatch(r"(\d+)\s+(critical|high|medium|low)", token)
        assert m, f"Unlesbares Severity-Token in README-Tabelle: {token!r}"
        parsed[m.group(2)] = int(m.group(1))
    return parsed


# Tabellenzeile der Kategorien-Tabelle:
# | `ARCH` | Bereich | Quelle | 12 | 2 critical · 3 high · 7 medium |
CATEGORY_ROW = re.compile(
    r"^\|\s*`(?P<code>[A-Z]+)`\s*\|[^|]*\|[^|]*\|\s*(?P<count>\d+)\s*\|"
    r"\s*(?P<severity>[^|]*?)\s*\|\s*$"
)
TOTAL_ROW = re.compile(
    r"^\|\s*\*\*Total\*\*\s*\|[^|]*\|[^|]*\|\s*\*\*(?P<count>\d+)\*\*\s*\|"
    r"\s*\*\*(?P<severity>[^|]*?)\*\*\s*\|\s*$"
)
# Provenance-Zeile eines eigenen Layers: «8 Checks (`CH-*`)»
LAYER_ROW = re.compile(r"(?P<count>\d+)\s+Checks\s+\(`(?P<prefix>[A-Z]+)-\*`\)")

PROSE_CHECKS = re.compile(r"(\d+)\s+Checks")
# Dieselbe Behauptung mit der Zahl **hinter** dem Wort: «anwendbaren Checks
# aus 90». `PROSE_CHECKS` verlangt die Zahl davor und hat diese Form vier
# Releases lang übersehen — README.md:71 stand auf 86, während der Katalog
# auf 90 gewachsen war. Kein fehlender Test, ein zu kurz greifender.
PROSE_CHECKS_TRAILING = re.compile(r"Checks\s+aus\s+(\d+)")
PROSE_CATEGORIES = re.compile(r"(\d+)\s+Kategorien")
BADGE_URL = re.compile(r"img\.shields\.io/badge/Checks-(\d+)-")
BADGE_ALT = re.compile(r"!\[Checks:\s*(\d+)\]")


class TestReadmeMatchesCatalog:
    def test_badge_shows_total(self, readme_lines, catalog):
        text = "\n".join(readme_lines)
        total = len(catalog)
        urls = [int(n) for n in BADGE_URL.findall(text)]
        alts = [int(n) for n in BADGE_ALT.findall(text)]
        assert urls, "Checks-Badge in README.md nicht gefunden"
        assert alts, "Alt-Text des Checks-Badge in README.md nicht gefunden"
        assert set(urls) == {total}, f"Badge-URL zeigt {urls}, Katalog hat {total}"
        assert set(alts) == {total}, f"Badge-Alt-Text zeigt {alts}, Katalog hat {total}"

    def test_prose_mentions_match_catalog(self, readme_lines, catalog):
        """Jede Prosa-Erwähnung «NN Checks» / «NN Kategorien» muss stimmen.

        Tabellenzeilen sind ausgenommen — die Provenance-Tabelle nennt
        historische Teilmengen, die separat geprüft werden.
        """
        total = len(catalog)
        n_categories = len(category_counts(catalog))
        for lineno, line in enumerate(readme_lines, start=1):
            if line.lstrip().startswith("|"):
                continue
            for n in PROSE_CHECKS.findall(line):
                assert int(n) == total, (
                    f"README.md:{lineno} nennt {n} Checks, Katalog hat {total}: {line.strip()!r}"
                )
            for n in PROSE_CHECKS_TRAILING.findall(line):
                assert int(n) == total, (
                    f"README.md:{lineno} nennt {n} Checks, Katalog hat {total}: {line.strip()!r}"
                )
            for n in PROSE_CATEGORIES.findall(line):
                assert int(n) == n_categories, (
                    f"README.md:{lineno} nennt {n} Kategorien, Katalog hat "
                    f"{n_categories}: {line.strip()!r}"
                )

    def test_category_table_counts(self, readme_lines, catalog):
        rows = {
            m.group("code"): int(m.group("count"))
            for m in (CATEGORY_ROW.match(line) for line in readme_lines)
            if m
        }
        assert rows, "Kategorien-Tabelle in README.md nicht gefunden"
        assert rows == category_counts(catalog)

    def test_category_table_severity_profiles(self, readme_lines, catalog):
        actual = _severity_by_category(catalog)
        seen = set()
        for line in readme_lines:
            m = CATEGORY_ROW.match(line)
            if not m:
                continue
            code = m.group("code")
            seen.add(code)
            assert _parse_severity_profile(m.group("severity")) == actual[code], (
                f"Severity-Profil für `{code}` in README.md weicht vom Katalog ab "
                f"(Katalog: {actual[code]})"
            )
        assert seen == set(actual), "Kategorien-Tabelle deckt nicht alle Kategorien ab"

    def test_total_row(self, readme_lines, catalog):
        matches = [m for m in (TOTAL_ROW.match(line) for line in readme_lines) if m]
        assert len(matches) == 1, "Genau eine **Total**-Zeile erwartet"
        m = matches[0]
        assert int(m.group("count")) == len(catalog)
        assert _parse_severity_profile(m.group("severity")) == severity_counts(catalog)

    def test_layer_rows_match_category_counts(self, readme_lines, catalog):
        counts = category_counts(catalog)
        seen = set()
        for line in readme_lines:
            for m in LAYER_ROW.finditer(line):
                prefix = m.group("prefix")
                seen.add(prefix)
                assert int(m.group("count")) == counts[prefix], (
                    f"Provenance-Tabelle nennt {m.group('count')} Checks für "
                    f"`{prefix}-*`, Katalog hat {counts[prefix]}"
                )
        # Die eigenen Layer (Custom-Kategorien) müssen alle auftauchen —
        # sonst fehlt beim nächsten Layer wieder eine Zeile.
        custom = {
            fm["category"]
            for fm in catalog.values()
            if str(fm.get("pdf_ref", "")).strip().lower().startswith("custom")
        }
        assert custom <= seen, (
            f"Provenance-Tabelle nennt keine Zeile für: {sorted(custom - seen)}"
        )
