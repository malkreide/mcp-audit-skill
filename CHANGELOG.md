# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-07-29

Initial public release. The skill had been in internal use across the Swiss
Public Data MCP portfolio; this release publishes it together with the
data-fidelity additions described below.

### Added

- **Step 1.2b — default matrix.** For every optional parameter of every endpoint
  used: what does omitting it actually mean? The answer lives only in the spec's
  parameter description — never in the response schema, never in a working
  example. Includes an extraction snippet for OpenAPI parameter descriptions, a
  table of the usual suspects (CKAN `rows`, WFS `maxFeatures`, SPARQL named
  graphs, Elasticsearch `size`, GraphQL `first`), and the rule that a non-zero
  recall delta is a finding.
- **Step 1.4 extended to query endpoints.** Formerly "reality check against
  homepage figures", now recall ground truth against the source's official web
  UI — explicitly for search endpoints, not only list endpoints. With a selection
  rule for 3–5 reference terms and a recall canary as a live test using floors
  rather than exact counts.
- **Fifth probe call per endpoint** — the scope probe (parameter omitted vs.
  explicitly maximal).
- **Step 3.6 — an empty result is not absence.** The tool description as a
  hallucination surface: a phrasing that explains an empty result causes
  confabulation more reliably than no phrasing at all. Two non-negotiable rules
  (a `hint` field on empty results; no description that explains or excuses one)
  plus query-syntax and whole-word matching guidance.
- **`scope_probe()` and `count_of()`** in `reference/probe_template.sh` —
  runnable, verified against a live API.
- **Two mandatory sections** in `reference/befund_tabelle_template.md`: default
  matrix and recall ground truth.
- **Anti-patterns 7 and 8** ("optional means unrestricted", "zero hits means
  there is nothing"), a fourth line in the mantra, and a findings entry
  documenting the incident these additions came from.

### Changed

- Note on the limits of mocking under step 3.4: a mock reproduces the assumption
  it was written with, so scope and recall bugs are structurally invisible to it.
- Skill description now also triggers on the symptom rather than only the task —
  "finds nothing", "too few results", "web UI shows more".

### Context

Sections 1.2b, 1.4 and 3.6 come from a single real incident:
[`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). The
server sent `ClassificationIds` only when the caller supplied them; the upstream
API restricts an ID-less search to one of 23 classifications. Searching for
"Quellensteuer" returned nothing despite several matching entries.

The uncomfortable part is that this skill already contained the check that would
have caught it. Step 1.4 was applied to the list endpoints — 140 collections, 23
classifications, both correct — and never to the search endpoint. The rule was
not missing; its reach was. That is recorded in the findings section rather than
quietly fixed.
