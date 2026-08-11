"""Prüfungen an den Vorlagen unter `reference/`.

Das ist der Code, den Leute kopieren. Ein Defekt hier vermehrt sich in jeden
`*-mcp`-Server, der die Vorlage übernimmt — deshalb sind die Ansprüche an
`reference/` höher als an den Rest des Repositories, nicht niedriger.

Jede Prüfung hier hat einen Wächter über ihren eigenen Anker. Der Grund ist
in allen vier Fällen derselbe: Sie hängen an einem Pfad, und alle vier melden
auf einem leeren Ergebnis Erfolg. Verschwindet `reference/`, prüft dann
niemand mehr etwas — und nichts wird rot.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from ._core import CheckFailed, pycache_to_temp, register

SHELL_TEMPLATE = "reference/probe_template.sh"

# Die Dateien, auf die SKILL.md und die READMEs namentlich zeigen. Ein toter
# Verweis in einer Anleitung kostet den Lesenden die Suche und endet oft im
# Schluss, das Repository sei unvollständig.
REFERENCED_FILES = (
    "reference/probe_template.sh",
    "reference/befund_tabelle_template.md",
    "reference/response_envelope.py",
    "reference/retry_backoff.py",
    "companion/mcp-data-fidelity/README.md",
)


def _reference_sources(root: Path) -> list[Path]:
    """Die Vorlagen-Module, oder ein Befund, falls es keine gibt.

    Über das Dateisystem statt über eine gepflegte Liste: Eine dritte Vorlage
    ist damit automatisch abgedeckt. Eine Abdeckungsgrenze, die niemand
    absichtlich gezogen hat, ist die teuerste Sorte.
    """
    directory = root / "reference"
    if not directory.is_dir():
        raise CheckFailed(
            "reference/ fehlt — Anker weg; diese Prüfung würde stillschweigend "
            "nichts mehr prüfen"
        )
    sources = sorted(directory.glob("*.py"))
    if not sources:
        raise CheckFailed(
            "reference/ enthält keine .py-Datei — die Prüfung hätte nichts zu "
            "tun und hätte genau deshalb Erfolg gemeldet"
        )
    return sources


@register(1, "shell reference is syntactically valid")
def shell_syntax(root: Path) -> str:
    # Der Anker ist der Dateiname. Verschwindet die Datei, meldet `bash -n`
    # zwar einen Fehler, aber einen über eine fehlende Datei — hier steht
    # stattdessen, was das für die Prüfung bedeutet.
    path = root / SHELL_TEMPLATE
    if not path.is_file():
        raise CheckFailed(
            f"{SHELL_TEMPLATE} fehlt — Anker weg; diese Prüfung hätte nichts zu parsen"
        )
    done = subprocess.run(
        ["bash", "-n", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise CheckFailed(
            f"{SHELL_TEMPLATE} parst nicht:\n{done.stdout}{done.stderr}".rstrip()
        )
    return f"{SHELL_TEMPLATE} parses"


@register(2, "python references are syntactically valid")
def python_syntax(root: Path) -> str:
    # Kompiliert, ohne Bytecode zu schreiben: `compileall` legt sonst
    # `__pycache__/` neben die Quellen, und genau daraus wurde hier schon
    # einmal eine eingecheckte .pyc (CHANGELOG 1.1.0, Removed).
    sources = _reference_sources(root)
    for path in sources:
        text = path.read_text(encoding="utf-8")
        try:
            compile(text, str(path), "exec")
        except SyntaxError as exc:
            raise CheckFailed(
                f"{path.relative_to(root)}: Syntaxfehler in Zeile "
                f"{exc.lineno} — {exc.msg}"
            ) from exc
    return f"{len(sources)} reference/*.py compile"


@register(3, "python references actually import")
def reference_imports(root: Path) -> str:
    # Kompilieren prüft Syntax. Ob eine Vorlage sich tatsächlich laden lässt
    # — Import vorhanden, Klassenkörper baut durch, Pydantic-Modell validiert
    # sein eigenes Schema — sagt erst der Import. Genau diese Dateien werden
    # kopiert; eine, die nur kompiliert, kostet den Kopierenden die Zeit bis
    # zum ersten Serverstart.
    sources = _reference_sources(root)
    lines = []
    with pycache_to_temp():
        for path in sources:
            name = f"_probe_reference_{path.stem}"
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise CheckFailed(f"{path.name}: kein Importer zuständig")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            try:
                spec.loader.exec_module(module)
            except ModuleNotFoundError as exc:
                raise CheckFailed(
                    f"{path.name}: Import scheitert an fehlendem Paket "
                    f"{exc.name!r}.\n"
                    "  Ist es eine Abhängigkeit der Vorlage, gehört es gepinnt "
                    "nach requirements-reference.txt:\n"
                    "    pip install -r requirements-reference.txt\n"
                    "  Ist es das nicht, importiert die Vorlage etwas, das "
                    "beim Kopieren nirgends existiert."
                ) from exc
            except BaseException as exc:
                # BaseException, nicht Exception: Eine Vorlage, die beim Import
                # `sys.exit` aufruft, ist genauso kaputt wie eine, die wirft —
                # nur würde ein SystemExit sonst den ganzen Lauf mitnehmen.
                if isinstance(exc, KeyboardInterrupt):
                    raise
                raise CheckFailed(
                    f"{path.name}: Import scheitert — {type(exc).__name__}: {exc}"
                ) from exc
            finally:
                sys.modules.pop(name, None)

            public = [n for n in vars(module) if not n.startswith("_")]
            if not public:
                raise CheckFailed(
                    f"{path.name}: importiert, stellt aber keinen Namen bereit "
                    "— eine Vorlage ohne kopierbares Symbol ist keine Vorlage"
                )
            lines.append(f"{path.name}: importiert, {len(public)} öffentliche Namen")

    lines.append(f"{len(sources)} Vorlage(n) unter reference/ importierbar")
    return "\n".join(lines)


@register(7, "referenced files exist")
def referenced_files(root: Path) -> str:
    missing = [name for name in REFERENCED_FILES if not (root / name).is_file()]
    if missing:
        raise CheckFailed("\n".join(f"missing: {name}" for name in missing))
    return "all reference files present"
