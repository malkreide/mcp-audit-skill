"""`tools/sweeps/cp1252_sweep.py` — Leseliste zu `OPS-005`, Modus 5.

Gefahren wird der Sweep über seine Kommandozeile gegen Wegwerf-Repos in
`tmp_path`, und seine Ausgabe geht IMMER in einen strikten cp1252-Strom: Ein
Werkzeug, das diesen Fehler sucht und ihn selbst hat, soll an jedem dieser
Tests fallen. Als eigener Prozess läuft er nur dort, wo es um die echte
Kodierung der Laufzeit geht.

Die Zeichen stehen hier als `chr(...)` und nicht als Literal. Was in einer
Beispieldatei steht, ist damit an genau einer Stelle entschieden.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.sweeps import cp1252_sweep  # noqa: E402

SWEEP = REPO_ROOT / "tools" / "sweeps" / "cp1252_sweep.py"

PFEIL = chr(0x2192)
HAKEN = chr(0x2713)
#: Ausserhalb der BMP: Als JSON-Escape wäre es ein Surrogatpaar.
ROBOTER = chr(0x1F916)
#: In cp1252 kodierbar, also nie ein Fund.
GEVIERT = chr(0x2014)
BACKSLASH = chr(0x5C)

KODIERUNG = {"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}


def rufe_sweep(
    wurzel: Path, *args: str, timeout: float = 120
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SWEEP), str(wurzel), *args],
        env={**os.environ, **KODIERUNG},
        capture_output=True,
        timeout=timeout,
    )


def sweep(wurzel: Path, *args: str) -> dict:
    roh = io.BytesIO()
    strom = io.TextIOWrapper(roh, encoding="cp1252", errors="strict")
    with contextlib.redirect_stdout(strom):
        assert cp1252_sweep.main([str(wurzel), *args]) == 0
    strom.flush()
    return json.loads(roh.getvalue().decode("cp1252"))


def lege_ab(wurzel: Path, pfad: str, inhalt: str) -> Path:
    ziel = wurzel / pfad
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(inhalt, encoding="utf-8", newline="\n")
    return ziel


def funde(tmp_path: Path, quelltext: str) -> list[dict]:
    """Die Funde in einem Repo mit genau einem Skript."""
    lege_ab(tmp_path, "a-mcp/scripts/gate.py", quelltext)
    return sweep(tmp_path)["repos"]["a-mcp"]["skripte"]["scripts/gate.py"]["funde"]


def klassen(tmp_path: Path, quelltext: str) -> list[str]:
    return [f["klasse"] for f in funde(tmp_path, quelltext)]


# --- Klassierung ------------------------------------------------------------


def test_pfeil_nur_im_kommentar_ist_kein_fund(tmp_path):
    assert funde(tmp_path, f"# a {PFEIL} b\nx = 1  # {PFEIL}\n") == []


def test_pfeil_in_print_ist_kandidat(tmp_path):
    (fund,) = funde(tmp_path, f'x = 1\nprint("a {PFEIL} b")\n')
    assert fund["klasse"] == "kandidat"
    assert fund["zeile"] == 2
    assert fund["codepunkte"] == ["U+2192"]


def test_was_cp1252_kann_ist_kein_fund(tmp_path):
    assert funde(tmp_path, f'print("fünf {GEVIERT} «gut» ß €")\n') == []


def test_pfeil_als_regex_argument_ist_eingabedatum(tmp_path):
    quelltext = f'import re\nV = re.compile(r"^\\s*{PFEIL}\\s*(PASSED)")\n'
    (fund,) = funde(tmp_path, quelltext)
    assert (fund["klasse"], fund["zeile"]) == ("eingabedatum", 2)


def test_regex_unter_anderem_namen(tmp_path):
    quelltext = (
        "import re as r\nfrom re import search as suche\n"
        f'r.match("{PFEIL}", s)\nsuche("{PFEIL}", s)\n'
    )
    assert klassen(tmp_path, quelltext) == ["eingabedatum"] * 2


def test_zusammengesetztes_muster_ist_eingabedatum(tmp_path):
    quelltext = (
        "import re\n"
        f're.compile(f"{PFEIL}{{x}}")\n'
        f're.compile("a" + "{PFEIL}")\n'
        f're.compile("|".join(["{PFEIL}", "b"]))\n'
        f're.compile(re.escape("{PFEIL}"))\n'
    )
    assert klassen(tmp_path, quelltext) == ["eingabedatum"] * 4


def test_ersatztext_von_sub_ist_kandidat(tmp_path):
    """`repl` wird geschrieben, nicht gelesen."""
    quelltext = (
        "import re\n"
        f're.sub("a", "{PFEIL}", s)\n'
        f're.sub("a", string=s, repl="{PFEIL}")\n'
        f're.sub("{PFEIL}", "a", s)\n'
    )
    erwartet = ["kandidat", "kandidat", "eingabedatum"]
    assert klassen(tmp_path, quelltext) == erwartet


def test_gleichnamige_fremde_funktion_ist_keine_regex_funktion(tmp_path):
    quelltext = f'compile("{PFEIL}", "x", "exec")\nobj.search("{PFEIL}")\n'
    assert klassen(tmp_path, quelltext) == ["kandidat", "kandidat"]


def test_fremder_aufruf_innerhalb_eines_regex_arguments_bleibt_kandidat(tmp_path):
    quelltext = f'import re\nre.search("a", melde("{PFEIL}"))\n'
    assert klassen(tmp_path, quelltext) == ["kandidat"]


def test_docstrings(tmp_path):
    quelltext = (
        f'"""Modul {PFEIL}"""\n'
        f'class K:\n    """Klasse {PFEIL}"""\n'
        f'    async def m(self):\n        """Methode {PFEIL}"""\n'
    )
    assert klassen(tmp_path, quelltext) == ["docstring"] * 3


def test_f_string_teile(tmp_path):
    quelltext = f'print(f"{{a}} {PFEIL} {{b}}")\nprint(f"{{a:{PFEIL}>9}}")\n'
    gefunden = funde(tmp_path, quelltext)
    assert [(f["klasse"], f["zeile"]) for f in gefunden] == [
        ("kandidat", 1),
        ("kandidat", 2),
    ]


def test_escape_folge_im_quelltext_ist_dasselbe_zeichen(tmp_path):
    """Im Quelltext steht kein Pfeil, in der Ausgabe schon."""
    quelltext = f'print("a {BACKSLASH}u2192 b")\n'
    assert PFEIL not in quelltext
    (fund,) = funde(tmp_path, quelltext)
    assert fund["codepunkte"] == ["U+2192"]


def test_codepunkte_einmal_und_sortiert(tmp_path):
    (fund,) = funde(tmp_path, f'print("{ROBOTER}{PFEIL}{HAKEN}{PFEIL}")\n')
    assert fund["codepunkte"] == ["U+2192", "U+2713", "U+1F916"]


def test_kontext_nennt_den_aufruf(tmp_path):
    """Die Lesehilfe: stderr bricht nie, stdout schon."""
    quelltext = (
        "import sys\n"
        f'print("{PFEIL}", file=sys.stderr)\n'
        f'M = "{PFEIL}"\n'
        f'raise SystemExit("{PFEIL}")\n'
    )
    kontexte = [f["kontext"] for f in funde(tmp_path, quelltext)]
    assert kontexte == ["print(file=sys.stderr)", "Assign", "SystemExit"]


def test_datei_die_ihren_docstring_ausgeben_kann_ist_markiert(tmp_path):
    lege_ab(tmp_path, "a-mcp/scripts/mit.py", f'"""{PFEIL}"""\nprint(__doc__)\n')
    lege_ab(tmp_path, "a-mcp/scripts/ohne.py", f'"""{PFEIL}"""\n')
    skripte = sweep(tmp_path)["repos"]["a-mcp"]["skripte"]
    assert skripte["scripts/mit.py"]["liest_doc"] is True
    assert skripte["scripts/ohne.py"]["liest_doc"] is False


def test_datei_die_ihre_ausgabe_umstellt_ist_markiert(tmp_path):
    umgestellt = 'import sys\nsys.stdout.reconfigure(encoding="utf-8")\n'
    lege_ab(tmp_path, "a-mcp/scripts/mit.py", umgestellt)
    lege_ab(tmp_path, "a-mcp/scripts/ohne.py", "x = 1\n")
    skripte = sweep(tmp_path)["repos"]["a-mcp"]["skripte"]
    assert skripte["scripts/mit.py"]["stellt_stdout_um"] is True
    assert skripte["scripts/ohne.py"]["stellt_stdout_um"] is False


def test_unlesbare_datei_ist_nicht_erhoben_statt_sauber(tmp_path):
    lege_ab(tmp_path, "a-mcp/scripts/kaputt.py", "def (:\n")
    eintrag = sweep(tmp_path)["repos"]["a-mcp"]["skripte"]["scripts/kaputt.py"]
    assert eintrag["nicht_erhoben"].startswith("SyntaxError")
    assert "funde" not in eintrag


def test_nur_scripts_im_wurzelverzeichnis(tmp_path):
    for pfad in ("tests/t.py", "sub/scripts/s.py", "src/x.py"):
        lege_ab(tmp_path, f"a-mcp/{pfad}", f'print("{PFEIL}")\n')
    assert sweep(tmp_path)["repos"]["a-mcp"]["skripte"] == {}


# --- Die eigene Ausgabe -----------------------------------------------------


def test_sweep_laeuft_selbst_unter_cp1252(tmp_path):
    """Der Test, der das Werkzeug gegen seinen eigenen Gegenstand hält."""
    lege_ab(tmp_path, "a-mcp/scripts/g.py", f'print("{PFEIL}{HAKEN}{ROBOTER}")\n')
    lege_ab(tmp_path, f"b{PFEIL}-mcp/scripts/{HAKEN}.py", f'print("{PFEIL}")\n')
    lauf = rufe_sweep(tmp_path)
    assert lauf.returncode == 0, lauf.stderr
    assert lauf.stderr == b""
    text = lauf.stdout.decode("cp1252")
    assert "U+2192" in text
    assert "U+1F916" in text
    # Auch nicht als JSON-Escape: Die Zeichen erscheinen als U+XXXX.
    assert BACKSLASH + "u2192" not in text
    assert BACKSLASH + "ud83e" not in text
    assert "b<U+2192>-mcp" in json.loads(text)["repos"]


# --- Gates ------------------------------------------------------------------

WORKFLOW = """\
on: push
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      - run: {befehl}
"""


def skript(tmp_path: Path, name: str = "scripts/gate.py") -> dict:
    return sweep(tmp_path)["repos"]["a-mcp"]["skripte"][name]


def mit_workflow(tmp_path: Path, befehl: str) -> dict:
    lege_ab(tmp_path, "a-mcp/scripts/gate.py", "x = 1\n")
    pfad = "a-mcp/.github/workflows/ci.yml"
    lege_ab(tmp_path, pfad, WORKFLOW.format(befehl=befehl))
    return skript(tmp_path)


@pytest.mark.parametrize(
    "befehl",
    [
        "python scripts/gate.py",
        'python3 ./scripts/gate.py --expect "$GITHUB_REF_NAME"',
        "uv run python scripts/gate.py",
        "uv run scripts/gate.py",
        "PYTHONPATH=src python -X utf8 -u scripts/gate.py ci",
        "/tmp/fresh/bin/python scripts/gate.py x",
        "python -m scripts.gate",
        "python $GITHUB_WORKSPACE/scripts/gate.py",
        "python ${{ github.workspace }}/scripts/gate.py",
        "cd . && python scripts/gate.py | tee log",
        "|\n          set -e\n          python \\\n            scripts/gate.py",
    ],
)
def test_aufruf_im_workflow_ist_gate(tmp_path, befehl):
    eintrag = mit_workflow(tmp_path, befehl)
    assert eintrag["gate"] is True
    assert eintrag["aufrufe"] == [".github/workflows/ci.yml"]


@pytest.mark.parametrize(
    "befehl",
    [
        "ruff check src/ scripts/gate.py",
        "echo siehe scripts/gate.py",
        "python sub/scripts/gate.py",
        "python scripts/gate.python",
        "|\n          # python scripts/gate.py\n          true",
        "true  # python scripts/gate.py",
    ],
)
def test_blosse_erwaehnung_ist_kein_gate(tmp_path, befehl):
    eintrag = mit_workflow(tmp_path, befehl)
    assert eintrag["gate"] is False
    assert eintrag["aufrufe"] == []


def test_erwaehnung_ohne_aufruf_bleibt_sichtbar(tmp_path):
    """Was der Leser als Aufruf verpasst, soll von Hand auffindbar sein."""
    eintrag = mit_workflow(tmp_path, "mystery-runner scripts/gate.py")
    assert eintrag["gate"] is False
    assert eintrag["erwaehnt"] == [".github/workflows/ci.yml"]


def test_nicht_aufgerufenes_skript_ist_kein_gate(tmp_path):
    lege_ab(tmp_path, "a-mcp/scripts/gate.py", "x = 1\n")
    eintrag = skript(tmp_path)
    assert (eintrag["gate"], eintrag["erwaehnt"]) == (False, [])


def test_arbeitsverzeichnis_entscheidet(tmp_path):
    lege_ab(tmp_path, "a-mcp/scripts/gate.py", "x = 1\n")
    lege_ab(tmp_path, "a-mcp/scripts/oben.py", "x = 1\n")
    lege_ab(
        tmp_path,
        "a-mcp/.github/workflows/ci.yaml",
        "jobs:\n  a:\n    defaults:\n      run:\n        working-directory: sub\n"
        "    steps:\n"
        "      - run: python scripts/gate.py\n"
        "      - run: python ../scripts/oben.py\n",
    )
    assert skript(tmp_path)["gate"] is False
    assert skript(tmp_path, "scripts/oben.py")["gate"] is True


def test_pre_commit_hook_ist_gate(tmp_path):
    lege_ab(tmp_path, "a-mcp/scripts/gate.py", "x = 1\n")
    lege_ab(tmp_path, "a-mcp/scripts/direkt.py", "x = 1\n")
    lege_ab(
        tmp_path,
        "a-mcp/.pre-commit-config.yaml",
        "repos:\n  - repo: local\n    hooks:\n"
        "      - id: a\n        entry: python3\n        args: [scripts/gate.py]\n"
        "      - id: b\n        entry: scripts/direkt.py\n",
    )
    assert skript(tmp_path)["aufrufe"] == [".pre-commit-config.yaml"]
    assert skript(tmp_path, "scripts/direkt.py")["gate"] is True


def test_viele_schalter_halten_die_erkennung_nicht_auf(tmp_path):
    """Passt ein Schalter auf zwei Zweige, verdoppelt jeder weitere die Arbeit."""
    lege_ab(tmp_path, "a-mcp/scripts/gate.py", "x = 1\n")
    workflow = WORKFLOW.format(befehl="python" + " -Xa" * 40 + " nichts")
    lege_ab(tmp_path, "a-mcp/.github/workflows/ci.yml", workflow)
    assert rufe_sweep(tmp_path, timeout=20).returncode == 0


def test_unlesbarer_workflow_ist_nicht_erhoben(tmp_path):
    lege_ab(tmp_path, "a-mcp/scripts/gate.py", "x = 1\n")
    lege_ab(tmp_path, "a-mcp/.github/workflows/ci.yml", "jobs: [\n")
    repo = sweep(tmp_path)["repos"]["a-mcp"]
    assert list(repo["nicht_erhoben"]) == [".github/workflows/ci.yml"]


# --- Zusatzwerte ------------------------------------------------------------


def repo(tmp_path: Path, **dateien: str) -> dict:
    """Legt die Dateien ab und gibt den Eintrag des Repos zurück."""
    for pfad, inhalt in dateien.items():
        lege_ab(tmp_path, f"a-mcp/{pfad}", inhalt)
    return sweep(tmp_path)["repos"]["a-mcp"]


def test_ruff_pin_aus_pyproject(tmp_path):
    inhalt = (
        '[project]\nname = "a"\n[project.optional-dependencies]\n'
        'dev = ["pytest>=8", "ruff==0.16.9"]  # frueher ruff==0.15.8\n'
    )
    assert repo(tmp_path, **{"pyproject.toml": inhalt})["ruff_pins"] == [
        {
            "angabe": "ruff==0.16.9",
            "quelle": "pyproject.toml project.optional-dependencies.dev",
        }
    ]


def test_ruff_pin_aus_jeder_anderen_quelle(tmp_path):
    gefunden = repo(
        tmp_path,
        **{
            "pyproject.toml": '[dependency-groups]\nlint = ["ruff>=0.5"]\n',
            "requirements-lint.txt": "# ruff==0.1\nruff==0.16.10  # Pin\n",
            ".github/workflows/ci.yml": WORKFLOW.format(
                befehl="pip install ruff==0.16.8  # nicht ruff==0.2.0"
            ),
            ".pre-commit-config.yaml": (
                "repos:\n"
                "  - repo: https://github.com/astral-sh/ruff-pre-commit\n"
                "    rev: v0.16.7\n    hooks: []\n"
            ),
        },
    )["ruff_pins"]
    assert [(p["angabe"], p["quelle"]) for p in gefunden] == [
        ("ruff>=0.5", "pyproject.toml dependency-groups.lint"),
        ("ruff==0.16.10", "requirements-lint.txt"),
        ("ruff==0.16.8", ".github/workflows/ci.yml"),
        ("ruff==0.16.7", ".pre-commit-config.yaml rev"),
    ]


def test_kein_ruff_pin_ist_eine_leere_liste(tmp_path):
    assert repo(tmp_path, README="x")["ruff_pins"] == []


def test_zeilenbreite_und_komma(tmp_path):
    inhalt = (
        "[tool.ruff]\nline-length = 110\n"
        "[tool.ruff.format]\nskip-magic-trailing-comma = true\n"
    )
    assert repo(tmp_path, **{"pyproject.toml": inhalt})["ruff_format"] == {
        "line_length": 110,
        "skip_magic_trailing_comma": True,
        "quelle": "pyproject.toml",
    }


def test_zeilenbreite_ohne_eintrag_ist_die_vorgabe(tmp_path):
    gefunden = repo(tmp_path, **{"pyproject.toml": '[project]\nname = "a"\n'})
    assert gefunden["ruff_format"] == {
        "line_length": 88,
        "skip_magic_trailing_comma": False,
        "quelle": "Vorgabe von ruff",
    }


def test_ruff_toml_geht_pyproject_vor(tmp_path):
    gefunden = repo(
        tmp_path,
        **{
            "ruff.toml": "line-length = 100\n",
            "pyproject.toml": "[tool.ruff]\nline-length = 120\n",
        },
    )["ruff_format"]
    assert (gefunden["line_length"], gefunden["quelle"]) == (100, "ruff.toml")


def rat(tmp_path: Path, quelltext: str) -> dict:
    return repo(tmp_path, **{"scripts/check_ruff_pin.py": quelltext})["rat"]


@pytest.mark.parametrize(
    "zeile",
    [
        "_INSTALL = '    pip install -e \".[dev]\"'",
        'print(f"oder: pip install ruff=={want}")',
        'raise SystemExit("a\\npython -m pip install x")',
    ],
)
def test_blankes_pip_install_ist_gemeldet(tmp_path, zeile):
    assert rat(tmp_path, zeile + "\n") == {"blankes_pip_install": True, "zeilen": [1]}


@pytest.mark.parametrize(
    "zeile",
    [
        "x = 'uv pip install --python .venv -e \".[dev]\"'",
        "x = '.venv/bin/python -m pip install -e .'",
        'print(f"{sys.executable} -m pip install x")',
        "# pip install ruff",
        '"""Frueher stand hier pip install ruff."""',
        'import re; P = re.compile("pip install ruff")',
        "x = 'uv sync'",
    ],
)
def test_rat_mit_umgebung_oder_ohne_rat(tmp_path, zeile):
    erwartet = {"blankes_pip_install": False, "zeilen": []}
    assert rat(tmp_path, zeile + "\n") == erwartet


def test_rat_ohne_gate_ist_nicht_erhoben(tmp_path):
    assert "nicht_erhoben" in repo(tmp_path, README="x")["rat"]


def test_cp1252_test_vorhanden(tmp_path):
    assert repo(tmp_path, README="x")["test_gates_cp1252"] is False
    pfad = "tests/test_gates_cp1252.py"
    assert repo(tmp_path, **{pfad: ""})["test_gates_cp1252"] is True


def git(repo_pfad: Path, *args: str) -> str:
    """git ohne die Konfiguration des Rechners, auf dem der Test läuft."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env |= {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    wer = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    lauf = subprocess.run(
        ["git", *wer, *args],
        cwd=repo_pfad,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return lauf.stdout.strip()


@pytest.mark.parametrize(
    ("gitignore", "erwartet"),
    [
        ("__pycache__/\n", True),
        ("**/__pycache__\n", True),
        ("*.py[cod]\n", True),
        (".venv/\n", False),
        ("# __pycache__/\n", False),
        ("__pycache__/*\n!scripts/__pycache__/*\n", False),
    ],
)
def test_gitignore_deckt_pycache(tmp_path, gitignore, erwartet):
    lege_ab(tmp_path, "a-mcp/.gitignore", gitignore)
    git(tmp_path / "a-mcp", "init", "-q")
    repo_eintrag = sweep(tmp_path)["repos"]["a-mcp"]
    assert repo_eintrag["gitignore_deckt_pycache"] is erwartet


def test_commit_und_zustand_des_checkouts(tmp_path):
    ziel = lege_ab(tmp_path, "a-mcp/scripts/gate.py", "x = 1\n").parents[1]
    git(ziel, "init", "-q")
    git(ziel, "add", "-A")
    git(ziel, "commit", "-q", "-m", "a")
    eintrag = sweep(tmp_path)["repos"]["a-mcp"]
    assert eintrag["commit"] == git(ziel, "rev-parse", "HEAD")
    assert eintrag["abweichungen_vom_commit"] == 0
    lege_ab(tmp_path, "a-mcp/scripts/neu.py", "x = 1\n")
    assert sweep(tmp_path)["repos"]["a-mcp"]["abweichungen_vom_commit"] == 1


def test_sweep_schreibt_den_index_nicht_neu(tmp_path):
    """`git status` frischt `.git/index` auf, sobald eine Dateizeit abweicht."""
    datei = lege_ab(tmp_path, "a-mcp/scripts/gate.py", "x = 1\n")
    ziel = datei.parents[1]
    git(ziel, "init", "-q")
    git(ziel, "add", "-A")
    git(ziel, "commit", "-q", "-m", "a")
    os.utime(datei, (1_000_000_000, 1_000_000_000))
    vorher = (ziel / ".git" / "index").read_bytes()
    assert sweep(tmp_path)["repos"]["a-mcp"]["abweichungen_vom_commit"] == 0
    assert (ziel / ".git" / "index").read_bytes() == vorher


def test_git_fuehrt_keinen_fsmonitor_aus(tmp_path):
    """Die Konfiguration im Klon darf beim Lesen nichts starten."""
    datei = lege_ab(tmp_path, "a-mcp/scripts/gate.py", "x = 1\n")
    ziel = datei.parents[1]
    git(ziel, "init", "-q")
    git(ziel, "add", "-A")
    git(ziel, "commit", "-q", "-m", "a")
    spur = tmp_path / "gestartet"
    git(ziel, "config", "core.fsmonitor", f"echo x > '{spur.as_posix()}' #")
    git(ziel, "status")
    assert spur.exists(), "die Attrappe wirkt nicht, der Test prüfte nichts"
    spur.unlink()
    sweep(tmp_path)
    assert not spur.exists()


def test_verzeichnis_ohne_git_erbt_keinen_fremden_commit(tmp_path):
    """`git rev-parse` sucht nach oben und fände das Repo darüber."""
    lege_ab(tmp_path, "a-mcp/README", "x")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "a")
    eintrag = sweep(tmp_path)["repos"]["a-mcp"]
    assert eintrag["commit"] is None
    assert eintrag["gitignore_deckt_pycache"] is None


def test_claude_md(tmp_path):
    teil_1 = "## Teil 1 " + GEVIERT + " Konventionen\n\nfünf\n\n"
    text = f"# CLAUDE.md\n\n{teil_1}## Teil 2 {GEVIERT} Dieses Repo\n\nx\n"
    gefunden = repo(tmp_path, **{"CLAUDE.md": text})["claude_md"]
    assert gefunden == {
        "zeilen": 9,
        "teil_1_sha256": hashlib.sha256(teil_1.encode()).hexdigest(),
    }


def test_claude_md_ohne_die_beiden_ueberschriften(tmp_path):
    ohne_1 = repo(tmp_path, **{"CLAUDE.md": "# x\n"})["claude_md"]
    assert ohne_1["teil_1_sha256"] is None
    assert "Teil 1" in ohne_1["nicht_erhoben"]
    ohne_2 = repo(tmp_path, **{"CLAUDE.md": "## Teil 1\n"})["claude_md"]
    assert ohne_2["teil_1_sha256"] is None
    assert "Teil 2" in ohne_2["nicht_erhoben"]


def test_ohne_claude_md(tmp_path):
    gefunden = repo(tmp_path, README="x")["claude_md"]
    assert gefunden == {"nicht_erhoben": "CLAUDE.md fehlt"}


# --- Der Lauf ---------------------------------------------------------------

GATE = "scripts/check_version_sync.py"


def lauf_von(tmp_path: Path, quelltext: str, *args: str) -> dict:
    lege_ab(tmp_path, f"a-mcp/{GATE}", quelltext)
    return sweep(tmp_path, "--lauf", *args)["repos"]["a-mcp"]["lauf"][GATE]


def test_ohne_schalter_kein_lauf(tmp_path):
    lege_ab(tmp_path, f"a-mcp/{GATE}", "open('gelaufen', 'w')\n")
    assert "lauf" not in sweep(tmp_path)["repos"]["a-mcp"]
    assert not (tmp_path / "a-mcp" / "gelaufen").exists()


def test_lauf_bestaetigt_einen_fund(tmp_path):
    gemessen = lauf_von(tmp_path, f'print("{PFEIL}")\n')
    assert (gemessen["exit"], gemessen["unicode_encode_error"]) == (1, True)


def test_lauf_ohne_fehler(tmp_path):
    gemessen = lauf_von(tmp_path, "print('gut')\n")
    assert (gemessen["exit"], gemessen["unicode_encode_error"]) == (0, False)


def test_frueher_abbruch_entlastet_nicht(tmp_path):
    """Die Zeile mit dem Pfeil wird nie erreicht. Der Kandidat bleibt stehen."""
    quelltext = f'raise SystemExit(3)\nprint("{PFEIL}")\n'
    gemessen = lauf_von(tmp_path, quelltext)
    assert (gemessen["exit"], gemessen["unicode_encode_error"]) == (3, False)
    ergebnis = sweep(tmp_path, "--lauf")
    (fund,) = ergebnis["repos"]["a-mcp"]["skripte"][GATE]["funde"]
    assert fund["klasse"] == "kandidat"
    assert "nicht entlasten" in ergebnis["hinweis"]


def test_stderr_bricht_nicht(tmp_path):
    """Die Grundlage der Lesehilfe, gemessen statt behauptet."""
    gemessen = lauf_von(tmp_path, f'raise SystemExit("{PFEIL}")\n')
    assert (gemessen["exit"], gemessen["unicode_encode_error"]) == (1, False)


def test_lauf_umgebung(tmp_path, monkeypatch):
    for name in ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONDONTWRITEBYTECODE"):
        monkeypatch.delenv(name, raising=False)
    quelltext = (
        "import os, sys\n"
        "e = os.environ\n"
        "ok = (e['PYTHONIOENCODING'], e['PYTHONUTF8']) == ('cp1252', '0')\n"
        "ok = ok and e['PYTHONDONTWRITEBYTECODE'] == '1'\n"
        "ok = ok and os.path.basename(os.getcwd()) == 'a-mcp'\n"
        "sys.exit(0 if ok else 9)\n"
    )
    assert lauf_von(tmp_path, quelltext)["exit"] == 0


def test_zeitschranke(tmp_path):
    quelltext = "import time\ntime.sleep(4)\n"
    gemessen = lauf_von(tmp_path, quelltext, "--zeitschranke", "1")
    assert gemessen["exit"] is None
    assert "1 s" in gemessen["nicht_erhoben"]


def test_andere_skripte_laufen_nie(tmp_path):
    lege_ab(tmp_path, "a-mcp/scripts/record_fixtures.py", "open('da', 'w')\n")
    workflow = WORKFLOW.format(befehl="python scripts/record_fixtures.py")
    lege_ab(tmp_path, "a-mcp/.github/workflows/ci.yml", workflow)
    assert sweep(tmp_path, "--lauf")["repos"]["a-mcp"]["lauf"] == {}
    assert not (tmp_path / "a-mcp" / "da").exists()


def test_lauf_schreibt_nichts_in_den_checkout(tmp_path, monkeypatch):
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    lege_ab(tmp_path, "a-mcp/scripts/helfer.py", "print('da')\n")
    lege_ab(tmp_path, f"a-mcp/{GATE}", "import helfer\n")
    vorher = sorted(tmp_path.rglob("*"))
    sweep(tmp_path, "--lauf")
    assert sorted(tmp_path.rglob("*")) == vorher


def test_lauf_als_eigener_prozess_unter_cp1252(tmp_path):
    """Auch die Fehlerzeile eines Gates darf den Sweep nicht abbrechen."""
    lege_ab(tmp_path, f"a-mcp/{GATE}", f'raise ValueError("{PFEIL}{ROBOTER}")\n')
    lauf = rufe_sweep(tmp_path, "--lauf")
    assert (lauf.returncode, lauf.stderr) == (0, b"")
    gemessen = json.loads(lauf.stdout)["repos"]["a-mcp"]["lauf"][GATE]
    assert gemessen["stderr_letzte_zeile"].startswith("ValueError")


def test_ergebnis_nennt_die_laufumgebung(tmp_path):
    lege_ab(tmp_path, f"a-mcp/{GATE}", "x = 1\n")
    umgebung = sweep(tmp_path, "--lauf")["laufumgebung"]
    assert umgebung["python"] == sys.version.split()[0]
    assert {"ruff_im_path", "ruff_als_modul"} <= set(umgebung)
