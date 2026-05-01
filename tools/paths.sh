#!/usr/bin/env bash
# tools/paths.sh — sourceable bash helpers for cross-platform path handling.
#
# Source from any skill script that needs to talk to both the local shell
# (POSIX paths) and the Claude Read/Write tools (OS-native paths).
#
#   source "$(dirname "$0")/paths.sh"
#   native=$(to_native_path "/c/Users/foo")    # → C:\Users\foo on Windows
#   posix=$(to_posix_path "C:\\Users\\foo")    # → /c/Users/foo

# Detect host: "windows" (Git Bash / MSYS / Cygwin) vs "posix".
audit_host_os() {
  case "${OSTYPE:-}" in
    msys*|cygwin*|win32*) echo "windows" ;;
    *)
      if [[ -n "${WINDIR:-}" || -n "${SYSTEMROOT:-}" ]]; then
        echo "windows"
      else
        echo "posix"
      fi
      ;;
  esac
}

# Convert POSIX-drive path "/c/foo/bar" → Windows path "C:\foo\bar".
_posix_to_windows() {
  local p=$1
  if [[ "$p" =~ ^/([a-zA-Z])(/|$)(.*) ]]; then
    local drive=${BASH_REMATCH[1]^^}
    local rest=${BASH_REMATCH[3]}
    rest=${rest//\//\\}
    echo "${drive}:\\${rest}"
  else
    echo "$p"
  fi
}

# Convert Windows path "C:\foo\bar" → POSIX-drive path "/c/foo/bar".
_windows_to_posix() {
  local p=$1
  if [[ "$p" =~ ^([a-zA-Z]):[\\/](.*) ]]; then
    local drive=${BASH_REMATCH[1],,}
    local rest=${BASH_REMATCH[2]}
    rest=${rest//\\/\/}
    echo "/${drive}/${rest}"
  else
    echo "$p"
  fi
}

# Public: to_native_path "$path" → OS-native path form.
# On Windows hosts, POSIX-drive paths are converted to Windows form.
# On POSIX hosts, Windows-drive paths are converted to POSIX form.
to_native_path() {
  local p=$1
  local host
  host=$(audit_host_os)
  if [[ "$host" == "windows" ]]; then
    if command -v cygpath >/dev/null 2>&1; then
      cygpath -w "$p"
    else
      _posix_to_windows "$p"
    fi
  else
    case "$p" in
      [a-zA-Z]:[/\\]*) _windows_to_posix "$p" ;;
      *) echo "$p" ;;
    esac
  fi
}

# Public: to_posix_path "$path" → POSIX path form (forward slashes).
to_posix_path() {
  local p=$1
  case "$p" in
    [a-zA-Z]:[/\\]*)
      if command -v cygpath >/dev/null 2>&1; then
        cygpath -u "$p"
      else
        _windows_to_posix "$p"
      fi
      ;;
    *) echo "${p//\\//}" ;;
  esac
}

# Public: to_windows_path "$path" → Windows path form (backslashes).
to_windows_path() {
  local p=$1
  case "$p" in
    /[a-zA-Z]/*) _posix_to_windows "$p" ;;
    *) echo "${p//\//\\}" ;;
  esac
}

# Public: ensure_python_utf8 — export PYTHONIOENCODING/PYTHONUTF8 for child
# Python processes. Idempotent.
ensure_python_utf8() {
  export PYTHONUTF8=1
  export PYTHONIOENCODING=utf-8
}
