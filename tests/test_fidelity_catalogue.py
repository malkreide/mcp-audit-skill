"""`fidelity/14` — die Zuordnungstabelle gegen den Katalog, jetzt lokal.

WARUM DIESE PRUEFUNG EIGENE TESTS BEKOMMT und die uebrigen fuenf der Suite
nicht: Bei den fuenf hat sich nur der PFAD geaendert; ihre Logik steht unter
`tools/gates/` und faehrt dort gegen Wegwerf-Baeume. Bei dieser hier hat sich
der EINSTIEG geaendert, und zwar der ganze: Sie las drei Umgebungsvariablen,
die ein Wochenplan-Workflow setzte, und liest jetzt zwei Pfade im eigenen
Baum. Was dabei wegfaellt, ist mehr Code als das, was bleibt — genau die
Sorte Umbau, nach der eine Pruefung noch gruen ist und nichts mehr prueft.

DER FIXTURE-BAUM IST KLEIN UND VOLLSTAENDIG ERFUNDEN. Ihn aus dem echten Baum
zu kopieren waere bequemer und falsch: Diese Tests muessen rot werden, wenn
die LOGIK bricht, nicht wenn der Katalog waechst. Der echte Baum wird genau
einmal befragt — vom Lauf der Suite selbst.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.harness import CheckFailed  # noqa: E402
from tools.suites.mcp_data_fidelity import catalogue  # noqa: E402
from tools.suites.mcp_data_fidelity.skill_doc import BASE, TABLE_HEADING  # noqa: E402

#: Zwei Regeln, drei Checks, zwei Kategorien — klein genug, um die Zahlen im
#: Kopf zu behalten, gross genug fuer jede Aussage der Pruefung.
KATALOG = {
    "FID-001.md": "---\nid: FID-001\n---\n\nrumpf\n",
    "FID-002.md": "---\nid: FID-002\nadoption: advisory\n---\n\nrumpf\n",
    "ARCH-003.md": "---\nid: ARCH-003\n---\n\nrumpf\n",
}

KOPFZEILE = (
    "Stand des Katalogs: 3 Checks in zwei Kategorien, davon zwei in der "
    "Kategorie `FID`."
)
EINSTUFUNG = (
    "**Zwei Checks dieser Tabelle sind `enforced`, nicht einer:** `FID-001` "
    "und `ARCH-003` fuehren kein `adoption`-Feld. `advisory` sind `FID-002`:"
)
TABELLE = (
    "| Regel | Check |\n"
    "|---|---|\n"
    "| 1 — erste Regel | [`FID-001`](/checks/FID-001.md) und "
    "[`ARCH-003`](/checks/ARCH-003.md) |\n"
    "| 2 — zweite Regel | [`FID-002`](/checks/FID-002.md) |\n"
)

SKILL = (
    "---\nname: mcp-data-fidelity\ndescription: kurz\n---\n\n"
    "## Regel 1 — erste\n\ntext\n\n"
    "## Regel 2 — zweite\n\ntext\n\n"
    f"{TABLE_HEADING}\n\n{KOPFZEILE}\n\n{EINSTUFUNG}\n\n{TABELLE}\n"
)

#: `GERMAN_NUMBERS` faengt bei «fuenf» an — die Herkunftsfassung brauchte
#: nichts darunter, weil die echte Tabelle nie kleiner war. Der Fixture-Baum
#: ist absichtlich winzig und darf diese Luecke nicht mitbringen, sonst
#: prueften alle Tests hier sie statt der Sache. Dass die Luecke SICHTBAR ist,
#: prueft `test_ANKER_ein_unbekanntes_zahlwort_…` weiter unten — und das ist
#: keine Erfindung dieses Tests: Beim Schreiben sind zwei Faelle hier genau
#: darueber rot geworden.
ZAHLWOERTER = {
    **catalogue.GERMAN_NUMBERS,
    "eins": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
}


@pytest.fixture(autouse=True)
def zwei_kennt_die_pruefung(monkeypatch):
    monkeypatch.setattr(catalogue, "GERMAN_NUMBERS", ZAHLWOERTER)


@pytest.fixture
def baum(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "checks").mkdir()
    for name, text in KATALOG.items():
        (tmp_path / "checks" / name).write_text(text, encoding="utf-8")
    (tmp_path / "checks" / "MANIFEST.txt").write_text(
        "".join(f"{name[:-3]}\n" for name in KATALOG), encoding="utf-8"
    )
    (tmp_path / BASE).mkdir(parents=True)
    (tmp_path / BASE / "SKILL.md").write_text(SKILL, encoding="utf-8")
    return tmp_path


def schreibe(baum: pathlib.Path, alt: str, neu: str) -> None:
    pfad = baum / BASE / "SKILL.md"
    text = pfad.read_text(encoding="utf-8")
    assert alt in text, f"Anker {alt!r} steht gar nicht im Fixture-Baum"
    pfad.write_text(text.replace(alt, neu), encoding="utf-8")


# --------------------------------------------------------------------------
# Der neue Einstieg — kein Netz, keine Umgebungsvariablen
# --------------------------------------------------------------------------


def test_der_gruene_fall(baum):
    ergebnis = catalogue.catalogue_drift(baum)
    assert "3 Checks" in ergebnis
    assert "2 `enforced`" in ergebnis


def test_ANKER_die_pruefung_braucht_keine_umgebungsvariable(baum, monkeypatch):
    """Der eigentliche Ertrag von Phase 4, als Zusage statt als Behauptung.

    Die Herkunftsfassung wurde rot, sobald `$CATALOGUE_MANIFEST`,
    `$CATALOGUE_CHECKS_DIR` oder `$CATALOGUE_COMMIT` fehlten — sie brauchte
    einen Workflow, der sie setzt. Bliebe hier eine solche Abhaengigkeit
    stehen, liefe die Pruefung im PR nie und niemand saehe es.
    """
    for name in ("CATALOGUE_MANIFEST", "CATALOGUE_CHECKS_DIR", "CATALOGUE_COMMIT"):
        monkeypatch.delenv(name, raising=False)
    assert catalogue.catalogue_drift(baum)


def test_ein_fehlender_katalog_ist_ein_befund(baum):
    (baum / "checks" / "MANIFEST.txt").unlink()
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "checks/MANIFEST.txt" in str(befund.value)


def test_ein_verlinkter_check_ohne_datei_ist_ein_toter_link(baum):
    (baum / "checks" / "ARCH-003.md").unlink()
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "ARCH-003" in str(befund.value)
    assert "toter Link" in str(befund.value)


def test_ein_manifest_ohne_check_ids_ist_ein_befund(baum):
    (baum / "checks" / "MANIFEST.txt").write_text("irgendwas\n", encoding="utf-8")
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "Liste von Check-IDs" in str(befund.value)


# --------------------------------------------------------------------------
# Die drei Gegenstaende: Zahlen, Identitaeten, Einstufung
# --------------------------------------------------------------------------


def test_eine_falsche_katalog_groesse_faellt_auf(baum):
    schreibe(baum, "3 Checks in", "4 Checks in")
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "Katalog-Groesse" in str(befund.value)


def test_eine_falsche_fid_zahl_faellt_auf(baum):
    schreibe(baum, "davon zwei in der Kategorie", "davon sechs in der Kategorie")
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "FID-Checks" in str(befund.value)


def test_ANKER_ein_neuer_fid_check_ohne_zeile_faellt_auf(baum):
    """Der Fall vom 5. August: `FID-006` ging auf, die Tabelle sagte weiter
    «kein Check»."""
    (baum / "checks" / "FID-009.md").write_text(
        "---\nid: FID-009\n---\n", encoding="utf-8"
    )
    (baum / "checks" / "MANIFEST.txt").write_text(
        "FID-001\nFID-002\nFID-009\nARCH-003\n", encoding="utf-8"
    )
    schreibe(baum, "3 Checks in", "4 Checks in")
    schreibe(baum, "davon zwei in der Kategorie", "davon drei in der Kategorie")
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "FID-009" in str(befund.value)
    assert "nicht verlinkt" in str(befund.value)


def test_ANKER_ein_zurueckgezogener_check_faellt_auf_obwohl_die_zahlen_stimmen(baum):
    """Der Fall vom 7. August, und der Grund, warum nicht nur Summen zaehlen.

    `DRIFT-007` wurde zurueckgezogen, `DRIFT-008` kam — die Kategorie behielt
    ihre Zahl, und die Tabelle zeigte auf eine Datei, die es nicht mehr gab.
    Hier dasselbe: `ARCH-003` wird zu `ARCH-004`, die Summe bleibt 3.
    """
    (baum / "checks" / "ARCH-003.md").rename(baum / "checks" / "ARCH-004.md")
    (baum / "checks" / "MANIFEST.txt").write_text(
        "FID-001\nFID-002\nARCH-004\n", encoding="utf-8"
    )
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "ARCH-003" in str(befund.value)


def test_ANKER_eine_falsche_einstufung_faellt_auf_obwohl_jede_id_existiert(baum):
    """Der Fall, den Zahlen UND Identitaeten beide durchgelassen haben."""
    (baum / "checks" / "FID-001.md").write_text(
        "---\nid: FID-001\nadoption: advisory\n---\n", encoding="utf-8"
    )
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "Einstufung FID-001" in str(befund.value)
    assert "`enforced`" in str(befund.value)


def test_ein_fehlendes_adoption_feld_gilt_als_enforced(baum):
    """Die Vorgabe des Katalogs — und der Grund, warum die Behauptung drueben
    ueberhaupt falsch werden konnte."""
    adoption = catalogue.read_adoption(baum, {"FID-001", "FID-002"})
    assert adoption == {"FID-001": "enforced", "FID-002": "advisory"}


def test_ein_verlinkter_check_ohne_einstufung_faellt_auf(baum):
    """Nichterwaehnung liest sich wie «nicht betroffen»."""
    schreibe(baum, " und `ARCH-003` fuehren", " fuehrt")
    schreibe(baum, "**Zwei Checks", "**Eins Checks")
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "ARCH-003" in str(befund.value)


def test_das_zahlwort_wird_gegen_die_eigene_aufzaehlung_gehalten(baum):
    schreibe(baum, "**Zwei Checks", "**Sechs Checks")
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "Einstufung: der Satz sagt" in str(befund.value)


# --------------------------------------------------------------------------
# Die Anker selbst — eine umformulierte Behauptung ist ein Befund
# --------------------------------------------------------------------------


def test_ANKER_eine_umformulierte_kopfzeile_ist_ein_befund(baum):
    """Sonst prueft die Pruefung die Zahlen stillschweigend nicht mehr."""
    schreibe(baum, "3 Checks in zwei Kategorien", "drei Checks, zwei Kategorien")
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "Katalogstand" in str(befund.value)


def test_ANKER_ein_umformulierter_einstufungssatz_ist_ein_befund(baum):
    schreibe(baum, "sind `enforced`, nicht einer:**", "blockieren:**")
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "Einstufung" in str(befund.value)


def test_ANKER_ein_unbekanntes_zahlwort_zeigt_auf_diese_datei_nicht_auf_den_katalog(
    baum, monkeypatch
):
    """Beim Umzug geschlossen — die Herkunftsfassung las hier still `None`.

    `GERMAN_NUMBERS.get()` machte aus einem unbekannten Wort ein `None`, und
    der Vergleich darunter meldete dann einen DRIFT: «Tabelle sagt 'vier'
    (None), Katalog hat 4». Der Befund zeigte damit auf den Katalog, waehrend
    der Fehler in dieser Datei lag.
    """
    monkeypatch.setattr(catalogue, "GERMAN_NUMBERS", {"dreizehn": 13})
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    text = str(befund.value)
    assert "GERMAN_NUMBERS" in text
    assert "kein Drift" in text
    assert "Katalog-Groesse" not in text


def test_ANKER_eine_verschwundene_tabellenueberschrift_ist_ein_befund(baum):
    schreibe(baum, TABLE_HEADING, "### Zuordnung")
    with pytest.raises(CheckFailed) as befund:
        catalogue.catalogue_drift(baum)
    assert "Anker" in str(befund.value)
