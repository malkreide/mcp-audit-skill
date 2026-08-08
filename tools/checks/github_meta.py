"""Die einzige Pruefung, die etwas ausserhalb des Repositories liest."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from ._core import CheckFailed, register

# Die API-Antwort kommt als Umgebungsvariable, nicht ueber einen Netzaufruf in
# dieser Datei. Das ist die Grenze, an der sich entscheidet, ob die Pruefung
# testbar ist: mit dem `curl` hier waeren genau die zwei Faelle, um die es
# geht — falsches Zahlwort, umformulierte Phrase — nur im CI beobachtbar.
JSON_ENV = "GITHUB_REPO_JSON"

DOCSTRING_PHRASE = re.compile(r"patterns for the (?P<word>\w+) [\w-]+ rules")
DESCRIPTION_PHRASE = re.compile(r"(?P<word>\w+) transport-hardening rules")


def _repo_slug() -> str:
    return os.environ.get("GITHUB_REPOSITORY", "<owner>/<repo>")


def assert_description_matches(description: str, expected_word: str) -> str:
    """Reine Vergleichsfunktion — ohne Netz, ohne Umgebung.

    Sie ist der Grund, warum diese Pruefung ueberhaupt Tests hat: Der Teil,
    der schiefgehen kann, haengt an zwei Zeichenketten und an nichts sonst.
    """
    found = DESCRIPTION_PHRASE.search(description)
    if not found:
        raise CheckFailed(
            "GitHub description does not carry the phrase '<word> "
            f"transport-hardening rules' — got {description!r}.\n"
            "  Either it was reworded (then adjust this anchor in the same "
            "commit) or the count was dropped from it. An anchor that is gone "
            "makes this check stop checking without saying so."
        )
    if found.group("word") != expected_word:
        raise CheckFailed(
            f"GitHub description says {found.group('word')!r} rules, the repo "
            f"has {expected_word!r}.\n"
            "  The description lives outside the repository, so no commit "
            "fixes it — set it on the repo itself:\n"
            f'    gh repo edit {_repo_slug()} --description "..."'
        )
    return found.group("word")


@register(
    9,
    "the GitHub description names the current rule count",
    offline=False,
)
def github_description(root: Path) -> str:
    """Die Description steht AUSSERHALB des Repos.

    Sie faellt damit durch jede Pruefung, die Dateien liest — und genau dort
    ist die Regelzahl zuletzt haengengeblieben: «twelve», als SKILL.md schon
    dreizehn fuehrte. Das ist Regel 13 raeumlich statt zeitlich: Die Abdeckung
    hatte eine Grenze, die niemand absichtlich gezogen hat, und ausserhalb
    davon wurde nichts rot.

    Kein zweiter WORDS-Wortschatz: Verglichen wird gegen das Zahlwort aus dem
    Docstring von `reference/patterns.py`, und Check 3 hat bereits belegt,
    dass dieses Wort der Regelzahl entspricht. Zwei Stellen mit derselben
    Tabelle waeren genau das, was hier auseinanderlaeuft.
    """
    raw = os.environ.get(JSON_ENV)
    if not raw:
        raise CheckFailed(
            f"{JSON_ENV} ist nicht gesetzt — diese Pruefung braucht die "
            "API-Antwort von GitHub und faellt lieber aus, als «bestanden» zu "
            "melden, ohne verglichen zu haben.\n"
            "  Die CI setzt sie; lokal fahren nur die Offline-Pruefungen."
        )
    try:
        description = (json.loads(raw).get("description") or "").strip()
    except json.JSONDecodeError as exc:
        raise CheckFailed(f"{JSON_ENV} ist kein gueltiges JSON: {exc}") from exc

    patterns = (root / "reference/patterns.py").read_text(encoding="utf-8")
    m = DOCSTRING_PHRASE.search(patterns)
    if not m:
        raise CheckFailed(
            "reference/patterns.py: number word gone — Check 3 should have "
            "caught this first; without it there is nothing to compare the "
            "description against"
        )

    word = assert_description_matches(description, m.group("word"))
    return f"description says {word}, matching the repo"
