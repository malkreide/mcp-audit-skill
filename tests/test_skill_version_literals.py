# -*- coding: utf-8 -*-
"""Hält die `--skill-version`-Literale an der letzten Release-Version.

Anders als die Katalog-Zahlen hängt dieser Wert nicht an `checks/`,
sondern am CHANGELOG: Quelle ist die oberste Release-Überschrift, also
der erste `## [vX.Y.Z]`-Block unterhalb von `## [Unreleased]`.

Der Wert ist unbewacht besonders anfällig, weil er nirgends im Code
vorkommt: `audit_init.py` hat keinen Default ausser `"unspecified"`, die
Doku-Beispiele sind die einzige Quelle. Wer den Befehl kopiert, schreibt
den dort stehenden String in seine `audit-meta.json` — und die ist der
Audit-Trail, an dem später hängt, mit welcher Skill-Version ein Befund
entstanden ist. Ein falscher Wert fällt nie auf und lässt sich später
nicht mehr rekonstruieren.

Beim v1.1.0-Release wurden zwei von drei Fundorten nachgezogen; der
dritte (die Usage-Zeile in `tools/audit_init.py`) blieb auf `1.0.0`
stehen. Genau deshalb zählt dieser Test alle Fundorte, statt eine Liste
bekannter Dateien zu pflegen.

Ausgenommen sind zwei Orte, an denen ein Versions-Literal legitim **nicht**
aktuell ist:

- `CHANGELOG.md` — dort ist jede Zahl historisch und soll es bleiben.
- `tests/` — Fixtures und Parametrisierungen brauchen frei wählbare
  Versionen.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# `## [v1.1.0] — 2026-07-30 — …` (Unreleased trägt keine Versionsnummer
# und wird von diesem Muster deshalb von selbst übersprungen)
RELEASE_HEADING = re.compile(r"^## \[v?(?P<version>\d+\.\d+\.\d+)\]", re.MULTILINE)

# `--skill-version "1.1.0"` und `--skill-version 1.1.0`
VERSION_LITERAL = re.compile(r'--skill-version\s+"?(?P<version>\d+\.\d+\.\d+)"?')

# Verzeichnisse, die gar nicht erst durchsucht werden.
SKIP_DIRS = {".git", "tests", "audits", "node_modules", "__pycache__"}
# Dateien, in denen ein veraltetes Literal richtig ist.
SKIP_FILES = {CHANGELOG}


def _released_version() -> str:
    m = RELEASE_HEADING.search(CHANGELOG.read_text(encoding="utf-8"))
    assert m, "Keine Release-Überschrift `## [vX.Y.Z]` in CHANGELOG.md gefunden"
    return m.group("version")


def _scan_files():
    for path in REPO_ROOT.rglob("*"):
        if path.suffix not in {".md", ".py"} or not path.is_file():
            continue
        if path in SKIP_FILES:
            continue
        if SKIP_DIRS & set(path.relative_to(REPO_ROOT).parts):
            continue
        yield path


@pytest.fixture(scope="module")
def occurrences():
    found = []
    for path in _scan_files():
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in VERSION_LITERAL.finditer(line):
                found.append((path.relative_to(REPO_ROOT), lineno, m.group("version")))
    return found


class TestSkillVersionLiterals:
    def test_changelog_has_release_version(self):
        # Scheitert, wenn die oberste Release-Überschrift verschwindet oder
        # ihr Format sich ändert — sonst hinge der Test an einer leeren Quelle.
        assert re.fullmatch(r"\d+\.\d+\.\d+", _released_version())

    def test_literals_exist(self, occurrences):
        # Ohne diese Bedingung liefe der Test grün, wenn alle Beispiele
        # verschwinden oder anders formatiert werden.
        assert occurrences, (
            "Kein `--skill-version <version>` in der Doku gefunden — "
            "Anker verschwunden oder Format geändert"
        )

    def test_all_literals_match_released_version(self, occurrences):
        expected = _released_version()
        stale = [(str(p), n, v) for p, n, v in occurrences if v != expected]
        assert not stale, (
            f"Veraltete `--skill-version`-Literale (Release ist {expected}): "
            + ", ".join(f"{p}:{n} → {v}" for p, n, v in stale)
        )
