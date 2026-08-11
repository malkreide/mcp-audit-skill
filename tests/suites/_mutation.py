"""Die Bausteine, aus denen eine Mutation besteht.

Zusammengefuehrt aus den drei Herkunftsrepos, die je eine eigene Fassung
fuehrten. Zwei Formate lagen vor: `mcp-data-source-probe-skill` und
`mcp-data-fidelity-skill` schrieben eine Dataclass mit PRUEFNUMMER,
`mcp-transport-hardening-skill` ein Tupel mit dem FUNKTIONSNAMEN. Hier gilt
der Funktionsname, und zwar nicht aus Geschmack:

Die Nummern sind seit Phase 0 suite-lokal — `audit/1` und `probe/1` gibt es
beide. Eine Mutation, die «1» sagt, muesste also zusaetzlich sagen, welche
Suite gemeint ist, und dieselbe Angabe stuende dann zweimal da. Der
Funktionsname ist ueber alle Suiten eindeutig und sagt ausserdem beim Lesen,
worum es geht.

WAS EINE MUTATION NENNEN MUSS, und alle drei Teile sind Pflicht:

  * WELCHE Pruefung sie treffen soll,
  * WAS sie kaputt macht — als Delta auf einer Kopie des echten Baums, nicht
    als handgeschriebene Attrappe (siehe `conftest.py`),
  * WELCHER Teil des Befundes dabei herauskommen muss.

DAS DRITTE IST NICHT ZIERDE. «Wird rot» genuegt nicht: Eine Pruefung, die aus
dem falschen Grund rot wird, schickt den Lesenden zur falschen Datei — und ist
beim naechsten Mal aus dem falschen Grund gruen.

UND EINE MUTATION, DIE NICHT GREIFT, IST EIN FEHLER. Sucht sie Text, den es
nicht mehr gibt, wirft sie `MutationStale`, statt still nichts zu tun. Sonst
waere eine veraltete Mutation ein Test, der nichts mehr testet — genau der
Fehler, gegen den die Pruefungen gerichtet sind, eine Ebene hoeher.
"""

from __future__ import annotations

import dataclasses
import re
import shutil
from collections.abc import Callable
from pathlib import Path


class MutationStale(AssertionError):
    """Die Mutation greift nicht mehr — sie sucht etwas, das es nicht gibt."""


@dataclasses.dataclass(frozen=True)
class Mutation:
    """Ein Defekt, die Pruefung, die ihn fangen muss, und ihr Befund."""

    #: Der Name der Prueffunktion, z.B. `"rule_count_consistent"`.
    check: str
    #: Kurz und sprechend; steht als pytest-`id` im Lauf.
    name: str
    apply: Callable[[Path], None]
    #: Teilzeichenkette, die im Befund vorkommen MUSS.
    expect: str


# --------------------------------------------------------------------------
# Bausteine
# --------------------------------------------------------------------------


def _lies(root: Path, rel: str) -> tuple[Path, str]:
    pfad = root / rel
    if not pfad.is_file():
        raise MutationStale(f"{rel} gibt es im Fixture-Baum nicht (mehr)")
    return pfad, pfad.read_text(encoding="utf-8")


def replace(rel: str, alt: str, neu: str, *, count: int = -1) -> Callable[[Path], None]:
    """Woertlich ersetzen — ALLE Vorkommen, wie `str.replace`.

    Findet sich `alt` nicht, ist das ein Fehler. Und `count=-1` ist derselbe
    gemessene Vorgabewert wie bei `regex_sub`: `retry_backoff.py` ruft
    `random.random()` ZWEIMAL — einmal fuer den `Retry-After`-Hinweis, einmal
    fuer den regulaeren Backoff. Nur das erste zu ersetzen liess die Vorlage
    weiterhin jittern, und die Mutation blieb gruen, ohne dass es auffiel.
    """

    def apply(root: Path) -> None:
        pfad, text = _lies(root, rel)
        if alt not in text:
            raise MutationStale(f"{rel}: {alt!r} steht dort nicht (mehr)")
        pfad.write_text(text.replace(alt, neu, count), encoding="utf-8")

    return apply


def regex_sub(
    rel: str, muster: str, ersatz: str, *, count: int = 0, flags: int = re.M
) -> Callable[[Path], None]:
    """ALLE Treffer, nicht der erste — `count=0` wie bei `re.subn`.

    Der Vorgabewert ist gemessen und nicht geraten. Mit `count=1` gingen drei
    Mutationen daneben, und zwar leise falsch: «alle Regel-Ueberschriften
    umbenannt» benannte eine um und liess dreizehn stehen, «alle
    Release-Ueberschriften umformatiert» eine von vielen. Die Pruefung wurde
    dann zwar rot — aber mit dem Befund fuer einen ganz anderen Defekt, und
    genau das ist der Fall, den die `expect`-Zusicherung fangen soll.
    """

    def apply(root: Path) -> None:
        pfad, text = _lies(root, rel)
        neu, n = re.subn(muster, ersatz, text, count=count, flags=flags)
        if n == 0:
            raise MutationStale(f"{rel}: das Muster {muster!r} greift nicht (mehr)")
        pfad.write_text(neu, encoding="utf-8")

    return apply


def append(rel: str, text: str) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        pfad, alt = _lies(root, rel)
        pfad.write_text(alt + text, encoding="utf-8")

    return apply


def write(rel: str, text: str) -> Callable[[Path], None]:
    """Ueberschreibt oder legt an. Kein Waechter — das IST der neue Inhalt."""

    def apply(root: Path) -> None:
        pfad = root / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")

    return apply


def remove(rel: str) -> Callable[[Path], None]:
    """Loescht Datei oder Verzeichnis. Was es nicht gibt, ist ein Fehler."""

    def apply(root: Path) -> None:
        ziel = root / rel
        if ziel.is_dir():
            shutil.rmtree(ziel)
        elif ziel.exists():
            ziel.unlink()
        else:
            raise MutationStale(f"{rel} gibt es im Fixture-Baum nicht (mehr)")

    return apply


def drop_last_line(rel: str) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        pfad, text = _lies(root, rel)
        zeilen = text.splitlines(keepends=True)
        if not zeilen:
            raise MutationStale(f"{rel} ist leer")
        pfad.write_text("".join(zeilen[:-1]), encoding="utf-8")

    return apply


def chain(*schritte: Callable[[Path], None]) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        for schritt in schritte:
            schritt(root)

    return apply
