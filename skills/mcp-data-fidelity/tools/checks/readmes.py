"""Prüfungen an den READMEs — den zwei Dateien, die von aussen gelesen werden.

Beide Zusagen hier stimmten zum Zeitpunkt des Schreibens. Das ist die Sorte
Aussage, die unbemerkt veraltet: Niemand liest ein Versions-Badge nach, und
eine Tabelle, der ein Eintrag fehlt, sieht vollständig aus.
"""

from __future__ import annotations

import re
from pathlib import Path

from ._core import CheckFailed, register

RELEASE_HEADING = re.compile(r"^## \[v?(?P<version>\d+\.\d+\.\d+)\]")
BADGE = re.compile(r"badge/version-(\d+\.\d+\.\d+)-")

MEMBERS = (
    "mcp-data-source-probe-skill",
    "mcp-data-fidelity-skill",
    "mcp-transport-hardening-skill",
    "mcp-audit-skill",
    "mcp-continuous-auditor",
)
TOPIC_URL = "https://github.com/topics/mcp-quality-chain"
CHAIN_SECTIONS = (
    ("README.md", "The MCP quality chain"),
    ("README.de.md", "Die MCP-Qualitätskette"),
)


def top_release(root: Path) -> tuple[int, str, str]:
    """Zeile, Überschrift und Version des obersten Releases im CHANGELOG.

    Quelle ist die oberste Release-Überschrift. `[Unreleased]` trägt keine
    Versionsnummer und wird vom Muster von selbst übersprungen.

    Geteilt mit Prüfung 13: Badge und Tag werden gegen dieselbe Stelle
    gehalten, nicht gegen zwei Lesungen, die auseinanderlaufen können.
    """
    path = root / "CHANGELOG.md"
    if not path.is_file():
        raise CheckFailed("CHANGELOG.md: missing")
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = RELEASE_HEADING.match(line)
        if match:
            return number, line, match.group("version")
    raise CheckFailed(
        "CHANGELOG.md: keine Release-Überschrift '## [X.Y.Z]' gefunden — Anker "
        "weg, diese Prüfung hätte nichts, wogegen sie vergleicht"
    )


@register(7, "version badge matches the latest CHANGELOG release")
def version_badge(root: Path) -> str:
    lineno, heading, expected = top_release(root)

    # Über das Dateisystem, nicht als gepflegte Liste: Eine dritte
    # Sprachfassung ist damit automatisch abgedeckt.
    readmes = sorted(root.glob("README*.md"))
    if not readmes:
        raise CheckFailed(
            "keine README*.md gefunden — nichts zu prüfen, was ohne diesen "
            "Wächter still durchginge"
        )

    for path in readmes:
        found = BADGE.findall(path.read_text(encoding="utf-8"))
        if not found:
            raise CheckFailed(
                f"{path.name}: kein Versions-Badge gefunden — Anker weg oder "
                "umformuliert, diese Prüfung würde aufhören, diese Datei zu "
                "prüfen"
            )
        stale = sorted({v for v in found if v != expected})
        if stale:
            raise CheckFailed(
                f"{path.name}: das Versions-Badge zeigt {stale}, das oberste "
                f"Release in CHANGELOG.md ist {expected} (Zeile {lineno}: "
                f"{heading.strip()!r}).\n"
                "  Entweder wurde das Badge zum Release nicht mitgezogen, oder "
                "eine Release-Überschrift ist verlorengegangen — prüfen, welche "
                "Seite sich bewegt hat."
            )
    return (
        f"{expected} in {len(readmes)} README-Datei(en), aus CHANGELOG-Zeile {lineno}"
    )


@register(8, "the quality-chain table names all five members")
def quality_chain(root: Path) -> str:
    # Die fünf Repositories der Kette stehen pro Sprache an genau einer Stelle
    # beisammen, und nichts ausserhalb dieses Repos ist von hier aus prüfbar.
    # Prüfbar ist, dass die Tabelle nicht still ein Mitglied verloren hat. Das
    # Topic selbst liegt auf GitHub und wird vom Wächter in mcp-audit-skill
    # geprüft — dem einzigen Repo, das das Manifest führt.
    lines = []
    for name, heading in CHAIN_SECTIONS:
        path = root / name
        if not path.is_file():
            raise CheckFailed(f"{name}: missing")
        match = re.search(
            rf"^### {re.escape(heading)}\n(.*?)(?=^#{{2,3}} |\Z)",
            path.read_text(encoding="utf-8"),
            re.M | re.S,
        )
        if not match:
            raise CheckFailed(
                f"{name}: Abschnitt '### {heading}' nicht gefunden — Anker weg "
                "oder umformuliert, diese Prüfung würde stillschweigend "
                "aufhören zu prüfen"
            )
        body = match.group(1)
        missing = [repo for repo in MEMBERS if repo not in body]
        if missing:
            raise CheckFailed(f"{name}: die Kettentabelle nennt {missing} nicht")
        if TOPIC_URL not in body:
            raise CheckFailed(
                f"{name}: die gemeinsame Topic-Seite {TOPIC_URL} ist nicht "
                "verlinkt — ohne sie ist die Tabelle eine Liste, die von aussen "
                "niemand findet"
            )
        lines.append(f"{name}: alle {len(MEMBERS)} Mitglieder genannt, Topic verlinkt")
    return "\n".join(lines)
