# -*- coding: utf-8 -*-
"""Tests für den Ruff-Pin-Guard.

Der Pre-Commit-Hook verspricht, lokal genau das zu erzwingen, was der lint-Job
prüft. Dieses Versprechen hängt vollständig daran, dass beide dieselbe
Ruff-Version nennen — und die Version steht an zwei Orten, die nichts
aneinander bindet ausser einer Bitte im Kommentar.

Geprüft wird die **reine** Seite: `compare()` bekommt beide Dateiinhalte als
Strings. Kein Dateisystem, keine Mocks — ein Mock bildete nur die eigene
Annahme über das Dateiformat ab.

Zwei Eigenschaften wiegen schwerer als die Einzelfälle:

* ein **fehlender** Pin ist ein Befund, nicht ein stilles Bestehen — sonst
  bestünde eine Konfiguration, die Ruff gar nicht mehr pinnt, immer;
* die echten Repo-Dateien müssen zueinander passen, sonst ist der Guard grün
  und die Realität rot.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.check_ruff_pin import compare, precommit_pin, workflow_pins

REPO_ROOT = Path(__file__).resolve().parent.parent

WORKFLOW = """\
jobs:
  lint:
    steps:
      - run: pip install ruff==0.15.8
      - run: ruff check .
"""

PRECOMMIT = """\
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.8
    hooks:
      - id: ruff-check
      - id: ruff-format
"""


def test_matching_pins_pass():
    ok, message = compare(WORKFLOW, PRECOMMIT)
    assert ok, message
    assert "0.15.8" in message


def test_v_prefix_is_stripped_before_comparing():
    """`rev: v0.15.8` und `ruff==0.15.8` sind dieselbe Version."""
    assert precommit_pin(PRECOMMIT) == "0.15.8"


@pytest.mark.parametrize(
    "workflow_pin, hook_rev",
    [
        ("0.15.22", "v0.15.8"),  # nur der Workflow gebumpt
        ("0.15.8", "v0.15.22"),  # nur der Hook gebumpt
    ],
)
def test_diverging_pins_are_reported(workflow_pin, hook_rev):
    ok, message = compare(
        WORKFLOW.replace("0.15.8", workflow_pin),
        PRECOMMIT.replace("v0.15.8", hook_rev),
    )
    assert not ok
    assert message.startswith("DRIFT:")


def test_missing_workflow_pin_is_a_finding():
    """Ohne Pin hat der Vergleich nicht stattgefunden — kein stilles Bestehen."""
    ok, message = compare(WORKFLOW.replace("ruff==0.15.8", "ruff"), PRECOMMIT)
    assert not ok
    assert message.startswith("KEIN PIN:")


def test_missing_hook_rev_is_a_finding():
    ok, message = compare(WORKFLOW, PRECOMMIT.replace("    rev: v0.15.8\n", ""))
    assert not ok
    assert message.startswith("KEIN PIN:")


def test_missing_ruff_repo_entirely_is_a_finding():
    ok, message = compare(WORKFLOW, "repos: []\n")
    assert not ok
    assert message.startswith("KEIN PIN:")


def test_rev_of_another_repo_is_not_mistaken_for_ruffs():
    """Ein zweites Repo mit eigener `rev` darf den Vergleich nicht verfaelschen."""
    with_other = (
        "repos:\n"
        "  - repo: https://github.com/pre-commit/pre-commit-hooks\n"
        "    rev: v9.9.9\n"
        "    hooks:\n"
        "      - id: end-of-file-fixer\n"
        "  - repo: https://github.com/astral-sh/ruff-pre-commit\n"
        "    rev: v0.15.8\n"
        "    hooks:\n"
        "      - id: ruff-check\n"
    )
    assert precommit_pin(with_other) == "0.15.8"
    ok, _ = compare(WORKFLOW, with_other)
    assert ok


def test_several_workflow_pins_must_all_match():
    two = WORKFLOW + "      - run: pip install ruff==0.15.22\n"
    assert workflow_pins(two) == ["0.15.8", "0.15.22"]
    ok, message = compare(two, PRECOMMIT)
    assert not ok
    assert "0.15.22" in message


def test_the_real_repo_files_agree():
    """Der Guard prüft nichts, wenn er nicht auf die echten Dateien passt."""
    workflow = REPO_ROOT / ".github" / "workflows" / "lint.yml"
    precommit = REPO_ROOT / ".pre-commit-config.yaml"
    assert workflow.is_file(), f"{workflow} fehlt"
    assert precommit.is_file(), f"{precommit} fehlt"

    ok, message = compare(
        workflow.read_text(encoding="utf-8"),
        precommit.read_text(encoding="utf-8"),
    )
    assert ok, message
