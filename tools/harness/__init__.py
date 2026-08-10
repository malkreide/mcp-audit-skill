"""Das gemeinsame Geruest der Pruefungen, fuer alle Skills dieses Repos.

    bash scripts/validate.sh              # der dokumentierte Weg
    python -m tools.harness               # dasselbe, ohne Umweg
    python -m tools.harness --suite audit # nur eine Suite

WAS HIER ANDERS IST als in `tools/checks/`. Jenes Paket fuehrt die Gates
dieses Repositories unter einem flachen Nummernraum. Dieses hier fuehrt die
Gates ALLER vier Skills, die in dieses Repository zusammenlaufen, und traegt
dafuer die Suite in der Kennung mit. `tools/checks/` geht in Phase 1 der
Zusammenfuehrung darin auf; bis dahin stehen beide nebeneinander, damit die
Umstellung nicht am selben Tag stattfinden muss wie der Umzug der Inhalte.
Der Plan dazu steht in `docs/consolidation/MERGE-PLAN.md`.

WARUM DIE PRUEFMODULE HIER NICHT IMPORTIERT WERDEN. In den Herkunftsrepos
listet `__init__.py` jedes Pruefmodul auf, weil `@register` beim Import
laeuft — fehlt eine Zeile, verschwindet die Pruefung lautlos aus jedem Lauf.
Diese Liste bleibt, sie zieht aber je Suite in `tools/suites/<name>/`, und ein
Test haelt sie gegen den Paketinhalt. Hier steht nur das Geruest, das alle
teilen; es kennt seine Pruefungen nicht, sondern nimmt sie entgegen.
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
