"""Das Paket `mcp-audit.skill` — Manifest, Bau und Check 5.

Der teuerste Fehler dieser Kette ist nicht ein kaputtes Archiv, sondern ein
STILL UNVOLLSTAENDIGES: Ein Paket ohne `checks/` sagt beim Audit nichts
Falsches, es sagt weniger und sieht dabei vollstaendig aus. Deshalb steht in
`expand()` die Regel «Muster ohne Wirkung ist ein Fehler», und deshalb ist
jeder Test hier ein MUTATIONSTEST: Er nimmt dem Baum gezielt etwas weg und
sichert zu, dass die Meldung die richtige Ursache nennt. Eine Pruefung, die
aus dem falschen Grund rot wird, ist beim naechsten Mal aus dem falschen
Grund gruen.

Gefahren wird gegen einen Fixture-Baum, nicht gegen das Repository — sonst
liesse sich «Katalog fehlt» nur pruefen, indem man den Katalog loescht.
"""

from __future__ import annotations

import pathlib
import sys
import zipfile

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import build_skill, skill_package  # noqa: E402
from tools.checks import CheckFailed  # noqa: E402
from tools.checks.skill_archive import (  # noqa: E402
    skill_archive_is_current,
    vergleiche,
)
from tools.skill_package import (  # noqa: E402
    ARCHIVE_NAME,
    MANIFEST_NAME,
    SKILL_NAME,
    ManifestError,
    expand,
    frontmatter_problems,
    member_name,
    package_files,
    parse_manifest,
)

FRONTMATTER = (
    f"---\nname: {SKILL_NAME}\ndescription: " + "x" * 200 + "\n---\n\n# Ueberschrift\n"
)


def schreibe(pfad: pathlib.Path, text: str) -> None:
    """Schreibt mit LF, auf jedem Betriebssystem.

    `Path.write_text` oeffnet im Textmodus und uebersetzt `\\n` unter Windows
    zu `\\r\\n`. Fuer diese Datei ist das kein Detail: Der Build liest BYTES,
    also verglichen die Byte-Zusicherungen unten sonst gegen etwas anderes,
    als der Fixture-Baum enthaelt — und der Test waere unter Windows rot,
    ohne dass am Bau etwas falsch ist. Genau so ist er es beim ersten Lauf
    auch gewesen.

    Der Fixture-Baum bildet damit ab, was `.gitattributes` fuer das echte
    Repository zusichert: LF im Arbeitsbaum, auf jedem Host.
    """
    pfad.write_text(text, encoding="utf-8", newline="\n")


@pytest.fixture
def tree(tmp_path: pathlib.Path) -> pathlib.Path:
    """Ein minimaler, aber vollstaendiger Skill-Baum.

    Enthaelt genau das, woran die Regeln haengen: einen Einstiegspunkt, ein
    Verzeichnis mit mehreren Dateien (steht fuer `checks/`) und ein Werkzeug,
    das ausgeschlossen werden kann.
    """
    root = tmp_path / "repo"
    (root / "checks").mkdir(parents=True)
    (root / "tools").mkdir()
    schreibe(root / "SKILL.md", FRONTMATTER)
    schreibe(root / "checks" / "ARCH-001.md", "erster\n")
    schreibe(root / "checks" / "SEC-001.md", "zweiter\n")
    schreibe(root / "tools" / "nuetzlich.py", "x = 1\n")
    schreibe(root / "tools" / "intern.py", "y = 2\n")
    schreibe(
        root / MANIFEST_NAME,
        "# Kommentar\n\nSKILL.md\nchecks/*.md\ntools/*.py\n!tools/intern.py\n",
    )
    return root


# --------------------------------------------------------------------------
# Das Manifest als Text
# --------------------------------------------------------------------------


def test_kommentare_und_leerzeilen_zaehlen_nicht_als_muster():
    ein, aus = parse_manifest("# nur Prosa\n\n   \nSKILL.md\n")
    assert ein == ["SKILL.md"]
    assert aus == []


def test_ausrufezeichen_trennt_ausschluss_von_einschluss():
    ein, aus = parse_manifest("tools/*.py\n!tools/intern.py\n")
    assert ein == ["tools/*.py"]
    assert aus == ["tools/intern.py"]


@pytest.mark.parametrize(
    ("zeile", "erwartet"),
    [
        ("/etc/passwd", "absoluter Pfad"),
        ("C:/Windows/system.ini", "absoluter Pfad"),
        ("../nachbar/SKILL.md", "verlässt das Repository"),
        ("docs\\*.md", "Backslash"),
        ("!", "ohne Muster"),
    ],
)
def test_ANKER_unbrauchbare_zeilen_sind_ein_fehler(zeile, erwartet):
    """Jede dieser Zeilen kaeme sonst als leeres Ergebnis durch.

    `docs\\*.md` ist der Fall aus der Praxis: Unter Windows getippt, passt es
    dort auf Dateien und unter Linux auf nichts — der Build in der CI wuerde
    dann mit «Muster ohne Treffer» abbrechen, also mit der falschen Ursache.
    """
    with pytest.raises(ManifestError) as befund:
        parse_manifest(f"SKILL.md\n{zeile}\n")
    assert erwartet in str(befund.value)


def test_ANKER_manifest_ohne_muster_ist_ein_fehler():
    with pytest.raises(ManifestError):
        parse_manifest("# nur Kommentare\n")


# --------------------------------------------------------------------------
# Muster gegen den Baum
# --------------------------------------------------------------------------


def test_expand_liefert_sortiert_und_doppelfrei(tree):
    ein, aus = parse_manifest((tree / MANIFEST_NAME).read_text(encoding="utf-8"))
    dateien = expand(tree, [*ein, "checks/*.md"], aus)
    assert dateien == [
        "SKILL.md",
        "checks/ARCH-001.md",
        "checks/SEC-001.md",
        "tools/nuetzlich.py",
    ]


def test_ANKER_ein_muster_ohne_treffer_bricht_ab(tree):
    """Der teuerste Fall: `checks/` umbenannt, Paket ohne Katalog.

    Ohne diese Regel lieferte `glob` eine leere Liste, der Build meldete
    Erfolg, und der Nutzer bekaeme ein Skill, das jedes Audit besteht, weil
    es nichts zu pruefen hat.
    """
    (tree / "checks" / "ARCH-001.md").unlink()
    (tree / "checks" / "SEC-001.md").unlink()
    with pytest.raises(ManifestError) as befund:
        package_files(tree)
    assert "checks/*.md" in str(befund.value)


def test_ANKER_ein_ausschluss_ohne_wirkung_bricht_ab(tree):
    """Eine Zeile, die eine Entscheidung begruendet, die nicht mehr faellt."""
    (tree / "tools" / "intern.py").unlink()
    with pytest.raises(ManifestError) as befund:
        package_files(tree)
    assert "tools/intern.py" in str(befund.value)


def test_ANKER_paket_ohne_skill_md_ist_kein_skill(tree):
    schreibe(tree / MANIFEST_NAME, "checks/*.md\n")
    with pytest.raises(ManifestError) as befund:
        package_files(tree)
    assert "SKILL.md" in str(befund.value)


def test_ANKER_fehlendes_manifest_ist_ein_fehler(tree):
    (tree / MANIFEST_NAME).unlink()
    with pytest.raises(ManifestError):
        package_files(tree)


def test_member_name_setzt_genau_eine_wurzel():
    """Ohne Wurzelverzeichnis schuettete das Archiv seinen Inhalt aus."""
    assert member_name("checks/SEC-001.md") == f"{SKILL_NAME}/checks/SEC-001.md"


# --------------------------------------------------------------------------
# Das Frontmatter — woran der Upload scheitert
# --------------------------------------------------------------------------


def test_gueltiges_frontmatter_hat_keine_beanstandung():
    assert frontmatter_problems(FRONTMATTER) == []


def test_ANKER_zu_lange_description_wird_vor_dem_upload_gefangen():
    """Sonst faellt der Fehler beim Nutzer an, nicht beim Bauen."""
    zu_lang = FRONTMATTER.replace(
        "x" * 200, "x" * (skill_package.DESCRIPTION_MAX_CHARS + 1)
    )
    probleme = frontmatter_problems(zu_lang)
    assert probleme
    assert str(skill_package.DESCRIPTION_MAX_CHARS) in probleme[0]


def test_ANKER_zu_kurze_description_loest_den_skill_nicht_aus():
    probleme = frontmatter_problems(FRONTMATTER.replace("x" * 200, "kurz"))
    assert probleme and "zu wenig" in probleme[0]


def test_ANKER_falscher_name_wuerde_das_archiv_anders_benennen():
    probleme = frontmatter_problems(FRONTMATTER.replace(SKILL_NAME, "mcp-audit-skill"))
    assert probleme and SKILL_NAME in probleme[0]


def test_ANKER_fehlendes_frontmatter_ist_ein_befund():
    assert frontmatter_problems("# Ohne Kopf\n")


def test_das_echte_SKILL_md_besteht_das_frontmatter():
    """Die eine Stelle, an der dieser Test das Repository selbst befragt."""
    text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert frontmatter_problems(text) == []


# --------------------------------------------------------------------------
# Der Bau
# --------------------------------------------------------------------------


def test_build_schreibt_genau_die_dateien_aus_dem_manifest(tree):
    ziel = tree / ARCHIVE_NAME
    dateien = build_skill.build(tree, ziel)
    with zipfile.ZipFile(ziel) as zf:
        assert sorted(zf.namelist()) == sorted(member_name(d) for d in dateien)
        assert zf.read(member_name("checks/SEC-001.md")) == b"zweiter\n"
    assert f"{SKILL_NAME}/tools/intern.py" not in zipfile.ZipFile(ziel).namelist()


def test_der_build_ist_bit_identisch_reproduzierbar(tree):
    """Ohne diese Zusage waere Check 5 nicht entscheidbar.

    Der Zeitstempel jeder Datei wird zwischen den beiden Laeufen veraendert:
    Genau das ist der Unterschied, den ein Auschecken erzeugt, und genau der
    darf im Archiv nicht ankommen.
    """
    erst = build_skill.build(tree, tree / "a.skill") and (tree / "a.skill").read_bytes()
    for pfad in tree.rglob("*"):
        if pfad.is_file():
            pfad.touch()
    build_skill.build(tree, tree / "b.skill")
    assert erst == (tree / "b.skill").read_bytes()


def test_ANKER_build_mit_kaputtem_frontmatter_bricht_ab(tree):
    schreibe(tree / "SKILL.md", "# ohne Kopf\n")
    with pytest.raises(ManifestError):
        build_skill.build(tree, tree / ARCHIVE_NAME)


def test_ein_abgebrochener_build_hinterlaesst_kein_halbes_archiv(tree):
    """Sonst ginge die Ruine anschliessend als «gebaut» durch."""
    ziel = tree / ARCHIVE_NAME
    schreibe(tree / "SKILL.md", "# ohne Kopf\n")
    with pytest.raises(ManifestError):
        build_skill.build(tree, ziel)
    assert not ziel.exists()
    assert not list(tree.glob("*.part"))


# --------------------------------------------------------------------------
# Check 5 — die reine Urteilsfunktion und die Verdrahtung
# --------------------------------------------------------------------------


def test_vergleiche_ist_gruen_bei_gleichem_inhalt():
    ok, meldung = vergleiche({"a": b"1"}, {"a": b"1"})
    assert ok
    assert "1 Eintraege" in meldung


@pytest.mark.parametrize(
    ("erwartet", "vorhanden", "ursache"),
    [
        ({"a": b"1", "b": b"2"}, {"a": b"1"}, "fehlen im Archiv"),
        ({"a": b"1"}, {"a": b"1", "b": b"2"}, "nicht im Manifest"),
        ({"a": b"1"}, {"a": b"2"}, "weichen vom Archiv ab"),
    ],
)
def test_vergleiche_nennt_bei_jeder_abweichung_ihre_eigene_ursache(
    erwartet, vorhanden, ursache
):
    """Drei Abweichungen, drei Ursachen — ein gemeinsames «veraltet» schickte
    bei einer geloeschten Datei an dieselbe Stelle wie bei einer geaenderten.
    """
    ok, meldung = vergleiche(erwartet, vorhanden)
    assert not ok
    assert ursache in meldung


def test_check5_ist_gruen_am_frisch_gebauten_baum(tree):
    build_skill.build(tree, tree / ARCHIVE_NAME)
    assert "alle aktuell" in skill_archive_is_current(tree)


def test_ANKER_check5_wird_rot_wenn_eine_quelle_sich_aendert(tree):
    """Der Fall, gegen den Check 5 geschrieben ist: Katalog waechst, Archiv
    nicht. Ohne die Pruefung ginge das Release mit dem alten Paket raus.
    """
    build_skill.build(tree, tree / ARCHIVE_NAME)
    schreibe(tree / "checks" / "SEC-001.md", "geaendert\n")
    with pytest.raises(CheckFailed) as befund:
        skill_archive_is_current(tree)
    assert "weichen vom Archiv ab" in str(befund.value)
    assert "build-skill.sh" in str(befund.value)


def test_ANKER_check5_wird_rot_wenn_eine_neue_datei_fehlt(tree):
    build_skill.build(tree, tree / ARCHIVE_NAME)
    schreibe(tree / "checks" / "SEC-002.md", "neu\n")
    with pytest.raises(CheckFailed) as befund:
        skill_archive_is_current(tree)
    assert "fehlen im Archiv" in str(befund.value)


def test_ANKER_check5_wird_rot_ohne_archiv(tree):
    with pytest.raises(CheckFailed) as befund:
        skill_archive_is_current(tree)
    assert ARCHIVE_NAME in str(befund.value)


def test_ANKER_check5_wird_rot_bei_kaputtem_archiv(tree):
    schreibe(tree / ARCHIVE_NAME, "kein ZIP")
    with pytest.raises(CheckFailed) as befund:
        skill_archive_is_current(tree)
    assert "ZIP" in str(befund.value)
