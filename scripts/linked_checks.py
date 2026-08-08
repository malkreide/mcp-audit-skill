#!/usr/bin/env python3
"""Die Check-IDs, die die Zuordnungstabelle in SKILL.md verlinkt — eine je Zeile.

WOZU. Prüfung 14 braucht neben dem Manifest die Einstufung (`enforced` /
`advisory`) jedes verlinkten Checks, und die steht im Frontmatter der
Check-Datei drüben. Der Abruf gehört in den Workflow und nicht in die Prüfung
(siehe `tools/checks/catalogue.py`) — aber der Workflow kann nicht wissen,
WELCHE Dateien er holen soll, ohne SKILL.md zu lesen. Genau das tut dieses
Skript, und zwar mit demselben Regex, den die Prüfung selbst benutzt.

Dass beide dieselbe Konstante teilen, ist der Punkt: Eine zweite, in YAML
nachgebaute Liste wäre die Sorte Kopie, die auseinanderläuft, ohne dass etwas
rot wird — der Fehler, gegen den dieses Repository geschrieben ist, in seinem
eigenen Werkzeug.

Ausgabe: eine ID je Zeile, sortiert. Kein Treffer ist ein Fehler und kein
leerer Erfolg — eine leere Liste liesse den Workflow null Dateien holen, und
die Prüfung meldete danach «Einstufung stimmt für alle 0».
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.checks.catalogue import LINKED, table_section  # noqa: E402
from tools.checks.skill_doc import read_skill  # noqa: E402


def linked_checks(root: Path) -> list[str]:
    return sorted(set(LINKED.findall(table_section(read_skill(root)))))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ids = linked_checks(root)
    if not ids:
        print(
            "SKILL.md verlinkt keinen einzigen Check — die Tabelle ist leer "
            "oder der Anker ist weg. Ohne IDs holt der Workflow nichts, und "
            "Prüfung 14 prüfte die Einstufung von null Checks.",
            file=sys.stderr,
        )
        return 1
    print("\n".join(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
