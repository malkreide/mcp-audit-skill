"""Die Faelle der Ruff-Gates, die sich nur mit untergeschobener `ruff` prüfen lassen.

Alle uebrigen Checks kommen mit Baum-Mutationen aus und stehen deshalb in
`mutations.py`. `ruff_version.py` nicht: Sein Urteil haengt am PATH, nicht am
Baum. Genau das war als Inline-Shell nicht pruefbar — man konnte den Schritt
nur im CI beobachten und hoffen, dass er im Ernstfall das Richtige tut.

Die vier Faelle hier sind der Ernstfall:

* eine ruff mit der FALSCHEN Version — der gemessene Vorfall, gegen den es
  diesen Check ueberhaupt gibt (0.15.8 vor 0.16.1 im PATH);
* eine ruff mit GEAENDERTER Ausgabeform — der Anker, dessen Verlust den Check
  sonst still nichts mehr vergleichen liesse;
* eine ruff, die ABSTUERZT;
* GAR KEINE ruff.

Die letzten drei muessen alle FEHLER heissen, nicht «uebersprungen».
"""

from __future__ import annotations

import pytest
from conftest import gepinnte_version


def test_passende_version_ist_gruen(tree, run_check, ruff_shim):
    pin = gepinnte_version(tree)
    p = run_check("ruff_version", tree, pfad=ruff_shim(f'echo "ruff {pin}"'))
    assert p.returncode == 0, p.stdout + p.stderr
    assert pin in p.stdout


def test_falsche_version_wird_rot(tree, run_check, ruff_shim):
    """Der gemessene Vorfall: eine aeltere ruff liegt vorne im PATH."""
    pin = gepinnte_version(tree)
    p = run_check("ruff_version", tree, pfad=ruff_shim('echo "ruff 0.15.8"'))
    kombiniert = p.stdout + p.stderr
    assert p.returncode != 0, kombiniert
    assert "Die ruff auf dem PATH ist 0.15.8" in kombiniert
    assert f"gepinnt ist {pin}" in kombiniert


@pytest.mark.parametrize(
    ("rumpf", "erwartet"),
    [
        # ANKER: Ausgabeform geaendert. Der Check darf dann nicht null
        # vergleichen und «ok» melden — er muss sagen, dass er nichts lesen kann.
        ('echo "Ruff, version 0.16.1"', "antwortet nicht in der Form"),
        ('echo ""', "antwortet nicht in der Form"),
        # ruff selbst kaputt.
        ('echo "boom" >&2; exit 3', "endete mit einem Fehler"),
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
def test_unbrauchbare_ruff_wird_rot(tree, run_check, ruff_shim, rumpf, erwartet):
    p = run_check("ruff_version", tree, pfad=ruff_shim(rumpf))
    kombiniert = p.stdout + p.stderr
    assert p.returncode != 0, (
        f"ruff_version blieb gruen, obwohl die ruff auf dem PATH unbrauchbar "
        f"ist. «nicht gelaufen» als «bestanden» zu melden ist genau der "
        f"Fehler, den dieser Check nicht machen darf.\n{kombiniert}"
    )
    assert erwartet in kombiniert, (
        f"rot, aber nicht aus dem erwarteten Grund.\n"
        f"  erwartet: {erwartet!r}\n  gemeldet: {kombiniert.strip()!r}"
    )
