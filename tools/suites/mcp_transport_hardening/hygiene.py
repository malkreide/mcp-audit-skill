"""Die Dateien, auf die dieser Skill verweist."""

from __future__ import annotations

from pathlib import Path

from tools.gates import hygiene as gates
from tools.harness import register

from ._suite import SUITE
from .skill_doc import BASE

#: `LICENSE` steht NICHT mehr darin: Sie lag im Herkunftsrepo neben dem Skill
#: und liegt jetzt einmal in der Repo-Wurzel. Derselbe Grund wie bei den fuenf
#: absorbierten Pruefungen — was dem Repository gehoert, gehoert nicht der
#: Suite.
REFERENCED_FILES = (
    f"{BASE}/SKILL.md",
    f"{BASE}/README.md",
    f"{BASE}/README.de.md",
    f"{BASE}/CHANGELOG.md",
    f"{BASE}/reference/patterns.py",
)


@register(10, "every referenced file is present", suite=SUITE)
def referenced_files_exist(root: Path) -> str:
    return gates.referenced_files_exist(root, files=REFERENCED_FILES)
