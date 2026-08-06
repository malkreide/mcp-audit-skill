"""Alle Prüfungen dieses Repositories, als importierbares Paket.

    bash scripts/validate.sh          # der dokumentierte Weg
    python -m tools.checks            # dasselbe, ohne Umweg
    python -m tools.checks 12 13 14   # nur diese

Die Nummern sind stabil und tauchen im CHANGELOG und in Befunden auf. Neue
Prüfungen hängen sich hinten an, statt bestehende zu verschieben.

Der Import der Module unten geschieht um der Registrierung willen: `@register`
läuft beim Import, nicht beim Aufruf. Fehlt eine Zeile, verschwindet die
Prüfung aus dem Lauf, ohne dass etwas rot wird — deshalb hält
`test_registry_covers_every_module` die Registry gegen den Paketinhalt.

Wer eine Prüfung hinzufügt, braucht dreierlei: eine `@register`-Nummer,
mindestens eine Mutation in `tests/mutations.py` — `test_every_check_has_mutations`
besteht darauf — und einen Eintrag im CHANGELOG.
"""

from . import (
    github_meta,
    hygiene,
    readmes,
    references,
    ruff_gate,
    skill_doc,
    toolchain,
)
from ._core import (
    Check,
    CheckFailed,
    Result,
    all_checks,
    register,
    run,
    run_all,
)

__all__ = [
    "Check",
    "CheckFailed",
    "Result",
    "all_checks",
    "github_meta",
    "hygiene",
    "readmes",
    "references",
    "register",
    "ruff_gate",
    "run",
    "run_all",
    "skill_doc",
    "toolchain",
]
