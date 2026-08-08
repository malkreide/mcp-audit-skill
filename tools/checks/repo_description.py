"""Die GitHub-Description nennt die aktuelle Regelzahl.

Die Description steht AUSSERHALB des Repos und faellt damit durch jede
Pruefung, die Dateien liest. Genau dort ist die Regelzahl zuletzt
haengengeblieben: «twelve», als SKILL.md schon dreizehn fuehrte. Das ist
Regel 13 raeumlich statt zeitlich — die Abdeckung hatte eine Grenze, die
niemand absichtlich gezogen hat, und ausserhalb davon wurde nichts rot.

Kein zweiter WORDS-Wortschatz: Verglichen wird gegen das Zahlwort aus dem
Docstring von `reference/patterns.py`, und `rule_count.py` hat bereits belegt,
dass dieses Wort der Regelzahl entspricht. Zwei Stellen mit derselben Tabelle
waeren genau das, was hier auseinanderlaeuft.

AUFRUF: `python tools/checks/repo_description.py <pfad-zur-repo.json>`

Der API-Aufruf steht bewusst NICHT hier, sondern im Workflow. Dieses Skript
bekommt die fertige Antwort als Datei. Das ist der Unterschied zwischen einer
Pruefloglik, die sich ohne Netz testen laesst, und einer, die man nur im CI
beobachten kann — die Auslagerung waere sonst umsonst gewesen.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        sys.exit(
            f"usage: {argv[0] if argv else 'repo_description.py'} <pfad-zur-repo.json>"
        )
    repo_json = pathlib.Path(argv[1])

    patterns = pathlib.Path("reference/patterns.py").read_text(encoding="utf-8")
    m = re.search(r"patterns for the (?P<word>\w+) [\w-]+ rules", patterns)
    if not m:
        sys.exit(
            "reference/patterns.py: number word gone — rule_count.py "
            "should have caught this first; without it there is nothing "
            "to compare the description against"
        )
    word = m.group("word")

    repo = json.loads(repo_json.read_text(encoding="utf-8"))
    description = repo.get("description") or ""

    found = re.search(r"(?P<word>\w+) transport-hardening rules", description)
    if not found:
        sys.exit(
            "GitHub description does not carry the phrase '<word> "
            f"transport-hardening rules' — got {description!r}.\n"
            "  Either it was reworded (then adjust this anchor in the same "
            "commit) or the count was dropped from it. An anchor that is "
            "gone makes this check stop checking without saying so."
        )
    if found.group("word") != word:
        sys.exit(
            f"GitHub description says {found.group('word')!r} rules, the repo "
            f"has {word!r}.\n"
            "  The description lives outside the repository, so no commit "
            "fixes it — set it on the repo itself:\n"
            f"    gh repo edit {os.environ.get('GITHUB_REPOSITORY', '<repo>')} "
            f'--description "..."'
        )
    print(f"ok — GitHub description says {found.group('word')}, matching the repo")


if __name__ == "__main__":
    main(sys.argv)
