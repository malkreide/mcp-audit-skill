"""Pruefungen an der Werkzeugkette: der ruff-Pin und die laufende ruff."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ._core import CheckFailed, register

CI = Path(".github/workflows/ci.yml")
PRE_COMMIT = Path(".pre-commit-config.yaml")

# `ruff==0.16.1` — die Ziffer vorn haelt Kommentar-Nennungen wie
# `ruff==<version>` draussen.
CI_PIN = re.compile(r"""ruff==(?P<version>[0-9][^\s"']*)""")

# `rev: v0.16.1` innerhalb des ruff-pre-commit-Blocks. Das `v` ist dort
# Konvention und gehoert nicht zur Version.
HOOK_REV = re.compile(
    r"ruff-pre-commit.*?^\s*rev:\s*v?(?P<version>[0-9]\S*)\s*$", re.M | re.S
)

# Die Ausgabeform «ruff 0.16.1» ist selbst ein Anker.
VERSION_LINE = re.compile(r"^ruff\s+(?P<version>[0-9]\S*)", re.M)


def _read(root: Path, rel: Path) -> str:
    path = root / rel
    if not path.is_file():
        raise CheckFailed(f"{rel.as_posix()} gibt es nicht — es gibt nichts zu lesen.")
    return path.read_text(encoding="utf-8")


def _pin(root: Path, *, zusatz: str = "") -> str:
    m = CI_PIN.search(_read(root, CI))
    if not m:
        raise CheckFailed(f"{CI.as_posix()} nennt kein 'ruff==<version>'.{zusatz}")
    return m.group("version")


@register(7, "the ruff pin agrees between CI and the pre-commit hook")
def ruff_pin_sync(root: Path) -> str:
    """Der Pin steht zweimal: in ci.yml und als `rev` im Pre-Commit-Hook.

    Laufen sie auseinander, formatiert der Hook nach der einen und die CI
    prueft nach der anderen Version — der Hook meldet gruen und die CI wird
    rot. Ein fehlender Pin ist ebenfalls ein Fehler: dann hat der Vergleich
    nicht stattgefunden.

    WAS DIESE PRUEFUNG NICHT TUT, und der Grund fuer Check 8 daneben: Sie
    vergleicht ZWEI TEXTE. Ob die ruff, die anschliessend `ruff format
    --check` faehrt, diese Version traegt, sagt sie nicht.
    """
    ci = _pin(root)
    m = HOOK_REV.search(_read(root, PRE_COMMIT))
    if not m:
        raise CheckFailed(
            f"{PRE_COMMIT.as_posix()} nennt keine rev fuer ruff-pre-commit."
        )
    hook = m.group("version")
    if ci != hook:
        raise CheckFailed(
            f"Ruff-Pins laufen auseinander — ci.yml {ci}, Hook {hook}. "
            "Beide im selben Commit bumpen."
        )
    return f"{ci}; beide DATEIEN stimmen ueberein"


@register(8, "the ruff on PATH is the pinned one")
def ruff_version_matches_pin(root: Path) -> str:
    """Haelt den Text gegen das laufende Programm.

    Check 7 belegt, dass ci.yml und der Hook dieselbe Zahl nennen — nicht,
    dass die ruff, die die Gates gefahren hat, diese Zahl traegt. Liegt eine
    andere ruff weiter vorne im PATH, meldet Check 7 weiter «beide Stellen
    stimmen ueberein», und das Gate laeuft daneben auf einer Version, die
    niemand gepinnt hat.

    Nicht theoretisch: Bis 0.15.8 liess `ruff format --check .` Markdown
    unberuehrt, seit 0.16.1 ist die Formatierung von Python-Bloecken in
    Markdown stabil und standardmaessig an. Gemessen im Schwester-Repo
    mcp-data-source-probe-skill (dort Check 18) und mehrfach in
    Entwicklungsumgebungen, in denen eine 0.15.8 die installierte 0.16.1
    verdeckte.

    DREI ANKER, jeder mit eigener Meldung statt still: der Pin, die
    Anwesenheit von ruff auf dem PATH, und die AUSGABEFORM `ruff <version>`.
    """
    expected = _pin(
        root,
        zusatz=(
            " — Anker weg. Ohne ihn hat diese Pruefung nichts, wogegen sie die "
            "laufende ruff haelt, und haette genau deshalb Erfolg gemeldet.\n"
            "  Check 7 meldet dasselbe und ist die Stelle, an der das zu "
            "reparieren ist."
        ),
    )

    # FAIL statt skip, wie bei den Gates selbst: Eine uebersprungene Pruefung
    # meldete «bestanden», wo «nicht gelaufen» richtig waere.
    found_at = shutil.which("ruff")
    if found_at is None:
        raise CheckFailed(
            "ruff liegt nicht auf dem PATH — diese Pruefung kann die laufende "
            f"Version nicht ermitteln.\n    pip install ruff=={expected}"
        )

    done = subprocess.run(
        [found_at, "--version"], capture_output=True, text=True, check=False
    )
    raw = (done.stdout + done.stderr).strip()
    if done.returncode != 0:
        raise CheckFailed(f"`ruff --version` endete mit {done.returncode}: {raw}")

    line = VERSION_LINE.search(raw)
    if not line:
        raise CheckFailed(
            "`ruff --version` antwortet nicht in der Form 'ruff <version>' — "
            f"gelesen wurde: {raw!r}. Hat upstream die Ausgabe geaendert, "
            "gehoert VERSION_LINE in tools/checks/toolchain.py nachgezogen; "
            "ohne das verglich diese Pruefung nichts mehr und meldete es nicht."
        )
    running = line.group("version")
    if running != expected:
        raise CheckFailed(
            f"Die ruff auf dem PATH ist {running}, gepinnt ist {expected} "
            f"({found_at}). Das Format-Gate laeuft dann auf einer anderen "
            "Version als der gepinnten. Beide Richtungen kosten: eine aeltere "
            "laesst durch, was spaeter rot wird; eine neuere beanstandet, was "
            "der Pin durchlaesst. Check 7 merkt es nicht — er vergleicht zwei "
            "Texte miteinander, nicht den Text mit dem laufenden Programm."
        )
    return f"{running} auf dem PATH, wie in ci.yml gepinnt"
