"""Pruefungen an SKILL.md selbst: Frontmatter und Regelabschnitte."""

from __future__ import annotations

import re
from pathlib import Path

from ._core import CheckFailed, register

EXPECTED_NAME = "mcp-transport-hardening"
MAX_DESCRIPTION = 1024

FRONTMATTER = re.compile(r"^---\nname: (.+?)\ndescription: (.+?)\n---\n", re.S)


def _skill(root: Path) -> str:
    return (root / "SKILL.md").read_text(encoding="utf-8")


@register(1, "SKILL.md carries a well-formed frontmatter")
def skill_frontmatter(root: Path) -> str:
    """Drei Behauptungen, die sonst niemand nachhaelt.

    Der Name laedt den Skill; ein anderer laedt ihn unter falschem Namen, und
    zwar still. Die Description wird ab 1024 Zeichen abgeschnitten.

    Ein fehlendes Frontmatter ist ein FEHLER, kein Grund zum Ueberspringen:
    Dann hat der Vergleich nicht stattgefunden, und «nicht gelaufen» als
    «bestanden» zu melden ist die eine Auskunft, die schlimmer ist als keine.
    """
    m = FRONTMATTER.match(_skill(root))
    if not m:
        raise CheckFailed("SKILL.md: frontmatter missing or malformed")
    name, desc = m.group(1).strip(), m.group(2).strip()
    if name != EXPECTED_NAME:
        raise CheckFailed(f"SKILL.md: expected name {EXPECTED_NAME!r}, got {name!r}")
    if len(desc) > MAX_DESCRIPTION:
        raise CheckFailed(
            f"SKILL.md: description too long ({len(desc)} > {MAX_DESCRIPTION})"
        )
    return f"name={name}, description={len(desc)} chars"


@register(2, "every rule carries a counter-example pair and a Nachweis")
def rule_sections(root: Path) -> str:
    """Der Skill lebt davon, dass jede Regel FALSCH und RICHTIG zeigt.

    Eine Regel ohne `# ✗`/`# ✓`-Paar ist eine Behauptung; eine ohne
    `**Nachweis:**` eine Behauptung ohne Beleg. Beides faellt beim Lesen nicht
    auf, weil der Abschnitt vollstaendig AUSSIEHT.

    Die Nummern muessen lueckenlos von 1 aufsteigen. Eine uebersprungene
    Nummer ist der Zustand, in dem die Regelzahl an vier Stellen noch stimmt
    und trotzdem eine Regel fehlt.
    """
    sections = re.split(r"^## (?=Regel )", _skill(root), flags=re.M)[1:]
    if not sections:
        raise CheckFailed("SKILL.md: no '## Regel N' sections found")

    numbers = [int(re.match(r"Regel (\d+)", s).group(1)) for s in sections]
    if numbers != list(range(1, len(numbers) + 1)):
        raise CheckFailed(f"SKILL.md: rule numbers not sequential: {numbers}")

    for section in sections:
        title = section.splitlines()[0]
        body = section.split("\n## ")[0]
        if "# ✗" not in body or "# ✓" not in body:
            raise CheckFailed(
                f"{title}: missing the counter-example / example code pair"
            )
        if "**Nachweis:**" not in body:
            raise CheckFailed(f"{title}: missing the Nachweis sentence")
    return f"{len(sections)} rules, each with a code pair and a Nachweis"
