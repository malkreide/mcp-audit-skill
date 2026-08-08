"""Die Faelle von Check 6, die an der ANTWORT von ruff haengen, nicht am Baum.

Check 6 haelt die offenen Namen in `reference/` gegen eine Positivliste. Was
er dabei liest, kommt aus `ruff check --output-format json` — und genau diese
Schnittstelle ist die verletzliche Stelle: Aendert upstream die Meldungsform
oder das Ausgabeformat, findet die Pruefung keine Namen mehr. Ohne eigene
Zweige dafuer meldete sie dann «keine unerwarteten Namen», also «bestanden»,
wo «nicht gelaufen» richtig waere.

Diese Faelle lassen sich nicht ueber eine Baum-Mutation herstellen. Sie
brauchen eine untergeschobene `ruff`, die etwas Bestimmtes antwortet — dieselbe
Technik wie bei Check 8.
"""

from __future__ import annotations

import pytest

from tools.checks import CheckFailed
from tools.checks.references import reference_open_names

# Ein Befund in der Form, die ruff heute liefert.
EIN_BEFUND = '[{"code":"F821","message":"Undefined name `get_settings`"}]'


def test_geaenderte_meldungsform_ist_ein_befund(tree, ruff_shim):
    """ANKER: `Undefined name \\`x\\`` ist die Form, aus der der Name kommt."""
    ruff_shim(
        'echo \'[{"code":"F821","message":"Undefinierter Name `get_settings`"}]\'; exit 1'
    )
    with pytest.raises(CheckFailed) as befund:
        reference_open_names(tree)
    assert "traegt nicht die Form" in str(befund.value)


def test_kein_json_ist_ein_befund(tree, ruff_shim):
    """ANKER: das Ausgabeformat selbst."""
    ruff_shim("echo 'kein json'; exit 1")
    with pytest.raises(CheckFailed) as befund:
        reference_open_names(tree)
    assert "lieferte kein JSON" in str(befund.value)


def test_ruff_fehler_ist_ein_befund_kein_leeres_ergebnis(tree, ruff_shim):
    """exit 2 heisst «ruff ist gescheitert», nicht «nichts gefunden»."""
    ruff_shim("echo 'boom' >&2; exit 2")
    with pytest.raises(CheckFailed) as befund:
        reference_open_names(tree)
    assert "endete mit 2" in str(befund.value)


def test_null_treffer_bei_gefuellter_liste_ist_ein_befund(tree, ruff_shim):
    """Der Fall, der sonst als «alles sauber» durchginge.

    Nachgemessen und der Grund fuer diesen Zweig: `ruff check` liefert auf
    einen falschen Pfad eine leere Trefferliste UND exit 0.
    """
    ruff_shim("echo '[]'; exit 0")
    with pytest.raises(CheckFailed) as befund:
        reference_open_names(tree)
    text = str(befund.value)
    assert "Kein einziger offener Name" in text
    assert "nichts geprueft" in text


def test_ein_unerwarteter_name_ist_ein_befund(tree, ruff_shim):
    """Der Tippfehler-Fall, hier ueber die Antwort statt ueber den Baum."""
    ruff_shim('echo \'[{"code":"F821","message":"Undefined name `sttings`"}]\'; exit 1')
    with pytest.raises(CheckFailed) as befund:
        reference_open_names(tree)
    assert "['sttings']" in str(befund.value)
