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


@pytest.mark.parametrize("number", [12, 13, 14])
def test_a_missing_ruff_is_a_finding_not_a_skip(
    number: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ohne ruff auf dem PATH werden alle drei Gates rot, nicht still grün.

    Diese Verzweigung lässt sich nicht als Mutation am Baum ausdrücken — sie
    hängt an der Umgebung, nicht an einer Datei. Getestet gehört sie trotzdem:
    Ein übersprungener Check meldete «bestanden», wo «nicht gelaufen» richtig
    wäre, und das ist die eine Auskunft, die schlimmer ist als keine.
    """
    monkeypatch.setenv("PATH", "/nonexistent")
    by_number = {check.number: check for check in all_checks()}

    with pytest.raises(CheckFailed) as raised:
        by_number[number].run(REPO_ROOT)
    assert "ruff liegt nicht auf dem PATH" in str(raised.value)


def _fake_ruff(directory: Path, output: str, *, code: int = 0) -> Path:
    """Ein `ruff` auf dem PATH, das sagt, was der Test braucht.

    Die Verzweigung hängt an der Umgebung, nicht an einer Datei — als
    Mutation am Baum ist sie nicht ausdrückbar.
    """
    shim = directory / "ruff"
    shim.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "{output}"\nexit {code}\n', encoding="utf-8"
    )
    shim.chmod(0o755)
    return shim


def test_check_18_catches_what_16_cannot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Die Daseinsberechtigung von Check 18, als Test.

    Check 16 vergleicht ci.yml mit .pre-commit-config.yaml — zwei Texte. Auf
    einem Rechner, auf dem eine ANDERE ruff weiter vorne im PATH liegt, sagt
    er weiter «beide Stellen stimmen überein» und hat damit recht: Die zwei
    Dateien tun es. Nur fahren die Gates 12, 13 und 14 daneben eine Version,
    die niemand gepinnt hat, und der Lauf meldet grün auf einem Baum, den die
    CI ablehnen kann.

    Wird dieser Test rot, weil 16 die Lage plötzlich selbst bemerkt, ist das
    eine gute Nachricht mit Handlungsbedarf: Dann ist 18 überflüssig geworden
    und sollte gehen, statt als Zierde stehenzubleiben.
    """
    _fake_ruff(tmp_path, "ruff 9.9.9")
    monkeypatch.setenv("PATH", str(tmp_path))
    by_number = {check.number: check for check in all_checks()}

    by_number[16].run(REPO_ROOT)

    with pytest.raises(CheckFailed) as raised:
        by_number[18].run(REPO_ROOT)
    message = str(raised.value)
    assert "Die ruff auf dem PATH ist 9.9.9" in message
    assert "which -a ruff" in message


def test_check_18_needs_a_ruff_it_can_ask(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ohne ruff ist das ein Befund, kein Skip — wie bei den Gates selbst."""
    monkeypatch.setenv("PATH", "/nonexistent")
    by_number = {check.number: check for check in all_checks()}

    with pytest.raises(CheckFailed) as raised:
        by_number[18].run(REPO_ROOT)
    assert "ruff liegt nicht auf dem PATH" in str(raised.value)


def test_check_18_says_so_when_it_cannot_read_the_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Die Ausgabeform von `ruff --version` ist selbst ein Anker.

    Änderte upstream sie, verglichen wir nichts mehr. Ein Befund, der auf die
    Ausgabe zeigt, ist die einzige Antwort, die niemanden in die falsche
    Datei schickt.
    """
    _fake_ruff(tmp_path, "astral ruff, version 0.16.1")
    monkeypatch.setenv("PATH", str(tmp_path))
    by_number = {check.number: check for check in all_checks()}

    with pytest.raises(CheckFailed) as raised:
        by_number[18].run(REPO_ROOT)
    assert "antwortet nicht in der Form" in str(raised.value)


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
