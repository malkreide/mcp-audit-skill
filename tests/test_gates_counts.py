"""Das generische Zaehl-Gate unter `tools/gates/counts.py` (G14).

Die am staerksten verzweigte der sechzehn Familien: dreimal dieselbe
Bewegung, dreimal mit anderer EINHEIT — probe zaehlt Schritte, fidelity und
transport zaehlen Regeln. Was sich unterschied, war die Ueberschrift und das
Wort im Befundtext; beides ist jetzt Parameter.

Was hier geprueft wird, ist genau das, was durch die Zusammenlegung neu ist:

* dass die Einheit wirklich durchgereicht wird und nicht bloss so heisst;
* dass die LUECKENLOSIGKEIT mitgeprueft wird, nicht nur die Anzahl;
* dass ein Spiegel dieselben NUMMERN nennen muss, nicht bloss gleich viele.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gates import counts as gates  # noqa: E402
from tools.harness import CheckFailed  # noqa: E402

REGEL = re.compile(r"^## Regel (?P<nummer>\d+)", re.M)
SCHRITT = re.compile(r"^## Schritt (?P<nummer>\d+)", re.M)


def schreibe(root: pathlib.Path, name: str, zeilen: list[str]) -> None:
    (root / name).write_text("\n".join(zeilen) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Die normative Quelle
# --------------------------------------------------------------------------


def test_fortlaufende_nummern_werden_gezaehlt():
    text = "## Regel 1\ntext\n## Regel 2\ntext\n## Regel 3\n"
    assert gates.numbered(text, pattern=REGEL, quelle="SKILL.md", unit="Regeln") == [
        1,
        2,
        3,
    ]


def test_ANKER_eine_luecke_ist_ein_befund_nicht_nur_eine_kleinere_zahl():
    """Der Grund, warum nicht bloss gezaehlt wird.

    Wer Abschnitt 2 von drei loescht, hat zwei Abschnitte — eine reine
    Anzahl-Pruefung gegen eine ebenfalls angepasste Zaehlung waere gruen,
    waehrend die Numerierung 1,3 lautet. Die Zahl stimmt dann, die Sache
    nicht.
    """
    text = "## Regel 1\n## Regel 3\n"
    with pytest.raises(CheckFailed) as befund:
        gates.numbered(text, pattern=REGEL, quelle="SKILL.md", unit="Regeln")
    assert "nicht fortlaufend" in str(befund.value)
    assert "[1, 3]" in str(befund.value)


def test_eine_nummerierung_ab_null_ist_erlaubt():
    """Dieses Repo faengt bei `## Schritt 0` an — die Pruefung darf das nicht
    als Luecke lesen."""
    text = "## Schritt 0\n## Schritt 1\n## Schritt 2\n"
    assert gates.numbered(
        text, pattern=SCHRITT, quelle="SKILL.md", unit="Schritte"
    ) == [0, 1, 2]


def test_ANKER_kein_treffer_ist_ein_befund_keine_leere_menge():
    """Ein Anker, der weg ist, laesst diese Pruefung stillschweigend aufhoeren
    zu pruefen — deshalb ist die Abwesenheit selbst der Befund."""
    with pytest.raises(CheckFailed) as befund:
        gates.numbered("nichts davon", pattern=REGEL, quelle="X.md", unit="Regeln")
    assert "keine nummerierte" in str(befund.value)


def test_ANKER_die_einheit_steht_wirklich_im_befundtext():
    """Sonst waere der Parameter Zierde. probe zaehlt Schritte, die anderen
    zaehlen Regeln — wer den Befund liest, soll wissen, wovon die Rede ist."""
    for unit in ("Regeln", "Schritte"):
        with pytest.raises(CheckFailed) as befund:
            gates.numbered("leer", pattern=REGEL, quelle="X.md", unit=unit)
        assert unit in str(befund.value)


# --------------------------------------------------------------------------
# Die Spiegel
# --------------------------------------------------------------------------


@pytest.fixture
def baum(tmp_path):
    schreibe(tmp_path, "SKILL.md", ["## Regel 1", "a", "## Regel 2", "b"])
    return tmp_path


def test_ein_stimmiger_spiegel_ist_gruen(baum):
    schreibe(baum, "README.md", ["## Regel 1", "## Regel 2"])
    meldung = gates.count_agrees(
        baum,
        source="SKILL.md",
        pattern=REGEL,
        unit="Regeln",
        mirrors=(("README.md", REGEL, None),),
    )
    assert "2 Regeln" in meldung


def test_ohne_spiegel_wird_nur_die_quelle_geprueft(baum):
    assert "2 Regeln" in gates.count_agrees(
        baum, source="SKILL.md", pattern=REGEL, unit="Regeln"
    )


def test_ein_fehlender_eintrag_im_spiegel_wird_beim_namen_genannt(baum):
    schreibe(baum, "README.md", ["## Regel 1"])
    with pytest.raises(CheckFailed) as befund:
        gates.count_agrees(
            baum,
            source="SKILL.md",
            pattern=REGEL,
            unit="Regeln",
            mirrors=(("README.md", REGEL, None),),
        )
    assert "fehlt [2]" in str(befund.value)


def test_ANKER_gleich_viele_ist_nicht_dasselbe_wie_dieselben(tmp_path):
    """Eine Datei, die 0..1 fuehrt, waehrend die Quelle 1..2 sagt, hat
    dieselbe ANZAHL und meint etwas anderes. Genau das faengt eine reine
    Zaehlung nicht."""
    schreibe(tmp_path, "SKILL.md", ["## Schritt 1", "## Schritt 2"])
    schreibe(tmp_path, "cmd.md", ["## Schritt 0", "## Schritt 1"])
    with pytest.raises(CheckFailed) as befund:
        gates.count_agrees(
            tmp_path,
            source="SKILL.md",
            pattern=SCHRITT,
            unit="Schritte",
            mirrors=(("cmd.md", SCHRITT, None),),
        )
    text = str(befund.value)
    assert "zusaetzlich [0]" in text
    assert "fehlt [2]" in text


def test_die_meldung_nennt_die_quelle_als_massgeblich(baum):
    schreibe(baum, "README.md", ["## Regel 1"])
    with pytest.raises(CheckFailed) as befund:
        gates.count_agrees(
            baum,
            source="SKILL.md",
            pattern=REGEL,
            unit="Regeln",
            mirrors=(("README.md", REGEL, None),),
        )
    assert "Die Quelle ist SKILL.md" in str(befund.value)


def test_eine_fehlende_datei_ist_ein_befund(tmp_path):
    with pytest.raises(CheckFailed) as befund:
        gates.count_agrees(tmp_path, source="SKILL.md", pattern=REGEL, unit="Regeln")
    assert "fehlt" in str(befund.value)


def test_mehrere_spiegel_werden_alle_geprueft(baum):
    schreibe(baum, "README.md", ["## Regel 1", "## Regel 2"])
    schreibe(baum, "README.de.md", ["## Regel 1"])
    with pytest.raises(CheckFailed) as befund:
        gates.count_agrees(
            baum,
            source="SKILL.md",
            pattern=REGEL,
            unit="Regeln",
            mirrors=(("README.md", REGEL, None), ("README.de.md", REGEL, None)),
        )
    assert "README.de.md" in str(befund.value)


# --------------------------------------------------------------------------
# Der Abschnitts-Scope
# --------------------------------------------------------------------------


LIST_ITEM = re.compile(r"^(?P<nummer>\d+)\. \*\*", re.M)


def test_ANKER_ohne_abschnitt_zaehlt_jede_liste_des_dokuments_mit(tmp_path):
    """Gemessen beim Umzug von `mcp-transport-hardening`.

    Dessen README fuehrt nach den vierzehn Regeln noch zwei weitere
    nummerierte Listen — zusammen lasen sich die Nummern als 1..14,1..5,1..3
    und damit als «nicht fortlaufend». Der Befund war richtig, der Gegenstand
    falsch.
    """
    schreibe(tmp_path, "SKILL.md", ["## Regel 1", "## Regel 2"])
    schreibe(
        tmp_path,
        "README.md",
        ["## Regeln", "1. **a**", "2. **b**", "", "## Anderes", "1. **x**"],
    )
    with pytest.raises(CheckFailed) as befund:
        gates.count_agrees(
            tmp_path,
            source="SKILL.md",
            pattern=REGEL,
            unit="Regeln",
            mirrors=(("README.md", LIST_ITEM, None),),
        )
    assert "nicht fortlaufend" in str(befund.value)


def test_mit_abschnitt_zaehlt_nur_die_gemeinte_liste(tmp_path):
    schreibe(tmp_path, "SKILL.md", ["## Regel 1", "## Regel 2"])
    schreibe(
        tmp_path,
        "README.md",
        ["## Regeln", "1. **a**", "2. **b**", "", "## Anderes", "1. **x**"],
    )
    assert gates.count_agrees(
        tmp_path,
        source="SKILL.md",
        pattern=REGEL,
        unit="Regeln",
        mirrors=(("README.md", LIST_ITEM, "Regeln"),),
    )


def test_ANKER_eine_fehlende_abschnitts_ueberschrift_ist_ein_befund(tmp_path):
    schreibe(tmp_path, "SKILL.md", ["## Regel 1"])
    schreibe(tmp_path, "README.md", ["## Anders benannt", "1. **a**"])
    with pytest.raises(CheckFailed) as befund:
        gates.count_agrees(
            tmp_path,
            source="SKILL.md",
            pattern=REGEL,
            unit="Regeln",
            mirrors=(("README.md", LIST_ITEM, "Regeln"),),
        )
    assert "nicht gefunden" in str(befund.value)
