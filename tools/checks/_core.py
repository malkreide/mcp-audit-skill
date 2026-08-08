"""Geruest der Pruefungen: Befund-Exception, Registry, Ausfuehrung.

Uebernommen aus `mcp-data-source-probe-skill` und `mcp-data-fidelity-skill`,
damit die Kette EIN Geruest fuehrt statt fuenf aehnliche. Die Vorgeschichte
hier ist dieselbe: Bis vor Kurzem standen diese Pruefungen als Heredocs in
`.github/workflows/ci.yml` — billig zu schreiben und praktisch nicht zu
testen, denn ein Heredoc laesst sich nur ausfuehren, indem man das ganze
Repository in genau den Zustand bringt, den es beanstanden soll.

Der Zwischenschritt waren eigenstaendige Skripte mit `sys.exit`. Testbar
wurden sie damit nur ueber einen Unterprozess, und zusicherbar war die
Meldung nur als Teilzeichenkette der vereinigten Ausgabe. Jede Pruefung ist
jetzt eine gewoehnliche Funktion:

    (root: Path) -> str        # Erfolgsmeldung
    raises CheckFailed         # Befund, mit Diagnose im Text

Zwei Eigenschaften folgen daraus, und beide sind der eigentliche Zweck:

*root* statt `cwd` — eine Pruefung laesst sich gegen einen Fixture-Baum
fahren, in dem gezielt ein Anker fehlt, ohne Unterprozess und ohne
Verzeichniswechsel. Das ist die Grundlage der Mutationstests unter `tests/`.

`CheckFailed` statt `sys.exit` — ein Befund ist abfangbar und sein Text
zusicherbar. `sys.exit` beendet den Prozess; ein Test konnte nur «nicht 0»
pruefen, nicht *warum*. Eine Pruefung, die aus dem falschen Grund rot wird,
ist fast so teuer wie eine, die gar nicht rot wird — sie schickt den Lesenden
zur falschen Datei.
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
    """Eine Pruefung hat einen Befund.

    Der Text ist das Produkt: Er sagt, was nicht stimmt, und wo moeglich, an
    welcher der beteiligten Stellen jemand nachziehen muss. Die
    Mutationstests sichern genau diesen Text zu, nicht nur den Fehlschlag.
    """


@dataclasses.dataclass(frozen=True)
class Check:
    """Eine registrierte Pruefung.

    `offline` markiert, ob die Pruefung ohne Netz und ohne Token laeuft.
    `scripts/validate.sh` faehrt nur die Offline-Pruefungen — der Runner muss
    in einem Clone ohne Zugangsdaten vollstaendig durchlaufen. Die eine
    Online-Pruefung ruft die CI zusaetzlich auf.
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
    """Nimmt eine Pruefung unter einer festen Nummer in die Registry auf.

    Die Nummer ist stabil und taucht in CHANGELOG-Eintraegen und in Befunden
    auf («Check 7 meldet dasselbe»). Sie doppelt zu vergeben ist ein Fehler
    beim IMPORT, nicht erst zur Laufzeit — sonst verdeckt die zweite Pruefung
    stillschweigend die erste.
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
    """Alle registrierten Pruefungen, nach Nummer sortiert."""
    checks = [_REGISTRY[i] for i in sorted(_REGISTRY)]
    if offline_only:
        checks = [c for c in checks if c.offline]
    return checks


@contextlib.contextmanager
def pycache_to_temp() -> Iterator[None]:
    """Lenkt Bytecode-Caches aus dem Arbeitsbaum in ein Temp-Verzeichnis.

    Ein Import schreibt `__pycache__/` neben die Quelle — und dieses
    Repository faehrt eine Pruefung, die getrackten Bytecode beanstandet. Eine
    Pruefung, die die naechste rot macht, ist kein Befund, sondern ein
    Eigentor.
    """
    previous = sys.pycache_prefix
    with tempfile.TemporaryDirectory(prefix="transport-pycache-") as tmp:
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
    """Fuehrt eine Pruefung aus und faengt ihren Befund ab.

    Ein Absturz der Pruefung selbst (TypeError, kaputtes Regex, …) ist ein
    Fehlschlag mit Traceback, kein durchschlagender Abbruch: Sonst naehme ein
    defekter Check den restlichen Lauf mit, und ein roter Lauf zeigte einen
    statt aller Befunde. Er wird aber ausdruecklich als Defekt der Pruefung
    ausgewiesen — «der Check ist abgestuerzt» ist eine andere Nachricht als
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
                "Die Pruefung selbst ist abgestuerzt — das ist ein Defekt in "
                "tools/checks, kein Befund ueber das Repository.\n"
                f"{traceback.format_exc()}"
            ),
        )


def run_all(root: Path, checks: Sequence[Check]) -> list[Result]:
    """Faehrt alle Pruefungen, auch nach einem Fehlschlag.

    Ein Lauf soll jedes Problem auf einmal nennen. Nach dem ersten Befund
    abzubrechen heisst, dass jeder Fehlschlag genau eine Runde kostet.
    """
    return [run(check, root) for check in checks]
