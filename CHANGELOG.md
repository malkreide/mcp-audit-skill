# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-08-01

Adds a structural-assertion discipline to the probe, splits the companion skill
out into its own repository, and documents what running the probe template
actually does.

### Changed

- **`companion/mcp-data-fidelity/` is now a pointer, not a copy.** The skill has
  its own repository —
  [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill),
  released as `v1.0.0` — and that is its canonical home. What sat here was
  byte-identical to that release, so the move loses nothing; keeping it would
  have meant maintaining two copies that drift. The directory now holds a single
  `README.md` naming the new location, so anyone browsing the old path lands on
  a signpost rather than a 404.
- Both READMEs point at the standalone repository for installation, and the
  companion section now lists **six** rules rather than five — rule 6 was added
  after the copy was made, so this repository has been describing the companion
  by one rule short of what it shipped.
- CI drops the companion from the syntax check, the frontmatter check and the
  file list, and gains a guard that fails if a `SKILL.md` ever reappears under
  `companion/` — that reappearance is exactly the drift the split ended.

- Both READMEs gain a **Security** section. The one thing in this repository that
  actually does something is `reference/probe_template.sh`, and it deserved
  saying out loud: it makes live HTTP requests against whatever `BASE` it is
  given — several per endpoint, with the scope probe deliberately asking for the
  maximum a source will return — and it writes raw API responses to `$OUTDIR`.
  Point it only at sources you may query, mind their rate limits, and keep the
  output out of commits.

### Removed

- `companion/mcp-data-fidelity/reference/__pycache__/patterns.cpython-311.pyc`,
  a compiled artefact that had been committed by accident.

### Added

- **Section 1.2c — structural assertion before an empty probe counts as a
  finding.** A misread nesting returns the same empty list as a genuine
  zero-hit answer: no error, no status code, no warning. Evidence: an MCP
  Registry query kept returning nothing because the fields live under
  `servers[].server.*` and the probe looked one level up. Every probe that
  reports zero must also print the response's top-level keys and a truncated
  raw excerpt, and the finding table gains a "structure confirmed" column.
  Same rule as 3.6, one layer up: there it protects the model from the tool,
  here it protects the probe from itself.
- **1.2c, second part — aggregated endpoints lag behind authoritative ones.**
  PyPI's aggregate JSON endpoint reported the previous version after three
  consecutive releases while the simple index and a real install were current.
  Any freshness claim must record *which* endpoint was queried.
- **Anti-patterns 9 and 10** plus two release-checklist items for the above.
- **`mcp-data-fidelity` rule 6 — confirm the response shape before counting
  it.** Rules 1–5 cover what the server *sends* and what it *tells* the model;
  rule 6 covers what it *reads*. `payload.get("servers", [])` turns an upstream
  shape change into a valid-looking empty result — the same confabulation
  surface as rule 3, one layer down. A schema mismatch belongs in the error
  channel, not in an empty list.
- **`rows_of()` guard in `companion/mcp-data-fidelity/reference/patterns.py`**,
  deliberately not full schema validation: it checks only the envelope and the
  fields the caller actually reads. Verified against all four cases — valid,
  missing envelope, wrong type, fields one level deeper — plus a genuine empty,
  which still returns `[]`.

- **Companion skill `mcp-data-fidelity`** under `companion/`, separately
  installable. Five rules for MCP tools that query an external data source:
  scope parameters sent explicitly, parameter groups sent in full, empty results
  that carry a next step, the tool description as a hallucination surface, and
  query syntax in the description with recall in the tests. Ships with
  copy-paste FastMCP / httpx / pydantic patterns in `reference/patterns.py`.

  It is a companion rather than a patch to Anthropic's `mcp-builder` because
  that skill is vendored: an in-place edit would be overwritten on the next
  sync, and a fork would cut off upstream improvements.

- CI validates the companion skill alongside the main one — Python syntax,
  frontmatter, and file presence.

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
