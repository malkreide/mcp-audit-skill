"""Jede Prüfung muss auf einem kaputten Baum rot werden — und richtig rot.

Der eigentliche Test dieser Suite. Alles in `test_suite_integrity.py` sorgt
dafür, dass er nicht schrumpft, ohne dass es jemand merkt.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mutations import MUTATIONS, Mutation

from tools.checks import CheckFailed, all_checks

BY_NUMBER = {check.number: check for check in all_checks()}


def _id(mutation: Mutation) -> str:
    return f"{mutation.check:02d}-{mutation.name}"


@pytest.mark.parametrize("mutation", MUTATIONS, ids=_id)
def test_mutation_is_caught(mutation: Mutation, fixture_repo: Path) -> None:
    """Der Befund muss kommen UND das Richtige sagen.

    Nur auf `CheckFailed` zu prüfen wäre die halbe Zusicherung: Eine Prüfung,
    die aus dem falschen Grund rot wird, schickt den Lesenden zur falschen
    Datei. Deshalb steht in jeder Mutation, welcher Teil des Befundes
    herauskommen muss.
    """
    check = BY_NUMBER[mutation.check]
    mutation.apply(fixture_repo)

    with pytest.raises(CheckFailed) as raised:
        check.run(fixture_repo)

    message = str(raised.value)
    assert mutation.expect in message, (
        f"Prüfung {check.number} wurde rot, aber mit einem anderen Befund als "
        f"erwartet.\n  erwartet (Teilstring): {mutation.expect!r}\n"
        f"  bekommen:\n{message}"
    )


@pytest.mark.parametrize("mutation", MUTATIONS, ids=_id)
def test_mutation_leaves_the_other_checks_alone(
    mutation: Mutation, fixture_repo: Path
) -> None:
    """Die mutierte Prüfung ist rot — aber nicht der ganze Baum.

    Ohne das hier wäre eine Mutation wie «lösche SKILL.md» ein billiger Weg zu
    einem grünen Mutationstest: Sie macht alles rot, also auch das Gewünschte,
    und belegt über die einzelne Prüfung nichts. Zugesichert wird, dass die
    Mutation zielt.

    Dass mehrere Prüfungen mithängen, ist dabei erlaubt und oft korrekt — wer
    `reference/` löscht, trifft 1, 2, 9, 10 und 11 zu Recht.
    """
    check = BY_NUMBER[mutation.check]
    mutation.apply(fixture_repo)

    others = [c for c in all_checks() if c.number != check.number]
    still_red = []
    for other in others:
        try:
            other.run(fixture_repo)
        except CheckFailed:
            still_red.append(other.number)

    assert len(still_red) < len(others), (
        f"Die Mutation «{mutation.name}» macht JEDE Prüfung rot — sie zielt "
        f"nicht auf Prüfung {check.number}, sie zerstört den Baum. Eine solche "
        "Mutation belegt über die einzelne Prüfung nichts."
    )


def test_check_9_catches_what_10_and_11_cannot(fixture_repo: Path) -> None:
    """Die Daseinsberechtigung der Sonde, als Test.

    Auf einem Baum, in dem `reference/` aus der ruff-Konfiguration genommen
    wurde, laufen beide Gates grün durch: Sie haben nichts zu beanstanden,
    weil sie nichts mehr lesen. Genau deshalb kann kein Gate sich selbst
    bewachen.

    Wird dieser Test rot, weil 10 oder 11 die Lage plötzlich selbst bemerken,
    ist das eine gute Nachricht mit Handlungsbedarf: Dann ist 9 überflüssig
    geworden und sollte gehen, statt als Zierde stehenzubleiben.
    """
    ruff_toml = fixture_repo / "ruff.toml"
    ruff_toml.write_text(
        ruff_toml.read_text(encoding="utf-8").replace(
            "[lint]\n", 'exclude = ["reference"]\n\n[lint]\n'
        ),
        encoding="utf-8",
    )

    BY_NUMBER[10].run(fixture_repo)
    BY_NUMBER[11].run(fixture_repo)

    with pytest.raises(CheckFailed) as raised:
        BY_NUMBER[9].run(fixture_repo)
    assert "greift auf reference/ nicht mehr" in str(raised.value)


def test_probe_file_is_removed_even_when_the_gate_is_blind(
    fixture_repo: Path,
) -> None:
    """Prüfung 9 legt eine fehlerhafte Datei ab. Sie darf nie liegenbleiben.

    Eine vergessene Sonde setzt die Prüfungen 1, 10 und 11 des nächsten Laufs
    auf eine Datei an, die niemand geschrieben hat — der Befund zeigte dann
    auf ein Gespenst. In der Shell-Fassung hing das an einem `trap`; hier an
    `try/finally`, und dieser Test ist der Beleg dafür.
    """
    ruff_toml = fixture_repo / "ruff.toml"
    ruff_toml.write_text(
        ruff_toml.read_text(encoding="utf-8").replace(
            "[lint]\n", 'exclude = ["reference"]\n\n[lint]\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(CheckFailed):
        BY_NUMBER[9].run(fixture_repo)

    leftovers = list((fixture_repo / "reference").glob("_ruff_gate_probe*"))
    assert leftovers == [], f"Sonde liegengeblieben: {leftovers}"
