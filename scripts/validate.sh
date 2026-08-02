#!/usr/bin/env bash
# Every gate the CI applies, in one command.
#
# This file is where the checks live; .github/workflows/ci.yml calls it rather
# than repeating them. Two copies would drift, and a drifted pre-flight check is
# worse than none: it reports green on a tree CI will reject, which is the one
# failure mode a pre-flight check must not have.
#
# Usage:
#   bash scripts/validate.sh
#
# Every check runs even after an earlier one fails, so a single pass shows all
# the problems rather than only the first. Exit status is 0 only if all passed.

set -u

cd "$(dirname "$0")/.."

PY="$(command -v python3 || command -v python)" || {
    echo "neither python3 nor python found on PATH" >&2
    exit 1
}
export PYTHONUTF8=1

# compileall writes bytecode caches beside the sources. Redirect them out of the
# working tree — an untracked reference/__pycache__/ is how a .pyc came to be
# committed once already (CHANGELOG 1.1.0, Removed).
CACHE_DIR="$(mktemp -d)"
trap 'rm -rf "$CACHE_DIR"' EXIT
export PYTHONPYCACHEPREFIX="$CACHE_DIR"

passed=0
failed=0

check() {
    # $1 = label, $2 = function to run. Output is captured and indented so a
    # failing check shows its diagnosis directly under its own line.
    local label="$1"; shift
    local out status
    out="$("$@" 2>&1)"; status=$?
    if [ "$status" -eq 0 ]; then
        passed=$((passed + 1))
        printf '  ok    %s\n' "$label"
    else
        failed=$((failed + 1))
        printf '  FAIL  %s\n' "$label"
    fi
    if [ -n "$out" ]; then
        printf '%s\n' "$out" | sed 's/^/          /'
    fi
}

# ----------------------------------------------------------------------

shell_syntax() {
    bash -n reference/probe_template.sh && echo "reference/probe_template.sh parses"
}

python_syntax() {
    "$PY" -m compileall -q reference/ && echo "reference/*.py compile"
}

frontmatter() {
    "$PY" - <<'PY'
import pathlib, re, sys
expected = {
    "SKILL.md": "mcp-data-source-probe",
}
for path, want in expected.items():
    p = pathlib.Path(path)
    if not p.is_file():
        sys.exit(f"{path}: missing")
    m = re.match(r"^---\nname: (.+?)\ndescription: (.+?)\n---\n",
                 p.read_text(encoding="utf-8"), re.S)
    if not m:
        sys.exit(f"{path}: frontmatter missing or malformed")
    name, desc = m.group(1).strip(), m.group(2).strip()
    if name != want:
        sys.exit(f"{path}: expected name {want!r}, got {name!r}")
    if len(desc) > 1024:
        sys.exit(f"{path}: description too long ({len(desc)} > 1024)")
    # Printed as remaining headroom, not just a length: the limit is close
    # enough that an added trigger phrase can cross it in one edit.
    print(f"{path}: name={name}, description={len(desc)}/1024 chars "
          f"({1024 - len(desc)} left)")
PY
}

cross_references() {
    "$PY" - <<'PY'
import re, sys
text = open("SKILL.md", encoding="utf-8").read()
headings = set(re.findall(r"^#{2,4} (\d+\.\d+[a-z]?)", text, re.M))
referenced = set(re.findall(r"\((\d+\.\d+)[a-z]?\)", text))
missing = sorted(r for r in referenced if not any(h.startswith(r) for h in headings))
if missing:
    sys.exit(f"SKILL.md references non-existent sections: {missing}")
print(f"{len(headings)} numbered sections, {len(referenced)} referenced, all resolve")
PY
}

referenced_files() {
    local missing=0 f
    for f in reference/probe_template.sh \
             reference/befund_tabelle_template.md \
             reference/response_envelope.py \
             reference/retry_backoff.py \
             companion/mcp-data-fidelity/README.md; do
        if [ ! -f "$f" ]; then
            echo "missing: $f"
            missing=1
        fi
    done
    [ "$missing" -eq 0 ] && echo "all reference files present"
}

companion_pointer() {
    # The skill moved to its own repository. If this directory ever holds a
    # SKILL.md again, the two copies will drift — that is the situation the
    # move was meant to end.
    if [ -e companion/mcp-data-fidelity/SKILL.md ]; then
        echo "companion/ carries a SKILL.md again — it moved to its own repo"
        return 1
    fi
    if ! grep -q 'malkreide/mcp-data-fidelity-skill' \
            companion/mcp-data-fidelity/README.md; then
        echo "pointer does not name the canonical repository"
        return 1
    fi
    echo "pointer names the canonical repository"
}

quality_chain() {
    # The five repositories of the chain are named together in exactly one
    # place per language, and nothing outside this repo can be tested from
    # here. What CAN be tested is that the table has not quietly lost a member
    # — which is how the trailing "alongside them, there is also
    # mcp-continuous-auditor" sentence went unnoticed for as long as it did:
    # the auditor was mentioned but not in the table, so it read as an
    # afterthought rather than as the fifth link.
    #
    # The topic itself lives on GitHub and is checked by the guard in
    # mcp-audit-skill (tools/check_quality_chain.py), which is the only repo
    # that carries the manifest.
    "$PY" - <<'PY'
import pathlib, re, sys

MEMBERS = [
    "mcp-data-source-probe-skill",
    "mcp-data-fidelity-skill",
    "mcp-transport-hardening-skill",
    "mcp-audit-skill",
    "mcp-continuous-auditor",
]
TOPIC_URL = "https://github.com/topics/mcp-quality-chain"

for path, heading in [("README.md", "The MCP quality chain"),
                      ("README.de.md", "Die MCP-Qualitätskette")]:
    text = pathlib.Path(path).read_text(encoding="utf-8")
    m = re.search(rf"^### {re.escape(heading)}\n(.*?)(?=^#{{2,3}} |\Z)",
                  text, re.M | re.S)
    if not m:
        sys.exit(f"{path}: section '### {heading}' not found — anchor gone or "
                 "reworded, so this check would silently stop checking")
    body = m.group(1)
    missing = [r for r in MEMBERS if r not in body]
    if missing:
        sys.exit(f"{path}: the chain table does not name {missing}")
    if TOPIC_URL not in body:
        sys.exit(f"{path}: the shared topic page {TOPIC_URL} is not linked — "
                 "without it the table is a list nobody outside can find")
    print(f"{path}: all {len(MEMBERS)} members named, topic page linked")
PY
}

version_badge() {
    "$PY" - <<'PY'
import pathlib, re, sys

# Quelle ist die oberste Release-Überschrift. `[Unreleased]` trägt keine
# Versionsnummer und wird vom Muster von selbst übersprungen.
lines = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8").splitlines()
HEADING = re.compile(r"^## \[v?(?P<version>\d+\.\d+\.\d+)\]")
source = next(((n, ln, m.group("version"))
               for n, ln in enumerate(lines, 1)
               if (m := HEADING.match(ln))), None)
if source is None:
    sys.exit("CHANGELOG.md: no '## [X.Y.Z]' release heading found — anchor "
             "gone, so this check would have nothing to compare against")
lineno, heading, expected = source

# Über das Dateisystem, nicht als gepflegte Liste: eine dritte
# Sprachfassung ist damit automatisch abgedeckt.
readmes = sorted(pathlib.Path(".").glob("README*.md"))
if not readmes:
    sys.exit("no README*.md found — nothing to check, which would pass silently")

BADGE = re.compile(r"badge/version-(\d+\.\d+\.\d+)-")
for path in readmes:
    found = BADGE.findall(path.read_text(encoding="utf-8"))
    if not found:
        sys.exit(f"{path}: no version badge found — anchor gone or reworded, "
                 "so this check would stop checking this file")
    stale = sorted({v for v in found if v != expected})
    if stale:
        sys.exit(
            f"{path}: version badge shows {stale}, but the topmost release in "
            f"CHANGELOG.md is {expected} (line {lineno}: {heading.strip()!r}).\n"
            "  Either the badge was not bumped with the release, or a release "
            "heading was lost — check which side moved before editing."
        )
print(f"{expected} in {len(readmes)} README file(s), "
      f"from CHANGELOG line {lineno}")
PY
}

# ----------------------------------------------------------------------

echo "validate — mcp-data-source-probe-skill"
echo "  repo:   $(pwd)"
echo "  python: $("$PY" --version 2>&1)"
echo ""

check "1  shell reference is syntactically valid"     shell_syntax
check "2  python references are syntactically valid"  python_syntax
check "3  SKILL.md carries a well-formed frontmatter" frontmatter
check "4  cross-references resolve to real sections"  cross_references
check "5  referenced files exist"                     referenced_files
check "6  the companion pointer still points somewhere" companion_pointer
check "7  version badge matches the latest CHANGELOG release" version_badge
check "8  the quality-chain table names all five members"    quality_chain

echo ""
if [ "$failed" -eq 0 ]; then
    echo "$((passed + failed)) checks, all passed"
    exit 0
fi
echo "$((passed + failed)) checks, $failed failed"
exit 1
