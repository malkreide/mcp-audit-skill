"""Pruefungen an den READMEs: Regelzahl, Kettentabelle, Version-Badge."""

from __future__ import annotations

import re
from pathlib import Path

from ._core import CheckFailed, register

# Bis "fifteen", damit die naechsten Regeln den Wortschatz nicht sprengen: ein
# Zahlwort, das hier fehlt, ergibt `None` und meldete dieselbe Meldung wie ein
# echter Zahlendreher — der Befund zeigte dann auf die falsche Datei.
WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15,
}  # fmt: skip

RULE_LISTS = [
    ("README.md", "The fourteen rules"),
    ("README.de.md", "Die vierzehn Regeln"),
]

MEMBERS = [
    "mcp-data-source-probe-skill",
    "mcp-data-fidelity-skill",
    "mcp-transport-hardening-skill",
    "mcp-audit-skill",
    "mcp-continuous-auditor",
]
TOPIC_URL = "https://github.com/topics/mcp-quality-chain"
CHAIN_SECTIONS = [
    ("README.md", "The MCP quality chain"),
    ("README.de.md", "Die MCP-Qualitätskette"),
]

DOCSTRING_PHRASE = re.compile(r"patterns for the (?P<word>\w+) [\w-]+ rules")
HEADING = re.compile(r"^## \[v?(?P<version>\d+\.\d+\.\d+)\]")
BADGE = re.compile(r"badge/version-(\d+\.\d+\.\d+)-")


def _listed(root: Path, path: str, heading: str) -> int:
    text = (root / path).read_text(encoding="utf-8")
    m = re.search(rf"^## {heading}\n(.*?)(?=^## )", text, re.M | re.S)
    if not m:
        raise CheckFailed(f"{path}: section '## {heading}' not found")
    return len(re.findall(r"^\d+\. ", m.group(1), re.M))


@register(3, "rule count is consistent across SKILL.md, both READMEs and patterns.py")
def rule_count(root: Path) -> str:
    """SKILL.md ist die Quelle; alles andere wird dagegen gehalten.

    `reference/patterns.py` erhebt dabei zwei Behauptungen, die sonst nichts
    prueft: das Zahlwort in seinem Modul-Docstring, und dass jede Regel darin
    tatsaechlich vorkommt. Beide waren richtig, als sie geschrieben wurden —
    genau so hat ein Schwesterrepo zwei Wochen lang weiter «five rules»
    gefuehrt, nachdem die sechste dazugekommen war.
    """
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    expected = len(re.findall(r"^## Regel \d+", skill, re.M))

    for path, heading in RULE_LISTS:
        got = _listed(root, path, heading)
        if got != expected:
            raise CheckFailed(f"{path}: lists {got} rules, SKILL.md defines {expected}")

    patterns = (root / "reference/patterns.py").read_text(encoding="utf-8")
    m = DOCSTRING_PHRASE.search(patterns)
    if not m:
        raise CheckFailed(
            "reference/patterns.py: the phrase 'patterns for the <word> "
            "... rules' is gone — anchor removed or reworded, so this check "
            "would silently stop checking"
        )
    if m.group("word") not in WORDS:
        raise CheckFailed(
            f"reference/patterns.py: docstring says {m.group('word')!r}, which "
            "is not a number word this check knows — extend WORDS in "
            "tools/checks/readmes.py, otherwise the comparison below reports a "
            "mismatch that is really a gap in this check"
        )
    if WORDS[m.group("word")] != expected:
        raise CheckFailed(
            f"reference/patterns.py: docstring says {m.group('word')!r} rules, "
            f"SKILL.md defines {expected}"
        )

    # «Rule 4», «Rules 2 + 3», «Rules 5-7», «rule 1(c)».
    #
    # Nur EINZELNE Nennungen zaehlen als Abdeckung. Eine Sammelueberschrift wie
    # «Rules 8-12» benennt einen Abschnitt; sie belegt nicht, dass es fuer
    # Regel 12 ein Muster gibt, das jemand kopieren koennte. Diese Pruefung
    # expandierte frueher Bereiche, und ein Mutationstest hat gezeigt, was das
    # kostet: Den ganzen Regel-13-Block zu loeschen liess die Datei gruen, weil
    # die Abschnittsueberschrift darueber die 13 mitzaehlte. Bereiche werden
    # weiterhin expandiert — aber nur fuer die Zeile, die ausgegeben wird,
    # nicht fuer das Urteil.
    mentioned, singular = set(), set()
    for mm in re.finditer(r"[Rr]ules?\s+(\d+(?:\s*(?:[-–+,]|and)\s*\d+)*)", patterns):
        nums = [int(n) for n in re.findall(r"\d+", mm.group(1))]
        if len(nums) == 1:
            singular.update(nums)
        if re.search(r"[-–]", mm.group(1)) and len(nums) == 2:
            mentioned.update(range(nums[0], nums[1] + 1))
        else:
            mentioned.update(nums)
    missing = sorted(set(range(1, expected + 1)) - singular)
    if missing:
        raise CheckFailed(
            f"reference/patterns.py: nothing for rule(s) {missing} — a rule "
            "without a pattern is a rule nobody can copy. A collective «Rules "
            "N-M» heading does not count; the rule needs a block that names it "
            "on its own"
        )
    return (
        f"{expected} rules, consistent everywhere; patterns.py says "
        f"{m.group('word')} and covers {sorted(mentioned)}, each named singly"
    )


@register(4, "the quality-chain table names all five members")
def chain_table(root: Path) -> str:
    """Die fuenf Repos der Kette stehen je Sprache an genau EINER Stelle.

    Von hier aus laesst sich nichts ausserhalb dieses Repos pruefen — das
    GitHub-Topic prueft der Guard in `mcp-audit-skill`, dem einzigen Repo mit
    dem Manifest. Was sich hier pruefen laesst, ist, dass die Tabelle nicht
    still ein Mitglied verloren hat.

    Verglichen wird auf NAMENSGRENZE, nicht auf Teilzeichenkette: ein blosses
    `name in body` haette `mcp-continuous-auditor2` und `mcp-audit-skill-v2`
    durchgelassen. `\\b` allein reicht nicht — der Bindestrich ist ein
    Nicht-Wortzeichen und kommt in diesen Namen selbst vor.
    """
    for path, heading in CHAIN_SECTIONS:
        text = (root / path).read_text(encoding="utf-8")
        m = re.search(
            rf"^### {re.escape(heading)}\n(.*?)(?=^#{{2,3}} |\Z)", text, re.M | re.S
        )
        if not m:
            raise CheckFailed(
                f"{path}: section '### {heading}' not found — anchor gone or "
                "reworded, so this check would silently stop checking"
            )
        body = m.group(1)
        missing = [
            r
            for r in MEMBERS
            if not re.search(rf"(?<![\w-]){re.escape(r)}(?![\w-])", body)
        ]
        if missing:
            raise CheckFailed(f"{path}: the chain table does not name {missing}")
        if TOPIC_URL not in body:
            raise CheckFailed(
                f"{path}: the shared topic page {TOPIC_URL} is not linked — "
                "without it the table is a list nobody outside can find"
            )
    return f"all {len(MEMBERS)} members named in {len(CHAIN_SECTIONS)} READMEs"


@register(5, "the version badge matches the latest CHANGELOG release")
def version_badge(root: Path) -> str:
    """Quelle ist die oberste Release-Ueberschrift in CHANGELOG.md.

    `[Unreleased]` traegt keine Versionsnummer und wird vom Muster von selbst
    uebersprungen. Die READMEs werden ueber das Dateisystem gesucht, nicht als
    gepflegte Liste: eine dritte Sprachfassung ist damit automatisch
    abgedeckt, ohne dass jemand daran denken muss.
    """
    lines = (root / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()
    source = next(
        (
            (n, ln, m.group("version"))
            for n, ln in enumerate(lines, 1)
            if (m := HEADING.match(ln))
        ),
        None,
    )
    if source is None:
        raise CheckFailed(
            "CHANGELOG.md: no '## [X.Y.Z]' release heading found — anchor gone, "
            "so this check would have nothing to compare against"
        )
    lineno, heading, expected = source

    readmes = sorted(root.glob("README*.md"))
    if not readmes:
        raise CheckFailed(
            "no README*.md found — nothing to check, which would pass silently"
        )

    for path in readmes:
        found = BADGE.findall(path.read_text(encoding="utf-8"))
        if not found:
            raise CheckFailed(
                f"{path.name}: no version badge found — anchor gone or "
                "reworded, so this check would stop checking this file"
            )
        stale = sorted({v for v in found if v != expected})
        if stale:
            raise CheckFailed(
                f"{path.name}: version badge shows {stale}, but the topmost "
                f"release in CHANGELOG.md is {expected} (line {lineno}: "
                f"{heading.strip()!r}).\n"
                "  Either the badge was not bumped with the release, or a "
                "release heading was lost — check which side moved before "
                "editing."
            )
    return (
        f"badge matches CHANGELOG ({expected}, line {lineno}) in {len(readmes)} file(s)"
    )
