#!/usr/bin/env bash
# Every gate the CI applies, in one command.
#
# Usage:
#   bash scripts/validate.sh          # alle Gates
#   bash scripts/validate.sh 9 10     # nur diese
#
# Diese Datei ist neu in 1.8.0. Bis dahin hatte dieses Repository gar keinen
# lokalen Runner: Die Prüfungen standen als Heredocs in
# .github/workflows/ci.yml, und wer sie vor dem Push fahren wollte, hätte den
# Workflow von Hand nachspielen müssen. Entsprechend hat das niemand getan.
#
# Die Prüfungen selbst stehen unter `tools/checks/` — eine Funktion pro Gate,
# mit `CheckFailed` statt `sys.exit`, damit `tests/` sie gegen Fixture-Bäume
# fahren und ihre Befunde zusichern kann.
#
# `.github/workflows/ci.yml` ruft diese Datei auf, statt die Gates ein zweites
# Mal hinzuschreiben. Zwei Kopien driften, und ein gedrifteter Pre-Flight-Check
# ist schlimmer als keiner: Er meldet grün auf einem Baum, den die CI ablehnt.
#
# Jede Prüfung läuft auch nach einem Fehlschlag der vorigen, so nennt ein
# einzelner Lauf jedes Problem statt nur des ersten. Exit 0 nur, wenn alle
# bestanden haben.
#
# Ohne Netz und ohne Tag-Kontext vollständig durchlaufbar. Die zwei Prüfungen,
# die beides brauchen — Tag gegen CHANGELOG (13) und Katalog-Drift (14) —,
# sind als `offline=False` markiert und bleiben hier aussen vor; die CI ruft
# sie dort auf, wo ihr Kontext existiert.

set -eu

cd "$(dirname "$0")/.."

PY="$(command -v python3 || command -v python)" || {
    echo "neither python3 nor python found on PATH" >&2
    exit 1
}
export PYTHONUTF8=1

exec "$PY" -m tools.checks "$@"
