"""Der Ruff-Pin steht an zwei Stellen. Sie müssen dasselbe sagen.

Einmal als `pip install ruff==…` in `.github/workflows/ci.yml`, einmal als
`rev` des Pre-Commit-Hooks. Laufen sie auseinander, formatiert der Hook nach
der einen und die CI prüft nach der anderen Version: Der Commit geht lokal
grün durch und wird erst im Pull Request rot — die teuerste Reihenfolge.

Dasselbe gilt für die Menge der Hooks. Die Gates sind `ruff check` UND
`ruff format --check` (Checks 13 und 14). Fällt einer der beiden Hooks weg,
läuft er lokal nicht mehr, und es entsteht dieselbe Bruchstelle eine Zeile
weiter unten.

Ein fehlender Pin ist ebenfalls ein Befund, nicht ein Grund zum Überspringen:
Dann hat der Vergleich nicht stattgefunden.

Check 18 schliesst die Lücke, die Check 16 offen lässt, und der Unterschied
ist der ganze Punkt: Check 16 vergleicht ZWEI TEXTE miteinander. Er belegt,
dass beide Dateien dieselbe Zahl nennen — nicht, dass die ruff, die gleich
Checks 12, 13 und 14 fährt, diese Zahl trägt. Ein `ruff` weiter vorne auf dem
PATH als das gerade installierte macht Check 16 grün melden («Ruff-Pin 0.16.1
… stimmen überein»), während der Lauf daneben auf einer anderen Version
stattfindet. Genau die Auskunft, gegen die dieses Repository angeschrieben
ist: eine Prüfung, die etwas bestätigt, das sie nicht gemessen hat.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ._core import CheckFailed, register

CI = ".github/workflows/ci.yml"
HOOKS = ".pre-commit-config.yaml"

CI_PIN = re.compile(r"ruff==(?P<version>\d[^\s\"']*)")
HOOK_REV = re.compile(
    r"ruff-pre-commit.*?^\s*rev:\s*v?(?P<version>\d\S*)\s*$",
    re.S | re.M,
)
REQUIRED_HOOKS = ("ruff-check", "ruff-format")

# Die Ausgabe von `ruff --version` ist selbst ein Anker: «ruff 0.16.1». Ändert
# upstream ihre Form, darf diese Prüfung nicht stillschweigend nichts mehr
# vergleichen — sie sagt dann, dass sie die Antwort nicht lesen konnte.
VERSION_LINE = re.compile(r"^ruff\s+(?P<version>\d\S*)")


def _read(root: Path, name: str) -> str:
    path = root / name
    if not path.is_file():
        raise CheckFailed(
            f"{name} fehlt — ohne die Datei gibt es nichts zu vergleichen"
        )
    return path.read_text(encoding="utf-8")


@register(16, "the ruff pin agrees between CI and the pre-commit hook")
def ruff_pin_sync(root: Path) -> str:
    ci = _read(root, CI)
    hooks = _read(root, HOOKS)

    ci_pin = CI_PIN.search(ci)
    if not ci_pin:
        raise CheckFailed(
            f"{CI} nennt kein 'ruff==<version>' — entweder wurde der Pin "
            "gelöst (dann ändert ein Upstream-Release Formatter oder Regelsatz "
            "zu einem Zeitpunkt, den niemand gewählt hat) oder der Schritt ist "
            "ganz weg"
        )
    hook_rev = HOOK_REV.search(hooks)
    if not hook_rev:
        raise CheckFailed(
            f"{HOOKS} nennt keine rev für ruff-pre-commit — ohne sie gibt es "
            "keine zweite Version zu vergleichen, und der lokale Hook läuft "
            "auf irgendetwas"
        )

    if ci_pin.group("version") != hook_rev.group("version"):
        raise CheckFailed(
            f"Ruff-Pins laufen auseinander — {CI} sagt "
            f"{ci_pin.group('version')}, der Hook sagt "
            f"{hook_rev.group('version')}.\n"
            "  Der Hook formatiert dann nach der einen und die CI prüft nach "
            "der anderen Version: lokal grün, im Pull Request rot. Beide im "
            "selben Commit anheben."
        )

    missing = [
        hook
        for hook in REQUIRED_HOOKS
        if not re.search(rf"^\s*-\s*id:\s*{re.escape(hook)}\s*$", hooks, re.M)
    ]
    if missing:
        raise CheckFailed(
            f"{HOOKS} führt {missing} nicht mehr. Die Checks 13 und 14 prüfen "
            "beides; läuft lokal nur eines, meldet der Commit grün und erst "
            "die CI rot."
        )

    return (
        f"Ruff-Pin {ci_pin.group('version')} in {CI} und {HOOKS}, "
        f"{len(REQUIRED_HOOKS)} Hooks vorhanden"
    )


@register(18, "the ruff on PATH is the pinned one")
def ruff_version_matches_pin(root: Path) -> str:
    # Der Pin kommt aus ci.yml, nicht aus einer Konstante hier. Eine dritte
    # Stelle für dieselbe Zahl wäre eine dritte Stelle zum Auseinanderlaufen —
    # dieselbe Begründung, aus der ruff nicht in requirements-dev.txt steht.
    ci = _read(root, CI)
    pinned = CI_PIN.search(ci)
    if not pinned:
        raise CheckFailed(
            f"{CI} nennt kein 'ruff==<version>' — Anker weg. Ohne ihn hat "
            "diese Prüfung nichts, wogegen sie die laufende ruff hält, und "
            "sie hätte genau deshalb Erfolg gemeldet.\n"
            "  Check 16 meldet dasselbe und ist die Stelle, an der das zu "
            "reparieren ist."
        )
    expected = pinned.group("version")

    # FAIL statt skip, wie bei den Gates selbst: Eine übersprungene Prüfung
    # meldete «bestanden», wo «nicht gelaufen» richtig wäre.
    found_at = shutil.which("ruff")
    if found_at is None:
        raise CheckFailed(
            "ruff liegt nicht auf dem PATH — diese Prüfung kann die laufende "
            f"Version nicht ermitteln.\n    pip install ruff=={expected}"
        )

    done = subprocess.run(
        ["ruff", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise CheckFailed(
            f"`ruff --version` endete mit {done.returncode} — die laufende "
            f"Version liess sich nicht ermitteln:\n"
            f"{done.stdout}{done.stderr}".rstrip()
        )

    line = VERSION_LINE.match(done.stdout.strip())
    if not line:
        raise CheckFailed(
            "`ruff --version` antwortet nicht in der Form 'ruff <version>' — "
            f"gelesen wurde {done.stdout.strip()!r}.\n"
            "  Der Anker ist die Ausgabeform selbst. Hat upstream sie "
            "geändert, gehört VERSION_LINE in tools/checks/toolchain.py "
            "nachgezogen; ohne das vergliche diese Prüfung nichts mehr und "
            "meldete es nicht."
        )
    running = line.group("version")

    if running != expected:
        raise CheckFailed(
            f"Die ruff auf dem PATH ist {running}, gepinnt ist {expected}.\n"
            f"  Gefunden unter: {found_at}\n"
            "  Die Checks 12, 13 und 14 fahren dann eine andere Version als "
            "die CI. Beide Richtungen kosten: Eine ältere lässt durch, was im "
            "Pull Request rot wird; eine neuere beanstandet, was die CI "
            "durchlässt. Check 16 merkt es nicht — er vergleicht zwei Texte "
            "miteinander, nicht den Text mit dem laufenden Programm.\n"
            f"    pip install ruff=={expected}\n"
            "  Ist die richtige Version schon installiert, liegt eine zweite "
            "weiter vorne auf dem PATH:\n"
            "    which -a ruff"
        )

    return f"ruff {running} auf dem PATH, wie in {CI} gepinnt"
