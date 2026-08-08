"""Fixtures fuer die Pruefungen unter tools/checks/.

WARUM DER ECHTE BAUM UND KEINE SYNTHETISCHEN FIXTURES: Die Pruefungen handeln
von DIESEN Dateien — von den Ankern in SKILL.md, den Ueberschriften in beiden
READMEs, dem Docstring in reference/patterns.py. Eine minimale Kunstwelt
danebenzustellen hiesse, eine zweite Sammlung Behauptungen zu pflegen, die
genauso auseinanderlaufen kann wie die erste. Genau davor warnen die
Pruefungen.

Jeder Test bekommt deshalb eine KOPIE des echten Baums in einem tmp_path und
mutiert darin. Der Originalbaum wird nie angefasst.

KEIN UNTERPROZESS MEHR. Solange die Pruefungen `sys.exit` riefen, war ein
Unterprozess der einzige Weg, sie zu beobachten, und zusicherbar war nur eine
Teilzeichenkette der vereinigten Ausgabe. Seit sie `(root) -> str` sind und
`CheckFailed` werfen, ruft der Test die Funktion direkt und sichert den
Meldungstext zu.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil

import pytest

from tools.checks import all_checks
from tools.checks.github_meta import JSON_ENV

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Die echte Description des Repos. Steht hier, weil `github_meta` sie aus der
# Umgebung liest statt sie selbst zu holen — der API-Aufruf bleibt im
# Workflow, damit diese Tests ohne Netz laufen.
GOOD_DESCRIPTION = (
    "Claude Skill with fourteen transport-hardening rules for MCP servers, "
    "across both spec baselines — scope follows where the line sits in the "
    "code, not the transport it runs"
)

# Pruefungen, deren Ergebnis nicht allein am Baum haengt, sondern an dem, was
# auf dem PATH liegt. Check 8 vergleicht den Pin mit der laufenden ruff — ohne
# untergeschobene ruff haenge der Test davon ab, welche Version die Maschine
# zufaellig installiert hat, und das waere kein Test, sondern eine
# Wetterbeobachtung. Diese bekommen einen Shim (siehe `ruff_shim`).
UMGEBUNGSABHAENGIG = {"ruff_version_matches_pin"}

CHECKS_BY_NAME = {c.run.__name__: c for c in all_checks()}


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
def ruff_shim(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """Legt eine gefaelschte `ruff` an und setzt den PATH auf sie.

    Damit werden die Faelle pruefbar, die als Inline-Shell unpruefbar waren:
    eine ruff mit der falschen Version, eine mit geaenderter Ausgabeform, eine,
    die abstuerzt — und gar keine.
    """

    def _shim(rumpf: str | None) -> pathlib.Path:
        d = tmp_path / "shim"
        d.mkdir(exist_ok=True)
        if rumpf is not None:
            f = d / "ruff"
            f.write_text(f"#!/bin/sh\n{rumpf}\n", encoding="utf-8")
            f.chmod(0o755)
        # Nur das Shim-Verzeichnis: eine echte ruff weiter hinten im PATH
        # machte den Fall «gar keine ruff» unpruefbar.
        monkeypatch.setenv("PATH", str(d))
        return d

    return _shim


@pytest.fixture
def repo_json(monkeypatch: pytest.MonkeyPatch):
    """Setzt die API-Antwort, die `github_meta` aus der Umgebung liest."""

    def _set(description: str | None = GOOD_DESCRIPTION) -> None:
        monkeypatch.setenv(JSON_ENV, json.dumps({"description": description}))
        monkeypatch.setenv(
            "GITHUB_REPOSITORY", "malkreide/mcp-transport-hardening-skill"
        )

    return _set


def gepinnte_version(tree: pathlib.Path) -> str:
    """Der ruff-Pin aus der ci.yml des gegebenen Baums."""
    m = re.search(
        r"""ruff==([0-9][^\s"']*)""",
        (tree / ".github/workflows/ci.yml").read_text(encoding="utf-8"),
    )
    assert m, "ci.yml nennt keinen ruff-Pin — dann testet hier nichts mehr"
    return m.group(1)
