"""Die beiden Ruff-Gates — und der Wächter, der belegt, dass sie beissen.

Reihenfolge mit Absicht: Erst die Sonde (12), dann die Gates selbst (13, 14).
Ein grünes 13 heisst nur dann «der Baum ist sauber», wenn 12 vorher gezeigt
hat, dass 13 überhaupt etwas liest.

Zur Zuständigkeit: Bis 1.6.0 liefen `ruff check` und `ruff format --check` nur
in `.github/workflows/ci.yml`. `scripts/validate.sh` — die Datei, die von sich
sagt, sie sei «every gate the CI applies, in one command» — fuhr sie nicht.
Damit hatte der lokale Runner genau die Eigenschaft, gegen die sein eigener
Kopfkommentar argumentiert: Er meldete grün auf einem Baum, den die CI wegen
Lint oder Formatierung ablehnt. Jetzt stehen die Gates hier, und die CI ruft
den Runner auf, statt sie ein zweites Mal hinzuschreiben.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ._core import CheckFailed, register

# Der Pfad ist relativ und liegt bewusst unter `reference/`: Dort und nirgends
# sonst wurde das Linting schon einmal abgeschaltet.
PROBE = Path("reference/_ruff_gate_probe.py")

# F401 (ungenutzter Import) und ein Formatverstoss in derselben Datei — so
# testet eine Sonde beide Gates.
PROBE_SOURCE = "import os\nx   =    1\n"

MISSING_RUFF = (
    "ruff liegt nicht auf dem PATH.\n"
    "FAIL statt skip, aus demselben Grund wie bei den Vorlagen-"
    "Abhängigkeiten: Eine übersprungene Prüfung meldete «bestanden», wo "
    "«nicht gelaufen» richtig wäre.\n"
    "  Die gepinnte Version steht in .github/workflows/ci.yml und in\n"
    "  .pre-commit-config.yaml — beide müssen übereinstimmen (Check 16)."
)


def _ruff(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Ruft ruff so auf, wie die CI es tut.

    `.` statt `reference/`: Ein explizit genannter Pfad umgeht `exclude` und
    würde genau die Lücke zudecken, die Check 12 sucht. `--no-cache`, damit
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


@register(12, "the ruff gate still bites on reference/")
def ruff_gate_bites(root: Path) -> str:
    # `ruff check` und `ruff format --check` sind die einzigen Gates dieses
    # Repos, deren Anker nicht in ihrem eigenen Befund auftaucht. Jede andere
    # Prüfung hier wird rot, wenn ihr Anker verschwindet; die Ruff-Schritte
    # melden auf einem Baum, in dem `reference/` aus der Konfiguration
    # ausgeschlossen wurde, eine Warnung auf stderr und Exit 0 — «All checks
    # passed!», ohne eine Zeile gelesen zu haben. Grün wird dann ausgerechnet
    # der Code, den Leute kopieren.
    #
    # Der Fall ist nicht hypothetisch: In ruff.toml stand für genau diese
    # Dateien schon einmal `select = []` (die Begründung und ihre Widerlegung
    # stehen dort). Damals hat es niemand gemerkt, weil nichts rot wurde.
    #
    # Geprüft wird deshalb nicht die Konfiguration, sondern die Wirkung: Eine
    # absichtlich fehlerhafte Datei liegt kurz unter `reference/`, und beide
    # Gates müssen sie beim Namen nennen. Ein Konfigurationsleser müsste
    # `exclude`, `[lint] exclude`, `[format] exclude`, `select` und
    # `per-file-ignores` einzeln kennen — und verpasste den Schalter, den ruff
    # erst nach diesem Commit bekommt.
    if not (root / "reference").is_dir():
        raise CheckFailed(
            "reference/ fehlt — Anker weg; die Sonde hätte kein Verzeichnis, "
            "in dem sie das Gate testen könnte"
        )
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
            f"{PROBE} liess sich nicht entfernen — bitte von Hand löschen"
        )
    return "beide Ruff-Gates beanstanden eine fehlerhafte Datei unter reference/"


@register(13, "ruff check passes on the whole tree")
def ruff_check(root: Path) -> str:
    done = _ruff(root, "check", "--output-format=concise")
    if done.returncode != 0:
        raise CheckFailed(
            "ruff check hat Befunde — dieselbe Invokation, die die CI fährt:\n"
            f"{done.stdout}{done.stderr}".rstrip()
        )
    return "ruff check: keine Befunde"


@register(14, "ruff format leaves the tree unchanged")
def ruff_format(root: Path) -> str:
    done = _ruff(root, "format", "--check")
    if done.returncode != 0:
        raise CheckFailed(
            "ruff format würde Dateien ändern — dieselbe Invokation, die die "
            f"CI fährt. `ruff format .` räumt es auf:\n"
            f"{done.stdout}{done.stderr}".rstrip()
        )
    return "ruff format: nichts zu ändern"
