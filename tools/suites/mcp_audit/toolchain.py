"""Pruefungen an der Werkzeugkette: der ruff-Pin und die laufende ruff.

DIE REINE LOGIK STEHT NICHT HIER, SONDERN BLEIBT IN `tools/check_ruff_pin.py`
UND `tools/check_ruff_version.py`. Das ist Absicht und der einzige Punkt, an
dem dieses Repo von der Kettenkonvention abweicht:

* Der Pre-Commit-Hook ruft `python3 tools/check_ruff_pin.py` DIREKT auf
  (`.pre-commit-config.yaml`, `language: system`). Die Datei muss ihren
  Einstiegspunkt behalten, sonst bricht der Hook — und er ist das, was die
  Zusage «was lokal durchlaeuft, laeuft auch in der CI durch» ueberhaupt
  einloest.
* Beide READMEs benennen `tools/check_ruff_pin.py` namentlich als die Stelle,
  die den Pin erzwingt.

Die Alternative waere gewesen, die Funktionen hierher zu ziehen und dort
Shims zurueckzulassen. Das ergaebe zwei Dateien, wo eine reicht, und die
Frage «welche gilt?» — genau die Sorte zweiter Stelle, gegen die diese
Pruefungen existieren. Stattdessen: EINE Implementierung, zwei Einstiege.
Dieses Modul ist der Adapter, kein zweiter Ort.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from tools import check_ruff_pin as crp
from tools import check_ruff_version as crv
from tools.harness import CheckFailed, register

from ._suite import SUITE


@register(
    1, "the ruff pin agrees between lint.yml and the pre-commit hook", suite=SUITE
)
def ruff_pin_sync(root: Path) -> str:
    """Vergleicht ZWEI TEXTE — lint.yml und .pre-commit-config.yaml.

    Laufen sie auseinander, formatiert der Hook nach der einen und die CI
    prueft nach der anderen Version: der Hook meldet gruen und die CI wird
    rot. Ein fehlender Pin ist ebenfalls ein Befund; dann hat der Vergleich
    nicht stattgefunden.

    Was diese Pruefung NICHT tut, ist der Grund fuer Check 2 daneben: Ob die
    ruff, die anschliessend die Gates faehrt, diese Version traegt, sagt sie
    nicht.
    """
    workflow = root / crp.LINT_WORKFLOW
    precommit = root / crp.PRECOMMIT_CONFIG
    for path in (workflow, precommit):
        if not path.is_file():
            raise CheckFailed(f"Datei nicht lesbar: {path}")

    ok, message = crp.compare(
        workflow.read_text(encoding="utf-8"),
        precommit.read_text(encoding="utf-8"),
    )
    if not ok:
        raise CheckFailed(
            f"{message}\n"
            "  Beide Stellen im selben Commit bumpen: `rev:` in "
            f"{crp.PRECOMMIT_CONFIG.as_posix()} und `pip install ruff==…` in "
            f"{crp.LINT_WORKFLOW.as_posix()}."
        )
    return message


@register(2, "the ruff on PATH is the pinned one", suite=SUITE)
def ruff_version_matches_pin(root: Path) -> str:
    """Haelt den Text gegen das laufende Programm.

    Check 1 belegt, dass lint.yml und der Hook dieselbe Zahl nennen — nicht,
    dass die ruff, die gleich `ruff check` faehrt, diese Zahl traegt. Liegt
    eine andere weiter vorne im PATH, laufen die Gates auf einer Version, die
    niemand gepinnt hat.

    Nicht theoretisch: Bis 0.15.8 liess `ruff format --check .` Markdown
    unberuehrt, seit 0.16.1 nicht mehr. Gemessen in
    mcp-data-source-probe-skill (dort Check 18) und mehrfach in
    Entwicklungsumgebungen, in denen eine 0.15.8 die installierte 0.16.1
    verdeckte.
    """
    workflow = root / crp.LINT_WORKFLOW
    if not workflow.is_file():
        raise CheckFailed(f"Datei nicht lesbar: {workflow}")
    pins = crp.workflow_pins(workflow.read_text(encoding="utf-8"))
    pinned = pins[0] if pins else None

    # FAIL statt skip: Eine uebersprungene Pruefung meldete «bestanden», wo
    # «nicht gelaufen» richtig waere.
    executable = shutil.which("ruff")
    if executable is None:
        raise CheckFailed(
            "ruff liegt nicht auf dem PATH — die laufende Version laesst sich "
            "nicht ermitteln."
        )
    done = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, check=False
    )
    ok, message = crv.compare(pinned, done.stdout + done.stderr, done.returncode)
    if not ok:
        raise CheckFailed(f"{message}\n  Gelaufene ruff: {executable}")
    return message
