"""Die Tabelle der Qualitaetskette nennt alle fuenf Mitglieder.

Die fuenf Repositories der Kette stehen je Sprache an genau EINER Stelle
zusammen. Von hier aus laesst sich nichts ausserhalb dieses Repos pruefen — das
GitHub-Topic selbst prueft der Guard in `mcp-audit-skill`, dem einzigen Repo
mit dem Manifest. Was sich hier pruefen laesst, ist, dass die Tabelle nicht
still ein Mitglied verloren hat.

ACHTUNG, Eigenschaft dieses Checks: Verglichen wird per Teilzeichenkette. Ein
Mitglied, das einen SUFFIX bekommt (`mcp-continuous-auditor2`), besteht damit
weiterhin — der alte Name steckt ja noch darin. Gefangen wird das Umbenennen
und das Weglassen, nicht das Anhaengen.
"""

from __future__ import annotations

import pathlib
import re
import sys

MEMBERS = [
    "mcp-data-source-probe-skill",
    "mcp-data-fidelity-skill",
    "mcp-transport-hardening-skill",
    "mcp-audit-skill",
    "mcp-continuous-auditor",
]
TOPIC_URL = "https://github.com/topics/mcp-quality-chain"

SECTIONS = [
    ("README.md", "The MCP quality chain"),
    ("README.de.md", "Die MCP-Qualitätskette"),
]


def main() -> None:
    for path, heading in SECTIONS:
        text = pathlib.Path(path).read_text(encoding="utf-8")
        m = re.search(
            rf"^### {re.escape(heading)}\n(.*?)(?=^#{{2,3}} |\Z)", text, re.M | re.S
        )
        if not m:
            sys.exit(
                f"{path}: section '### {heading}' not found — anchor gone "
                "or reworded, so this check would silently stop checking"
            )
        body = m.group(1)
        missing = [r for r in MEMBERS if r not in body]
        if missing:
            sys.exit(f"{path}: the chain table does not name {missing}")
        if TOPIC_URL not in body:
            sys.exit(
                f"{path}: the shared topic page {TOPIC_URL} is not linked — "
                "without it the table is a list nobody outside can find"
            )
        print(f"ok — {path}: all {len(MEMBERS)} members named, topic page linked")


if __name__ == "__main__":
    main()
