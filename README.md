# mcp-data-source-probe-skill

![Version](https://img.shields.io/badge/version-1.0.0-blue)
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
└── reference/
    ├── probe_template.sh                 # runnable probe harness incl. scope_probe()
    ├── befund_tabelle_template.md        # findings table: default matrix, recall ground truth
    ├── response_envelope.py              # pydantic v2 envelope with source + provenance
    └── retry_backoff.py                  # exponential backoff reference implementation
```

## The four disciplines

1. Live probe **before** design
2. Dump fallback **before** API dependency
3. Retry **before** defeatism
4. Ground truth **before** self-confidence

## Related repositories

| Repository | Role |
|---|---|
| [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Auditing *after* the build. The same rules appear there as checks `FID-001`–`FID-005`. |
| [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Continuous verification of servers in operation |
| [`termdat-mcp`](https://github.com/malkreide/termdat-mcp) | The server whose [issue #11](https://github.com/malkreide/termdat-mcp/issues/11) produced the fourth discipline |

Build by this skill and you pass the `FID` checks; fail them in an audit and the remediation procedure is here.

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## License

MIT License — see [LICENSE](LICENSE)

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)
