"""Hält die LAUFENDE ruff gegen den Pin — der eigenständige Einstieg.

`check_ruff_pin.py` vergleicht zwei Texte miteinander. Ob die ruff, die
anschliessend `ruff check` und `ruff format --check` fährt, dieselbe Version
trägt, steht in keinem der beiden Texte: Liegt eine andere weiter vorne im
PATH, laufen die Gates auf einer Version, die niemand gepinnt hat.

Nicht theoretisch: Bis 0.15.8 liess `ruff format --check .` Markdown
unberührt, seit 0.16.1 nicht mehr.

DIESE DATEI IST SEIT PHASE 2 EINE HÜLLE, KEINE IMPLEMENTIERUNG — aus demselben
Grund wie `check_ruff_pin.py` daneben. Die Logik steht in
`tools/gates/toolchain.py`; sie war in den vier Repos der Kette dieselbe, und
die reichste Fassung (`mcp-data-fidelity-skill`) listet zusätzlich die
beschattenden Binaries auf dem PATH auf. Das kommt hier mit.

`compare` und `parse_version` werden re-exportiert, weil
`tests/test_ruff_version.py` sie importiert.

Exit-Codes:

  0  die laufende ruff trägt die gepinnte Version
  1  Abweichung, kein ruff auf dem PATH, oder der Pin fehlt
  2  Aufruffehler (requirements-lint.txt ist nicht lesbar)

Aufruf:

    python tools/check_ruff_version.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.gates.toolchain import (  # noqa: E402
    VERSION_LINE,
    parse_version,
    requirements_pin,
    ruffs_on_path,
)
from tools.gates.toolchain import compare_binary as compare  # noqa: E402
from tools.path_utils import force_utf8_stdio  # noqa: E402

PIN_SOURCE = Path("requirements-lint.txt")

__all__ = [
    "PIN_SOURCE",
    "VERSION_LINE",
    "compare",
    "main",
    "parse_version",
]


def main() -> int:
    force_utf8_stdio()
    source = _REPO_ROOT / PIN_SOURCE
    if not source.is_file():
        print(f"Datei nicht lesbar: {source}", file=sys.stderr)
        return 2

    pinned = requirements_pin(source.read_text(encoding="utf-8"))

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
    ok, message = compare(
        pinned,
        done.stdout + done.stderr,
        done.returncode,
        shadowing=ruffs_on_path(),
    )
    if ok:
        print(message)
        return 0

    print(message, file=sys.stderr)
    print(f"\nGelaufene ruff: {executable}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
