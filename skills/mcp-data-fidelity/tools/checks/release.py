"""Der Tag ist die dritte Stelle, die eine Version behauptet.

Prüfung 7 bindet Badge an CHANGELOG. Der Tag war von keiner geprüft — und er
ist die einzige der drei, die man nach dem Veröffentlichen nicht mehr
stillschweigend korrigieren kann.

`offline=False`, weil die Prüfung einen Tag-Kontext braucht: Sie läuft im
Tag-Lauf der CI, nicht im lokalen Runner. Ein Branch- oder PR-Lauf hat keinen
Tag, und einen Check, der ohne seinen Gegenstand «bestanden» meldet, will
niemand.

**Grenze, ausdrücklich:** Bei einem Tag-Lauf führt GitHub die `ci.yml` des
*getaggten* Commits aus, nicht die von `main`. Tags auf Commits ohne diese
Prüfung werden von ihr nie erfasst — sie sind stattdessen von Hand
verifiziert (siehe CHANGELOG 1.8.0).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from ._core import CheckFailed, register
from .readmes import top_release

TAG_ENV = "TAG_NAME"
VERSION_TAG = re.compile(r"v?(?P<version>\d+\.\d+\.\d+)")


def assert_tag_matches(tag: str, top: str, lineno: int, heading: str) -> str:
    """Die reine Logik — ohne Umgebung, damit die Tests sie fahren können."""
    # Leer statt ungesetzt wäre der stille Fall: Ein Vergleich gegen "" ergäbe
    # dieselbe Meldung wie ein falscher Tag und führte in die Irre. Deshalb
    # zuerst gegen den Wert selbst prüfen.
    if not tag:
        raise CheckFailed(
            f"${TAG_ENV} ist leer — die Prüfung lief ohne Tag-Kontext. Entweder "
            "hat sich `github.ref_name` geändert oder die `if`-Bedingung greift "
            "nicht mehr; so oder so hat dieser Check nicht stattgefunden."
        )
    match = VERSION_TAG.fullmatch(tag)
    if not match:
        raise CheckFailed(
            f"Tag {tag!r} ist keine Version der Form vX.Y.Z. Der Trigger steht "
            'auf `tags: ["v*"]` — ein Tag, der damit anfängt, aber keine '
            "Versionsnummer ist, gehört nicht an ein Release."
        )
    tagged = match.group("version")
    if tagged != top:
        raise CheckFailed(
            f"Tag {tag!r} nennt {tagged}, oberstes Release in CHANGELOG.md ist "
            f"{top} (Zeile {lineno}: {heading.strip()!r}).\n"
            "  Entweder wurde der Tag vor dem Release-Commit gesetzt, oder er "
            "zeigt auf den falschen Commit. Tag löschen und neu setzen — der "
            "CHANGELOG ist hier die Quelle, nicht der Tag."
        )
    return f"Tag {tag} und CHANGELOG-Spitze stimmen überein ({top}, Zeile {lineno})"


@register(13, "tag and CHANGELOG name the same version", offline=False)
def tag_matches_changelog(root: Path) -> str:
    lineno, heading, top = top_release(root)
    return assert_tag_matches(os.environ.get(TAG_ENV, ""), top, lineno, heading)
