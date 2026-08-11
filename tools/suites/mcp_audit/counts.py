"""Die Schrittzahl dieses Skills — die Bindung des generischen Gates.

`SKILL.md` fuehrt acht nummerierte Schritte (0 bis 7), und
`.claude/commands/audit-mcp.md` fuehrt zu jedem eine `**Output Schritt N:**`
-Zeile. Die beiden Dateien beschreiben denselben Ablauf an zwei Stellen —
geprueft hat das bisher nichts.

WARUM GERADE DIESE ZWEI. Beide nummerieren unmissverstaendlich, und der
Command ist das, was tatsaechlich laeuft. Kommt in `SKILL.md` ein Schritt
dazu, ohne dass der Command ihn kennt, faehrt der Skill weniger, als seine
Dokumentation verspricht — und nichts sagte es.

WAS DIESE PRUEFUNG AUSDRUECKLICH NICHT ENTSCHEIDET: Beide READMEs sprechen vom
«six-step workflow» beziehungsweise «6-Schritte-Workflow». Ob das veraltet ist
oder «die Schritte 1 bis 6» meint — also ohne die Vorbereitung (0) und den
bedingten Release-Vorschlag (7) —, steht nirgends im Repository. Das ist eine
Frage an den Betreiber und keine, die eine Pruefung raten darf; sie steht als
offener Punkt im Merge-Plan unter 4.2h.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.gates import counts as gates
from tools.harness import register

from ._suite import SUITE

SOURCE = "SKILL.md"
SCHRITT = re.compile(r"^## Schritt (?P<nummer>\d+)", re.M)
COMMAND = ".claude/commands/audit-mcp.md"
OUTPUT_SCHRITT = re.compile(r"^\*\*Output Schritt (?P<nummer>\d+)", re.M)

#: Beide READMEs behaupten die Zahl in PROSA statt sie aufzuzaehlen. Bis 2b-iv
#: stand dort «six-step» beziehungsweise «6-Schritte» — entweder veraltet oder
#: «die Schritte 1 bis 6» gemeint, und nichts im Repository sagte welches. Der
#: Betreiber hat entschieden: Es ist die volle Zahl, also acht. Seither steht
#: sie hier unter Aufsicht.
PROSA = (
    ("README.md", re.compile(r"(?P<wert>[\w-]+)-step workflow")),
    ("README.de.md", re.compile(r"(?P<wert>\d+)-Schritte-Workflow")),
)


@register(14, "every statement of the step count agrees", suite=SUITE)
def step_count_agrees(root: Path) -> str:
    return gates.count_agrees(
        root,
        source=SOURCE,
        pattern=SCHRITT,
        unit="Schritte",
        mirrors=((COMMAND, OUTPUT_SCHRITT, None),),
        claims=PROSA,
    )
