"""Die Faelle von Check 8, die sich nur mit untergeschobener `ruff` pruefen lassen.

Alle uebrigen Pruefungen kommen mit Baum-Mutationen aus und stehen deshalb in
`mutations.py`. Check 8 nicht: Sein Urteil haengt am PATH, nicht am Baum.
Genau das war als Inline-Shell nicht pruefbar — man konnte den Schritt nur im
CI beobachten und hoffen, dass er im Ernstfall das Richtige tut.

Die Faelle hier sind der Ernstfall:

* eine ruff mit der FALSCHEN Version — der gemessene Vorfall, gegen den es
  Check 8 ueberhaupt gibt (0.15.8 vor 0.16.1 im PATH);
* eine ruff mit GEAENDERTER Ausgabeform — der Anker, dessen Verlust die
  Pruefung sonst still nichts mehr vergleichen liesse;
* eine ruff, die ABSTUERZT;
* GAR KEINE ruff.

Die letzten drei muessen alle FEHLER heissen, nicht «uebersprungen».
"""

from __future__ import annotations

import pytest
from conftest import gepinnte_version

from tools.checks import CheckFailed
from tools.checks.toolchain import ruff_version_matches_pin


def test_passende_version_ist_gruen(tree, ruff_shim):
    pin = gepinnte_version(tree)
    ruff_shim(f'echo "ruff {pin}"')
    assert pin in ruff_version_matches_pin(tree)


def test_falsche_version_wird_rot(tree, ruff_shim):
    """Der gemessene Vorfall: eine aeltere ruff liegt vorne im PATH."""
    pin = gepinnte_version(tree)
    ruff_shim('echo "ruff 0.15.8"')
    with pytest.raises(CheckFailed) as befund:
        ruff_version_matches_pin(tree)
    text = str(befund.value)
    assert "Die ruff auf dem PATH ist 0.15.8" in text
    assert f"gepinnt ist {pin}" in text
    # Der Befund muss sagen, warum Check 7 das NICHT merkt — sonst sucht der
    # naechste Leser den Fehler in der falschen Datei.
    assert "zwei Texte" in text


@pytest.mark.parametrize(
    ("rumpf", "erwartet"),
    [
        # ANKER: Ausgabeform geaendert. Die Pruefung darf dann nicht null
        # vergleichen und «ok» melden — sie muss sagen, dass sie nichts lesen
        # kann.
        ('echo "Ruff, version 0.16.1"', "antwortet nicht in der Form"),
        ('echo ""', "antwortet nicht in der Form"),
        # ruff selbst kaputt.
        ('echo "boom" >&2; exit 3', "endete mit 3"),
        # ANKER: gar keine ruff. FAIL statt skip.
        (None, "liegt nicht auf dem PATH"),
    ],
    ids=[
        "ANKER-ausgabeform",
        "ANKER-leere-ausgabe",
        "ruff-stuerzt-ab",
        "ANKER-keine-ruff",
    ],
)
def test_unbrauchbare_ruff_wird_rot(tree, ruff_shim, rumpf, erwartet):
    ruff_shim(rumpf)
    with pytest.raises(CheckFailed) as befund:
        ruff_version_matches_pin(tree)
    assert erwartet in str(befund.value), (
        f"rot, aber nicht aus dem erwarteten Grund.\n"
        f"  erwartet: {erwartet!r}\n  gemeldet: {str(befund.value).strip()!r}"
    )
