# -*- coding: utf-8 -*-
"""Hält die Zahlen in BEIDEN READMEs am Katalog fest.

Die Katalog-Zählungen leben an drei Orten: `checks/MANIFEST.txt`, den
Lock-Tests in `test_parse_catalog.py` und der Prosa/den Tabellen in den
READMEs. Die ersten beiden prüft CI seit je — die dritte war bis
hierher ungesichert, und genau dort ist beim Hinzufügen von `IDENT` die
Aktualisierung ausgeblieben. Ein Wert, den nichts erzwingt, driftet.

Seit der Aufteilung in ein englisches `README.md` und ein deutsches
`README.de.md` läuft dieser Test über **beide** Dateien. Das ist kein
Komfort, sondern Notwendigkeit: Die Prosa-Muster waren deutsch
(«Kategorien», «Checks aus»), und eine Übersetzung allein hätte sie
tatenlos gemacht — die Tests wären grün geblieben, während sie nichts
mehr prüfen. Genau die Fehlerklasse, gegen die `FID` und `DRIFT` im
Katalog stehen. Deshalb hat jede Sprache eigene Prosa-Muster, und eine
neue Fassung braucht hier einen Eintrag, sonst prüft sie niemand.

Geprüft wird pro Datei:

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

# Platzhalter für «keine Checks dieser Severity» in den Tabellen.
DASH = "—"

# Prosa-Muster je Sprachfassung. Die strukturellen Muster (Tabellen,
# Badges) sind sprachneutral und stehen weiter unten einmalig.
#
# Wer eine Sprachfassung hinzufügt, trägt sie hier ein. Fehlt der Eintrag,
# prüft diese Datei sie nicht — und das fällt nicht auf, weil ein Test,
# der nichts findet, grün ist. `test_every_readme_is_covered` macht genau
# das zum Fehler.
PROSE = {
    "README.md": {
        "checks": re.compile(r"(\d+)\s+checks", re.IGNORECASE),
        "checks_trailing": re.compile(r"checks\s+out\s+of\s+(\d+)", re.IGNORECASE),
        "categories": re.compile(r"(\d+)\s+categories", re.IGNORECASE),
    },
    "README.de.md": {
        "checks": re.compile(r"(\d+)\s+Checks"),
        # Dieselbe Behauptung mit der Zahl **hinter** dem Wort: «anwendbaren
        # Checks aus 90». Das Muster mit der Zahl davor hat diese Form vier
        # Releases lang übersehen — die Zeile stand auf 86, während der
        # Katalog auf 90 gewachsen war. Kein fehlender Test, ein zu kurz
        # greifender.
        "checks_trailing": re.compile(r"Checks\s+aus\s+(\d+)"),
        "categories": re.compile(r"(\d+)\s+Kategorien"),
    },
}


@pytest.fixture(scope="module", params=sorted(PROSE))
def readme(request) -> tuple[str, list[str]]:
    """Name und Zeilen einer Sprachfassung — jeder Test läuft über beide."""
    name = request.param
    path = REPO_ROOT / name
    assert path.is_file(), f"{name} fehlt"
    return name, path.read_text(encoding="utf-8").splitlines()


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
# Provenance-Zeile eines eigenen Layers: «8 Checks (`CH-*`)».
# Case-insensitive, damit eine Fassung, die «checks» klein schreibt, nicht
# stillschweigend ungeprüft bleibt. Die Einzahl ist mitgemustert: Ein Layer
# mit genau einem Check schreibt «1 Check (`DEP-*`)», und ein Muster, das
# nur den Plural kennt, hätte ausgerechnet den neuesten Layer ungeprüft
# durchgelassen — sichtbar erst, wenn er wächst.
LAYER_ROW = re.compile(
    r"(?P<count>\d+)\s+Checks?\s+\(`(?P<prefix>[A-Z]+)-\*`\)", re.IGNORECASE
)
BADGE_URL = re.compile(r"img\.shields\.io/badge/Checks-(\d+)-")
BADGE_ALT = re.compile(r"!\[Checks:\s*(\d+)\]")


def test_every_readme_is_covered():
    """Jede README-Sprachfassung im Repo hat Prosa-Muster in `PROSE`.

    Ohne diesen Test verschwindet eine neue Fassung lautlos aus der
    Prüfung: Die Fixture parametrisiert über `PROSE`, nicht über das
    Dateisystem, und was dort nicht steht, wird nie gelesen.
    """
    on_disk = {p.name for p in REPO_ROOT.glob("README*.md")}
    assert on_disk == set(PROSE), (
        f"README-Fassungen ohne Prosa-Muster: {sorted(on_disk - set(PROSE))}; "
        f"Muster ohne Datei: {sorted(set(PROSE) - on_disk)}"
    )


class TestReadmeMatchesCatalog:
    def test_badge_shows_total(self, readme, catalog):
        name, lines = readme
        text = "\n".join(lines)
        total = len(catalog)
        urls = [int(n) for n in BADGE_URL.findall(text)]
        alts = [int(n) for n in BADGE_ALT.findall(text)]
        assert urls, f"Checks-Badge in {name} nicht gefunden"
        assert alts, f"Alt-Text des Checks-Badge in {name} nicht gefunden"
        assert set(urls) == {total}, (
            f"{name}: Badge-URL zeigt {urls}, Katalog hat {total}"
        )
        assert set(alts) == {total}, (
            f"{name}: Badge-Alt-Text zeigt {alts}, Katalog hat {total}"
        )

    def test_prose_mentions_match_catalog(self, readme, catalog):
        """Jede Prosa-Erwähnung «NN Checks» / «NN Kategorien» muss stimmen.

        Tabellenzeilen sind ausgenommen — die Provenance-Tabelle nennt
        historische Teilmengen, die separat geprüft werden.
        """
        name, lines = readme
        patterns = PROSE[name]
        total = len(catalog)
        n_categories = len(category_counts(catalog))
        for lineno, line in enumerate(lines, start=1):
            if line.lstrip().startswith("|"):
                continue
            for n in patterns["checks"].findall(line):
                assert int(n) == total, (
                    f"{name}:{lineno} nennt {n} Checks, Katalog hat {total}: {line.strip()!r}"
                )
            for n in patterns["checks_trailing"].findall(line):
                assert int(n) == total, (
                    f"{name}:{lineno} nennt {n} Checks, Katalog hat {total}: {line.strip()!r}"
                )
            for n in patterns["categories"].findall(line):
                assert int(n) == n_categories, (
                    f"{name}:{lineno} nennt {n} Kategorien, Katalog hat "
                    f"{n_categories}: {line.strip()!r}"
                )

    def test_prose_patterns_actually_match_something(self, readme):
        """Ein Muster, das nie greift, prüft nichts — und ist grün dabei.

        Nach der Übersetzung war genau das die Gefahr: deutsche Muster auf
        englischem Text. Jedes Muster muss in seiner Fassung mindestens
        einmal zutreffen.
        """
        name, lines = readme
        text = "\n".join(ln for ln in lines if not ln.lstrip().startswith("|"))
        for key, pattern in PROSE[name].items():
            assert pattern.search(text), (
                f"{name}: Muster {key} ({pattern.pattern!r}) trifft nirgends zu — "
                "die Prüfung liefe ins Leere"
            )

    def test_category_table_counts(self, readme, catalog):
        name, lines = readme
        rows = {
            m.group("code"): int(m.group("count"))
            for m in (CATEGORY_ROW.match(line) for line in lines)
            if m
        }
        assert rows, f"Kategorien-Tabelle in {name} nicht gefunden"
        assert rows == category_counts(catalog)

    def test_category_table_severity_profiles(self, readme, catalog):
        name, lines = readme
        actual = _severity_by_category(catalog)
        seen = set()
        for line in lines:
            m = CATEGORY_ROW.match(line)
            if not m:
                continue
            code = m.group("code")
            seen.add(code)
            assert _parse_severity_profile(m.group("severity")) == actual[code], (
                f"Severity-Profil für `{code}` in {name} weicht vom Katalog ab "
                f"(Katalog: {actual[code]})"
            )
        assert seen == set(actual), (
            f"{name}: Kategorien-Tabelle deckt nicht alle Kategorien ab"
        )

    def test_total_row(self, readme, catalog):
        name, lines = readme
        matches = [m for m in (TOTAL_ROW.match(line) for line in lines) if m]
        assert len(matches) == 1, f"{name}: genau eine **Total**-Zeile erwartet"
        m = matches[0]
        assert int(m.group("count")) == len(catalog)
        assert _parse_severity_profile(m.group("severity")) == severity_counts(catalog)

    def test_layer_rows_match_category_counts(self, readme, catalog):
        name, lines = readme
        counts = category_counts(catalog)
        seen = set()
        for line in lines:
            for m in LAYER_ROW.finditer(line):
                prefix = m.group("prefix")
                seen.add(prefix)
                assert int(m.group("count")) == counts[prefix], (
                    f"{name}: Provenance-Tabelle nennt {m.group('count')} Checks für "
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
            f"{name}: Provenance-Tabelle nennt keine Zeile für: {sorted(custom - seen)}"
        )
