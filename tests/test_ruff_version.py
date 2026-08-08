"""Tests für den Ruff-Version-Guard.

Der Pin-Guard nebenan vergleicht zwei **Texte**: `lint.yml` und
`.pre-commit-config.yaml`. Dass die ruff, die anschliessend `ruff check .` und
`ruff format --check .` fährt, diese Version trägt, hat er nie gemessen — und
meldete trotzdem «beide Stellen stimmen überein». Genau diese Lücke schliesst
`check_ruff_version.py`, und hier wird sie nachgeprüft.

Geprüft wird die **reine** Seite: `compare()` bekommt den Pin, die rohe
Ausgabe von `ruff --version` und deren Exit-Code als Werte. Kein PATH, kein
Unterprozess, keine Mocks. Damit sind vier Fälle prüfbar, die als
Workflow-Schritt nur im CI zu beobachten gewesen wären.

Die Fälle mit **ANKER** im Namen wiegen schwerer als die Einzelfälle: Fällt
ein Anker weg, hat der Check nichts mehr, wogegen er vergleicht — und die
naheliegende Implementierung meldet dafür «bestanden».
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.check_ruff_pin import workflow_pins
from tools.check_ruff_version import compare, parse_version

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_passende_version_ist_gruen() -> None:
    ok, message = compare("0.16.1", "ruff 0.16.1\n", 0)
    assert ok, message
    assert "0.16.1" in message


def test_falsche_version_wird_rot() -> None:
    """Der gemessene Vorfall: eine ältere ruff liegt vorne im PATH."""
    ok, message = compare("0.16.1", "ruff 0.15.8\n", 0)
    assert not ok
    assert "0.15.8" in message
    assert "0.16.1" in message
    # Der Befund muss sagen, warum der Pin-Sync das NICHT merkt — sonst sucht
    # der nächste Leser den Fehler in der falschen Datei.
    assert "zwei Texte" in message


def test_ANKER_fehlender_pin_ist_ein_befund() -> None:
    """Kein Pin heisst «nicht verglichen», nicht «bestanden»."""
    ok, message = compare(None, "ruff 0.16.1\n", 0)
    assert not ok
    assert "Anker" in message


@pytest.mark.parametrize(
    "raw",
    ["Ruff, version 0.16.1", "", "0.16.1", "ruff\n"],
    ids=["andere-form", "leer", "ohne-namen", "ohne-version"],
)
def test_ANKER_unlesbare_ausgabeform_ist_ein_befund(raw: str) -> None:
    """Ändert upstream die Ausgabe, darf der Check nicht still nichts tun."""
    ok, message = compare("0.16.1", raw, 0)
    assert not ok
    assert "antwortet nicht in der Form" in message


def test_fehlerhafter_aufruf_ist_ein_befund() -> None:
    ok, message = compare("0.16.1", "boom", 3)
    assert not ok
    assert "endete mit 3" in message


@pytest.mark.parametrize(
    ("raw", "erwartet"),
    [("ruff 0.16.1", "0.16.1"), ("ruff 0.16.1+deadbeef", "0.16.1+deadbeef")],
)
def test_parse_version(raw: str, erwartet: str) -> None:
    assert parse_version(raw) == erwartet


def test_echter_pin_ist_lesbar() -> None:
    """Der Guard darf nicht grün sein, weil er den echten Pin nicht findet."""
    text = (REPO_ROOT / ".github/workflows/lint.yml").read_text(encoding="utf-8")
    pins = workflow_pins(text)
    assert pins, (
        "lint.yml nennt kein `ruff==<version>` — dann prüft der "
        "Ruff-Version-Guard im Ernstfall nichts."
    )
