"""Verweise auf Workflow-Dateien, gegen den Baum gehalten.

Uebernommen aus `mcp-data-fidelity-skill` — Familie G15 des Merge-Plans, die
EINZIGE der sechzehn, die nicht bloss zusammengelegt, sondern erweitert
wurde. Warum, steht weiter unten unter SCOPE.

Der Anlass steht in dessen CHANGELOG 1.8.0: `catalogue-drift.yml` wurde zu
`weekly-drift.yml`, und drei Stellen zeigten namentlich auf die alte Datei.
Gefunden hat sie ein `grep` von Hand. Das ist genau die Klasse, gegen die
diese Repositories geschrieben sind: Der Text liest sich weiterhin richtig,
und die Datei gibt es nicht mehr.

SCOPE — DIE ERWEITERUNG FUER DAS MONOREPO. Die Herkunftsfassung durchsuchte
den GANZEN Baum und nahm an, jede Erwaehnung einer `.yml` sei ein Verweis auf
einen EIGENEN Workflow. In einem Skill-Repo stimmt das. In diesem hier nicht:
Gemessen beim Zusammenfuehren fand sie sieben unaufloesbare Erwaehnungen, und
VIER davon waren gar keine — `checks/OPS-001.md`, `DRIFT-005.md`,
`IDENT-006.md` und `ARCH-005.md` nennen Workflows, die ein GEPRUEFTER SERVER
haben soll. Der Katalog beschreibt fremde Repositories; seine Beispiele gegen
den eigenen Baum zu halten ergaebe vier Befunde, wo null Evidenz vorliegt.

`scope` nennt deshalb die Pfade, die ueber DIESES Repository sprechen. Als
Allowlist und nicht als Ausnahmeliste: Eine Ausnahmeliste waechst still, und
was niemand ausgenommen hat, wird geprueft — hier ist es umgekehrt richtig,
weil der Regelfall in einem Monorepo die fremde Rede ist.

ZURUECKGEZOGENE PFADE. Eine Umbenennung hinterlaesst Erwaehnungen, die
RICHTIG BLEIBEN — im CHANGELOG steht, wie die Datei damals hiess, und das
darf nicht umgeschrieben werden. Deshalb `RETIRED`, und deshalb ist die
Ausnahme PRO DATEI und nicht pauschal: Wo ueber die Vergangenheit geredet
wird, ist der alte Name richtig; ueberall sonst ist er ein toter Zeiger, auch
wenn er in dieser Tabelle steht. Eine pauschale Ausnahme haette den
Anlassfall nicht gefangen — dort nannte ein Pruefmodul die alte Datei als
LEBENDEN Zeiger.

DREI WAECHTER UEBER DIE TABELLE SELBST, weil eine Ausnahmeliste genauso still
veraltet wie das, wovor sie ausnimmt:

  * Ein `RETIRED`-Pfad, den es wieder gibt, ist ein Fehler — der Eintrag
    naehme sonst einen LEBENDEN Workflow von der Pruefung aus.
  * Eine Datei unter `historical_in`, die die Erwaehnung gar nicht (mehr)
    enthaelt, ist eine Ausnahme, die niemand braucht.
  * Findet die Pruefung im ganzen Scope keine einzige Erwaehnung, hat sie
    nichts getan und meldete trotzdem Erfolg.

GRENZE, AUSDRUECKLICH. Geprueft wird die Richtung «Verweis → Datei». Die
Gegenrichtung — ein Workflow, den niemand erwaehnt — ist KEIN Befund: Ein
Workflow muss nicht dokumentiert sein, um zu laufen, und eine Pruefung, die
das verlangt, erzwingt Prosa statt Korrektheit.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from tools.harness import CheckFailed

WORKFLOW_DIR = ".github/workflows"

#: Welche Dateien ueberhaupt durchsucht werden. Ueber die Endung und nicht als
#: gepflegte Liste: Eine neue Datei ist damit von selbst erfasst, und genau
#: das Vergessen ist der Fehler, um den es hier geht.
SCANNED_SUFFIXES = {".py", ".md", ".sh", ".yml", ".yaml", ".toml", ".cfg"}
SKIPPED_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}

#: Vollpfad oder blosser Dateiname. Der blosse Name zaehlt nur, wenn er zum
#: Vokabular gehoert (existierende plus zurueckgezogene Workflows) — sonst
#: schluege jede `.pre-commit-config.yaml` in der Prosa an.
MENTION = re.compile(r"(?P<prefix>\.github/workflows/)?(?P<name>[\w.-]+\.ya?ml)")


@dataclasses.dataclass(frozen=True)
class Retired:
    """Ein Workflow-Pfad, den es nicht mehr gibt, und wo er noch stehen darf."""

    successor: str
    since: str
    historical_in: tuple[str, ...]


def existing_workflows(root: Path) -> set[str]:
    """Die Workflows, die es wirklich gibt."""
    verzeichnis = root / WORKFLOW_DIR
    if not verzeichnis.is_dir():
        raise CheckFailed(
            f"{WORKFLOW_DIR} fehlt — ohne das Verzeichnis hat diese Pruefung "
            "nichts, wogegen sie die Verweise haelt."
        )
    return {f"{WORKFLOW_DIR}/{p.name}" for p in sorted(verzeichnis.glob("*.y*ml"))}


def in_scope(root: Path, scope: tuple[str, ...]) -> list[Path]:
    """Die Dateien, die ueber DIESES Repository sprechen.

    `scope` sind Pfad-Praefixe, je eine Datei oder ein Verzeichnis. Ein
    Praefix, das auf nichts passt, ist ein Befund und kein leeres Ergebnis:
    Wer ein Verzeichnis umbenennt und den Scope nicht nachzieht, nimmt es
    stillschweigend aus der Pruefung.
    """
    if not scope:
        raise CheckFailed(
            "Kein Scope genannt — dann durchsucht diese Pruefung nichts und "
            "meldete genau das als Erfolg."
        )

    gefunden: list[Path] = []
    leer = []
    for praefix in scope:
        ziel = root / praefix
        if ziel.is_file():
            treffer = [ziel]
        elif ziel.is_dir():
            treffer = [
                p
                for p in sorted(ziel.rglob("*"))
                if p.is_file()
                and p.suffix in SCANNED_SUFFIXES
                and not any(teil in SKIPPED_DIRS for teil in p.parts)
            ]
        else:
            leer.append(praefix)
            continue
        if not treffer:
            leer.append(praefix)
        gefunden.extend(treffer)

    if leer:
        raise CheckFailed(
            f"Scope-Eintrag ohne Treffer: {leer}.\n"
            "  Umbenannt oder geloescht — und damit stillschweigend aus dieser "
            "Pruefung genommen. Den Scope nachziehen oder den Eintrag "
            "entfernen."
        )
    return gefunden


def collect_mentions(
    root: Path,
    *,
    scope: tuple[str, ...],
    vocabulary: set[str],
    declaring: str,
) -> dict[str, set[str]]:
    """Erwaehnter Workflow-Pfad -> die Dateien, die ihn nennen."""
    basenames = {pfad.rsplit("/", 1)[-1]: pfad for pfad in vocabulary}
    mentions: dict[str, set[str]] = {}
    for pfad in in_scope(root, scope):
        name = pfad.relative_to(root).as_posix()
        if name == declaring:
            continue
        text = pfad.read_text(encoding="utf-8", errors="replace")
        for treffer in MENTION.finditer(text):
            if treffer.group("prefix"):
                ziel = f"{WORKFLOW_DIR}/{treffer.group('name')}"
            elif treffer.group("name") in basenames:
                ziel = basenames[treffer.group("name")]
            else:
                continue
            mentions.setdefault(ziel, set()).add(name)
    return mentions


def assert_mentions_resolve(
    mentions: dict[str, set[str]],
    existing: set[str],
    *,
    retired: dict[str, Retired],
) -> str:
    """Die reine Logik — ohne Dateisystem, damit die Tests sie fahren koennen."""
    if not mentions:
        raise CheckFailed(
            "Kein einziger Verweis auf eine Workflow-Datei im ganzen Scope. "
            "Entweder ist die Erkennung kaputt oder die Verweise sind weg — so "
            "oder so hat diese Pruefung nichts geprueft und wuerde das als "
            "Erfolg melden."
        )

    befunde = []

    for ziel, quellen in sorted(mentions.items()):
        if ziel in existing:
            continue
        eintrag = retired.get(ziel)
        if eintrag is None:
            befunde.append(
                f"{ziel} wird genannt, existiert aber nicht — von "
                f"{sorted(quellen)}.\n"
                "      Tippfehler, oder die Datei ist weg. Wurde sie "
                "umbenannt, gehoert der neue Pfad an die genannten Stellen und "
                "der alte in die RETIRED-Tabelle der Suite."
            )
            continue
        lebend = sorted(set(quellen) - set(eintrag.historical_in))
        if lebend:
            befunde.append(
                f"{ziel} ist seit {eintrag.since} zurueckgezogen, wird aber "
                f"als LEBENDER Zeiger genannt — von {lebend}.\n"
                f"      Nachfolger ist {eintrag.successor}. Wer die Stelle "
                "historisch meint, traegt sie in `historical_in` ein; alles "
                "andere zeigt ins Leere."
            )

    for ziel, eintrag in sorted(retired.items()):
        if ziel in existing:
            befunde.append(
                f"{ziel} steht in RETIRED, gibt es im Baum aber wieder. Der "
                "Eintrag naehme damit einen LEBENDEN Workflow von dieser "
                "Pruefung aus."
            )
            continue
        genannt = mentions.get(ziel, set())
        ueberfluessig = sorted(set(eintrag.historical_in) - genannt)
        if ueberfluessig:
            befunde.append(
                f"{ziel}: `historical_in` nennt {ueberfluessig}, dort steht die "
                "Erwaehnung aber gar nicht (mehr). Eine Ausnahme, die niemand "
                "braucht, verdeckt beim naechsten Mal eine, die jemand braucht."
            )

    if befunde:
        raise CheckFailed("\n".join(f"  - {b}" for b in befunde))

    return (
        f"{len(mentions)} genannte Workflow-Pfade loesen auf "
        f"({len(existing)} vorhanden, {len(retired)} zurueckgezogen)"
    )


def referenced_workflows_exist(
    root: Path,
    *,
    scope: tuple[str, ...],
    retired: dict[str, Retired] | None = None,
    declaring: str = "tools/gates/workflows.py",
) -> str:
    """G15 — jeder Verweis auf einen Workflow zeigt auf eine Datei, die es gibt."""
    zurueckgezogen = retired or {}
    existing = existing_workflows(root)
    mentions = collect_mentions(
        root,
        scope=scope,
        vocabulary=existing | set(zurueckgezogen),
        declaring=declaring,
    )
    return assert_mentions_resolve(mentions, existing, retired=zurueckgezogen)
