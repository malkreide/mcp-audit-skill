"""Hygiene: kein Bytecode im Index, und die genannten Dateien gibt es.

Zusammengefuehrt aus den drei Fassungen in `mcp-data-source-probe-skill`,
`mcp-data-fidelity-skill` und `mcp-transport-hardening-skill` — Familien G7
und G8 des Merge-Plans.

Die beiden Pruefungen stehen zusammen, weil sie dieselbe Frage aus zwei
Richtungen stellen: Was liegt im Index, das nicht hineingehoert, und was
gehoert hinein, liegt aber nicht da.

WAS BEIM ZUSAMMENFUEHREN AUS WELCHER FASSUNG KAM. Der Code von G7 war in
probe und fidelity zeichengleich; transport hatte dieselbe Logik mit einem
anderen Muster, dafuer aber die ausfuehrlichere Begruendung UND den
Behebungshinweis (`git rm --cached`). Beides ist uebernommen. Die Muster sind
vereinigt: probes Regex faengt `.pyd` nicht, transports Tupel faengt
`__pycache__/` nur mit Schraegstrich — zusammen decken sie beides ab.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from tools.harness import CheckFailed

#: `(^|/)__pycache__/` faengt das Verzeichnis an jeder Tiefe, `\\.py[cod]$` die
#: kompilierten Endungen. Vereinigung der beiden Fassungen: probes Regex
#: kannte `.pyd` nicht als Endung im Tupel-Sinn, transports Tupel prueft
#: `endswith` und faende ein `__pycache__/` am Pfadanfang nicht.
COMPILED = re.compile(r"(^|/)__pycache__/|\.py[cod]$")


def no_compiled_python(root: Path) -> str:
    """G7 — kein Bytecode im Index.

    `.gitignore` haelt `__pycache__/` normalerweise draussen. Hineinkommen tut
    es trotzdem: durch ein `git add -f`, durch eine fehlende
    `.gitignore`-Zeile, oder weil eine Datei getrackt war, BEVOR die Zeile
    dazukam — dann ignoriert git sie nicht mehr.

    Der Fall ist belegt: In `mcp-data-source-probe-skill` war eine `.pyc`
    schon einmal eingecheckt (CHANGELOG 1.1.0, «Removed»). Der Vorfall stand
    dokumentiert, ein Waechter dagegen fehlte — das Schwesterrepo
    `mcp-transport-hardening-skill` hatte ihn, jenes nicht. Genau die Sorte
    Luecke, die diese Zusammenfuehrung schliesst.

    GEFRAGT WIRD GIT, NICHT DAS DATEISYSTEM. Ein `find` faende auch den
    Bytecode, den der letzte Testlauf erzeugt hat und den niemand committen
    will; das waere ein Befund ueber den Arbeitsplatz, nicht ueber das
    Repository.

    Kein Repository oder kein git heisst FEHLER, nicht «uebersprungen»: Diese
    Pruefung kann dann nichts sagen, und «nicht gelaufen» als «bestanden» zu
    melden ist die eine Auskunft, die schlimmer ist als keine.
    """
    done = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise CheckFailed(
            f"`git ls-files` in {root} endete mit {done.returncode} — diese "
            "Pruefung liest den Index und kann ihn hier nicht lesen; sie "
            "meldet deshalb einen Befund statt Erfolg.\n"
            f"  {done.stderr.strip()}"
        )

    getrackt = sorted(
        line for line in done.stdout.splitlines() if COMPILED.search(line)
    )
    if getrackt:
        raise CheckFailed(
            "kompiliertes Python ist getrackt:\n"
            + "\n".join(f"  {name}" for name in getrackt)
            + "\n  `git rm --cached` darauf, und pruefen, ob .gitignore die "
            "Zeile hat — eine Datei, die vor der Ignore-Zeile getrackt wurde, "
            "ignoriert git nicht mehr."
        )
    return "kein kompiliertes Python im Index"


def referenced_files_exist(root: Path, *, files: tuple[str, ...]) -> str:
    """G8 — die Dateien, auf die dieses Repo verweist, gibt es auch.

    Diese Pruefung gehoert frueh in die Nummerierung: Sie erklaert die
    Abstuerze der anderen. Fehlt eine Vorlage, meldet die Syntax-Pruefung
    einen FileNotFoundError — richtig, aber die Diagnose steht hier.

    Die Liste ist Parameter und nicht abgeleitet, und das ist Absicht: Sie
    nennt, was jemand ZUGESICHERT hat. Ein Verzeichnis-Glob faende nur, was
    da ist, und koennte deshalb nie melden, dass etwas fehlt.
    """
    if not files:
        raise CheckFailed(
            "Die Liste der referenzierten Dateien ist leer — dann prueft "
            "diese Pruefung nichts und meldete genau das als Erfolg."
        )
    fehlend = [name for name in files if not (root / name).is_file()]
    if fehlend:
        raise CheckFailed(
            f"referenzierte Datei(en) fehlen: {fehlend}\n"
            "  Entweder ist die Datei weg, oder sie wurde umbenannt und die "
            "Liste in der Suite nicht nachgezogen. Beides macht Links und "
            "Anleitungen still falsch."
        )
    return f"alle {len(files)} referenzierten Dateien vorhanden"
