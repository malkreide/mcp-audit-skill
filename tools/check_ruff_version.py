"""Die ruff auf dem PATH trägt die Version, die lint.yml pinnt.

`tools/check_ruff_pin.py` vergleicht ZWEI TEXTE: `lint.yml` und
`.pre-commit-config.yaml`. Er belegt, dass beide dieselbe Zahl nennen — nicht,
dass die ruff, die `ruff check .` und `ruff format --check .` gefahren hat,
diese Zahl trägt. Liegt eine andere ruff weiter vorne im PATH als die gerade
installierte, meldet er weiter «beide Stellen stimmen überein», und die Gates
laufen daneben auf einer Version, die niemand gepinnt hat.

Für dieses Portfolio ist das nicht theoretisch: Bis ruff 0.15.8 liess
`ruff format --check .` Markdown unberührt, seit 0.16.1 ist die Formatierung
von Python-Blöcken in Markdown stabil und standardmässig an. Genau der
Unterschied, gegen den der Pin existiert — und ohne diesen Check hätte der Pin
ihn nur behauptet. Gemessen in `mcp-data-source-probe-skill` (dort Check 18)
und noch einmal in einer Entwicklungsumgebung, in der eine 0.15.8 unter
`/root/.local/bin` die frisch installierte 0.16.1 verdeckte.

DREI ANKER, und jeder fällt mit eigener Meldung statt still: der Pin in
`lint.yml`, die Anwesenheit von ruff auf dem PATH, und die AUSGABEFORM
`ruff <version>`. Ändert upstream die Form, darf dieser Check nicht
stillschweigend nichts mehr vergleichen — er sagt dann, dass er die Antwort
nicht lesen konnte.

Aufruf:

    python tools/check_ruff_version.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.check_ruff_pin import LINT_WORKFLOW, workflow_pins  # noqa: E402
from tools.path_utils import force_utf8_stdio  # noqa: E402

# Die Ausgabeform «ruff 0.16.1» ist selbst ein Anker.
VERSION_LINE = re.compile(r"^ruff\s+([0-9]\S*)", re.MULTILINE)


def parse_version(raw: str) -> str | None:
    """Die Version aus der Ausgabe von `ruff --version`, sonst `None`."""
    match = VERSION_LINE.search(raw)
    return match.group(1) if match else None


def compare(pinned: str | None, raw: str, returncode: int) -> tuple[bool, str]:
    """Reine Vergleichsfunktion: `(stimmt_ueberein, Meldung)`.

    Alles, was schiefgehen kann, ist hier entscheidbar — ohne PATH, ohne
    Unterprozess. Genau deshalb ist dieser Check testbar und der Schritt, den
    er ersetzt, war es nicht.
    """
    if pinned is None:
        return False, (
            f"{LINT_WORKFLOW.as_posix()} nennt kein `ruff==<version>` — Anker "
            "weg. Ohne ihn hat dieser Check nichts, wogegen er die laufende "
            "ruff hält, und hätte genau deshalb Erfolg gemeldet."
        )
    if returncode != 0:
        return False, f"`ruff --version` endete mit {returncode}: {raw.strip()}"

    running = parse_version(raw)
    if running is None:
        return False, (
            "`ruff --version` antwortet nicht in der Form 'ruff <version>' — "
            f"gelesen wurde: {raw.strip()!r}. Hat upstream die Ausgabe "
            "geändert, gehört VERSION_LINE hier nachgezogen; ohne das "
            "verglich dieser Check nichts mehr und meldete es nicht."
        )
    if running != pinned:
        return False, (
            f"Die ruff auf dem PATH ist {running}, gepinnt ist {pinned}. Die "
            "Gates laufen dann auf einer anderen Version als der gepinnten. "
            "Beide Richtungen kosten: eine ältere lässt durch, was später rot "
            "wird; eine neuere beanstandet, was der Pin durchlässt. Der "
            "Pin-Sync merkt es nicht — er vergleicht zwei Texte miteinander, "
            "nicht den Text mit dem laufenden Programm."
        )
    return True, f"Ruff-Version OK ({running} auf dem PATH, wie gepinnt)."


def main() -> int:
    force_utf8_stdio()
    workflow = _REPO_ROOT / LINT_WORKFLOW
    if not workflow.is_file():
        print(f"Datei nicht lesbar: {workflow}", file=sys.stderr)
        return 2

    pins = workflow_pins(workflow.read_text(encoding="utf-8"))
    pinned = pins[0] if pins else None

    executable = shutil.which("ruff")
    if executable is None:
        # FAIL statt skip: ein übersprungener Schritt meldete «bestanden», wo
        # «nicht gelaufen» richtig wäre.
        print(
            "ruff liegt nicht auf dem PATH — die laufende Version lässt sich "
            "nicht ermitteln.",
            file=sys.stderr,
        )
        return 1

    done = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    ok, message = compare(pinned, done.stdout + done.stderr, done.returncode)
    if ok:
        print(message)
        return 0

    print(message, file=sys.stderr)
    print(f"\nGelaufene ruff: {executable}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
