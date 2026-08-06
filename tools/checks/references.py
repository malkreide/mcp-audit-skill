"""Prüfungen an den Vorlagen unter `reference/` und den genannten Dateien.

`reference/patterns.py` ist der Code, den Leute kopieren. Ein Defekt darin
vermehrt sich in jeden Server, der die Vorlage übernimmt — die Ansprüche hier
sind deshalb höher als an den Rest des Repositories, nicht niedriger.

**Warum es hier keinen Import-Smoke-Test gibt**, anders als im
Schwester-Repo: Die Vorlagen dieses Repos sind absichtlich offen. Sie nennen
Namen aus der Zielumgebung (`log`, Client-Objekte, Settings), die es hier
nicht gibt; `ruff.toml` unterdrückt dafür gezielt `F821` unter
`reference/*.py`. Ein Import würde also an genau der Eigenschaft scheitern,
die den Zweck ausmacht. Wer das später ändert — geschlossene Vorlagen, die
sich laden lassen —, sollte die Prüfung nachziehen; bis dahin ist ihr Fehlen
Absicht und keine Lücke.
"""

from __future__ import annotations

from pathlib import Path

from ._core import CheckFailed, register

# Die Dateien, auf die SKILL.md und die READMEs namentlich zeigen. Ein toter
# Verweis in einer Anleitung kostet den Lesenden die Suche und endet oft im
# Schluss, das Repository sei unvollständig.
REFERENCED_FILES = (
    "SKILL.md",
    "reference/patterns.py",
    "README.md",
    "README.de.md",
    "LICENSE",
    "CHANGELOG.md",
)


def reference_sources(root: Path) -> list[Path]:
    """Die Vorlagen-Module, oder ein Befund, falls es keine gibt.

    Der Anker ist der Verzeichnisname. Verschwindet `reference/`, hätten die
    Prüfungen 1, 9, 10 und 11 nichts mehr zu tun — und alle vier melden auf
    einem leeren Ergebnis Erfolg. Genau deshalb steht der Wächter *in* der
    Prüfung und nicht als eigener Schritt daneben: So kann er nicht
    unabhängig von dem verschwinden, was er bewacht.
    """
    directory = root / "reference"
    if not directory.is_dir():
        raise CheckFailed(
            "reference/ fehlt — Verzeichnis umbenannt oder gelöscht. Ohne es "
            "prüft diese Prüfung stillschweigend nichts mehr."
        )
    sources = sorted(directory.glob("*.py"))
    if not sources:
        raise CheckFailed(
            "reference/ enthält keine .py-Datei — die Prüfung hätte nichts zu "
            "tun und hätte genau deshalb Erfolg gemeldet"
        )
    return sources


@register(1, "python references are syntactically valid")
def python_syntax(root: Path) -> str:
    # Kompiliert, ohne Bytecode zu schreiben: `compileall` legt sonst
    # `__pycache__/` neben die Quellen, und Prüfung 3 mahnt eingechecktes
    # Bytecode zu Recht an. Eine Prüfung, die die nächste rot macht, ist kein
    # Befund, sondern ein Eigentor.
    sources = reference_sources(root)
    for path in sources:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            raise CheckFailed(
                f"{path.name}: Syntaxfehler in Zeile {exc.lineno} — {exc.msg}"
            ) from exc
    return f"{len(sources)} reference/*.py compile"


@register(2, "referenced files exist")
def referenced_files(root: Path) -> str:
    missing = [name for name in REFERENCED_FILES if not (root / name).is_file()]
    if missing:
        raise CheckFailed("\n".join(f"missing: {name}" for name in missing))
    return f"all {len(REFERENCED_FILES)} referenced files present"
