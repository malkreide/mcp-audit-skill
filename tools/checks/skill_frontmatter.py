"""SKILL.md traegt ein wohlgeformtes Frontmatter.

Geprueft werden drei Behauptungen, die sonst niemand nachhaelt:

* Das Frontmatter existiert ueberhaupt und laesst sich parsen.
* Der Name ist `mcp-transport-hardening` — ein anderer Name laesst den Skill
  unter falschem Namen laden, und zwar still.
* Die Description bleibt unter 1024 Zeichen, weil laengere abgeschnitten
  werden.

Ein fehlendes Frontmatter ist ein FEHLER, kein Grund zum Ueberspringen: Dann
hat der Vergleich nicht stattgefunden, und «nicht gelaufen» als «bestanden» zu
melden ist die eine Auskunft, die schlimmer ist als keine.
"""

from __future__ import annotations

import pathlib
import re
import sys

EXPECTED_NAME = "mcp-transport-hardening"
MAX_DESCRIPTION = 1024


def main() -> None:
    p = pathlib.Path("SKILL.md")
    m = re.match(
        r"^---\nname: (.+?)\ndescription: (.+?)\n---\n",
        p.read_text(encoding="utf-8"),
        re.S,
    )
    if not m:
        sys.exit("SKILL.md: frontmatter missing or malformed")
    name, desc = m.group(1).strip(), m.group(2).strip()
    if name != EXPECTED_NAME:
        sys.exit(f"SKILL.md: expected name {EXPECTED_NAME!r}, got {name!r}")
    if len(desc) > MAX_DESCRIPTION:
        sys.exit(f"SKILL.md: description too long ({len(desc)} > {MAX_DESCRIPTION})")
    print(f"ok — name={name}, description={len(desc)} chars")


if __name__ == "__main__":
    main()
