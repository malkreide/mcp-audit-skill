"""Hält den Ruff-Pin an EINER Quelle fest — der Einstieg für den Hook.

Die Version steht nur in `requirements-lint.txt`. Alles andere richtet sich
danach:

  * `requirements-lint.txt`      — `ruff==X.Y.Z`, die einzige Quelle
  * `.pre-commit-config.yaml`    — `rev: vX.Y.Z` beim ruff-pre-commit-Repo,
    dieselbe Version (pre-commit baut eine eigene Umgebung und kann die
    Datei nicht lesen)
  * `.github/workflows/lint.yml` und `test.yml` — installieren mit
    `pip install -r requirements-lint.txt` und nennen KEINE eigene Zahl

Der Pre-Commit-Hook existiert, um lokal genau die Formatierung zu erzwingen,
die der lint-Job prüft. Das hält nur, solange beide dieselbe Version nennen.
Laufen die Pins auseinander, formatiert der Hook nach der einen und die CI
prüft nach der anderen: **der Hook meldet grün und die CI wird rot** — also
genau der Fehlschlag, gegen den der Hook eingeführt wurde, eine Ebene höher.

DIESE DATEI IST SEIT PHASE 2 EINE HÜLLE, KEINE IMPLEMENTIERUNG. Die
Vergleichsfunktion steht in `tools/gates/toolchain.py`, zusammen mit der der
drei Schwesterrepos — sie war in allen vieren dieselbe Logik mit einem anderen
Dateinamen. Hier bleibt der Einstiegspunkt, weil `.pre-commit-config.yaml` ihn
namentlich aufruft (`entry: python3 tools/check_ruff_pin.py`,
`language: system`) und beide READMEs ihn nennen. Eine Implementierung, zwei
Einstiege: dieser hier für den Hook, `tools/suites/mcp_audit/toolchain.py` für
die Registry.

Die Namen unten werden re-exportiert, weil `tests/test_ruff_pin.py` und
`tests/test_ruff_version.py` sie importieren. Sie zu verstecken hiesse, die
Tests der reinen Logik an den Umzug zu koppeln, und der Umzug ändert an dieser
Logik nichts.

Exit-Codes:

  0  Quelle, Hook und Workflows stimmen
  1  Befund: Abweichung, fehlender Pin, zweite Quelle, nicht verdrahtet
  2  Aufruffehler (eine der Dateien ist nicht lesbar)

Aufruf:

    python tools/check_ruff_pin.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.gates.toolchain import (  # noqa: E402
    compare,
    precommit_pin,
    requirements_pin,
    workflow_pins,
)
from tools.path_utils import force_utf8_stdio  # noqa: E402

PIN_SOURCE = Path("requirements-lint.txt")
LINT_WORKFLOW = Path(".github") / "workflows" / "lint.yml"
TEST_WORKFLOW = Path(".github") / "workflows" / "test.yml"
WORKFLOWS = (LINT_WORKFLOW, TEST_WORKFLOW)
PRECOMMIT_CONFIG = Path(".pre-commit-config.yaml")

__all__ = [
    "LINT_WORKFLOW",
    "PIN_SOURCE",
    "PRECOMMIT_CONFIG",
    "TEST_WORKFLOW",
    "WORKFLOWS",
    "compare",
    "main",
    "precommit_pin",
    "requirements_pin",
    "workflow_pins",
]


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    source = _REPO_ROOT / PIN_SOURCE
    precommit = _REPO_ROOT / PRECOMMIT_CONFIG
    workflows = {w.as_posix(): _REPO_ROOT / w for w in WORKFLOWS}

    for path in (source, precommit, *workflows.values()):
        if not path.is_file():
            print(f"Datei nicht lesbar: {path}", file=sys.stderr)
            return 2

    ok, message = compare(
        source.read_text(encoding="utf-8"),
        precommit.read_text(encoding="utf-8"),
        {name: p.read_text(encoding="utf-8") for name, p in workflows.items()},
    )
    if ok:
        print(message)
        return 0

    print(message, file=sys.stderr)
    print(
        f"\nDie Version steht nur in {PIN_SOURCE.as_posix()}: dort und `rev:` "
        f"in {PRECOMMIT_CONFIG.as_posix()} im selben Commit anheben. Die "
        "Workflows installieren mit `pip install -r` und nennen keine Zahl.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
