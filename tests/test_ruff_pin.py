"""Tests für den Ruff-Pin-Guard.

Der Pin hat EINE Quelle, `requirements-lint.txt`. Der Pre-Commit-Hook muss
dieselbe Version nennen, und die Workflows müssen aus der Datei installieren,
statt eine eigene Zahl zu tragen. Dieser Guard ist das, was «eine Quelle» mehr
sein lässt als eine Bitte im Kommentar.

Geprüft wird die **reine** Seite: `compare()` bekommt die Dateiinhalte als
Strings. Kein Dateisystem, keine Mocks — ein Mock bildete nur die eigene
Annahme über das Dateiformat ab.

Drei Eigenschaften wiegen schwerer als die Einzelfälle:

* ein **fehlender** Pin ist ein Befund, nicht ein stilles Bestehen — sonst
  bestünde eine Konfiguration, die Ruff gar nicht mehr pinnt, immer;
* ein Workflow, der selbst pinnt, ist ein Befund **auch mit der richtigen
  Zahl** — die Kopie ist der Fehler, nicht die Abweichung. Genau so lief die
  Kopie in `test.yml` jahrelang ungeprüft mit;
* die echten Repo-Dateien müssen zueinander passen, sonst ist der Guard grün
  und die Realität rot.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.check_ruff_pin import (
    PIN_SOURCE,
    PRECOMMIT_CONFIG,
    WORKFLOWS,
    compare,
    precommit_pin,
    requirements_pin,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

QUELLE = """\
# die einzige Quelle
ruff==0.15.8
"""

WORKFLOW = """\
jobs:
  lint:
    steps:
      - run: pip install -r requirements-lint.txt
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


def workflows(text: str = WORKFLOW) -> dict[str, str]:
    return {"lint.yml": text}


def test_matching_pins_pass():
    ok, message = compare(QUELLE, PRECOMMIT, workflows())
    assert ok, message
    assert "0.15.8" in message


def test_v_prefix_is_stripped_before_comparing():
    """`rev: v0.15.8` und `ruff==0.15.8` sind dieselbe Version."""
    assert precommit_pin(PRECOMMIT) == "0.15.8"


@pytest.mark.parametrize(
    "source_pin, hook_rev",
    [
        ("0.15.22", "v0.15.8"),  # nur die Quelle gebumpt
        ("0.15.8", "v0.15.22"),  # nur der Hook gebumpt
    ],
)
def test_diverging_pins_are_reported(source_pin, hook_rev):
    ok, message = compare(
        QUELLE.replace("0.15.8", source_pin),
        PRECOMMIT.replace("v0.15.8", hook_rev),
        workflows(),
    )
    assert not ok
    assert message.startswith("DRIFT:")


def test_missing_source_pin_is_a_finding():
    """Ohne Pin hat der Vergleich nicht stattgefunden — kein stilles Bestehen."""
    ok, message = compare(
        QUELLE.replace("ruff==0.15.8", "ruff"), PRECOMMIT, workflows()
    )
    assert not ok
    assert message.startswith("KEIN PIN:")


def test_a_pin_only_in_a_comment_is_no_pin():
    """Ein auskommentierter Pin ist keiner — und kein «mehrfach gepinnt»."""
    kommentiert = "# ruff==0.15.8\nruff\n"
    assert requirements_pin(kommentiert) is None
    ok, message = compare(kommentiert, PRECOMMIT, workflows())
    assert not ok
    assert "KEIN PIN:" in message
    assert "mehrfach" not in message


def test_two_versions_in_the_source_are_a_contradiction():
    ok, message = compare(QUELLE + "ruff==0.15.22\n", PRECOMMIT, workflows())
    assert not ok
    assert "mehrfach" in message


def test_missing_hook_rev_is_a_finding():
    no_rev = PRECOMMIT.replace("    rev: v0.15.8\n", "")
    ok, message = compare(QUELLE, no_rev, workflows())
    assert not ok
    assert message.startswith("KEIN PIN:")


def test_missing_ruff_repo_entirely_is_a_finding():
    ok, message = compare(QUELLE, "repos: []\n", workflows())
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
    ok, _ = compare(QUELLE, with_other, workflows())
    assert ok


# --------------------------------------------------------------------------
# Eine Quelle: die Workflows lesen aus ihr und tragen keine eigene Zahl
# --------------------------------------------------------------------------


def test_ANKER_ein_workflow_pin_ist_eine_zweite_quelle_auch_wenn_er_passt():
    """Die Kopie ist der Fehler, nicht die Abweichung — sie driftet spaeter."""
    gepinnt = WORKFLOW.replace(
        "-r requirements-lint.txt", "-r requirements-lint.txt ruff==0.15.8"
    )
    ok, message = compare(QUELLE, PRECOMMIT, workflows(gepinnt))
    assert not ok
    assert "ZWEITE QUELLE: lint.yml" in message


def test_ein_workflow_ohne_installation_aus_der_quelle_ist_nicht_verdrahtet():
    ohne = WORKFLOW.replace("-r requirements-lint.txt", "ruff")
    ok, message = compare(QUELLE, PRECOMMIT, workflows(ohne))
    assert not ok
    assert "NICHT VERDRAHTET: lint.yml" in message


def test_die_lange_option_zaehlt_als_verdrahtet():
    lang = WORKFLOW.replace("-r ", "--requirement ")
    ok, message = compare(QUELLE, PRECOMMIT, workflows(lang))
    assert ok, message


def test_jeder_befund_wird_genannt_nicht_nur_der_erste():
    """Ein Lauf nennt alle — sonst kostet jede Korrektur eine Runde."""
    kaputt = {
        "lint.yml": WORKFLOW.replace("-r requirements-lint.txt", "ruff==0.15.8"),
        "test.yml": "run: pip install pytest\n",
    }
    ok, message = compare(QUELLE, PRECOMMIT.replace("v0.15.8", "v0.15.22"), kaputt)
    assert not ok
    for erwartet in (
        "DRIFT:",
        "ZWEITE QUELLE: lint.yml",
        "NICHT VERDRAHTET: lint.yml",
        "NICHT VERDRAHTET: test.yml",
    ):
        assert erwartet in message, erwartet


def test_the_real_repo_files_agree():
    """Der Guard prüft nichts, wenn er nicht auf die echten Dateien passt."""
    pfade = [PIN_SOURCE, PRECOMMIT_CONFIG, *WORKFLOWS]
    for rel in pfade:
        assert (REPO_ROOT / rel).is_file(), f"{rel} fehlt"

    def lies(rel: Path) -> str:
        return (REPO_ROOT / rel).read_text(encoding="utf-8")

    ok, message = compare(
        lies(PIN_SOURCE),
        lies(PRECOMMIT_CONFIG),
        {rel.as_posix(): lies(rel) for rel in WORKFLOWS},
    )
    assert ok, message
