"""Die generischen Gates `hygiene` und `references` (G7 bis G9).

Der Gegenstand ist derselbe wie bei den uebrigen Gates: Was durch die
Zusammenfuehrung neu ist. Bei G7 ist das die VEREINIGUNG der beiden Muster —
probes Regex und transports Tupel fanden je etwas, das dem anderen entging.
Bei G8 und G9 ist es die Parametrisierung: Liste und Verzeichnisse kamen aus
einer festen Konstante und sind jetzt Argument.

Dazu, quer durch: dass ein LEERER Gegenstand ein Befund ist und kein Erfolg.
Eine Liste ohne Eintraege, ein Verzeichnis ohne Vorlagen — beides pruefte
nichts und meldete genau das als bestanden.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gates import hygiene as gates  # noqa: E402
from tools.gates import references as ref_gates  # noqa: E402
from tools.harness import CheckFailed  # noqa: E402

# --------------------------------------------------------------------------
# G7 — kein Bytecode im Index
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pfad",
    [
        "__pycache__/x.cpython-311.pyc",
        "tools/__pycache__/y.pyc",
        "a.pyc",
        "a.pyo",
        "a.pyd",
    ],
)
def test_ANKER_das_vereinigte_muster_faengt_beide_fassungen(pfad):
    """probes Regex kannte `.pyd` nicht, transports Tupel fand `__pycache__/`
    am Pfadanfang nicht. Zusammen decken sie beides ab — und das ist der
    einzige inhaltliche Gewinn dieser Zusammenlegung."""
    assert gates.COMPILED.search(pfad), pfad


@pytest.mark.parametrize("pfad", ["a.py", "pycache/a.txt", "notes.pydantic.md"])
def test_das_muster_faengt_nichts_harmloses(pfad):
    assert not gates.COMPILED.search(pfad)


def test_ANKER_kein_git_repo_ist_ein_befund_kein_uebersprungen(tmp_path):
    """«Nicht gelaufen» als «bestanden» zu melden ist die eine Auskunft, die
    schlimmer ist als keine."""
    with pytest.raises(CheckFailed) as befund:
        gates.no_compiled_python(tmp_path)
    assert "git ls-files" in str(befund.value)


def _git_baum(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def test_ein_sauberer_index_ist_gruen(tmp_path):
    root = _git_baum(tmp_path)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "a.py"], check=True)
    assert gates.no_compiled_python(root)


def test_getrackter_bytecode_ist_ein_befund_mit_dem_namen(tmp_path):
    root = _git_baum(tmp_path)
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "a.pyc").write_bytes(b"\x00")
    subprocess.run(
        ["git", "-C", str(root), "add", "-f", "__pycache__/a.pyc"], check=True
    )
    with pytest.raises(CheckFailed) as befund:
        gates.no_compiled_python(root)
    text = str(befund.value)
    assert "__pycache__/a.pyc" in text
    # Ein Befund soll sagen, wie er zu beheben ist.
    assert "git rm --cached" in text


# --------------------------------------------------------------------------
# G8 — die referenzierten Dateien
# --------------------------------------------------------------------------


def test_ANKER_eine_leere_liste_ist_ein_befund(tmp_path):
    """Sonst pruefte diese Pruefung nichts und meldete genau das als Erfolg."""
    with pytest.raises(CheckFailed) as befund:
        gates.referenced_files_exist(tmp_path, files=())
    assert "leer" in str(befund.value)


def test_eine_fehlende_datei_wird_beim_namen_genannt(tmp_path):
    (tmp_path / "da.md").write_text("x", encoding="utf-8")
    with pytest.raises(CheckFailed) as befund:
        gates.referenced_files_exist(tmp_path, files=("da.md", "weg.md"))
    assert "weg.md" in str(befund.value)
    assert "da.md" not in str(befund.value)


def test_ein_verzeichnis_zaehlt_nicht_als_datei(tmp_path):
    """`is_file()` und nicht `exists()`: Ein Verzeichnis gleichen Namens
    erfuellt die Zusage nicht, auf die jemand verlinkt hat."""
    (tmp_path / "templates").mkdir()
    with pytest.raises(CheckFailed):
        gates.referenced_files_exist(tmp_path, files=("templates",))


def test_die_meldung_nennt_die_zahl(tmp_path):
    for name in ("a.md", "b.md"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert "2" in gates.referenced_files_exist(tmp_path, files=("a.md", "b.md"))


# --------------------------------------------------------------------------
# G9 — die Vorlagen lassen sich uebersetzen
# --------------------------------------------------------------------------


@pytest.fixture
def vorlagen(tmp_path):
    (tmp_path / "reference").mkdir()
    (tmp_path / "reference" / "muster.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


def test_ANKER_ein_fehlendes_verzeichnis_ist_ein_befund(tmp_path):
    with pytest.raises(CheckFailed) as befund:
        ref_gates.python_syntax(tmp_path, source_dirs=("reference",))
    assert "fehlt" in str(befund.value)


def test_ANKER_ein_verzeichnis_ohne_vorlagen_ist_ein_befund(tmp_path):
    """Ein leeres Ergebnis als Erfolg zu melden ist der Fehler, gegen den
    diese Pruefung gerichtet ist."""
    (tmp_path / "reference").mkdir()
    with pytest.raises(CheckFailed) as befund:
        ref_gates.python_syntax(tmp_path, source_dirs=("reference",))
    assert "Kein `*.py`" in str(befund.value)


def test_ANKER_ohne_verzeichnisangabe_wird_nichts_geprueft(tmp_path):
    with pytest.raises(CheckFailed) as befund:
        ref_gates.python_syntax(tmp_path, source_dirs=())
    assert "Kein Verzeichnis" in str(befund.value)


def test_ein_syntaxfehler_wird_mit_zeile_gemeldet(vorlagen):
    (vorlagen / "reference" / "kaputt.py").write_text("def (\n", encoding="utf-8")
    with pytest.raises(CheckFailed) as befund:
        ref_gates.python_syntax(vorlagen, source_dirs=("reference",))
    text = str(befund.value)
    assert "kaputt.py" in text
    assert "Zeile" in text


def test_undefinierte_namen_sind_KEIN_befund(vorlagen):
    """Die Grenze dieser Pruefung, und sie ist Absicht.

    Vorlagen-Code referenziert Namen, die erst im Zielserver existieren. Ein
    Import fiele darueber — zu Recht, aber nicht als Aussage ueber die
    Vorlage. `compile()` prueft die Syntax und sonst nichts.
    """
    (vorlagen / "reference" / "vorlage.py").write_text(
        "def handler():\n    return log.info(ctx)\n", encoding="utf-8"
    )
    assert ref_gates.python_syntax(vorlagen, source_dirs=("reference",))


def test_mehrere_verzeichnisse_werden_zusammen_gezaehlt(tmp_path):
    for name in ("a", "b"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "m.py").write_text("x = 1\n", encoding="utf-8")
    assert "2" in ref_gates.python_syntax(tmp_path, source_dirs=("a", "b"))


def test_private_module_bleiben_aussen_vor(vorlagen):
    """`_`-Praefix ist die Konvention der Sonden aus `gates/ruff.py`. Eine
    liegengebliebene Sonde soll diese Pruefung nicht mitzaehlen."""
    (vorlagen / "reference" / "_sonde.py").write_text("x = (\n", encoding="utf-8")
    assert ref_gates.python_syntax(vorlagen, source_dirs=("reference",))
