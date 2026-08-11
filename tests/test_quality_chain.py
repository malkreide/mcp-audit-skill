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
from pathlib import Path

import pytest

from tools.check_quality_chain import (
    MISSING,
    compare,
    fix_commands,
    load_manifest,
)
from tools.suites.mcp_audit.skill_doc import CHAIN_SECTIONS

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
    assert len(manifest["members"]) == 4


def test_ANKER_mitglied_ist_ein_skill_und_nicht_ein_repo():
    """Der Entscheid, den Phase 3 umgesetzt hat.

    Vorher waren Mitglied und Repo dasselbe, weil jeder Skill sein eigenes
    Repository hatte. Seit dem Einzug liegen drei davon hier — an einem
    Repo-Namen laesst sich die Mitgliedschaft nicht mehr ablesen.
    """
    members = load_manifest(MANIFEST_PATH)["members"]
    assert all("skill" in m for m in members)
    assert not any("repo" in m for m in members), (
        "Ein Mitglied traegt noch 'repo'. Die Kette zaehlt Skills; wessen "
        "GitHub-Metadaten geprueft werden, steht in 'repos'."
    )


def test_ANKER_jedes_mitglied_zeigt_auf_eine_echte_skill_md():
    """Das Manifest gegen den Baum, nicht gegen eine Annahme.

    `path` ist der Grund, warum diese Pruefung ueberhaupt moeglich ist: Ein
    Mitglied, dessen Verzeichnis niemand mehr pflegt, faellt hier auf und
    nicht erst, wenn jemand den Skill installieren will.
    """
    for member in load_manifest(MANIFEST_PATH)["members"]:
        skill_md = REPO_ROOT / member["path"] / "SKILL.md"
        assert skill_md.is_file(), f"{member['skill']}: {skill_md} fehlt"
        kopf = skill_md.read_text(encoding="utf-8")[:400]
        assert f"name: {member['skill']}" in kopf, (
            f"{member['skill']}: Frontmatter-name in {skill_md} weicht ab — "
            "daran haengt, ob Claude den Skill ueberhaupt zieht."
        )


def test_manifest_nennt_dieses_repo():
    """Ein Manifest, das das eigene Repo auslässt, prüft die Kette von aussen
    — und übersieht ausgerechnet die Metadaten, die hier gepflegt werden."""
    assert "malkreide/mcp-audit-skill" in load_manifest(MANIFEST_PATH)["repos"]


def test_ANKER_der_auditor_traegt_die_kette_ohne_mitglied_zu_sein():
    """Er ist kein Skill, sondern die Laufzeit, die die Kette faehrt.

    Trotzdem gehoeren seine Metadaten geprueft: Ohne gemeinsames Topic ist die
    Gruppe auf GitHub genau dort unsichtbar, wo jemand sie sucht.
    """
    manifest = load_manifest(MANIFEST_PATH)
    assert "malkreide/mcp-continuous-auditor" in manifest["repos"]
    assert "mcp-continuous-auditor" not in {m["skill"] for m in manifest["members"]}


def test_jedes_mitglied_hat_beide_sprachfassungen():
    for member in load_manifest(MANIFEST_PATH)["members"]:
        for key in ("stage", "stage_de", "question", "question_de"):
            assert member.get(key), f"{member['skill']}: '{key}' fehlt"


def test_doppelte_mitglieder_werden_abgelehnt(tmp_path):
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    data["members"].append(dict(data["members"][0]))
    path = tmp_path / "quality-chain.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="doppelt"):
        load_manifest(path)


def test_doppelte_repos_werden_abgelehnt(tmp_path):
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    data["repos"].append(data["repos"][0])
    path = tmp_path / "quality-chain.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="doppelt"):
        load_manifest(path)


def test_ANKER_jede_companion_datei_mit_kettentabelle_steht_in_chain_sections():
    """Die Bindung selbst, gegen den Baum gehalten.

    `audit/12` prueft nur, was in `CHAIN_SECTIONS` steht. Eine vierte
    Companion-README — oder eine dritte Sprachfassung — waere damit still
    ungeprueft, und die Tabelle darin duerfte veralten, waehrend der Lauf
    gruen meldet. Genau das ist zwischen 2b-iv-a und 2b-iv-c passiert: Die
    drei Herkunfts-Pruefungen waren nach `audit/12` absorbiert, `audit/12`
    las aber nur die beiden READMEs der Wurzel, und die sechs
    Companion-Tabellen beschrieben in dieser Zeit noch fuenf Repositories.
    """
    gefuehrt = {datei for datei, _ in CHAIN_SECTIONS}
    vorhanden = {
        pfad.relative_to(REPO_ROOT).as_posix()
        for muster in ("skills/*/README*.md", "skills/*/SKILL.md")
        for pfad in sorted(REPO_ROOT.glob(muster))
    }
    assert vorhanden, "keine Companion-Datei gefunden — dann prueft dieser Test nichts"
    fehlend = sorted(vorhanden - gefuehrt)
    assert not fehlend, (
        f"Diese Dateien fuehren eine Ketten-Tabelle, stehen aber nicht in "
        f"CHAIN_SECTIONS: {fehlend}. Ihre Tabelle darf damit veralten, ohne "
        "dass etwas rot wird."
    )


@pytest.mark.parametrize(
    ("readme", "heading"),
    CHAIN_SECTIONS,
    ids=lambda wert: wert if wert.endswith(".md") else "",
)
def test_readme_tabelle_nennt_jedes_mitglied_des_manifests(readme, heading):
    """Die Tabelle ist die menschenlesbare Fassung des Manifests.

    Kein Vergleich der Prosa — nur, dass kein Mitglied fehlt. Wer eines
    hinzufügt und die READMEs vergisst, sieht es hier statt in vier Wochen.
    """
    # EINE IMPLEMENTIERUNG, ZWEI EINSTIEGE. Seit Phase 2b-iii steht die Logik
    # in `tools/gates/readmes.py` und laeuft als `audit/12` im Gate-Lauf.
    # Dieser Test ruft dieselbe Funktion — er ist der zweite Einstieg, nicht
    # eine zweite Fassung. Vorher waren es zwei: hier ein pytest, in den drei
    # Schwesterrepos je ein Check mit eigener, hart gefuehrter Namensliste.
    from tools.gates.readmes import chain_table

    assert chain_table(REPO_ROOT, sections=((readme, heading),))


@pytest.mark.parametrize("readme", ["README.md", "README.de.md"])
def test_readme_verlinkt_die_topic_seite(readme):
    """Die Topic-Seite ist der Einstiegspunkt, den GitHub selbst pflegt —
    ohne Link darauf ist die Kette nur eine Aufzählung."""
    text = (REPO_ROOT / readme).read_text(encoding="utf-8")
    assert HOMEPAGE in text, f"{readme}: Link auf {HOMEPAGE} fehlt"
