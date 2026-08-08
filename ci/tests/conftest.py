"""Fixtures fuer die Checks unter ci/checks/.

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
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

SCRIPTS = {
    "skill_frontmatter": "ci/checks/skill_frontmatter.py",
    "rule_sections": "ci/checks/rule_sections.py",
    "rule_count": "ci/checks/rule_count.py",
    "chain_table": "ci/checks/chain_table.py",
    "version_badge": "ci/checks/version_badge.py",
    "repo_description": "ci/checks/repo_description.py",
}

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

    def _run(name: str, tree: pathlib.Path, description: str = GOOD_DESCRIPTION):
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
            },
            capture_output=True,
            text=True,
        )

    return _run
