"""Die eine Zusage, die ausserhalb jeder Datei steht: die GitHub-Description.

Sie fällt durch jede Prüfung, die Dateien liest — auch durch
`scripts/validate.sh`, das offline und ohne Token laufen können muss. Deshalb
ist diese Prüfung als einzige `offline=False`: Die CI ruft sie zusätzlich auf,
der lokale Runner nicht.

Kein zweiter Ort für die Wahrheit: Verglichen wird gegen die Ziffer aus dem
Frontmatter von SKILL.md, und Check 11 hat vorher belegt, dass diese Ziffer
der Zahl der [Kern]-Schritte entspricht — und dass jeder Schritt überhaupt
eine Markierung trägt. Die englische Zahlwort-Tabelle steht nur hier, weil nur
hier ein englisches Wort gegen eine Ziffer gehalten wird; die deutsche in
`skill_doc` deckt das Zahlwort der Einleitung ab.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from ._core import CheckFailed, register
from .skill_doc import core_step_count, read_skill

# Bis «ten», aus demselben Grund wie die deutsche Tabelle in `skill_doc`: Ein
# fehlendes Zahlwort ergäbe sonst dieselbe Meldung wie ein echter
# Zahlendreher, und der Befund zeigte auf die falsche Datei.
ENGLISH_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

PROMISE = re.compile(r"(?P<word>\w+)-step core procedure")

# Woher die Description kommt. Die CI legt die API-Antwort dort ab; ein Test
# zeigt auf eine Fixture-Datei. Der Abruf selbst steht bewusst nicht hier —
# eine Prüfung, die Netz braucht, um überhaupt zu starten, lässt sich nicht
# gegen einen Fixture-Baum fahren.
JSON_ENV = "GITHUB_REPO_JSON"

# Der Vorschlag, den der Befund unten ausgibt. Als Konstante, damit ein Test
# ihn gegen das echte SKILL.md halten kann: Ein Hinweis, der eine Description
# empfiehlt, die diese Prüfung anschliessend beanstandet, schickt den Lesenden
# im Kreis. Wird SKILL.md je auf vier Kernschritte umgestellt, wird
# `test_suggested_description_is_advice_that_works` rot — und zwar hier, wo
# der Satz steht.
SUGGESTED_DESCRIPTION = (
    "Claude Skill for probing public data sources before building an MCP "
    "server - a three-step core procedure"
)


def _repo_slug() -> str:
    return os.environ.get("GITHUB_REPOSITORY", "<owner>/<repo>")


def assert_description_matches(description: str, expected: int) -> str:
    """Die reine Logik — ohne Datei, ohne Netz, ohne Umgebung.

    Getrennt, damit die Mutationstests genau das prüfen können, was hier
    schiefgehen kann: fehlender Anker, unbekanntes Zahlwort, Abweichung.
    """
    found = PROMISE.search(description)
    if not found:
        raise CheckFailed(
            "Die GitHub-Description trägt die Wendung '<word>-step core "
            f"procedure' nicht — gelesen wurde {description!r}.\n"
            "  Entweder wurde sie umformuliert (dann diesen Anker im selben "
            "Commit nachziehen) oder die Zusage wurde aus ihr gestrichen. Ein "
            "Anker, der weg ist, lässt diese Prüfung aufhören zu prüfen, ohne "
            "es zu sagen.\n"
            "  Sie hängt am Repository selbst, kein Commit repariert sie:\n"
            f"    gh repo edit {_repo_slug()} "
            f'--description "{SUGGESTED_DESCRIPTION}"'
        )
    word = found.group("word")
    if word not in ENGLISH_NUMBERS:
        raise CheckFailed(
            f"Die GitHub-Description sagt {word!r}, und das ist kein Zahlwort, "
            "das diese Prüfung kennt — ENGLISH_NUMBERS in "
            "tools/checks/github_meta.py ergänzen, sonst meldet der Vergleich "
            "unten eine Abweichung, die in Wahrheit eine Lücke hier ist"
        )
    if ENGLISH_NUMBERS[word] != expected:
        raise CheckFailed(
            f"Die GitHub-Description verspricht {word!r} "
            f"({ENGLISH_NUMBERS[word]}) Kernschritte, SKILL.md markiert "
            f"{expected} als [Kern].\n"
            "  Die Description liegt ausserhalb des Repositories, kein Commit "
            "repariert sie — am Repository selbst setzen:\n"
            f'    gh repo edit {_repo_slug()} --description "..."'
        )
    return (
        f"ok — die GitHub-Description sagt {word} Kernschritte, passend zu "
        f"SKILL.md ({expected})"
    )


@register(
    15,
    "the GitHub description names the current core-step count",
    offline=False,
)
def github_description(root: Path) -> str:
    raw = os.environ.get(JSON_ENV)
    if not raw:
        raise CheckFailed(
            f"${JSON_ENV} ist nicht gesetzt — diese Prüfung liest die "
            "Repository-Metadaten aus der abgelegten API-Antwort. FAIL statt "
            "skip: Eine übersprungene Prüfung meldete «bestanden», wo «nicht "
            "gelaufen» richtig wäre."
        )
    path = Path(raw)
    if not path.is_file():
        raise CheckFailed(f"${JSON_ENV} zeigt auf {raw}, dort liegt keine Datei")
    payload = json.loads(path.read_text(encoding="utf-8"))
    description = payload.get("description") or ""
    return assert_description_matches(description, core_step_count(read_skill(root)))
