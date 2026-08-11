"""Die Gates dieses Repositories — Suite `audit`.

    bash scripts/validate.sh                 # der dokumentierte Weg
    python -m tools.harness --suite audit    # dasselbe, nur diese Suite
    python -m tools.harness audit/1 audit/2  # nur diese Pruefungen

WARUM ES DIESE SUITE GIBT, obwohl die Pruefungen schon testbar waren. Der
Ertrag ist ein anderer als in den Schwesterrepos:

* EIN Lauf nennt ALLE Befunde. Vorher waren die vier Pruefungen vier
  Workflow-Schritte; der erste rote brach den Job ab, und die drei dahinter
  liefen nicht. Jeder Fehlschlag kostete eine eigene Runde.
* Die REIHENFOLGE steht in der Nummer, nicht in der Job-Datei. Check 1 (Pin)
  und 2 (laufende ruff) vor den Gates 3 und 4 — ein Lint-Befund auf einer
  ungepinnten ruff ist wertlos, und das war bisher nur durch die Reihenfolge
  der `run:`-Zeilen zugesichert.
* Ein ABSTURZ der Pruefung wird als Defekt im Geruest ausgewiesen, nicht als
  Befund ueber das Repository.

DIE NUMMERN SIND UNVERAENDERT GEBLIEBEN. Sie hiessen vor der
Zusammenfuehrung 1 bis 5 und heissen jetzt `audit/1` bis `audit/5` — die Zahl
dahinter ist dieselbe, weil sie im CHANGELOG und in `release.yml` zitiert
wird. Genau dafuer traegt die Registry eine Suite-Spalte.

Der Import der Module unten geschieht um der REGISTRIERUNG willen: `@register`
laeuft beim Import. Fehlt eine Zeile, verschwindet die Pruefung aus jedem
Lauf, ohne dass etwas rot wird — deshalb haelt
`test_registry_deckt_jedes_pruefmodul_ab` die Zeile gegen den Paketinhalt.
"""

from . import (
    counts,
    hygiene,
    release,
    ruff_gate,
    skill_archive,
    skill_doc,
    toolchain,
)
from ._suite import SUITE

__all__ = [
    "SUITE",
    "counts",
    "hygiene",
    "release",
    "ruff_gate",
    "skill_archive",
    "skill_doc",
    "toolchain",
]
