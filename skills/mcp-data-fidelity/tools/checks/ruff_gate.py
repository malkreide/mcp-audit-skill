"""Die beiden Ruff-Gates — und die Wächter, die belegen, dass sie beissen.

Reihenfolge mit Absicht: Erst die Sonde (9), dann die Gates selbst (10, 11).
Ein grünes 10 heisst nur dann «der Baum ist sauber», wenn 9 vorher gezeigt
hat, dass 10 überhaupt etwas liest.

Prüfung 17 stellt dieselbe Frage eine Ebene feiner. 9 fragt, **ob** die Gates
auf `reference/` greifen; 17 fragt, **mit welcher Breite** — der einen Zahl,
die beide lesen. Sie ist deshalb eine eigene Prüfung und kein Zusatz zu 9:
Ein Gate, das greift, aber auf einer Breite misst, die niemand hier
aufgeschrieben hat, ist grün aus einem Grund, den das Repository nicht besitzt.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ._core import CheckFailed, register
from .references import reference_sources

# Der Pfad liegt bewusst unter `reference/`: Dort und nirgends sonst wurde das
# Linting in diesem Repo schon einmal abgeschaltet.
PROBE = Path("reference/_ruff_gate_probe.py")

# F401 (ungenutzter Import) und ein Formatverstoss in derselben Datei — so
# testet eine Sonde beide Gates. F821 wäre untauglich: Genau diese Regel ist
# für `reference/` absichtlich unterdrückt, die Sonde schlüge nie an.
PROBE_SOURCE = "import os\nx   =    1\n"

MISSING_RUFF = (
    "ruff liegt nicht auf dem PATH.\n"
    "FAIL statt skip: Eine übersprungene Prüfung meldete «bestanden», wo "
    "«nicht gelaufen» richtig wäre.\n"
    "  Die gepinnte Version steht in .github/workflows/ci.yml und in\n"
    "  .pre-commit-config.yaml — beide müssen übereinstimmen (Prüfung 12)."
)


def _ruff(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Ruft ruff so auf, wie die CI es tut.

    `.` statt `reference/`: Ein explizit genannter Pfad umgeht `exclude` und
    würde genau die Lücke zudecken, die Prüfung 9 sucht. `--no-cache`, damit
    ein Ergebnis aus einem früheren Lauf nicht als aktuelles durchgeht.
    """
    if shutil.which("ruff") is None:
        raise CheckFailed(MISSING_RUFF)
    return subprocess.run(
        ["ruff", *args, "--no-cache", "."],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


@register(9, "the ruff gate still bites on reference/")
def ruff_gate_bites(root: Path) -> str:
    # Wird `reference/` in ruff.toml ausgeschlossen — per `exclude`,
    # `[lint] exclude`, `[format] exclude`, `select = []` oder einem
    # pauschalen `per-file-ignores` —, melden beide Gates eine Warnung auf
    # stderr und Exit 0: «All checks passed!», ohne eine Zeile gelesen zu
    # haben. Grün wird dann ausgerechnet der Code, den Leute kopieren.
    #
    # Der Fall ist nicht hypothetisch, und zwar in genau diesem Repo: Für
    # diese Dateien stand hier schon einmal `select = []` (Begründung und
    # Widerlegung stehen in ruff.toml). Gemerkt hat es niemand, weil nichts
    # rot wurde.
    #
    # Geprüft wird deshalb nicht die Konfiguration, sondern die Wirkung. Ein
    # Konfigurationsleser müsste alle fünf Schalter einzeln kennen — und
    # verpasste den, den ruff erst nach diesem Commit bekommt.
    reference_sources(root)
    probe = root / PROBE
    if probe.exists():
        raise CheckFailed(
            f"{PROBE} liegt schon da. Die Sonde legt diese Datei selbst an und "
            "räumt sie weg; existiert sie vorher, würde diese Prüfung sie "
            "überschreiben und löschen. Bitte von Hand prüfen und entfernen."
        )

    probe.write_text(PROBE_SOURCE, encoding="utf-8")
    try:
        check_out = _ruff(root, "check", "--output-format=concise")
        format_out = _ruff(root, "format", "--check")
    finally:
        probe.unlink(missing_ok=True)

    # Gegen den Dateinamen, nicht gegen den Exit-Status: Ein anderer, echter
    # Fund anderswo im Baum ginge sonst als bestandene Sonde durch, und diese
    # Prüfung wäre grün, ohne die Vorlagen geprüft zu haben.
    needle = PROBE.name
    findings = []
    if needle not in check_out.stdout + check_out.stderr:
        findings.append(
            f"ruff check hat {PROBE} nicht beanstandet — das Lint-Gate greift "
            "auf reference/ nicht mehr. Verdächtig sind exclude, select und "
            "per-file-ignores in ruff.toml.\n"
            f"ruff check meldete:\n{check_out.stdout}{check_out.stderr}".rstrip()
        )
    if needle not in format_out.stdout + format_out.stderr:
        findings.append(
            f"ruff format --check hat {PROBE} nicht beanstandet — das "
            "Format-Gate greift auf reference/ nicht mehr. Verdächtig sind "
            "exclude und [format] exclude in ruff.toml.\n"
            f"ruff format meldete:\n{format_out.stdout}{format_out.stderr}".rstrip()
        )
    if findings:
        raise CheckFailed("\n".join(findings))

    if probe.exists():
        raise CheckFailed(
            f"{PROBE} liess sich nicht entfernen — eine liegengebliebene Sonde "
            "setzt die Prüfungen 1, 10 und 11 des nächsten Laufs auf eine "
            "Datei an, die niemand geschrieben hat"
        )
    return "beide Ruff-Gates beanstanden eine fehlerhafte Datei unter reference/"


@register(10, "ruff check passes on the whole tree")
def ruff_check(root: Path) -> str:
    done = _ruff(root, "check", "--output-format=concise")
    if done.returncode != 0:
        raise CheckFailed(
            "ruff check hat Befunde — dieselbe Invokation, die die CI fährt:\n"
            f"{done.stdout}{done.stderr}".rstrip()
        )
    return "ruff check: keine Befunde"


@register(11, "ruff format leaves the tree unchanged")
def ruff_format(root: Path) -> str:
    done = _ruff(root, "format", "--check")
    if done.returncode != 0:
        raise CheckFailed(
            "ruff format würde Dateien ändern — dieselbe Invokation, die die "
            "CI fährt. `ruff format .` räumt es auf:\n"
            f"{done.stdout}{done.stderr}".rstrip()
        )
    return "ruff format: nichts zu ändern"


CONFIG = "ruff.toml"

# Die zweite Sonde, in zwei Dateien: eine Zeile aus genau `line-length`
# Zeichen, und eine aus einer mehr. Zwei Dateien und nicht eine, weil
# `ruff format --check` je DATEI urteilt und nicht je Zeile — der gute und der
# schlechte Fall müssen deshalb auseinanderliegen.
LENGTH_PROBE_AT = Path("reference/_line_length_probe_at.py")
LENGTH_PROBE_OVER = Path("reference/_line_length_probe_over.py")

LINE_LENGTH = re.compile(r"^\s*line-length\s*=\s*(?P<value>\d+)\s*$", re.M)

# Unterhalb dieser Breite baut `_call_of` keine gültige Zeile mehr. Ein Befund
# und kein Überspringen: Eine Prüfung, die sich bei einem unerwarteten Wert
# selbst abschaltet, meldet «bestanden», wo «nicht gelaufen» richtig wäre.
MIN_WIDTH = 40

NO_LINE_LENGTH = (
    f"{CONFIG} nennt kein 'line-length = <N>' — Anker weg oder nie gesetzt.\n"
    "  Dann gilt ruffs Vorgabe, und die Spaltenbreite dieses Repos ist eine "
    "Entscheidung von upstream: Die nächste Änderung daran formatiert "
    "unberührten Code um.\n"
    "  Das trifft `format` härter als `check` — `format` hat kein `select`, "
    "dort ist das Ergebnis selbst das Kriterium."
)


def _comment_of(width: int) -> str:
    """Eine Kommentarzeile aus genau `width` Zeichen, an Leerzeichen umbrechbar.

    Umbrechbar mit Absicht. Ruff meldet E501 NICHT auf einer überlangen Zeile,
    die sich nicht umbrechen lässt — ein langer URL etwa, wie er in
    `tools/checks/catalogue.py` steht. Eine Sonde aus einem einzigen langen
    Wort hätte also nichts gemessen und genau das als bestanden gemeldet.
    """
    body = ("ab " * width)[: width - 2]
    if body.endswith(" "):
        # Sonst stünde am Zeilenende ein Leerzeichen, und die Sonde schlüge
        # über W291 an statt über E501 — rot aus dem falschen Grund.
        body = body[:-1] + "c"
    return "# " + body


def _call_of(width: int) -> str:
    """Ein Aufruf aus genau `width` Zeichen, den der Formatter umbrechen kann.

    Für das Format-Gate. Der Formatter kennt kein E501 und kein `select`; sein
    einziges Kriterium ist, ob er die Zeile anfassen würde. Zwei Argumente,
    damit es eine Stelle gibt, an der er brechen kann.
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


@register(17, "the declared line length is the width both gates enforce")
def line_length_effective(root: Path) -> str:
    # Geprüft wird die Wirkung, nicht der Eintrag — dieselbe Begründung wie bei
    # Prüfung 9. Dass `line-length = 88` in ruff.toml steht, heisst noch nicht,
    # dass bei 88 gemessen wird: `[lint.pycodestyle] max-line-length` setzt für
    # E501 eine zweite Breite, ohne dass der Formatter davon erfährt. Dann
    # stünde in der Konfiguration eine Zahl, die nur eines der beiden Gates
    # einhält, und der Eintrag läse sich weiterhin richtig.
    config = root / CONFIG
    if not config.is_file():
        raise CheckFailed(
            f"{CONFIG} fehlt — ohne die Datei hat diese Prüfung keine "
            "deklarierte Breite, gegen die sie messen könnte"
        )
    declared = LINE_LENGTH.search(config.read_text(encoding="utf-8"))
    if not declared:
        raise CheckFailed(NO_LINE_LENGTH)
    width = int(declared.group("value"))
    if width < MIN_WIDTH:
        raise CheckFailed(
            f"{CONFIG} deklariert line-length = {width}. Unter {MIN_WIDTH} kann "
            "diese Prüfung keine Sonde mehr bauen, die genau eine Zeichenbreite "
            "trifft — sie würde ab hier nichts mehr messen und das als "
            "bestanden melden."
        )

    reference_sources(root)
    probes = {LENGTH_PROBE_AT: width, LENGTH_PROBE_OVER: width + 1}
    for probe in probes:
        if (root / probe).exists():
            raise CheckFailed(
                f"{probe} liegt schon da. Die Sonde legt diese Datei selbst an "
                "und räumt sie weg; existiert sie vorher, würde diese Prüfung "
                "sie überschreiben und löschen. Bitte von Hand prüfen und "
                "entfernen."
            )

    for probe, at in probes.items():
        (root / probe).write_text(_probe_source(at), encoding="utf-8")
    try:
        check_out = _ruff(root, "check", "--output-format=concise")
        format_out = _ruff(root, "format", "--check")
    finally:
        for probe in probes:
            (root / probe).unlink(missing_ok=True)

    checked = check_out.stdout + check_out.stderr
    formatted = format_out.stdout + format_out.stderr
    at_name, over_name = LENGTH_PROBE_AT.as_posix(), LENGTH_PROBE_OVER.as_posix()

    findings = []

    # --- Lint-Seite: misst E501 bei genau `width`? -----------------------
    too_narrow = sorted(_e501_lines(checked, at_name))
    if too_narrow:
        findings.append(
            f"ruff check meldet E501 auf einer Zeile aus genau {width} Zeichen "
            f"({at_name}, Zeile {too_narrow}) — das Lint-Gate misst ENGER als "
            f"die deklarierten {width}.\n"
            "  Verdächtig ist [lint.pycodestyle] max-line-length in "
            f"{CONFIG}: Sie setzt für E501 eine zweite Breite, die der "
            "Formatter nicht kennt."
        )
    if not _e501_lines(checked, over_name):
        findings.append(
            f"ruff check meldet kein E501 auf einer Zeile aus {width + 1} "
            f"Zeichen ({over_name}) — das Lint-Gate misst WEITER als die "
            f"deklarierten {width}, oder E501 steht nicht mehr im `select`.\n"
            f"  So oder so ist die Zahl in {CONFIG} eine Behauptung über eine "
            "Breite, die auf der Lint-Seite niemand durchsetzt."
        )

    # --- Format-Seite: bricht der Formatter bei genau `width`? -----------
    #
    # Gegen den Dateinamen und nicht gegen den Exit-Status: Ein echter
    # Formatverstoss anderswo im Baum ginge sonst als bestandene Sonde durch.
    if at_name in formatted:
        findings.append(
            f"ruff format würde eine Zeile aus genau {width} Zeichen umbrechen "
            f"({at_name}) — der Formatter bricht ENGER als die deklarierten "
            f"{width}."
        )
    if over_name not in formatted:
        findings.append(
            f"ruff format lässt eine Zeile aus {width + 1} Zeichen stehen "
            f"({over_name}) — der Formatter bricht WEITER als die deklarierten "
            f"{width}, oder er liest `reference/` gar nicht mehr (dann sagt "
            "Prüfung 9 mehr dazu).\n"
            f"  `format` hat kein `select`: Hier ist das Ergebnis das einzige "
            "Kriterium, und es hängt an genau dieser Zahl."
        )

    if findings:
        raise CheckFailed("\n".join(findings))

    for probe in probes:
        if (root / probe).exists():
            raise CheckFailed(
                f"{probe} liess sich nicht entfernen — eine liegengebliebene "
                "Sonde setzt die Prüfungen 1, 10 und 11 des nächsten Laufs auf "
                "eine Datei an, die niemand geschrieben hat"
            )

    return (
        f"line-length = {width} deklariert; beide Gates lassen {width} Zeichen "
        f"durch und beanstanden {width + 1}"
    )
