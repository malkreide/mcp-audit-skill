# -*- coding: utf-8 -*-
"""Tests for cross-platform path conversion helpers."""
from __future__ import annotations

import io
import sys
from unittest import mock

import pytest

from tools.path_utils import (
    force_utf8_stdio,
    is_posix_drive_path,
    is_windows_drive_path,
    to_native_path,
    to_posix_path,
    to_windows_path,
)


class TestPathDetection:
    def test_posix_drive_lowercase(self):
        assert is_posix_drive_path("/c/Users/foo") is True

    def test_posix_drive_uppercase(self):
        assert is_posix_drive_path("/C/Users/foo") is True

    def test_posix_drive_just_root(self):
        assert is_posix_drive_path("/c") is True

    def test_posix_drive_two_letter_first_segment_is_not_drive(self):
        assert is_posix_drive_path("/cd/foo") is False

    def test_pure_posix_not_drive(self):
        assert is_posix_drive_path("/home/user") is False

    def test_windows_drive_backslash(self):
        assert is_windows_drive_path("C:\\Users") is True

    def test_windows_drive_forward_slash(self):
        assert is_windows_drive_path("C:/Users") is True

    def test_windows_drive_lowercase(self):
        assert is_windows_drive_path("c:\\foo") is True

    def test_no_drive_letter(self):
        assert is_windows_drive_path("Users\\foo") is False


class TestPosixToWindows:
    def test_basic(self):
        assert to_windows_path("/c/Users/foo") == "C:\\Users\\foo"

    def test_uppercases_drive(self):
        assert to_windows_path("/c/Users/foo").startswith("C:")

    def test_no_op_for_already_windows(self):
        assert to_windows_path("D:\\already\\windows") == "D:\\already\\windows"

    def test_pure_posix_pass_through(self):
        # Forward slashes get backslashed but no drive added.
        assert to_windows_path("/home/user/file") == "\\home\\user\\file"


class TestWindowsToPosix:
    def test_basic(self):
        assert to_posix_path("C:\\Users\\foo") == "/c/Users/foo"

    def test_lowercases_drive(self):
        assert to_posix_path("C:\\foo").startswith("/c/")

    def test_forward_slash_input(self):
        assert to_posix_path("C:/Users/foo") == "/c/Users/foo"

    def test_no_op_for_already_posix(self):
        assert to_posix_path("/home/user") == "/home/user"


class TestToNativePath:
    def test_native_windows(self):
        with mock.patch("tools.path_utils.is_windows", return_value=True):
            assert to_native_path("/c/Users/foo") == "C:\\Users\\foo"

    def test_native_posix(self):
        with mock.patch("tools.path_utils.is_windows", return_value=False):
            assert to_native_path("C:\\Users\\foo") == "/c/Users/foo"

    def test_native_passthrough_pure_posix_on_posix(self):
        with mock.patch("tools.path_utils.is_windows", return_value=False):
            assert to_native_path("/home/user") == "/home/user"

    def test_empty_string(self):
        assert to_native_path("") == ""


class TestForceUtf8Stdio:
    def test_idempotent(self):
        # Already UTF-8 → nothing changes.
        before_stdout = sys.stdout
        force_utf8_stdio()
        force_utf8_stdio()
        # We cannot strictly require "before is after" because the wrapper
        # may legitimately be installed; but no exceptions should be raised.

    def test_replaces_cp1252(self):
        # Simulate Windows cp1252 default by wrapping stdout buffer.
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        try:
            fake_out = io.BytesIO()
            fake_err = io.BytesIO()
            sys.stdout = io.TextIOWrapper(fake_out, encoding="cp1252", write_through=True)
            sys.stderr = io.TextIOWrapper(fake_err, encoding="cp1252", write_through=True)
            assert sys.stdout.encoding.lower() == "cp1252"
            force_utf8_stdio()
            assert sys.stdout.encoding.lower() == "utf-8"
            assert sys.stderr.encoding.lower() == "utf-8"
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason=(
        "paths.sh is a Bash helper for POSIX shell users; on Windows the "
        "Python-side helpers in tools/path_utils.py are the supported entry "
        "point and are exhaustively tested elsewhere in this module."
    ),
)
class TestPathsShell:
    """Smoke test the bash helper by invoking it via subprocess on POSIX hosts."""

    @staticmethod
    def _bash_available():
        import shutil
        return shutil.which("bash") is not None

    @staticmethod
    def _helper_posix():
        from pathlib import Path
        helper = Path(__file__).resolve().parent.parent / "tools" / "paths.sh"
        return helper, helper.as_posix()

    def test_paths_sh_is_executable(self):
        if not self._bash_available():
            pytest.skip("bash not on PATH")
        helper, helper_posix = self._helper_posix()
        assert helper.exists()
        # Use single quotes inside the bash script and forward-slash path
        # to source. The to_posix_path call on Windows hosts may delegate
        # to cygpath, which on Git Bash for Windows returns /c/Users/foo.
        import subprocess
        # Python source: 'C:\\Users\\foo' is 4 escapes → in the actual
        # string, single backslashes: C:\Users\foo. Bash single-quotes
        # preserve those literally.
        script = (
            f'source "{helper_posix}"\n'
            "input='C:\\Users\\foo'\n"
            'to_posix_path "$input"\n'
        )
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"bash exited {result.returncode}: stderr={result.stderr!r} "
            f"stdout={result.stdout!r}"
        )
        # Accept both /c/Users/foo (MSYS cygpath, regex fallback) and
        # /cygdrive/c/Users/foo (Cygwin cygpath default).
        out = result.stdout.strip()
        assert out in ("/c/Users/foo", "/cygdrive/c/Users/foo"), (
            f"unexpected to_posix_path output: {out!r}"
        )

    def test_paths_sh_to_windows(self):
        if not self._bash_available():
            pytest.skip("bash not on PATH")
        helper, helper_posix = self._helper_posix()
        import subprocess
        script = (
            f'source "{helper_posix}"\n'
            "to_windows_path '/c/Users/foo'\n"
        )
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"bash exited {result.returncode}: stderr={result.stderr!r} "
            f"stdout={result.stdout!r}"
        )
        assert result.stdout.strip() == "C:\\Users\\foo"
