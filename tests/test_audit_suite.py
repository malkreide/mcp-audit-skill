"""Die Suite `audit` unter `tools/suites/mcp_audit/` und ihre Pruefungen.

`tests/test_ruff_pin.py` und `tests/test_ruff_version.py` pruefen weiterhin die
REINEN Vergleichsfunktionen — sie sind unveraendert geblieben, weil die
Registry sie nur einhaengt statt sie zu ersetzen. Diese Datei prueft, was
dadurch neu ist:

* dass jede registrierte Pruefung am echten Baum gruen ist;
* dass sie an einem gezielt kaputten Baum rot wird, MIT der erwarteten
  Meldung — eine Pruefung, die aus dem falschen Grund rot wird, ist beim
  naechsten Mal aus dem falschen Grund gruen;
* dass die Registry selbst vollstaendig bleibt.

Der teuerste Fall steht unten, jetzt auf ZWEI Ebenen: `@register` laeuft beim
IMPORT. Fehlt die Importzeile eines Moduls in
`tools/suites/mcp_audit/__init__.py`, verschwinden dessen Pruefungen; fehlt die
Importzeile der ganzen Suite in `tools/suites/__init__.py`, verschwinden ALLE.
Beide Male wird nichts rot — der Runner meldet «all passed» ueber weniger, als
er glaubt.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.suites  # noqa: E402
import tools.suites.mcp_audit  # noqa: E402
from tools.gates import ruff as gates_ruff  # noqa: E402
from tools.gates import toolchain as gates_toolchain  # noqa: E402
from tools.harness import CheckFailed, all_checks  # noqa: E402
from tools.harness._core import Check, run  # noqa: E402
from tools.suites.mcp_audit import SUITE  # noqa: E402

CHECKS_BY_NAME = {c.run.__name__: c for c in all_checks(suite=SUITE)}


def importierte_namen(init: str) -> set[str]:
    """Die Namen aus `from . import …`, ein- ODER mehrzeilig.

    Die mehrzeilige Form mit Klammern kam mit der siebten Suite-Datei: `ruff
    format` bricht die Zeile ab einer bestimmten Laenge selbst um. Ein Muster,
    das nur die einzeilige Form kennt, laese ab da eine LEERE Menge — und
    dieser Test meldete dann jedes Modul als fehlend. Er ist damals genau so
    rot geworden, was der richtige Ausgang ist; die stille Variante waere
    gewesen, wenn er umgekehrt gruen geblieben waere.
    """
    einzeilig = re.findall(r"^from \. import ([^(\n]+)$", init, re.M)
    mehrzeilig = re.findall(r"^from \. import \(\s*(.*?)\)", init, re.M | re.S)
    return {
        name.strip()
        for block in [*einzeilig, *mehrzeilig]
        for name in block.split(",")
        if name.strip()
    }


@pytest.fixture
def tree(tmp_path: pathlib.Path) -> pathlib.Path:
    """Eine Wegwerf-Kopie des echten Repos.

    Nur die Dateien, an denen die Pruefungen 1 bis 4 haengen — ein
    vollstaendiges Kopieren waere fuer jeden Test unnoetig teuer, und was
    nicht gelesen wird, macht den Fixture-Baum nur unuebersichtlich.

    Check 5 (das Skill-Archiv) faehrt gegen einen eigenen Baum in
    `tests/test_skill_package.py`: Er braucht Manifest, Katalog und Archiv,
    also gerade das, was dieser Fixture-Baum bewusst weglaesst.
    """
    dst = tmp_path / "repo"
    (dst / ".github" / "workflows").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / ".github/workflows/lint.yml", dst / ".github/workflows")
    shutil.copy2(REPO_ROOT / ".pre-commit-config.yaml", dst)
    shutil.copy2(REPO_ROOT / "ruff.toml", dst)
    (dst / "beispiel.py").write_text("x = 1\n", encoding="utf-8")
    return dst


# --------------------------------------------------------------------------
# Die Pruefungen am gesunden und am kaputten Baum
# --------------------------------------------------------------------------


def test_pin_sync_wird_rot_wenn_die_pins_auseinanderlaufen(tree):
    p = tree / ".pre-commit-config.yaml"
    p.write_text(
        p.read_text(encoding="utf-8").replace("rev: v0.16.1", "rev: v0.15.8"),
        encoding="utf-8",
    )
    with pytest.raises(CheckFailed) as befund:
        CHECKS_BY_NAME["ruff_pin_sync"].run(tree)
    assert "0.15.8" in str(befund.value)


def test_ANKER_pin_sync_ohne_pin_ist_ein_befund(tree):
    p = tree / ".github/workflows/lint.yml"
    p.write_text(
        p.read_text(encoding="utf-8").replace("ruff==0.16.1", "ruff"), encoding="utf-8"
    )
    with pytest.raises(CheckFailed) as befund:
        CHECKS_BY_NAME["ruff_pin_sync"].run(tree)
    # Kein Pin heisst «nicht verglichen», nicht «bestanden».
    assert str(befund.value)


# Die REINEN Urteilsfunktionen sind anderswo geprueft: `compare()` in
# tests/test_ruff_pin.py und tests/test_ruff_version.py, `bewerte()` unten.
# Hier geht es um die VERDRAHTUNG — dass die Registry den Befund als
# CheckFailed weiterreicht statt ihn zu verschlucken.


def test_ANKER_ruff_version_ohne_ruff_ist_ein_befund(tree, monkeypatch):
    """Kein ruff heisst FEHLER, nicht «uebersprungen».

    `shutil.which` ist die eine Naht, an der diese Pruefung die Umgebung
    befragt — sie hier zu ersetzen ist genauer und portabler, als eine
    gefaelschte ruff in den PATH zu legen. Ein `#!/bin/sh`-Shim faellt unter
    Windows um, und die Matrix dieses Repos enthaelt windows-latest.

    Gepatcht wird seit Phase 2 im GATE, nicht mehr im Suite-Modul: Dort steht
    die Logik, das Suite-Modul bindet sie nur noch. Der Anker wandert mit der
    Naht mit — bliebe er stehen, patchte er ein Modul, das `shutil` gar nicht
    mehr importiert, und der Test wuerde gruen, ohne zu messen.
    """
    monkeypatch.setattr(gates_toolchain.shutil, "which", lambda _: None)
    with pytest.raises(CheckFailed) as befund:
        CHECKS_BY_NAME["ruff_version_matches_pin"].run(tree)
    assert "liegt nicht auf dem PATH" in str(befund.value)


@pytest.mark.parametrize("name", ["ruff_check", "ruff_format"])
def test_ANKER_die_gates_ohne_ruff_sind_ein_befund(tree, monkeypatch, name):
    monkeypatch.setattr(gates_ruff.shutil, "which", lambda _: None)
    with pytest.raises(CheckFailed) as befund:
        CHECKS_BY_NAME[name].run(tree)
    assert "FAIL statt skip" in str(befund.value)


# --- die reine Urteilsfunktion der Gates -----------------------------------


def test_bewerte_gruen_bei_exit_null():
    ok, message = gates_ruff.bewerte("check", 0, "All checks passed!")
    assert ok
    assert "All checks passed!" in message


def test_bewerte_reicht_die_ausgabe_durch():
    ok, message = gates_ruff.bewerte("check", 1, "beispiel.py:1:8: F401 unused import")
    assert not ok
    assert "F401" in message


def test_bewerte_haengt_beim_format_den_hinweis_an():
    """Ein Befund soll sagen, wie er zu beheben ist."""
    ok, message = gates_ruff.bewerte("format", 1, "1 file would be reformatted")
    assert not ok
    assert "reformatted" in message
    assert "ruff format ." in message


def test_bewerte_meldet_auch_ohne_ausgabe_etwas():
    """Eine leere Erfolgsmeldung liesse den Lauf schweigen, wo er reden soll."""
    for kind in ("check", "format"):
        ok, message = gates_ruff.bewerte(kind, 0, "")
        assert ok
        assert message


# --------------------------------------------------------------------------
# Die Registry selbst
# --------------------------------------------------------------------------


def test_nummern_sind_lueckenlos_und_eindeutig():
    """Lueckenlos JE SUITE, nicht ueber alle.

    Der vereinigte Nummernraum ist absichtlich nicht lueckenlos — `audit/1`
    und `probe/1` existieren beide. Innerhalb der Suite gilt die Invariante
    unveraendert weiter.
    """
    numbers = [c.number for c in all_checks(suite=SUITE)]
    assert numbers == sorted(set(numbers)), f"nicht eindeutig: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"nicht lueckenlos: {numbers}. Eine Luecke ist fast immer eine "
        "Pruefung, die aus der Registry gefallen ist."
    )


def test_registry_deckt_jedes_pruefmodul_ab():
    """Ein Modul ohne Importzeile in __init__.py registriert nichts.

    VOLLSTAENDIG STATISCH — weder importiert noch `all_checks()` befragt, und
    das ist der ganze Punkt. `@register` laeuft beim Import: Sobald IRGENDEIN
    Test das Modul importiert (dieser hier importiert `ruff_gate` fuer die
    `bewerte`-Tests), ist es registriert, ganz gleich was in `__init__.py`
    steht. Eine Laufzeit-Abfrage koennte den Fehler deshalb nie finden — sie
    hat ihn beim Bau dieser Datei tatsaechlich uebersehen.

    Verglichen werden zwei TEXTE: welche Module `@register(` enthalten, und
    welche `__init__.py` importiert.
    """
    paket = pathlib.Path(tools.suites.mcp_audit.__file__).parent
    mit_register = {
        datei.stem
        for datei in sorted(paket.glob("*.py"))
        if not datei.name.startswith("_")
        and "@register(" in datei.read_text(encoding="utf-8")
    }
    init = (paket / "__init__.py").read_text(encoding="utf-8")
    importiert = importierte_namen(init)

    fehlend = sorted(mit_register - importiert)
    assert not fehlend, (
        f"Diese Module rufen @register, stehen aber nicht in der Importzeile "
        f"von __init__.py: {fehlend}. Ohne sie verschwinden ihre Pruefungen "
        "aus jedem Lauf von validate.sh, ohne dass etwas rot wird."
    )


def test_jede_suite_steht_in_der_importzeile():
    """Die Ebene ueber dem Pruefmodul — und die teurere von beiden.

    Fehlt ein Modul in der Importzeile seiner Suite, verschwinden dessen
    Pruefungen. Fehlt die SUITE in `tools/suites/__init__.py`, verschwinden
    alle ihre auf einmal, und der Runner meldet «all passed» ueber ein
    Repository, das er nicht geprueft hat.

    Ebenfalls vollstaendig statisch, und aus demselben Grund: Diese Datei
    importiert `tools.suites.mcp_audit` selbst, die Suite waere zur Laufzeit
    also immer registriert.
    """
    paket = pathlib.Path(tools.suites.__file__).parent
    vorhanden = {
        d.name
        for d in sorted(paket.iterdir())
        if d.is_dir() and not d.name.startswith(("_", "."))
    }
    init = (paket / "__init__.py").read_text(encoding="utf-8")
    importiert = importierte_namen(init)

    fehlend = sorted(vorhanden - importiert)
    assert not fehlend, (
        f"Diese Suiten liegen unter tools/suites/, stehen aber nicht in der "
        f"Importzeile von __init__.py: {fehlend}. Ohne sie verschwinden ALLE "
        "ihre Pruefungen aus jedem Lauf, ohne dass etwas rot wird."
    )


def test_eine_abgestuerzte_pruefung_ist_ein_defekt_kein_befund(tmp_path):
    def stuerzt_ab(root):
        raise TypeError("kaputt")

    ergebnis = run(
        Check(number=99, label="kaputt", run=stuerzt_ab, suite="test"), tmp_path
    )
    assert not ergebnis.ok
    assert "abgestuerzt" in ergebnis.output
    assert "TypeError" in ergebnis.output


def test_ein_befund_wird_nicht_fuer_einen_absturz_gehalten(tmp_path):
    def meldet_befund(root):
        raise CheckFailed("das Repository hat ein Problem")

    ergebnis = run(
        Check(number=98, label="Befund", run=meldet_befund, suite="test"), tmp_path
    )
    assert not ergebnis.ok
    assert ergebnis.output == "das Repository hat ein Problem"
    assert "abgestuerzt" not in ergebnis.output


def test_ein_lauf_nennt_alle_befunde_nicht_nur_den_ersten():
    """Der Ertrag gegenueber vier Workflow-Schritten.

    Vorher brach der erste rote Schritt den Job ab, und die drei dahinter
    liefen nicht — jeder Fehlschlag kostete eine eigene Runde.
    """

    def rot(root):
        raise CheckFailed("Befund")

    checks = [
        Check(number=n, label=f"c{n}", run=rot, suite="test") for n in (91, 92, 93)
    ]
    from tools.harness import run_all

    ergebnisse = run_all(pathlib.Path("."), checks)
    assert len(ergebnisse) == 3
    assert all(not e.ok for e in ergebnisse)


def test_der_runner_waehlt_alle_offline_pruefungen():
    """Der dokumentierte Weg und die Registry duerfen nicht auseinanderlaufen.

    Ohne Unterprozess: `validate.sh` ist eine duenne Huelle um
    `python -m tools.harness`, und dessen Auswahl laesst sich direkt befragen.
    Ein Lauf des Skripts braeuchte ruff und wuerde damit die Testumgebung
    pruefen statt die Auswahl.
    """
    from tools.harness.__main__ import select

    gewaehlt = {c.number for c in select([], include_network=False)}
    erwartet = {c.number for c in all_checks(offline_only=True)}
    assert gewaehlt == erwartet, (
        f"Der Runner faehrt {sorted(gewaehlt)}, die Registry kennt "
        f"{sorted(erwartet)} — eine Pruefung liefe nie."
    )
