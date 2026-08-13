"""Hält die HARNESS-Zahlen in beiden READMEs an der Registry fest.

`test_readme_counts.py` prüft die Zahlen des KATALOGS — 120 Checks, 12
Kategorien. Seit der Zusammenführung nennen die READMEs eine zweite Sorte
Zahl, und beide heissen «Check»:

* der Katalog hat 120 — das, wogegen ein fremder Server auditiert wird
* die Harness fährt 37 — das, was dieses Repository gegen sich selbst hält

DER KONFLIKT WAR GEMESSEN UND IST DER GRUND FÜR DIESE DATEI. Beim Einbau der
Struktur-Übersicht schlug `test_prose_mentions_match_catalog` an: «README.md
nennt 37 Checks, Katalog hat 120». Der Guard hatte recht — nach seinem Muster
war das eine Behauptung über den Katalog.

Der bequeme Ausweg wäre gewesen, ihn Code-Blöcke überspringen zu lassen. Das
hätte eine echte Zusage abgeschaltet: Eine falsche 120 in einem Code-Block
wäre danach durchgegangen. Stattdessen ist das Wort im Text QUALIFIZIERT
(«37 harness checks» / «37 Harness-Checks»), womit das Katalog-Muster
(`\\d+\\s+Checks`) dort gar nicht mehr greift — und diese Datei legt die Zusage
daneben, die vorher fehlte. Unterm Strich wird mehr geprüft als zuvor, nicht
weniger.

37 UND NICHT 38, und das ist keine Schludrigkeit: `all_checks()` führt 38
Prüfungen, `audit/13` darunter ist aber `offline=False` — es hält das Git-Tag
gegen den CHANGELOG und hat ohne Remote nichts zu lesen. Ein Lauf ohne
`--include-network` fährt 37. Die READMEs nennen beide Zahlen, und dieser Test
hält beide.

Stdlib-only, kein Netz.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import tools.suites  # noqa: F401  — Import registriert alle Suiten
from tools.harness import all_checks

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Je Sprachfassung: die Überschrift des Abschnitts, das Muster für die
#: Gesamtzahl und die Spaltenüberschrift der Suiten-Tabelle. Wer eine Fassung
#: hinzufügt, trägt sie hier ein — `test_ANKER_jede_readme_fassung_ist_erfasst`
#: macht das Vergessen zum Fehler statt zum stillen Bestehen.
FASSUNGEN = {
    "README.md": {
        "heading": "### One harness, four suites",
        "offline": re.compile(r"\*\*(\d+)\s+harness checks\*\*"),
        "network": re.compile(r"and (\d+) with `--include-network`"),
        "mutations": re.compile(r"(\d+)\s+mutations"),
    },
    "README.de.md": {
        "heading": "### Eine Harness, vier Suiten",
        "offline": re.compile(r"\*\*(\d+)\s+Harness-Checks\*\*"),
        "network": re.compile(r"mit\s+`--include-network`\s+(\d+)"),
        "mutations": re.compile(r"(\d+)\s+Mutationen"),
    },
}

#: Eine Zeile der Suiten-Tabelle: | `audit` | … | 15 | — |
TABELLENZEILE = re.compile(
    r"^\|\s*`(?P<suite>\w+)`\s*\|[^|]*\|\s*(?P<checks>\d+)\s*\|", re.M
)


@pytest.fixture(scope="module", params=sorted(FASSUNGEN))
def fassung(request) -> tuple[str, str, dict]:
    name = request.param
    pfad = REPO_ROOT / name
    assert pfad.is_file(), f"{name} fehlt"
    return name, pfad.read_text(encoding="utf-8"), FASSUNGEN[name]


def _abschnitt(name: str, text: str, heading: str) -> str:
    """Der Abschnitt bis zur nächsten Überschrift.

    Fehlt die Überschrift, ist das ein FEHLER und kein stilles Durchwinken:
    Dieser Test hätte sonst nichts mehr, wogegen er prüft.
    """
    treffer = re.search(
        rf"^{re.escape(heading)}\n(.*?)(?=^#{{2,3}} |\Z)", text, re.M | re.S
    )
    if treffer is None:
        raise AssertionError(
            f"{name}: Abschnitt '{heading}' nicht gefunden — der Anker ist weg "
            "oder umbenannt, und dieser Test prüfte sonst nichts mehr."
        )
    return treffer.group(1)


def test_die_offline_zahl_stimmt(fassung):
    name, text, muster = fassung
    erwartet = len(all_checks(offline_only=True))
    gefunden = muster["offline"].findall(text)
    assert gefunden, (
        f"{name}: keine qualifizierte Angabe der Harness-Zahl gefunden. "
        "Ohne sie prüft dieser Test nichts — und das Katalog-Muster greift "
        "auf eine unqualifizierte Angabe fälschlich zu."
    )
    for n in gefunden:
        assert int(n) == erwartet, (
            f"{name} nennt {n} Harness-Checks, die Registry führt {erwartet} offline."
        )


def test_die_netz_zahl_stimmt(fassung):
    """Die Gesamtzahl inklusive der Prüfungen, die ein Remote brauchen."""
    name, text, muster = fassung
    erwartet = len(all_checks())
    gefunden = muster["network"].findall(text)
    assert gefunden, f"{name}: keine Angabe zur `--include-network`-Zahl."
    for n in gefunden:
        assert int(n) == erwartet, (
            f"{name} nennt {n} Checks mit Netz, die Registry führt {erwartet}."
        )


def test_die_mutationszahl_stimmt(fassung):
    """Der Baum nennt die Mutationszahl. Nichts hielt sie bisher.

    ZWEIMAL IN EINER SITZUNG KORRIGIERT, beide Male von Hand: erst 98 statt
    101 im MERGE-PLAN, dann dieselbe Zahl im Suite-Docstring. Eine Zahl, die
    eine ZUSAGE ist, gehört an die Quelle gebunden.

    Die Test-Anzahl daneben ist ausdrücklich NICHT gebunden und steht deshalb
    gar nicht mehr im Baum: Sie ändert sich mit jedem PR, der einen Test
    hinzufügt, und ein Gate, das bei jeder fremden Änderung rot wird, ist nach
    zwei Wochen abgeschaltet. Zusage binden, Beiwerk weglassen.
    """
    name, text, muster = fassung
    from tests.suites import mcp_data_fidelity, mcp_data_source_probe
    from tests.suites import mcp_transport_hardening as transport

    erwartet = (
        len(mcp_data_source_probe.MUTATIONS)
        + len(mcp_data_fidelity.MUTATIONS)
        + len(transport.MUTATIONS)
    )
    gefunden = muster["mutations"].findall(text)
    assert gefunden, (
        f"{name}: nennt keine Mutationszahl — leeres Ergebnis ist ein Befund, "
        "kein Bestehen."
    )
    for n in gefunden:
        assert int(n) == erwartet, (
            f"{name} nennt {n} Mutationen, die Suiten führen {erwartet}."
        )


def test_die_suiten_tabelle_stimmt_je_suite(fassung):
    """Nicht nur die Summe — die VERTEILUNG.

    Eine Summe kann stimmen, während zwei Zeilen gegeneinander verschoben
    sind. Das ist dieselbe Fehlerklasse, für die `check_reported_numbers.py`
    je Status vergleicht statt nur das Total.
    """
    name, text, muster = fassung
    abschnitt = _abschnitt(name, text, muster["heading"])
    zeilen = {
        m.group("suite"): int(m.group("checks"))
        for m in TABELLENZEILE.finditer(abschnitt)
    }
    assert zeilen, (
        f"{name}: die Suiten-Tabelle unter '{muster['heading']}' ist leer oder "
        "hat ihre Form geändert — leeres Ergebnis ist ein Befund, kein Bestehen."
    )

    erwartet: dict[str, int] = {}
    for check in all_checks(offline_only=True):
        erwartet[check.suite] = erwartet.get(check.suite, 0) + 1

    assert zeilen == erwartet, (
        f"{name}: die Suiten-Tabelle nennt {zeilen}, die Registry führt "
        f"{erwartet} (offline)."
    )


def test_ANKER_jede_readme_fassung_ist_erfasst():
    """Eine Sprachfassung ohne Eintrag prüft niemand — und ist grün dabei.

    Wörtlich die Vorkehrung aus `test_readme_counts.py`, aus demselben Anlass:
    Die Muster sind sprachabhängig, eine Übersetzung allein macht sie tatenlos.
    """
    vorhanden = {p.name for p in REPO_ROOT.glob("README*.md")}
    fehlend = vorhanden - set(FASSUNGEN)
    assert not fehlend, (
        f"README-Fassungen ohne Eintrag in FASSUNGEN: {sorted(fehlend)}. "
        "Ohne Eintrag prüft diese Datei sie nicht, und das fällt nicht auf."
    )
