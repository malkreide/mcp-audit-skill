"""Prüfungen an SKILL.md — dem Dokument, das der Skill selbst ist.

Die Zahl der Regeln steht an fünf Stellen: als Überschriften in SKILL.md, als
Zahlwort in zwei README-Überschriften, als Zahlwort im Docstring von
`reference/patterns.py` und implizit in der Zuordnungstabelle. Fünf Stellen
für eine Zahl sind vier zu viel, aber keine lässt sich streichen — was
bleibt, ist sie gegeneinander zu halten.
"""

from __future__ import annotations

import re
from pathlib import Path

from ._core import CheckFailed, register

EXPECTED_NAME = "mcp-data-fidelity"
DESCRIPTION_LIMIT = 1024
FRONTMATTER = re.compile(r"^---\nname: (.+?)\ndescription: (.+?)\n---\n", re.S)

RULE_HEADING = re.compile(r"^## Regel (\d+)", re.M)

# Das Zahlwort in der Überschrift steht absichtlich hier und nicht als Regex:
# Wird eine Regel ergänzt, müssen beide READMEs und diese Konstante im selben
# Commit mitgehen — sonst fällt die Prüfung aus, statt eine veraltete Zahl
# grün durchzulassen.
RULE_SECTIONS = (
    ("README.md", "The twelve rules"),
    ("README.de.md", "Die zwölf Regeln"),
)

PATTERNS = "reference/patterns.py"
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
    "eleven": 11,
    "twelve": 12,
}

TABLE_HEADING = "### Welche Regel welcher Check ist"
CHECK_ID = re.compile(r"\b[A-Z]{2,6}-\d{3}\b")

# Der En-Dash steht als Escape und nicht als Zeichen: Von einem Minus ist er
# im Quelltext kaum zu unterscheiden, und ein Zeichen, das man nicht sehen
# kann, gehört nicht in ein Regex. Beide Formen kommen in patterns.py vor —
# «Rules 5-7» mit Minus, «Rules 1–6» mit En-Dash.
DASH = r"[-\u2013]"
RULE_MENTION = rf"[Rr]ules?\s+(\d+(?:\s*(?:{DASH}|[+,]|and)\s*\d+)*)"


def read_skill(root: Path) -> str:
    path = root / "SKILL.md"
    if not path.is_file():
        raise CheckFailed("SKILL.md: missing")
    return path.read_text(encoding="utf-8")


def rule_count(text: str) -> int:
    """Die Zahl der Regeln — die eine normative Quelle.

    Alles andere wird dagegen gehalten, nichts daneben gepflegt.
    """
    numbers = [int(n) for n in RULE_HEADING.findall(text)]
    if not numbers:
        raise CheckFailed(
            "SKILL.md: keine Überschrift '## Regel N' gefunden — Anker weg "
            "oder umformuliert, diese Prüfung würde stillschweigend aufhören "
            "zu prüfen"
        )
    if numbers != list(range(1, len(numbers) + 1)):
        raise CheckFailed(f"SKILL.md: Regelnummern nicht fortlaufend: {numbers}")
    return len(numbers)


@register(4, "SKILL.md carries a well-formed frontmatter")
def frontmatter(root: Path) -> str:
    match = FRONTMATTER.match(read_skill(root))
    if not match:
        raise CheckFailed("SKILL.md: frontmatter missing or malformed")
    name, description = match.group(1).strip(), match.group(2).strip()
    if name != EXPECTED_NAME:
        raise CheckFailed(f"SKILL.md: expected name {EXPECTED_NAME!r}, got {name!r}")
    if len(description) > DESCRIPTION_LIMIT:
        raise CheckFailed(
            f"SKILL.md: description too long ({len(description)} > {DESCRIPTION_LIMIT})"
        )
    left = DESCRIPTION_LIMIT - len(description)
    return (
        f"SKILL.md: name={name}, description={len(description)}/"
        f"{DESCRIPTION_LIMIT} chars ({left} left)"
    )


def _listed_rules(root: Path, name: str, heading: str) -> int:
    path = root / name
    if not path.is_file():
        raise CheckFailed(f"{name}: missing")
    match = re.search(
        rf"^## {re.escape(heading)}\n(.*?)(?=^## )",
        path.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    if not match:
        raise CheckFailed(
            f"{name}: Abschnitt '## {heading}' nicht gefunden — Anker weg oder "
            "umformuliert. Steht dort ein anderes Zahlwort, gehört RULE_SECTIONS "
            "in tools/checks/skill_doc.py im selben Commit mitgezogen."
        )
    return len(re.findall(r"^\d+\. ", match.group(1), re.M))


def _mentioned_rules(text: str) -> set[int]:
    """«Rule 1», «Rules 4 + 5», «Rules 5-7» — Bereiche aufgelöst."""
    mentioned: set[int] = set()
    for match in re.finditer(RULE_MENTION, text):
        numbers = [int(n) for n in re.findall(r"\d+", match.group(1))]
        if re.search(DASH, match.group(1)) and len(numbers) == 2:
            mentioned.update(range(numbers[0], numbers[1] + 1))
        else:
            mentioned.update(numbers)
    return mentioned


@register(5, "the rule count agrees across SKILL.md, both READMEs and patterns.py")
def rule_count_consistent(root: Path) -> str:
    expected = rule_count(read_skill(root))
    lines = []
    for name, heading in RULE_SECTIONS:
        got = _listed_rules(root, name, heading)
        if got != expected:
            raise CheckFailed(
                f"{name}: listet {got} Regeln, SKILL.md definiert {expected}"
            )
        lines.append(f"{name}: {got} Regeln")

    # patterns.py macht zwei Aussagen, die sonst nichts prüft: das Zahlwort in
    # seinem Modul-Docstring, und dass jede Regel überhaupt darin vorkommt.
    # Beide stimmten, als sie geschrieben wurden — genau so beschrieb das
    # Schwester-Repo zwei Wochen lang «fünf Regeln», nachdem hier die sechste
    # dazugekommen war.
    path = root / PATTERNS
    if not path.is_file():
        raise CheckFailed(f"{PATTERNS}: missing")
    patterns = path.read_text(encoding="utf-8")

    claim = re.search(r"patterns for the (?P<word>\w+) [\w-]+ rules", patterns)
    if not claim:
        raise CheckFailed(
            f"{PATTERNS}: die Wendung 'patterns for the <word> ... rules' ist "
            "weg — Anker entfernt oder umformuliert, diese Prüfung würde "
            "stillschweigend aufhören zu prüfen"
        )
    word = claim.group("word")
    if word not in ENGLISH_NUMBERS:
        raise CheckFailed(
            f"{PATTERNS}: der Docstring sagt {word!r}, und das ist kein "
            "Zahlwort, das diese Prüfung kennt — ENGLISH_NUMBERS in "
            "tools/checks/skill_doc.py ergänzen, sonst meldet der Vergleich "
            "unten eine Abweichung, die in Wahrheit eine Lücke hier ist"
        )
    if ENGLISH_NUMBERS[word] != expected:
        raise CheckFailed(
            f"{PATTERNS}: der Docstring sagt {word!r} Regeln, SKILL.md "
            f"definiert {expected}"
        )

    missing = sorted(set(range(1, expected + 1)) - _mentioned_rules(patterns))
    if missing:
        raise CheckFailed(
            f"{PATTERNS}: nichts zu Regel {missing} — eine Regel ohne Muster "
            "ist eine Regel, die niemand kopieren kann"
        )

    lines.append(f"{PATTERNS}: sagt {word}, deckt alle {expected} ab")
    return "\n".join(lines)


@register(6, "every rule has a row in the rule-to-check table")
def rule_to_check_table(root: Path) -> str:
    # Die Zuordnung Regel -> Audit-Check ist die Stelle, an der dieses Repo
    # zweimal falsch stand (1.4.0 und 1.6.0), und sie zeigt auf ein fremdes
    # Repo, dessen Katalog sich schneller bewegt. Was von hier aus ohne Netz
    # prüfbar ist, ist nicht der Inhalt einer Zeile — dafür gibt es Prüfung 14
    # im Wochenplan —, sondern dass jede Regel überhaupt eine Zeile hat und
    # jede Zeile mindestens eine Check-ID nennt.
    #
    # Grenze, ausdrücklich: Diese Prüfung hätte den Anlass für sich selbst
    # NICHT gefangen. «Ein `FID-006` existiert nicht» nennt eine Check-ID und
    # wäre grün durchgegangen. Sie fängt die nächste Regel ohne Zeile, nicht
    # die nächste veraltete Zeile.
    skill = read_skill(root)
    expected = rule_count(skill)

    match = re.search(
        rf"^{re.escape(TABLE_HEADING)}\n(.*?)(?=^#{{2,3}} |\Z)",
        skill,
        re.M | re.S,
    )
    if not match:
        raise CheckFailed(
            f"SKILL.md: Abschnitt {TABLE_HEADING!r} nicht gefunden — Anker weg "
            "oder umformuliert, diese Prüfung würde stillschweigend aufhören "
            "zu prüfen"
        )

    rows: dict[int, str] = {}
    for line in match.group(1).splitlines():
        row = re.match(r"^\|\s*(\d+)\s*—\s*(.*?)\s*\|(.*)\|\s*$", line)
        if not row:
            continue
        number = int(row.group(1))
        if number in rows:
            raise CheckFailed(f"SKILL.md: Regel {number} hat mehr als eine Zeile")
        rows[number] = row.group(3)

    missing = sorted(set(range(1, expected + 1)) - set(rows))
    if missing:
        raise CheckFailed(
            f"SKILL.md: keine Tabellenzeile für Regel {missing} — eine Regel "
            "ohne Zeile liest sich, als hätte der Katalog nichts zu ihr zu sagen"
        )
    extra = sorted(set(rows) - set(range(1, expected + 1)))
    if extra:
        raise CheckFailed(
            f"SKILL.md: Tabellenzeile für Regel {extra}, die SKILL.md nicht "
            f"definiert ({expected} Regeln)"
        )

    silent = sorted(n for n, cell in rows.items() if not CHECK_ID.search(cell))
    if silent:
        raise CheckFailed(
            f"SKILL.md: Zeile {silent} nennt gar keinen Check — sagen, welcher "
            "Check die Regel abdeckt, oder in Check-IDs sagen, was sie nicht "
            "abdeckt"
        )

    return f"{expected} Regeln, {len(rows)} Zeilen, jede nennt mindestens einen Check"
