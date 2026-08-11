"""Frontmatter und Regel-Abschnitte des Transport-Skills."""

from __future__ import annotations

import re
from pathlib import Path

from tools.gates import skill_doc as gates
from tools.harness import CheckFailed, register

from ._suite import SUITE

BASE = "skills/mcp-transport-hardening"
SKILL_PATH = f"{BASE}/SKILL.md"
EXPECTED_NAME = "mcp-transport-hardening"


@register(1, "SKILL.md carries a well-formed frontmatter", suite=SUITE)
def skill_frontmatter(root: Path) -> str:
    return gates.frontmatter(root, skill_path=SKILL_PATH, expected_name=EXPECTED_NAME)


@register(2, "every rule carries a counter-example pair and a Nachweis", suite=SUITE)
def rule_sections(root: Path) -> str:
    """Der Skill lebt davon, dass jede Regel FALSCH und RICHTIG zeigt.

    Eine Regel ohne `# ✗`/`# ✓`-Paar ist eine Behauptung; eine ohne
    `**Nachweis:**` eine Behauptung ohne Beleg. Beides faellt beim Lesen nicht
    auf, weil der Abschnitt vollstaendig AUSSIEHT.

    SKILL-EIGEN und deshalb hier statt in `tools/gates/`: Kein anderer Skill
    der Kette baut seine Regeln aus diesem Paar. Was nur einen Gegenstand hat,
    generisch zu machen heisst, eine Abstraktion ohne zweiten Fall zu bauen.
    """
    text = (root / SKILL_PATH).read_text(encoding="utf-8")
    sections = re.split(r"^## (?=Regel )", text, flags=re.M)[1:]
    if not sections:
        raise CheckFailed(f"{SKILL_PATH}: keine '## Regel N'-Abschnitte gefunden")

    for section in sections:
        title = section.splitlines()[0]
        body = section.split("\n## ")[0]
        if "# ✗" not in body or "# ✓" not in body:
            raise CheckFailed(f"{title}: das Gegenbeispiel-Paar fehlt")
        if "**Nachweis:**" not in body:
            raise CheckFailed(f"{title}: der Nachweis-Satz fehlt")

    return f"{len(sections)} Regeln, jede mit Gegenbeispiel-Paar und Nachweis"
