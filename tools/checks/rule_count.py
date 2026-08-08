"""Die Regelzahl stimmt in SKILL.md, beiden READMEs und reference/patterns.py.

SKILL.md ist die Quelle: so viele `## Regel N`-Abschnitte, so viele Regeln.
Alles andere wird dagegen gehalten.

`reference/patterns.py` erhebt dabei zwei Behauptungen, die sonst nichts
prueft: das Zahlwort in seinem Modul-Docstring, und dass jede Regel darin
tatsaechlich vorkommt. Beide waren richtig, als sie geschrieben wurden — genau
so hat ein Schwesterrepo zwei Wochen lang weiter «five rules» gefuehrt,
nachdem die sechste dazugekommen war.
"""

from __future__ import annotations

import pathlib
import re
import sys

# Bis "fifteen", damit die naechsten Regeln den Wortschatz nicht sprengen: ein
# Zahlwort, das hier fehlt, ergibt `None` und meldete dieselbe Meldung wie ein
# echter Zahlendreher — der Befund zeigte dann auf die falsche Datei.
WORDS = {
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
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
}

READMES = [
    ("README.md", "The fourteen rules"),
    ("README.de.md", "Die vierzehn Regeln"),
]


def listed(path: str, heading: str) -> int:
    text = pathlib.Path(path).read_text(encoding="utf-8")
    m = re.search(rf"^## {heading}\n(.*?)(?=^## )", text, re.M | re.S)
    if not m:
        sys.exit(f"{path}: section '## {heading}' not found")
    return len(re.findall(r"^\d+\. ", m.group(1), re.M))


def main() -> None:
    skill = pathlib.Path("SKILL.md").read_text(encoding="utf-8")
    expected = len(re.findall(r"^## Regel \d+", skill, re.M))

    for path, heading in READMES:
        got = listed(path, heading)
        if got != expected:
            sys.exit(f"{path}: lists {got} rules, SKILL.md defines {expected}")
        print(f"ok — {path}: {got} rules")

    patterns = pathlib.Path("reference/patterns.py").read_text(encoding="utf-8")

    m = re.search(r"patterns for the (?P<word>\w+) [\w-]+ rules", patterns)
    if not m:
        sys.exit(
            "reference/patterns.py: the phrase 'patterns for the <word> "
            "... rules' is gone — anchor removed or reworded, so this "
            "check would silently stop checking"
        )
    if m.group("word") not in WORDS:
        sys.exit(
            f"reference/patterns.py: docstring says "
            f"{m.group('word')!r}, which is not a number word this "
            "check knows — extend WORDS in tools/checks/rule_count.py, "
            "otherwise the comparison below reports a mismatch that is "
            "really a gap in this script"
        )
    claimed = WORDS[m.group("word")]
    if claimed != expected:
        sys.exit(
            f"reference/patterns.py: docstring says {m.group('word')!r} "
            f"rules, SKILL.md defines {expected}"
        )

    # «Rule 4», «Rules 2 + 3», «Rules 5-7», «rule 1(c)».
    #
    # Nur EINZELNE Nennungen zaehlen als Abdeckung. Eine Sammelueberschrift wie
    # «Rules 8-12» benennt einen Abschnitt; sie belegt nicht, dass es fuer
    # Regel 12 ein Muster gibt, das jemand kopieren koennte. Dieser Check
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
        sys.exit(
            f"reference/patterns.py: nothing for rule(s) {missing} — "
            "a rule without a pattern is a rule nobody can copy. A "
            "collective «Rules N-M» heading does not count; the rule "
            "needs a block that names it on its own"
        )
    print(
        f"ok — reference/patterns.py: says {m.group('word')}, covers "
        f"{sorted(mentioned)}, each named singly"
    )

    print(f"ok — {expected} rules, consistent everywhere")


if __name__ == "__main__":
    main()
