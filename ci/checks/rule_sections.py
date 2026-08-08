"""Jede Regel in SKILL.md traegt ein Gegenbeispiel-Paar und einen Nachweis.

Der Skill lebt davon, dass jede Regel zeigt, wie es FALSCH aussieht (`# ✗`) und
wie RICHTIG (`# ✓`). Eine Regel ohne dieses Paar ist eine Behauptung; eine
Regel ohne `**Nachweis:**` ist eine Behauptung ohne Beleg. Beides faellt beim
Lesen nicht auf, weil der Abschnitt vollstaendig AUSSIEHT.

Geprueft wird zusaetzlich, dass die Nummern lueckenlos von 1 aufsteigen. Eine
uebersprungene Nummer ist der Zustand, in dem die Regelzahl an vier Stellen
noch stimmt und trotzdem eine Regel fehlt.

Fehlen die Abschnitte ganz, ist das ein FEHLER und kein Skip: Ohne sie hat
dieser Check nichts geprueft und haette genau deshalb Erfolg gemeldet.
"""

from __future__ import annotations

import pathlib
import re
import sys


def main() -> None:
    skill = pathlib.Path("SKILL.md").read_text(encoding="utf-8")
    sections = re.split(r"^## (?=Regel )", skill, flags=re.M)[1:]
    if not sections:
        sys.exit("SKILL.md: no '## Regel N' sections found")

    numbers = [int(re.match(r"Regel (\d+)", s).group(1)) for s in sections]
    if numbers != list(range(1, len(numbers) + 1)):
        sys.exit(f"SKILL.md: rule numbers not sequential: {numbers}")

    for section in sections:
        title = section.splitlines()[0]
        body = section.split("\n## ")[0]
        if "# ✗" not in body or "# ✓" not in body:
            sys.exit(f"{title}: missing the counter-example / example code pair")
        if "**Nachweis:**" not in body:
            sys.exit(f"{title}: missing the Nachweis sentence")
        print(f"ok — {title[:60]}")
    print(f"ok — {len(sections)} rules, each with a code pair and a Nachweis")


if __name__ == "__main__":
    main()
