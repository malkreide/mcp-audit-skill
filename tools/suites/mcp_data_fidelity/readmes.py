"""Regelzahl und Versions-Badge des Fidelity-Skills.

DIE REGELZAHL STEHT AN FUENF STELLEN: als Ueberschriften in `SKILL.md`, als
nummerierte Liste in beiden READMEs, als Zahlwort im Modul-Docstring von
`reference/patterns.py` und implizit in der Zuordnungstabelle (die prueft
`fidelity/6`). Fuenf Stellen fuer eine Zahl sind vier zu viel, aber keine
laesst sich streichen — was bleibt, ist sie gegeneinander zu halten.

DER BELEGTE ANLASS: Dieses Repo beschrieb zwei Wochen lang «fuenf Regeln»,
nachdem die sechste dazugekommen war. Beide Aussagen waren richtig, als sie
geschrieben wurden.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.gates import counts as count_gates
from tools.gates import readmes as gates
from tools.harness import CheckFailed, register

from ._suite import SUITE
from .skill_doc import BASE, REGEL, SKILL_PATH, read_skill, rule_numbers

PATTERNS = f"{BASE}/reference/patterns.py"

#: Die READMEs zaehlen dieselben Regeln ein zweites Mal auf. Das `**` gehoert
#: zum Muster: Jeder Eintrag beginnt mit einer fetten Kurzfassung, und ohne
#: diese Einschraenkung faenge das Muster jede andere nummerierte Liste mit.
LIST_ITEM = re.compile(r"^(?P<nummer>\d+)\. \*\*", re.M)
RULE_LISTS = (
    (f"{BASE}/README.md", LIST_ITEM, "The fourteen rules"),
    (f"{BASE}/README.de.md", LIST_ITEM, "Die vierzehn Regeln"),
)

#: Die Behauptung in PROSA — `patterns.py` sagt die Zahl als englisches
#: Zahlwort statt sie aufzuzaehlen. `count_agrees` liest sie ueber
#: `as_number`, dieselbe Funktion wie die GitHub-Description.
DOCSTRING_CLAIM = (
    (PATTERNS, re.compile(r"patterns for the (?P<wert>\w+) [\w-]+ rules")),
)

#: «Rule 1», «Rules 4 + 5», «Rules 5-7», «Rules 1–6» — Bereiche aufgeloest.
#: Der En-Dash steht als Escape und nicht als Zeichen: Von einem Minus ist er
#: im Quelltext kaum zu unterscheiden, und ein Zeichen, das man nicht sehen
#: kann, gehoert nicht in ein Regex. Beide Formen kommen in `patterns.py` vor.
DASH = r"[-–]"
RULE_MENTION = re.compile(rf"[Rr]ules?\s+(\d+(?:\s*(?:{DASH}|[+,]|and)\s*\d+)*)")


def mentioned_rules(text: str) -> set[int]:
    genannt: set[int] = set()
    for treffer in RULE_MENTION.finditer(text):
        nummern = [int(n) for n in re.findall(r"\d+", treffer.group(1))]
        if re.search(DASH, treffer.group(1)) and len(nummern) == 2:
            genannt.update(range(nummern[0], nummern[1] + 1))
        else:
            genannt.update(nummern)
    return genannt


@register(
    5,
    "the rule count agrees across SKILL.md, both READMEs and patterns.py",
    suite=SUITE,
)
def rule_count_consistent(root: Path) -> str:
    """Das generische Zaehl-Gate, plus eine Zusage, die nur dieser Skill hat.

    G14 deckt die vier ZAEHLENDEN Stellen ab. Was es nicht abdeckt und was
    deshalb darunter steht: dass zu JEDER Regel ueberhaupt etwas in
    `patterns.py` steht. Das ist keine Zahl, sondern eine Abdeckung — eine
    Regel ohne Muster ist eine Regel, die niemand kopieren kann, und die Zahl
    im Docstring bleibt dabei richtig.
    """
    ergebnis = count_gates.count_agrees(
        root,
        source=SKILL_PATH,
        pattern=REGEL,
        unit="Regeln",
        mirrors=RULE_LISTS,
        claims=DOCSTRING_CLAIM,
    )

    nummern = rule_numbers(read_skill(root))
    pfad = root / PATTERNS
    if not pfad.is_file():
        raise CheckFailed(f"{PATTERNS} fehlt")
    fehlend = sorted(set(nummern) - mentioned_rules(pfad.read_text(encoding="utf-8")))
    if fehlend:
        raise CheckFailed(
            f"{PATTERNS}: nichts zu Regel {fehlend} — eine Regel ohne Muster "
            "ist eine Regel, die niemand kopieren kann. Die Zahl im Docstring "
            "stimmt dabei weiter; deshalb faengt das Zaehl-Gate diesen Fall "
            "nicht."
        )

    return f"{ergebnis}; {PATTERNS}: deckt alle {len(nummern)} ab"


@register(7, "the version badge matches the latest CHANGELOG release", suite=SUITE)
def version_badge(root: Path) -> str:
    return gates.version_badge(root, base=BASE)
