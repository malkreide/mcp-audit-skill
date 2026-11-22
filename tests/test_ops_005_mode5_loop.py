"""Fährt die Bash-Schleife aus `OPS-005` Modus 5 gegen ein Wegwerf-Repo.

Die Schleife läuft im Repo, das geprüft wird. Bis 2026-11-22 führte sie jedes
Skript aus, das ein Workflow oder pre-commit **erwähnt**, auch in einem
Kommentar und auch `record_fixtures.py`, das ins Netz geht und Fixtures
überschreibt. Ihre Fehlerausgabe legte sie als `err.txt` ins geprüfte Repo, und
ein Gate, das es nicht gibt, galt als bestanden.

Der Block wird aus der Check-Datei gezogen, nicht nachgebaut. So prüft der Test
das, was jemand beim Audit kopiert.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.suites.mcp_data_source_probe.references import (  # noqa: E402
    brauchbare_bash,
)

OPS_005 = REPO_ROOT / "checks" / "OPS-005.md"
PIN, SYNC = "scripts/check_ruff_pin.py", "scripts/check_version_sync.py"
SCHREIBER = "scripts/record_fixtures.py"
STILL = "print('ok')\n"
PFEIL = "print('a ' + chr(0x2192) + ' b')\n"
#: Auch unter UTF-8 rot: Der Exit-Code ist in beiden Läufen 1, der Grund nicht.
ROT_MIT_PFEIL = PFEIL + "raise SystemExit(1)\n"
#: Fängt den Abbruch selbst ab: kein Traceback, aber ein anderer Exit-Code.
ABGEFANGEN = (
    "import sys\n"
    "try:\n"
    "    print(chr(0x2192))\n"
    "except UnicodeEncodeError:\n"
    "    sys.exit(3)\n"
)


def _block() -> str:
    text = OPS_005.read_text(encoding="utf-8")
    modus = text.split("### Modus 5")[1].split("\n## ")[0]
    treffer = [
        b
        for b in re.findall(r"```bash\n(.*?)```", modus, re.S)
        if "PYTHONIOENCODING" in b
    ]
    assert len(treffer) == 1, (
        f"erwartet: ein Bash-Block mit der Schleife, gefunden: {len(treffer)}"
    )
    return treffer[0]


def _repo(tmp_path: Path, skripte: dict[str, str], erwaehnt: list[str]) -> Path:
    repo = tmp_path / "ziel-mcp"
    for name, inhalt in skripte.items():
        ziel = repo / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8", newline="\n")
    workflow = repo / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "".join(f"# {s}\n" for s in erwaehnt), encoding="utf-8", newline="\n"
    )
    return repo


def _fahre(repo: Path) -> str:
    skript = repo.parent / "schleife.sh"
    skript.write_text(_block(), encoding="utf-8", newline="\n")
    temp = repo.parent / "temp"
    temp.mkdir()
    pfad = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    # Ohne die Variable wäre der Nachweis «kein __pycache__» geschenkt.
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    lauf = subprocess.run(
        [brauchbare_bash(), skript.as_posix()],
        cwd=repo,
        env={**env, "PATH": pfad, "TMPDIR": temp.as_posix()},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert lauf.stderr == "", lauf.stderr
    assert list(temp.iterdir()) == []
    return lauf.stdout


def _dateien(repo: Path) -> dict[str, bytes | None]:
    return {
        p.relative_to(repo).as_posix(): p.read_bytes() if p.is_file() else None
        for p in repo.rglob("*")
    }


def test_ein_nur_erwaehntes_skript_wird_nicht_ausgefuehrt(tmp_path: Path):
    schreiber = "open('geschrieben.json', 'w').close()\n"
    repo = _repo(
        tmp_path,
        {PIN: STILL, SYNC: STILL, SCHREIBER: schreiber},
        [PIN, SYNC, SCHREIBER],
    )
    ausgabe = _fahre(repo)
    assert not (repo / "geschrieben.json").exists()
    assert [z for z in ausgabe.splitlines() if SCHREIBER in z and "UNGEPRUEFT" in z], (
        ausgabe
    )
    assert not [z for z in ausgabe.splitlines() if PIN in z or SYNC in z], ausgabe


def test_die_schleife_hinterlaesst_nichts_im_geprueften_repo(tmp_path: Path):
    skripte = {PIN: "import nachbar\n" + STILL, "scripts/nachbar.py": "", SYNC: PFEIL}
    # Eine fremde Datei mit dem Namen, den die Schleife früher benutzte.
    skripte["err.txt"] = "gehört dem Repo"
    repo = _repo(tmp_path, skripte, [PIN, SYNC])
    vorher = _dateien(repo)
    _fahre(repo)
    assert _dateien(repo) == vorher


def test_ein_gate_das_es_nicht_gibt_ist_nicht_bestanden(tmp_path: Path):
    repo = _repo(tmp_path, {SYNC: STILL}, [PIN, SYNC])
    zeilen = [z for z in _fahre(repo).splitlines() if PIN in z]
    assert len(zeilen) == 1 and zeilen[0].startswith("FEHLT"), zeilen


@pytest.mark.parametrize(
    "inhalt",
    [PFEIL, ABGEFANGEN, ROT_MIT_PFEIL],
    ids=["beides", "exit-code", "traceback"],
)
def test_ein_abbruch_unter_cp1252_ist_ein_befund(tmp_path: Path, inhalt: str):
    repo = _repo(tmp_path, {PIN: STILL, SYNC: inhalt}, [PIN, SYNC])
    zeilen = [z for z in _fahre(repo).splitlines() if z.startswith("BEFUND")]
    assert len(zeilen) == 1 and SYNC in zeilen[0], zeilen


def test_ein_rotes_gate_ohne_unterschied_ist_kein_befund(tmp_path: Path):
    repo = _repo(tmp_path, {PIN: STILL, SYNC: "raise SystemExit(1)\n"}, [PIN, SYNC])
    assert "BEFUND" not in _fahre(repo)
