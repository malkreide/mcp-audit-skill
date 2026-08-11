"""Hält die beiden Ruff-Pins aneinander fest — der Einstieg für den Hook.

Ruff ist an zwei Orten gepinnt, und beide müssen dieselbe Version nennen:

  * `.github/workflows/lint.yml` — `pip install ruff==X.Y.Z`
  * `.pre-commit-config.yaml`    — `rev: vX.Y.Z` beim ruff-pre-commit-Repo

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

  0  beide Pins nennen dieselbe Version
  1  Abweichung, oder einer der Pins fehlt
  2  Aufruffehler (eine der beiden Dateien ist nicht lesbar)

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
    workflow_pins,
)
from tools.path_utils import force_utf8_stdio  # noqa: E402

LINT_WORKFLOW = Path(".github") / "workflows" / "lint.yml"
PRECOMMIT_CONFIG = Path(".pre-commit-config.yaml")

__all__ = [
    "LINT_WORKFLOW",
    "PRECOMMIT_CONFIG",
    "compare",
    "main",
    "precommit_pin",
    "workflow_pins",
]


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
