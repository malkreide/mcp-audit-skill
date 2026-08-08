"""Der ruff-Pin steht in ci.yml und in .pre-commit-config.yaml — beide gleich.

Der Pin steht zweimal: oben in ci.yml als `pip install ruff==…` und als `rev`
im Pre-Commit-Hook. Laufen sie auseinander, formatiert der Hook nach der einen
und die CI prueft nach der anderen Version — der Hook meldet gruen und die CI
wird rot. Ein fehlender Pin ist ebenfalls ein Fehler: dann hat der Vergleich
nicht stattgefunden.

WAS DIESER CHECK NICHT TUT, und das ist der Grund, warum es `ruff_version.py`
daneben gibt: Er vergleicht ZWEI TEXTE. Ob die ruff, die anschliessend
`ruff format --check` faehrt, diese Version traegt, sagt er nicht.
"""

from __future__ import annotations

import pathlib
import re
import sys

from _ruff_pin import lies_pin

PRE_COMMIT = pathlib.Path(".pre-commit-config.yaml")

# `rev: v0.16.1` innerhalb des ruff-pre-commit-Blocks, bis zum naechsten
# `hooks:`. Das `v` ist dort Konvention und gehoert nicht zur Version.
HOOK_REV = re.compile(
    r"ruff-pre-commit.*?^\s*rev:\s*v?(?P<version>[0-9]\S*)\s*$",
    re.M | re.S,
)


def lies_hook_rev() -> str:
    if not PRE_COMMIT.is_file():
        sys.exit(f"{PRE_COMMIT} gibt es nicht — es gibt nichts zu vergleichen.")
    m = HOOK_REV.search(PRE_COMMIT.read_text(encoding="utf-8"))
    if not m:
        sys.exit(f"::error::{PRE_COMMIT} nennt keine rev fuer ruff-pre-commit.")
    return m.group("version")


def main() -> None:
    ci = lies_pin()
    hook = lies_hook_rev()
    if ci != hook:
        sys.exit(
            f"::error::Ruff-Pins laufen auseinander — ci.yml {ci}, Hook {hook}. "
            "Beide im selben Commit bumpen."
        )
    print(f"Ruff-Pin OK ({ci}; beide DATEIEN stimmen ueberein).")


if __name__ == "__main__":
    main()
