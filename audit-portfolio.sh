#!/usr/bin/env bash
#
# audit-portfolio.sh — Headless batch audit across MCP servers
#
# Reads portfolio.yaml (server list + profile per server), runs the
# /audit-mcp slash-command via `claude -p` non-interactively per server,
# aggregates findings into a portfolio-summary.md.
#
# Usage:
#   ./audit-portfolio.sh                                # all servers
#   ./audit-portfolio.sh zh-education-mcp               # single server
#   ./audit-portfolio.sh zh-education-mcp foo-mcp       # subset
#   ./audit-portfolio.sh --force                        # re-run already-audited
#   ./audit-portfolio.sh --portfolio my-portfolio.yaml  # custom portfolio file
#   ./audit-portfolio.sh --dry-run                      # plan only, no claude
#
# Env vars:
#   WORK_DIR    default: $HOME/mcp-audit-runs           (where target repos clone)
#   LOG_DIR     default: ./portfolio-logs/<date>        (per-server stdout logs)
#   CLAUDE_BIN  default: claude
#
# Dependencies: yq (Mike Farah Go-yq OR kislyuk Python-yq), git, claude CLI

set -euo pipefail

PORTFOLIO_FILE="portfolio.yaml"
FORCE=0
DRY_RUN=0
declare -a SERVER_FILTER=()

while [[ $# -gt 0 ]]; do
  case $1 in
    --portfolio)
      PORTFOLIO_FILE=$2; shift 2 ;;
    --force)
      FORCE=1; shift ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    -h|--help)
      sed -n '2,/^$/p' "$0" | sed 's/^# *//; s/^#$//'
      exit 0 ;;
    --*)
      echo "Unknown flag: $1" >&2
      exit 1 ;;
    *)
      SERVER_FILTER+=("$1"); shift ;;
  esac
done

WORK_DIR=${WORK_DIR:-$HOME/mcp-audit-runs}
LOG_DIR=${LOG_DIR:-./portfolio-logs/$(date +%Y-%m-%d)}
CLAUDE_BIN=${CLAUDE_BIN:-claude}
TODAY=$(date +%Y-%m-%d)

# Dependency check — claude only required when not in dry-run.
# yq must be present first so we can detect its flavor; Python yq additionally
# requires jq because it is implemented as a jq wrapper.
for cmd in yq git; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: '$cmd' not found in PATH." >&2
    [[ "$cmd" == "yq" ]] && echo "  Install: brew install yq  (Go) — or: pip install yq  (Python, requires jq)" >&2
    exit 1
  fi
done

# Detect yq flavor: Python (kislyuk) needs -y for YAML output and depends on jq;
# Go (Mike Farah) outputs YAML by default and is self-contained.
if yq --help 2>&1 | grep -qiE "transcode|jq wrapper"; then
  YQ_FLAVOR=python
else
  YQ_FLAVOR=go
fi

# Now that flavor is known, check the remaining dependencies.
required=()
[[ "$YQ_FLAVOR" == python ]] && required+=(jq)
[[ $DRY_RUN -eq 0 ]] && required+=("$CLAUDE_BIN")
for cmd in "${required[@]}"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: '$cmd' not found in PATH." >&2
    [[ "$cmd" == jq ]] && echo "  Python yq is a jq wrapper. Install: brew install jq  (or: apt install jq)" >&2
    exit 1
  fi
done

yq_yaml() {
  if [[ "$YQ_FLAVOR" == python ]]; then
    yq -y "$@"
  else
    yq "$@"
  fi
}

if [[ ! -f "$PORTFOLIO_FILE" ]]; then
  echo "Error: $PORTFOLIO_FILE not found." >&2
  echo "  Copy portfolio.example.yaml to portfolio.yaml and fill in your servers." >&2
  exit 1
fi

count=$(yq -r '.servers | length' "$PORTFOLIO_FILE")
if [[ -z "$count" || "$count" == "null" || "$count" -eq 0 ]]; then
  echo "Error: $PORTFOLIO_FILE contains no servers under .servers." >&2
  exit 1
fi

mkdir -p "$WORK_DIR" "$LOG_DIR"

declare -a RESULTS_NAME=() RESULTS_STATUS=() RESULTS_REPORT=()

echo "Portfolio audit run — $(date)"
echo "  Portfolio: $PORTFOLIO_FILE ($count server(s) total)"
echo "  Work dir:  $WORK_DIR"
echo "  Log dir:   $LOG_DIR"
echo "  yq:        $YQ_FLAVOR"
[[ $DRY_RUN -eq 1 ]] && echo "  Mode:      DRY-RUN (no claude calls)"
echo

audited=0
for ((i=0; i<count; i++)); do
  name=$(yq -r ".servers[$i].name" "$PORTFOLIO_FILE")
  repo=$(yq -r ".servers[$i].repo" "$PORTFOLIO_FILE")

  if [[ ${#SERVER_FILTER[@]} -gt 0 ]]; then
    matched=0
    for f in "${SERVER_FILTER[@]}"; do
      [[ "$f" == "$name" ]] && matched=1 && break
    done
    [[ $matched -eq 0 ]] && continue
  fi

  audited=$((audited+1))
  target="$WORK_DIR/$name"
  log="$LOG_DIR/$name.log"

  echo "[$audited] $name  ($repo)"

  if [[ $DRY_RUN -eq 1 ]]; then
    RESULTS_NAME+=("$name"); RESULTS_STATUS+=("dry-run"); RESULTS_REPORT+=("-")
    continue
  fi

  reuse_existing=0
  if [[ -d "$target/.git" ]]; then
    current_remote=$(git -C "$target" remote get-url origin 2>/dev/null || echo "")
    if [[ "$current_remote" == "$repo" ]]; then
      reuse_existing=1
    else
      echo "  ↻ remote URL changed (was: ${current_remote:-<none>}; now: $repo) — re-cloning"
      rm -rf "$target"
    fi
  fi

  if [[ $reuse_existing -eq 1 ]]; then
    if ! (cd "$target" && git fetch --quiet --depth 1 origin && git reset --quiet --hard origin/HEAD); then
      echo "  ✗ git update failed"
      RESULTS_NAME+=("$name"); RESULTS_STATUS+=("clone-failed"); RESULTS_REPORT+=("-")
      continue
    fi
  else
    rm -rf "$target"
    if ! git clone --quiet --depth 1 "$repo" "$target"; then
      echo "  ✗ git clone failed"
      RESULTS_NAME+=("$name"); RESULTS_STATUS+=("clone-failed"); RESULTS_REPORT+=("-")
      continue
    fi
  fi

  if [[ $FORCE -eq 0 ]]; then
    existing=$(find "$target/audits" -maxdepth 1 -type d -name "${TODAY}-*" 2>/dev/null | head -1 || true)
    if [[ -n "$existing" && -f "$existing/audit-report.md" ]]; then
      echo "  ⏭  already audited today — $existing/audit-report.md"
      RESULTS_NAME+=("$name"); RESULTS_STATUS+=("skipped"); RESULTS_REPORT+=("$existing/audit-report.md")
      continue
    fi
  fi

  profile=$(yq_yaml ".servers[$i].profile" "$PORTFOLIO_FILE")

  prompt=$(cat <<EOF
Headless-Modus für /audit-mcp. Das folgende Profil ist autoritativ — überspringe die User-Bestätigung in Schritt 1 und gehe direkt zu Schritt 2 weiter.

\`\`\`yaml
$profile
\`\`\`

Jetzt /audit-mcp $target ausführen.
EOF
)

  echo "  → claude -p (log: $log)"
  if "$CLAUDE_BIN" -p "$prompt" > "$log" 2>&1; then
    report=$(find "$target/audits" -maxdepth 1 -type d -name "${TODAY}-*" 2>/dev/null | sort | tail -1 || true)
    if [[ -n "$report" && -f "$report/audit-report.md" ]]; then
      echo "  ✓ done — $report/audit-report.md"
      RESULTS_NAME+=("$name"); RESULTS_STATUS+=("done"); RESULTS_REPORT+=("$report/audit-report.md")
    else
      echo "  ⚠ claude finished but no audit-report.md found — see $log"
      RESULTS_NAME+=("$name"); RESULTS_STATUS+=("no-report"); RESULTS_REPORT+=("-")
    fi
  else
    echo "  ✗ claude exited non-zero — see $log"
    RESULTS_NAME+=("$name"); RESULTS_STATUS+=("audit-failed"); RESULTS_REPORT+=("-")
  fi
done

# Aggregate
summary="$LOG_DIR/portfolio-summary.md"
{
  echo "# Portfolio Audit Summary — $TODAY"
  echo
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "_Dry-run — no audits executed._"
    echo
  fi
  echo "| Server | Status | Critical | High | Medium | Low | Production-Ready | Report |"
  echo "|---|---|---|---|---|---|---|---|"

  for ((j=0; j<${#RESULTS_NAME[@]}; j++)); do
    n=${RESULTS_NAME[$j]}
    s=${RESULTS_STATUS[$j]}
    r=${RESULTS_REPORT[$j]}

    if [[ -f "$r" ]]; then
      findings_dir="$(dirname "$r")/findings"
      crit=0; high=0; med=0; low=0
      if [[ -d "$findings_dir" ]]; then
        # templates/finding.md stores severity as a table row:
        #   | **Severity** | critical |
        # Older free-form findings used `**Severity:** critical`. Match both.
        sev_pat='(\|\s*\*\*Severity\*\*\s*\|\s*|^\*\*Severity:\*\*\s*)'
        crit=$(grep -lEi "${sev_pat}critical" "$findings_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
        high=$(grep -lEi "${sev_pat}high"     "$findings_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
        med=$( grep -lEi "${sev_pat}medium"   "$findings_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
        low=$( grep -lEi "${sev_pat}low"      "$findings_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
      fi

      ready_line=$(grep -m1 'Production-Readiness' "$r" || true)
      if echo "$ready_line" | grep -q "❌"; then
        ready="❌"
      elif echo "$ready_line" | grep -q "✅"; then
        ready="✅"
      else
        ready="?"
      fi
      echo "| $n | $s | $crit | $high | $med | $low | $ready | [Report]($r) |"
    else
      echo "| $n | $s | - | - | - | - | - | - |"
    fi
  done

  echo
  echo "_Generated $(date -u +%Y-%m-%dT%H:%M:%SZ) by audit-portfolio.sh_"
} > "$summary"

echo
echo "Done. $audited server(s) processed."
echo "Summary: $summary"
