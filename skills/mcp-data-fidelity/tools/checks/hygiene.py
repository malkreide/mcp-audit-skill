"""Prüfung am Zustand des Repositories selbst."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ._core import CheckFailed, register

COMPILED = re.compile(r"(^|/)__pycache__/|\.py[cod]$")


@register(3, "no compiled python is tracked")
def no_compiled_python(root: Path) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise CheckFailed(
            f"{root} ist kein Git-Repository — diese Prüfung liest den Index "
            "und hätte hier nichts zu lesen:\n" + done.stderr.strip()
        )
    tracked = [line for line in done.stdout.splitlines() if COMPILED.search(line)]
    if tracked:
        raise CheckFailed(
            "kompiliertes Python ist eingecheckt (siehe .gitignore):\n"
            + "\n".join(tracked)
        )
    return "kein kompiliertes Python eingecheckt"
