"""Die Checks unter tools/checks/ gegen den echten Baum und gegen Mutationen.

Zwei Behauptungen werden geprueft, und die zweite ist die, die es vorher nicht
gab:

1. Am unveraenderten Baum ist jeder Check gruen. Das faehrt die CI ohnehin —
   hier steht es, damit ein Fehlschlag in 2. nicht mit «der Baum ist eben
   kaputt» verwechselt wird.

2. Zu jedem Defekt, den ein Check abdeckt, gibt es eine Mutation, die ihn rot
   macht — MIT der erwarteten Meldung. Ein Check, der aus dem falschen Grund
   rot wird, ist beim naechsten Mal aus dem falschen Grund gruen.

Dass die Suite selbst vollstaendig bleibt, prueft `test_suite_integrity.py`.
"""

from __future__ import annotations

import pytest
from conftest import GOOD_DESCRIPTION, SCRIPTS, UMGEBUNGSABHAENGIG, gepinnte_version
from mutations import DESCRIPTIONS, MUTATIONS


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_unveraenderter_baum_ist_gruen(name, tree, run_check, ruff_shim):
    # Umgebungsabhaengige Checks bekommen eine ruff untergeschoben, die den
    # gepinnten Wert meldet. Sonst haenge dieser Test daran, welche ruff auf
    # der Maschine liegt — und wuerde genau dort rot, wo der Check RECHT hat.
    pfad = (
        ruff_shim(f'echo "ruff {gepinnte_version(tree)}"')
        if name in UMGEBUNGSABHAENGIG
        else None
    )
    p = run_check(name, tree, pfad=pfad)
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
