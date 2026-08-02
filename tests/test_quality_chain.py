"""Tests für den Qualitätsketten-Guard und für die Ketten-Tabelle in den READMEs.

Zwei Dinge werden hier geprüft, und sie liegen bewusst in einer Datei, weil sie
dieselbe Frage von zwei Seiten stellen: Steht die Zugehörigkeit der fünf Repos
überall gleich?

* Die **reine** Seite des Guards — `compare()` und `fix_commands()` bekommen
  das Metadaten-Dict übergeben. Der Netzaufruf (`fetch()`) wird bewusst *nicht*
  gemockt: Ein Mock bildete nur die eigene Annahme über die GitHub-Antwort ab
  und könnte sie nie widerlegen — die Grenze, an der `DRIFT-004` ansetzt.

* Das **Manifest gegen die READMEs**. Die Kette steht an drei Orten in diesem
  Repo — `docs/quality-chain.json`, `README.md`, `README.de.md` — und an
  weiteren acht in den vier Schwester-Repos. Die drei hier sind erreichbar,
  also werden sie erzwungen.

Die härteste Eigenschaft ist die, die am leichtesten kaputtgeht: ein
**fehlendes** Feld in der API-Antwort ist ungeprüft und nicht bestanden. Ohne
diesen Test wäre die bequeme Variante — fehlendes `topics` als «keine Topics»
zu lesen — nicht von der richtigen zu unterscheiden, solange die API das Feld
mitschickt.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tools.check_quality_chain import (
    MISSING,
    compare,
    fix_commands,
    load_manifest,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "docs" / "quality-chain.json"

TOPIC = "mcp-quality-chain"
HOMEPAGE = "https://github.com/topics/mcp-quality-chain"


def _meta(**overrides):
    """Ein Repo, das alles richtig macht — überschreibbar pro Test."""
    base = {
        "topics": ["claude-skill", "mcp", TOPIC],
        "homepage": HOMEPAGE,
        "description": "Claude Skill for something",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------
# compare() — die reine Seite
# --------------------------------------------------------------------------


def test_ein_vollstaendiges_repo_hat_keine_befunde():
    assert compare(_meta(), TOPIC, HOMEPAGE) == []


def test_fehlendes_topic_ist_ein_befund():
    problems = compare(_meta(topics=["mcp", "claude-skill"]), TOPIC, HOMEPAGE)
    assert len(problems) == 1
    assert TOPIC in problems[0]
    # Die bestehenden Topics gehören in die Meldung: wer sie nicht sieht,
    # ersetzt sie beim Beheben versehentlich.
    assert "claude-skill" in problems[0]


def test_leere_topic_liste_ist_ein_befund_und_nennt_keine():
    problems = compare(_meta(topics=[]), TOPIC, HOMEPAGE)
    assert len(problems) == 1
    assert "keine" in problems[0]


@pytest.mark.parametrize("field", ["topics", "homepage", "description"])
def test_fehlendes_feld_ist_unverified_und_nicht_bestanden(field):
    """Der Kern des Guards: kein Feld heisst nicht geprüft, nicht bestanden.

    Wenn die API ein Feld nicht mehr mitschickt, darf der Guard weder «stimmt»
    melden noch einen inhaltlichen Befund erfinden, den er nicht gemessen hat.
    """
    meta = _meta()
    del meta[field]
    problems = compare(meta, TOPIC, HOMEPAGE)
    assert len(problems) == 1
    assert problems[0].startswith("UNVERIFIED:")
    assert "kein Bestehen" in problems[0]


@pytest.mark.parametrize("field", ["topics", "homepage", "description"])
def test_explizites_missing_verhaelt_sich_wie_ein_fehlendes_feld(field):
    """`fetch()` setzt MISSING statt den Schlüssel wegzulassen — gleiche Wirkung."""
    problems = compare(_meta(**{field: MISSING}), TOPIC, HOMEPAGE)
    assert len(problems) == 1
    assert problems[0].startswith("UNVERIFIED:")


def test_null_topics_ist_keine_topics_und_nicht_unverified():
    """`"topics": null` ist eine Aussage der API, `MISSING` ist keine."""
    problems = compare(_meta(topics=None), TOPIC, HOMEPAGE)
    assert len(problems) == 1
    assert not problems[0].startswith("UNVERIFIED:")


def test_falsche_homepage_ist_ein_befund():
    problems = compare(_meta(homepage="https://example.com"), TOPIC, HOMEPAGE)
    assert len(problems) == 1
    assert "Homepage" in problems[0]


def test_leere_homepage_ist_ein_befund():
    # Die API liefert für eine ungesetzte Homepage mal `""`, mal `null`.
    for empty in ("", None):
        problems = compare(_meta(homepage=empty), TOPIC, HOMEPAGE)
        assert len(problems) == 1, f"homepage={empty!r}"


def test_abschliessender_schraegstrich_ist_kein_befund():
    assert compare(_meta(homepage=HOMEPAGE + "/"), TOPIC, HOMEPAGE) == []


@pytest.mark.parametrize("empty", ["", "   ", None])
def test_leere_description_ist_ein_befund(empty):
    problems = compare(_meta(description=empty), TOPIC, HOMEPAGE)
    assert len(problems) == 1
    assert "Description" in problems[0]


def test_mehrere_abweichungen_werden_alle_gemeldet():
    problems = compare(
        _meta(topics=["mcp"], homepage="", description=""), TOPIC, HOMEPAGE
    )
    assert len(problems) == 3


# --------------------------------------------------------------------------
# fix_commands() — was der Guard vorschlägt, statt selbst zu schreiben
# --------------------------------------------------------------------------


def test_ein_vollstaendiges_repo_braucht_kein_kommando():
    assert fix_commands("o/r", _meta(), TOPIC, HOMEPAGE) == []


def test_topic_kommando_nennt_die_liste_nach_dem_setzen():
    commands = fix_commands("o/r", _meta(topics=["mcp"]), TOPIC, HOMEPAGE)
    assert len(commands) == 1
    assert f"--add-topic {TOPIC}" in commands[0]
    # Das bestehende Topic muss in der Nachher-Liste auftauchen, sonst räumt
    # jemand es beim Übersetzen in einen API-Aufruf ab.
    assert "mcp" in commands[0].split("#", 1)[1]


def test_fuer_ein_ungeprueftes_feld_gibt_es_kein_kommando():
    """Ein Kommando gegen unbekannten Zustand wäre geraten, nicht gemessen."""
    meta = _meta()
    del meta["topics"]
    assert fix_commands("o/r", meta, TOPIC, HOMEPAGE) == []


# --------------------------------------------------------------------------
# Manifest und READMEs
# --------------------------------------------------------------------------


def test_manifest_ist_lesbar_und_vollstaendig():
    manifest = load_manifest(MANIFEST_PATH)
    assert manifest["topic"] == TOPIC
    assert manifest["homepage"] == HOMEPAGE
    assert len(manifest["members"]) == 5


def test_manifest_nennt_dieses_repo():
    """Ein Manifest, das das eigene Repo auslässt, prüft die Kette von aussen
    — und übersieht ausgerechnet die Metadaten, die hier gepflegt werden."""
    repos = {m["repo"] for m in load_manifest(MANIFEST_PATH)["members"]}
    assert "malkreide/mcp-audit-skill" in repos


def test_jedes_mitglied_hat_beide_sprachfassungen():
    for member in load_manifest(MANIFEST_PATH)["members"]:
        for key in ("stage", "stage_de", "question", "question_de"):
            assert member.get(key), f"{member['repo']}: '{key}' fehlt"


def test_doppelte_mitglieder_werden_abgelehnt(tmp_path):
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    data["members"].append(dict(data["members"][0]))
    path = tmp_path / "quality-chain.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="doppelt"):
        load_manifest(path)


@pytest.mark.parametrize(
    ("readme", "heading"),
    [
        ("README.md", "The MCP quality chain"),
        ("README.de.md", "Die MCP-Qualitätskette"),
    ],
)
def test_readme_tabelle_nennt_jedes_mitglied_des_manifests(readme, heading):
    """Die Tabelle ist die menschenlesbare Fassung des Manifests.

    Kein Vergleich der Prosa — nur, dass kein Mitglied fehlt. Wer eines
    hinzufügt und die READMEs vergisst, sieht es hier statt in vier Wochen.
    """
    text = (REPO_ROOT / readme).read_text(encoding="utf-8")
    section = re.search(
        rf"^### {re.escape(heading)}\n(.*?)(?=^#{{2,3}} )", text, re.M | re.S
    )
    assert section, f"{readme}: Abschnitt '### {heading}' nicht gefunden"
    body = section.group(1)

    for member in load_manifest(MANIFEST_PATH)["members"]:
        name = member["repo"].split("/", 1)[1]
        assert name in body, f"{readme}: '{name}' fehlt in der Ketten-Tabelle"


@pytest.mark.parametrize("readme", ["README.md", "README.de.md"])
def test_readme_verlinkt_die_topic_seite(readme):
    """Die Topic-Seite ist der Einstiegspunkt, den GitHub selbst pflegt —
    ohne Link darauf ist die Kette nur eine Aufzählung."""
    text = (REPO_ROOT / readme).read_text(encoding="utf-8")
    assert HOMEPAGE in text, f"{readme}: Link auf {HOMEPAGE} fehlt"
