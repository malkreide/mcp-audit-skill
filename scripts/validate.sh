#!/usr/bin/env bash
# Alle Offline-Gates dieses Repositories in einem Kommando.
#
# Die Pruefungen selbst stehen unter `tools/checks/` — eine Funktion pro Gate,
# jede gegen einen uebergebenen Baum fahrbar und damit unter `tests/`
# mutationsgeprueft. Diese Datei ist nur der Einstieg.
set -euo pipefail

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

cd "$(dirname "$0")/.."
exec "$PY" -m tools.checks "$@"
