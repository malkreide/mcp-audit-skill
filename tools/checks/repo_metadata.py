"""Die Repo-Description ist die fünfte Stelle, die die Zahl der Regeln nennt.

Prüfung 5 hält vier gegeneinander: SKILL.md, beide READMEs und den Docstring
von `reference/patterns.py`. Die fünfte liegt ausserhalb des Arbeitsbaums, in
den GitHub-Metadaten, und war deshalb von keiner Prüfung erfasst. Sie ist
prompt veraltet: Als Regel 11 und 12 dazukamen, sagte die Description weiter
«ten data-fidelity rules». Aufgefallen ist das beim Lesen, nicht beim Prüfen —
die Fehlerform, gegen die dieses Repository geschrieben ist.

WARUM IM WOCHENPLAN UND NICHT IM PR-LAUF. Dieselbe Antwort wie bei Prüfung 14,
und sie trägt hier sogar weiter. Der Fehler ist keine Eigenschaft eines
Commits: Die Description lässt sich im Browser ändern, ohne dass hier ein Diff
entsteht. Ein PR-Lauf könnte sie also gar nicht bewachen — er sähe die
Änderung nie und meldete «bestanden». Dazu das Übliche: Netz vor dem
Merge-Button färbt bei einem Aussetzer einen unbeteiligten PR rot, und Regel 5
dieses Skills sagt, was mit einem Test passiert, der ständig falsch anschlägt.

DER ABRUF STEHT NICHT HIER, aus demselben Grund wie bei Prüfung 14: Der
Workflow legt die Antwort der Repo-API als Datei ab und nennt sie in
`$REPO_METADATA`; diese Prüfung liest sie. Eine Prüfung, die Netz braucht, um
überhaupt zu starten, lässt sich nicht gegen einen Fixture-Baum fahren — und
dann bliebe sie selbst ungeprüft.

GRENZE, AUSDRÜCKLICH. Geprüft wird die **Zahl**, nicht der Satz: Was neben dem
Zahlwort steht, darf sich frei ändern. Verschwindet der Anker aber ganz, ist
das ein Befund und kein Durchwinken — ein Wächter, der sein eigenes
Verschwinden hinnimmt, ist der Fall aus `ruff.toml`, wo `select = []` stand
und beide Ruff-Schritte «All checks passed!» meldeten.

Und was diese Prüfung NICHT kann: die Description reparieren. Sie liegt in den
Metadaten, nicht im Baum — der Befund nennt deshalb den Handgriff im Browser
statt einer Datei. Das ist die Regel-12-Unterscheidung an der eigenen
Werkzeugkette: «nicht erhoben» wäre hier «kein Commit kann das beheben», und
das gehört in den Befundtext.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from ._core import CheckFailed, register
from .skill_doc import ENGLISH_NUMBERS, read_skill, rule_count

METADATA_ENV = "REPO_METADATA"
METADATA_URL = "https://api.github.com/repos/malkreide/mcp-data-fidelity-skill"

# Derselbe Ankertyp wie in `patterns.py` («patterns for the <word> ... rules»):
# ein Zahlwort vor einem festen Substantiv. Bewusst kein `\d+` daneben — die
# Description schreibt die Zahl aus, und zwei zulässige Schreibweisen wären
# zwei Stellen, an denen sie auseinanderlaufen kann.
RULE_CLAIM = re.compile(r"(?P<word>\w+) data-fidelity rules")


def parse_metadata(raw: str) -> str:
    """Die Description aus der abgelegten API-Antwort, oder ein Befund.

    Bestätigt die Struktur, bevor gelesen wird — Regel 6, auf das eigene
    Werkzeug angewandt. Ein `payload.get("description")` würde aus einer
    umbenannten oder weggefallenen Antwort still eine leere Description machen,
    und die Prüfung meldete dann eine Abweichung, die in Wahrheit ein
    Formatwechsel drüben ist.
    """
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CheckFailed(
            "Die abgelegte Antwort der Repo-API ist kein JSON — Format drüben "
            f"geändert, oder eine Fehlerseite ist abgespeichert worden ({exc}). "
            "Das ist ein Befund über den Abruf, nicht über die Description."
        ) from exc
    if not isinstance(payload, dict):
        raise CheckFailed(
            f"Die Antwort der Repo-API ist {type(payload).__name__}, erwartet "
            "war ein Objekt"
        )
    if "description" not in payload:
        raise CheckFailed(
            "Die Antwort der Repo-API führt kein 'description'. Vorhandene "
            f"Schlüssel: {sorted(payload)[:10]}"
        )
    description = payload["description"]
    if not description:
        raise CheckFailed(
            "Die Repo-Description ist leer. Ausdrücklich ein Befund und kein "
            "Überspringen: Ohne Description hat diese Prüfung keinen "
            "Gegenstand, und «kein Gegenstand» als «bestanden» zu melden ist "
            "genau der stille Fall, gegen den sie steht."
        )
    return str(description)


def assert_description_matches(description: str, expected: int) -> str:
    """Die reine Logik: Description gegen die Regelzahl, ohne Netz und Dateien."""
    match = RULE_CLAIM.search(description)
    if not match:
        raise CheckFailed(
            "Die Repo-Description nennt keine '<Zahlwort> data-fidelity rules' "
            f"mehr:\n    {description!r}\n"
            "  Umformuliert — damit wäre die Zahl dort ungeprüft. Entweder den "
            "Anker wiederherstellen oder RULE_CLAIM in "
            "tools/checks/repo_metadata.py im selben Zug mitziehen."
        )
    word = match.group("word")
    if word not in ENGLISH_NUMBERS:
        raise CheckFailed(
            f"Die Repo-Description sagt {word!r}, und das ist kein Zahlwort, "
            "das diese Prüfung kennt — ENGLISH_NUMBERS in "
            "tools/checks/skill_doc.py ergänzen, sonst meldet der Vergleich "
            "unten eine Abweichung, die in Wahrheit eine Lücke hier ist."
        )
    if ENGLISH_NUMBERS[word] != expected:
        raise CheckFailed(
            "DRIFT — die Repo-Description ist gegenüber SKILL.md veraltet:\n"
            f"  - Description: {word!r} ({ENGLISH_NUMBERS[word]}) Regeln\n"
            f"  - SKILL.md:    {expected} Regeln\n\n"
            "Quelle ist SKILL.md. Die Description liegt in den GitHub-Metadaten "
            "und nicht im Arbeitsbaum: Sie wird von Hand nachgezogen — "
            "Repo-Startseite, Zahnrad neben «About» —, kein Commit behebt das."
        )
    return f"Repo-Description sagt {word} ({expected}) Regeln, deckt sich mit SKILL.md"


@register(
    15,
    "the GitHub repo description names the same rule count as SKILL.md",
    offline=False,
)
def description_matches_rule_count(root: Path) -> str:
    raw = os.environ.get(METADATA_ENV)
    if not raw:
        raise CheckFailed(
            f"${METADATA_ENV} ist nicht gesetzt — diese Prüfung liest die "
            "abgelegte Antwort der Repo-API. Der Abruf steht in "
            f".github/workflows/weekly-drift.yml ({METADATA_URL}). FAIL "
            "statt skip: Eine übersprungene Prüfung meldete «bestanden», wo "
            "«nicht gelaufen» richtig wäre."
        )
    path = Path(raw)
    if not path.is_file():
        raise CheckFailed(f"${METADATA_ENV} zeigt auf {raw}, dort liegt keine Datei")
    return assert_description_matches(
        parse_metadata(path.read_text(encoding="utf-8")), rule_count(read_skill(root))
    )
