"""Das generische Ruff-Gate unter `tools/gates/ruff.py`.

OHNE ECHTES RUFF, und das ist keine Bequemlichkeit. Der pytest-Job dieses
Repos installiert kein ruff — das liegt im lint-Job —, und die Matrix faehrt
Linux UND Windows. Ein Test, der eine echte oder untergeschobene ruff
braeuchte, pruefte die Testumgebung statt den Code, und ein
`#!/bin/sh`-Shim faellt unter Windows ohnehin um.

Ersetzt wird deshalb `_ruff` — die eine Naht, an der diese Gates den
Unterprozess anfassen. Was danach kommt, ist Entscheidungslogik ueber zwei
Zeichenketten, und genau die ist hier der Gegenstand.

Die Gates am ECHTEN Baum faehrt `scripts/validate.sh` als `audit/3`, `audit/4`,
`audit/6` und `audit/7`.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gates import ruff as gates  # noqa: E402
from tools.harness import CheckFailed  # noqa: E402


class FakeRuff:
    """Ersetzt `_ruff` und merkt sich, was die Sonden geschrieben haben.

    Der Reihe nach: erst `check`, dann `format`. Beide Ausgaben kommen aus dem
    Test, damit er die Entscheidung prueft und nicht ruffs Verhalten.
    """

    def __init__(self, check_out: str = "", format_out: str = ""):
        self.antworten = {"check": check_out, "format": format_out}
        self.gesehen: list[str] = []

    def __call__(self, root, *args):
        import subprocess

        kind = "check" if "check" in args else "format"
        # Was zu diesem Zeitpunkt unter probe_dir liegt, festhalten — die
        # Sonden raeumt das Gate danach wieder weg.
        for datei in sorted(root.rglob("_*probe*.py")):
            self.gesehen.append(datei.relative_to(root).as_posix())
        return subprocess.CompletedProcess(args, 0, self.antworten[kind], "")


@pytest.fixture
def baum(tmp_path):
    root = tmp_path / "repo"
    (root / "reference").mkdir(parents=True)
    (root / "ruff.toml").write_text("line-length = 88\n", encoding="utf-8")
    return root


# --------------------------------------------------------------------------
# Die Sonden: gelegt, gemessen, weggeraeumt
# --------------------------------------------------------------------------


def test_ANKER_ein_fehlendes_sondenverzeichnis_ist_ein_befund(baum, monkeypatch):
    """«Kein Verzeichnis» darf nicht wie «Gate greift» aussehen.

    Verschwindet das Verzeichnis, haette die Sonde nichts, woran sie das Gate
    testen koennte — und ein leeres Ergebnis als Erfolg zu melden ist genau
    der Fehler, gegen den diese Pruefung gerichtet ist.
    """
    monkeypatch.setattr(gates, "_ruff", FakeRuff())
    with pytest.raises(CheckFailed) as befund:
        gates.gate_bites(baum, probe_dir="gibtsnicht")
    assert "Anker weg" in str(befund.value)


def test_ANKER_eine_liegengebliebene_sonde_wird_nicht_ueberschrieben(baum, monkeypatch):
    """Sonst loeschte diese Pruefung eine Datei, die jemand anders geschrieben hat."""
    fremd = baum / "reference" / gates.PROBE_NAME
    fremd.write_text("# von Hand\n", encoding="utf-8")
    monkeypatch.setattr(gates, "_ruff", FakeRuff())
    with pytest.raises(CheckFailed) as befund:
        gates.gate_bites(baum, probe_dir="reference")
    assert "liegt schon da" in str(befund.value)
    assert fremd.read_text(encoding="utf-8") == "# von Hand\n"


def test_die_sonde_liegt_waehrend_der_messung_und_danach_nicht_mehr(baum, monkeypatch):
    fake = FakeRuff(check_out=gates.PROBE_NAME, format_out=gates.PROBE_NAME)
    monkeypatch.setattr(gates, "_ruff", fake)
    gates.gate_bites(baum, probe_dir="reference")
    assert f"reference/{gates.PROBE_NAME}" in fake.gesehen
    assert not (baum / "reference" / gates.PROBE_NAME).exists()


def test_die_sonde_wird_auch_nach_einem_befund_weggeraeumt(baum, monkeypatch):
    """Sonst setzte sie die Gates des naechsten Laufs auf eigene Reste an."""
    monkeypatch.setattr(gates, "_ruff", FakeRuff())  # beide Gates schweigen
    with pytest.raises(CheckFailed):
        gates.gate_bites(baum, probe_dir="reference")
    assert not (baum / "reference" / gates.PROBE_NAME).exists()


@pytest.mark.parametrize(
    ("check_out", "format_out", "erwartet"),
    [
        ("", gates.PROBE_NAME, "Lint-Gate greift"),
        (gates.PROBE_NAME, "", "Format-Gate greift"),
    ],
)
def test_schweigt_ein_gate_zur_sonde_ist_das_ein_befund(
    baum, monkeypatch, check_out, format_out, erwartet
):
    monkeypatch.setattr(gates, "_ruff", FakeRuff(check_out, format_out))
    with pytest.raises(CheckFailed) as befund:
        gates.gate_bites(baum, probe_dir="reference")
    assert erwartet in str(befund.value)


# --------------------------------------------------------------------------
# Die Breiten-Sonde
# --------------------------------------------------------------------------


@pytest.mark.parametrize("width", [40, 88, 100, 120])
def test_die_sonden_treffen_genau_die_verlangte_breite(width):
    """Trifft die Sonde die Breite nicht, misst sie etwas anderes als gemeint."""
    assert len(gates._comment_of(width)) == width
    assert len(gates._call_of(width)) == width


def test_die_kommentar_sonde_endet_nicht_auf_leerzeichen():
    """Sonst schluege sie ueber W291 an statt ueber E501 — rot aus dem falschen
    Grund, und beim naechsten Mal gruen aus dem falschen Grund."""
    for width in range(40, 130):
        assert not gates._comment_of(width).endswith(" "), width


def _laengen_ausgabe(width: int) -> tuple[str, str]:
    """Was ein gesundes Repo meldet: E501 nur auf der zu langen Sonde,
    Umbruch nur auf der zu langen Sonde."""
    over = f"reference/{gates.LENGTH_PROBE_OVER}"
    return f"{over}:1:{width}: E501 Line too long\n", f"Would reformat: {over}\n"


def test_bei_gesunder_konfiguration_ist_die_breite_bestaetigt(baum, monkeypatch):
    monkeypatch.setattr(gates, "_ruff", FakeRuff(*_laengen_ausgabe(89)))
    meldung = gates.line_length_effective(
        baum, probe_dir="reference", lint_enforces_e501=True
    )
    assert "88" in meldung and "89" in meldung


def test_ANKER_ohne_e501_im_select_bleibt_die_format_haelfte(baum, monkeypatch):
    """Der Fall dieses Repos — und der Grund, warum es keine Vorgabe gibt.

    `ruff.toml` fuehrt E501 ausdruecklich nicht im `select` («das entscheidet
    der Formatter»). Mit `lint_enforces_e501=True` waere jeder Lauf hier rot,
    und zwar aus einem Grund, der in der Konfiguration als Entscheidung
    dokumentiert steht.
    """
    _, format_out = _laengen_ausgabe(89)
    monkeypatch.setattr(gates, "_ruff", FakeRuff("", format_out))

    meldung = gates.line_length_effective(
        baum, probe_dir="reference", lint_enforces_e501=False
    )
    assert "Formatter" in meldung

    with pytest.raises(CheckFailed) as befund:
        gates.line_length_effective(
            baum, probe_dir="reference", lint_enforces_e501=True
        )
    assert "E501" in str(befund.value)


def test_ANKER_ohne_e501_wird_die_format_haelfte_trotzdem_geprueft(baum, monkeypatch):
    """Sonst waere `lint_enforces_e501=False` ein Schalter, der alles abschaltet."""
    monkeypatch.setattr(gates, "_ruff", FakeRuff("", ""))  # Formatter schweigt
    with pytest.raises(CheckFailed) as befund:
        gates.line_length_effective(
            baum, probe_dir="reference", lint_enforces_e501=False
        )
    assert "laesst eine Zeile" in str(befund.value)


def test_eine_fehlende_konfiguration_ist_ein_befund(baum, monkeypatch):
    (baum / "ruff.toml").unlink()
    monkeypatch.setattr(gates, "_ruff", FakeRuff())
    with pytest.raises(CheckFailed) as befund:
        gates.line_length_effective(
            baum, probe_dir="reference", lint_enforces_e501=False
        )
    assert "fehlt" in str(befund.value)


def test_ANKER_eine_zu_schmale_breite_ist_ein_befund_kein_stilles_bestehen(
    baum, monkeypatch
):
    """Unter MIN_WIDTH liesse sich keine Sonde mehr bauen, die genau eine
    Zeichenbreite trifft — die Pruefung wuerde nichts mehr messen."""
    (baum / "ruff.toml").write_text("line-length = 20\n", encoding="utf-8")
    monkeypatch.setattr(gates, "_ruff", FakeRuff())
    with pytest.raises(CheckFailed) as befund:
        gates.line_length_effective(
            baum, probe_dir="reference", lint_enforces_e501=False
        )
    assert str(gates.MIN_WIDTH) in str(befund.value)


def test_e501_zeilen_werden_nur_fuer_die_genannte_datei_gelesen():
    ausgabe = "a.py:1:89: E501 Line too long\nb.py:2:89: E501 Line too long\n"
    assert gates._e501_lines(ausgabe, "a.py") == {1}
    assert gates._e501_lines(ausgabe, "b.py") == {2}
    assert gates._e501_lines(ausgabe, "c.py") == set()
