"""Die READMEs: stimmt das Versions-Badge, und ist die Kette vollstaendig?

Zusammengefuehrt aus den drei Fassungen in `mcp-data-source-probe-skill`,
`mcp-data-fidelity-skill` und `mcp-transport-hardening-skill` — Familien G11
und G12 des Merge-Plans.

BEIDE PRUEFUNGEN SUCHEN IHRE DATEIEN UEBER DAS DATEISYSTEM, nicht ueber eine
gepflegte Liste: Eine dritte Sprachfassung ist damit automatisch abgedeckt,
ohne dass jemand daran denken muss. Findet die Suche nichts, ist das ein
Befund — «nichts gefunden» und «alles in Ordnung» duerfen nicht gleich
aussehen.

DER GROESSTE UNTERSCHIED ZU DEN HERKUNFTSFASSUNGEN steht in `chain_table`.
Dort fuehrte jedes der drei Repos die Mitglieder der Kette als HARTE LISTE im
eigenen Pruefmodul — fuenf Namen, dreimal gepflegt. Seit Phase 3b stehen sie
an einer Stelle, in `docs/quality-chain.json`, und diese Pruefung liest sie
von dort. Damit kann die Tabelle im README nicht mehr gegen eine Liste
stimmen, die ihrerseits veraltet ist.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tools.harness import CheckFailed

RELEASE_HEADING = re.compile(r"^## \[v?(?P<version>\d+\.\d+\.\d+)\]")
BADGE = re.compile(r"badge/version-(\d+\.\d+\.\d+)-")


def _readmes(root: Path, base: str) -> list[Path]:
    verzeichnis = root / base
    gefunden = sorted(verzeichnis.glob("README*.md"))
    if not gefunden:
        raise CheckFailed(
            f"keine README*.md unter {base} gefunden — nichts zu pruefen, was "
            "ohne diesen Waechter still durchginge"
        )
    return gefunden


def top_release(root: Path, *, base: str = ".") -> tuple[int, str, str]:
    """Die oberste Release-Ueberschrift: `(Zeile, Text, Version)`.

    `[Unreleased]` traegt keine Versionsnummer und wird vom Muster von selbst
    uebersprungen — genau deshalb steht die Version im Muster und nicht im
    Klammerinhalt.
    """
    changelog = root / base / "CHANGELOG.md"
    if not changelog.is_file():
        raise CheckFailed(f"{base}/CHANGELOG.md fehlt")

    zeilen = changelog.read_text(encoding="utf-8").splitlines()
    treffer = next(
        (
            (n, zeile, m.group("version"))
            for n, zeile in enumerate(zeilen, 1)
            if (m := RELEASE_HEADING.match(zeile))
        ),
        None,
    )
    if treffer is None:
        raise CheckFailed(
            f"{base}/CHANGELOG.md: keine Release-Ueberschrift '## [X.Y.Z]' "
            "gefunden — Anker weg, diese Pruefung haette nichts, wogegen sie "
            "vergleicht"
        )
    return treffer


def version_badge(root: Path, *, base: str = ".") -> str:
    """G11 — das Versions-Badge zeigt das oberste Release des CHANGELOG."""
    lineno, heading, erwartet = top_release(root, base=base)

    for pfad in _readmes(root, base):
        gefunden = BADGE.findall(pfad.read_text(encoding="utf-8"))
        if not gefunden:
            raise CheckFailed(
                f"{pfad.name}: kein Versions-Badge gefunden — Anker weg oder "
                "umformuliert; diese Pruefung wuerde aufhoeren, diese Datei zu "
                "pruefen, ohne dass etwas rot wird"
            )
        veraltet = sorted({v for v in gefunden if v != erwartet})
        if veraltet:
            raise CheckFailed(
                f"{pfad.name}: das Versions-Badge zeigt {veraltet}, das "
                f"oberste Release im CHANGELOG ist {erwartet} (Zeile "
                f"{lineno}: {heading.strip()!r}).\n"
                "  Entweder wurde das Badge zum Release nicht mitgezogen, oder "
                "eine Release-Ueberschrift ist verlorengegangen — pruefen, "
                "welches von beidem."
            )
    return f"Versions-Badge {erwartet} in allen READMEs unter {base}"


def chain_members(root: Path, *, manifest: str) -> list[str]:
    """Die Namen der Ketten-Mitglieder, aus dem Manifest.

    AUS DEM MANIFEST UND NICHT AUS EINER KONSTANTE. In den Herkunftsrepos
    stand die Liste dreimal im Pruefcode; seit Phase 3b steht sie einmal in
    `docs/quality-chain.json`. Eine Tabelle gegen eine Liste zu halten, die
    ihrerseits veralten kann, prueft nur, ob zwei Kopien noch dieselbe
    Unwahrheit sagen.
    """
    pfad = root / manifest
    if not pfad.is_file():
        raise CheckFailed(
            f"{manifest} fehlt — ohne das Manifest weiss diese Pruefung nicht, "
            "wen die Tabelle nennen muss."
        )
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    namen = [m.get("skill") for m in daten.get("members", [])]
    if not namen or not all(namen):
        raise CheckFailed(
            f"{manifest}: 'members' ist leer oder ein Mitglied hat kein "
            "'skill' — dann prueft diese Pruefung nichts."
        )
    return namen


def chain_table(
    root: Path,
    *,
    sections: tuple[tuple[str, str], ...],
    manifest: str = "docs/quality-chain.json",
) -> str:
    """G12 — die Ketten-Tabelle nennt jedes Mitglied des Manifests.

    Kein Vergleich der Prosa — nur, dass kein Mitglied fehlt. Wer eines
    hinzufuegt und die READMEs vergisst, sieht es hier statt in vier Wochen.

    Der Abschnitt wird ueber seine UEBERSCHRIFT gefunden, und fehlt sie, ist
    das ein Befund: Ohne Anker wuerde diese Pruefung stillschweigend aufhoeren
    zu pruefen.
    """
    namen = chain_members(root, manifest=manifest)

    for datei, ueberschrift in sections:
        pfad = root / datei
        if not pfad.is_file():
            raise CheckFailed(f"{datei} fehlt")
        text = pfad.read_text(encoding="utf-8")
        # `##` ODER `###`: Der Anker ist der TEXT der Ueberschrift, nicht ihre
        # Tiefe. Die READMEs fuehren die Tabelle unter «Related repositories»
        # als `###`, die drei `SKILL.md` unter `## Verwandte Skills` als `##`.
        # Auf eine Tiefe zu bestehen hiesse, die Haelfte der Tabellen
        # ungeprueft zu lassen — und genau das war bis 2b-iv-c der Fall.
        abschnitt = re.search(
            rf"^#{{2,3}} {re.escape(ueberschrift)}\n(.*?)(?=^#{{2,3}} |\Z)",
            text,
            re.M | re.S,
        )
        if not abschnitt:
            raise CheckFailed(
                f"{datei}: Abschnitt '{ueberschrift}' nicht gefunden — "
                "Anker weg oder umformuliert, diese Pruefung wuerde "
                "stillschweigend aufhoeren zu pruefen"
            )
        rumpf = abschnitt.group(1)
        fehlend = [name for name in namen if name not in rumpf]
        if fehlend:
            raise CheckFailed(
                f"{datei}: die Ketten-Tabelle nennt {fehlend} nicht.\n"
                f"  Das Manifest {manifest} fuehrt sie als Mitglied — "
                "entweder ist die Tabelle nicht nachgezogen worden, oder das "
                "Mitglied gehoert dort nicht mehr hin."
            )
    return f"{len(sections)} Ketten-Tabellen nennen alle {len(namen)} Mitglieder"
