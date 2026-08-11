"""Prüfungen an den READMEs — den zwei Dateien, die von aussen gelesen werden.

Beide Zusagen hier sind Zahlen bzw. Listen, die zum Zeitpunkt des Schreibens
stimmten. Das ist die Sorte Aussage, die unbemerkt veraltet: Niemand liest ein
Versions-Badge nach, und eine Tabelle, der ein Eintrag fehlt, sieht vollständig
aus.
"""

from __future__ import annotations

import re
from pathlib import Path

from ._core import CheckFailed, register
from .skill_doc import read_skill, step_kinds

RELEASE_HEADING = re.compile(r"^## \[v?(?P<version>\d+\.\d+\.\d+)\]")
BADGE = re.compile(r"badge/version-(\d+\.\d+\.\d+)-")

# Die Schritt-Aufzählung der beiden READMEs. Pro Sprache: die Überschrift des
# Abschnitts, das Wort für einen einzelnen Schritt und das für mehrere.
#
# Getrennte Wörter statt eines optionalen Suffixes, weil genau dieser
# Unterschied das Urteil trägt: «Schritt 3» zählt als eigener Aufzählungspunkt,
# «Schritte 4-6» ist die Sammelzeile für die Übergabe. Wer beides gleich läse,
# zählte die Sammelzeile als vierten Kernschritt mit.
STEP_SECTIONS = (
    ("README.md", "Features", "Step", "Steps"),
    ("README.de.md", "Funktionen", "Schritt", "Schritte"),
)

# Die READMEs setzen ein Halbgeviert zwischen die beiden Zahlen. Als Escape
# geschrieben, nicht als Zeichen: RUF001 beanstandet ein woertlich gesetztes
# Halbgeviert zu Recht, weil es im Quelltext nicht vom Bindestrich zu
# unterscheiden ist. Akzeptiert werden alle drei Striche — welchen ein Editor
# einsetzt, ist Typografie und darf keinen Befund ausloesen.
SPAN_DASH = r"[-\u2013\u2014]"

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


def _readmes(root: Path) -> list[Path]:
    """Über das Dateisystem, nicht als gepflegte Liste.

    Eine dritte Sprachfassung ist damit automatisch abgedeckt.
    """
    found = sorted(root.glob("README*.md"))
    if not found:
        raise CheckFailed(
            "keine README*.md gefunden — nichts zu prüfen, was ohne diesen "
            "Wächter still durchginge"
        )
    return found


@register(9, "version badge matches the latest CHANGELOG release")
def version_badge(root: Path) -> str:
    # Quelle ist die oberste Release-Überschrift. `[Unreleased]` trägt keine
    # Versionsnummer und wird vom Muster von selbst übersprungen.
    changelog = root / "CHANGELOG.md"
    if not changelog.is_file():
        raise CheckFailed("CHANGELOG.md: missing")
    lines = changelog.read_text(encoding="utf-8").splitlines()
    source = next(
        (
            (n, line, match.group("version"))
            for n, line in enumerate(lines, 1)
            if (match := RELEASE_HEADING.match(line))
        ),
        None,
    )
    if source is None:
        raise CheckFailed(
            "CHANGELOG.md: keine Release-Überschrift '## [X.Y.Z]' gefunden — "
            "Anker weg, diese Prüfung hätte nichts, wogegen sie vergleicht"
        )
    lineno, heading, expected = source

    readmes = _readmes(root)
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
                "  Entweder wurde das Badge zum Release nicht mitgezogen, "
                "oder eine Release-Überschrift ist verlorengegangen — prüfen, "
                "welche Seite sich bewegt hat."
            )
    return f"{expected} in {len(readmes)} README file(s), from CHANGELOG line {lineno}"


@register(10, "the quality-chain table names all five members")
def quality_chain(root: Path) -> str:
    # Die fünf Repositories der Kette stehen pro Sprache an genau einer Stelle
    # beisammen, und nichts ausserhalb dieses Repos ist von hier aus prüfbar.
    # Prüfbar ist, dass die Tabelle nicht still ein Mitglied verloren hat —
    # so blieb der nachgestellte Satz «daneben gibt es noch
    # mcp-continuous-auditor» so lange unbemerkt: Der Auditor war erwähnt,
    # aber nicht in der Tabelle, und las sich damit als Nachgedanke statt als
    # fünftes Glied.
    #
    # Das Topic selbst liegt auf GitHub und wird vom Wächter in
    # mcp-audit-skill (tools/check_quality_chain.py) geprüft — dem einzigen
    # Repo, das das Manifest führt.
    lines = []
    for name, heading in CHAIN_SECTIONS:
        path = root / name
        if not path.is_file():
            raise CheckFailed(f"{name}: missing")
        text = path.read_text(encoding="utf-8")
        match = re.search(
            rf"^### {re.escape(heading)}\n(.*?)(?=^#{{2,3}} |\Z)",
            text,
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
                "verlinkt — ohne sie ist die Tabelle eine Liste, die von "
                "aussen niemand findet"
            )
        lines.append(f"{name}: all {len(MEMBERS)} members named, topic page linked")
    return "\n".join(lines)


@register(19, "both READMEs enumerate the steps SKILL.md defines")
def readme_step_list(root: Path) -> str:
    # Die Aufteilung in [Kern] und [Übergabe] steht in SKILL.md, und Check 11
    # hält sie dort gegen Frontmatter und Einleitung. Was Check 11 NICHT
    # erreicht, sind die beiden READMEs: Sie zählen dieselben Schritte ein
    # zweites Mal auf, in Prosa, und niemand hielt sie bisher gegen die
    # Quelle. Käme ein vierter Kernschritt dazu, liste hier weiter «Step 1-3»
    # samt «Steps 4-6» — vollständig aussehend und falsch. Genau die Sorte
    # Aussage, die unbemerkt veraltet.
    #
    # Das Schwester-Repo mcp-transport-hardening-skill prüft die Entsprechung
    # (Regelzahl gegen beide READMEs) seit Längerem; hier fehlte sie.
    kinds = step_kinds(read_skill(root))
    core = sum(1 for k in kinds if k == "Kern")
    total = len(kinds)

    lines = []
    for name, heading, singular, plural in STEP_SECTIONS:
        path = root / name
        if not path.is_file():
            raise CheckFailed(f"{name}: missing")
        text = path.read_text(encoding="utf-8")
        match = re.search(
            rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)",
            text,
            re.M | re.S,
        )
        if not match:
            raise CheckFailed(
                f"{name}: Abschnitt '## {heading}' nicht gefunden — Anker weg "
                "oder umformuliert, diese Prüfung würde stillschweigend "
                "aufhören zu prüfen"
            )
        body = match.group(1)

        # Nur EINZELNE Nennungen zählen als Kernschritt. Die Sammelzeile
        # «Steps 4-6» benennt die Übergabe; sie als Aufzählungspunkt
        # mitzuzählen hiesse, drei Schritte für einen zu nehmen.
        listed = [
            int(n) for n in re.findall(rf"^- \*\*{singular} (\d+) — ", body, re.M)
        ]
        if not listed:
            raise CheckFailed(
                f"{name}: kein Aufzählungspunkt '- **{singular} N — ' im "
                f"Abschnitt '## {heading}' — Anker weg oder umformuliert, "
                "diese Prüfung würde aufhören, die Schritt-Liste zu prüfen"
            )
        if listed != list(range(1, core + 1)):
            raise CheckFailed(
                f"{name}: der Abschnitt '## {heading}' zählt die Schritte "
                f"{listed} einzeln auf, SKILL.md markiert {core} als [Kern] "
                f"(von {total} insgesamt).\n"
                "  Entweder kam ein Kernschritt dazu, ohne dass die READMEs "
                "mitgingen, oder ein Schritt hat die Art gewechselt — prüfen, "
                "welche Seite sich bewegt hat."
            )

        handover = total - core
        if handover == 0:
            lines.append(f"{name}: {core} Kernschritt(e) einzeln, keine Übergabe")
            continue

        # Die Sammelzeile trägt zwei Zahlen, und beide sind prüfbar: Der
        # Anfang muss auf den letzten Kernschritt folgen, das Ende die
        # Gesamtzahl treffen. Eine Lücke dazwischen liesse einen Schritt aus,
        # den SKILL.md führt.
        span = re.search(rf"^- \*\*{plural} (\d+){SPAN_DASH}(\d+) — ", body, re.M)
        if not span:
            raise CheckFailed(
                f"{name}: keine Sammelzeile '- **{plural} N-M — ' im "
                f"Abschnitt '## {heading}' — Anker weg oder umformuliert. "
                f"SKILL.md führt {handover} Übergabeschritt(e); ohne diese "
                "Zeile nennt die README sie nicht, und diese Prüfung merkte "
                "es nicht mehr"
            )
        first, last = int(span.group(1)), int(span.group(2))
        if (first, last) != (core + 1, total):
            raise CheckFailed(
                f"{name}: die Übergabe steht als '{plural} {first}-{last}', "
                f"SKILL.md führt Schritt {core + 1} bis {total} als "
                "[Übergabe].\n"
                "  Eine Sammelzeile, die zu früh anfängt, zählt einen "
                "Kernschritt zur Übergabe; eine, die zu früh endet, lässt "
                "einen Schritt ganz aus."
            )
        lines.append(
            f"{name}: {core} Kernschritt(e) einzeln, "
            f"{plural} {first}-{last} als Übergabe"
        )

    return "\n".join(lines)
