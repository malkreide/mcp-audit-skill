"""Das gemeinsame Geruest unter `tools/harness/`.

Der Gegenstand dieser Datei ist die eine Eigenschaft, die das
zusammengefuehrte Geruest haben muss und die vier getrennte Registries nicht
brauchten: DIESELBE NUMMER IN ZWEI SUITEN. `audit/1` und `probe/1` sind
verschiedene Pruefungen, beide behalten die Nummer, unter der sie in ihrem
CHANGELOG steht.

Die Registry ist Modulzustand, den `@register` beim Import fuellt. Jeder Test
hier baut sich seine eigene und stellt danach die echte wieder her — sonst
haengt das Ergebnis daran, welche Datei pytest zuerst eingesammelt hat.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.harness import _core  # noqa: E402
from tools.harness.__main__ import parse_args, select  # noqa: E402
from tools.harness._core import (  # noqa: E402
    Check,
    CheckFailed,
    all_checks,
    pycache_to_temp,
    register,
    run,
    run_all,
    suites,
)


@pytest.fixture
def leere_registry(monkeypatch):
    """Eine frische Registry, die nach dem Test verschwindet."""
    monkeypatch.setattr(_core, "_REGISTRY", {})
    return _core._REGISTRY


def gruen(text: str = "ok"):
    def pruefung(root: pathlib.Path) -> str:
        return text

    return pruefung


# --------------------------------------------------------------------------
# Der Grund fuer die Suite-Spalte
# --------------------------------------------------------------------------


def test_ANKER_dieselbe_nummer_darf_in_zwei_suiten_stehen(leere_registry):
    """Die Zusicherung, an der die ganze Zusammenfuehrung haengt.

    Vier Repos numerieren jedes ab 1, und die Nummern stehen in vier
    CHANGELOGs. Ein flacher Nummernraum haette 48 von 53 Registrierungen
    umnumeriert und damit jede dieser Referenzen stillschweigend falsch
    gemacht.
    """
    register(1, "audit-seins", suite="audit")(gruen())
    register(1, "probe-seins", suite="probe")(gruen())

    ids = [c.id for c in all_checks()]
    assert ids == ["audit/1", "probe/1"]


def test_dieselbe_nummer_in_derselben_suite_ist_ein_importfehler(leere_registry):
    """Doppelt vergeben heisst: die zweite verdeckt die erste, lautlos."""
    register(3, "erste", suite="audit")(gruen())
    with pytest.raises(RuntimeError) as fehler:
        register(3, "zweite", suite="audit")(gruen())
    assert "audit" in str(fehler.value)
    assert "3" in str(fehler.value)


def test_nummern_sind_je_suite_lueckenlos_und_eindeutig(leere_registry):
    """Dieselbe Invariante wie in den Herkunftsrepos — nur je Suite.

    Eine Luecke ist dort fast immer eine Pruefung, die aus der Registry
    gefallen ist. Ueber alle Suiten gerechnet waere die Pruefung sinnlos: Der
    vereinigte Nummernraum ist absichtlich nicht lueckenlos.
    """
    for n in (1, 2, 3):
        register(n, f"a{n}", suite="audit")(gruen())
    for n in (1, 2):
        register(n, f"p{n}", suite="probe")(gruen())

    for suite in suites():
        nummern = [c.number for c in all_checks(suite=suite)]
        assert nummern == sorted(set(nummern)), f"{suite}: nicht eindeutig"
        assert nummern == list(range(1, len(nummern) + 1)), f"{suite}: nicht lueckenlos"


def test_die_kennung_nennt_suite_und_nummer(leere_registry):
    register(7, "irgendwas", suite="transport")(gruen())
    assert all_checks()[0].id == "transport/7"


# --------------------------------------------------------------------------
# Auswahl
# --------------------------------------------------------------------------


def test_suite_filter_liefert_nur_deren_pruefungen(leere_registry):
    register(1, "a", suite="audit")(gruen())
    register(1, "p", suite="probe")(gruen())
    assert [c.id for c in all_checks(suite="probe")] == ["probe/1"]


def test_offline_filter_laesst_die_netzpruefung_draussen(leere_registry):
    register(1, "offline", suite="audit")(gruen())
    register(2, "braucht netz", suite="audit", offline=False)(gruen())
    assert [c.number for c in all_checks(offline_only=True)] == [1]


def test_select_nimmt_einzelne_kennungen(leere_registry):
    register(1, "a", suite="audit")(gruen())
    register(2, "b", suite="audit")(gruen())
    assert [c.id for c in select(["audit/2"])] == ["audit/2"]


def test_ANKER_eine_unbekannte_kennung_bricht_ab(leere_registry):
    """«Nichts gefahren» und «alles bestanden» sehen am Ende gleich aus."""
    register(1, "a", suite="audit")(gruen())
    with pytest.raises(SystemExit) as abbruch:
        select(["audit/9"])
    assert "audit/9" in str(abbruch.value)


def test_ANKER_eine_unbekannte_suite_bricht_ab(leere_registry):
    register(1, "a", suite="audit")(gruen())
    with pytest.raises(SystemExit) as abbruch:
        select([], suite="tippfehler")
    assert "tippfehler" in str(abbruch.value)


def test_ANKER_der_alte_flag_name_aus_fidelity_gilt_weiter():
    """`--include-context-bound` ist der dokumentierte Aufruf eines der vier.

    Die Zusammenfuehrung darf ihre Kosten nicht in fremde READMEs verlagern:
    Was dort steht, muss weiter laufen.
    """
    assert parse_args(["--include-context-bound"]).include_network
    assert parse_args(["--include-network"]).include_network
    assert not parse_args([]).include_network


# --------------------------------------------------------------------------
# Ausfuehrung
# --------------------------------------------------------------------------


def test_eine_abgestuerzte_pruefung_ist_ein_defekt_kein_befund(tmp_path):
    def stuerzt_ab(root):
        raise TypeError("kaputt")

    ergebnis = run(
        Check(number=99, label="kaputt", run=stuerzt_ab, suite="test"), tmp_path
    )
    assert not ergebnis.ok
    assert "abgestuerzt" in ergebnis.output
    assert "TypeError" in ergebnis.output
    assert "tools/harness" in ergebnis.output


def test_ein_befund_wird_nicht_fuer_einen_absturz_gehalten(tmp_path):
    def meldet_befund(root):
        raise CheckFailed("das Repository hat ein Problem")

    ergebnis = run(
        Check(number=98, label="Befund", run=meldet_befund, suite="test"), tmp_path
    )
    assert not ergebnis.ok
    assert ergebnis.output == "das Repository hat ein Problem"
    assert "abgestuerzt" not in ergebnis.output


def test_ein_lauf_nennt_alle_befunde_nicht_nur_den_ersten(tmp_path):
    def rot(root):
        raise CheckFailed("Befund")

    checks = [
        Check(number=n, label=f"c{n}", run=rot, suite="test") for n in (91, 92, 93)
    ]
    ergebnisse = run_all(tmp_path, checks)
    assert len(ergebnisse) == 3
    assert all(not e.ok for e in ergebnisse)


def test_ANKER_ein_leerer_lauf_ist_rot(leere_registry, capsys):
    """«0 checks, all passed» waere die gefaehrlichste gruene Meldung ueberhaupt.

    Solange keine Suite ihre Pruefmodule importiert, ist die Registry leer.
    Meldete der Runner das als Erfolg, liefe die CI gruen ueber ein
    Repository, das nichts geprueft hat — und niemand saehe es.
    """
    from tools.harness.__main__ import main

    assert main([]) == 1
    assert "kein Erfolg" in capsys.readouterr().out


def test_pycache_to_temp_stellt_das_praefix_wieder_her():
    vorher = sys.pycache_prefix
    with pycache_to_temp():
        assert sys.pycache_prefix != vorher
    assert sys.pycache_prefix == vorher
