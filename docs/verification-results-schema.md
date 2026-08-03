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
| `pass` | Check fully satisfied, on positive evidence | No |
| `fail` | Check failed; concrete remediation needed | **Yes** |
| `partial` | Check 50%+ but not fully satisfied | **Yes** |
| `not_verified` | Applicable and attempted; no evidence either way | No (yes under `needs-attention`) |
| `todo` | Manual review required, not attempted yet | No |
| `n/a` | Not applicable to this profile (rare; usually omitted) | No |

#### Why `not_verified` is its own value

[`OPS-004`](../checks/OPS-004.md) has required this status since it was written — "a `pass` rests on positive evidence, not on the absence of negative evidence; otherwise the status is `not_verified`" — while this schema did not know the value. A status the schema rejects cannot be recorded, so an auditor who followed the rule got a validation error and wrote `pass` instead: the one outcome `OPS-004` exists to forbid. A rule the tooling makes impossible to follow is not a strict rule; it is a rule that resolves to its opposite.

`not_verified` versus `todo` turns on whether anyone looked. `todo` is work not started. `not_verified` is work done that produced no answer — a tool that could not be reached, a behaviour reproducible only in production, a grep whose pattern cannot be shown to fire when the anti-pattern is present. Only the second belongs under «Offen» in the report.

It does not veto a release: an unanswerable check is not a failed one. It is listed *beside* the verdict instead, in `not_verified_findings`, and named in the executive summary — a green verdict over a large unverified set is a narrower claim than the same verdict over none, and the reader has to be able to tell them apart.

### Severity enum

`critical`, `high`, `medium`, `low`. Mirrors the check-file frontmatter.

### Required fields per result

- `status` — one of the values above
- `category` — `ARCH`, `SEC`, `CH`, `HITL`, `OBS`, `OPS`, `SCALE`, `SDK`
- `severity` — one of the values above
- `adoption` — `enforced` (default) or `advisory`. Optional; omitting it keeps
  the check blocking, so a results file written before this field existed
  behaves exactly as it did. Prefer `aggregate --checks-dir` over setting it
  here: the catalogue is authoritative, and a stage that depends on whoever
  wrote the results file is a stage that silently does not apply.
- `evidence` (list of strings) — **enforced against the catalogue.**
  `aggregate --checks-dir` holds every judged result to that check's
  `evidence_required` and refuses to write a summary if one falls short.
- `gaps` (list of strings, may be empty)

#### Why the evidence count is enforced, and enforced on `pass` too

This line used to read "may be empty", and that was the hole.
`evidence_required` has sat in the frontmatter of all 90 checks from the
beginning and `SKILL.md` states the rule in prose — but nothing under `tools/`
ever read the field, so a `pass` carrying an empty evidence list went through
the gate untouched.

The asymmetry is what makes it matter. An unevidenced `fail` gets worked on:
somebody opens the finding document and looks. An unevidenced `pass` **ends the
conversation** about that check, and nothing downstream ever disagrees with it.
It is the same defect as an empty finding document — which this schema already
rejects — pointing the direction where it is invisible.

A rule nobody enforces holds right up until somebody is in a hurry, which is
when it is needed. It has already failed that way: a *confirmed* circular import
in `bag-health-mcp` was closed as an import-order artefact, on reasoning rather
than a second measurement. The reasoning was wrong and the probe was right. An
explanation that names no measurement has not closed anything.

What each status owes:

| Status | Evidence required |
|---|---|
| `pass`, `fail`, `partial` | the catalogue's full `evidence_required` |
| `not_verified` | one item — what was attempted |
| `todo`, `n/a` | none |

`not_verified` owes one rather than the full count because by definition it has
no evidence *either way*: requiring the full count would contradict the status,
and requiring nothing would make it the way around the gate. `todo` and `n/a`
claim nothing, and demanding observations for them would push an auditor to
invent some — the opposite of the point.

Whitespace-only entries do not count. Two spaces are exactly as informative as
no entry, and the failure this guards against produces both.

`--allow-unevidenced` downgrades the refusal to warnings, for migrating an older
results file. The summary then records `evidence_gate.enforced = false`, as it
does when `--checks-dir` is omitted entirely — because a summary that stays
silent about a gate that did not run reads exactly like one that passed it.

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
      "pass": 8, "fail": 6, "partial": 9, "not_verified": 2, "todo": 3, "n/a": 7
    },
    "by_severity_among_findings": {
      "critical": 0, "high": 1, "medium": 14, "low": 0
    },
    "by_category": {
      "ARCH": {"pass": 5, "fail": 3, "partial": 5,
               "not_verified": 0, "todo": 0, "n/a": 0},
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
  "blocking_findings": ["OPS-001"],
  "not_verified_findings": ["SEC-014", "OBS-003"],
  "catalog_epoch": {
    "previous_run_id": "2026-07-02T101500-Z-srgssr-mcp",
    "previous_catalog_hash": "a1b2c3…",
    "catalog_hash": "d4e5f6…",
    "previous_checks_evaluated": 36,
    "checks_evaluated": 54,
    "comparable": false,
    "reason": "catalogue changed between the runs …"
  }
}
```

### Catalog epochs

`catalog_epoch` appears only when `aggregate` was given `--previous`. It answers one question: **may this run's numbers be put beside the previous run's?**

Two audits of the same server are a trend only if they were measured with the same ruler. When the catalogue changes between them, «30 pass / 4 fail / 2 partial → x/y/z» is not a delta — it is two different measurements with an arrow drawn between them. In the run this comes from, that arrow would have spanned 36 checks against 54, and every number would have been read as movement in the server.

The comparison is therefore refused rather than normalised. There is no correct way to subtract a count taken over one catalogue from a count taken over another, and a footnote does not survive being quoted. With `comparable: false`, [`tools/build_report.py`](../tools/build_report.py) prints both catalogue hashes, both check counts and the reason — and no status comparison at all. With `comparable: true`, it prints a `delta_by_status` table.

An unknown hash on either side is also `comparable: false`. Not knowing whether the ruler changed is not the same as knowing it did not.

### Target revision

`audit-meta.json` carries `target_sha` / `target_dirty` when [`tools/audit_init.py init`](../tools/audit_init.py) was given `--target-repo`. `catalog_hash` pins what the audit was measured *with*; `target_sha` pins what it was measured *against*. Without the second, a commit landing mid-audit splits the report silently: checks that ran before it describe one tree, checks after it another, and the report presents the mixture as one verdict.

`aggregate_results.py validate` re-checks it and hard-fails on a moved target, recording the outcome under `target.status` (`unchanged` / `moved` / `unrecorded` / `unreachable` / `unreadable`). Only `moved` fails; a run that never recorded a SHA warns, because failing those would just teach auditors to pass `--skip-target-check` by reflex.

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
