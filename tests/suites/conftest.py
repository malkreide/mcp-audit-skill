"""Fixture-Baeume fuer die Mutationstests.

DER FIXTURE-BAUM IST EINE KOPIE DIESES REPOSITORIES, keine handgeschriebene
Attrappe. Das ist der entscheidende Punkt, und alle drei Herkunftsrepos haben
ihn gleich begruendet: Ein selbstgebautes Mini-Repo enthaelt die Anker per
Konstruktion — man schreibt ja hinein, was die Pruefung sucht. Eine Testsuite
auf so einem Baum prueft am Ende nur sich selbst und bliebe gruen, waehrend im
echten Baum der Anker laengst weg ist. Genau der Fehler, gegen den die
Pruefungen gerichtet sind, eine Ebene hoeher.

Deshalb: Der Baum kommt aus `git ls-files`, jede Mutation ist ein Delta
darauf, und `test_der_unveraenderte_baum_ist_gruen` belegt, dass die Kopie den
echten Baum nicht verloren hat.

ZWEI EBENEN, weil eine Kopie je Test sonst laenger braucht als der ganze Rest
der Suite: `pristine` baut die Kopie EINMAL pro Sitzung aus dem Arbeitsbaum
(gemessen ~30 ms), `tree` dupliziert sie je Test (~32 ms). Der Originalbaum
wird nie angefasst.

`--others --exclude-standard` neben `--cached`: Auch noch nicht hinzugefuegte
Dateien gehoeren dazu, sonst pruefte die Suite waehrend der Arbeit an einer
neuen Datei einen Baum ohne sie.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _arbeitsbaum_dateien(root: Path) -> list[str]:
    done = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return [zeile for zeile in done.stdout.splitlines() if zeile]


@pytest.fixture(scope="session")
def pristine(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Die Kopie des Arbeitsbaums, einmal je Sitzung."""
    ziel = tmp_path_factory.mktemp("pristine") / "repo"
    ziel.mkdir()
    dateien = _arbeitsbaum_dateien(REPO_ROOT)
    assert dateien, (
        "git ls-files liefert nichts — dann waere der Fixture-Baum leer und "
        "jede Pruefung darauf gruen, ohne etwas gesehen zu haben."
    )
    for name in dateien:
        quelle = REPO_ROOT / name
        if not quelle.is_file():
            continue
        neu = ziel / name
        neu.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle, neu)
    return ziel


@pytest.fixture
def tree(pristine: Path, tmp_path: Path) -> Path:
    """Eine Wegwerf-Kopie je Test."""
    ziel = tmp_path / "repo"
    shutil.copytree(pristine, ziel)
    return ziel
