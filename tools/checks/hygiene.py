"""Prüfungen am Zustand des Repositories selbst.

Beides sind Wächter über Vorfälle, die es hier schon gegeben hat, nicht über
gedachte.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ._core import CheckFailed, register

COMPILED = re.compile(r"(^|/)__pycache__/|\.py[cod]$")

POINTER = "companion/mcp-data-fidelity/README.md"
CANONICAL_REPO = "malkreide/mcp-data-fidelity-skill"


@register(4, "no compiled python is tracked")
def no_compiled_python(root: Path) -> str:
    # Eine .pyc war hier schon einmal eingecheckt (CHANGELOG 1.1.0, Removed).
    # Der Vorfall stand dokumentiert, ein Wächter dagegen fehlte — das
    # Schwester-Repo mcp-transport-hardening-skill hatte ihn, dieses nicht.
    done = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise CheckFailed(
            f"{root} ist kein Git-Repository — diese Prüfung liest den Index "
            "und hätte hier nichts zu lesen:\n" + done.stderr.strip()
        )
    tracked = [line for line in done.stdout.splitlines() if COMPILED.search(line)]
    if tracked:
        raise CheckFailed(
            "kompiliertes Python ist eingecheckt (siehe .gitignore):\n"
            + "\n".join(tracked)
        )
    return "kein kompiliertes Python eingecheckt"


@register(8, "the companion pointer still points somewhere")
def companion_pointer(root: Path) -> str:
    # Der Skill ist in ein eigenes Repository gezogen. Trägt dieses
    # Verzeichnis je wieder eine SKILL.md, driften die zwei Kopien — genau
    # die Lage, die der Umzug beenden sollte.
    if (root / "companion/mcp-data-fidelity/SKILL.md").exists():
        raise CheckFailed(
            "companion/ trägt wieder eine SKILL.md — der Skill ist in sein "
            "eigenes Repository gezogen, zwei Kopien driften"
        )
    # Der Anker ist der Dateipfad. Fehlt die Datei, meldete eine
    # Inhaltssuche dasselbe wie ein falscher Inhalt — der Befund zeigte auf
    # die falsche Ursache, und der Zeiger wäre ganz weg statt nur falsch.
    pointer = root / POINTER
    if not pointer.is_file():
        raise CheckFailed(
            f"{POINTER} fehlt — der Zeiger ist nicht falsch, sondern weg; "
            "diese Prüfung hätte nichts zu lesen"
        )
    if CANONICAL_REPO not in pointer.read_text(encoding="utf-8"):
        raise CheckFailed(
            f"{POINTER} nennt nicht das kanonische Repository "
            f"({CANONICAL_REPO}) — ein Zeiger, der nicht zeigt, ist ein toter "
            "Ordner mit Text darin"
        )
    return "pointer names the canonical repository"
