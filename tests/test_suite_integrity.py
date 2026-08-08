"""Die Testsuite selbst bleibt vollstaendig.

`test_mutations.py` prueft die Checks. Diese Datei prueft die Pruefung: Sie
faellt, wenn die Suite eine Zusage nicht mehr einloest — statt erst dann, wenn
ein Anker still verschwindet und niemand es merkt.

Das ist derselbe Gedanke eine Ebene hoeher. Ein Check ohne Mutationstest ist
eine Behauptung; ein Mutationstest, den niemand einfordert, kommt beim
naechsten Check einfach nicht mehr dazu.
"""

from __future__ import annotations

import pytest
from conftest import SCRIPTS
from mutations import MUTATIONS


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_jeder_check_hat_eine_anker_mutation(name):
    """Kein Check ohne Beleg, dass ein fehlender Anker ihn rot macht.

    Kommt ein weiterer Check dazu, faellt hier auf, dass seine Anker-Zusage
    noch unbelegt ist.
    """
    anker = [m for m in MUTATIONS if m[1] == name and "ANKER" in m[0]]
    assert anker, (
        f"{name} hat keine ANKER-Mutation. Ohne sie ist unbelegt, dass ein "
        "entfernter Anker FEHLER heisst und nicht «uebersprungen» — und genau "
        "das ist der Fehler, den diese Checks nicht machen duerfen."
    )


def test_jede_mutation_nennt_einen_bekannten_check():
    """Eine Mutation auf einen Check, den es nicht gibt, laeuft ins Leere.

    Ohne diesen Test wuerde ein Tippfehler im Check-Namen zu einem
    KeyError im Testlauf — lesbar, aber erst zur Laufzeit und ohne zu sagen,
    dass die Mutationstabelle das Problem ist.
    """
    unbekannt = sorted({m[1] for m in MUTATIONS} - SCRIPTS.keys())
    assert not unbekannt, (
        f"Mutationen verweisen auf unbekannte Checks: {unbekannt}. "
        "Entweder ist der Name vertippt, oder der Check wurde entfernt und "
        "seine Mutationen blieben stehen."
    )


def test_keine_doppelten_mutations_ids():
    """Zwei Mutationen mit demselben Namen verdecken einander im Bericht."""
    ids = [m[0] for m in MUTATIONS]
    doppelt = sorted({i for i in ids if ids.count(i) > 1})
    assert not doppelt, f"Mutations-IDs kommen mehrfach vor: {doppelt}"
