"""Die Testsuite und die Registry selbst bleiben vollstaendig.

`test_mutations.py` prueft die Pruefungen. Diese Datei prueft die Pruefung:
Sie faellt, wenn die Suite eine Zusage nicht mehr einloest — statt erst dann,
wenn ein Anker still verschwindet und niemand es merkt.

Der teuerste Fall steht ganz unten: `@register` laeuft beim IMPORT. Fehlt die
Importzeile eines Moduls in `tools/checks/__init__.py`, verschwinden dessen
Pruefungen aus jedem Lauf, ohne dass irgendetwas rot wird — der Runner meldet
dann «all passed» ueber weniger, als er glaubt.
"""

from __future__ import annotations

import pathlib
import re

import pytest
from conftest import CHECKS_BY_NAME

import tools.checks
from tools.checks import CheckFailed, all_checks
from tools.checks._core import Check, run


@pytest.mark.parametrize("name", sorted(CHECKS_BY_NAME))
def test_jede_pruefung_hat_eine_anker_mutation(name):
    """Keine Pruefung ohne Beleg, dass ein fehlender Anker sie rot macht."""
    from mutations import MUTATIONS

    anker = [m for m in MUTATIONS if m[1] == name and "ANKER" in m[0]]
    assert anker, (
        f"{name} hat keine ANKER-Mutation. Ohne sie ist unbelegt, dass ein "
        "entfernter Anker FEHLER heisst und nicht «uebersprungen» — und genau "
        "das ist der Fehler, den diese Pruefungen nicht machen duerfen."
    )


def test_jede_mutation_nennt_eine_bekannte_pruefung():
    """Eine Mutation auf eine Pruefung, die es nicht gibt, laeuft ins Leere."""
    from mutations import MUTATIONS

    unbekannt = sorted({m[1] for m in MUTATIONS} - CHECKS_BY_NAME.keys())
    assert not unbekannt, (
        f"Mutationen verweisen auf unbekannte Pruefungen: {unbekannt}. "
        "Entweder ist der Name vertippt, oder die Pruefung wurde entfernt und "
        "ihre Mutationen blieben stehen."
    )


def test_keine_doppelten_mutations_ids():
    """Zwei Mutationen mit demselben Namen verdecken einander im Bericht."""
    from mutations import MUTATIONS

    ids = [m[0] for m in MUTATIONS]
    doppelt = sorted({i for i in ids if ids.count(i) > 1})
    assert not doppelt, f"Mutations-IDs kommen mehrfach vor: {doppelt}"


def test_nummern_sind_lueckenlos_und_eindeutig():
    """Eine Luecke heisst meist, dass eine Pruefung still herausgefallen ist.

    Doppelte Nummern faengt `register` schon beim Import ab; hier geht es um
    die Luecke, die niemand meldet.
    """
    numbers = [c.number for c in all_checks()]
    assert numbers == sorted(set(numbers)), f"Nummern nicht eindeutig: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"Nummern nicht lueckenlos: {numbers}. Eine Luecke ist fast immer eine "
        "Pruefung, die aus der Registry gefallen ist."
    )


def test_registry_deckt_jedes_pruefmodul_ab():
    """Ein Modul ohne Importzeile in __init__.py registriert nichts.

    VOLLSTAENDIG STATISCH — weder importiert noch `all_checks()` befragt, und
    das ist der ganze Punkt. `@register` laeuft beim Import: Sobald IRGENDEIN
    Test das Modul importiert — `test_ruff_gates.py` holt sich
    `toolchain.ruff_version_matches_pin`, `test_open_names.py` die
    `references` — ist es registriert, ganz gleich was in `__init__.py` steht.

    GEMESSEN, dass eine Laufzeit-Abfrage das nicht faengt: Mit der
    Importzeile fuer `toolchain` entfernt meldete `validate.sh` «8 checks,
    all passed» statt zehn, und im vollen pytest-Lauf fiel dieser Test NICHT
    — er wurde vom Import in `test_ruff_gates.py` verdeckt. Rot wurde die
    Suite nur ueber die Mutationen, die zufaellig auf die verlorenen
    Pruefungen zeigten. Ein Modul ohne Mutationen waere unbemerkt geblieben.

    Verglichen werden deshalb zwei TEXTE: welche Module `@register(`
    enthalten, und welche `__init__.py` importiert.
    """
    paket = pathlib.Path(tools.checks.__file__).parent
    mit_register = {
        datei.stem
        for datei in sorted(paket.glob("*.py"))
        if not datei.name.startswith("_")
        and "@register(" in datei.read_text(encoding="utf-8")
    }
    init = (paket / "__init__.py").read_text(encoding="utf-8")
    importiert = {
        name.strip()
        for zeile in re.findall(r"^from \. import (.+)$", init, re.M)
        for name in zeile.split(",")
    }

    fehlend = sorted(mit_register - importiert)
    assert not fehlend, (
        f"Diese Module unter tools/checks/ rufen @register, stehen aber nicht "
        f"in der Importzeile von __init__.py: {fehlend}. Ohne sie verschwinden "
        "ihre Pruefungen aus jedem Lauf von validate.sh, ohne dass etwas rot "
        "wird."
    )


def test_der_offline_runner_laesst_die_netz_pruefung_draussen():
    """`validate.sh` muss in einem Clone ohne Zugangsdaten durchlaufen."""
    offline = {c.number for c in all_checks(offline_only=True)}
    alle = {c.number for c in all_checks()}
    netz = alle - offline
    assert netz, (
        "Keine Pruefung ist als Netz-Pruefung markiert. Entweder stimmt das — "
        "dann kann diese Zusicherung weg — oder eine Netz-Pruefung laeuft "
        "faelschlich im Offline-Runner mit."
    )


def test_eine_abgestuerzte_pruefung_ist_ein_defekt_kein_befund(tmp_path):
    """«Der Check ist kaputt» ist eine andere Nachricht als «das Repo hat einen Befund».

    Ohne diese Unterscheidung liest sich ein Tippfehler im Regex wie ein
    echtes Problem am Repository — und jemand sucht an der falschen Stelle.
    """

    def stuerzt_ab(root):
        raise TypeError("kaputt")

    ergebnis = run(
        Check(number=99, label="absichtlich kaputt", run=stuerzt_ab), tmp_path
    )
    assert not ergebnis.ok
    assert "abgestuerzt" in ergebnis.output
    assert "kein Befund ueber das Repository" in ergebnis.output
    assert "TypeError" in ergebnis.output


def test_ein_befund_wird_nicht_fuer_einen_absturz_gehalten(tmp_path):
    def meldet_befund(root):
        raise CheckFailed("das Repository hat ein Problem")

    ergebnis = run(Check(number=98, label="Befund", run=meldet_befund), tmp_path)
    assert not ergebnis.ok
    assert ergebnis.output == "das Repository hat ein Problem"
    assert "abgestuerzt" not in ergebnis.output
