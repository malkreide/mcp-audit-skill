#!/usr/bin/env bash
# Live-Probe template for a new *-mcp data source.
#
# Copy this file, set BASE, and run each block. The output goes into your
# Befund-Tabelle (Schritt 1.3 of the mcp-data-source-probe skill).
#
# Prerequisites: curl, python3, jq (optional).

set -u
BASE="${BASE:-https://cms.example.ch/api/v1/json}"
OUTDIR="${OUTDIR:-/tmp/mcp-probe}"
mkdir -p "$OUTDIR"

probe() {
    # $1 = label, $2 = path (relative to BASE), $3+ = optional query
    local label="$1"; shift
    local path="$1"; shift
    local query="${1:-}"
    local url="${BASE}/${path}${query:+?${query}}"
    local file="${OUTDIR}/$(echo "$label" | tr ' /' '__').json"
    echo ""
    echo "=== ${label} ==="
    echo "    ${url}"
    curl -sL -w "    HTTP %{http_code} | %{size_download}B | %{time_total}s\n" \
        "$url" -o "$file"
    python3 -c "
import json, sys
try:
    d = json.load(open('$file'))
    if isinstance(d, dict):
        print('    success:', d.get('success'), '| count:', d.get('count'), '| msg:', d.get('message',''))
        data = d.get('data')
        if isinstance(data, list):
            print('    records:', len(data))
            if data: print('    keys:', list(data[0].keys())[:15])
        elif isinstance(data, dict):
            print('    keys:', list(data.keys())[:15])
    elif isinstance(d, list):
        print('    list size:', len(d))
        if d: print('    keys:', list(d[0].keys())[:15])
except Exception as e:
    print('    PARSE ERROR:', e)
"
}

echo "## Probe BASE: $BASE"
echo "## Output:   $OUTDIR"

# ----------------------------------------------------------------------
# Customise the probes below for the actual data source.
# Rule: at least 5 calls per endpoint
#       (baseline, docs-example, filtered, error-case, SCOPE).
# ----------------------------------------------------------------------

probe "list_entity_baseline"   "table/entity/list" "limit=3"
probe "single_entity_by_id_1"  "table/entity/id/1" ""
probe "filtered_by_status"     "table/entity/list" "filter_status=active&limit=5"
probe "invalid_id_errorcase"   "table/entity/id/999999" ""
probe "search_endpoint"        "search/default/Foo" "limit=5"

# ----------------------------------------------------------------------
# Scope probe (skill section 1.2b) — the one that catches silent defaults.
#
# An optional filter parameter often does NOT mean "unrestricted" when
# omitted; it means an arbitrary subset the API picked for you. That fact
# lives only in the spec's PARAMETER DESCRIPTION — never in the response,
# never in a working example. termdat-mcp searched 1 of 23 classifications
# for months because nobody ran this comparison.
#
# Change exactly ONE variable between A and B, or the API will confess to
# a crime it did not commit.
# ----------------------------------------------------------------------

count_of() {
    python3 -c "
import json, sys
d = json.load(open('$1'))
print(len(d) if isinstance(d, list) else len((d.get('data') or d.get('result') or [])))
" 2>/dev/null || echo "?"
}

scope_probe() {
    # $1 = label, $2 = path, $3 = query WITHOUT the scope param,
    # $4 = the same query WITH the scope param set to its maximum
    local label="$1" path="$2" without="$3" with_max="$4"
    local fa="${OUTDIR}/scope_${label}_A.json" fb="${OUTDIR}/scope_${label}_B.json"
    curl -sL "${BASE}/${path}?${without}"  -o "$fa"
    curl -sL "${BASE}/${path}?${with_max}" -o "$fb"
    local a b; a=$(count_of "$fa"); b=$(count_of "$fb")
    echo ""
    echo "=== SCOPE ${label} ==="
    echo "    A (param omitted):  ${a}"
    echo "    B (param maximal):  ${b}"
    if [ "$a" != "$b" ]; then
        echo "    ⚠️  DELTA — the omitted parameter restricts the search. Send it explicitly."
    else
        echo "    ✅ no delta — omitting is equivalent to unrestricted (record the evidence)"
    fi
}

# One scope_probe per optional filter/scope parameter found in 1.2b.
# scope_probe "classification" "Search" \
#     "SearchTerm=Testbegriff" \
#     "SearchTerm=Testbegriff&ClassificationIds=1&ClassificationIds=2"

# ----------------------------------------------------------------------
# Recall ground truth (skill section 1.4b)
#
# Open the source's official web UI, search the SAME terms, note the hit
# counts, and fill the table below. Every delta needs an explanation —
# "don't know" is an open finding, not a result.
#
#   | term          | web UI | API | delta | explanation |
#   |---------------|-------:|----:|------:|-------------|
#   | <many hits>   |        |     |       |             |
#   | <few hits>    |        |     |       |             |
#   | <compound>    |        |     |       |             |
#
# Pick a compound or special-character term deliberately: most full-text
# indexes match whole words, so German compounds are NOT found by their
# parts ("Quellensteuer" misses "Quellensteuerverordnung"; the wildcard
# form finds it). Do NOT use the anchor demo query — it always works, it
# was optimised during the build.
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Dump-URL reachability check
# ----------------------------------------------------------------------

echo ""
echo "=== Bulk dump probe ==="
DUMP_URL="${DUMP_URL:-https://cms.example.ch/exports/all.json.zip}"
echo "    $DUMP_URL"
curl -sLI "$DUMP_URL" | grep -E "^HTTP|^Content-Length|^Last-Modified|^Content-Type" | sed 's/^/    /'

echo ""
echo "---"
echo "Next: fill the Befund-Tabelle and decide architecture (A/B/C)."
