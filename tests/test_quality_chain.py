"""Tests für den Qualitätsketten-Guard und für die Ketten-Tabelle in den READMEs.

Zwei Dinge werden hier geprüft, und sie liegen bewusst in einer Datei, weil sie
dieselbe Frage von zwei Seiten stellen: Steht die Zugehörigkeit überall gleich?

* Die **reine** Seite des Guards — `compare()`, `fix_commands()`,
  `compare_carriers()` und `carrier_fix_commands()` bekommen ihre Daten
  übergeben. Die Netzaufrufe (`fetch()`, `fetch_carriers()`) werden bewusst
  *nicht* gemockt: Ein Mock bildete nur die eigene Annahme über die
  GitHub-Antwort ab und könnte sie nie widerlegen — die Grenze, an der
  `DRIFT-004` ansetzt.

* Das **Manifest gegen die READMEs**. Die Kette steht an mehreren Orten in
  diesem Repo — `docs/quality-chain.json`, `README.md`, `README.de.md`, dazu
  die Ketten-Tabellen unter `skills/`. Sie sind alle erreichbar, also werden
  sie erzwungen.

Seit der Zusammenführung stellt der Guard die Frage in BEIDE Richtungen, und
die zweite hat einen eigenen Abschnitt weiter unten: Wer trägt das Topic, ohne
im Manifest zu stehen? Die Summary-Stufe des Workflows liegt daneben in
`test_quality_chain_workflow.py` — sie las eine Woche lang ein Schema, das es
nicht mehr gab.

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
    carrier_fix_commands,
    compare,
    compare_carriers,
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
# compare_carriers() — die andere Richtung
# --------------------------------------------------------------------------
#
# `compare()` fragt: Trägt jedes Repo aus dem Manifest das Topic? Diese Hälfte
# fragt das Gegenteil: Trägt jemand das Topic, der NICHT im Manifest steht?
#
# Der Anlass ist gemessen. Nach der Zusammenführung wurden die drei
# Herkunftsrepos archiviert — und ein archiviertes Repo behält seine Topics.
# Der Wächter war grün, das Manifest richtig, und die Topic-Seite zeigte
# weiterhin fünf Einträge, wo zwei gelten. Es gab keinen Test, den das rot
# machen konnte, weil die Frage nie gestellt wurde.

DECLARED = ["malkreide/mcp-audit-skill", "malkreide/mcp-continuous-auditor"]


def _carrier(name, archived=False):
    return {"full_name": name, "archived": archived}


def _alle_deklarierten():
    return [_carrier(name) for name in DECLARED]


def test_nur_deklarierte_traeger_sind_kein_befund():
    assert compare_carriers(_alle_deklarierten(), DECLARED, TOPIC) == []


def test_ein_ueberzaehliger_traeger_wird_gemeldet():
    carriers = [*_alle_deklarierten(), _carrier("malkreide/mcp-data-fidelity-skill")]
    problems = compare_carriers(carriers, DECLARED, TOPIC)
    assert len(problems) == 1
    assert "mcp-data-fidelity-skill" in problems[0]
    assert problems[0].startswith("Überzählig:")


def test_ein_archivierter_traeger_wird_als_solcher_benannt():
    """Der Zusatz ist kein Schmuck: Er sagt, warum das Aufräumen zwei
    Handgriffe mehr braucht — siehe `carrier_fix_commands`."""
    carriers = [*_alle_deklarierten(), _carrier("malkreide/alt-skill", archived=True)]
    problems = compare_carriers(carriers, DECLARED, TOPIC)
    assert len(problems) == 1
    assert "(archiviert)" in problems[0]


def test_grossschreibung_macht_kein_repo_ueberzaehlig():
    """GitHub vergleicht Repo-Namen ohne Rücksicht auf Gross-/Kleinschreibung;
    täte diese Funktion es nicht, wäre `Malkreide/…` ein erfundener Befund."""
    carriers = [_carrier("Malkreide/MCP-Audit-Skill")]
    assert compare_carriers(carriers, DECLARED, TOPIC) == []


def test_ANKER_ein_leeres_ergebnis_ist_ein_befund_und_kein_bestehen():
    """Die deklarierten Repos TRAGEN das Topic — das steht über die Repo-API
    fest. Findet die Suche daraufhin gar nichts, hat nicht der Bestand
    gestimmt, sondern der Index hat nicht geantwortet.

    Ohne diesen Test wäre der bequeme Weg — leere Liste, keine Schleife, keine
    Befunde, «sauber» — von der richtigen Antwort nicht zu unterscheiden.
    """
    problems = compare_carriers([], DECLARED, TOPIC)
    assert len(problems) == 1
    assert problems[0].startswith("UNVERIFIED:")
    assert "kein Bestehen" in problems[0]


def test_eine_gekappte_trefferliste_sagt_es():
    carriers = [*_alle_deklarierten(), _carrier("malkreide/fremd")]
    problems = compare_carriers(carriers, DECLARED, TOPIC, total_count=42)
    assert any(p.startswith("UNVERIFIED:") and "42" in p for p in problems)
    # Der Überzählige wird trotzdem gemeldet: unvollständig ist nicht nichts.
    assert any(p.startswith("Überzählig:") for p in problems)


@pytest.mark.parametrize("total", [2, None])
def test_eine_vollstaendige_trefferliste_meldet_keine_kappung(total):
    problems = compare_carriers(
        _alle_deklarierten(), DECLARED, TOPIC, total_count=total
    )
    assert problems == []


def test_ein_treffer_ohne_namen_ist_unverified():
    """Nicht zuzuordnen heisst nicht sauber — sonst zählte eine kaputte
    Antwort als bestandener Vergleich."""
    carriers = [*_alle_deklarierten(), _carrier(None)]
    problems = compare_carriers(carriers, DECLARED, TOPIC)
    assert len(problems) == 1
    assert problems[0].startswith("UNVERIFIED:")


def test_mehrere_ueberzaehlige_werden_alle_gemeldet():
    fremd = ["malkreide/a", "malkreide/b", "malkreide/c"]
    carriers = [*_alle_deklarierten(), *(_carrier(n) for n in fremd)]
    problems = compare_carriers(carriers, DECLARED, TOPIC)
    assert len(problems) == 3
    for name in fremd:
        assert any(name in p for p in problems)


# --------------------------------------------------------------------------
# carrier_fix_commands() — auch hier schreibt der Guard nicht
# --------------------------------------------------------------------------


def test_ohne_ueberzaehlige_gibt_es_kein_kommando():
    assert carrier_fix_commands(_alle_deklarierten(), DECLARED, TOPIC) == []


def test_kommando_fuer_einen_gewoehnlichen_traeger():
    carriers = [_carrier("malkreide/fremd")]
    commands = carrier_fix_commands(carriers, DECLARED, TOPIC)
    assert commands == [f"gh repo edit malkreide/fremd --remove-topic {TOPIC}"]


def test_ANKER_ein_archivierter_traeger_braucht_das_paar_drumherum():
    """Ein archiviertes Repository ist schreibgeschützt — `--remove-topic`
    allein läuft dort ins Leere. Stünde hier nur das eine Kommando, merkte das
    erst, wer es ausführt, und zwar an einer Fehlermeldung."""
    carriers = [_carrier("malkreide/alt-skill", archived=True)]
    commands = carrier_fix_commands(carriers, DECLARED, TOPIC)
    assert len(commands) == 1
    assert "gh repo unarchive malkreide/alt-skill" in commands[0]
    assert f"--remove-topic {TOPIC}" in commands[0]
    assert "gh repo archive malkreide/alt-skill" in commands[0]


def test_das_manifest_taugt_als_vergleichsliste():
    """Die Verbindung zwischen Manifest und dieser Prüfung — ohne sie könnte
    `repos` umbenannt werden, ohne dass hier etwas rot wird."""
    manifest = load_manifest(MANIFEST_PATH)
    fremd = [_carrier(name) for name in manifest["repos"]]
    fremd.append(_carrier("malkreide/nicht-im-manifest"))
    problems = compare_carriers(fremd, manifest["repos"], manifest["topic"])
    assert len(problems) == 1
    assert "nicht-im-manifest" in problems[0]


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
        for muster in (
            "README*.md",
            "SKILL.md",
            "skills/*/README*.md",
            "skills/*/SKILL.md",
        )
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
