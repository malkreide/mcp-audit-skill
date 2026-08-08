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
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ._core import CheckFailed, register

FEHLT = (
    "ruff liegt nicht auf dem PATH — dieses Gate kann nicht laufen. FAIL statt "
    "skip: «nicht gelaufen» als «bestanden» zu melden ist die eine Auskunft, "
    "die schlimmer ist als keine."
)


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


@register(3, "ruff check passes on the whole tree")
def ruff_check(root: Path) -> str:
    done = _ruff(root, "check", ".")
    if done.returncode != 0:
        raise CheckFailed((done.stdout + done.stderr).strip())
    return (done.stdout or "All checks passed!").strip()


@register(4, "ruff format leaves the tree unchanged")
def ruff_format(root: Path) -> str:
    done = _ruff(root, "format", "--check", ".")
    if done.returncode != 0:
        raise CheckFailed(
            (done.stdout + done.stderr).strip()
            + "\n  `ruff format .` raeumt das auf; der Pre-Commit-Hook tut es "
            "vor jedem Commit."
        )
    return (done.stdout or "already formatted").strip()
