"""Der Ruff-Pin steht an zwei Stellen. Sie müssen dasselbe sagen.

Einmal als `pip install ruff==…` in `.github/workflows/ci.yml`, einmal als
`rev` des Pre-Commit-Hooks. Laufen sie auseinander, formatiert der Hook nach
der einen und die CI prüft nach der anderen Version: Der Commit geht lokal
grün durch und wird erst im Pull Request rot — die teuerste Reihenfolge.

Dasselbe gilt für die Menge der Hooks. Die Gates sind `ruff check` UND
`ruff format --check` (Prüfungen 10 und 11). Fällt einer der beiden Hooks
weg, läuft er lokal nicht mehr, und es entsteht dieselbe Bruchstelle eine
Zeile weiter unten.

Ein fehlender Pin ist ebenfalls ein Befund, nicht ein Grund zum Überspringen:
Dann hat der Vergleich nicht stattgefunden.
"""

from __future__ import annotations

import re
from pathlib import Path

from ._core import CheckFailed, register

CI = ".github/workflows/ci.yml"
HOOKS = ".pre-commit-config.yaml"

CI_PIN = re.compile(r"ruff==(?P<version>\d[^\s\"']*)")
HOOK_REV = re.compile(
    r"ruff-pre-commit.*?^\s*rev:\s*v?(?P<version>\d\S*)\s*$",
    re.S | re.M,
)
REQUIRED_HOOKS = ("ruff-check", "ruff-format")


def _read(root: Path, name: str) -> str:
    path = root / name
    if not path.is_file():
        raise CheckFailed(
            f"{name} fehlt — ohne die Datei gibt es nichts zu vergleichen"
        )
    return path.read_text(encoding="utf-8")


@register(12, "the ruff pin agrees between CI and the pre-commit hook")
def ruff_pin_sync(root: Path) -> str:
    ci = _read(root, CI)
    hooks = _read(root, HOOKS)

    ci_pin = CI_PIN.search(ci)
    if not ci_pin:
        raise CheckFailed(
            f"{CI} nennt kein 'ruff==<version>' — entweder wurde der Pin gelöst "
            "(dann ändert ein Upstream-Release Formatter oder Regelsatz zu "
            "einem Zeitpunkt, den niemand gewählt hat) oder der Schritt ist "
            "ganz weg"
        )
    hook_rev = HOOK_REV.search(hooks)
    if not hook_rev:
        raise CheckFailed(
            f"{HOOKS} nennt keine rev für ruff-pre-commit — ohne sie gibt es "
            "keine zweite Version zu vergleichen, und der lokale Hook läuft auf "
            "irgendetwas"
        )

    if ci_pin.group("version") != hook_rev.group("version"):
        raise CheckFailed(
            f"Ruff-Pins laufen auseinander — {CI} sagt {ci_pin.group('version')}, "
            f"der Hook sagt {hook_rev.group('version')}.\n"
            "  Der Hook formatiert dann nach der einen und die CI prüft nach "
            "der anderen Version: lokal grün, im Pull Request rot. Beide im "
            "selben Commit anheben."
        )

    missing = [
        hook
        for hook in REQUIRED_HOOKS
        if not re.search(rf"^\s*-\s*id:\s*{re.escape(hook)}\s*$", hooks, re.M)
    ]
    if missing:
        raise CheckFailed(
            f"{HOOKS} führt {missing} nicht mehr. Die Prüfungen 10 und 11 "
            "prüfen beides; läuft lokal nur eines, meldet der Commit grün und "
            "erst die CI rot."
        )

    return (
        f"Ruff-Pin {ci_pin.group('version')} in {CI} und {HOOKS}, "
        f"{len(REQUIRED_HOOKS)} Hooks vorhanden"
    )
