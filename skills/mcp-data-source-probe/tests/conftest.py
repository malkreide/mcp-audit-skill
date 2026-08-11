"""Fixture-Bäume für die Mutationstests.

Der Fixture-Baum ist eine **Kopie dieses Repositories**, keine handgeschriebene
Attrappe. Das ist der entscheidende Punkt: Ein selbstgebautes Mini-Repo enthält
die Anker per Konstruktion — man schreibt ja hinein, was die Prüfung sucht.
Eine Testsuite auf so einem Baum prüft am Ende nur sich selbst und bliebe
grün, während im echten Baum der Anker längst weg ist. Genau der Fehler, gegen
den die Prüfungen gerichtet sind, eine Ebene höher.

Deshalb: Der Baum kommt aus `git ls-files`, jede Mutation ist ein Delta darauf,
und `test_pristine_fixture_passes_every_offline_check` belegt, dass die Kopie
den echten Baum nicht verloren hat.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.checks.github_meta import JSON_ENV, SUGGESTED_DESCRIPTION

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_SLUG = "malkreide/mcp-data-source-probe-skill"


def _working_tree_files(root: Path) -> list[str]:
    """Alles, was ein Commit von hier aus mitnähme.

    `--others --exclude-standard` neben `--cached`: Auch noch nicht
    hinzugefügte Dateien gehören dazu, sonst prüfte die Suite während der
    Arbeit an einer neuen Datei einen Baum ohne sie.
    """
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
    return [line for line in done.stdout.splitlines() if line]


@pytest.fixture(scope="session")
def pristine_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Eine Kopie des Arbeitsbaums, einmal pro Sitzung gebaut."""
    root = tmp_path_factory.mktemp("pristine") / "repo"
    root.mkdir()
    for name in _working_tree_files(REPO_ROOT):
        source = REPO_ROOT / name
        if not source.is_file():
            continue
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    # Check 4 liest den Git-Index. Ohne Repository hätte er nichts zu lesen und
    # würde in jedem Test aus dem falschen Grund rot.
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)

    # Check 15 liest die abgelegte API-Antwort. Der gute Fall trägt genau die
    # Description, die der Befund von Check 15 vorschlägt — steht sie auf dem
    # echten Repository, muss sie hier durchgehen.
    (root / "repo.json").write_text(
        json.dumps({"description": SUGGESTED_DESCRIPTION}), encoding="utf-8"
    )
    return root


@pytest.fixture
def fixture_repo(
    pristine_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Ein frischer Baum pro Test — Mutationen dürfen ihn ruinieren."""
    root = tmp_path / "repo"
    shutil.copytree(pristine_repo, root)
    monkeypatch.setenv(JSON_ENV, str(root / "repo.json"))
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO_SLUG)
    return root
