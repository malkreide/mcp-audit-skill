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
# Coverage axis (skill section 1.3b) — what the planned tools will NOT reach.
#
# The findings table records what the probed endpoints return. It does not
# record which part of the holdings no planned tool touches at all: that
# produces no error, no delta, no row — it is invisible from the probe unless
# someone asks on purpose.
#
# Enumerate the source's own axis (rubrics, types, registers, themes), then
# mark the planned tools INTO it. Deriving the list from the tool design can
# not, by construction, find what the design overlooks.
#
# Cost of skipping it: the scope gets justified months later from memory, in a
# README or an audit, and memory produces plausible reasons rather than
# measured ones.
# ----------------------------------------------------------------------

echo ""
echo "=== Coverage axis ==="
CATEGORIES_PATH="${CATEGORIES_PATH:-categories}"
curl -sL "${BASE}/${CATEGORIES_PATH}" -o "${OUTDIR}/categories.json"
COVERED="${COVERED:-}"   # space-separated ids the planned tools will query
COVERED="$COVERED" python3 - "${OUTDIR}/categories.json" <<'PY'
import json, os, sys
try:
    cats = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:
    print(f"    no category endpoint here ({exc}) — fall back to facets of an "
          "empty search, the dump's type column, or the rubric list of the "
          "official UI. The axis has to come from the source either way.")
    raise SystemExit(0)
if isinstance(cats, dict):
    cats = cats.get("data") or cats.get("categories") or []
covered = set(os.environ.get("COVERED", "").split())
for c in cats:
    key = str(c.get("id") or c.get("name") or c)
    count = c.get("count", "?") if isinstance(c, dict) else "?"
    mark = "erreichbar" if key in covered else "NICHT erreichbar  <- needs a reason"
    print(f"    {key:<24} {count:>9}  {mark}")
print("\n    Every 'NICHT erreichbar' row needs one of three reasons in the")
print("    findings table: out of scope by decision (with the reason), out of")
print("    technical reach (no endpoint / auth / licence), or still open.")
PY

# ----------------------------------------------------------------------
# Widening schedule (skill section 1.5)
#
# If a tool shortens the search term after zero hits, the ladder is an
# assumption about the source's matching granularity. The source answers it
# in a handful of calls: from which prefix length does it return hits?
#
# A ladder that shortened in 30% steps and bottomed out at eight characters
# ended at "Betonsan" for "Betonsanierungsarbeiten"; the source starts
# answering at "Beton". Three characters short, reported as "nothing found".
# German compounds break at morpheme boundaries — a percentage hits one only
# by accident.
# ----------------------------------------------------------------------

widening_probe() {
    # $1 = test term, $2 = search path (default: search), $3 = query key
    local term="$1" path="${2:-search}" key="${3:-q}"
    local n p hits
    echo ""
    echo "=== WIDENING ${term} ==="
    echo "    len  prefix                        hits"
    for (( n=${#term}; n>=3; n-- )); do
        p="${term:0:n}"
        curl -sL --get --data-urlencode "${key}=${p}" \
            "${BASE}/${path}" -o "${OUTDIR}/widen.json"
        hits=$(count_of "${OUTDIR}/widen.json")
        printf "    %2d   %-28s %s\n" "$n" "$p" "$hits"
    done
    echo "    -> shortest prefix WITH hits is the ladder's floor. Record it in"
    echo "       the findings table and as a code comment, with term and date."
    echo "    -> also try '${term:0:5}*': if the wildcard returns the same in one"
    echo "       call, the ladder is a workaround for a feature you already have."
}

# 3-5 terms, chosen deliberately: a long compound, one with a hyphen, one with
# an umlaut, one from another language region. NOT the anchor demo query.
# widening_probe "Betonsanierungsarbeiten"

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
