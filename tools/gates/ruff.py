"""Die Ruff-Gates: laufen sie, greifen sie, und bei welcher Breite?

Zusammengefuehrt aus den drei Fassungen in `mcp-audit-skill`,
`mcp-data-source-probe-skill` und `mcp-data-fidelity-skill` — Familien G3 bis
G6 des Merge-Plans.

VIER PRUEFUNGEN, ZWEI EBENEN. `ruff_check` und `ruff_format` fahren die Gates;
`gate_bites` und `line_length_effective` pruefen, ob die Gates ueberhaupt noch
etwas tun. Die zweite Ebene gibt es, weil die erste eine Eigenschaft hat, die
keine andere Pruefung dieses Repos teilt: Ihr Anker taucht in ihrem eigenen
Befund NICHT auf. Jede andere wird rot, wenn ihr Gegenstand verschwindet; die
Ruff-Schritte melden auf einem Baum, aus dessen Konfiguration ein Verzeichnis
ausgeschlossen wurde, «All checks passed!» — ohne eine Zeile gelesen zu haben.

Der Fall ist nicht hypothetisch: In `ruff.toml` von
`mcp-data-fidelity-skill` stand fuer genau diese Dateien einmal `select = []`.
Beide Ruff-Schritte meldeten gruen, und niemand merkte es, weil nichts rot
wurde.

WAS BEIM ZUSAMMENFUEHREN AUS WELCHER FASSUNG KAM:

* Der AUFGELOESTE PFAD aus `mcp-audit-skill`: `shutil.which("ruff")` statt
  `["ruff", …]`. Das ist derselbe Binary, den `gates/toolchain.py` misst — eine
  Pruefung, die eine andere ruff faehrt als die, deren Version zugesichert
  wurde, waere schlimmer als keine.
* `--no-cache` aus `mcp-data-source-probe-skill`: Ohne das geht ein Ergebnis
  aus einem frueheren Lauf als aktuelles durch, und die Sonden unten messen
  dann den Cache statt das Gate.
* `--output-format=concise` aus denselben beiden: Der Befund ist die Meldung,
  und die lange Form fuellt sie mit Rahmen statt mit Fundstellen.
* Die BREITEN-SONDE aus `mcp-data-fidelity-skill`. Sie gab es nur dort.

Alles drei war in seiner Kopie haengengeblieben, ohne dass jemand dagegen
entschieden haette.

DAS VERZEICHNIS DER SONDEN IST PARAMETER. In den Herkunftsrepos hiess es
`reference/` und war fest verdrahtet. Hier gibt es mehrere: Jeder eingezogene
Skill bringt sein eigenes mit, und welches ein Gate bewacht, entscheidet die
Suite.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from tools.harness import CheckFailed

DEFAULT_CONFIG = "ruff.toml"

FEHLT_RUFF = (
    "ruff liegt nicht auf dem PATH — dieses Gate kann nicht laufen. FAIL statt "
    "skip: «nicht gelaufen» als «bestanden» zu melden ist die eine Auskunft, "
    "die schlimmer ist als keine."
)

HINWEIS_FORMAT = (
    "\n  `ruff format .` raeumt das auf; der Pre-Commit-Hook tut es vor jedem Commit."
)

#: Eine Datei, die BEIDE Gates beanstanden muessen: `import os` ist ein
#: unbenutzter Import (F401), und `x   =    1` bringt der Formatter in Ordnung.
PROBE_NAME = "_ruff_gate_probe.py"
PROBE_SOURCE = "import os\nx   =    1\n"

LINE_LENGTH = re.compile(r"^\s*line-length\s*=\s*(?P<value>\d+)\s*$", re.M)

#: Unter dieser Breite laesst sich keine Sonde mehr bauen, die genau eine
#: Zeichenbreite trifft — die Pruefung wuerde ab hier nichts mehr messen und
#: genau das als bestanden melden.
MIN_WIDTH = 40

LENGTH_PROBE_AT = "_line_length_probe_at.py"
LENGTH_PROBE_OVER = "_line_length_probe_over.py"


# ---------------------------------------------------------------------------
# Reine Funktionen
# ---------------------------------------------------------------------------


def bewerte(kind: str, returncode: int, ausgabe: str) -> tuple[bool, str]:
    """Rein: `(gruen, Meldung)` aus Exit-Code und Ausgabe.

    Kein PATH, kein Unterprozess — dieselbe Bauart wie `compare()` in
    `gates/toolchain.py`, und aus demselben Grund: Der Teil, der schiefgehen
    kann, soll als Wert pruefbar sein. Die Testmatrix faehrt Linux UND
    Windows, und der pytest-Job installiert kein ruff; ein Test, der eine
    echte oder untergeschobene ruff braucht, pruefte die Testumgebung statt
    den Code.
    """
    text = ausgabe.strip()
    if returncode == 0:
        return True, text or ("All checks passed!" if kind == "check" else "formatted")
    if kind == "format":
        return False, text + HINWEIS_FORMAT
    return False, text


def _comment_of(width: int) -> str:
    """Eine Kommentarzeile aus genau `width` Zeichen, an Leerzeichen umbrechbar.

    Umbrechbar mit Absicht. Ruff meldet E501 NICHT auf einer ueberlangen
    Zeile, die sich nicht umbrechen laesst — ein langer URL etwa. Eine Sonde
    aus einem einzigen langen Wort haette also nichts gemessen und genau das
    als bestanden gemeldet.
    """
    body = ("ab " * width)[: width - 2]
    if body.endswith(" "):
        # Sonst stuende am Zeilenende ein Leerzeichen, und die Sonde schlueg
        # ueber W291 an statt ueber E501 — rot aus dem falschen Grund.
        body = body[:-1] + "c"
    return "# " + body


def _call_of(width: int) -> str:
    """Ein Aufruf aus genau `width` Zeichen, den der Formatter umbrechen kann.

    Fuer das Format-Gate. Der Formatter kennt kein E501 und kein `select`;
    sein einziges Kriterium ist, ob er die Zeile anfassen wuerde. Zwei
    Argumente, damit es eine Stelle gibt, an der er brechen kann.
    """
    head, tail = "y = fn(", ")"
    return head + "a" * (width - len(head) - len(tail) - 4) + ", bb" + tail


def _probe_source(width: int) -> str:
    return f"{_comment_of(width)}\n{_call_of(width)}\n"


def _e501_lines(output: str, name: str) -> set[int]:
    """Die Zeilennummern, auf denen ruff in dieser Datei E501 meldet."""
    return {
        int(match.group(1))
        for match in re.finditer(rf"^{re.escape(name)}:(\d+):\d+: E501\b", output, re.M)
    }


# ---------------------------------------------------------------------------
# Der Unterprozess
# ---------------------------------------------------------------------------


def _ruff(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Ruft ruff so auf, wie die CI es tut.

    `.` als Ziel und nicht ein genannter Pfad: Ein explizit uebergebenes
    Verzeichnis umgeht `exclude` und deckte genau die Luecke zu, die
    `gate_bites` sucht.
    """
    executable = shutil.which("ruff")
    if executable is None:
        raise CheckFailed(FEHLT_RUFF)
    return subprocess.run(
        [executable, *args, "--no-cache", "."],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _sonde_legen(root: Path, pfad: Path, inhalt: str) -> None:
    if pfad.exists():
        raise CheckFailed(
            f"{pfad.relative_to(root).as_posix()} liegt schon da. Die Sonde "
            "legt diese Datei selbst an und raeumt sie weg; existiert sie "
            "vorher, wuerde diese Pruefung sie ueberschreiben und loeschen. "
            "Bitte von Hand pruefen und entfernen."
        )
    pfad.write_text(inhalt, encoding="utf-8")


def _verzeichnis(root: Path, probe_dir: str) -> Path:
    directory = root / probe_dir
    if not directory.is_dir():
        raise CheckFailed(
            f"{probe_dir} fehlt — Anker weg; die Sonde haette kein "
            "Verzeichnis, in dem sie das Gate testen koennte"
        )
    return directory


# ---------------------------------------------------------------------------
# Die Gates
# ---------------------------------------------------------------------------


def ruff_check(root: Path) -> str:
    """G3 — `ruff check` ueber den ganzen Baum."""
    done = _ruff(root, "check", "--output-format=concise")
    ok, message = bewerte("check", done.returncode, done.stdout + done.stderr)
    if not ok:
        raise CheckFailed(
            "ruff check hat Befunde — dieselbe Invokation, die die CI "
            f"faehrt:\n{message}"
        )
    return message


def ruff_format(root: Path) -> str:
    """G4 — `ruff format --check` laesst den Baum unveraendert."""
    done = _ruff(root, "format", "--check")
    ok, message = bewerte("format", done.returncode, done.stdout + done.stderr)
    if not ok:
        raise CheckFailed(message)
    return message


def gate_bites(root: Path, *, probe_dir: str) -> str:
    """G5 — beide Gates beanstanden eine fehlerhafte Datei unter `probe_dir`.

    Geprueft wird die WIRKUNG, nicht die Konfiguration. Ein
    Konfigurationsleser muesste `exclude`, `[lint] exclude`, `[format]
    exclude`, `select` und `per-file-ignores` einzeln kennen — und verpasste
    den Schalter, den ruff erst nach diesem Commit bekommt.
    """
    verzeichnis = _verzeichnis(root, probe_dir)
    probe = verzeichnis / PROBE_NAME
    name = probe.relative_to(root).as_posix()

    _sonde_legen(root, probe, PROBE_SOURCE)
    try:
        check_out = _ruff(root, "check", "--output-format=concise")
        format_out = _ruff(root, "format", "--check")
    finally:
        probe.unlink(missing_ok=True)

    # Gegen den Dateinamen, nicht gegen den Exit-Status: Ein anderer, echter
    # Fund anderswo im Baum ginge sonst als bestandene Sonde durch, und diese
    # Pruefung waere gruen, ohne die Vorlagen geprueft zu haben.
    befunde = []
    if PROBE_NAME not in check_out.stdout + check_out.stderr:
        befunde.append(
            f"ruff check hat {name} nicht beanstandet — das Lint-Gate greift "
            f"auf {probe_dir} nicht mehr. Verdaechtig sind exclude, select "
            "und per-file-ignores in der Konfiguration.\n"
            f"ruff check meldete:\n{check_out.stdout}{check_out.stderr}".rstrip()
        )
    if PROBE_NAME not in format_out.stdout + format_out.stderr:
        befunde.append(
            f"ruff format --check hat {name} nicht beanstandet — das "
            f"Format-Gate greift auf {probe_dir} nicht mehr. Verdaechtig sind "
            "exclude und [format] exclude.\n"
            f"ruff format meldete:\n{format_out.stdout}{format_out.stderr}".rstrip()
        )
    if befunde:
        raise CheckFailed("\n".join(befunde))

    if probe.exists():
        raise CheckFailed(
            f"{name} liess sich nicht entfernen — bitte von Hand loeschen"
        )
    return f"beide Ruff-Gates beanstanden eine fehlerhafte Datei unter {probe_dir}"


def line_length_effective(
    root: Path,
    *,
    probe_dir: str,
    lint_enforces_e501: bool,
    config: str = DEFAULT_CONFIG,
) -> str:
    """G6 — die deklarierte Breite ist die, die BEIDE Gates durchsetzen.

    Dass `line-length = 88` in der Konfiguration steht, heisst noch nicht,
    dass bei 88 gemessen wird: `[lint.pycodestyle] max-line-length` setzt fuer
    E501 eine zweite Breite, ohne dass der Formatter davon erfaehrt. Dann
    stuende dort eine Zahl, die nur eines der beiden Gates einhaelt, und der
    Eintrag laese sich weiterhin richtig.

    NICHT DASSELBE wie die Frage, OB der Wert richtig gewaehlt ist. Diese
    Pruefung misst die Wirkung; ob die Zahl selbst die richtige ist, ist eine
    Portfolio-Frage und steht in `tests/test_ruff_line_length.py`.

    `lint_enforces_e501` HAT KEINE VORGABE, und das ist die Entscheidung. Die
    Repos der Kette sind sich hier uneinig, und beide Seiten sind begruendet:
    `mcp-data-fidelity-skill` fuehrt E501 im `select`, dieses Repo laesst es
    ausdruecklich weg («das entscheidet der Formatter»). Anders als bei
    `required_hooks` gibt es hier keine harmlose Vorgabe — `True` erfaende
    einen Befund, wo die Konfiguration in Ordnung ist, und `False` naehme der
    Pruefung stillschweigend ihre Lint-Haelfte. Also muss es jede Suite sagen.

    Ist E501 nicht im `select`, bleibt die Format-Haelfte: Der Formatter kennt
    kein `select`, sein einziges Kriterium ist, ob er die Zeile anfassen
    wuerde. Genau daran haengt die Zahl in einem Repo, das die Lint-Seite
    bewusst nicht bemueht.
    """
    pfad = root / config
    if not pfad.is_file():
        raise CheckFailed(
            f"{config} fehlt — ohne die Datei hat diese Pruefung keine "
            "deklarierte Breite, gegen die sie messen koennte"
        )
    declared = LINE_LENGTH.search(pfad.read_text(encoding="utf-8"))
    if not declared:
        raise CheckFailed(
            f"{config} nennt kein `line-length` — dann misst ruff auf seinem "
            "Default, und die Breite ist keine Entscheidung, sondern eine "
            "Abwesenheit."
        )
    width = int(declared.group("value"))
    if width < MIN_WIDTH:
        raise CheckFailed(
            f"{config} deklariert line-length = {width}. Unter {MIN_WIDTH} "
            "kann diese Pruefung keine Sonde mehr bauen, die genau eine "
            "Zeichenbreite trifft — sie wuerde ab hier nichts mehr messen und "
            "das als bestanden melden."
        )

    verzeichnis = _verzeichnis(root, probe_dir)
    sonden = {
        verzeichnis / LENGTH_PROBE_AT: width,
        verzeichnis / LENGTH_PROBE_OVER: width + 1,
    }
    for pfad_sonde, breite in sonden.items():
        _sonde_legen(root, pfad_sonde, _probe_source(breite))
    try:
        check_out = _ruff(root, "check", "--output-format=concise")
        format_out = _ruff(root, "format", "--check")
    finally:
        for pfad_sonde in sonden:
            pfad_sonde.unlink(missing_ok=True)

    checked = check_out.stdout + check_out.stderr
    formatted = format_out.stdout + format_out.stderr
    at_name = (verzeichnis / LENGTH_PROBE_AT).relative_to(root).as_posix()
    over_name = (verzeichnis / LENGTH_PROBE_OVER).relative_to(root).as_posix()

    befunde = []

    # --- Lint-Seite: misst E501 bei genau `width`? -------------------------
    #
    # Nur, wenn die Suite sagt, dass sie das ueberhaupt tut. Sonst waere jeder
    # Lauf hier rot, und zwar aus einem Grund, der in der Konfiguration als
    # Entscheidung dokumentiert ist.
    zu_eng = sorted(_e501_lines(checked, at_name)) if lint_enforces_e501 else []
    if zu_eng:
        befunde.append(
            f"ruff check meldet E501 auf einer Zeile aus genau {width} Zeichen "
            f"({at_name}, Zeile {zu_eng}) — das Lint-Gate misst ENGER als die "
            f"deklarierten {width}.\n"
            "  Verdaechtig ist [lint.pycodestyle] max-line-length in "
            f"{config}: Sie setzt fuer E501 eine zweite Breite, die der "
            "Formatter nicht kennt."
        )
    if lint_enforces_e501 and not _e501_lines(checked, over_name):
        befunde.append(
            f"ruff check meldet kein E501 auf einer Zeile aus {width + 1} "
            f"Zeichen ({over_name}) — das Lint-Gate misst WEITER als die "
            f"deklarierten {width}, oder E501 steht nicht mehr im `select`.\n"
            f"  So oder so ist die Zahl in {config} eine Behauptung ueber eine "
            "Breite, die auf der Lint-Seite niemand durchsetzt."
        )

    # --- Format-Seite: bricht der Formatter bei genau `width`? -------------
    #
    # Gegen den Dateinamen und nicht gegen den Exit-Status: Ein echter
    # Formatverstoss anderswo im Baum ginge sonst als bestandene Sonde durch.
    if at_name in formatted:
        befunde.append(
            f"ruff format wuerde eine Zeile aus genau {width} Zeichen "
            f"umbrechen ({at_name}) — der Formatter bricht ENGER als die "
            f"deklarierten {width}."
        )
    if over_name not in formatted:
        befunde.append(
            f"ruff format laesst eine Zeile aus {width + 1} Zeichen stehen "
            f"({over_name}) — der Formatter bricht WEITER als die deklarierten "
            f"{width}, oder er liest {probe_dir} gar nicht mehr (dann sagt "
            "G5 mehr dazu).\n"
            "  `format` hat kein `select`: Hier ist das Ergebnis das einzige "
            "Kriterium, und es haengt an genau dieser Zahl."
        )

    if befunde:
        raise CheckFailed("\n".join(befunde))

    for pfad_sonde in sonden:
        if pfad_sonde.exists():
            raise CheckFailed(
                f"{pfad_sonde.name} liess sich nicht entfernen — eine "
                "liegengebliebene Sonde setzt die Gates des naechsten Laufs "
                "auf eine Datei an, die niemand geschrieben hat"
            )

    wer, laesst, beanstandet = (
        ("beide Gates", "lassen", "beanstanden")
        if lint_enforces_e501
        else ("der Formatter", "laesst", "beanstandet")
    )
    return (
        f"line-length = {width} deklariert; {wer} {laesst} {width} Zeichen "
        f"durch und {beanstandet} {width + 1}"
    )
