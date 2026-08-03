"""Hält die Regel zur negativen Kontrolle in `SKILL.md` fest.

Die Regel entstand aus zwei Fehlmessungen der auditierenden Instanz selbst,
beide in einer Sitzung: ein `grep`-Muster, das nur `- uses:`-Zeilen traf und
deshalb nahelegte, drei CI-Dateien täten nichts (sie haben 9 bis 11 Schritte),
und ein `pip install` mit unterdrückter Ausgabe, dessen Fehlschlag dazu führte,
dass ein Versionsvergleich zweimal unter derselben Version lief.

Beide Ergebnisse waren plausibel. Genau darum ist Prosa allein zu wenig: Eine
Regel, die niemand einfordert, verschwindet beim nächsten Umbau des Dokuments.

**Jede Prüfung hier scheitert auch, wenn ihr Muster gar nichts findet.** Ein
Test, der nach einer Umformulierung ins Leere greift, prüft stillschweigend
nichts mehr — dieselbe Fehlerklasse, gegen die die Regel selbst gerichtet ist.
Diese Datei wendet also an, was sie einfordert.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL = REPO_ROOT / "SKILL.md"

ANCHOR = "#### Negative Kontrolle"


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def section(skill_text: str) -> str:
    """Der Abschnitt selbst, vom Anker bis zur nächsten `###`-Überschrift.

    Schlägt fehl, wenn der Anker fehlt — sonst würden alle folgenden Prüfungen
    auf einem leeren String bestehen und stillschweigend nichts mehr prüfen.
    """
    match = re.search(rf"^{re.escape(ANCHOR)}.*?(?=^### )", skill_text, re.M | re.S)
    assert match, (
        f"Anker {ANCHOR!r} fehlt in SKILL.md — umbenannt oder entfernt. "
        "Ohne ihn prüft diese Datei nichts mehr."
    )
    body = match.group(0)
    assert body.strip(), "Abschnitt ist leer"
    return body


class TestDieRegelStehtUndGrenztSichAb:
    def test_der_abschnitt_existiert_und_hat_substanz(self, section):
        assert len(section) > 800, (
            f"Abschnitt auf {len(section)} Zeichen geschrumpft — "
            "vermutlich ausgehöhlt statt überarbeitet"
        )

    def test_die_abgrenzung_zu_2_6_ist_benannt(self, section):
        """Die Regel ist nur dann neu, wenn sie sagt, wo §2.6 nicht greift.

        §2.6 behandelt das leere Ergebnis. Diese Regel behandelt das gefüllte,
        plausible, falsche. Fällt die Abgrenzung weg, liest sich der Abschnitt
        wie eine Wiederholung und wird beim nächsten Aufräumen gestrichen.
        """
        assert "§2.6" in section

    def test_die_regel_gilt_den_ad_hoc_kommandos_nicht_dem_katalog(self, section):
        assert "Ad-hoc" in section or "Wegwerf" in section

    def test_eine_null_wird_als_behauptung_benannt(self, section):
        """Der operative Kern: «0 Treffer» ist zweideutig."""
        assert re.search(r"Null ist eine Behauptung", section)


class TestDieBelegeStehenNamentlichDrin:
    """Eine Regel ohne den Fall, der sie erzwungen hat, wird wegargumentiert."""

    def test_der_grep_fehlschlag_ist_belegt(self, section):
        assert "- uses:" in section
        assert re.search(r"9 bis 11 Schritte", section)

    def test_der_unterdrueckte_install_ist_belegt(self, section):
        assert "pip install" in section
        assert "0.15.8" in section

    def test_die_unterdrueckungs_muster_sind_konkret_genannt(self, section):
        """Abstrakt formuliert erkennt sie im Alltag niemand wieder."""
        for muster in ("2>/dev/null", "|| true"):
            assert muster in section, f"{muster} nicht mehr genannt"

    def test_der_ausgangswert_der_katalogabdeckung_steht_drin(self, section):
        """12 von 98 — gemessen, nicht geschätzt, und als Ausgangswert markiert.

        Bewusst kein Gate: Ein Guard, der bei 86 von 97 Checks anschlägt, wird
        abgeschaltet, und die Zahl misst die Erwähnung, nicht die Praxis. Der
        Wert steht als Richtungsanzeige da, und der Test hält fest, dass er
        überhaupt beziffert ist.
        """
        assert re.search(r"12\s*von\s*98", section)


class TestDieChecklistFordertEsEin:
    def test_schritt_4_verlangt_die_negative_kontrolle(self, skill_text):
        checklist = re.search(
            r"^## Qualitätschecklist.*?(?=^## )", skill_text, re.M | re.S
        )
        assert checklist, "Qualitätschecklist nicht gefunden — Anker weg"
        body = checklist.group(0)
        assert "negative Kontrolle" in body, (
            "Die Checklist fordert die Regel nicht ein. Eine Regel, die vor "
            "Abschluss nicht abgehakt wird, wirkt nicht."
        )
        assert "2>/dev/null" in body

    def test_das_anti_pattern_ist_eingetragen_und_verlinkt(self, skill_text):
        anti = re.search(r"^## Anti-Patterns.*?(?=^---)", skill_text, re.M | re.S)
        assert anti, "Anti-Pattern-Abschnitt nicht gefunden — Anker weg"
        body = anti.group(0)
        assert "also stimmt die Zahl" in body
        # Der Link muss auf den Abschnitt oben zeigen; ein toter Anker macht
        # den Eintrag zur Sackgasse.
        assert "#negative-kontrolle" in body

    def test_die_anti_pattern_nummern_bleiben_lueckenlos(self, skill_text):
        anti = re.search(r"^## Anti-Patterns.*?(?=^---)", skill_text, re.M | re.S)
        nummern = [int(n) for n in re.findall(r"^(\d+)\. \*\*", anti.group(0), re.M)]
        assert nummern, "keine nummerierten Anti-Patterns gefunden"
        assert nummern == list(range(1, len(nummern) + 1)), (
            f"Nummerierung springt: {nummern}"
        )
