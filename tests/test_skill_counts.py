# -*- coding: utf-8 -*-
"""Hält die Zahlen in SKILL.md am Katalog fest.

Gegenstück zu `test_readme_counts.py`. `SKILL.md` führt dieselbe
Kategorien-Übersicht in einem anderen Format: eine Spalte mit dem
erwarteten Bereich («Typische Anzahl Checks», etwa `4–6`) und eine mit
dem Ist-Stand (`5 / 5 ✅`). Geprüft wird beides — der Ist-Stand gegen den
Katalog, der Bereich auf Plausibilität gegenüber dem Ist-Stand.

Bewusst **nicht** geprüft werden die Schätzwerte in der Prosa
(«~50 Checks», «~15–20 Checks» in Schritt 3): Sie beziffern, wie viele
Checks nach dem Applicability-Filter typischerweise übrig bleiben, nicht
die Katalog-Grösse. Sie hängen am Profil, nicht am Katalog, und eine
Bindung an `len(catalog)` wäre schlicht falsch.

Ebenso ausgenommen ist die Gesamt-Schätzung `~75` in der Total-Zeile:
Sie summiert die Bereichs-Spalte, nicht den Bestand. Geprüft wird
deshalb nur, dass sie innerhalb der Summe aller Bereiche liegt.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.parse_catalog import category_counts, parse_catalog


REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"
SKILL = REPO_ROOT / "SKILL.md"

# SKILL.md schreibt die Anzahl Kategorien aus.
NUMBER_WORDS = {
    1: "eine", 2: "zwei", 3: "drei", 4: "vier", 5: "fünf",
    6: "sechs", 7: "sieben", 8: "acht", 9: "neun", 10: "zehn",
    11: "elf", 12: "zwölf",
}

# | `IDENT` | Custom — … | 4–6 | 5 / 5 ✅ |
CATEGORY_ROW = re.compile(
    r"^\|\s*`(?P<code>[A-Z]+)`\s*\|[^|]*\|"
    r"\s*(?P<lo>\d+)\s*[–-]\s*(?P<hi>\d+)\s*\|"
    r"\s*(?P<ist>\d+)\s*/\s*(?P<soll>\d+)\s*✅?\s*\|\s*$"
)
TOTAL_ROW = re.compile(
    r"^\|\s*\*\*Total\*\*\s*\|[^|]*\|"
    r"\s*\*\*~?(?P<estimate>\d+)\*\*\s*\|"
    r"\s*\*\*(?P<ist>\d+)\s*/\s*(?P<soll>\d+)\s*✅?\s*\*\*\s*\|\s*$"
)
# «79 Checks in zehn Kategorien» — ohne führende Tilde, die eine
# Schätzung markiert. Die Trenner sind `\s+`, nicht ein Leerzeichen: Prosa
# bricht um, und ein Muster mit hartem Leerzeichen prüft die Formatierung
# statt den Satz (SKILL.md §4.1).
INTRO_SIZE = re.compile(
    r"(?<!~)\b(?P<count>\d+)\s+Checks\s+in\s+(?P<word>\w+)\s+Kategorien"
)

# «### 2.1 Elf Kategorien» — die Abschnitts-Überschrift schreibt die Anzahl
# ebenfalls aus. Sie wurde bisher nicht geprüft und stand nach der Ergänzung
# der Kategorie DRIFT auf «Zehn», während die Tabelle darunter elf Zeilen
# hatte und das Intro «elf» sagte. Eine Überschrift ist die Zeile, die beim
# Überfliegen gelesen wird — sie darf nicht als Einzige veralten.
HEADING_SIZE = re.compile(
    r"^#{2,4}\s+[\d.]+\s+(?P<word>[A-Za-zÄÖÜäöü]+)\s+Kategorien\s*$"
)


@pytest.fixture(scope="module")
def skill_lines() -> list[str]:
    return SKILL.read_text(encoding="utf-8").splitlines()


@pytest.fixture(scope="module")
def catalog():
    return parse_catalog(CHECKS_DIR)


def _category_rows(lines):
    return [m for m in (CATEGORY_ROW.match(line) for line in lines) if m]


def _prose_lines(lines):
    """Fliesstext ohne Tabellenzeilen — dieselbe Auswahl wie der Zeilen-Scan."""
    return [line for line in lines if not line.lstrip().startswith("|")]


def _flat(lines) -> str:
    """Fliesstext zu einer Zeile: jede Whitespace-Folge wird ein Leerzeichen."""
    return re.sub(r"\s+", " ", " ".join(_prose_lines(lines))).strip()


class TestSkillMatchesCatalog:
    def test_intro_states_catalog_size(self, skill_lines, catalog):
        total = len(catalog)
        expected_word = NUMBER_WORDS[len(category_counts(catalog))]
        found = [
            (lineno, m)
            for lineno, line in enumerate(skill_lines, start=1)
            if not line.lstrip().startswith("|")
            for m in INTRO_SIZE.finditer(line)
        ]
        assert found, "Keine Angabe «NN Checks in <wort> Kategorien» in SKILL.md gefunden"
        for lineno, m in found:
            assert int(m.group("count")) == total, (
                f"SKILL.md:{lineno} nennt {m.group('count')} Checks, Katalog hat {total}"
            )
            assert m.group("word").lower() == expected_word, (
                f"SKILL.md:{lineno} nennt «{m.group('word')} Kategorien», "
                f"Katalog hat {len(category_counts(catalog))} ({expected_word})"
            )

    def test_no_count_claim_hides_in_a_line_break(self, skill_lines):
        """Der Zeilen-Scan darf keine Behauptung übersehen, die umbricht.

        `test_intro_states_catalog_size` liest zeilenweise, weil es die
        Zeilennummer melden will. Genau das ist der blinde Fleck aus
        SKILL.md §4.1: Bricht «86 Checks in elf Kategorien» zwischen zwei
        Wörtern um, findet der Scan sie nicht — und eine veraltete Zahl
        stünde ungeprüft im Dokument, ohne dass irgendein Test rot wird.

        Deshalb dieselbe Suche ein zweites Mal auf dem geglätteten Text.
        Weniger Treffer im Zeilen-Scan heisst: mindestens eine Angabe
        versteckt sich in einem Umbruch.
        """
        per_line = sum(
            1 for line in _prose_lines(skill_lines) for _ in INTRO_SIZE.finditer(line)
        )
        flattened = len(INTRO_SIZE.findall(_flat(skill_lines)))

        assert flattened >= 1, (
            "Keine Angabe «NN Checks in <wort> Kategorien» im geglätteten "
            "Text — dieser Test prüft sonst stillschweigend nichts mehr."
        )
        assert per_line == flattened, (
            f"{flattened - per_line} Angabe(n) «NN Checks in <wort> Kategorien» "
            f"laufen in SKILL.md über einen Zeilenumbruch und werden vom "
            f"Zeilen-Scan nicht geprüft. Satz auf eine Zeile ziehen."
        )

    def test_section_heading_states_category_count(self, skill_lines, catalog):
        """Die Abschnitts-Überschrift muss dieselbe Anzahl nennen wie das Intro.

        Regressionsschutz: Nach der Ergänzung von `DRIFT` blieb «### 2.1 Zehn
        Kategorien» stehen, obwohl die Tabelle elf Zeilen hatte. Die
        Intro-Zeile war korrekt und wurde geprüft — die Überschrift nicht.
        """
        expected_word = NUMBER_WORDS[len(category_counts(catalog))]
        found = [
            (lineno, m)
            for lineno, line in enumerate(skill_lines, start=1)
            if (m := HEADING_SIZE.match(line))
        ]
        assert found, (
            "Keine Überschrift «<Wort> Kategorien» in SKILL.md gefunden — "
            "wurde sie umbenannt? Dann gehört das Muster nachgezogen, sonst "
            "prüft dieser Test stillschweigend nichts mehr."
        )
        for lineno, m in found:
            assert m.group("word").lower() == expected_word, (
                f"SKILL.md:{lineno} nennt «{m.group('word')} Kategorien», "
                f"Katalog hat {len(category_counts(catalog))} ({expected_word})"
            )

    def test_category_table_covers_catalog(self, skill_lines, catalog):
        rows = {m.group("code") for m in _category_rows(skill_lines)}
        assert rows, "Kategorien-Tabelle in SKILL.md nicht gefunden"
        assert rows == set(category_counts(catalog))

    def test_category_table_actual_counts(self, skill_lines, catalog):
        counts = category_counts(catalog)
        for m in _category_rows(skill_lines):
            code = m.group("code")
            ist, soll = int(m.group("ist")), int(m.group("soll"))
            assert ist == soll, (
                f"`{code}`: Ist-Stand {ist} / {soll} ist in sich widersprüchlich"
            )
            assert ist == counts[code], (
                f"`{code}` steht in SKILL.md auf {ist}, Katalog hat {counts[code]}"
            )

    def test_category_ranges_contain_actual(self, skill_lines, catalog):
        """Die Bereichs-Spalte muss den Ist-Stand einschliessen.

        Wächst eine Kategorie über ihren dokumentierten Bereich hinaus,
        ist nicht der Katalog falsch, sondern die Erwartung veraltet —
        genau das soll auffallen.
        """
        counts = category_counts(catalog)
        for m in _category_rows(skill_lines):
            code = m.group("code")
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            assert lo <= hi, f"`{code}`: Bereich {lo}–{hi} ist verdreht"
            assert lo <= counts[code] <= hi, (
                f"`{code}`: Katalog hat {counts[code]} Checks, dokumentierter "
                f"Bereich ist {lo}–{hi} — Bereich anpassen oder Kategorie prüfen"
            )

    def test_total_row(self, skill_lines, catalog):
        matches = [m for m in (TOTAL_ROW.match(line) for line in skill_lines) if m]
        assert len(matches) == 1, "Genau eine **Total**-Zeile in SKILL.md erwartet"
        m = matches[0]
        assert int(m.group("ist")) == len(catalog)
        assert int(m.group("soll")) == len(catalog)

        # Die Schätzung summiert die Bereichs-Spalte und darf nicht mit dem
        # Bestand verwechselt werden — geprüft wird nur ihre Plausibilität.
        rows = _category_rows(skill_lines)
        lo_sum = sum(int(r.group("lo")) for r in rows)
        hi_sum = sum(int(r.group("hi")) for r in rows)
        estimate = int(m.group("estimate"))
        assert lo_sum <= estimate <= hi_sum, (
            f"Total-Schätzung ~{estimate} liegt ausserhalb der Summe der "
            f"Bereiche ({lo_sum}–{hi_sum})"
        )
