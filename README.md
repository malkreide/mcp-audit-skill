# mcp-data-fidelity-skill

![Version](https://img.shields.io/badge/version-1.7.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill for MCP server tools that query an external data source — so that a server does not quietly return less than the source holds.

🇩🇪 [Deutsche Version](README.de.md)

## Overview

Companion to Anthropic's `mcp-builder`. That skill covers whether a server is *built* correctly — naming, annotations, pagination, transport, error handling. This one covers the question next to it: **does it return what the source actually holds?**

That is a class of bug in its own right, because it is silent. HTTP 200, well-formed JSON, green tests — and wrong in substance. A server that searches two percent of a corpus without saying so produces answers nobody recognises as wrong.

The guiding question for every data-querying tool: *if this tool finds nothing, can I tell whether there is nothing there or whether I asked the wrong way?* If the answer is no, one of the fourteen rules applies. And the step below it, since rule 10: *and if I did ask the wrong way — can I get from here to the right question?*

## The fourteen rules

Rules 1–6 and 10–14 come from incidents. Rules 7–9 are derived from MCP spec 2026-07-28 — the difference is stated rather than smoothed over, in the README and in `SKILL.md`. The numbering follows the order the rules were added in, not that grouping.

1. **Send scope parameters explicitly, never inherit them.** An omitted optional filter often means an arbitrary slice rather than "unrestricted" — a fact stated only in the spec's parameter description, never visible from a working call. The converse holds too: a deliberate narrowing of recall (exact instead of wildcard, no fuzzy) has to name the rubrics or data classes carrying the risk **and** show, from the scope enumeration, that they are reachable. A rationale that would read the same for any source at all is coupled to nothing.
2. **Send parameter groups in full.** Send some members of a group and the rest keep their server-side default, so the argument can only widen, never narrow — a no-op that looks like control.
3. **An empty result carries a next step.** Zero hits are ambiguous. The result needs a concrete `hint` field, in the tool result rather than the README. A transport or authorization failure is not an empty result and must never be formatted as one — it carries a different next step: check the configuration, do not widen the search.
4. **The tool description is a hallucination surface.** A phrasing that *explains* an empty result causes confabulation more reliably than no phrasing at all. Ask for a retry, never license a conclusion.
5. **Query syntax in the description, recall in the tests.** Document the query language and its matching granularity; guard recall with live floors, because a mock reproduces the assumption it was written with. And assert on structured fields with exact equality, never a substring: a prefix assertion holds until the field value grows, and then it keeps holding while meaning something else.
6. **Confirm the response shape before counting it.** `payload.get("servers", [])` turns an upstream shape change into a valid-looking empty result. A schema mismatch belongs in the error channel, not in an empty list.
7. **A total, documented sort order.** A relevance score has ties, and an unstable order across page boundaries *loses rows* — the same silent incompleteness as rule 1, arrived at by paging rather than by filtering. Applies on every spec version; on 2026-07-28 it also decides whether a reconnect keeps the client's prompt cache.
8. **An honest `ttlMs`.** Never longer than the source's actual freshness: a `ttlMs` that outlives the next update lets the client serve an answer the server already knew would be stale. Derive it from `source_freshness`, and set `cacheScope` against `requires_credentials` — too wide a scope on a credential-dependent result is a leak, not a freshness bug.
9. **`input_required` is not an empty answer.** An MRTR follow-up question looks successful — HTTP 200, well-formed, no hits in it. Keep it strictly apart from a genuine zero-hit: no `hint` on a question, no `inputRequests` on an empty set. A model must never read "question" as "no data", or the reverse.
10. **Suggesting is not widening.** On an empty result, offer shorter variants of the term the caller sent — and query none of them. The safety property: no row in a result may be attributable to a term the caller did not choose. The Nachweis is a pair, not a single assertion — suggestions appear, suggestions are never searched (a call counter on the upstream route). Drop either half and the other passes trivially.
11. **An empty result carries the request that produced it.** Scope, filters and limits as they actually went out — not as the caller passed them in. "Nothing there" and "asked wrong" differ in exactly one thing, the request; leave it out and the model has nothing to tell them apart. The sharper half: a hint that reads the same on every empty result carries no information at all. The Nachweis is again a pair — the echo matches the outgoing request, and two runs that went out differently read differently, including the one where rule 1's best-effort scope widening quietly failed.
12. **Absence is three-valued: not collected / collected and empty / withheld.** One `null` for all three turns "we did not measure this" into a claim about the record that nobody measured. The third value is *set* where the decision was made, never derived from a lookup default — an unexpectedly missing key is a schema error (rule 6), not a state. And what it means, plus what the caller must do about it, is documented per field: silence is fatal on one field and free on the next, and no house-wide convention can carry that difference.
13. **The field name is part of the contract, spelling included.** Rule 6 asks whether the key is *there*; this asks whether it is there *in the spelling the code reads*. A wrong case gives you an empty hit list saying "not found" — no error, no exception, no log line. Normalise at the parse boundary, once, for every reader: hard-wiring either spelling tears the same hole open at the next switch, and a source that mixes spellings inside one header row will switch. Normalise **and then** confirm — rule 6 keeps its full strength afterwards, and two keys that collapse under normalisation are a finding, not a silent overwrite.
14. **A count column that does not hold counts.** Sources suppress small case numbers and write "1 bis 5", "<5", "NULL", or leave the cell empty — measured at 18.6 % and 18.1 % of two tables. Crashing on it is loud and honest; counting it as `0` is worse, because the sum stays plausible, is quietly too low, and is recognisable as wrong by nothing at all. Exclude those rows and **declare** how many, in the tool result and with the measured number: a sum missing a fifth of its rows in silence is not a sum, it is a lower bound passing itself off as one. Rule 12 sorts out the single cell; this rule is about what the sum does with it.

## Prerequisites

- Claude Code, Claude Desktop, or claude.ai with skill support
- The patterns in `reference/patterns.py` target FastMCP, httpx and pydantic v2 — the rules themselves are stack-independent
- Rules 8 and 9 assume MCP spec 2026-07-28: `ttlMs`/`cacheScope` on the list responses and MRTR (`resultType: "input_required"`) do not exist before it. On an older or frozen server they are ticked off as not applicable, not as unmet. Rules 1–7 and 10–14 apply either way.

## Installation

```bash
git clone https://github.com/malkreide/mcp-data-fidelity-skill.git
cp -r mcp-data-fidelity-skill ~/.claude/skills/mcp-data-fidelity
```

The directory name must be `mcp-data-fidelity` — skill discovery uses it.

## Usage / Quickstart

The skill triggers on its own when a search, query, or filter tool is designed, when a tool description is written, or when a server is reported to return too little. To invoke it explicitly:

```
> Schreib die Tool-Description für dieses Such-Tool
> Warum findet mein Server nichts, obwohl das Web-UI 12 Treffer zeigt?
```

## Project Structure

```
.
├── SKILL.md                  # the fourteen rules, with the release checklist
├── reference/
│   └── patterns.py           # copy-paste FastMCP / httpx / pydantic v2 patterns
├── scripts/
│   └── validate.sh           # entry point for the checks; CI runs this file
├── tools/
│   └── checks/               # the checks themselves — one function per gate
└── tests/
    ├── mutations.py          # per check, a tree it MUST go red on
    └── test_*.py             # runs them, and holds the checks against this repo
```

## Where these rules come from

Rules 1–5 come from a single real incident: [`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). The server sent `ClassificationIds` only when the caller supplied them; the upstream API restricts an ID-less search to `VARIA` — one of 23 classifications. "Quellensteuer" returned zero hits despite several matching entries, "Pensionskasse" one instead of 21.

Four things about it generalise:

1. **33 green offline tests caught nothing** — a mock cannot in principle refute the assumption it was written with.
2. **A 68-check audit had passed** — every category tested how the server was built, none tested data fidelity.
3. **The server's own documentation pushed the model into confabulating** — see rule 4.
4. **It was found by a user with the web UI open beside it** — ground truth comes from outside the test suite.

Rule 6 was added after a second case: an MCP Registry query returned nothing for a while because the fields sit under `servers[].server.*` and the client looked one level up. Syntactically fine, semantically blind.

Rule 10 and the addendum to rule 1 come from a third case, [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp), and it shipped. Version 0.20.0 declined a suggestion mechanism and argued the refusal from bankruptcy notices, debt-collection summonses, estate calls and construction objections — rubrics the server's allow-list exists to exclude. Since the searchable set is therefore the non-sensitive one, the sensitive-data exemption was claimed for exactly the set the criterion applies to. The reasoning stood in both `SECURITY` files, the CHANGELOG and the closing PR; the [2026-07-30 re-audit](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md) caught it, 0.22.0 fixed it.

The opposite direction is the second error of the same case: the suggestion mechanism the check asks for reads as permission to query the suggestions as well — and then the server serves notices under a term nobody chose. Both routes end in the same trap, which is why the resolution splits them rather than choosing between them.

Rules 13 and 14 come from a fifth case, and like the third it shipped: [`zh-education-mcp`](https://github.com/malkreide/zh-education-mcp) against [`www.bista.zh.ch`](https://www.bista.zh.ch), noticed on 2026-08-03. Twice the same form, at two different places in the same row. The field **name**: the code read `r["Schulgemeinde"]`, the source delivered `schulgemeinde`, and the result was not an exception but an empty hit list saying "Schulgemeinde not found" — a failure that looks like an answer. Four of six endpoints in use had switched, and two of them mix the spelling inside one header row, which is why the fix is not "move to the new spelling" but "normalise at the parse boundary". The **value**: the source suppresses small case numbers and writes "1 bis 5" into a column called a count — 18.6 % and 18.1 % of two tables, 1.0 % "NULL" in a third. What generalises is the ranking of the three responses, and that the middle one surprises: the crash is honest, the silent `0` is not.

Rules 7–9 do **not** have that provenance, and the skill says so where it states them. They are derived from MCP spec 2026-07-28: a stateless core without `initialize`, so reconnects are the normal case (rule 7); `ttlMs`/`cacheScope` on the list responses (rule 8); MRTR replacing server-initiated elicitation (rule 9). Derived, not measured — which in this repository is a difference worth naming. The bar for an outside proposal is unchanged: it still needs an incident. What cleared the lower bar here is a protocol change that hits all 42 servers of the portfolio at once, not a plausible-sounding guideline.

## Related repositories

### The MCP quality chain

Five repositories, one lifecycle. Each answers a different question, in the order they come up. The shared GitHub topic is [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain), which lists all five on one page.

| Stage | Repository | Question it answers |
|---|---|---|
| before the build | [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | Is the source usable, and what does it hold? Default matrix (1.2b), recall ground truth (1.4), empty results (3.6). Distributed this skill under `companion/` until this repository became its home. |
| in the build | **`mcp-data-fidelity-skill`** | **This skill:** does it return what the source actually holds? |
| in the build | [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-transport-hardening-skill) | Does it come up, and does it turn away the right callers? The same silent class one layer down — not what the answer contains, but whether one arrives at all |
| after the build | [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Does it hold up against the catalogue? Rules 1–6 map onto the six `FID` checks — not one to one: rules 3 and 4 share `FID-003`, rule 5 needs `FID-005` and `FID-002`, rule 6 is `FID-006`. Rules 7–9 sit outside `FID`, in `ARCH-020`, `HITL-006` and `ARCH-018`, with rule 9's boundary against the empty set in `FID-003`; rule 10 sits on `ARCH-003` (catalogue: 113 checks on `main`, v2.0.0 cut; all of these checks are advisory except `ARCH-003`, which is enforced and applies always). Rules 12, 13 and 14 sit on no check at all. Full table, with what each check does *not* cover, in `SKILL.md`. |
| in operation | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Does it still hold up tomorrow? Its recall floors are rule 5 kept running against the live source. |

Alongside, not part of the chain: [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) — Anthropic's generic build guidance, complemented rather than replaced. It is someone else's repository and cannot carry the topic.

Plus the two servers this skill came from: [`termdat-mcp`](https://github.com/malkreide/termdat-mcp), whose [issue #11](https://github.com/malkreide/termdat-mcp/issues/11) produced rules 1–5, and [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp), whose [`ARCH-003` finding](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md) produced rule 10 and the scope addendum to rule 1.

Build by rules 1–6 and you pass the `FID` checks; fail them in an audit and the remediation is here. Rules 7–9 are covered outside `FID`, and those checks are `advisory` — they are counted, not enforced. Rule 10 is the exception: `ARCH-003` blocks. Three rules have no check at all — 12, 13 and 14 — and for the rest what remains open is scope rather than coverage, the widest of those being rule 7: its check measures on baseline `2026-07-28`, while pagination loss also happens on `2025-11-25`. Which is a gap and which is a named edge is stated per row in `SKILL.md`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## Contributing

Corrections are welcome: a rule that is wrong, a case it decides badly, a source
whose defaults have changed since the table was written.

New rules have a higher bar. Rules 1–6 each come from a specific failure that
actually happened, and that is the main reason the set is worth reading — a
plausible-sounding guideline without a scar behind it makes the skill longer and
weaker. Rule 10 clears the same bar: shipped in `amtsblatt-mcp` 0.20.0, caught by
the re-audit, fixed in 0.22.0. So do rules 13 and 14: shipped in `zh-education-mcp`,
noticed against the live source on 2026-08-03, with the share of affected endpoints
and suppressed rows measured rather than estimated. A proposal should name the incident, carry a ✗/✓ pair, and state its
**Nachweis**: the two calls, the delta, the assertion that separates a working
control from a broken one.

Rules 7–9 cleared a lower bar and say so in the text: their evidence is the
mechanism of MCP spec 2026-07-28, derived rather than measured. That exception is
for a protocol change affecting every server at once, not a second route in for
guidelines in general. Should one of the three show up in the wild, the incident
belongs in this file.

The skill's own subject applies to the proposal. If a rule cannot be violated in
a way that something notices, it is not yet a rule — and if the evidence for it
comes only from a mock, it is not yet evidence.

Before opening a pull request, run the checks:

```bash
pip install -r requirements-dev.txt
bash scripts/validate.sh
pytest
```

`validate.sh` is the same file CI invokes, so there is no second copy to drift
out of step. Every check runs even after one fails, so a red run names every
problem at once.

`pytest` applies the paragraph above to the checks themselves. Each one is an
ordinary function under `tools/checks/`, and each has at least one tree in
`tests/mutations.py` that it **must** go red on — along with an assertion about
*what it then says*. A check without a mutation fails the suite. The same
sentence, one level up: a check that cannot be violated in a way that something
notices is not yet a check.

Open an issue before a large pull request, so the shape can be settled first.

## Security

This repository ships documentation and reference code — no running server, no
package to install. `reference/patterns.py` is material to adapt, not a library
to import: the names stand in for whatever the target project calls them.

The failure class these rules address is an integrity problem rather than a
classic vulnerability. A server that searches a fraction of its corpus without
saying so returns answers that look correct, cannot be recognised as wrong, and
are then used to make decisions. Rule 4 is the sharpest form of it: a tool
description that *explains* an empty result reliably produces confabulation.

One half of rule 8 is a classic vulnerability rather than an integrity problem:
`cacheScope`. On a server whose results depend on the caller's credentials, too
wide a scope means one caller's answer is served to another. That is a data leak,
not a stale cache, and it is decided in the same line of code as the `ttlMs`.

Two limits worth stating. The scope widening in rule 1 is deliberately
best-effort — if the vocabulary endpoint is unreachable the query still runs,
just unwidened — so a transient upstream failure narrows recall without failing
the call. And the `rows_of()` guard in rule 6 validates only the envelope and the
fields actually read, not the full response schema; that is a deliberate trade,
not an oversight.

Found an error in the rules, or a case they get wrong? Please open an issue.

## License

MIT License — see [LICENSE](LICENSE)

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)
