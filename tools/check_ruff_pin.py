#!/usr/bin/env python3
"""Hält die beiden Ruff-Pins aneinander fest.

Ruff ist an zwei Orten gepinnt, und beide müssen dieselbe Version nennen:

  * `.github/workflows/lint.yml` — `pip install ruff==X.Y.Z`
  * `.pre-commit-config.yaml`    — `rev: vX.Y.Z` beim ruff-pre-commit-Repo

Der Pre-Commit-Hook existiert, um lokal genau die Formatierung zu erzwingen,
die der lint-Job prüft. Das hält nur, solange beide dieselbe Version nennen.
Laufen die Pins auseinander, formatiert der Hook nach der einen und die CI
prüft nach der anderen: **der Hook meldet grün und die CI wird rot** — also
genau der Fehlschlag, gegen den der Hook eingeführt wurde, eine Ebene höher.

Abgesichert wäre das sonst nur durch einen Kommentar in beiden Dateien, der
darum bittet, sie zusammen zu bumpen. Bitten ist keine Prüfung; das ist
dieselbe Regel, aus der `DRIFT-003` entstand — ein Wert, den nichts erzwingt,
driftet.

ZWEI ENTSCHEIDUNGEN
-------------------
1. **Ein fehlender Pin ist ein Befund, kein stilles Bestehen.** Fehlt eine der
   beiden Stellen, hat der Vergleich nicht stattgefunden. Dann `KEIN PIN` und
   Exit 1, statt aus der halben Evidenz «stimmt» zu drucken.

2. **Der Vergleich ist eine reine Funktion.** `compare()` nimmt die beiden
   Dateiinhalte als Strings entgegen und ist ohne Dateisystem testbar. Nur
   `main()` liest von der Platte.

Das `v`-Präfix der pre-commit-`rev` gehört zum Git-Tag, nicht zur Version, und
wird vor dem Vergleich abgeschnitten.

Bewusst Regex statt PyYAML: für zwei Felder lohnt keine Abhängigkeit, und der
Check läuft damit in einem Job, der nichts installiert hat.

Formatierung: dieselben zwei Regeln wie in `check_version_sync.py` im übrigen
Portfolio, denn diese Datei ist zum Kopieren gedacht, und dort stehen
`line-length` 88, 100, 110 und 120 nebeneinander. `ruff format` zieht einen
Ausdruck zusammen, sobald er in die jeweilige Breite passt — eine Zeile
zwischen 89 und 120 Zeichen wäre also in der einen Hälfte der Repos
formatgerecht und in der anderen nicht, und `ruff format --check` fiele beim
Kopieren um:

  - keine Zeile über 88 Zeichen — lange Ausdrücke bekommen eine lokale
    Variable statt eines Umbruchs
  - keine impliziten String-Verkettungen über mehrere Zeilen, ausser in
    Aufrufen mit Magic Trailing Comma

Exit-Codes:
  0  beide Pins nennen dieselbe Version
  1  Abweichung, oder einer der Pins fehlt
  2  Aufruffehler (eine der beiden Dateien ist nicht lesbar)

Aufruf:
    python tools/check_ruff_pin.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402

LINT_WORKFLOW = Path(".github") / "workflows" / "lint.yml"
PRECOMMIT_CONFIG = Path(".pre-commit-config.yaml")

# `pip install ruff==0.15.8` — auch mit Leerzeichen um `==` und selbst dann,
# wenn auf derselben Zeile weitere Pakete stehen.
PIP_PIN = re.compile(r"\bruff\s*==\s*([0-9][^\s'\"]*)")

# Der Eintrag des ruff-pre-commit-Repos bis zum nächsten `- repo:` oder
# Dateiende. `rev:` wird nur innerhalb dieses Ausschnitts gesucht, damit nicht
# versehentlich die `rev` eines anderen Repos gelesen wird.
RUFF_REPO_BLOCK = re.compile(
    r"^\s*-\s*repo:\s*\S*ruff-pre-commit\s*$(.*?)(?=^\s*-\s*repo:|\Z)",
    re.MULTILINE | re.DOTALL,
)
REV = re.compile(r"^\s*rev:\s*['\"]?(\S+?)['\"]?\s*$", re.MULTILINE)


def workflow_pins(text: str) -> list[str]:
    """Alle im Workflow gepinnten Ruff-Versionen."""
    return PIP_PIN.findall(text)


def precommit_pin(text: str) -> str | None:
    """Die `rev` des ruff-pre-commit-Repos, ohne `v`-Präfix.

    `None`, wenn das Repo fehlt oder keine `rev` trägt — beides bedeutet, dass
    es nichts zu vergleichen gibt, und wird von `compare()` als Befund
    behandelt.
    """
    block = RUFF_REPO_BLOCK.search(text)
    if block is None:
        return None
    rev = REV.search(block.group(1))
    if rev is None:
        return None
    return rev.group(1).removeprefix("v")


def compare(workflow_text: str, precommit_text: str) -> tuple[bool, str]:
    """Reine Vergleichsfunktion: `(stimmt_ueberein, Meldung)`.

    Ohne Datei- oder Netzzugriff, damit der Test nicht die eigene Annahme über
    das Dateiformat abbildet, sondern das echte Verhalten prüft.
    """
    pins = workflow_pins(workflow_text)
    hook = precommit_pin(precommit_text)

    workflow = LINT_WORKFLOW.as_posix()
    config = PRECOMMIT_CONFIG.as_posix()

    if not pins:
        return False, f"KEIN PIN: in {workflow} steht kein `ruff==<version>`."
    if hook is None:
        missing = "fehlt das ruff-pre-commit-Repo oder dessen `rev:`."
        return False, f"KEIN PIN: in {config} {missing}"

    divergent = sorted({p for p in pins if p != hook})
    if divergent:
        others = ", ".join(repr(p) for p in divergent)
        head = f"DRIFT: {config} pinnt Ruff auf {hook!r},"
        return False, f"{head} {workflow} auf {others}."

    return True, f"Ruff-Pin OK ({hook}; beide Stellen stimmen ueberein)."


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    workflow = _REPO_ROOT / LINT_WORKFLOW
    precommit = _REPO_ROOT / PRECOMMIT_CONFIG

    for path in (workflow, precommit):
        if not path.is_file():
            print(f"Datei nicht lesbar: {path}", file=sys.stderr)
            return 2

    ok, message = compare(
        workflow.read_text(encoding="utf-8"),
        precommit.read_text(encoding="utf-8"),
    )
    if ok:
        print(message)
        return 0

    print(message, file=sys.stderr)
    print(
        "\nBeide Stellen im selben Commit bumpen: `rev:` in "
        f"{PRECOMMIT_CONFIG.as_posix()} und `pip install ruff==…` in "
        f"{LINT_WORKFLOW.as_posix()}. Sonst formatiert der Hook nach der einen "
        "und die CI prueft nach der anderen Version.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
