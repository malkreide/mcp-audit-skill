"""Der Tag gegen die CHANGELOG-Spitze — die Bindung des generischen Gates.

`offline=False` GEHOERT ZUR SACHE. Die Pruefung braucht einen Tag-Kontext und
laeuft im Tag-Lauf der CI, nicht im lokalen Runner: `scripts/validate.sh`
faehrt nur die Offline-Pruefungen, damit ein frischer Clone ohne Zugangsdaten
vollstaendig durchlaeuft. Ein Branch- oder PR-Lauf hat keinen Tag, und einen
Check, der ohne seinen Gegenstand «bestanden» meldet, will niemand.

Sie kam aus `mcp-data-fidelity-skill` und gab es nur dort. Der Tag ist die
dritte Stelle, die eine Version behauptet — und die einzige, die man nach dem
Veroeffentlichen nicht mehr stillschweigend korrigieren kann.
"""

from __future__ import annotations

from pathlib import Path

from tools.gates import release as gates
from tools.harness import register

from ._suite import SUITE


@register(13, "tag and CHANGELOG name the same version", suite=SUITE, offline=False)
def tag_matches_changelog(root: Path) -> str:
    return gates.tag_matches_changelog(root)
