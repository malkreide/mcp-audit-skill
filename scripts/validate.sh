#!/usr/bin/env bash
# Every gate the CI applies, in one command.
#
# Usage:
#   bash scripts/validate.sh          # alle Gates
#   bash scripts/validate.sh 12 13    # nur diese
#
# Die Prüfungen selbst stehen unter `tools/checks/` — eine Funktion pro Gate,
# mit `CheckFailed` statt `sys.exit`, damit `tests/` sie gegen Fixture-Bäume
# fahren und ihre Befunde zusichern kann. Bis 1.6.0 standen sie als
# Shell-Funktionen und Python-Heredocs in dieser Datei; das war nicht testbar,
# und Check 12 ist der Beleg, dass eine ungetestete Prüfung still aufhören
# kann zu prüfen.
#
# `.github/workflows/ci.yml` ruft diese Datei auf, statt die Gates ein zweites
# Mal hinzuschreiben. Zwei Kopien driften, und ein gedrifteter Pre-Flight-Check
# ist schlimmer als keiner: Er meldet grün auf einem Baum, den die CI ablehnt —
# genau die eine Eigenschaft, die ein Pre-Flight-Check nicht haben darf. Das
# schliesst `ruff check` und `ruff format --check` ein; sie liefen bis 1.6.0
# nur in der CI und waren damit exakt diese Bruchstelle.
#
# Jede Prüfung läuft auch nach einem Fehlschlag der vorigen, so nennt ein
# einzelner Lauf jedes Problem statt nur des ersten. Exit 0 nur, wenn alle
# bestanden haben.
#
# Ohne Netz und ohne Token vollständig durchlaufbar. Die eine Prüfung, die
# beides braucht — die GitHub-Description gegen SKILL.md —, ist als
# `offline=False` markiert und bleibt hier aussen vor; die CI ruft sie
# zusätzlich auf.

set -eu

cd "$(dirname "$0")/.."

PY="$(command -v python3 || command -v python)" || {
    echo "neither python3 nor python found on PATH" >&2
    exit 1
}
export PYTHONUTF8=1

exec "$PY" -m tools.checks "$@"
