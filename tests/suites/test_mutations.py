"""Jede Pruefung muss auf einem kaputten Baum rot werden — und richtig rot.

Der eigentliche Test der Companion-Suiten. Bis 2b-iv-c stand er nur in den
drei Herkunftsrepos; die READMEs dieses Repos versprachen ihn und loesten das
Versprechen nicht ein. Genau die Sorte Behauptung, gegen die diese Skills
geschrieben sind.

DREI ZUSICHERUNGEN, und die dritte ist die teure:

1. Am unveraenderten Baum ist jede Pruefung gruen. Das faehrt `validate.sh`
   ohnehin — hier steht es, damit ein Fehlschlag in 2. nicht mit «der Baum ist
   eben kaputt» verwechselt wird.
2. Zu jedem Defekt gibt es eine Mutation, die die Pruefung rot macht — MIT der
   erwarteten Meldung.
3. Und sie bleibt nicht gruen. `pytest.raises` faellt zwar auch, wenn nichts
   geworfen wird, aber mit «DID NOT RAISE» — einer Meldung, die nicht sagt,
   worum es ging. Dieser Fall ist der wichtigere von beiden, und er verdient
   einen eigenen Satz.

JEDE PRUEFUNG BRAUCHT MINDESTENS EINE MUTATION. Das prueft
`test_ANKER_jede_pruefung_hat_eine_mutation` — sonst waere die billigste Art,
diese Datei gruen zu halten, eine Pruefung ohne Eintrag.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.suites  # noqa: E402,F401  — laedt die Registry
from tools.harness import CheckFailed, all_checks  # noqa: E402

from . import (  # noqa: E402
    mcp_data_fidelity,
    mcp_data_source_probe,
    mcp_transport_hardening,
)
from ._mutation import Mutation  # noqa: E402

#: Suite -> Mutationen. Der Import oben laeuft ueber dasselbe Verzeichnis, das
#: `tools/suites/` fuehrt; fehlt hier eine Suite, faellt der Waechter unten.
NACH_SUITE = {
    "probe": mcp_data_source_probe.MUTATIONS,
    "fidelity": mcp_data_fidelity.MUTATIONS,
    "transport": mcp_transport_hardening.MUTATIONS,
}

ALLE: list[tuple[str, Mutation]] = [
    (suite, mutation)
    for suite, mutationen in NACH_SUITE.items()
    for mutation in mutationen
]

CHECKS = {
    suite: {c.run.__name__: c for c in all_checks(suite=suite)} for suite in NACH_SUITE
}


#: Die pytest-`id` je Fall. Als fertige LISTE und nicht als `ids=`-Funktion:
#: Die bekommt jeden Parameter EINZELN zu sehen und kann aus einer `Mutation`
#: allein keinen sprechenden Namen bilden.
IDS = [f"{suite}/{m.check}/{m.name}" for suite, m in ALLE]


@pytest.mark.parametrize(
    ("suite", "name"),
    [(suite, name) for suite, checks in CHECKS.items() for name in sorted(checks)],
    ids=lambda wert: wert,
)
def test_der_unveraenderte_baum_ist_gruen(suite, name, tree):
    """Der Ausgangspunkt, von dem die Mutationen wegfuehren.

    Und zugleich der Beleg, dass die Kopie den echten Baum nicht verloren hat:
    Eine Pruefung, die hier rot wird, misst den Fixture-Bau statt das
    Repository.
    """
    meldung = CHECKS[suite][name].run(tree)
    assert meldung, f"{suite}/{name} meldet Erfolg, ohne ein Wort darueber, was sie sah"


@pytest.mark.parametrize(("suite", "mutation"), ALLE, ids=IDS)
def test_die_mutation_wird_rot(suite, mutation, tree):
    mutation.apply(tree)
    with pytest.raises(CheckFailed) as befund:
        CHECKS[suite][mutation.check].run(tree)
    assert mutation.expect in str(befund.value), (
        f"{suite}/{mutation.check} wurde rot, aber nicht aus dem erwarteten "
        f"Grund.\n  erwartet (Teilzeichenkette): {mutation.expect!r}\n"
        f"  gemeldet:\n{befund.value}"
    )


@pytest.mark.parametrize(("suite", "mutation"), ALLE, ids=IDS)
def test_die_mutation_bleibt_nicht_gruen(suite, mutation, tree):
    """Derselbe Fall aus der anderen Richtung, mit einer Meldung, die redet."""
    mutation.apply(tree)
    try:
        meldung = CHECKS[suite][mutation.check].run(tree)
    except CheckFailed:
        return
    pytest.fail(
        f"{suite}/{mutation.check} blieb gruen, obwohl «{mutation.name}» im "
        "Baum steht. Genau das ist der Fall, den diese Pruefung verhindern "
        f"soll.\n  gemeldet: {meldung!r}"
    )


@pytest.mark.parametrize("suite", sorted(NACH_SUITE))
def test_ANKER_jede_pruefung_hat_eine_mutation(suite):
    """Sonst waere eine Pruefung ohne Eintrag der billigste Weg zu Gruen."""
    abgedeckt = {mutation.check for mutation in NACH_SUITE[suite]}
    fehlend = sorted(set(CHECKS[suite]) - abgedeckt)
    assert not fehlend, (
        f"Diese Pruefungen der Suite `{suite}` haben keine Mutation: "
        f"{fehlend}. Eine Pruefung, die nie rot geworden ist, ist eine "
        "Behauptung."
    )


@pytest.mark.parametrize("suite", sorted(NACH_SUITE))
def test_ANKER_keine_mutation_zeigt_ins_leere(suite):
    """Die Gegenrichtung: ein Eintrag auf eine Pruefung, die es nicht gibt.

    Er liefe sonst mit `KeyError` auf — einem Absturz statt eines Befundes,
    und der Lesende suchte den Fehler im Fixture-Baum statt in dieser Datei.
    """
    unbekannt = sorted({m.check for m in NACH_SUITE[suite]} - set(CHECKS[suite]))
    assert not unbekannt, (
        f"Die Suite `{suite}` hat keine Pruefungen namens {unbekannt}. "
        "Umbenannt oder aus der Registry gefallen — beides gehoert hier "
        "nachgezogen."
    )


@pytest.mark.parametrize("suite", sorted(NACH_SUITE))
def test_ANKER_jede_suite_mit_eigenen_pruefungen_hat_mutationen(suite):
    assert NACH_SUITE[suite], f"`{suite}` fuehrt keine einzige Mutation"
    assert CHECKS[suite], f"`{suite}` fuehrt keine einzige Pruefung"
