#!/usr/bin/env bash
# Baut mcp-audit.skill — die Datei, die man bei Claude hochlaedt.
#
# Die Logik steht in `tools/build_skill.py`, nicht hier: Die Testmatrix dieses
# Repos faehrt windows-latest, und dort gibt es weder bash noch `zip`. Diese
# Datei ist nur der Einstieg, wie `scripts/validate.sh` daneben.
set -euo pipefail

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

cd "$(dirname "$0")/.."
export PYTHONUTF8=1
exec "$PY" tools/build_skill.py "$@"
