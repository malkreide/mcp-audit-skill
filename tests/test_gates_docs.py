"""Die generischen Gates `skill_doc` und `readmes` (G10 bis G12).

Was durch die Zusammenfuehrung neu ist:

* bei G10 die Parametrisierung — Pfad, erwarteter Name und Grenze kamen aus
  drei festen Konstanten und sind jetzt Argument;
* bei G11 der `base`-Parameter, ohne den ein Monorepo mit vier CHANGELOGs
  nicht pruefbar waere;
* bei G12 die QUELLE der Mitgliederliste. Sie stand dreimal als harte Liste im
  Pruefcode; jetzt kommt sie aus `docs/quality-chain.json`. Eine Tabelle gegen
  eine Liste zu halten, die ihrerseits veralten kann, prueft nur, ob zwei
  Kopien dieselbe Unwahrheit sagen.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gates import readmes as readme_gates  # noqa: E402
from tools.gates import skill_doc as gates  # noqa: E402
from tools.harness import CheckFailed  # noqa: E402


def schreibe_skill(root: pathlib.Path, name: str, description: str) -> None:
    (root / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# Titel\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------
# G10 — Frontmatter
# --------------------------------------------------------------------------


def test_ein_gesundes_frontmatter_nennt_den_verbleibenden_spielraum(tmp_path):
    """Die Grenze ist nah genug, dass eine ergaenzte Wendung sie in einer
    Bearbeitung reisst. Wer die Zahl sieht, merkt es vorher."""
    schreibe_skill(tmp_path, "mcp-audit", "kurz")
    meldung = gates.frontmatter(
        tmp_path, skill_path="SKILL.md", expected_name="mcp-audit"
    )
    assert "1024" in meldung
    assert "frei" in meldung


def test_ANKER_der_erwartete_name_ist_wirklich_ein_parameter(tmp_path):
    """Vier Skills, vier Namen, eine Implementierung — sonst waere die
    Zusammenlegung eine Umbenennung statt einer Vereinigung."""
    schreibe_skill(tmp_path, "mcp-data-fidelity", "kurz")
    assert gates.frontmatter(
        tmp_path, skill_path="SKILL.md", expected_name="mcp-data-fidelity"
    )
    with pytest.raises(CheckFailed) as befund:
        gates.frontmatter(tmp_path, skill_path="SKILL.md", expected_name="mcp-audit")
    assert "mcp-audit" in str(befund.value)


def test_eine_zu_lange_description_ist_ein_befund(tmp_path):
    schreibe_skill(tmp_path, "x", "a" * 50)
    with pytest.raises(CheckFailed) as befund:
        gates.frontmatter(tmp_path, skill_path="SKILL.md", expected_name="x", limit=40)
    assert "abgeschnitten" in str(befund.value)


def test_ANKER_ein_fehlendes_frontmatter_ist_ein_befund(tmp_path):
    """«Nicht gelaufen» als «bestanden» zu melden ist die eine Auskunft, die
    schlimmer ist als keine."""
    (tmp_path / "SKILL.md").write_text("# Kein Frontmatter\n", encoding="utf-8")
    with pytest.raises(CheckFailed) as befund:
        gates.frontmatter(tmp_path, skill_path="SKILL.md", expected_name="x")
    assert "Frontmatter" in str(befund.value)


def test_eine_fehlende_datei_ist_ein_befund(tmp_path):
    with pytest.raises(CheckFailed) as befund:
        gates.frontmatter(tmp_path, skill_path="SKILL.md", expected_name="x")
    assert "fehlt" in str(befund.value)


def test_der_pfad_ist_ein_parameter(tmp_path):
    """Im Monorepo liegt je Skill eine eigene SKILL.md unter `skills/<name>/`."""
    unter = tmp_path / "skills" / "irgendwas"
    unter.mkdir(parents=True)
    schreibe_skill(unter, "mcp-transport-hardening", "kurz")
    assert gates.frontmatter(
        tmp_path,
        skill_path="skills/irgendwas/SKILL.md",
        expected_name="mcp-transport-hardening",
    )


# --------------------------------------------------------------------------
# G11 — Versions-Badge
# --------------------------------------------------------------------------


def baum_mit_badge(root: pathlib.Path, badge: str, release: str = "1.7.0") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [Unreleased]\n\n## [v{release}] — 2026-01-01\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"![Version](https://img.shields.io/badge/version-{badge}-blue)\n",
        encoding="utf-8",
    )


def test_ein_passendes_badge_ist_gruen(tmp_path):
    baum_mit_badge(tmp_path, "1.7.0")
    assert "1.7.0" in readme_gates.version_badge(tmp_path)


def test_ANKER_unreleased_wird_uebersprungen(tmp_path):
    """`[Unreleased]` traegt keine Versionsnummer — deshalb steht die Version
    im Muster und nicht im Klammerinhalt."""
    baum_mit_badge(tmp_path, "1.7.0")
    _, heading, version = readme_gates.top_release(tmp_path)
    assert version == "1.7.0"
    assert "Unreleased" not in heading


def test_ein_veraltetes_badge_ist_ein_befund(tmp_path):
    baum_mit_badge(tmp_path, "1.6.0")
    with pytest.raises(CheckFailed) as befund:
        readme_gates.version_badge(tmp_path)
    text = str(befund.value)
    assert "1.6.0" in text and "1.7.0" in text


def test_ANKER_ein_fehlendes_badge_ist_ein_befund(tmp_path):
    """Anker weg heisst: Diese Pruefung wuerde aufhoeren zu pruefen."""
    baum_mit_badge(tmp_path, "1.7.0")
    (tmp_path / "README.md").write_text("ohne Badge\n", encoding="utf-8")
    with pytest.raises(CheckFailed) as befund:
        readme_gates.version_badge(tmp_path)
    assert "kein Versions-Badge" in str(befund.value)


def test_ANKER_der_base_parameter_traegt_das_monorepo(tmp_path):
    """Vier Skills, vier CHANGELOGs, vier Badge-Saetze — ohne `base` waere im
    Monorepo nur einer davon pruefbar."""
    baum_mit_badge(tmp_path / "skills" / "a", "1.7.0")
    baum_mit_badge(tmp_path / "skills" / "b", "2.0.0", release="2.0.0")
    assert "1.7.0" in readme_gates.version_badge(tmp_path, base="skills/a")
    assert "2.0.0" in readme_gates.version_badge(tmp_path, base="skills/b")


def test_ohne_readme_ist_es_ein_befund(tmp_path):
    baum_mit_badge(tmp_path, "1.7.0")
    (tmp_path / "README.md").unlink()
    with pytest.raises(CheckFailed) as befund:
        readme_gates.version_badge(tmp_path)
    assert "keine README" in str(befund.value)


# --------------------------------------------------------------------------
# G12 — die Ketten-Tabelle
# --------------------------------------------------------------------------


def baum_mit_kette(root: pathlib.Path, *, tabelle: str, mitglieder: list[str]) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "quality-chain.json").write_text(
        json.dumps({"members": [{"skill": m} for m in mitglieder]}),
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"## Vorher\n\n### Die Kette\n\n{tabelle}\n\n## Nachher\n", encoding="utf-8"
    )


SECTIONS = (("README.md", "Die Kette"),)


def test_eine_vollstaendige_tabelle_ist_gruen(tmp_path):
    baum_mit_kette(tmp_path, tabelle="| a | b |", mitglieder=["a", "b"])
    assert "2" in readme_gates.chain_table(tmp_path, sections=SECTIONS)


def test_ANKER_die_mitglieder_kommen_aus_dem_manifest(tmp_path):
    """Der eigentliche Gewinn dieser Zusammenlegung.

    In den Herkunftsrepos stand die Liste dreimal als Konstante im Pruefcode.
    Eine Tabelle gegen eine Kopie zu halten prueft nur, ob beide dieselbe
    Unwahrheit sagen — deshalb liest diese Pruefung `quality-chain.json`.
    """
    baum_mit_kette(tmp_path, tabelle="| a |", mitglieder=["a"])
    assert readme_gates.chain_table(tmp_path, sections=SECTIONS)

    # Ein Mitglied kommt dazu, die Tabelle bleibt — jetzt muss es rot werden.
    baum_mit_kette(tmp_path, tabelle="| a |", mitglieder=["a", "neu"])
    with pytest.raises(CheckFailed) as befund:
        readme_gates.chain_table(tmp_path, sections=SECTIONS)
    assert "neu" in str(befund.value)


def test_ANKER_eine_fehlende_ueberschrift_ist_ein_befund(tmp_path):
    """Ohne Anker wuerde diese Pruefung stillschweigend aufhoeren zu pruefen."""
    baum_mit_kette(tmp_path, tabelle="| a |", mitglieder=["a"])
    (tmp_path / "README.md").write_text("### Anders benannt\n\n| a |\n", "utf-8")
    with pytest.raises(CheckFailed) as befund:
        readme_gates.chain_table(tmp_path, sections=SECTIONS)
    assert "nicht gefunden" in str(befund.value)


def test_ein_leeres_manifest_ist_ein_befund(tmp_path):
    baum_mit_kette(tmp_path, tabelle="| a |", mitglieder=[])
    with pytest.raises(CheckFailed) as befund:
        readme_gates.chain_table(tmp_path, sections=SECTIONS)
    assert "leer" in str(befund.value)


def test_ein_fehlendes_manifest_ist_ein_befund(tmp_path):
    (tmp_path / "README.md").write_text("### Die Kette\n\n| a |\n", encoding="utf-8")
    with pytest.raises(CheckFailed) as befund:
        readme_gates.chain_table(tmp_path, sections=SECTIONS)
    assert "fehlt" in str(befund.value)
