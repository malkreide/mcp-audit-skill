"""Das generische Toolchain-Gate unter `tools/gates/toolchain.py`.

`tests/test_ruff_pin.py` und `tests/test_ruff_version.py` pruefen weiterhin
die REINEN Vergleichsfunktionen ueber ihre alten Einstiege — sie sind
unveraendert geblieben, weil der Umzug an der Logik nichts geaendert hat.
Diese Datei prueft, was durch die Zusammenfuehrung NEU ist:

* dass der CI-Workflow-Pfad wirklich ein Parameter ist und nicht bloss so
  heisst — er war der einzige Grund, warum die vier Fassungen auseinander
  liefen (`lint.yml` hier, `ci.yml` in den drei Schwesterrepos);
* dass die Hook-Menge zusicherbar ist, ohne dass eine Vorgabe sie erfindet;
* dass die aus `mcp-data-fidelity-skill` uebernommene Auflistung beschattender
  Binaries im Befund landet.
"""

from __future__ import annotations

import os
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gates import toolchain as gates  # noqa: E402
from tools.harness import CheckFailed  # noqa: E402

HOOKS = """\
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.1
    hooks:
      - id: ruff-check
      - id: ruff-format
"""


def baum(tmp_path: pathlib.Path, *, ci_name: str, hooks: str = HOOKS) -> pathlib.Path:
    """Ein Minimalbaum mit frei waehlbarem Namen der CI-Datei."""
    root = tmp_path / "repo"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / ci_name).write_text(
        "steps:\n  - run: pip install ruff==0.16.1\n", encoding="utf-8"
    )
    (root / ".pre-commit-config.yaml").write_text(hooks, encoding="utf-8")
    return root


# --------------------------------------------------------------------------
# Der Parameter, um dessentwillen die vier Fassungen zusammengelegt wurden
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ci_name", ["lint.yml", "ci.yml"])
def test_ANKER_der_workflow_pfad_ist_wirklich_ein_parameter(tmp_path, ci_name):
    """Beide Schreibweisen der Kette, dieselbe Implementierung.

    Der Pfad war der EINZIGE inhaltliche Unterschied zwischen den vier
    Fassungen. Traegt der Parameter ihn nicht wirklich, waere die
    Zusammenfuehrung eine Umbenennung statt einer Vereinigung — und die drei
    Schwesterrepos koennten das Gate in Phase 3 nicht benutzen.
    """
    root = baum(tmp_path, ci_name=ci_name)
    meldung = gates.ruff_pin_sync(root, ci_workflow=f".github/workflows/{ci_name}")
    assert "0.16.1" in meldung


def test_der_falsche_workflow_pfad_ist_ein_befund_kein_stilles_bestehen(tmp_path):
    """«Datei nicht da» darf nicht wie «Pins stimmen ueberein» aussehen."""
    root = baum(tmp_path, ci_name="ci.yml")
    with pytest.raises(CheckFailed) as befund:
        gates.ruff_pin_sync(root, ci_workflow=".github/workflows/lint.yml")
    assert "nicht lesbar" in str(befund.value)


def test_die_meldung_nennt_den_uebergebenen_pfad(tmp_path):
    """Ein Befund soll zur richtigen Datei schicken, nicht zur Vorgabe."""
    root = baum(tmp_path, ci_name="ci.yml")
    (root / ".github/workflows/ci.yml").write_text("steps: []\n", encoding="utf-8")
    with pytest.raises(CheckFailed) as befund:
        gates.ruff_pin_sync(root, ci_workflow=".github/workflows/ci.yml")
    text = str(befund.value)
    assert "ci.yml" in text
    assert "lint.yml" not in text


# --------------------------------------------------------------------------
# Die Hook-Menge — aus mcp-data-fidelity-skill uebernommen
# --------------------------------------------------------------------------


def test_ein_fehlender_geforderter_hook_ist_ein_befund(tmp_path):
    ohne_check = HOOKS.replace("      - id: ruff-check\n", "")
    root = baum(tmp_path, ci_name="ci.yml", hooks=ohne_check)
    with pytest.raises(CheckFailed) as befund:
        gates.ruff_pin_sync(
            root,
            ci_workflow=".github/workflows/ci.yml",
            required_hooks=("ruff-check", "ruff-format"),
        )
    assert "ruff-check" in str(befund.value)


def test_ANKER_ohne_angabe_wird_keine_hook_menge_erfunden(tmp_path):
    """Die Vorgabe ist LEER, und das ist die Entscheidung.

    `mcp-transport-hardening-skill` fuehrt begruendet nur `ruff-format`: Sein
    `ruff.toml` hat `select = []`, und die CI prueft gezielt statt ueber den
    ganzen Baum. Eine Vorgabe waere dort eine erfundene Zusage — und der
    erste, der sie «erfuellt», braeche die Absicht des Repos.
    """
    ohne_check = HOOKS.replace("      - id: ruff-check\n", "")
    root = baum(tmp_path, ci_name="ci.yml", hooks=ohne_check)
    assert gates.ruff_pin_sync(root, ci_workflow=".github/workflows/ci.yml")


# --------------------------------------------------------------------------
# Die Beschattung im Befundtext
# --------------------------------------------------------------------------


def test_der_befund_listet_die_beschattenden_binaries():
    """Ein blosses «falsche Version» schickt zu `pip install` — dort hilft es nicht.

    Die gepinnte Version ist dann laengst installiert, sie steht bloss hinter
    einer zweiten im PATH. Die Liste macht das sichtbar, statt es erraten zu
    lassen.
    """
    ok, meldung = gates.compare_binary(
        "0.16.1",
        "ruff 0.15.8\n",
        0,
        shadowing=["/root/.local/bin/ruff", "/usr/local/bin/ruff"],
    )
    assert not ok
    assert "/root/.local/bin/ruff" in meldung
    assert "dieser laeuft" in meldung


def test_ohne_beschattung_bleibt_die_meldung_ohne_liste():
    ok, meldung = gates.compare_binary("0.16.1", "ruff 0.15.8\n", 0)
    assert not ok
    assert "Gefunden auf dem PATH" not in meldung


def test_ruffs_on_path_liefert_die_reihenfolge_des_path(monkeypatch, tmp_path):
    erst, dann = tmp_path / "a", tmp_path / "b"
    for d in (erst, dann):
        d.mkdir()
        ruff = d / "ruff"
        ruff.write_text("", encoding="utf-8")
        ruff.chmod(0o755)
    monkeypatch.setenv("PATH", f"{erst}{os.pathsep}{dann}")
    gefunden = gates.ruffs_on_path()
    assert gefunden == [str(erst / "ruff"), str(dann / "ruff")]
