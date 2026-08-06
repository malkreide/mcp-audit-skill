"""Wächter über die Suite selbst.

Eine Testsuite kann genauso still aufhören zu prüfen wie ein CI-Schritt. Die
Wege dorthin sind hier zugemauert: eine Prüfung ohne Mutation, ein
Fixture-Baum, der mit dem echten nichts mehr zu tun hat, und ein Modul, das
sich aus der Registry verabschiedet.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import REPO_ROOT, synthetic_manifest
from mutations import MUTATIONS

from tools.checks import Check, CheckFailed, all_checks, run
from tools.checks._core import _REGISTRY
from tools.checks.catalogue import assert_table_matches, parse_manifest
from tools.checks.readmes import top_release
from tools.checks.release import assert_tag_matches
from tools.checks.skill_doc import read_skill

OFFLINE = all_checks(offline_only=True)
CONTEXT_BOUND = {13, 14}


def _id(check: Check) -> str:
    return f"{check.number:02d}-{check.run.__name__}"


def test_every_check_has_at_least_one_mutation() -> None:
    """Der Zwang.

    Ohne ihn wäre eine neue Prüfung genau das, wogegen dieses Repository
    angeschrieben ist: eine Behauptung, die nie widerlegt wurde. Wer hier
    hinzufügt, fügt in `tests/mutations.py` mit hinzu.
    """
    covered = {m.check for m in MUTATIONS}
    missing = sorted({c.number for c in all_checks()} - covered)
    assert not missing, (
        f"Prüfung(en) {missing} haben keine Mutation. Eine Prüfung, die nie rot "
        "geworden ist, ist unbelegt — mindestens eine Mutation nach "
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

    Und zwar lautlos: Der Lauf wird kürzer, alles bleibt grün.
    """
    package = REPO_ROOT / "tools" / "checks"
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


def test_check_numbers_are_unique() -> None:
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


@pytest.mark.parametrize("check", all_checks(), ids=_id)
def test_check_passes_on_the_pristine_fixture(check: Check, fixture_repo: Path) -> None:
    """Und die Gegenprobe: Die Kopie muss dasselbe sagen wie das Original.

    Hier laufen auch 13 und 14 mit — im Fixture existiert ihr Kontext, den der
    echte Baum nicht mitbringt: ein Tag-Name und ein abgelegtes Manifest.
    Geht etwas kaputt, was oben grün ist, liegt es am Kopieren, und dann misst
    jede Mutation an einem Strohmann.
    """
    check.run(fixture_repo)


def test_the_offline_runner_leaves_the_context_bound_checks_out() -> None:
    """`scripts/validate.sh` muss ohne Netz und ohne Tag durchlaufen.

    Sonst wäre der lokale Runner in einem frischen Clone rot, und ein Runner,
    der immer rot ist, wird nicht mehr gelesen — Regel 5, angewandt auf das
    eigene Werkzeug.
    """
    assert {c.number for c in all_checks()} - {
        c.number for c in OFFLINE
    } == CONTEXT_BOUND


@pytest.mark.parametrize("number", [9, 10, 11])
def test_a_missing_ruff_is_a_finding_not_a_skip(
    number: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ohne ruff auf dem PATH werden alle drei Gates rot, nicht still grün.

    Diese Verzweigung lässt sich nicht als Mutation am Baum ausdrücken — sie
    hängt an der Umgebung, nicht an einer Datei. Getestet gehört sie trotzdem:
    Ein übersprungener Check meldete «bestanden», wo «nicht gelaufen» richtig
    wäre.
    """
    monkeypatch.setenv("PATH", "/nonexistent")
    by_number = {check.number: check for check in all_checks()}
    with pytest.raises(CheckFailed) as raised:
        by_number[number].run(REPO_ROOT)
    assert "ruff liegt nicht auf dem PATH" in str(raised.value)


@pytest.mark.parametrize(
    ("env", "expect"),
    [
        ({}, "ist nicht gesetzt"),
        ({"CATALOGUE_MANIFEST": ""}, "ist nicht gesetzt"),
    ],
)
def test_catalogue_without_its_manifest_is_a_finding(
    env: dict[str, str], expect: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CATALOGUE_MANIFEST", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    by_number = {check.number: check for check in all_checks()}
    with pytest.raises(CheckFailed) as raised:
        by_number[14].run(REPO_ROOT)
    assert expect in str(raised.value)


@pytest.mark.parametrize(
    ("tag", "expect"),
    [
        ("", "ist leer"),
        ("v1", "keine Version der Form vX.Y.Z"),
        ("release-2026", "keine Version der Form vX.Y.Z"),
        ("v0.0.1", "oberstes Release in CHANGELOG.md ist"),
    ],
)
def test_tag_shapes_that_must_be_findings(tag: str, expect: str) -> None:
    """Die Tag-Prüfung hat vier Ausgänge; drei hängen am Tag, nicht am Baum.

    Ein leerer Tag ist ausdrücklich dabei: Er wäre der stille Fall — die
    Prüfung lief, hatte aber keinen Gegenstand, und ohne diesen Zweig sähe das
    aus wie «bestanden».
    """
    lineno, heading, top = top_release(REPO_ROOT)
    with pytest.raises(CheckFailed) as raised:
        assert_tag_matches(tag, top, lineno, heading)
    assert expect in str(raised.value)


def test_the_synthetic_catalogue_is_accepted() -> None:
    """Der gute Fall von Prüfung 14, ohne Netz.

    Was das belegt und was nicht, steht bei `synthetic_manifest` in
    conftest.py: Es belegt, dass die Prüfung einen stimmigen Katalog
    durchlässt — nicht, dass SKILL.md zum echten passt. Dafür gibt es den
    Wochenplan.
    """
    skill = read_skill(REPO_ROOT)
    assert_table_matches(synthetic_manifest(skill), skill)


def test_a_manifest_that_is_not_a_catalogue_is_a_finding() -> None:
    """Format drüben geändert ist etwas anderes als Drift.

    Ohne diesen Zweig würde ein umgestelltes MANIFEST.txt als «null Checks»
    gelesen und ergäbe einen Drift-Befund, der auf die falsche Datei zeigt.
    """
    with pytest.raises(CheckFailed) as raised:
        parse_manifest("das ist jetzt YAML:\n  - FID-001\n")
    assert "sieht nicht aus wie eine Liste von Check-IDs" in str(raised.value)


def test_a_crashing_check_is_reported_as_a_defect_not_as_a_finding() -> None:
    """Ein kaputter Check darf den Lauf weder mitnehmen noch sich tarnen."""

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
