"""Die Vorlagen dieses Skills — Shell, Import, Verweise.

DREI PRUEFUNGEN, DIE DIE ANDEREN SUITEN NICHT HABEN, und der Grund ist
derselbe fuer alle drei: Die Vorlagen dieses Skills sind GESCHLOSSEN. Sie
laufen, und deshalb laesst sich mehr an ihnen messen als «kompiliert».
`mcp-data-fidelity` und `mcp-transport-hardening` fuehren absichtlich offene
Vorlagen, die Namen aus der Zielumgebung nennen — dort waere ein Import ein
Befund ueber die falsche Sache.

Die Syntax-Haelfte (`compile()`) ist dagegen generisch und laeuft als
`audit/10` einmal ueber alle drei Vorlagen-Verzeichnisse. Was hier steht, ist
die Haelfte, die daran ANSCHLIESST.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from tools.gates import hygiene as gates
from tools.harness import CheckFailed, pycache_to_temp, register

from ._suite import SUITE
from .skill_doc import BASE

SHELL_TEMPLATE = f"{BASE}/reference/probe_template.sh"
REFERENCE_DIR = f"{BASE}/reference"

#: Die Dateien, auf die `SKILL.md` und die READMEs namentlich zeigen. Ein
#: toter Verweis in einer Anleitung kostet den Lesenden die Suche und endet
#: oft im Schluss, das Repository sei unvollstaendig.
#:
#: `LICENSE` steht nicht darin — sie liegt jetzt einmal in der Repo-Wurzel und
#: gehoert dem Repository, nicht der Suite.
REFERENCED_FILES = (
    f"{BASE}/SKILL.md",
    f"{BASE}/README.md",
    f"{BASE}/README.de.md",
    f"{BASE}/CHANGELOG.md",
    f"{BASE}/reference/probe_template.sh",
    f"{BASE}/reference/befund_tabelle_template.md",
    f"{BASE}/reference/response_envelope.py",
    f"{BASE}/reference/retry_backoff.py",
    f"{BASE}/reference/adoption.toml",
)


def reference_sources(root: Path) -> list[Path]:
    verzeichnis = root / REFERENCE_DIR
    if not verzeichnis.is_dir():
        raise CheckFailed(
            f"{REFERENCE_DIR} fehlt — Anker weg; diese Pruefung wuerde "
            "stillschweigend nichts mehr pruefen."
        )
    quellen = sorted(verzeichnis.glob("*.py"))
    if not quellen:
        raise CheckFailed(
            f"{REFERENCE_DIR} enthaelt keine .py-Datei — die Pruefung haette "
            "nichts zu tun und haette genau deshalb Erfolg gemeldet."
        )
    return quellen


@register(1, "shell reference is syntactically valid", suite=SUITE)
def shell_syntax(root: Path) -> str:
    """SKILL-EIGEN: Nur dieser Skill liefert eine Shell-Vorlage aus.

    Der Anker ist der Dateiname. Verschwindet die Datei, meldet `bash -n` zwar
    einen Fehler, aber einen ueber eine fehlende Datei — hier steht
    stattdessen, was das fuer die Pruefung bedeutet.
    """
    pfad = root / SHELL_TEMPLATE
    if not pfad.is_file():
        raise CheckFailed(
            f"{SHELL_TEMPLATE} fehlt — Anker weg; diese Pruefung haette nichts "
            "zu parsen."
        )
    done = subprocess.run(
        ["bash", "-n", str(pfad)],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise CheckFailed(
            f"{SHELL_TEMPLATE} parst nicht:\n{done.stdout}{done.stderr}".rstrip()
        )
    return f"{SHELL_TEMPLATE} parst"


@register(3, "python references actually import", suite=SUITE)
def reference_imports(root: Path) -> str:
    """Kompilieren prueft Syntax; ob eine Vorlage sich LADEN laesst, sagt erst
    der Import.

    Import vorhanden, Klassenkoerper baut durch, das Pydantic-Modell validiert
    sein eigenes Schema. Genau diese Dateien werden kopiert; eine, die nur
    kompiliert, kostet den Kopierenden die Zeit bis zum ersten Serverstart.

    HAENGT AN `requirements-reference.txt`, und das ist der Grund, warum diese
    Pruefung nicht generisch werden kann: Sie braucht die Laufzeit-Pakete der
    Vorlagen (`pydantic`, `httpx`) im Interpreter. FAIL statt skip, wenn sie
    fehlen — «nicht gelaufen» als «bestanden» zu melden ist die eine Auskunft,
    die schlimmer ist als keine.
    """
    quellen = reference_sources(root)
    zeilen = []
    with pycache_to_temp():
        for pfad in quellen:
            name = f"_probe_reference_{pfad.stem}"
            spec = importlib.util.spec_from_file_location(name, pfad)
            if spec is None or spec.loader is None:
                raise CheckFailed(f"{pfad.name}: kein Importer zustaendig")
            modul = importlib.util.module_from_spec(spec)
            sys.modules[name] = modul
            try:
                spec.loader.exec_module(modul)
            except ModuleNotFoundError as exc:
                raise CheckFailed(
                    f"{pfad.name}: Import scheitert an fehlendem Paket "
                    f"{exc.name!r}.\n"
                    "  Ist es eine Abhaengigkeit der Vorlage, gehoert es "
                    "gepinnt nach requirements-reference.txt:\n"
                    "    pip install -r requirements-reference.txt\n"
                    "  Ist es das nicht, importiert die Vorlage etwas, das "
                    "beim Kopieren nirgends existiert."
                ) from exc
            except BaseException as exc:
                # BaseException, nicht Exception: Eine Vorlage, die beim Import
                # `sys.exit` aufruft, ist genauso kaputt wie eine, die wirft —
                # nur wuerde ein SystemExit sonst den ganzen Lauf mitnehmen.
                if isinstance(exc, KeyboardInterrupt):
                    raise
                raise CheckFailed(
                    f"{pfad.name}: Import scheitert — {type(exc).__name__}: {exc}"
                ) from exc
            finally:
                sys.modules.pop(name, None)

            oeffentlich = [n for n in vars(modul) if not n.startswith("_")]
            if not oeffentlich:
                raise CheckFailed(
                    f"{pfad.name}: importiert, stellt aber keinen Namen bereit "
                    "— eine Vorlage ohne kopierbares Symbol ist keine Vorlage."
                )
            zeilen.append(
                f"{pfad.name}: importiert, {len(oeffentlich)} oeffentliche Namen"
            )

    zeilen.append(f"{len(quellen)} Vorlage(n) unter {REFERENCE_DIR} importierbar")
    return "\n".join(zeilen)


@register(7, "referenced files exist", suite=SUITE)
def referenced_files_exist(root: Path) -> str:
    return gates.referenced_files_exist(root, files=REFERENCED_FILES)
