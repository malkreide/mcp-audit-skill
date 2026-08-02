# mcp-data-source-probe-skill

![Version](https://img.shields.io/badge/version-1.3.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill that probes a public data source *before* an MCP server is built against it — and measures whether the finished server returns what the source actually holds.

🇩🇪 [Deutsche Version](README.de.md)

## Overview

Building an MCP server against a documented API is easy. Building one that returns the *whole* dataset is not, because the ways in which an API quietly returns less than everything are invisible from a working example: an omitted filter that silently restricts the scope, a limit that defaults to 25, a full-text index that matches whole words so German compounds are unfindable.

This skill encodes a four-discipline procedure that the Swiss Public Data MCP portfolio (40+ servers) follows for every new data source. It is deliberately empirical: documentation is a photograph, a live probe is the current state, and we build on the current state.

The fourth discipline — **ground truth before self-confidence** — was added after a real incident. A server passed a 68-check audit and 33 green tests while searching one 23rd of its database, because an optional parameter it never sent defaults to a single subject area upstream. The bug was found by a user with the official web UI open beside it.

## Features

- **Step 1 — Live probe before design.** Five probe calls per endpoint, a default matrix for every optional parameter, recall ground truth against the source's own web UI, dump availability.
- **Step 2 — Architecture decision.** A decision tree that picks live-API / hybrid / dump-only from the probe findings, plus a portfolio-synergy check (new server or tool extension?).
- **Step 3 — Non-negotiable resilience defaults.** Retry with backoff, provenance and attribution in every response, anchor demo query, error-state tests, graceful degradation, and empty results that carry a next step instead of an excuse.
- **Steps 4–5 — Handover.** Inputs for repository creation and the portfolio card.
- **Findings culture.** Non-obvious discoveries are recorded so the next server inherits them rather than rediscovering them.

## Prerequisites

- Claude Code, Claude Desktop, or claude.ai with skill support
- `curl` and `python3` for the probe commands
- Optional: `jq` for ad-hoc JSON inspection

## Installation

```bash
git clone https://github.com/malkreide/mcp-data-source-probe-skill.git
cp -r mcp-data-source-probe-skill ~/.claude/skills/mcp-data-source-probe
```

The directory name must be `mcp-data-source-probe` — skill discovery uses it.

To install the companion skill `mcp-data-fidelity` as well (see below), clone it
from its own repository:

```bash
git clone https://github.com/malkreide/mcp-data-fidelity-skill.git
cp -r mcp-data-fidelity-skill ~/.claude/skills/mcp-data-fidelity
```

## Usage / Quickstart

The skill triggers on its own when you plan, build, or debug an MCP server against a data source. To invoke it explicitly:

```
> Ich würde gerne die API von opendata.swiss via MCP anbinden
> Warum findet mein Server nichts, obwohl das Web-UI 12 Treffer zeigt?
```

To run the probe template directly:

```bash
BASE="https://api.example.ch/v2" OUTDIR=/tmp/probe bash reference/probe_template.sh
```

## Project Structure

```
.
├── SKILL.md                              # the procedure itself
├── reference/
│   ├── probe_template.sh                 # runnable probe harness incl. scope_probe()
│   ├── befund_tabelle_template.md        # findings table: default matrix, recall ground truth
│   ├── response_envelope.py              # pydantic v2 envelope with source + provenance
│   └── retry_backoff.py                  # exponential backoff reference implementation
├── companion/
│   └── mcp-data-fidelity/
│       └── README.md                     # pointer — the skill moved to its own repo
└── scripts/
    └── validate.sh                       # the repository's checks; CI runs this file
```

## Companion skill: `mcp-data-fidelity`

`mcp-data-fidelity` used to ship in this repository under `companion/`. It now
lives in its own repository, which is its canonical home:
**[`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill)**.

The two divide the work by phase. `mcp-data-source-probe` covers what happens
*before and around* the build: probing the source, choosing an architecture,
measuring recall against ground truth. `mcp-data-fidelity` covers the code
itself — it complements Anthropic's `mcp-builder` with six rules for tools that
query an external source:

1. Send scope parameters explicitly, never inherit them
2. Send parameter groups in full — a partial set silently inherits server defaults
3. An empty result carries a concrete next step
4. The tool description is a hallucination surface
5. Query syntax belongs in the description, recall belongs in the tests
6. Confirm the response shape before counting it — a misread nesting returns the
   same empty list as a genuine zero-hit answer

It exists as a companion rather than a patch because `mcp-builder` is a vendored
Anthropic skill: editing it in place would be overwritten on the next sync, and
forking it would cut off upstream improvements. Installing both means the generic
build guidance and these rules apply together.

## The four disciplines

1. Live probe **before** design
2. Dump fallback **before** API dependency
3. Retry **before** defeatism
4. Ground truth **before** self-confidence

## Related repositories

Five skills, one build. Each answers a different question, in the order they come up:

| Repository | Role |
|---|---|
| [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) | Generic build guidance — Anthropic's skill, complemented rather than replaced |
| **`mcp-data-source-probe-skill`** | **This skill:** the procedure *before* the build |
| [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill) | Does it return what the source actually holds? Shipped here under `companion/` until it got its own repository |
| [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-transport-hardening-skill) | Does it come up, and does it turn away the right callers? |
| [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Auditing *after* the build |

Alongside them: [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) for continuous verification of servers in operation, and [`termdat-mcp`](https://github.com/malkreide/termdat-mcp), whose [issue #11](https://github.com/malkreide/termdat-mcp/issues/11) produced the fourth discipline.

Probe by this skill and build by `mcp-data-fidelity`, and you pass the `FID` checks; fail them in an audit and the remediation is there.

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## Contributing

Corrections are welcome: a probe command that no longer works, a source whose
behaviour has changed, a step that reads more clearly another way.

New steps and anti-patterns have a higher bar. This procedure is deliberately
empirical — documentation is a photograph, a live probe is the current state —
and the same standard applies to the procedure itself. A proposed step should
come from a source that actually behaved that way, and say which one, so the next
person can re-probe it. That is what the findings culture is for: a discovery
nobody wrote down gets rediscovered at full price.

The most useful contribution is usually the smallest one — a single line in the
default matrix for a source not yet listed, with the parameter description that
proves it.

Before opening a pull request, run the checks:

```bash
bash scripts/validate.sh
```

It is the same file CI invokes, so there is no second copy to drift out of step.
All seven checks run even after one fails, so a red run names every problem at
once. Worth knowing before editing the frontmatter: the `description` limit is
1024 characters and the current one leaves single digits of headroom — the
script prints what is left.

Open an issue before a large pull request, so the shape can be settled first.

## Security

This repository ships documentation and reference code — no running server, no
package to install. The Python files under `reference/` are material to adapt,
not a library to import.

`reference/probe_template.sh` is the exception worth reading before you run it:
it makes **live HTTP requests** against whatever `BASE` you point it at, several
per endpoint, and the scope probe deliberately asks for the maximum a source
will give. Point it only at sources you are authorised to query, and mind their
rate limits — an empirical probe is still traffic on somebody else's server.

It also writes **raw API responses** to `$OUTDIR` (default `/tmp/mcp-probe`).
Those files are the evidence a probe is meant to produce, and they can contain
whatever the source returned. Keep them out of commits, and treat them as data
subject to the source's terms rather than as scratch output.

Found an error in the procedure, or a case it gets wrong? Please open an issue.

## License

MIT License — see [LICENSE](LICENSE)

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)
