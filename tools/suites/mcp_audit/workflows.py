"""Verweise auf Workflows dieses Repos — die Bindung des generischen Gates.

DER SCOPE IST DIE GANZE ENTSCHEIDUNG. Die Herkunftsfassung durchsuchte den
ganzen Baum; hier waere das falsch, und zwar messbar. Zwei Sorten Text nennen
Workflow-Dateien, ohne von diesem Repository zu sprechen:

* DER KATALOG. `checks/OPS-001.md`, `DRIFT-005.md`, `IDENT-006.md` und
  `ARCH-005.md` nennen `live-test.yml`, `live-tests.yml`, `publish.yml` und
  `security.yml` — Workflows, die ein GEPRUEFTER SERVER haben soll. Gegen den
  eigenen Baum gehalten ergaeben sie vier Befunde, wo null Evidenz vorliegt.

* DIE EINGEZOGENEN SKILLS UND DIESER PLAN. `skills/*/CHANGELOG.md` beschreibt
  die Workflows der Herkunftsrepos, `docs/consolidation/MERGE-PLAN.md`
  beschreibt sie ebenfalls. Beides ist Rede ueber fremde Baeume.

WARUM `tests/` DRAUSSEN BLEIBT, obwohl es echte Verweise enthaelt. Tests
nennen Workflow-Namen als FIXTURE-DATEN — `tests/test_gates_toolchain.py`
schreibt `ci.yml` in einen Wegwerf-Baum, um zu belegen, dass der
Workflow-Pfad wirklich ein Parameter ist. Das ist keine Behauptung ueber
diesen Baum. Und wo ein Test wirklich an einer Datei haengt (er kopiert
`lint.yml`), braucht er keinen Zeiger-Waechter: Verschwindet sie, faellt der
Test direkt um. Dieser Waechter existiert fuer PROSA und KONFIGURATION, wo ein
toter Zeiger still bleibt.
"""

from __future__ import annotations

from pathlib import Path

from tools.gates import workflows as gates
from tools.harness import register

from ._suite import SUITE

#: Die Pfade, die ueber DIESES Repository sprechen. Allowlist und nicht
#: Ausnahmeliste: In einem Monorepo ist der Regelfall die fremde Rede.
SCOPE = (
    "README.md",
    "README.de.md",
    "SKILL.md",
    ".github",
    ".claude",
    "tools",
    "scripts",
)

#: Noch leer: In diesem Repo wurde bisher kein Workflow umbenannt. Der
#: Mechanismus steht bereit — `mcp-data-fidelity-skill` bringt mit seiner
#: Suite den Eintrag fuer `catalogue-drift.yml` mit.
RETIRED: dict[str, gates.Retired] = {}


@register(15, "every referenced workflow exists", suite=SUITE)
def referenced_workflows_exist(root: Path) -> str:
    return gates.referenced_workflows_exist(
        root,
        scope=SCOPE,
        retired=RETIRED,
        declaring="tools/suites/mcp_audit/workflows.py",
    )
