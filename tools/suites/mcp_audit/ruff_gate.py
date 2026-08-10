"""Die Ruff-Gates selbst, als Pruefungen statt als Workflow-Zeilen.

Sie standen bis hierher als zwei nackte `run:`-Zeilen in `lint.yml`. Das
funktionierte, hatte aber zwei Kosten, die erst mit der Registry sichtbar
werden:

* Sie liefen VOR Check 1 und 2 in derselben Job-Reihenfolge, aber ohne
  Zusammenhang. Als registrierte Pruefungen entscheidet die NUMMER, und die
  sagt: erst der Pin (1), dann die laufende ruff (2), dann die Gates (3, 4).
  Ein Befund von Check 3 auf einer ungepinnten ruff ist wertlos.
* Ein rotes Gate brach den Job ab, und alles dahinter lief nicht. `run_all`
  bricht nicht ab — ein Lauf nennt Lint- UND Format-Befunde auf einmal.

Beide Gates fahren ueber den ganzen Baum, wie zuvor. Die Konfiguration kommt
aus `ruff.toml`; hier stehen bewusst keine Regeln, sonst waere das eine
zweite Stelle, an der der Regelsatz steht.

DIE URTEILSLOGIK IST VOM UNTERPROZESS GETRENNT (`bewerte`). Das ist keine
Stilfrage: Die Testsuite dieses Repos laeuft auf Linux UND Windows, und der
pytest-Job installiert kein ruff — das liegt im lint-Job. Ein Test, der eine
echte oder untergeschobene ruff braucht, pruefte damit die Testumgebung statt
den Code, und ein `#!/bin/sh`-Shim faellt unter Windows ohnehin um. Was hier
schiefgehen kann, haengt an einem Exit-Code und einem Text — beides Werte.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from tools.harness import CheckFailed, register

from ._suite import SUITE

FEHLT = (
    "ruff liegt nicht auf dem PATH — dieses Gate kann nicht laufen. FAIL statt "
    "skip: «nicht gelaufen» als «bestanden» zu melden ist die eine Auskunft, "
    "die schlimmer ist als keine."
)

HINWEIS_FORMAT = (
    "\n  `ruff format .` raeumt das auf; der Pre-Commit-Hook tut es vor jedem Commit."
)


def bewerte(kind: str, returncode: int, ausgabe: str) -> tuple[bool, str]:
    """Rein: `(gruen, Meldung)` aus Exit-Code und Ausgabe.

    Kein PATH, kein Unterprozess — dieselbe Bauart wie `compare()` in
    `tools/check_ruff_pin.py`, und aus demselben Grund: Der Teil, der
    schiefgehen kann, soll als Wert pruefbar sein.
    """
    text = ausgabe.strip()
    if returncode == 0:
        return True, text or ("All checks passed!" if kind == "check" else "formatted")
    if kind == "format":
        return False, text + HINWEIS_FORMAT
    return False, text


def _ruff(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("ruff")
    if executable is None:
        raise CheckFailed(FEHLT)
    return subprocess.run(
        [executable, *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _gate(root: Path, kind: str, *args: str) -> str:
    done = _ruff(root, *args)
    ok, message = bewerte(kind, done.returncode, done.stdout + done.stderr)
    if not ok:
        raise CheckFailed(message)
    return message


@register(3, "ruff check passes on the whole tree", suite=SUITE)
def ruff_check(root: Path) -> str:
    return _gate(root, "check", "check", ".")


@register(4, "ruff format leaves the tree unchanged", suite=SUITE)
def ruff_format(root: Path) -> str:
    return _gate(root, "format", "format", "--check", ".")
