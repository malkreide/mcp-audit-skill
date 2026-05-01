#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-platform path utilities for the mcp-audit-skill.

Solves two recurring issues observed in real audits:

1. On Windows under Git Bash, POSIX-style paths like `/c/Users/hayal/skill`
   work for Bash tools but Claude's Read tool expects native Windows paths
   (`C:\\Users\\hayal\\skill`). The skill must convert before invoking Read.

2. Python on Windows defaults stdout/stderr to cp1252, which crashes on
   any non-ASCII output (✅, ❌, ä). Skill scripts must force UTF-8.

Usage:
    from tools.path_utils import (
        force_utf8_stdio,
        to_native_path,
        to_posix_path,
        is_windows,
    )

CLI:
    python tools/path_utils.py to-native /c/Users/foo/bar
    python tools/path_utils.py to-posix  C:\\Users\\foo\\bar
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from pathlib import PurePath, PurePosixPath, PureWindowsPath


# ---------------------------------------------------------------------------
# UTF-8 stdio
# ---------------------------------------------------------------------------

def force_utf8_stdio() -> None:
    """Reconfigure sys.stdout/stderr to UTF-8 if not already.

    Idempotent and safe to call from any script. Required at the top of
    every Python snippet the skill emits, otherwise Windows-Python will
    crash on the first non-ASCII character.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        encoding = (getattr(stream, "encoding", "") or "").lower()
        if encoding == "utf-8":
            continue
        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            continue
        try:
            wrapped = io.TextIOWrapper(buffer, encoding="utf-8", errors="replace")
        except Exception:
            continue
        setattr(sys, stream_name, wrapped)


# ---------------------------------------------------------------------------
# Path normalisation
# ---------------------------------------------------------------------------

_POSIX_DRIVE_RE = re.compile(r"^/([a-zA-Z])(/|$)")
_WIN_DRIVE_RE = re.compile(r"^([a-zA-Z]):[\\/]")


def is_windows() -> bool:
    return os.name == "nt"


def is_posix_drive_path(path: str) -> bool:
    """True for paths like '/c/Users/foo' (Git Bash on Windows)."""
    return bool(_POSIX_DRIVE_RE.match(path))


def is_windows_drive_path(path: str) -> bool:
    """True for paths like 'C:\\Users\\foo' or 'C:/Users/foo'."""
    return bool(_WIN_DRIVE_RE.match(path))


def to_native_path(path: str) -> str:
    """Convert any path representation to the OS-native form.

    On Windows: POSIX-drive paths are converted to Windows form.
    On POSIX: Windows-drive paths are converted to /<drive>/... form.
    Other paths are returned unchanged.
    """
    if not path:
        return path
    if is_windows():
        if is_posix_drive_path(path):
            return _posix_to_windows(path)
        return path.replace("/", "\\") if not path.startswith("\\\\") else path
    # On POSIX hosts, convert Windows-drive paths to POSIX form.
    if is_windows_drive_path(path):
        return _windows_to_posix(path)
    return path


def to_posix_path(path: str) -> str:
    """Convert any path representation to POSIX form (forward slashes)."""
    if not path:
        return path
    if is_windows_drive_path(path):
        return _windows_to_posix(path)
    return path.replace("\\", "/")


def to_windows_path(path: str) -> str:
    """Convert any path representation to Windows form."""
    if not path:
        return path
    if is_posix_drive_path(path):
        return _posix_to_windows(path)
    return path.replace("/", "\\")


def _posix_to_windows(path: str) -> str:
    m = _POSIX_DRIVE_RE.match(path)
    if not m:
        return path
    drive = m.group(1).upper()
    rest = path[m.end():]
    rest = rest.replace("/", "\\")
    return f"{drive}:\\{rest}"


def _windows_to_posix(path: str) -> str:
    m = _WIN_DRIVE_RE.match(path)
    if not m:
        return path
    drive = m.group(1).lower()
    rest = path[m.end():].replace("\\", "/")
    return f"/{drive}/{rest}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="path_utils",
        description="Cross-platform path conversion for mcp-audit-skill scripts.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_native = sub.add_parser("to-native", help="Convert to OS-native path form")
    p_native.add_argument("path")
    p_posix = sub.add_parser("to-posix", help="Convert to POSIX path form")
    p_posix.add_argument("path")
    p_win = sub.add_parser("to-windows", help="Convert to Windows path form")
    p_win.add_argument("path")
    args = parser.parse_args(argv)

    if args.cmd == "to-native":
        print(to_native_path(args.path))
    elif args.cmd == "to-posix":
        print(to_posix_path(args.path))
    elif args.cmd == "to-windows":
        print(to_windows_path(args.path))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
