"""Frontmatter und Zuordnungstabelle des Fidelity-Skills."""

from __future__ import annotations

import re
from pathlib import Path

from tools.gates import skill_doc as gates
from tools.harness import CheckFailed, register

from ._suite import SUITE

BASE = "skills/mcp-data-fidelity"
SKILL_PATH = f"{BASE}/SKILL.md"
EXPECTED_NAME = "mcp-data-fidelity"

#: Die Ueberschrift der Regel↔Check-Tabelle. Sie ist der Anker fuer `fidelity/6`
#: UND fuer `fidelity/14` — beide lesen denselben Abschnitt, die eine
#: strukturell, die andere gegen den Katalog. Deshalb steht sie hier und nicht
#: zweimal.
TABLE_HEADING = "### Welche Regel welcher Check ist"

#: Das Muster der normativen Quelle. Es steht HIER und nicht in `readmes.py`
#: wie bei `transport`, weil es zwei Aufrufer hat: `fidelity/5` zaehlt damit,
#: `fidelity/6` haelt die Tabelle dagegen. Zwei Lesungen derselben Datei
#: koennen auseinanderlaufen; eine kann es nicht.
REGEL = re.compile(r"^## Regel (?P<nummer>\d+)", re.M)

CHECK_ID = re.compile(r"\b[A-Z]{2,6}-\d{3}\b")


def read_skill(root: Path) -> str:
    pfad = root / SKILL_PATH
    if not pfad.is_file():
        raise CheckFailed(
            f"{SKILL_PATH} fehlt — ohne die Datei hat diese Pruefung nichts zu "
            "lesen und meldete das als Erfolg."
        )
    return pfad.read_text(encoding="utf-8")


def rule_numbers(text: str) -> list[int]:
    """Die Regelnummern aus `SKILL.md` — die eine normative Quelle.

    Absichtlich OHNE die Lueckenlosigkeits-Pruefung aus
    `tools/gates/counts.numbered`: Die faehrt `fidelity/5`, und zweimal
    denselben Befund zu melden hiesse, einen Fehler doppelt zu zaehlen. Hier
    wird die Menge nur gebraucht, um die Tabelle dagegen zu halten — und die
    muss auch dann noch vollstaendig sein, wenn die Numerierung gerade
    kaputt ist.
    """
    nummern = [int(m.group("nummer")) for m in REGEL.finditer(text)]
    if not nummern:
        raise CheckFailed(
            f"{SKILL_PATH}: keine Ueberschrift '## Regel N' gefunden — Anker "
            "weg oder umformuliert; diese Pruefung wuerde stillschweigend "
            "aufhoeren zu pruefen."
        )
    return nummern


def table_section(skill: str) -> str:
    """Der Rumpf der Zuordnungstabelle, bis zur naechsten Ueberschrift."""
    treffer = re.search(
        rf"^{re.escape(TABLE_HEADING)}\n(.*?)(?=^#{{2,3}} |\Z)",
        skill,
        re.M | re.S,
    )
    if not treffer:
        raise CheckFailed(
            f"{SKILL_PATH}: Abschnitt {TABLE_HEADING!r} nicht gefunden — Anker "
            "weg oder umformuliert; diese Pruefung wuerde stillschweigend "
            "aufhoeren zu pruefen."
        )
    return treffer.group(1)


@register(4, "SKILL.md carries a well-formed frontmatter", suite=SUITE)
def skill_frontmatter(root: Path) -> str:
    return gates.frontmatter(root, skill_path=SKILL_PATH, expected_name=EXPECTED_NAME)


@register(6, "every rule has a row in the rule-to-check table", suite=SUITE)
def rule_to_check_table(root: Path) -> str:
    """Jede Regel hat eine Zeile, und jede Zeile nennt einen Check.

    SKILL-EIGEN und deshalb hier: Nur dieser Skill fuehrt eine Zuordnung
    Regel → Katalog-Check. Er stand an dieser Stelle zweimal falsch (CHANGELOG
    1.4.0 und 1.6.0).

    GRENZE, AUSDRUECKLICH — und sie ist im Monorepo eine andere als vorher.
    Diese Pruefung haette den Anlass fuer sich selbst NICHT gefangen: «Ein
    `FID-006` existiert nicht» nennt eine Check-ID und ginge gruen durch. Sie
    faengt die naechste Regel OHNE Zeile, nicht die naechste VERALTETE Zeile.
    Das war im Herkunftsrepo eine echte Luecke, die nur ein Wochenplan
    schliessen konnte; hier liegt der Katalog im selben Commit, und
    `fidelity/14` schliesst sie im PR.
    """
    skill = read_skill(root)
    nummern = rule_numbers(skill)
    erwartet = set(nummern)

    zeilen: dict[int, str] = {}
    for zeile in table_section(skill).splitlines():
        treffer = re.match(r"^\|\s*(\d+)\s*—\s*(.*?)\s*\|(.*)\|\s*$", zeile)
        if not treffer:
            continue
        nummer = int(treffer.group(1))
        if nummer in zeilen:
            raise CheckFailed(
                f"{SKILL_PATH}: Regel {nummer} hat mehr als eine Tabellenzeile"
            )
        zeilen[nummer] = treffer.group(3)

    fehlend = sorted(erwartet - set(zeilen))
    if fehlend:
        raise CheckFailed(
            f"{SKILL_PATH}: keine Tabellenzeile fuer Regel {fehlend} — eine "
            "Regel ohne Zeile liest sich, als haette der Katalog nichts zu ihr "
            "zu sagen."
        )
    zuviel = sorted(set(zeilen) - erwartet)
    if zuviel:
        raise CheckFailed(
            f"{SKILL_PATH}: Tabellenzeile fuer Regel {zuviel}, die SKILL.md "
            f"nicht definiert ({len(erwartet)} Regeln)."
        )

    stumm = sorted(n for n, zelle in zeilen.items() if not CHECK_ID.search(zelle))
    if stumm:
        raise CheckFailed(
            f"{SKILL_PATH}: Zeile {stumm} nennt gar keinen Check — sagen, "
            "welcher Check die Regel abdeckt, oder in Check-IDs sagen, was sie "
            "nicht abdeckt."
        )

    return (
        f"{len(erwartet)} Regeln, {len(zeilen)} Zeilen, jede nennt mindestens "
        "einen Check"
    )
