"""Alle Pruefungen dieses Repositories, als importierbares Paket.

    bash scripts/validate.sh          # der dokumentierte Weg
    python -m tools.checks            # dasselbe, ohne Umweg
    python -m tools.checks 7 8        # nur diese

Die Nummern sind stabil und tauchen im CHANGELOG und in Befunden auf («Check 7
meldet dasselbe»). Neue Pruefungen haengen sich hinten an, statt bestehende zu
verschieben. Die Nummern gelten je Repository — die Kette teilt das Geruest,
nicht die Numerierung.

Der Import der Module unten geschieht um der REGISTRIERUNG willen: `@register`
laeuft beim Import, nicht beim Aufruf. Fehlt eine Zeile, verschwindet die
Pruefung aus dem Lauf, ohne dass etwas rot wird — deshalb haelt
`test_registry_covers_every_check_module` die Registry gegen den Paketinhalt.

Wer eine Pruefung hinzufuegt, braucht dreierlei: eine `@register`-Nummer,
mindestens eine Mutation in `tests/mutations.py` — `test_every_check_has_...`
besteht darauf — und einen Eintrag im CHANGELOG.
"""

from . import github_meta, readmes, references, skill_doc, toolchain
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
    "github_meta",
    "pycache_to_temp",
    "readmes",
    "references",
    "register",
    "run",
    "run_all",
    "skill_doc",
    "toolchain",
]
