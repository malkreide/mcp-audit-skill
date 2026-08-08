"""Die Pruefungen unter tools/checks/ gegen den echten Baum und gegen Mutationen.

Zwei Behauptungen werden geprueft, und die zweite ist die, um die es geht:

1. Am unveraenderten Baum ist jede Pruefung gruen. Das faehrt die CI ohnehin —
   hier steht es, damit ein Fehlschlag in 2. nicht mit «der Baum ist eben
   kaputt» verwechselt wird.

2. Zu jedem Defekt, den eine Pruefung abdeckt, gibt es eine Mutation, die sie
   rot macht — MIT der erwarteten Meldung. Eine Pruefung, die aus dem falschen
   Grund rot wird, ist beim naechsten Mal aus dem falschen Grund gruen.

Seit die Pruefungen `(root) -> str` sind und `CheckFailed` werfen, laeuft das
ohne Unterprozess: Der Test ruft die Funktion mit dem Fixture-Baum und faengt
die Ausnahme. Zugesichert wird der Text, nicht bloss ein Exit-Code.

Dass die Suite selbst vollstaendig bleibt, prueft `test_suite_integrity.py`.
"""

from __future__ import annotations

import pytest
from conftest import CHECKS_BY_NAME, UMGEBUNGSABHAENGIG, gepinnte_version
from mutations import DESCRIPTIONS, MUTATIONS

from tools.checks import CheckFailed


@pytest.mark.parametrize("name", sorted(CHECKS_BY_NAME))
def test_unveraenderter_baum_ist_gruen(name, tree, ruff_shim, repo_json):
    # Umgebungsabhaengige Pruefungen bekommen eine ruff untergeschoben, die den
    # gepinnten Wert meldet. Sonst haenge dieser Test daran, welche ruff auf
    # der Maschine liegt — und wuerde genau dort rot, wo die Pruefung RECHT hat.
    if name in UMGEBUNGSABHAENGIG:
        ruff_shim(f'echo "ruff {gepinnte_version(tree)}"')
    repo_json()
    meldung = CHECKS_BY_NAME[name].run(tree)
    assert meldung, f"{name} meldet Erfolg ohne ein Wort darueber, was sie sah"


@pytest.mark.parametrize(
    ("mid", "check", "mutate", "expect"),
    MUTATIONS,
    ids=[m[0] for m in MUTATIONS],
)
def test_mutation_wird_rot(mid, check, mutate, expect, tree, repo_json):
    if mutate is not None:
        mutate(tree)
    repo_json(DESCRIPTIONS.get(mid))

    with pytest.raises(CheckFailed) as befund:
        CHECKS_BY_NAME[check].run(tree)

    assert expect in str(befund.value), (
        f"{check} wurde rot, aber nicht aus dem erwarteten Grund.\n"
        f"  erwartet: {expect!r}\n  gemeldet: {str(befund.value).strip()!r}"
    )


@pytest.mark.parametrize(
    ("mid", "check", "mutate", "expect"),
    MUTATIONS,
    ids=[m[0] for m in MUTATIONS],
)
def test_mutation_bleibt_nicht_gruen(mid, check, mutate, expect, tree, repo_json):
    """Derselbe Fall aus der anderen Richtung, und der teurere.

    `pytest.raises` oben faellt auch, wenn gar nichts geworfen wird — die
    Meldung waere dann aber «DID NOT RAISE» und sagte nicht, worum es ging.
    Dieser Test sagt es.
    """
    if mutate is not None:
        mutate(tree)
    repo_json(DESCRIPTIONS.get(mid))

    try:
        meldung = CHECKS_BY_NAME[check].run(tree)
    except CheckFailed:
        return
    pytest.fail(
        f"{check} blieb gruen, obwohl «{mid}» im Baum steht. Genau das ist der "
        f"Fall, den diese Pruefung verhindern soll.\n  gemeldet: {meldung!r}"
    )
