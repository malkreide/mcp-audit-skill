"""Hygiene und Vorlagen — die Bindung der generischen Gates.

DREI PRUEFUNGEN, DIE ES HIER VORHER NICHT GAB. Alle drei liefen in den
Schwesterrepos, keine in diesem — dieselbe Sorte Luecke, die schon `audit/6`
und `audit/7` geschlossen haben.

`audit/8` ist dabei die mit der belegten Vorgeschichte: In
`mcp-data-source-probe-skill` war eine `.pyc` schon einmal eingecheckt
(CHANGELOG 1.1.0, «Removed»). Der Vorfall stand dokumentiert, der Waechter
dagegen fehlte — `mcp-transport-hardening-skill` hatte ihn, jenes Repo nicht.
Dieses hier hatte ihn ebenfalls nicht.
"""

from __future__ import annotations

from pathlib import Path

from tools.gates import hygiene as gates
from tools.gates import references as ref_gates
from tools.harness import register

from ._suite import SUITE

#: Die strukturellen Anker dieses Repositories: Was `SKILL.md`, die READMEs
#: und `.claude/commands/audit-mcp.md` als vorhanden voraussetzen. Von Hand
#: gefuehrt und nicht abgeleitet — ein Glob faende nur, was da ist, und
#: koennte deshalb nie melden, dass etwas fehlt.
#:
#: Die vier `SKILL.md` der Kette stehen NICHT hier: Sie prueft
#: `tests/test_quality_chain.py` gegen das Manifest, und zwar samt ihrem
#: Frontmatter-Namen. Zweimal dieselbe Zusage waere eine Stelle zu viel.
REFERENCED_FILES = (
    "SKILL.md",
    "README.md",
    "README.de.md",
    "LICENSE",
    "CHANGELOG.md",
    "skill-manifest.txt",
    "checks/MANIFEST.txt",
    "templates/audit-report.md",
    "templates/finding.md",
    "docs/quality-chain.json",
)

#: Die Vorlagen-Verzeichnisse der eingezogenen Skills. Dieses Repo selbst
#: fuehrt unter `reference/` nur Markdown — Python-Vorlagen bringen die drei
#: Companions mit, und deren Lesbarkeit ist seit Phase 3a eine Zusage dieses
#: Repositories.
REFERENCE_DIRS = (
    "skills/mcp-data-source-probe/reference",
    "skills/mcp-data-fidelity/reference",
    "skills/mcp-transport-hardening/reference",
)


@register(8, "no compiled python is tracked", suite=SUITE)
def no_compiled_python(root: Path) -> str:
    return gates.no_compiled_python(root)


@register(9, "every referenced file is present", suite=SUITE)
def referenced_files_exist(root: Path) -> str:
    return gates.referenced_files_exist(root, files=REFERENCED_FILES)


@register(10, "the reference templates still compile", suite=SUITE)
def python_syntax(root: Path) -> str:
    return ref_gates.python_syntax(root, source_dirs=REFERENCE_DIRS)
