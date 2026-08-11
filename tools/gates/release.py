"""Der Tag ist die dritte Stelle, die eine Version behauptet.

Uebernommen aus `mcp-data-fidelity-skill` — Familie G16 des Merge-Plans. Es
gab sie nur dort, sie gilt aber fuer jeden Skill mit einem CHANGELOG und
einem Release-Tag.

G11 bindet das Badge an den CHANGELOG. Der Tag war von keiner Pruefung
erfasst — und er ist die einzige der drei Stellen, die man nach dem
Veroeffentlichen nicht mehr stillschweigend korrigieren kann.

`offline=False` GEHOERT ZUR SACHE, nicht zur Bequemlichkeit: Die Pruefung
braucht einen Tag-Kontext und laeuft im Tag-Lauf der CI, nicht im lokalen
Runner. Ein Branch- oder PR-Lauf hat keinen Tag, und einen Check, der ohne
seinen Gegenstand «bestanden» meldet, will niemand.

GRENZE, AUSDRUECKLICH: Bei einem Tag-Lauf faehrt GitHub den Workflow des
GETAGGTEN Commits, nicht den von `main`. Tags auf Commits ohne diese Pruefung
erfasst sie nie — die sind von Hand zu verifizieren.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from tools.gates.readmes import top_release
from tools.harness import CheckFailed

DEFAULT_TAG_ENV = "TAG_NAME"
VERSION_TAG = re.compile(r"v?(?P<version>\d+\.\d+\.\d+)")


def assert_tag_matches(
    tag: str,
    top: str,
    lineno: int,
    heading: str,
    *,
    tag_env: str = DEFAULT_TAG_ENV,
) -> str:
    """Die reine Logik — ohne Umgebung, damit die Tests sie fahren koennen."""
    # Leer statt ungesetzt waere der stille Fall: Ein Vergleich gegen "" ergaebe
    # dieselbe Meldung wie ein falscher Tag und fuehrte in die Irre. Deshalb
    # zuerst gegen den Wert selbst pruefen.
    if not tag:
        raise CheckFailed(
            f"${tag_env} ist leer — die Pruefung lief ohne Tag-Kontext. "
            "Entweder hat sich `github.ref_name` geaendert oder die "
            "`if`-Bedingung greift nicht mehr; so oder so hat dieser Check "
            "nicht stattgefunden."
        )
    match = VERSION_TAG.fullmatch(tag)
    if not match:
        raise CheckFailed(
            f"Tag {tag!r} ist keine Version der Form vX.Y.Z. Ein Tag, der mit "
            "`v` anfaengt, aber keine Versionsnummer ist, gehoert nicht an ein "
            "Release."
        )
    getaggt = match.group("version")
    if getaggt != top:
        raise CheckFailed(
            f"Tag {tag!r} nennt {getaggt}, oberstes Release im CHANGELOG ist "
            f"{top} (Zeile {lineno}: {heading.strip()!r}).\n"
            "  Entweder wurde der Tag vor dem Release-Commit gesetzt, oder er "
            "zeigt auf den falschen Commit. Tag loeschen und neu setzen — der "
            "CHANGELOG ist hier die Quelle, nicht der Tag."
        )
    return f"Tag {tag} und CHANGELOG-Spitze stimmen ueberein ({top}, Zeile {lineno})"


def tag_matches_changelog(
    root: Path,
    *,
    base: str = ".",
    tag_env: str = DEFAULT_TAG_ENV,
) -> str:
    """G16 — der Tag und die CHANGELOG-Spitze nennen dieselbe Version."""
    lineno, heading, top = top_release(root, base=base)
    return assert_tag_matches(
        os.environ.get(tag_env, ""), top, lineno, heading, tag_env=tag_env
    )
