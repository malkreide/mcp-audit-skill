"""Geruest der Pruefungen, EINMAL — mit einer Registry je Suite.

Dies ist die zusammengefuehrte Fassung der vier `tools/checks/_core.py`, die
heute in `mcp-audit-skill`, `mcp-data-source-probe-skill`,
`mcp-data-fidelity-skill` und `mcp-transport-hardening-skill` nebeneinander
stehen. Gemessen beim Zusammenfuehren: Die vier Dateien unterscheiden sich in
drei Zeilen Code — `pycache_to_temp` fehlt in einer, `python_version` gibt es
nur in einer, und ein Temp-Praefix heisst anders. Alles Uebrige war Docstring
und Umlaut-Schreibweise.

WARUM EINE SUITE-SPALTE, statt einfach alle Pruefungen in einen Topf zu legen.
Die vier Registries numerieren jede fuer sich ab 1, und diese Nummern sind
zugesichert: Sie stehen in CHANGELOG-Eintraegen und in Befunden («Check 7
meldet dasselbe»). Ein Zusammenlegen in einen flachen Nummernraum haette
genau diese Zusicherung gebrochen — 53 Registrierungen, von denen 48 eine
neue Nummer bekaemen, und jede Referenz darauf in vier CHANGELOGs waere
stillschweigend falsch geworden.

Die Suite traegt die Nummer stattdessen mit: `audit/1` und `probe/1` sind
verschiedene Pruefungen, beide behalten ihre Nummer, und die Lueckenlosigkeit
wird je Suite geprueft statt ueber alles. Damit bleibt die Invariante der
Herkunftsrepos woertlich erhalten, ohne dass es vier Registries braucht.

Jede registrierte Pruefung ist eine gewoehnliche Funktion:

    (root: Path) -> str        # Erfolgsmeldung
    raises CheckFailed         # Befund, mit Diagnose im Text

*root* statt `cwd` — eine Pruefung laesst sich gegen einen Fixture-Baum
fahren, in dem gezielt ein Anker fehlt, ohne Unterprozess und ohne
Verzeichniswechsel. Das ist die Grundlage der Mutationstests unter `tests/`.

`CheckFailed` statt `sys.exit` — ein Befund ist abfangbar und sein Text
zusicherbar. Eine Pruefung, die aus dem falschen Grund rot wird, ist fast so
teuer wie eine, die gar nicht rot wird: Sie schickt den Lesenden zur falschen
Datei.
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

    `suite` sagt, zu welchem Skill die Pruefung gehoert. Sie ist Teil der
    Identitaet, nicht bloss ein Etikett: Die Nummer allein ist erst zusammen
    mit der Suite eindeutig.

    `offline` markiert, ob die Pruefung ohne Netz und ohne Token laeuft.
    `scripts/validate.sh` faehrt nur die Offline-Pruefungen — der Runner muss
    in einem Clone ohne Zugangsdaten vollstaendig durchlaufen. Die uebrigen
    ruft die CI dort auf, wo ihr Kontext existiert.
    """

    number: int
    label: str
    run: Callable[[Path], str]
    suite: str
    offline: bool = True

    @property
    def id(self) -> str:
        """Die zitierfaehige Kennung, wie sie in Befunden auftaucht."""
        return f"{self.suite}/{self.number}"


# suite -> nummer -> Check. Zwei Ebenen, damit die Lueckenlosigkeit je Suite
# pruefbar bleibt, ohne die Registrierungen nachtraeglich zu gruppieren.
_REGISTRY: dict[str, dict[int, Check]] = {}


def register(
    number: int,
    label: str,
    *,
    suite: str,
    offline: bool = True,
) -> Callable[[Callable[[Path], str]], Callable[[Path], str]]:
    """Nimmt eine Pruefung unter einer festen Nummer in ihre Suite auf.

    Die Nummer ist stabil und taucht in CHANGELOG-Eintraegen und in Befunden
    auf. Sie INNERHALB EINER SUITE doppelt zu vergeben ist ein Fehler beim
    IMPORT, nicht erst zur Laufzeit — sonst verdeckt die zweite Pruefung
    stillschweigend die erste.

    Ueber Suiten hinweg ist dieselbe Nummer dagegen erlaubt und der
    Normalfall: `audit/1` und `probe/1` existieren beide.
    """

    def decorate(fn: Callable[[Path], str]) -> Callable[[Path], str]:
        bekannt = _REGISTRY.setdefault(suite, {})
        if number in bekannt:
            raise RuntimeError(
                f"Check-Nummer {number} ist in Suite «{suite}» doppelt "
                f"vergeben: {bekannt[number].run.__name__} und {fn.__name__}"
            )
        bekannt[number] = Check(
            number=number, label=label, run=fn, suite=suite, offline=offline
        )
        return fn

    return decorate


def suites() -> list[str]:
    """Alle Suiten, die etwas registriert haben, in stabiler Reihenfolge."""
    return sorted(_REGISTRY)


def all_checks(
    *,
    suite: str | None = None,
    offline_only: bool = False,
) -> list[Check]:
    """Alle registrierten Pruefungen, nach Suite und Nummer sortiert.

    Ohne `suite` liefert die Funktion den ganzen Baum — das ist, was ein Lauf
    ueber das gesamte Repository braucht. Mit `suite` nur deren Pruefungen;
    so faehrt die CI den Anteil, der zu den geaenderten Pfaden gehoert.
    """
    gewaehlt = _REGISTRY if suite is None else {suite: _REGISTRY.get(suite, {})}
    checks = [gewaehlt[s][n] for s in sorted(gewaehlt) for n in sorted(gewaehlt[s])]
    if offline_only:
        checks = [c for c in checks if c.offline]
    return checks


@contextlib.contextmanager
def pycache_to_temp(*, prefix: str = "harness-pycache-") -> Iterator[None]:
    """Lenkt Bytecode-Caches aus dem Arbeitsbaum in ein Temp-Verzeichnis.

    Ein Import schreibt `__pycache__/` neben die Quelle — und dieses
    Repository faehrt eine Pruefung, die getrackten Bytecode beanstandet. Eine
    Pruefung, die die naechste rot macht, ist kein Befund, sondern ein
    Eigentor.

    Das Praefix ist ein Parameter, weil die vier Herkunftsrepos hier je einen
    eigenen String hatten. Der Unterschied hat nie etwas getragen; als
    Vorgabewert kostet er auch nichts.
    """
    previous = sys.pycache_prefix
    with tempfile.TemporaryDirectory(prefix=prefix) as tmp:
        sys.pycache_prefix = tmp
        try:
            yield
        finally:
            sys.pycache_prefix = previous


def python_version() -> str:
    """Die laufende Python-Version, wie der Runner sie ausweist."""
    return sys.version.split()[0]


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
                "tools/harness, kein Befund ueber das Repository.\n"
                f"{traceback.format_exc()}"
            ),
        )


def run_all(root: Path, checks: Sequence[Check]) -> list[Result]:
    """Faehrt alle Pruefungen, auch nach einem Fehlschlag.

    Ein Lauf soll jedes Problem auf einmal nennen. Nach dem ersten Befund
    abzubrechen heisst, dass jeder Fehlschlag genau eine Runde kostet.
    """
    return [run(check, root) for check in checks]
