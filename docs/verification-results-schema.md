# Verification Results Schema & Findings Persistence Spec

This document defines the canonical contract between Step 4 (check execution), Step 5 (finding persistence), and Step 6 (report generation). Reference implementation: [`tools/aggregate_results.py`](../tools/aggregate_results.py). Conformance test: [`tests/test_aggregate_results.py`](../tests/test_aggregate_results.py).

## Why this exists

In the first real audit run (`srgssr-mcp`, 2026-04-30), three different stages of the same audit reported three different counts:

| Stage | Findings count | Reason |
|---|---|---|
| Step 5 announcement | 15 | counted FAIL + PARTIAL |
| Step 6 final report | 6 | counted FAIL only |
| Files on disk under `findings/` | 6 | only FAIL was persisted |

Three independent computations against the same data → three different numbers. The skill's credibility depends on this never recurring. The fix is structural: a single canonical aggregator that all downstream stages MUST consume.

## Schema: `verification-results.json`

Step 4 produces this file. It is the **only** ground truth.

```json
{
  "audit_meta": {
    "server_name": "srgssr-mcp",
    "audit_date": "2026-04-30",
    "skill_version": "0.8.x",
    "catalog_version": "2026-04",
    "applies_when_dsl_version": "1.0",
    "policy": "fail-or-partial"
  },
  "results": {
    "ARCH-001": {
      "status": "pass",
      "category": "ARCH",
      "severity": "medium",
      "evidence": ["src/server.py:42 — tool decorator with name=\"getX\""],
      "gaps": []
    },
    "OPS-001": {
      "status": "fail",
      "category": "OPS",
      "severity": "high",
      "evidence": [],
      "gaps": ["No tests/ directory", "No pytest in pyproject.toml"]
    }
  }
}
```

### Status enum

| Value | Meaning | Findings-doc by default? |
|---|---|---|
| `pass` | Check fully satisfied | No |
| `fail` | Check failed; concrete remediation needed | **Yes** |
| `partial` | Check 50%+ but not fully satisfied | **Yes** |
| `todo` | Manual review required, no judgment yet | No |
| `n/a` | Not applicable to this profile (rare; usually omitted) | No |

### Severity enum

`critical`, `high`, `medium`, `low`. Mirrors the check-file frontmatter.

### Required fields per result

- `status` — one of the values above
- `category` — `ARCH`, `SEC`, `CH`, `HITL`, `OBS`, `OPS`, `SCALE`, `SDK`
- `severity` — one of the values above
- `evidence` (list of strings, may be empty)
- `gaps` (list of strings, may be empty)

## Findings-Persistence Policies

A policy maps statuses to "should this produce a finding doc?". Three are supported:

| Policy | Statuses that produce a finding doc |
|---|---|
| `fail-or-partial` (default) | `fail`, `partial` |
| `fail-only` | `fail` |
| `needs-attention` | `fail`, `partial`, `todo` |

The chosen policy MUST be:
1. Set explicitly at the start of Step 5.
2. Persisted in `summary.json` so the report can reference it.
3. Identical between Step 5 (when finding docs are written) and Step 6 (when counts are reported).

## Aggregation: `summary.json`

The aggregator (`tools/aggregate_results.py aggregate`) consumes verification-results.json and produces summary.json. Shape:

```json
{
  "audit_meta": { "...": "..." },
  "totals": {
    "checks_evaluated": 33,
    "applicable": 26,
    "by_status": {
      "pass": 8, "fail": 6, "partial": 9, "todo": 3, "n/a": 7
    },
    "by_severity_among_findings": {
      "critical": 0, "high": 1, "medium": 14, "low": 0
    },
    "by_category": {
      "ARCH": {"pass": 5, "fail": 3, "partial": 5, "todo": 0, "n/a": 0},
      "...": "..."
    }
  },
  "findings": {
    "policy": "fail-or-partial",
    "policy_statuses": ["fail", "partial"],
    "expected_count": 15,
    "expected_ids": ["ARCH-001", "ARCH-002", "...", "OPS-003"],
    "details": [
      {
        "check_id": "OPS-001",
        "category": "OPS",
        "severity": "high",
        "status": "fail"
      }
    ]
  },
  "production_ready": false,
  "blocking_findings": ["OPS-001"]
}
```

### Production-readiness rule

`production_ready` is `false` if there is at least one `fail` with severity in `{critical, high}`. PARTIAL high/critical does **not** block — partial means progress, fail means no progress.

## Validation Gate (mandatory)

Before the audit is considered complete, this gate MUST pass:

```bash
python tools/aggregate_results.py validate audits/<run>/
```

It compares the set of expected check-IDs from `summary.json` against the on-disk filenames in `findings/`. The filename convention is `<CHECK-ID>-<slug>.md`; the validator extracts the prefix and matches against the expected set.

Outcomes:
- **Consistent** — all expected findings are persisted, no extras → exit 0
- **Missing** — some expected findings have no file on disk → exit 1
- **Unexpected** — files exist for checks that shouldn't have findings → exit 1

The first audit's bug would have been caught immediately:

```text
Findings on disk don't match summary.expected_ids:
  missing=['ARCH-001', 'ARCH-003', 'ARCH-004', ..., 'OPS-003'],  ← 9 missing
  unexpected=[]
```

## Filename Convention

```
findings/
  ARCH-001-tool-naming-convention.md
  ARCH-002-tool-descriptions.md
  OPS-001-test-strategy.md
  SEC-021-egress-allowlist.md
```

Format: `<CHECK-ID>-<slug>.md`. The slug is human-readable kebab-case.

## CLI summary

```bash
# Aggregate (Step 5 entry point)
python tools/aggregate_results.py aggregate verification-results.json \
    --policy fail-or-partial \
    --out summary.json

# List expected findings (used by Step 5 to know what to write)
python tools/aggregate_results.py expected-findings verification-results.json \
    --policy fail-or-partial

# Validate (Step 5 exit gate, Step 6 entry gate)
python tools/aggregate_results.py validate audits/<run>/
```

## Stages that MUST consume summary.json

- **Step 5** — only writes finding docs for `expected_ids`
- **Step 6** — all counts in audit-report.md
- **Notion-Sync (`audit-notion-sync.py push`)** — `findings`, `production_ready`, `blocking_findings`
- **Portfolio dashboards** — comparable counts across servers

If any stage recomputes counts independently, that is a bug. File an issue.
