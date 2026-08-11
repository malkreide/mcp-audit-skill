"""Versions-Badge und Regelzahl des Transport-Skills.

`version_badge` BINDET G11 ZUM ERSTEN MAL. Das Gate steht seit 2b-iii-a und
war bis hierher ohne Gegenstand: Die READMEs der Repo-Wurzel tragen kein
Badge, die der drei Companions schon.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.gates import counts as count_gates
from tools.gates import readmes as gates
from tools.harness import register

from ._suite import SUITE
from .skill_doc import BASE, SKILL_PATH

REGEL = re.compile(r"^## Regel (?P<nummer>\d+)", re.M)

#: Die READMEs zaehlen dieselben Regeln ein zweites Mal auf — als nummerierte
#: Liste unter «The fourteen rules» / «Die vierzehn Regeln». Das `**` gehoert
#: zum Muster: Jeder Eintrag beginnt mit einer fetten Kurzfassung, und ohne
#: diese Einschraenkung faenge das Muster jede andere nummerierte Liste im
#: Dokument mit.
LIST_ITEM = re.compile(r"^(?P<nummer>\d+)\. \*\*", re.M)
RULE_LISTS = (
    (f"{BASE}/README.md", LIST_ITEM, "The fourteen rules"),
    (f"{BASE}/README.de.md", LIST_ITEM, "Die vierzehn Regeln"),
)


@register(3, "rule count is consistent across SKILL.md and both READMEs", suite=SUITE)
def rule_count(root: Path) -> str:
    return count_gates.count_agrees(
        root,
        source=SKILL_PATH,
        pattern=REGEL,
        unit="Regeln",
        mirrors=RULE_LISTS,
    )


@register(5, "the version badge matches the latest CHANGELOG release", suite=SUITE)
def version_badge(root: Path) -> str:
    return gates.version_badge(root, base=BASE)
