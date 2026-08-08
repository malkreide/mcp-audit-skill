"""Die Registry unter `tools/checks/` und die Pruefungen, die sie fuehrt.

`tests/test_ruff_pin.py` und `tests/test_ruff_version.py` pruefen weiterhin die
REINEN Vergleichsfunktionen — sie sind unveraendert geblieben, weil die
Registry sie nur einhaengt statt sie zu ersetzen. Diese Datei prueft, was
dadurch neu ist:

* dass jede registrierte Pruefung am echten Baum gruen ist;
* dass sie an einem gezielt kaputten Baum rot wird, MIT der erwarteten
  Meldung — eine Pruefung, die aus dem falschen Grund rot wird, ist beim
  naechsten Mal aus dem falschen Grund gruen;
* dass die Registry selbst vollstaendig bleibt.

Der teuerste Fall steht unten: `@register` laeuft beim IMPORT. Fehlt die
Importzeile eines Moduls in `tools/checks/__init__.py`, verschwinden dessen
Pruefungen aus jedem Lauf, ohne dass irgendetwas rot wird — der Runner meldet
dann «all passed» ueber weniger, als er glaubt.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.checks  # noqa: E402
from tools.checks import CheckFailed, all_checks  # noqa: E402
from tools.checks._core import Check, run  # noqa: E402

CHECKS_BY_NAME = {c.run.__name__: c for c in all_checks()}


@pytest.fixture
def tree(tmp_path: pathlib.Path) -> pathlib.Path:
    """Eine Wegwerf-Kopie des echten Repos.

    Nur die Dateien, an denen die vier Pruefungen haengen — ein vollstaendiges
    Kopieren waere fuer jeden Test unnoetig teuer, und was nicht gelesen wird,
    macht den Fixture-Baum nur unuebersichtlich.
    """
    dst = tmp_path / "repo"
    (dst / ".github" / "workflows").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / ".github/workflows/lint.yml", dst / ".github/workflows")
    shutil.copy2(REPO_ROOT / ".pre-commit-config.yaml", dst)
    shutil.copy2(REPO_ROOT / "ruff.toml", dst)
    (dst / "beispiel.py").write_text("x = 1\n", encoding="utf-8")
    return dst


@pytest.fixture
def ruff_shim(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """Legt eine gefaelschte `ruff` an und setzt den PATH auf sie."""

    def _shim(rumpf: str | None) -> pathlib.Path:
        d = tmp_path / "shim"
        d.mkdir(exist_ok=True)
        if rumpf is not None:
            f = d / "ruff"
            f.write_text(f"#!/bin/sh\n{rumpf}\n", encoding="utf-8")
            f.chmod(0o755)
        monkeypatch.setenv("PATH", str(d))
        return d

    return _shim


# --------------------------------------------------------------------------
# Die Pruefungen am gesunden und am kaputten Baum
# --------------------------------------------------------------------------


def test_alle_pruefungen_sind_am_echten_repo_gruen():
    """Wird eine hier rot, ist der Baum kaputt — nicht die Suite."""
    for check in all_checks():
        assert check.run(REPO_ROOT), f"Check {check.number} meldet Erfolg ohne Wort"


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


def test_ruff_version_wird_rot_bei_falscher_version(tree, ruff_shim):
    ruff_shim('echo "ruff 0.15.8"')
    with pytest.raises(CheckFailed) as befund:
        CHECKS_BY_NAME["ruff_version_matches_pin"].run(tree)
    assert "0.15.8" in str(befund.value)


@pytest.mark.parametrize(
    ("rumpf", "erwartet"),
    [
        ('echo "Ruff, version 0.16.1"', "antwortet nicht in der Form"),
        ('echo "boom" >&2; exit 3', "endete mit 3"),
        (None, "liegt nicht auf dem PATH"),
    ],
    ids=["ANKER-ausgabeform", "ruff-stuerzt-ab", "ANKER-keine-ruff"],
)
def test_ANKER_unbrauchbare_ruff_ist_ein_befund(tree, ruff_shim, rumpf, erwartet):
    ruff_shim(rumpf)
    with pytest.raises(CheckFailed) as befund:
        CHECKS_BY_NAME["ruff_version_matches_pin"].run(tree)
    assert erwartet in str(befund.value)


def test_ruff_check_wird_rot_an_kaputtem_code(tree):
    (tree / "beispiel.py").write_text("import os\n", encoding="utf-8")  # F401
    with pytest.raises(CheckFailed) as befund:
        CHECKS_BY_NAME["ruff_check"].run(tree)
    assert "F401" in str(befund.value)


def test_ruff_format_wird_rot_an_unformatiertem_code(tree):
    (tree / "beispiel.py").write_text("x  =  1\n", encoding="utf-8")
    with pytest.raises(CheckFailed) as befund:
        CHECKS_BY_NAME["ruff_format"].run(tree)
    assert "reformatted" in str(befund.value)


def test_ANKER_die_gates_ohne_ruff_sind_ein_befund(tree, ruff_shim):
    """Kein ruff heisst FEHLER, nicht «uebersprungen»."""
    ruff_shim(None)
    for name in ("ruff_check", "ruff_format"):
        with pytest.raises(CheckFailed) as befund:
            CHECKS_BY_NAME[name].run(tree)
        assert "FAIL statt skip" in str(befund.value)


# --------------------------------------------------------------------------
# Die Registry selbst
# --------------------------------------------------------------------------


def test_nummern_sind_lueckenlos_und_eindeutig():
    numbers = [c.number for c in all_checks()]
    assert numbers == sorted(set(numbers)), f"nicht eindeutig: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"nicht lueckenlos: {numbers}. Eine Luecke ist fast immer eine "
        "Pruefung, die aus der Registry gefallen ist."
    )


def test_registry_deckt_jedes_pruefmodul_ab():
    """Ein Modul ohne Importzeile registriert nichts — und schweigt dazu.

    GELESEN WIRD DER QUELLTEXT, NICHT IMPORTIERT. `@register` laeuft beim
    Import: Wuerde dieser Test die Module importieren, um sie zu befragen,
    traegt er das fehlende Modul dabei nachtraeglich ein — und koennte den
    Fehler, den er sucht, niemals finden.
    """
    paket = pathlib.Path(tools.checks.__file__).parent
    mit_register = {
        datei.stem
        for datei in sorted(paket.glob("*.py"))
        if not datei.name.startswith("_")
        and "@register(" in datei.read_text(encoding="utf-8")
    }
    registriert = {c.run.__module__.rsplit(".", 1)[-1] for c in all_checks()}
    fehlend = sorted(mit_register - registriert)
    assert not fehlend, (
        f"Diese Module rufen @register, stehen aber nicht in der Registry: "
        f"{fehlend}. Fehlt ihre Importzeile in __init__.py, verschwinden ihre "
        "Pruefungen aus jedem Lauf, ohne dass etwas rot wird."
    )


def test_eine_abgestuerzte_pruefung_ist_ein_defekt_kein_befund(tmp_path):
    def stuerzt_ab(root):
        raise TypeError("kaputt")

    ergebnis = run(Check(number=99, label="kaputt", run=stuerzt_ab), tmp_path)
    assert not ergebnis.ok
    assert "abgestuerzt" in ergebnis.output
    assert "TypeError" in ergebnis.output


def test_ein_befund_wird_nicht_fuer_einen_absturz_gehalten(tmp_path):
    def meldet_befund(root):
        raise CheckFailed("das Repository hat ein Problem")

    ergebnis = run(Check(number=98, label="Befund", run=meldet_befund), tmp_path)
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

    checks = [Check(number=n, label=f"c{n}", run=rot) for n in (91, 92, 93)]
    from tools.checks import run_all

    ergebnisse = run_all(pathlib.Path("."), checks)
    assert len(ergebnisse) == 3
    assert all(not e.ok for e in ergebnisse)


def test_validate_sh_ruft_dieselben_pruefungen():
    """Der dokumentierte Weg und die Registry duerfen nicht auseinanderlaufen."""
    done = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/validate.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    for check in all_checks(offline_only=True):
        assert check.label in done.stdout, f"Check {check.number} fehlt im Lauf"
