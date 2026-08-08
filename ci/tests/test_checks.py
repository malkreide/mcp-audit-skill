"""Die sechs Checks unter ci/checks/ gegen den echten Baum und gegen Mutationen.

Drei Behauptungen werden geprueft, und die zweite ist die, die es vorher nicht
gab:

1. Am unveraenderten Baum ist jeder Check gruen. Das faehrt die CI ohnehin —
   hier steht es, damit ein Fehlschlag in 2. nicht mit «der Baum ist eben
   kaputt» verwechselt wird.

2. Zu jedem Defekt, den ein Check abdeckt, gibt es eine Mutation, die ihn rot
   macht — MIT der erwarteten Meldung. Ein Check, der aus dem falschen Grund
   rot wird, ist beim naechsten Mal aus dem falschen Grund gruen.

3. Jeder Check hat mindestens eine ANKER-Mutation. Anker weg muss FEHLER
   heissen, nicht «uebersprungen». Diese Zusage stand an sechs Stellen in der
   Prosa und war nirgends nachgeprueft.
"""

from __future__ import annotations

import pytest
from conftest import GOOD_DESCRIPTION, SCRIPTS
from mutations import DESCRIPTIONS, MUTATIONS


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_unveraenderter_baum_ist_gruen(name, tree, run_check):
    p = run_check(name, tree)
    assert p.returncode == 0, (
        f"{name} ist am unveraenderten Baum rot:\n{p.stdout}{p.stderr}"
    )


@pytest.mark.parametrize(
    ("mid", "check", "mutate", "expect"),
    MUTATIONS,
    ids=[m[0] for m in MUTATIONS],
)
def test_mutation_wird_rot(mid, check, mutate, expect, tree, run_check):
    if mutate is not None:
        mutate(tree)
    p = run_check(check, tree, DESCRIPTIONS.get(mid, GOOD_DESCRIPTION))
    combined = p.stdout + p.stderr

    assert p.returncode != 0, (
        f"{check} blieb gruen, obwohl «{mid}» im Baum steht. Genau das ist der "
        f"Fall, den dieser Check verhindern soll.\n{combined}"
    )
    assert expect in combined, (
        f"{check} wurde rot, aber nicht aus dem erwarteten Grund.\n"
        f"  erwartet: {expect!r}\n  gemeldet: {combined.strip()!r}"
    )


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_jeder_check_hat_eine_anker_mutation(name):
    """Kein Check ohne Beleg, dass ein fehlender Anker ihn rot macht.

    Das ist der Meta-Test: Kommt ein siebter Check dazu, faellt hier auf, dass
    seine Anker-Zusage noch unbelegt ist — statt erst dann, wenn ein Anker
    still verschwindet und niemand es merkt.
    """
    anker = [m for m in MUTATIONS if m[1] == name and "ANKER" in m[0]]
    assert anker, (
        f"{name} hat keine ANKER-Mutation. Ohne sie ist unbelegt, dass ein "
        "entfernter Anker FEHLER heisst und nicht «uebersprungen» — und genau "
        "das ist der Fehler, den diese Checks nicht machen duerfen."
    )
