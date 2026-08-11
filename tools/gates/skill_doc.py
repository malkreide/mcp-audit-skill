"""Das Frontmatter einer `SKILL.md` — drei Behauptungen, die sonst niemand nachhaelt.

Zusammengefuehrt aus den drei Fassungen in `mcp-data-source-probe-skill`,
`mcp-data-fidelity-skill` und `mcp-transport-hardening-skill` — Familie G10
des Merge-Plans. Der Code war in allen dreien praktisch zeichengleich; was
sich unterschied, waren der Pfad zur Datei, der erwartete Name und wie die
Konstante fuer die Laengengrenze hiess.

WARUM DIESE DREI DINGE. Der NAME laedt den Skill — ein anderer laedt ihn unter
falschem Namen, und zwar still. Die DESCRIPTION wird ab 1024 Zeichen
abgeschnitten, und was abgeschnitten ist, triggert nicht mehr. Ein FEHLENDES
Frontmatter ist ein Fehler und kein Grund zum Ueberspringen: Dann hat der
Vergleich nicht stattgefunden, und «nicht gelaufen» als «bestanden» zu melden
ist die eine Auskunft, die schlimmer ist als keine.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.harness import CheckFailed

FRONTMATTER = re.compile(
    r"\A---\s*\nname:\s*(?P<name>.+?)\s*\ndescription:\s*(?P<description>.+?)\s*\n---",
    re.S,
)

#: Ab hier schneidet die Plattform ab. Kein selbstgewaehlter Wert.
DESCRIPTION_LIMIT = 1024


def frontmatter(
    root: Path,
    *,
    skill_path: str,
    expected_name: str,
    limit: int = DESCRIPTION_LIMIT,
) -> str:
    """G10 — Frontmatter vorhanden, Name richtig, Description nicht zu lang.

    Der verbleibende Spielraum steht in der Erfolgsmeldung, nicht bloss die
    Laenge: Die Grenze ist nah genug, dass eine ergaenzte Trigger-Wendung sie
    in einer einzigen Bearbeitung reisst. Wer die Zahl sieht, merkt es vorher.
    """
    pfad = root / skill_path
    if not pfad.is_file():
        raise CheckFailed(
            f"{skill_path} fehlt — ohne die Datei hat diese Pruefung nichts zu "
            "lesen und meldete das als Erfolg."
        )

    match = FRONTMATTER.match(pfad.read_text(encoding="utf-8"))
    if not match:
        raise CheckFailed(f"{skill_path}: Frontmatter fehlt oder ist unvollstaendig")

    name = match.group("name").strip()
    description = match.group("description").strip()

    if name != expected_name:
        raise CheckFailed(
            f"{skill_path}: erwartet wurde name={expected_name!r}, da steht "
            f"{name!r}.\n"
            "  Daran haengt, unter welchem Namen Claude den Skill laedt — ein "
            "anderer laedt ihn still unter dem falschen."
        )
    if len(description) > limit:
        raise CheckFailed(
            f"{skill_path}: description ist {len(description)} Zeichen lang, "
            f"die Grenze liegt bei {limit}. Was darueber steht, wird "
            "abgeschnitten — und was abgeschnitten ist, triggert nicht mehr."
        )

    rest = limit - len(description)
    return (
        f"{skill_path}: name={name}, description={len(description)}/{limit} "
        f"Zeichen ({rest} frei)"
    )
