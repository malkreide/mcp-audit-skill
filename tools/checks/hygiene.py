"""Hygiene des Arbeitsbaums: referenzierte Dateien, kein getrackter Bytecode."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ._core import CheckFailed, register

# Dateien, auf die SKILL.md, beide READMEs oder die Workflows verweisen. Fehlt
# eine, laufen Links und Anleitungen ins Leere — und die Pruefungen, die sie
# lesen, stuerzen mit einem FileNotFoundError statt mit einem Befund.
REFERENZIERT = [
    "SKILL.md",
    "reference/patterns.py",
    "README.md",
    "README.de.md",
    "LICENSE",
    "CHANGELOG.md",
]

BYTECODE = ("__pycache__/", ".pyc", ".pyo", ".pyd")


@register(10, "every referenced file is present")
def referenced_files_exist(root: Path) -> str:
    """Die Dateien, auf die dieses Repo verweist, gibt es auch.

    Diese Pruefung steht bewusst frueh in der Nummerierung: Sie erklaert die
    Abstuerze der anderen. Fehlt `reference/patterns.py`, meldet Check 3 einen
    FileNotFoundError — richtig, aber die Diagnose steht hier.
    """
    fehlend = [f for f in REFERENZIERT if not (root / f).is_file()]
    if fehlend:
        raise CheckFailed(
            f"referenzierte Datei(en) fehlen: {fehlend}\n"
            "  Entweder ist die Datei weg, oder sie wurde umbenannt und die "
            "Liste in tools/checks/hygiene.py nicht nachgezogen. Beides macht "
            "Links und Anleitungen still falsch."
        )
    return f"alle {len(REFERENZIERT)} referenzierten Dateien vorhanden"


@register(11, "no compiled Python is tracked")
def no_compiled_python_tracked(root: Path) -> str:
    """Kein Bytecode im Index.

    `.gitignore` haelt `__pycache__/` normalerweise draussen. Hineinkommen
    tut es trotzdem: durch ein `git add -f`, durch eine fehlende
    `.gitignore`-Zeile, oder weil eine Datei getrackt war, bevor die Zeile
    dazukam — dann ignoriert git sie nicht mehr.

    GEFRAGT WIRD GIT, NICHT DAS DATEISYSTEM. Ein `find` faende auch den
    Bytecode, den der letzte Testlauf erzeugt hat und den niemand committen
    will; das waere ein Befund ueber den Arbeitsplatz, nicht ueber das
    Repository.

    Kein Repository oder kein git heisst FEHLER, nicht «uebersprungen»: Diese
    Pruefung kann dann nichts sagen, und «nicht gelaufen» als «bestanden» zu
    melden ist die eine Auskunft, die schlimmer ist als keine.
    """
    p = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if p.returncode != 0:
        raise CheckFailed(
            f"`git ls-files` in {root} endete mit {p.returncode} — diese "
            "Pruefung kann den Index nicht lesen und meldet deshalb einen "
            "Befund statt Erfolg.\n"
            f"  {p.stderr.strip()}"
        )
    getrackt = [
        line
        for line in p.stdout.splitlines()
        if line.endswith(BYTECODE[1:]) or "__pycache__/" in line
    ]
    if getrackt:
        raise CheckFailed(
            f"kompiliertes Python ist getrackt: {sorted(getrackt)}\n"
            "  `git rm --cached` darauf, und pruefen, ob .gitignore die Zeile "
            "hat — eine Datei, die vor der Ignore-Zeile getrackt wurde, "
            "ignoriert git nicht mehr."
        )
    return f"kein Bytecode unter {len(p.stdout.splitlines())} getrackten Dateien"
