"""Für jede Prüfung: mindestens ein Baum, auf dem sie rot werden MUSS.

Eine Prüfung, die nie rot geworden ist, ist eine Behauptung. Dieses
Repository hat den Beleg dafür in der eigenen Geschichte, und zwar in beide
Richtungen: `ruff.toml` stand auf `select = []`, beide Ruff-Schritte meldeten
«All checks passed!», und niemand merkte es — und der Katalog-Job schlug bei
seinem ersten Lauf umgekehrt falsch an, weil er eine korrekte Gegenrede in
SKILL.md als Fehler las.

Jede Mutation nennt drei Dinge:

  * WELCHE Prüfung sie treffen soll,
  * WAS sie kaputt macht — als Delta auf einer Kopie des echten Baums, nicht
    als handgeschriebene Attrappe (siehe `conftest.py`),
  * WELCHER Teil des Befundes dabei herauskommen muss.

Das Dritte ist nicht Zierde. «Wird rot» genügt nicht: Eine Prüfung, die aus
dem falschen Grund rot wird, schickt den Lesenden zur falschen Datei — und
Regel 5 sagt, was danach kommt.

Ausserdem schlägt eine Mutation, deren Suchtext nicht mehr im Baum steht,
laut fehl statt still zu passieren. Sonst wäre eine veraltete Mutation ein
Test, der nichts mehr testet — wieder derselbe Fehler, eine Ebene höher.
"""

from __future__ import annotations

import dataclasses
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

PATTERNS = "reference/patterns.py"
MANIFEST = "manifest.txt"
METADATA = "repo-metadata.json"


@dataclasses.dataclass(frozen=True)
class Mutation:
    check: int
    name: str
    apply: Callable[[Path], None]
    expect: str


class MutationStale(AssertionError):
    """Die Mutation greift nicht mehr — sie sucht etwas, das es nicht gibt.

    Ausdrücklich ein Fehler und kein Grund zum Überspringen: Eine Mutation,
    die ins Leere greift, lässt den Test grün werden, ohne die Prüfung je
    herausgefordert zu haben.
    """


# --- Bausteine ---------------------------------------------------------


def replace(rel: str, old: str, new: str) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise MutationStale(
                f"{rel} enthält {old!r} nicht mehr — diese Mutation greift ins "
                "Leere und würde die Prüfung nicht mehr herausfordern."
            )
        path.write_text(text.replace(old, new), encoding="utf-8")

    return apply


def regex_sub(
    rel: str, pattern: str, repl: str, flags: re.RegexFlag = re.M
) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        path = root / rel
        mutated, count = re.subn(
            pattern, repl, path.read_text(encoding="utf-8"), flags=flags
        )
        if count == 0:
            raise MutationStale(
                f"{rel}: das Muster {pattern!r} passt nirgends mehr — diese "
                "Mutation greift ins Leere."
            )
        path.write_text(mutated, encoding="utf-8")

    return apply


def append(rel: str, text: str) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        path = root / rel
        if not path.is_file():
            raise MutationStale(f"{rel} gibt es nicht mehr")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)

    return apply


def write(rel: str, text: str) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    return apply


def remove(rel: str) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        path = root / rel
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        else:
            raise MutationStale(f"{rel} gibt es schon nicht mehr")

    return apply


def remove_glob(pattern: str) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        found = list(root.glob(pattern))
        if not found:
            raise MutationStale(f"{pattern} passt auf nichts")
        for path in found:
            path.unlink()

    return apply


def drop_last_line(rel: str) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        path = root / rel
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 2:
            raise MutationStale(f"{rel} hat nichts zu streichen")
        path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    return apply


def track(rel: str, text: str) -> Callable[[Path], None]:
    """Legt eine Datei an UND nimmt sie in den Index auf.

    Für Prüfung 3: `.gitignore` deckt `*.py[cod]` ab, deshalb `add -f`.
    """

    def apply(root: Path) -> None:
        (root / rel).write_text(text, encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "-f", rel], check=True)

    return apply


def chain(*steps: Callable[[Path], None]) -> Callable[[Path], None]:
    """Mehrere Schritte als eine Mutation.

    Für Fälle, in denen eine Aussage an mehreren Stellen steht und erst das
    Streichen aller Stellen die Prüfung herausfordert.
    """

    def apply(root: Path) -> None:
        for step in steps:
            step(root)

    return apply


# --- Die Mutationen ----------------------------------------------------

MUTATIONS: list[Mutation] = [
    # 1 — python references are syntactically valid
    Mutation(1, "reference/ weg", remove("reference"), "reference/ fehlt"),
    Mutation(
        1,
        "reference/ ohne .py",
        remove_glob("reference/*.py"),
        "enthält keine .py-Datei",
    ),
    Mutation(
        1,
        "Syntaxfehler in der Vorlage",
        append(PATTERNS, "\ndef (:\n"),
        "Syntaxfehler",
    ),
    # 2 — referenced files exist
    Mutation(2, "LICENSE weg", remove("LICENSE"), "missing: LICENSE"),
    Mutation(2, "Vorlage weg", remove(PATTERNS), f"missing: {PATTERNS}"),
    # 3 — no compiled python is tracked
    Mutation(
        3,
        "eine .pyc liegt im Index",
        track("reference/_mutant.pyc", "nicht wirklich Bytecode\n"),
        "kompiliertes Python ist eingecheckt",
    ),
    Mutation(3, "kein Git-Repository", remove(".git"), "kein Git-Repository"),
    # 4 — SKILL.md carries a well-formed frontmatter
    Mutation(4, "SKILL.md weg", remove("SKILL.md"), "SKILL.md: missing"),
    Mutation(
        4,
        "Frontmatter-Zaun beschädigt",
        replace("SKILL.md", "---\nname:", "----\nname:"),
        "frontmatter missing or malformed",
    ),
    Mutation(
        4,
        "falscher Skill-Name",
        replace("SKILL.md", "name: mcp-data-fidelity\n", "name: mcp-fidelity\n"),
        "expected name",
    ),
    Mutation(
        4,
        "Description über der Grenze",
        regex_sub("SKILL.md", r"^description: ", "description: " + "x" * 1100 + " "),
        "description too long",
    ),
    # 5 — the rule count agrees across SKILL.md, both READMEs and patterns.py
    Mutation(
        5,
        "Regel-Überschriften umbenannt",
        regex_sub("SKILL.md", r"^## Regel (\d+)", r"## Rule \1"),
        "keine Überschrift '## Regel N'",
    ),
    Mutation(
        5,
        "Regelnummern nicht fortlaufend",
        regex_sub("SKILL.md", r"^## Regel 3\b", "## Regel 33"),
        "nicht fortlaufend",
    ),
    Mutation(
        5,
        "eine Regel fällt aus einem README",
        regex_sub("README.md", r"^12\. \*\*.*$\n", ""),
        "listet 11 Regeln",
    ),
    Mutation(
        5,
        "README-Abschnitt umformuliert",
        replace("README.de.md", "## Die zwölf Regeln", "## Die Regeln"),
        "Abschnitt '## Die zwölf Regeln' nicht gefunden",
    ),
    Mutation(
        5,
        "Docstring-Wendung in patterns.py weg",
        replace(PATTERNS, "patterns for the twelve", "patterns for twelve"),
        "die Wendung 'patterns for the <word> ... rules' ist",
    ),
    Mutation(
        5,
        "Docstring nennt eine andere Zahl",
        replace(PATTERNS, "patterns for the twelve", "patterns for the nine"),
        "der Docstring sagt 'nine'",
    ),
    Mutation(
        5,
        # Das Zahlwort muss eines sein, das ENGLISH_NUMBERS NICHT kennt — mit
        # Regel 11 und 12 sind 'eleven' und 'twelve' dort eingetragen, und die
        # Mutation griffe sonst ins Leere, ohne dass etwas rot würde.
        "Zahlwort, das die Tabelle nicht kennt",
        replace(PATTERNS, "patterns for the twelve", "patterns for the thirteen"),
        "ENGLISH_NUMBERS",
    ),
    Mutation(
        5,
        "patterns.py deckt eine Regel nicht mehr ab",
        chain(
            regex_sub(PATTERNS, r"[Rr]ules?\s+7-9", "Rules 7 and 8"),
            regex_sub(PATTERNS, r"([Rr])ule 9\b", r"\1ule IX"),
        ),
        "nichts zu Regel [9]",
    ),
    # 6 — every rule has a row in the rule-to-check table
    Mutation(
        6,
        "Tabellenüberschrift umformuliert",
        replace(
            "SKILL.md",
            "### Welche Regel welcher Check ist",
            "### Regel und Check",
        ),
        "nicht gefunden",
    ),
    Mutation(
        6,
        "eine Regel ohne Tabellenzeile",
        regex_sub("SKILL.md", r"^\| 3 — .*\n", ""),
        "keine Tabellenzeile für Regel [3]",
    ),
    Mutation(
        6,
        "eine Regel doppelt in der Tabelle",
        regex_sub("SKILL.md", r"^(\| 2 — .*)$", r"\1\n\1"),
        "mehr als eine Zeile",
    ),
    Mutation(
        6,
        "eine Zeile nennt keinen Check",
        regex_sub(
            "SKILL.md",
            r"^\| 2 — (.*?) \|.*\|$",
            r"| 2 — \1 | dazu gibt es drüben nichts |",
        ),
        "nennt gar keinen Check",
    ),
    # 7 — version badge matches the latest CHANGELOG release
    Mutation(
        7,
        "Badge nicht mitgezogen",
        regex_sub("README.md", r"badge/version-\d+\.\d+\.\d+-", "badge/version-0.9.0-"),
        "das Versions-Badge zeigt",
    ),
    Mutation(
        7,
        "Badge weg",
        regex_sub("README.de.md", r"badge/version-(\d+\.\d+\.\d+)-", r"badge/v\1-"),
        "kein Versions-Badge",
    ),
    Mutation(
        7,
        "Release-Überschriften umformatiert",
        regex_sub("CHANGELOG.md", r"^## \[v?(\d+\.\d+\.\d+)\]", r"## \1"),
        "keine Release-Überschrift",
    ),
    # 8 — the quality-chain table names all five members
    Mutation(
        8,
        "ein Mitglied fällt aus der Tabelle",
        replace("README.md", "mcp-continuous-auditor", "mcp-continuous-nichts"),
        "die Kettentabelle nennt",
    ),
    Mutation(
        8,
        "Abschnittsüberschrift umformuliert",
        replace("README.de.md", "### Die MCP-Qualitätskette", "### Die Qualitätskette"),
        "nicht gefunden",
    ),
    Mutation(
        8,
        "Topic-Seite nicht mehr verlinkt",
        replace(
            "README.md",
            "https://github.com/topics/mcp-quality-chain",
            "https://github.com/malkreide",
        ),
        "Topic-Seite",
    ),
    # 9 — the ruff gate still bites on reference/
    #
    # Die fünf Schalter, mit denen sich `reference/` aus einem der beiden
    # Gates nehmen lässt, ohne dass etwas rot wird. Gemessen: Ein TEILWEISES
    # per-file-ignores blendet das Gate nicht — mit nur `["F401"]` meldet ruff
    # auf der Sonde immer noch I001. Blind wird es erst, wenn jemand pauschal
    # abschaltet, und genau das ist die Bewegung, die dieses Repo schon einmal
    # gemacht hat.
    Mutation(
        9,
        "exclude nimmt reference/ aus beiden Gates",
        replace("ruff.toml", "[lint]\n", 'exclude = ["reference"]\n\n[lint]\n'),
        "Lint-Gate greift auf reference/ nicht mehr",
    ),
    Mutation(
        9,
        "[lint] exclude nimmt reference/ aus dem Lint-Gate",
        replace("ruff.toml", "[lint]\n", '[lint]\nexclude = ["reference/*"]\n'),
        "Lint-Gate greift auf reference/ nicht mehr",
    ),
    Mutation(
        9,
        "[format] exclude nimmt reference/ aus dem Format-Gate",
        append("ruff.toml", '\n[format]\nexclude = ["reference/*"]\n'),
        "Format-Gate greift auf reference/ nicht mehr",
    ),
    Mutation(
        9,
        "select = [] schaltet das Lint-Gate ab",
        regex_sub("ruff.toml", r"^select = \[.*\]$", "select = []"),
        "Lint-Gate greift auf reference/ nicht mehr",
    ),
    Mutation(
        9,
        "per-file-ignores schaltet reference/ pauschal ab",
        regex_sub(
            "ruff.toml", r'^"reference/\*\.py" = \[.*\]$', '"reference/*.py" = ["ALL"]'
        ),
        "Lint-Gate greift auf reference/ nicht mehr",
    ),
    Mutation(9, "reference/ weg", remove("reference"), "reference/ fehlt"),
    Mutation(
        9,
        "eine Sondendatei liegt schon da",
        write("reference/_ruff_gate_probe.py", "# von Hand hierher geraten\n"),
        "liegt schon da",
    ),
    # 10 — ruff check passes on the whole tree
    Mutation(
        10,
        "Lint-Befund in der Vorlage",
        append(PATTERNS, "\nimport os\n"),
        "ruff check hat Befunde",
    ),
    Mutation(
        10,
        "Lint-Befund ausserhalb von reference/",
        append("tools/checks/_core.py", "\nimport os\n"),
        "ruff check hat Befunde",
    ),
    # 11 — ruff format leaves the tree unchanged
    Mutation(
        11,
        "Formatverstoss in der Vorlage",
        append(PATTERNS, "\nmutant   =    1\n"),
        "ruff format würde Dateien ändern",
    ),
    Mutation(
        11,
        "Formatverstoss ausserhalb von reference/",
        append("tools/checks/_core.py", "\nmutant   =    1\n"),
        "ruff format würde Dateien ändern",
    ),
    # 12 — the ruff pin agrees between CI and the pre-commit hook
    Mutation(
        12,
        "Pin in ci.yml gelöst",
        regex_sub(".github/workflows/ci.yml", r"ruff==\d\S*", "ruff"),
        "nennt kein 'ruff==<version>'",
    ),
    Mutation(
        12,
        "rev im Hook weg",
        regex_sub(".pre-commit-config.yaml", r"^\s*rev: v?\d\S*$", "    rev: main"),
        "nennt keine rev für ruff-pre-commit",
    ),
    Mutation(
        12,
        "Pins laufen auseinander",
        regex_sub(".pre-commit-config.yaml", r"^(\s*rev: v?)\d\S*$", r"\g<1>0.0.1"),
        "Ruff-Pins laufen auseinander",
    ),
    Mutation(
        12,
        "ein Hook fällt weg",
        regex_sub(".pre-commit-config.yaml", r"^\s*- id: ruff-format\s*$\n", ""),
        "führt ['ruff-format'] nicht mehr",
    ),
    # 13 — tag and CHANGELOG name the same version
    Mutation(
        13,
        "Tag und CHANGELOG-Spitze laufen auseinander",
        regex_sub("CHANGELOG.md", r"^## \[v?\d+\.\d+\.\d+\]", "## [9.9.9]"),
        "oberstes Release in CHANGELOG.md ist 9.9.9",
    ),
    Mutation(
        13,
        "Release-Überschriften weg",
        regex_sub("CHANGELOG.md", r"^## \[v?(\d+\.\d+\.\d+)\]", r"## \1"),
        "keine Release-Überschrift",
    ),
    # 14 — SKILL.md matches the real catalogue of mcp-audit-skill
    Mutation(
        14,
        "abgelegtes Manifest fehlt",
        remove(MANIFEST),
        "dort liegt keine Datei",
    ),
    Mutation(
        14,
        "Manifest-Format drüben geändert",
        write(MANIFEST, "FID-001\nnicht mehr eine Check-ID\n"),
        "sieht nicht aus wie eine Liste von Check-IDs",
    ),
    Mutation(
        14,
        "Katalog um einen Check gewachsen",
        drop_last_line(MANIFEST),
        "Katalog-Grösse",
    ),
    Mutation(
        14,
        "ein verlinkter Check ist drüben weg",
        regex_sub(MANIFEST, r"^HITL-006\n", ""),
        "Die Tabelle verlinkt",
    ),
    Mutation(
        14,
        "neuer FID-Check, in der Tabelle nicht verlinkt",
        append(MANIFEST, "FID-099\n"),
        "in der Tabelle nicht verlinkt",
    ),
    Mutation(
        14,
        "Satz zum Katalogstand umformuliert",
        replace("SKILL.md", "Checks in zwölf Kategorien", "Checks, zwölf Kategorien"),
        "der Satz zum Katalogstand passt nicht mehr",
    ),
    Mutation(
        14,
        "Tabellenabschnitt weg",
        replace(
            "SKILL.md", "### Welche Regel welcher Check ist", "### Regel und Check"
        ),
        "nicht gefunden",
    ),
    # 15 — die Repo-Description nennt dieselbe Regelzahl wie SKILL.md
    #
    # Sieben Mutationen für sechs Zweige plus den Dateifall. Der Grund für die
    # Dichte ist, dass diese Prüfung als einzige einen Gegenstand hat, den kein
    # Commit ändert: Ein Befund, der auf die falsche Ursache zeigt, schickt
    # jemanden in den Browser, der in eine Datei gehört hätte — oder umgekehrt.
    Mutation(
        15,
        "abgelegte API-Antwort fehlt",
        remove(METADATA),
        "dort liegt keine Datei",
    ),
    Mutation(
        15,
        "kein JSON abgelegt",
        write(METADATA, "<html>rate limit exceeded</html>\n"),
        "ist kein JSON",
    ),
    Mutation(
        15,
        "Antwort ohne 'description'",
        write(METADATA, '{"full_name": "malkreide/mcp-data-fidelity-skill"}\n'),
        "führt kein 'description'",
    ),
    Mutation(
        15,
        "Description leer",
        write(METADATA, '{"description": null}\n'),
        "Repo-Description ist leer",
    ),
    Mutation(
        15,
        "Description umformuliert, Anker weg",
        write(METADATA, '{"description": "Claude Skill for MCP tool authors"}\n'),
        "nennt keine '<Zahlwort> data-fidelity rules'",
    ),
    Mutation(
        15,
        "Zahlwort, das die Prüfung nicht kennt",
        write(
            METADATA,
            '{"description": "Skill with thirteen data-fidelity rules"}\n',
        ),
        "ENGLISH_NUMBERS",
    ),
    Mutation(
        15,
        # Der eigentliche Anlass: Regel 11 und 12 kamen dazu, die Description
        # blieb auf «ten» stehen, und nichts wurde rot.
        "Description nach einer neuen Regel nicht nachgezogen",
        write(METADATA, '{"description": "Skill with ten data-fidelity rules"}\n'),
        "DRIFT — die Repo-Description ist gegenüber SKILL.md veraltet",
    ),
]
