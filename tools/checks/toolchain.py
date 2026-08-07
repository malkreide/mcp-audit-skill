"""Der Ruff-Pin steht an drei Stellen. Sie müssen dasselbe sagen.

Zwei davon sind Text: `pip install ruff==…` in `.github/workflows/ci.yml` und
die `rev` des Pre-Commit-Hooks. Laufen sie auseinander, formatiert der Hook
nach der einen und die CI prüft nach der anderen Version: Der Commit geht
lokal grün durch und wird erst im Pull Request rot — die teuerste Reihenfolge.
Das hält Prüfung 12 zusammen.

Die dritte ist keine Deklaration, sondern das Werkzeug selbst — der `ruff`,
den der PATH als ersten findet und den `tools/checks/ruff_gate.py`
tatsächlich startet. Ihn prüft Prüfung 18, und sie ist der Grund, warum die
beiden anderen nicht genügen: Zwei Dateien können sich einig sein, während
das ausführende Binary etwas Drittes ist. Dann haben die Prüfungen 9, 10, 11
und 17 mit einem Werkzeug gemessen, das dieses Repository nirgends nennt, und
ihr Grün gehört einer Version, die niemand gewählt hat.

Der Anlass ist gemessen und nicht gedacht: In der Entwicklungsumgebung, in der
Prüfung 17 entstand, lag ein älterer `ruff` unter `~/.local/bin` vor dem
gepinnten unter `/usr/local/bin`. Prüfung 12 war grün — sie liest ja Text —,
und der lokale Lauf maß mit 0.15.8, während die CI mit 0.16.1 prüfte.

Dasselbe gilt für die Menge der Hooks. Die Gates sind `ruff check` UND
`ruff format --check` (Prüfungen 10 und 11). Fällt einer der beiden Hooks
weg, läuft er lokal nicht mehr, und es entsteht dieselbe Bruchstelle eine
Zeile weiter unten.

Ein fehlender Pin ist ebenfalls ein Befund, nicht ein Grund zum Überspringen:
Dann hat der Vergleich nicht stattgefunden.

GRENZE, AUSDRÜCKLICH. Prüfung 18 sagt nichts darüber, welche Version
`pre-commit` installiert. Der Hook hält seine eigene Umgebung und startet
nicht den `ruff` vom PATH; was dort läuft, steht in der `rev`, und mehr als
die beiden Deklarationen gegeneinander zu halten ist von hier aus nicht
prüfbar.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from ._core import CheckFailed, register
from .ruff_gate import MISSING_RUFF

CI = ".github/workflows/ci.yml"
HOOKS = ".pre-commit-config.yaml"

CI_PIN = re.compile(r"ruff==(?P<version>\d[^\s\"']*)")
HOOK_REV = re.compile(
    r"ruff-pre-commit.*?^\s*rev:\s*v?(?P<version>\d\S*)\s*$",
    re.S | re.M,
)
REQUIRED_HOOKS = ("ruff-check", "ruff-format")

# `ruff --version` schreibt «ruff 0.16.1». Ändert sich das Format, ist das ein
# Befund und kein Durchwinken: Eine Prüfung, die ihre eigene Messung nicht
# lesen kann, hat nicht gemessen.
RUFF_VERSION = re.compile(r"^ruff (?P<version>\d+\.\d+\.\d+)")

NO_CI_PIN = (
    f"{CI} nennt kein 'ruff==<version>' — entweder wurde der Pin gelöst "
    "(dann ändert ein Upstream-Release Formatter oder Regelsatz zu "
    "einem Zeitpunkt, den niemand gewählt hat) oder der Schritt ist "
    "ganz weg"
)


def _read(root: Path, name: str) -> str:
    path = root / name
    if not path.is_file():
        raise CheckFailed(
            f"{name} fehlt — ohne die Datei gibt es nichts zu vergleichen"
        )
    return path.read_text(encoding="utf-8")


def pinned_version(root: Path) -> str:
    """Die gepinnte Version aus `ci.yml` — die eine Lesung.

    Geteilt zwischen den Prüfungen 12 und 18: Hook und Binary werden gegen
    dieselbe Stelle gehalten, nicht gegen zwei Lesungen, die auseinanderlaufen
    können. Ein zweites Regex für dieselbe Zahl wäre ein zweiter Ort, an dem
    sie veraltet.
    """
    match = CI_PIN.search(_read(root, CI))
    if not match:
        raise CheckFailed(NO_CI_PIN)
    return match.group("version")


@register(12, "the ruff pin agrees between CI and the pre-commit hook")
def ruff_pin_sync(root: Path) -> str:
    hooks = _read(root, HOOKS)

    pinned = pinned_version(root)
    hook_rev = HOOK_REV.search(hooks)
    if not hook_rev:
        raise CheckFailed(
            f"{HOOKS} nennt keine rev für ruff-pre-commit — ohne sie gibt es "
            "keine zweite Version zu vergleichen, und der lokale Hook läuft auf "
            "irgendetwas"
        )

    if pinned != hook_rev.group("version"):
        raise CheckFailed(
            f"Ruff-Pins laufen auseinander — {CI} sagt {pinned}, "
            f"der Hook sagt {hook_rev.group('version')}.\n"
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
            f"{HOOKS} führt {missing} nicht mehr. Die Prüfungen 10 und 11 "
            "prüfen beides; läuft lokal nur eines, meldet der Commit grün und "
            "erst die CI rot."
        )

    return (
        f"Ruff-Pin {pinned} in {CI} und {HOOKS}, {len(REQUIRED_HOOKS)} Hooks vorhanden"
    )


def ruffs_on_path() -> list[str]:
    """Jede ausführbare `ruff`-Datei auf dem PATH, in der Reihenfolge des PATH.

    Nur für den Befundtext. Ein blosses «falsche Version» schickt den Lesenden
    zu `pip install`, und genau dort hilft es nicht: Die gepinnte Version ist
    dann längst installiert, sie steht bloss hinter einer zweiten im PATH. Die
    Liste macht die Beschattung sichtbar, statt sie erraten zu lassen.
    """
    found = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry) / "ruff"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            found.append(str(candidate))
    return found


@register(18, "the ruff on PATH is the pinned version")
def ruff_binary_matches_pin(root: Path) -> str:
    # Gemessen wird das Werkzeug, nicht die Deklaration — dieselbe Bewegung wie
    # bei den Prüfungen 9 und 17, eine Ebene tiefer. Prüfung 12 hält zwei
    # Textstellen gegeneinander und ist grün, sobald sie sich einig sind. Ob
    # der `ruff`, der die Gates fährt, dieselbe Version hat, steht in keiner
    # der beiden Dateien.
    pinned = pinned_version(root)

    # `shutil.which` und nicht irgendein Pfad: Genau so löst `ruff_gate._ruff`
    # den Namen auf, wenn es `subprocess.run(["ruff", …])` startet. Eine
    # Prüfung, die einen anderen Binary misst als den, der die Gates fährt,
    # wäre schlimmer als keine.
    binary = shutil.which("ruff")
    if binary is None:
        raise CheckFailed(MISSING_RUFF)

    done = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, check=False
    )
    output = (done.stdout + done.stderr).strip()
    match = RUFF_VERSION.match(output)
    if not match:
        raise CheckFailed(
            f"`{binary} --version` sagt {output!r}, und daraus liest diese "
            "Prüfung keine Version der Form 'ruff X.Y.Z'.\n"
            "  Entweder hat ruff das Format geändert, oder das ist gar kein "
            "ruff. FAIL statt skip: Eine Prüfung, die ihre eigene Messung "
            "nicht lesen kann, hat nicht gemessen."
        )

    found = match.group("version")
    if found != pinned:
        others = ruffs_on_path()
        listing = "\n".join(
            f"      {path}" + ("   <- dieser laeuft" if i == 0 else "")
            for i, path in enumerate(others)
        )
        raise CheckFailed(
            f"Der ruff auf dem PATH ist {found}, gepinnt ist {pinned} ({CI}).\n"
            "  Die Prüfungen 9, 10, 11 und 17 messen mit diesem Binary. Sie "
            "haben also gegen ein Werkzeug geprüft, das dieses Repository "
            "nirgends nennt — und `format` hat kein `select`: Dort ist das "
            "Ergebnis selbst das Kriterium, und zwei Versionen formatieren "
            "verschieden.\n"
            "  Lokal grün und im Pull Request rot ist dabei der harmlose "
            "Ausgang. Der teure ist die andere Richtung.\n"
            f"  Gefunden auf dem PATH:\n{listing}\n"
            f"  Wenn {pinned} schon installiert ist, steht sie hinter einer "
            f"zweiten — sonst: pip install ruff=={pinned}"
        )

    return f"ruff {found} auf dem PATH ({binary}), wie in {CI} gepinnt"
