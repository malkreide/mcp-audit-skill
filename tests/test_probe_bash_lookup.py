"""`brauchbare_bash()` — die Naht, an der `probe/1` die Umgebung befragt.

DER ANLASS IST GEMESSEN UND NICHT GEDACHT. Auf `windows-latest` liegt in
`System32` eine `bash.exe`, die nur der Starter fuer das Windows Subsystem for
Linux ist. Ohne installierte Distribution antwortet sie mit «Windows Subsystem
for Linux has no installed distributions» und einem Exit-Code ungleich null —
und die Herkunftsfassung von `probe/1` las das als «die Vorlage parst nicht».

Ein Befund, der auf die falsche Datei zeigt. Das Herkunftsrepo hat den Fall
nie gesehen, weil seine CI nur Linux fuhr; die Matrix dieses Repos enthaelt
`windows-latest`, und dort ist er beim ersten Lauf der Mutationstests
aufgeschlagen.

WARUM DIESE TESTS NICHT UNTER `tests/suites/` STEHEN: Die Mutationen dort sind
Deltas auf einem Datei-Baum. Was hier gemessen wird, steht in keiner Datei —
es ist der PATH. Ein Baum laesst sich dafuer nicht praeparieren, ein PATH
schon.
"""

from __future__ import annotations

import pathlib
import stat
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.harness import CheckFailed  # noqa: E402
from tools.suites.mcp_data_source_probe.references import (  # noqa: E402
    brauchbare_bash,
)

#: Zwei Attrappen: eine, die wie die WSL-Huelle antwortet (Ausgabe plus
#: Exit-Code 1), und eine, die tut, was eine bash tut. Als Shell-Skripte und
#: nicht als Symlinks auf die echte bash, damit der Test misst, was er misst:
#: Es geht um den EXIT-CODE der Probe, nicht um den Dateinamen.
KAPUTT = (
    "#!/bin/sh\n"
    'echo "Windows Subsystem for Linux has no installed distributions." >&2\n'
    "exit 1\n"
)
ECHT = '#!/bin/sh\nexec /bin/bash "$@"\n'


def _lege_bash_ab(verzeichnis: pathlib.Path, inhalt: str) -> pathlib.Path:
    verzeichnis.mkdir(parents=True, exist_ok=True)
    pfad = verzeichnis / "bash"
    pfad.write_text(inhalt, encoding="utf-8")
    pfad.chmod(pfad.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return pfad


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Die Attrappen sind `#!/bin/sh`-Skripte; unter Windows misst das "
    "die Shebang-Behandlung statt die Auswahl.",
)
def test_ANKER_eine_bash_die_nicht_laeuft_wird_uebergangen(tmp_path, monkeypatch):
    """Der gemessene Fall: die kaputte liegt VOR der echten im PATH.

    Genau diese Reihenfolge hat auf `windows-latest` gegolten — `System32`
    kommt vor `Program Files\\Git\\bin`. Eine Auswahl, die die erste nimmt,
    faellt hier um.
    """
    _lege_bash_ab(tmp_path / "zuerst", KAPUTT)
    echt = _lege_bash_ab(tmp_path / "danach", ECHT)
    monkeypatch.setenv(
        "PATH", f"{tmp_path / 'zuerst'}:{tmp_path / 'danach'}:/usr/bin:/bin"
    )
    assert brauchbare_bash() == str(echt)


@pytest.mark.skipif(sys.platform == "win32", reason="siehe oben")
def test_ANKER_gar_keine_brauchbare_bash_ist_ein_befund_ueber_die_umgebung(
    tmp_path, monkeypatch
):
    """Und zwar mit eigenem Text — nicht als Befund ueber die Vorlage.

    Das ist der ganze Punkt der Aenderung: «nicht gelaufen» und «parst nicht»
    duerfen nicht gleich aussehen, sonst sucht jemand den Fehler in einer
    Datei, die niemand angesehen hat.
    """
    _lege_bash_ab(tmp_path / "nur-kaputt", KAPUTT)
    monkeypatch.setenv("PATH", str(tmp_path / "nur-kaputt"))
    with pytest.raises(CheckFailed) as befund:
        brauchbare_bash()
    text = str(befund.value)
    assert "Keine benutzbare bash" in text
    assert "KEIN Befund ueber die Vorlage" in text
    assert "parst nicht" not in text


@pytest.mark.skipif(sys.platform == "win32", reason="siehe oben")
def test_ein_leerer_pfad_ist_ein_befund_und_kein_absturz(monkeypatch):
    monkeypatch.setenv("PATH", "")
    with pytest.raises(CheckFailed) as befund:
        brauchbare_bash()
    assert "keine gefunden" in str(befund.value)


def test_die_echte_umgebung_hat_eine_brauchbare_bash():
    """Ohne das liefe `probe/1` hier ueberhaupt nicht — und dieser Test waere
    die Stelle, an der man es merkt."""
    assert brauchbare_bash()
