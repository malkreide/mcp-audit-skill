"""Der Version-Badge in jeder README stimmt mit dem obersten CHANGELOG-Release.

Quelle ist die oberste Release-Ueberschrift in CHANGELOG.md. `[Unreleased]`
traegt keine Versionsnummer und wird vom Muster von selbst uebersprungen.

Die READMEs werden ueber das Dateisystem gesucht, nicht als gepflegte Liste:
eine dritte Sprachfassung ist damit automatisch abgedeckt, ohne dass jemand
daran denken muss.

Beide Anker — die Release-Ueberschrift und der Badge — sind FEHLER, wenn sie
fehlen. Ohne sie haette dieser Check nichts zu vergleichen und genau deshalb
Erfolg gemeldet.
"""

from __future__ import annotations

import pathlib
import re
import sys

HEADING = re.compile(r"^## \[v?(?P<version>\d+\.\d+\.\d+)\]")
BADGE = re.compile(r"badge/version-(\d+\.\d+\.\d+)-")


def main() -> None:
    lines = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8").splitlines()
    source = next(
        (
            (n, ln, m.group("version"))
            for n, ln in enumerate(lines, 1)
            if (m := HEADING.match(ln))
        ),
        None,
    )
    if source is None:
        sys.exit(
            "CHANGELOG.md: no '## [X.Y.Z]' release heading found — anchor "
            "gone, so this check would have nothing to compare against"
        )
    lineno, heading, expected = source

    readmes = sorted(pathlib.Path(".").glob("README*.md"))
    if not readmes:
        sys.exit("no README*.md found — nothing to check, which would pass silently")

    for path in readmes:
        found = BADGE.findall(path.read_text(encoding="utf-8"))
        if not found:
            sys.exit(
                f"{path}: no version badge found — anchor gone or reworded, "
                "so this check would stop checking this file"
            )
        stale = sorted({v for v in found if v != expected})
        if stale:
            sys.exit(
                f"{path}: version badge shows {stale}, but the topmost release in "
                f"CHANGELOG.md is {expected} (line {lineno}: {heading.strip()!r}).\n"
                "  Either the badge was not bumped with the release, or a release "
                "heading was lost — check which side moved before editing."
            )
        print(f"ok — {path}: {expected}")
    print(
        f"ok — version badge matches CHANGELOG ({expected}, line {lineno}) "
        f"in {len(readmes)} file(s)"
    )


if __name__ == "__main__":
    main()
