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

import os
import subprocess
from pathlib import Path

from tools.gates import hygiene as gates
from tools.gates import references as ref_gates
from tools.harness import CheckFailed, register

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


def brauchbare_bash() -> str:
    """Eine bash, die auch wirklich laeuft — nicht bloss eine, die es gibt.

    BEIM EINZUG DAZUGEKOMMEN, und der Anlass ist gemessen: Auf
    `windows-latest` liegt in `System32` eine `bash.exe`, die nur der Starter
    fuer das Windows Subsystem for Linux ist. Ohne installierte Distribution
    antwortet sie mit «Windows Subsystem for Linux has no installed
    distributions» und einem Exit-Code ungleich null — und die
    Herkunftsfassung las das als «die Vorlage parst nicht».

    Ein Befund, der auf die falsche Datei zeigt: Jemand haette die Vorlage
    gesucht und dort nichts gefunden. Das Herkunftsrepo hat den Fall nie
    gesehen, weil seine CI nur Linux fuhr; die Matrix dieses Repos enthaelt
    `windows-latest`, und dort ist er beim ersten Lauf aufgeschlagen.

    Deshalb wird JEDE `bash` auf dem PATH kurz angesprochen (`bash -c ""`) und
    die erste genommen, die antwortet. Findet sich keine, ist das ein Befund
    ueber die UMGEBUNG — mit eigenem Text, damit er nicht mit einem ueber die
    Vorlage verwechselt wird.
    """
    gesehen: list[str] = []
    for verzeichnis in os.environ.get("PATH", "").split(os.pathsep):
        if not verzeichnis:
            continue
        for name in ("bash", "bash.exe"):
            kandidat = Path(verzeichnis) / name
            if not kandidat.is_file() or str(kandidat) in gesehen:
                continue
            gesehen.append(str(kandidat))
            probe = subprocess.run(
                [str(kandidat), "-c", ""],
                capture_output=True,
                text=True,
                check=False,
            )
            if probe.returncode == 0:
                return str(kandidat)

    raise CheckFailed(
        "Keine benutzbare bash auf dem PATH — diese Pruefung kann nicht "
        "laufen.\n"
        f"  angesprochen wurden: {gesehen or '— keine gefunden'}\n"
        "  FAIL statt skip: «nicht gelaufen» als «bestanden» zu melden ist die "
        "eine Auskunft, die schlimmer ist als keine. Und ausdruecklich KEIN "
        "Befund ueber die Vorlage — die ist hier gar nicht angesehen worden."
    )


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
        [brauchbare_bash(), "-n", str(pfad)],
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

    DIE MECHANIK STEHT SEIT PHASE 5 IM GATE. Sie hatte bis dahin genau einen
    Gegenstand; mit `transport/12` hat sie einen zweiten, und zwar aus einem
    ANDEREN Grund — dort haelt derselbe Import die Vorlage gegen die
    SDK-Oberflaeche. Zwei Gruende, ein Mechanismus.
    """
    return ref_gates.python_imports(
        root, source_dirs=(REFERENCE_DIR,), praefix="_probe_reference_"
    )


@register(7, "referenced files exist", suite=SUITE)
def referenced_files_exist(root: Path) -> str:
    return gates.referenced_files_exist(root, files=REFERENCED_FILES)
