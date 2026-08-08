"""Fixtures fuer die Checks unter tools/checks/.

WARUM DER ECHTE BAUM UND KEINE SYNTHETISCHEN FIXTURES: Die Checks handeln von
DIESEN Dateien — von den Ankern in SKILL.md, den Ueberschriften in beiden
READMEs, dem Docstring in reference/patterns.py. Eine minimale Kunstwelt
danebenzustellen hiesse, eine zweite Sammlung Behauptungen zu pflegen, die
genauso auseinanderlaufen kann wie die erste. Genau davor warnen die Checks.

Jeder Test bekommt deshalb eine KOPIE des echten Baums in einem tmp_path und
mutiert darin. Der Originalbaum wird nie angefasst.

WARUM SUBPROCESS UND KEIN IMPORT: Der Vertrag dieser Skripte gegenueber der CI
ist «Exit-Code plus Meldung», nicht «Rueckgabewert». Genau den pruefen die
Tests. Ein Import-und-Aufruf haette die Skripte umbauen muessen, damit sie
testbar werden — und die Umstellung sollte nichts am Verhalten aendern.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

SCRIPTS = {
    "skill_frontmatter": "tools/checks/skill_frontmatter.py",
    "rule_sections": "tools/checks/rule_sections.py",
    "rule_count": "tools/checks/rule_count.py",
    "chain_table": "tools/checks/chain_table.py",
    "reference_open_names": "tools/checks/reference_open_names.py",
    "version_badge": "tools/checks/version_badge.py",
    "repo_description": "tools/checks/repo_description.py",
    "ruff_pin_sync": "tools/checks/ruff_pin_sync.py",
    "ruff_version": "tools/checks/ruff_version.py",
}

# Checks, deren Ergebnis nicht allein am Baum haengt, sondern an dem, was auf
# dem PATH liegt. `ruff_version.py` vergleicht den Pin mit der laufenden ruff —
# ohne untergeschobene ruff haenge der Test davon ab, welche Version die
# Maschine zufaellig installiert hat, und das waere kein Test, sondern eine
# Wetterbeobachtung. Diese Checks bekommen einen Shim (siehe `ruff_shim`).
UMGEBUNGSABHAENGIG = {"ruff_version"}

# Die echte Description des Repos. Steht hier, weil `repo_description.py` sie
# als Datei bekommt statt sie selbst zu holen — der API-Aufruf bleibt im
# Workflow, damit diese Tests ohne Netz laufen.
GOOD_DESCRIPTION = (
    "Claude Skill with fourteen transport-hardening rules for MCP servers, "
    "across both spec baselines — scope follows where the line sits in the "
    "code, not the transport it runs"
)


@pytest.fixture
def tree(tmp_path: pathlib.Path) -> pathlib.Path:
    """Eine Wegwerf-Kopie des echten Repos."""
    dst = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT,
        dst,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache"),
    )
    return dst


@pytest.fixture
def run_check(tmp_path: pathlib.Path):
    """Faehrt einen Check gegen einen Baum und liefert das CompletedProcess."""

    def _run(
        name: str,
        tree: pathlib.Path,
        description: str = GOOD_DESCRIPTION,
        pfad: str | None = None,
    ):
        cmd = [sys.executable, SCRIPTS[name]]
        if name == "repo_description":
            repo_json = tmp_path / "repo.json"
            repo_json.write_text(
                json.dumps({"description": description}), encoding="utf-8"
            )
            cmd.append(str(repo_json))
        return subprocess.run(
            cmd,
            cwd=tree,
            env={
                **os.environ,
                "PYTHONUTF8": "1",
                "GITHUB_REPOSITORY": "malkreide/mcp-transport-hardening-skill",
                **({"PATH": pfad} if pfad is not None else {}),
            },
            capture_output=True,
            text=True,
        )

    return _run


@pytest.fixture
def ruff_shim(tmp_path: pathlib.Path):
    """Legt eine gefaelschte `ruff` an und liefert einen PATH, der sie zeigt.

    Damit werden die Faelle pruefbar, die als Inline-Shell unpruefbar waren:
    eine ruff mit der falschen Version, eine mit geaenderter Ausgabeform, eine,
    die abstuerzt — und gar keine.
    """

    def _shim(rumpf: str | None) -> str:
        d = tmp_path / "shim"
        d.mkdir(exist_ok=True)
        if rumpf is not None:
            f = d / "ruff"
            f.write_text(f"#!/bin/sh\n{rumpf}\n", encoding="utf-8")
            f.chmod(0o755)
        # Nur das Shim-Verzeichnis: eine echte ruff weiter hinten im PATH
        # wuerde den Fall «gar keine ruff» unpruefbar machen.
        return str(d)

    return _shim


def gepinnte_version(tree: pathlib.Path) -> str:
    """Der ruff-Pin aus der ci.yml des gegebenen Baums."""
    m = re.search(
        r"""ruff==([0-9][^\s"']*)""",
        (tree / ".github/workflows/ci.yml").read_text(encoding="utf-8"),
    )
    assert m, "ci.yml nennt keinen ruff-Pin — dann testet hier nichts mehr"
    return m.group(1)
