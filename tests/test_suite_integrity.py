"""Wächter über die Suite selbst.

Eine Testsuite kann genauso still aufhören zu prüfen wie ein CI-Schritt. Die
zwei Wege dorthin sind hier zugemauert: eine Prüfung ohne Mutation, und ein
Fixture-Baum, der mit dem echten nichts mehr zu tun hat.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import REPO_ROOT
from mutations import MUTATIONS

from tools.checks import Check, CheckFailed, all_checks, run
from tools.checks._core import _REGISTRY
from tools.checks.github_meta import SUGGESTED_DESCRIPTION, assert_description_matches
from tools.checks.skill_doc import core_step_count, read_skill

OFFLINE = all_checks(offline_only=True)


def _id(check: Check) -> str:
    return f"{check.number:02d}-{check.run.__name__}"


def test_every_check_has_at_least_one_mutation() -> None:
    """Der Zwang.

    Ohne ihn wäre eine neue Prüfung genau das, wogegen dieses Repository
    angeschrieben ist: eine Behauptung, die nie widerlegt wurde. Wer hier
    hinzufügt, fügt in `tests/mutations.py` mit hinzu.
    """
    covered = {m.check for m in MUTATIONS}
    registered = {c.number for c in all_checks()}
    missing = sorted(registered - covered)
    assert not missing, (
        f"Prüfung(en) {missing} haben keine Mutation. Eine Prüfung, die nie "
        "rot geworden ist, ist unbelegt — mindestens eine Mutation nach "
        "tests/mutations.py, die sie treffen MUSS."
    )


def test_no_mutation_points_at_a_check_that_is_gone() -> None:
    """Die Gegenrichtung.

    Eine Mutation auf eine Nummer, die es nicht mehr gibt, wäre ein Test, der
    nichts mehr fährt — und der Zähler oben zählte ihn trotzdem mit.
    """
    registered = {c.number for c in all_checks()}
    orphaned = sorted({m.check for m in MUTATIONS} - registered)
    assert not orphaned, (
        f"Mutation(en) zeigen auf Prüfung(en) {orphaned}, die es nicht mehr "
        "gibt — entweder wurde eine Prüfung entfernt, ohne ihre Mutationen "
        "mitzunehmen, oder eine Nummer hat sich verschoben."
    )


def test_registry_covers_every_check_module() -> None:
    """`@register` läuft beim Import — fehlt eine Import-Zeile, fehlt die Prüfung.

    Und zwar lautlos: Der Lauf wird kürzer, alles bleibt grün. Deshalb hier
    der Vergleich zwischen dem, was im Paket liegt, und dem, was registriert
    ist.
    """
    package = Path(__file__).resolve().parents[1] / "tools" / "checks"
    modules = {
        path.stem
        for path in package.glob("*.py")
        if not path.stem.startswith("_") and path.stem != "__init__"
    }
    registered_in = {check.run.__module__.rsplit(".", 1)[-1] for check in all_checks()}
    silent = sorted(modules - registered_in)
    assert not silent, (
        f"Modul(e) {silent} unter tools/checks/ registrieren keine Prüfung. "
        "Entweder fehlt der Import in tools/checks/__init__.py — dann "
        "verschwindet die Prüfung aus jedem Lauf, ohne dass etwas rot wird — "
        "oder das Modul gehört nicht dorthin."
    )


def test_check_numbers_are_unique_and_dense() -> None:
    """Lücken sind erlaubt, Dopplungen nicht.

    Die Nummern stehen im CHANGELOG und in Befunden («Check 12 hätte das
    gefangen»). Eine doppelt vergebene Nummer liesse eine Prüfung die andere
    verdecken; `register` verhindert das schon beim Import, dieser Test
    belegt, dass die Sperre noch da ist.
    """
    numbers = [c.number for c in all_checks()]
    assert numbers == sorted(set(numbers)), numbers
    assert len(_REGISTRY) == len(numbers)


@pytest.mark.parametrize("check", OFFLINE, ids=_id)
def test_check_passes_on_the_real_repository(check: Check) -> None:
    """Der Meta-Test.

    Ohne ihn prüfte die Suite am Ende nur sich selbst: Jedes Fixture, das man
    baut, enthält die Anker per Konstruktion, und jede Mutation ist ein Delta
    auf etwas Selbstgeschriebenes. Erst dieser Test hält die Prüfungen gegen
    den Baum, um den es geht.
    """
    check.run(REPO_ROOT)


@pytest.mark.parametrize("check", OFFLINE, ids=_id)
def test_check_passes_on_the_pristine_fixture(check: Check, fixture_repo: Path) -> None:
    """Und die Gegenprobe: Die Kopie muss dasselbe sagen wie das Original.

    Geht hier etwas kaputt, was oben grün ist, liegt es am Kopieren — eine
    verlorene Datei, ein anderes Zeilenende, ein fehlender Git-Index. Dann
    misst jede Mutation oben an einem Strohmann.
    """
    check.run(fixture_repo)


def test_the_offline_runner_leaves_the_network_check_out() -> None:
    """`scripts/validate.sh` muss ohne Netz und ohne Token durchlaufen.

    Sonst wäre der lokale Runner in einem frischen Clone rot, und ein Runner,
    der immer rot ist, wird nicht mehr gelesen.
    """
    assert {c.number for c in all_checks()} - {c.number for c in OFFLINE} == {15}


def test_suggested_description_is_advice_that_works() -> None:
    """Der Vorschlag im Befund von Check 15 muss die Prüfung bestehen.

    Ein Hinweis, der eine Description empfiehlt, die derselbe Check
    anschliessend beanstandet, schickt den Lesenden im Kreis. Stellt jemand
    SKILL.md auf vier Kernschritte um, wird dieser Test rot — an der Stelle,
    an der der Satz steht.
    """
    expected = core_step_count(read_skill(REPO_ROOT))
    assert_description_matches(SUGGESTED_DESCRIPTION, expected)


def test_a_crashing_check_is_reported_as_a_defect_not_as_a_finding() -> None:
    """Ein kaputter Check darf den Lauf weder mitnehmen noch sich tarnen.

    Nicht mitnehmen: Sonst zeigte ein roter Lauf einen statt aller Befunde.
    Nicht tarnen: «Die Prüfung ist abgestürzt» ist eine andere Nachricht als
    «das Repository hat einen Befund», und wer sie verwechselt, sucht am
    falschen Ort.
    """

    def broken(root: Path) -> str:
        raise TypeError("kaputt")

    result = run(Check(number=99, label="kaputt", run=broken), REPO_ROOT)
    assert not result.ok
    assert "abgestürzt" in result.output
    assert "TypeError" in result.output


def test_a_finding_is_not_mistaken_for_a_crash() -> None:
    def finds_something(root: Path) -> str:
        raise CheckFailed("hier stimmt etwas nicht")

    result = run(Check(number=98, label="Befund", run=finds_something), REPO_ROOT)
    assert not result.ok
    assert result.output == "hier stimmt etwas nicht"
