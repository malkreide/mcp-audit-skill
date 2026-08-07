"""Verweise auf Workflow-Dateien, gegen den Baum gehalten.

Der Anlass steht in 1.8.0: `catalogue-drift.yml` wurde zu `weekly-drift.yml`,
und drei Stellen zeigten namentlich auf die alte Datei — zwei Befundtexte, die
sagen, wo der Abruf steht, den sie selbst nicht machen, und ein historischer
Verweis. Gefunden hat sie ein `grep` von Hand. Prüfung 2 hält `REFERENCED_FILES`
gegen den Baum, aber diese Liste ist von Hand gepflegt und kennt die
`.github/`-Pfade nicht; ein toter Verweis auf einen Workflow blieb also
ungeprüft. Das ist genau die Klasse, gegen die dieses Repository geschrieben
ist: Der Text liest sich weiterhin richtig, und die Datei gibt es nicht mehr.

ZURÜCKGEZOGENE PFADE. Eine Umbenennung hinterlässt Erwähnungen, die **richtig
bleiben** — im CHANGELOG steht, wie die Datei damals hiess, und das darf nicht
umgeschrieben werden. Deshalb `RETIRED`, und deshalb ist die Ausnahme **pro
Datei** und nicht pauschal: Wo über die Vergangenheit geredet wird, ist der
alte Name richtig; überall sonst ist er ein toter Zeiger, auch wenn er in
dieser Tabelle steht. Eine pauschale Ausnahme hätte den Anlassfall nicht
gefangen — `catalogue.py` nannte die alte Datei als **lebenden** Zeiger.

DREI WÄCHTER ÜBER DIE TABELLE SELBST, weil eine Ausnahmeliste genauso still
veraltet wie das, wovor sie ausnimmt:

  * Ein `RETIRED`-Pfad, den es wieder gibt, ist ein Fehler — der Eintrag würde
    sonst einen **lebenden** Workflow von der Prüfung ausnehmen.
  * Eine Datei unter `historical_in`, die die Erwähnung gar nicht (mehr)
    enthält, ist eine Ausnahme, die niemand braucht — dieselbe Form wie eine
    Mutation, deren Suchtext nicht mehr im Baum steht.
  * Findet die Prüfung im ganzen Baum keine einzige Erwähnung, hat sie nichts
    getan und meldete trotzdem Erfolg. Das ist der `ruff.toml`-Fall.

GRENZE, AUSDRÜCKLICH. Geprüft wird die Richtung «Verweis → Datei». Die
Gegenrichtung — ein Workflow, den niemand erwähnt — ist **kein** Befund: Ein
Workflow muss nicht dokumentiert sein, um zu laufen, und eine Prüfung, die das
verlangt, erzwingt Prosa statt Korrektheit.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from ._core import CheckFailed, register

WORKFLOW_DIR = ".github/workflows"

# Die Datei, die diese Tabelle führt. Sie nennt jeden zurückgezogenen Pfad per
# Konstruktion und ist deshalb von der Prüfung ausgenommen — implizit und nicht
# je Eintrag, weil ein Eintrag ohne diese Zeile sonst sofort seinen eigenen
# Befund erzeugte.
DECLARING = "tools/checks/workflows.py"

# Welche Dateien überhaupt nach Erwähnungen durchsucht werden. Über die
# Endung und nicht als gepflegte Liste: Eine neue Datei ist damit von selbst
# erfasst, und genau das Vergessen ist der Fehler, um den es hier geht.
SCANNED_SUFFIXES = {".py", ".md", ".sh", ".yml", ".yaml", ".toml", ".cfg"}
SKIPPED_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}

# Vollpfad oder blosser Dateiname. Der blosse Name zählt nur, wenn er zum
# Vokabular gehört (existierende plus zurückgezogene Workflows) — sonst schlüge
# jede `.pre-commit-config.yaml` in der Prosa an.
MENTION = re.compile(r"(?P<prefix>\.github/workflows/)?(?P<name>[\w.-]+\.ya?ml)")


@dataclasses.dataclass(frozen=True)
class Retired:
    """Ein Workflow-Pfad, den es nicht mehr gibt, und wo er noch stehen darf."""

    successor: str
    since: str
    historical_in: tuple[str, ...]


RETIRED: dict[str, Retired] = {
    f"{WORKFLOW_DIR}/catalogue-drift.yml": Retired(
        successor=f"{WORKFLOW_DIR}/weekly-drift.yml",
        since="1.8.0",
        historical_in=(
            # Der CHANGELOG-Eintrag zu 1.7.0 beschreibt den damaligen Stand.
            # Ein CHANGELOG, der seine eigene Vergangenheit umschreibt, taugt
            # als Beleg nichts.
            "CHANGELOG.md",
            # «Bis 1.7.0 standen die Prüfungen als Heredocs in …» — die Aussage
            # wäre ohne den alten Namen nicht mehr auffindbar.
            "tools/checks/_core.py",
            # Der Kopf der Nachfolgerin sagt, wie sie vorher hiess, und was die
            # Umbenennung gekostet hat.
            f"{WORKFLOW_DIR}/weekly-drift.yml",
            # Eine Mutation legt die zurückgezogene Datei wieder an, um zu
            # belegen, dass der Wächter über die Tabelle beisst.
            "tests/mutations.py",
        ),
    ),
}


def existing_workflows(root: Path) -> set[str]:
    """Die Workflows im Baum, oder ein Befund, falls es keine gibt.

    Der Wächter steht *in* der Prüfung und nicht daneben: Verschwindet das
    Verzeichnis, hätte sie kein Vokabular mehr und liefe über jeden Verweis
    hinweg, ohne einen davon prüfen zu können.
    """
    directory = root / WORKFLOW_DIR
    if not directory.is_dir():
        raise CheckFailed(
            f"{WORKFLOW_DIR}/ fehlt — Verzeichnis umbenannt oder gelöscht. "
            "Ohne es hätte diese Prüfung nichts, wogegen sie Verweise hält."
        )
    found = {
        f"{WORKFLOW_DIR}/{path.name}"
        for path in sorted(directory.iterdir())
        if path.suffix in {".yml", ".yaml"} and path.is_file()
    }
    if not found:
        raise CheckFailed(
            f"{WORKFLOW_DIR}/ enthält keine Workflow-Datei — die Prüfung hätte "
            "nichts zu tun und hätte genau deshalb Erfolg gemeldet"
        )
    return found


def scanned_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in SCANNED_SUFFIXES
        and not SKIPPED_DIRS & set(path.relative_to(root).parts)
    )


def collect_mentions(root: Path, vocabulary: set[str]) -> dict[str, set[str]]:
    """Erwähnter Workflow-Pfad -> die Dateien, die ihn nennen."""
    basenames = {path.rsplit("/", 1)[-1]: path for path in vocabulary}
    mentions: dict[str, set[str]] = {}
    for path in scanned_files(root):
        name = path.relative_to(root).as_posix()
        if name == DECLARING:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in MENTION.finditer(text):
            if match.group("prefix"):
                target = f"{WORKFLOW_DIR}/{match.group('name')}"
            elif match.group("name") in basenames:
                target = basenames[match.group("name")]
            else:
                continue
            mentions.setdefault(target, set()).add(name)
    return mentions


def assert_mentions_resolve(mentions: dict[str, set[str]], existing: set[str]) -> str:
    """Die reine Logik — ohne Dateisystem, damit die Tests sie fahren können."""
    if not mentions:
        raise CheckFailed(
            "Kein einziger Verweis auf eine Workflow-Datei im ganzen Baum. "
            "Entweder ist die Erkennung kaputt oder die Verweise sind weg — so "
            "oder so hat diese Prüfung nichts geprüft und würde das als Erfolg "
            "melden."
        )

    problems = []

    for target, sources in sorted(mentions.items()):
        if target in existing:
            continue
        retired = RETIRED.get(target)
        if retired is None:
            problems.append(
                f"{target} wird genannt, existiert aber nicht — von "
                f"{sorted(sources)}.\n"
                "      Tippfehler, oder die Datei ist weg. Wurde sie "
                "umbenannt, gehört der neue Pfad an die genannten Stellen und "
                "der alte nach RETIRED in tools/checks/workflows.py."
            )
            continue
        living = sorted(set(sources) - set(retired.historical_in))
        if living:
            problems.append(
                f"{target} ist seit {retired.since} zurückgezogen, wird aber "
                f"als lebender Zeiger genannt — von {living}.\n"
                f"      Nachfolger ist {retired.successor}. Wer die Stelle "
                "historisch meint, trägt sie in `historical_in` ein; alles "
                "andere zeigt ins Leere."
            )

    for target, retired in sorted(RETIRED.items()):
        if target in existing:
            problems.append(
                f"{target} steht in RETIRED, gibt es im Baum aber wieder. Der "
                "Eintrag nähme damit einen LEBENDEN Workflow von dieser "
                "Prüfung aus — streichen."
            )
            continue
        stale = sorted(set(retired.historical_in) - mentions.get(target, set()))
        if stale:
            problems.append(
                f"{target}: `historical_in` nennt {stale}, dort steht der Pfad "
                "aber nicht (mehr). Eine Ausnahme ohne Gegenstand ist eine, "
                "die beim nächsten Mal die falsche Stelle durchwinkt — "
                "streichen."
            )

    if problems:
        raise CheckFailed(
            "Verweise auf Workflow-Dateien stimmen nicht mehr:\n\n"
            + "\n".join(f"  - {p}" for p in problems)
        )

    retired_seen = sum(1 for t in mentions if t in RETIRED)
    return (
        f"{len(mentions)} Workflow-Pfad(e) genannt, alle aufgelöst "
        f"({retired_seen} davon historisch)"
    )


@register(16, "every referenced workflow file exists")
def referenced_workflows_exist(root: Path) -> str:
    existing = existing_workflows(root)
    vocabulary = existing | set(RETIRED)
    return assert_mentions_resolve(collect_mentions(root, vocabulary), existing)
