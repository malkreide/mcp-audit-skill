# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-07-31

First standalone release. The skill was previously distributed as
`companion/mcp-data-fidelity/` inside
[`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill);
this repository makes it the canonical home. The skill content is unchanged from
that copy — packaging only.

### Added

- **Rule 1 — send scope parameters explicitly, never inherit them.** An omitted
  optional filter frequently means an arbitrary slice rather than "unrestricted".
  The fact lives only in the spec's parameter description — not in the response
  schema, not in the documentation example, and not visible from a working call.
  With the table of the usual suspects (CKAN `rows`, WFS `maxFeatures`, SPARQL
  named graphs, Elasticsearch `size`, GraphQL `first`, TERMDAT
  `ClassificationIds`) and the two-call recall delta that proves it.
- **Rule 2 — send parameter groups in full.** Members of a group that are not
  sent keep their server-side default, so the argument can widen but never
  narrow — a no-op that looks like control.
- **Rule 3 — an empty result carries a next step.** Zero hits are ambiguous
  between absent term, too narrow a query, restricted scope, and wrong syntax.
  The `hint` belongs in the tool result, not in the README, because the README is
  not handed to the model.
- **Rule 4 — the tool description is a hallucination surface.** The
  counter-intuitive one: a phrasing that explains an empty result causes
  confabulation more reliably than no phrasing at all. A caveat must ask for a
  retry, never license a conclusion.
- **Rule 5 — query syntax in the description, recall in the tests.** Query
  language plus matching granularity, since whole-word indexes make German
  compounds unfindable from their parts. Recall guarded by live floors rather
  than exact counts, because a test that cries wolf gets switched off.
- **Rule 6 — confirm the response shape before counting it.** Rules 1–5 cover
  what the server *sends* and what it *tells* the model; rule 6 covers what it
  *reads*. `payload.get("servers", [])` turns an upstream shape change into a
  valid-looking empty result — the same confabulation surface as rule 3, one
  layer down. A schema mismatch belongs in the error channel.
- **`reference/patterns.py`** — copy-paste FastMCP / httpx / pydantic v2
  patterns for all six rules, including the `rows_of()` guard, which deliberately
  checks only the envelope and the fields the caller actually reads rather than
  validating a full schema.
- **Release checklist** for a data-querying tool, in `SKILL.md`.

### Context

Rules 1–5 come from a single real incident:
[`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). The
server sent `ClassificationIds` only when the caller supplied them; the upstream
API restricts an ID-less search to one of 23 classifications. Searching for
"Quellensteuer" returned nothing despite several matching entries — past 33 green
offline tests and a passed 68-check audit.

Rule 6 comes from a second case: an MCP Registry query returned nothing for a
while because the fields sit under `servers[].server.*` and the client looked one
level up. Syntactically fine, semantically blind.

[Unreleased]: https://github.com/malkreide/mcp-data-fidelity-skill/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/malkreide/mcp-data-fidelity-skill/releases/tag/v1.0.0
