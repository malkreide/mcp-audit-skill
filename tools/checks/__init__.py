"""Alle Pruefungen dieses Repositories, als importierbares Paket.

    bash scripts/validate.sh          # der dokumentierte Weg
    python -m tools.checks            # dasselbe, ohne Umweg
    python -m tools.checks 1 2        # nur diese

WARUM ES DIESE REGISTRY HIER GIBT, obwohl die Pruefungen schon testbar waren.
Der Ertrag ist ein anderer als in den Schwesterrepos:

* EIN Lauf nennt ALLE Befunde. Vorher waren die vier Pruefungen vier
  Workflow-Schritte; der erste rote brach den Job ab, und die drei dahinter
  liefen nicht. Jeder Fehlschlag kostete eine eigene Runde.
* Die REIHENFOLGE steht in der Nummer, nicht in der Job-Datei. Check 1 (Pin)
  und 2 (laufende ruff) vor den Gates 3 und 4 — ein Lint-Befund auf einer
  ungepinnten ruff ist wertlos, und das war bisher nur durch die Reihenfolge
  der `run:`-Zeilen zugesichert.
* Ein ABSTURZ der Pruefung wird als Defekt in `tools/checks` ausgewiesen,
  nicht als Befund ueber das Repository.
* `offline` trennt, was ohne Netz und Token laeuft. Heute ist alles offline;
  das Flag steht bereit, falls eine Netz-Pruefung dazukommt.

Die Nummern sind stabil und gelten je Repository — die Kette teilt das
Geruest, nicht die Numerierung.

Der Import der Module unten geschieht um der REGISTRIERUNG willen: `@register`
laeuft beim Import. Fehlt eine Zeile, verschwindet die Pruefung aus jedem
Lauf, ohne dass etwas rot wird — deshalb haelt
`test_registry_deckt_jedes_pruefmodul_ab` die Registry gegen den Paketinhalt.
"""

from . import ruff_gate, skill_archive, toolchain
from ._core import (
    Check,
    CheckFailed,
    Result,
    all_checks,
    pycache_to_temp,
    register,
    run,
    run_all,
)

__all__ = [
    "Check",
    "CheckFailed",
    "Result",
    "all_checks",
    "pycache_to_temp",
    "register",
    "ruff_gate",
    "run",
    "run_all",
    "skill_archive",
    "toolchain",
]
