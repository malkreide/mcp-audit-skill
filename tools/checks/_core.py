"""Gerüst der Prüfungen: Befund-Exception, Registry, Ausführung.

Bis 1.6.0 standen diese Prüfungen als Python-Heredocs in
`scripts/validate.sh` und in `.github/workflows/ci.yml`. Das war billig zu
schreiben und praktisch nicht zu testen: Ein Heredoc lässt sich nur
ausführen, indem man das ganze Repository in genau den Zustand bringt, den es
beanstanden soll. Entsprechend war nie belegt, ob eine Prüfung überhaupt
beisst — ausgerechnet der Fehler, gegen den diese Prüfungen gerichtet sind.
Check 12 ist der Beleg, dass das kein theoretisches Risiko ist: Die beiden
Ruff-Gates liefen eine Zeit lang auf `select = []`, meldeten grün und niemand
merkte es.

Deshalb ist jede Prüfung jetzt eine gewöhnliche Funktion:

    (root: Path) -> str        # Erfolgsmeldung
    raises CheckFailed         # Befund, mit Diagnose im Text

Zwei Eigenschaften folgen daraus, und beide sind der eigentliche Zweck:

*root* statt `cwd` — eine Prüfung lässt sich gegen einen Fixture-Baum fahren,
in dem gezielt ein Anker fehlt. Das ist die Grundlage der Mutationstests unter
`tests/`.

`CheckFailed` statt `sys.exit` — ein Befund ist abfangbar und sein Text
zusicherbar. `sys.exit` beendet den Prozess; ein Test hätte nur «nicht 0»
prüfen können, nicht *warum*. Eine Prüfung, die aus dem falschen Grund rot
wird, ist fast so teuer wie eine, die gar nicht rot wird — sie schickt den
Lesenden zur falschen Datei.
"""

from __future__ import annotations

import contextlib
import dataclasses
import sys
import tempfile
import traceback
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path


class CheckFailed(Exception):
    """Eine Prüfung hat einen Befund.

    Der Text ist das Produkt: Er sagt, was nicht stimmt, und wo möglich, an
    welcher der beiden beteiligten Stellen jemand nachziehen muss. Die
    Mutationstests sichern genau diesen Text zu, nicht nur den Fehlschlag.
    """


@dataclasses.dataclass(frozen=True)
class Check:
    """Eine registrierte Prüfung.

    `offline` markiert, ob die Prüfung ohne Netz und ohne Token läuft.
    `scripts/validate.sh` fährt nur die Offline-Prüfungen — der Runner muss in
    einem Clone ohne Zugangsdaten vollständig durchlaufen. Die eine
    Online-Prüfung ruft die CI zusätzlich auf.
    """

    number: int
    label: str
    run: Callable[[Path], str]
    offline: bool = True


_REGISTRY: dict[int, Check] = {}


def register(
    number: int,
    label: str,
    *,
    offline: bool = True,
) -> Callable[[Callable[[Path], str]], Callable[[Path], str]]:
    """Nimmt eine Prüfung unter einer festen Nummer in die Registry auf.

    Die Nummer ist stabil und taucht in CHANGELOG-Einträgen und in Befunden
    auf («Check 12 hätte das gefangen»). Sie doppelt zu vergeben ist ein
    Fehler beim Import, nicht erst zur Laufzeit — sonst verdeckt die zweite
    Prüfung stillschweigend die erste.
    """

    def decorate(fn: Callable[[Path], str]) -> Callable[[Path], str]:
        if number in _REGISTRY:
            raise RuntimeError(
                f"Check-Nummer {number} ist doppelt vergeben: "
                f"{_REGISTRY[number].run.__name__} und {fn.__name__}"
            )
        _REGISTRY[number] = Check(number=number, label=label, run=fn, offline=offline)
        return fn

    return decorate


def all_checks(*, offline_only: bool = False) -> list[Check]:
    """Alle registrierten Prüfungen, nach Nummer sortiert."""
    checks = [_REGISTRY[i] for i in sorted(_REGISTRY)]
    if offline_only:
        checks = [c for c in checks if c.offline]
    return checks


@contextlib.contextmanager
def pycache_to_temp() -> Iterator[None]:
    """Lenkt Bytecode-Caches aus dem Arbeitsbaum in ein Temp-Verzeichnis.

    Ein Import schreibt `__pycache__/` neben die Quelle. Genau so kam hier
    schon einmal eine `.pyc` in den Commit (CHANGELOG 1.1.0, Removed) — und
    Check 4 würde sie beim nächsten Lauf zu Recht anmahnen, ausgelöst durch
    Check 3. Eine Prüfung, die die nächste rot macht, ist kein Befund,
    sondern ein Eigentor.
    """
    previous = sys.pycache_prefix
    with tempfile.TemporaryDirectory(prefix="probe-pycache-") as tmp:
        sys.pycache_prefix = tmp
        try:
            yield
        finally:
            sys.pycache_prefix = previous


@dataclasses.dataclass(frozen=True)
class Result:
    check: Check
    ok: bool
    output: str


def run(check: Check, root: Path) -> Result:
    """Führt eine Prüfung aus und fängt ihren Befund ab.

    Ein Absturz der Prüfung selbst (TypeError, kaputtes Regex, …) ist ein
    Fehlschlag mit Traceback, kein durchschlagender Abbruch: Sonst nähme ein
    defekter Check den restlichen Lauf mit, und ein roter Lauf zeigte einen
    statt aller Befunde. Er wird aber ausdrücklich als Defekt der Prüfung
    ausgewiesen — «der Check ist abgestürzt» ist eine andere Nachricht als
    «das Repository hat einen Befund».
    """
    try:
        return Result(check=check, ok=True, output=check.run(root))
    except CheckFailed as exc:
        return Result(check=check, ok=False, output=str(exc))
    except Exception:
        return Result(
            check=check,
            ok=False,
            output=(
                "Die Prüfung selbst ist abgestürzt — das ist ein Defekt in "
                f"tools/checks, kein Befund über das Repository.\n"
                f"{traceback.format_exc()}"
            ),
        )


def run_all(root: Path, checks: Sequence[Check]) -> list[Result]:
    """Fährt alle Prüfungen, auch nach einem Fehlschlag.

    Ein Lauf soll jedes Problem auf einmal nennen. Nach dem ersten Befund
    abzubrechen heisst, dass jeder Fehlschlag genau eine Runde kostet.
    """
    return [run(check, root) for check in checks]
