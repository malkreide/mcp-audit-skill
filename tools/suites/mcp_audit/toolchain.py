"""Pruefungen an der Werkzeugkette — die Bindung der generischen Gates.

DIE LOGIK STEHT NICHT HIER, SONDERN IN `tools/gates/toolchain.py`. Sie ist
dieselbe wie in den drei Schwesterrepos; was sich unterscheidet, sind zwei
Werte, und die stehen unten.

DASS SIE AUCH NICHT MEHR IN `tools/check_ruff_pin.py` STEHT, ist die
Aenderung aus Phase 2. Vorher war es umgekehrt: Das Skript trug die
Vergleichsfunktion, weil der Pre-Commit-Hook es direkt aufruft
(`.pre-commit-config.yaml`, `language: system`), und dieses Modul war der
Adapter. Mit der Zusammenfuehrung waeren daraus zwei Implementierungen
geworden — die generische fuer die vier Suiten und die alte fuer den Hook.
Jetzt traegt `tools/gates/` die Logik, und BEIDE Einstiege sind Huellen
darum: dieses Modul fuer die Registry, `tools/check_ruff_pin.py` fuer den
Hook. Der Einstiegspunkt des Hooks ist unveraendert geblieben; beide READMEs
nennen ihn namentlich.
"""

from __future__ import annotations

from pathlib import Path

from tools.gates import toolchain as gates
from tools.harness import register

from ._suite import SUITE

#: Der Pin steht hier in `lint.yml`, in den drei Schwesterrepos in `ci.yml` —
#: der einzige Grund, warum diese Dateien je auseinanderliefen.
CI_WORKFLOW = ".github/workflows/lint.yml"

#: Die Hooks, die dieses Repo lokal fahren MUSS. Ausdruecklich genannt und
#: nicht geerbt: `mcp-transport-hardening-skill` fuehrt begruendet nur
#: `ruff-format` — dort steht `select = []` in `ruff.toml`, und die CI prueft
#: gezielt statt ueber den ganzen Baum. Eine Vorgabe waere dort eine erfundene
#: Zusage statt einer gemeinsamen.
REQUIRED_HOOKS = ("ruff-check", "ruff-format")


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
    return gates.ruff_pin_sync(
        root, ci_workflow=CI_WORKFLOW, required_hooks=REQUIRED_HOOKS
    )


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
    return gates.ruff_version_matches_pin(root, ci_workflow=CI_WORKFLOW)
