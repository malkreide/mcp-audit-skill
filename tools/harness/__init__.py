"""Das gemeinsame Geruest der Pruefungen, fuer alle Skills dieses Repos.

    bash scripts/validate.sh              # der dokumentierte Weg
    python -m tools.harness               # dasselbe, ohne Umweg
    python -m tools.harness --suite audit # nur eine Suite

DIESES PAKET KENNT KEINE EINZIGE PRUEFUNG. Es fuehrt die Registry, faengt
Befunde ab und fasst zusammen — welche Pruefungen es gibt, steht unter
`tools/suites/<name>/`, eine Suite je Skill. Bis Phase 1 lag daneben noch ein
zweites Geruest unter `tools/checks/`; es ist in diesem aufgegangen.

WARUM DIE PRUEFMODULE HIER NICHT IMPORTIERT WERDEN. In den Herkunftsrepos
listet `__init__.py` jedes Pruefmodul auf, weil `@register` beim Import
laeuft — fehlt eine Zeile, verschwindet die Pruefung lautlos aus jedem Lauf.
Diese Liste bleibt, sie steht aber je Suite in `tools/suites/<name>/__init__.py`,
und ein Test haelt sie gegen den Paketinhalt. Die eine Stelle, die weiss,
welche Suiten es in DIESEM Baum gibt, ist `__main__.py` — der Einstiegspunkt,
nicht das Geruest. So bleibt das Geruest kopierbar.

Der Plan der Zusammenfuehrung steht in `docs/consolidation/MERGE-PLAN.md`.
"""

from ._core import (
    Check,
    CheckFailed,
    Result,
    all_checks,
    pycache_to_temp,
    python_version,
    register,
    run,
    run_all,
    suites,
)

__all__ = [
    "Check",
    "CheckFailed",
    "Result",
    "all_checks",
    "pycache_to_temp",
    "python_version",
    "register",
    "run",
    "run_all",
    "suites",
]
