"""Die kontextgebundenen Gates: `release` (G16) und `repo_meta` (G13).

Beide pruefen eine Behauptung, die AUSSERHALB der Arbeitskopie lebt — der
Git-Tag und die GitHub-Description. Kein Commit aendert sie, kein Test der
Arbeitskopie erreicht sie, also driften sie.

Getestet wird hier die REINE Logik: `assert_tag_matches` nimmt den Tag als
Argument, `assert_description_matches` die Description. Beide brauchen weder
Umgebung noch Netz — genau deshalb sind sie ueberhaupt testbar, und genau
deshalb sind sie von ihrem Umgebungs-Aufsatz getrennt.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gates.release import assert_tag_matches  # noqa: E402
from tools.gates.repo_meta import (  # noqa: E402
    as_number,
    assert_description_matches,
)
from tools.harness import CheckFailed  # noqa: E402

HEADING = "## [v1.7.0] — 2026-01-01"


# --------------------------------------------------------------------------
# G16 — der Tag
# --------------------------------------------------------------------------


@pytest.mark.parametrize("tag", ["v1.7.0", "1.7.0"])
def test_ein_passender_tag_ist_gruen(tag):
    assert "1.7.0" in assert_tag_matches(tag, "1.7.0", 3, HEADING)


def test_ANKER_ein_leerer_tag_ist_ein_befund_kein_bestehen():
    """Der stille Fall, und deshalb der erste im Code.

    Ein Vergleich gegen "" ergaebe dieselbe Meldung wie ein falscher Tag und
    fuehrte in die Irre — die Pruefung hat dann gar nicht stattgefunden.
    """
    with pytest.raises(CheckFailed) as befund:
        assert_tag_matches("", "1.7.0", 3, HEADING)
    assert "leer" in str(befund.value)
    assert "nicht stattgefunden" in str(befund.value)


def test_ein_tag_der_keine_version_ist_wird_abgelehnt():
    with pytest.raises(CheckFailed) as befund:
        assert_tag_matches("vorschau", "1.7.0", 3, HEADING)
    assert "vX.Y.Z" in str(befund.value)


def test_ein_abweichender_tag_nennt_beide_zahlen():
    with pytest.raises(CheckFailed) as befund:
        assert_tag_matches("v1.6.0", "1.7.0", 3, HEADING)
    text = str(befund.value)
    assert "1.6.0" in text and "1.7.0" in text
    # Der CHANGELOG ist die Quelle, nicht der Tag — das soll dastehen.
    assert "CHANGELOG" in text


def test_der_name_der_umgebungsvariable_steht_in_der_meldung():
    """Wer den Befund liest, soll wissen, welche Variable leer war."""
    with pytest.raises(CheckFailed) as befund:
        assert_tag_matches("", "1.7.0", 3, HEADING, tag_env="RELEASE_TAG")
    assert "RELEASE_TAG" in str(befund.value)


# --------------------------------------------------------------------------
# G13 — die Description
# --------------------------------------------------------------------------

CHECKS = ("Checks", re.compile(r"(?P<wert>\d+)\s+Checks"), 120)
KATEGORIEN = ("Kategorien", re.compile(r"(?P<wert>\d+)\s+Kategorien"), 12)
REGELN = ("Regeln", re.compile(r"(?P<wert>\w+) transport-hardening rules"), 12)


def test_eine_stimmige_description_ist_gruen():
    assert assert_description_matches(
        "… · 120 Checks · 12 Kategorien · …", claims=(CHECKS, KATEGORIEN)
    )


def test_ANKER_ziffern_und_zahlwoerter_werden_beide_gelesen():
    """Die vier Herkunftsfassungen waren sich hier uneinig: zwei lasen
    Ziffern, zwei englische Zahlwoerter. Der Text entscheidet, nicht die
    Pruefung."""
    assert as_number("12") == 12
    assert as_number("twelve") == 12
    assert as_number("Twelve") == 12
    assert as_number("zwoelf") is None
    assert assert_description_matches(
        "patterns for the twelve transport-hardening rules", claims=(REGELN,)
    )


def test_die_echte_drift_dieses_repos_wird_gefangen():
    """Der Anlass, gemessen und nicht gedacht.

    Die GitHub-Description dieses Repos nannte 116 Checks, waehrend der
    Katalog bei 120 stand — deshalb war der `repo-description`-Workflow auf
    `main` rot.
    """
    with pytest.raises(CheckFailed) as befund:
        assert_description_matches(
            "… · 116 Checks · 12 Kategorien · …", claims=(CHECKS, KATEGORIEN)
        )
    text = str(befund.value)
    assert "116" in text and "120" in text
    # Kein Commit repariert sie — das Kommando soll dabeistehen.
    assert "gh repo edit" in text


def test_ANKER_ein_fehlender_anker_ist_ein_befund():
    """Wurde die Wendung umformuliert, hoert die Pruefung auf zu pruefen —
    ohne es zu sagen. Deshalb ist die Abwesenheit selbst der Befund."""
    with pytest.raises(CheckFailed) as befund:
        assert_description_matches("ganz anders formuliert", claims=(CHECKS,))
    assert "traegt die erwartete Wendung nicht" in str(befund.value)


def test_ANKER_ein_widerspruch_in_der_description_wird_gefangen():
    """Uebernommen aus der Fassung dieses Repos, der einzigen der vier, die
    ALLE Vorkommen las. Wer nur das erste liest, meldet eine Description, die
    sich selbst widerspricht, als in Ordnung."""
    with pytest.raises(CheckFailed) as befund:
        assert_description_matches(
            "… 120 Checks … und anderswo 116 Checks …", claims=(CHECKS,)
        )
    assert "widerspricht sich selbst" in str(befund.value)


def test_ein_unbekanntes_zahlwort_ist_ein_befund_ueber_die_liste():
    """Sonst meldete der Vergleich eine Abweichung, die in Wahrheit eine
    Luecke in ENGLISH_NUMBERS ist."""
    with pytest.raises(CheckFailed) as befund:
        assert_description_matches(
            "patterns for the dreiundzwanzig transport-hardening rules",
            claims=(REGELN,),
        )
    assert "ENGLISH_NUMBERS" in str(befund.value)


def test_ANKER_ohne_zusage_wird_nichts_geprueft():
    with pytest.raises(CheckFailed) as befund:
        assert_description_matches("irgendwas", claims=())
    assert "Keine Zusage" in str(befund.value)


def test_mehrere_befunde_werden_zusammen_gemeldet():
    """Ein Lauf soll jedes Problem auf einmal nennen."""
    with pytest.raises(CheckFailed) as befund:
        assert_description_matches(
            "… · 116 Checks · 8 Kategorien · …", claims=(CHECKS, KATEGORIEN)
        )
    text = str(befund.value)
    assert "116" in text and "8" in text


def test_der_repo_slug_landet_im_vorschlag():
    with pytest.raises(CheckFailed) as befund:
        assert_description_matches(
            "…", claims=(CHECKS,), repo_slug="malkreide/mcp-audit-skill"
        )
    assert "malkreide/mcp-audit-skill" in str(befund.value)
