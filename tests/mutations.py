"""Für jede Prüfung: mindestens ein Baum, auf dem sie rot werden MUSS.

Eine Prüfung, die nie rot geworden ist, ist eine Behauptung. Dieses Repository
hat den Beleg dafür in der eigenen Geschichte: `ruff.toml` stand eine Zeit lang
auf `select = []`, beide Ruff-Schritte meldeten «All checks passed!», und
niemand merkte etwas — weil nichts rot wurde. Check 12 ist daraus entstanden,
und diese Datei ist die Verallgemeinerung davon.

Jede Mutation nennt drei Dinge:

  * WELCHE Prüfung sie treffen soll,
  * WAS sie kaputt macht — als Delta auf einer Kopie des echten Baums, nicht
    als handgeschriebene Attrappe (siehe `conftest.py`),
  * WELCHER Teil des Befundes dabei herauskommen muss.

Das Dritte ist nicht Zierde. «Wird rot» genügt nicht: Eine Prüfung, die aus
dem falschen Grund rot wird, schickt den Lesenden zur falschen Datei und
kostet mehr als eine, die schweigt. Zugesichert wird deshalb der Text.

Ausserdem schlägt eine Mutation, deren Suchtext nicht mehr im Baum steht,
laut fehl statt still zu passieren — sonst wäre eine veraltete Mutation ein
Test, der nichts mehr testet. Wieder derselbe Fehler, eine Ebene höher.
"""

from __future__ import annotations

import dataclasses
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path


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
        text = path.read_text(encoding="utf-8")
        mutated, count = re.subn(pattern, repl, text, flags=flags)
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


def track(rel: str, text: str) -> Callable[[Path], None]:
    """Legt eine Datei an UND nimmt sie in den Index auf.

    Für Check 4: `.gitignore` deckt `*.pyc` ab, deshalb `add -f` — genau so
    kam die eingecheckte .pyc seinerzeit zustande.
    """

    def apply(root: Path) -> None:
        (root / rel).write_text(text, encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "-f", rel], check=True)

    return apply


# --- Die Mutationen ----------------------------------------------------

MUTATIONS: list[Mutation] = [
    # 1 — shell reference is syntactically valid
    Mutation(
        1,
        "Vorlage weg",
        remove("reference/probe_template.sh"),
        "Anker weg",
    ),
    Mutation(
        1,
        "Vorlage parst nicht",
        append("reference/probe_template.sh", "\nif then\n"),
        "parst nicht",
    ),
    # 2 — python references are syntactically valid
    Mutation(
        2,
        "reference/ weg",
        remove("reference"),
        "reference/ fehlt",
    ),
    Mutation(
        2,
        "reference/ ohne .py",
        remove_glob("reference/*.py"),
        "enthält keine .py-Datei",
    ),
    Mutation(
        2,
        "Syntaxfehler in einer Vorlage",
        append("reference/retry_backoff.py", "\ndef (:\n"),
        "Syntaxfehler",
    ),
    # 3 — python references actually import
    Mutation(
        3,
        "reference/ weg",
        remove("reference"),
        "reference/ fehlt",
    ),
    Mutation(
        3,
        "Vorlage importiert ein Paket, das es nicht gibt",
        write("reference/_mutant.py", "import kein_solches_paket\n"),
        "requirements-reference.txt",
    ),
    Mutation(
        3,
        "Vorlage wirft beim Import",
        write("reference/_mutant.py", "raise RuntimeError('boom')\n"),
        "RuntimeError",
    ),
    Mutation(
        3,
        "Vorlage ruft beim Import sys.exit",
        write("reference/_mutant.py", "import sys\n\nsys.exit(3)\n"),
        "SystemExit",
    ),
    Mutation(
        3,
        "Vorlage ohne kopierbares Symbol",
        write("reference/_mutant.py", "_privat = 1\n"),
        "keinen Namen bereit",
    ),
    # 4 — no compiled python is tracked
    Mutation(
        4,
        "eine .pyc liegt im Index",
        track("reference/_mutant.pyc", "nicht wirklich Bytecode\n"),
        "kompiliertes Python ist eingecheckt",
    ),
    Mutation(
        4,
        "kein Git-Repository",
        remove(".git"),
        "kein Git-Repository",
    ),
    # 5 — SKILL.md carries a well-formed frontmatter
    Mutation(
        5,
        "SKILL.md weg",
        remove("SKILL.md"),
        "SKILL.md: missing",
    ),
    Mutation(
        5,
        "Frontmatter-Zaun beschädigt",
        replace("SKILL.md", "---\nname:", "----\nname:"),
        "frontmatter missing or malformed",
    ),
    Mutation(
        5,
        "falscher Skill-Name",
        replace("SKILL.md", "name: mcp-data-source-probe\n", "name: mcp-probe\n"),
        "expected name",
    ),
    Mutation(
        5,
        "Description über der Grenze",
        replace(
            "SKILL.md",
            "description: Standardisiertes",
            "description: " + "x" * 1024 + " Standardisiertes",
        ),
        "description too long",
    ),
    # 6 — cross-references resolve to real sections
    Mutation(
        6,
        "Nummerierungsschema der Überschriften geändert",
        regex_sub("SKILL.md", r"^(#{2,4}) (\d+)\.(\d+)", r"\1 \2-\3"),
        "Nummerierungsschema",
    ),
    Mutation(
        6,
        "Verweisnotation geändert",
        regex_sub("SKILL.md", r"\((\d+\.\d+)([a-z]?)\)", r"[\1\2]"),
        "Verweisnotation",
    ),
    Mutation(
        6,
        "Verweis auf einen Abschnitt, den es nicht gibt",
        replace(
            "SKILL.md",
            "\n# MCP Data Source Probe",
            "\nsiehe (9.9)\n\n# MCP Data Source Probe",
        ),
        "non-existent sections",
    ),
    # 7 — referenced files exist
    Mutation(
        7,
        "eine referenzierte Datei fehlt",
        remove("reference/befund_tabelle_template.md"),
        "missing: reference/befund_tabelle_template.md",
    ),
    Mutation(
        7,
        "der Companion-Zeiger fehlt",
        remove("companion/mcp-data-fidelity/README.md"),
        "missing: companion/mcp-data-fidelity/README.md",
    ),
    # 8 — the companion pointer still points somewhere
    Mutation(
        8,
        "companion/ trägt wieder eine SKILL.md",
        write("companion/mcp-data-fidelity/SKILL.md", "---\nname: x\n---\n"),
        "wieder eine SKILL.md",
    ),
    Mutation(
        8,
        "Zeiger-Datei weg",
        remove("companion/mcp-data-fidelity/README.md"),
        "sondern weg",
    ),
    Mutation(
        8,
        "Zeiger nennt das Repository nicht mehr",
        replace(
            "companion/mcp-data-fidelity/README.md",
            "malkreide/mcp-data-fidelity-skill",
            "irgendwo/anders",
        ),
        "nicht das kanonische Repository",
    ),
    # 9 — version badge matches the latest CHANGELOG release
    Mutation(
        9,
        "Badge nicht mitgezogen",
        regex_sub("README.md", r"badge/version-\d+\.\d+\.\d+-", "badge/version-0.9.0-"),
        "das Versions-Badge zeigt",
    ),
    Mutation(
        9,
        "Badge weg",
        regex_sub("README.de.md", r"badge/version-(\d+\.\d+\.\d+)-", r"badge/v\1-"),
        "kein Versions-Badge",
    ),
    Mutation(
        9,
        "Release-Überschriften umformatiert",
        regex_sub("CHANGELOG.md", r"^## \[v?(\d+\.\d+\.\d+)\]", r"## \1"),
        "keine Release-Überschrift",
    ),
    # 10 — the quality-chain table names all five members
    Mutation(
        10,
        "ein Mitglied fällt aus der Tabelle",
        replace("README.md", "mcp-continuous-auditor", "mcp-continuous-nichts"),
        "die Kettentabelle nennt",
    ),
    Mutation(
        10,
        "Abschnittsüberschrift umformuliert",
        replace(
            "README.de.md",
            "### Die MCP-Qualitätskette",
            "### Die Qualitätskette",
        ),
        "nicht gefunden",
    ),
    Mutation(
        10,
        "Topic-Seite nicht mehr verlinkt",
        replace(
            "README.md",
            "https://github.com/topics/mcp-quality-chain",
            "https://github.com/malkreide",
        ),
        "Topic-Seite",
    ),
    # 11 — the core-step count agrees everywhere in SKILL.md
    Mutation(
        11,
        "Schritt-Überschriften umbenannt",
        regex_sub("SKILL.md", r"^## Schritt (\d+):", r"## Phase \1:"),
        "keine Überschrift '## Schritt N:'",
    ),
    Mutation(
        11,
        "ein Schritt ohne [Kern]/[Übergabe]",
        regex_sub("SKILL.md", r"^(## Schritt 2:.*?) \[Kern\]$", r"\1"),
        "trägt keine Markierung",
    ),
    Mutation(
        11,
        "[Kern] hinter einem [Übergabe]",
        regex_sub("SKILL.md", r"^(## Schritt 5:.*?) \[Übergabe\]$", r"\1 [Kern]"),
        "kein zusammenhängender Anfang",
    ),
    Mutation(
        11,
        "Frontmatter-Ziffer weg",
        replace(
            "SKILL.md",
            "Standardisiertes 3-Schritte-Vorgehen",
            "Standardisiertes Vorgehen",
        ),
        "Frontmatter-Wendung 'Standardisiertes",
    ),
    Mutation(
        11,
        "Frontmatter-Ziffer und Markierungen laufen auseinander",
        replace(
            "SKILL.md",
            "Standardisiertes 3-Schritte-Vorgehen",
            "Standardisiertes 4-Schritte-Vorgehen",
        ),
        "das Frontmatter verspricht 4",
    ),
    Mutation(
        11,
        "Zahlwort der Einleitung veraltet",
        replace(
            "SKILL.md",
            "durchläuft die drei Schritte unten",
            "durchläuft die vier Schritte unten",
        ),
        "die Einleitung sagt 'vier'",
    ),
    Mutation(
        11,
        "Zahlwort, das die Tabelle nicht kennt",
        replace(
            "SKILL.md",
            "durchläuft die drei Schritte unten",
            "durchläuft die elf Schritte unten",
        ),
        "GERMAN_NUMBERS",
    ),
    Mutation(
        11,
        "Einleitungssatz umformuliert",
        replace(
            "SKILL.md",
            "durchläuft die drei Schritte unten",
            "geht die drei Schritte unten durch",
        ),
        "'durchläuft die <Zahlwort> Schritte unten'",
    ),
    # 12 — the ruff gate still bites on reference/
    #
    # Die fünf Schalter, mit denen sich `reference/` aus einem der beiden
    # Gates nehmen lässt, ohne dass ein Schritt rot wird. Ein
    # Konfigurationsleser müsste jeden einzeln kennen; die Sonde deckt alle ab,
    # weil sie die Wirkung misst statt der Einstellung.
    Mutation(
        12,
        "exclude nimmt reference/ aus beiden Gates",
        replace("ruff.toml", "[lint]\n", 'exclude = ["reference"]\n\n[lint]\n'),
        "Lint-Gate greift auf reference/ nicht mehr",
    ),
    Mutation(
        12,
        "[lint] exclude nimmt reference/ aus dem Lint-Gate",
        replace("ruff.toml", "[lint]\n", '[lint]\nexclude = ["reference/*"]\n'),
        "Lint-Gate greift auf reference/ nicht mehr",
    ),
    Mutation(
        12,
        "[format] exclude nimmt reference/ aus dem Format-Gate",
        append("ruff.toml", '\n[format]\nexclude = ["reference/*"]\n'),
        "Format-Gate greift auf reference/ nicht mehr",
    ),
    Mutation(
        12,
        "select = [] schaltet das Lint-Gate ab",
        regex_sub("ruff.toml", r"^select = \[.*\]$", "select = []"),
        "Lint-Gate greift auf reference/ nicht mehr",
    ),
    # Gemessen: Ein TEILWEISES per-file-ignores blendet das Gate nicht — mit
    # nur `["F401"]` meldet ruff auf der Sonde immer noch I001, und Check 12
    # bleibt grün, zu Recht. Blind wird das Gate erst, wenn jemand pauschal
    # abschaltet, und genau das ist die Bewegung, die dieses Repo schon einmal
    # gemacht hat.
    Mutation(
        12,
        "per-file-ignores schaltet reference/ pauschal ab",
        append(
            "ruff.toml",
            '\n[lint.per-file-ignores]\n"reference/*.py" = ["ALL"]\n',
        ),
        "Lint-Gate greift auf reference/ nicht mehr",
    ),
    Mutation(
        12,
        "reference/ weg",
        remove("reference"),
        "Anker weg",
    ),
    Mutation(
        12,
        "eine Sondendatei liegt schon da",
        write("reference/_ruff_gate_probe.py", "# von Hand hierher geraten\n"),
        "liegt schon da",
    ),
    # 13 — ruff check passes on the whole tree
    Mutation(
        13,
        "Lint-Befund in einer Vorlage",
        append("reference/retry_backoff.py", "\nimport os\n"),
        "ruff check hat Befunde",
    ),
    Mutation(
        13,
        "Lint-Befund ausserhalb von reference/",
        append("tools/checks/_core.py", "\nimport os\n"),
        "ruff check hat Befunde",
    ),
    # 14 — ruff format leaves the tree unchanged
    Mutation(
        14,
        "Formatverstoss in einer Vorlage",
        append("reference/retry_backoff.py", "\nmutant   =    1\n"),
        "ruff format würde Dateien ändern",
    ),
    Mutation(
        14,
        "Formatverstoss ausserhalb von reference/",
        append("tools/checks/_core.py", "\nmutant   =    1\n"),
        "ruff format würde Dateien ändern",
    ),
    # 15 — the GitHub description names the current core-step count
    Mutation(
        15,
        "Zusage aus der Description gestrichen",
        write("repo.json", '{"description": "Ein Claude Skill."}'),
        "trägt die Wendung",
    ),
    Mutation(
        15,
        "Description und SKILL.md laufen auseinander",
        write("repo.json", '{"description": "a four-step core procedure"}'),
        "verspricht 'four'",
    ),
    Mutation(
        15,
        "Zahlwort, das die Tabelle nicht kennt",
        write("repo.json", '{"description": "an eleven-step core procedure"}'),
        "ENGLISH_NUMBERS",
    ),
    Mutation(
        15,
        "abgelegte API-Antwort fehlt",
        remove("repo.json"),
        "dort liegt keine Datei",
    ),
    # 16 — the ruff pin agrees between CI and the pre-commit hook
    Mutation(
        16,
        "Pin in ci.yml gelöst",
        regex_sub(".github/workflows/ci.yml", r"ruff==\d\S*", "ruff"),
        "nennt kein 'ruff==<version>'",
    ),
    Mutation(
        16,
        "rev im Hook weg",
        regex_sub(".pre-commit-config.yaml", r"^\s*rev: v?\d\S*$", "    rev: main"),
        "nennt keine rev für ruff-pre-commit",
    ),
    Mutation(
        16,
        "Pins laufen auseinander",
        regex_sub(".pre-commit-config.yaml", r"^(\s*rev: v?)\d\S*$", r"\g<1>0.0.1"),
        "Ruff-Pins laufen auseinander",
    ),
    Mutation(
        16,
        "ein Hook fällt weg",
        regex_sub(".pre-commit-config.yaml", r"^\s*- id: ruff-format\s*$", ""),
        "führt ['ruff-format'] nicht mehr",
    ),
    # 17 — the templates hold what the adoption manifest claims
    #
    # Zwei Sorten Mutation, und beide werden gebraucht. Die ersten zwei nehmen
    # der Vorlage eine zugesicherte Eigenschaft — der Fall, für den die Prüfung
    # da ist. Der Rest greift die Prüfung selbst an: jeden Weg, auf dem sie
    # aufhören könnte zu prüfen, ohne rot zu werden. Der zweite Satz ist der
    # wichtigere, denn genau so ist der Ursprungsdefekt durchgekommen — nicht
    # weil ein Gate rot war und ignoriert wurde, sondern weil keines hinsah.
    Mutation(
        17,
        "der Jitter fällt aus der Vorlage",
        replace("reference/retry_backoff.py", "random.random()", "0.5"),
        "jitters — erwartet present",
    ),
    Mutation(
        17,
        "die Vorlage verpackt den Fehler wieder in ein RuntimeError",
        replace(
            "reference/retry_backoff.py",
            "    raise last_error\n",
            '    raise RuntimeError(f"Upstream {url} unreachable: {last_error}")\n',
        ),
        "no_bare_runtime_error — erwartet absent",
    ),
    Mutation(
        17,
        "Manifest weg",
        remove("reference/adoption.toml"),
        "Anker weg",
    ),
    Mutation(
        17,
        "Manifest ohne [[template]]",
        write("reference/adoption.toml", "schema = 1\nunmapped_ok = []\n"),
        "enthält kein [[template]]",
    ),
    Mutation(
        17,
        "Zuordnung zeigt auf eine Datei, die es nicht gibt",
        replace(
            "reference/adoption.toml",
            'file = "reference/retry_backoff.py"\nsymbol = "fetch_with_retry"',
            'file = "reference/retry_fortgezogen.py"\nsymbol = "fetch_with_retry"',
        ),
        "zeigt auf eine Datei, die es nicht gibt",
    ),
    Mutation(
        17,
        "Zuordnung nennt ein Symbol, das es nicht gibt",
        replace(
            "reference/adoption.toml",
            'file = "reference/retry_backoff.py"\nsymbol = "fetch_with_retry"',
            'file = "reference/retry_backoff.py"\nsymbol = "fetch_with_backoff"',
        ),
        "es gibt keine Funktion dieses Namens",
    ),
    Mutation(
        17,
        "Eigenschaft mit einer Art, die die Prüfung nicht kennt",
        replace("reference/adoption.toml", 'kind = "literal"', 'kind = "irgendwie"'),
        "kennt sie nicht",
    ),
    Mutation(
        17,
        "Eigenschaft ohne gültiges expect",
        replace(
            "reference/adoption.toml", 'expect = "absent"', 'expect = "vielleicht"'
        ),
        "Erlaubt sind 'present' und 'absent'",
    ),
    Mutation(
        17,
        "Vorlage ohne deklarierte Eigenschaft",
        regex_sub(
            "reference/adoption.toml",
            r"^\[\[template\.property\]\]$",
            "[[template.merkmal]]",
        ),
        "deklariert keine Eigenschaft",
    ),
    Mutation(
        17,
        "eine neue Vorlage, die niemand zugeordnet hat",
        write("reference/_mutant.py", "WERT = 1\n"),
        "ohne [[template]]-Eintrag",
    ),
    # Eine unlesbare Vorlage muss ein BEFUND sein, kein Absturz. Der
    # Unterschied ist der ganze Punkt von `CheckFailed`: «die Prüfung ist
    # abgestürzt» schickt den Lesenden nach tools/checks, «die Vorlage parst
    # nicht» nach reference/. Diese Mutation ist entstanden, weil genau das
    # hier zuerst falsch war.
    Mutation(
        17,
        "Vorlage parst nicht",
        append("reference/retry_backoff.py", "\ndef (:\n"),
        "Check 2 meldet dasselbe",
    ),
    # 18 — the ruff on PATH is the pinned one
    #
    # Die Prüfung hält eine Datei gegen ein laufendes Programm. Am Baum
    # mutierbar ist deshalb nur die Datei — der Effekt ist derselbe: Pin und
    # laufende Version sagen Verschiedenes. Die Gegenrichtung (dieselbe
    # ci.yml, eine andere ruff auf dem PATH) hängt an der Umgebung und steht
    # als Test in tests/test_suite_integrity.py.
    Mutation(
        18,
        "der Pin nennt eine Version, die nicht läuft",
        regex_sub(
            ".github/workflows/ci.yml",
            r"ruff==\d[^\s\"']*",
            "ruff==0.0.1",
        ),
        "gepinnt ist 0.0.1",
    ),
    Mutation(
        18,
        "der Pin ist ganz weg",
        regex_sub(
            ".github/workflows/ci.yml",
            r"ruff==\d[^\s\"']*",
            "ruff",
        ),
        "Anker weg",
    ),
    Mutation(
        18,
        "ci.yml weg",
        remove(".github/workflows/ci.yml"),
        "ohne die Datei gibt es nichts zu vergleichen",
    ),
    # 19 — both READMEs enumerate the steps SKILL.md defines
    #
    # Der erste Satz nimmt der README einen Schritt, den SKILL.md führt — der
    # Fall, für den die Prüfung da ist. Der zweite greift sie selbst an: jeden
    # Weg, auf dem sie aufhören könnte zu prüfen, ohne rot zu werden.
    Mutation(
        19,
        "die englische README verliert einen Kernschritt",
        regex_sub(
            "README.md",
            r"^- \*\*Step 3 — .*$",
            "- **Nothing to see here.** Placeholder.",
        ),
        "SKILL.md markiert 3 als [Kern]",
    ),
    Mutation(
        19,
        "die deutsche README verliert einen Kernschritt",
        regex_sub(
            "README.de.md",
            r"^- \*\*Schritt 3 — .*$",
            "- **Nichts zu sehen.** Platzhalter.",
        ),
        "SKILL.md markiert 3 als [Kern]",
    ),
    Mutation(
        19,
        "die Sammelzeile lässt den letzten Schritt aus",
        replace(
            "README.md",
            "- **Steps 4\u20136 — Handover.**",
            "- **Steps 4\u20135 — Handover.**",
        ),
        "lässt einen Schritt ganz aus",
    ),
    Mutation(
        19,
        "die Sammelzeile schluckt einen Kernschritt",
        replace(
            "README.de.md",
            "- **Schritte 4\u20136 — Übergabe.**",
            "- **Schritte 3\u20136 — Übergabe.**",
        ),
        "zählt einen Kernschritt zur Übergabe",
    ),
    Mutation(
        19,
        "die Sammelzeile ist ganz weg",
        regex_sub(
            "README.md",
            r"^- \*\*Steps 4\u20136 — .*$",
            "- **Handover.** Inputs for repository creation.",
        ),
        "keine Sammelzeile",
    ),
    Mutation(
        19,
        "der Abschnitt heisst anders",
        replace("README.md", "\n## Features\n", "\n## What it does\n"),
        "Abschnitt '## Features' nicht gefunden",
    ),
    Mutation(
        19,
        "die Aufzählung ist umformuliert",
        regex_sub(
            "README.de.md",
            r"^- \*\*Schritt (\d+) — ",
            r"- **Phase \1 — ",
        ),
        "kein Aufzählungspunkt",
    ),
]
