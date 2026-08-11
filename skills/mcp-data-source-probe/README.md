# mcp-data-source-probe

![Version](https://img.shields.io/badge/version-1.7.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill that probes a public data source *before* an MCP server is built against it — and measures whether the finished server returns what the source actually holds.

🇩🇪 [Deutsche Version](README.de.md)

## Overview

Building an MCP server against a documented API is easy. Building one that returns the *whole* dataset is not, because the ways in which an API quietly returns less than everything are invisible from a working example: an omitted filter that silently restricts the scope, a limit that defaults to 25, a full-text index that matches whole words so German compounds are unfindable.

This skill encodes a four-discipline procedure that the Swiss Public Data MCP portfolio (40+ servers) follows for every new data source. It is deliberately empirical: documentation is a photograph, a live probe is the current state, and we build on the current state.

The fourth discipline — **ground truth before self-confidence** — was added after a real incident. A server passed a 68-check audit and 33 green tests while searching one 23rd of its database, because an optional parameter it never sent defaults to a single subject area upstream. The bug was found by a user with the official web UI open beside it.

## Features

- **Step 1 — Live probe before design.** Five probe calls per endpoint, a default matrix for every optional parameter, a coverage matrix recording which part of the holdings no planned tool reaches, recall ground truth against the source's own web UI, a measured widening schedule, dump availability, and the source's refresh rhythm measured over at least two cycles — the number the advertised `ttlMs` is derived from.
- **Step 2 — Architecture decision.** A decision tree that picks live-API / hybrid / dump-only from the probe findings, a portfolio-synergy check (new server or tool extension?), and a second mandatory decision: which `mcp_spec_version` the server targets — `2026-07-28` by default, with a written reason for any deviation and no new server built on deprecated building blocks.
- **Step 3 — Non-negotiable resilience defaults.** Retry with backoff, provenance and attribution in every response, anchor demo query, error-state tests, graceful degradation, and empty results that carry a next step instead of an excuse.
- **Steps 4–6 — Handover.** Inputs for repository creation, plus two properties the generated scaffold carries: a `_version.py` that reads the installed package's own metadata (never a hand-written number), and an upper bound on every dependency, measured and dated in `PUBLISHING.md`. Then a stable start line on stderr, recorded as `start_event` in the register — and the register itself, whose normative half is a `portfolio.json` in the index repository: versioned, diffable, account-free. The human-readable half is a rendering you pick: a Notion database, a generated Markdown table, or none at all.
- **After the release.** The pre-release checklist covers the source tree; what ships is the artefact. Install the pinned version into an empty venv, run the console script for six seconds with stdin closed, compare the installed version against `main` — and remember that a tag publishes nothing: `publish.yml` fires on `release: types: [published]`.
- **Findings culture.** Non-obvious discoveries are recorded so the next server inherits them rather than rediscovering them.

## Prerequisites

- Claude Code, Claude Desktop, or claude.ai with skill support
- `curl` and `python3` for the probe commands
- Optional: `jq` for ad-hoc JSON inspection

## Installation

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git
cp -r mcp-audit-skill/skills/mcp-data-source-probe ~/.claude/skills/mcp-data-source-probe
```

The directory name must be `mcp-data-source-probe` — skill discovery uses it.

The four skills of the chain live in **one** repository since the
consolidation; copy whichever ones you want, they are independent at install
time. `mcp-audit` itself sits at the repository root and additionally ships as
a packaged `mcp-audit.skill`.

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
skills/mcp-data-source-probe/
├── SKILL.md                              # the procedure itself
├── CHANGELOG.md                          # this skill's own version history
├── README.md / README.de.md
└── reference/
    ├── probe_template.sh                 # runnable probe harness: scope, coverage,
    │                                     #   widening, freshness, order
    ├── befund_tabelle_template.md        # findings table: default matrix, recall
    │                                     #   ground truth, refresh rhythm, spec target
    ├── response_envelope.py              # pydantic v2 envelope with source + provenance
    ├── retry_backoff.py                  # exponential backoff reference implementation
    └── adoption.toml                     # what each template guarantees, per property
```

Around it, shared by all four skills — one configuration, one harness, one
test suite:

```
mcp-audit/
├── ruff.toml                             # one line width, one rule set
├── .pre-commit-config.yaml               # ruff pinned to the same version as CI
├── scripts/validate.sh                   # entry point; CI runs this file
├── tools/harness/                        # the registry — knows no single check
├── tools/gates/                          # the sixteen generic checks
├── tools/suites/mcp_data_source_probe/   # this skill's own nine checks
└── tests/                                # runs them, and holds them against the tree
```

`python -m tools.harness --suite probe` runs only this skill's checks;
`bash scripts/validate.sh` runs all four suites in one go.

## Sibling skill: `mcp-data-fidelity`

`mcp-data-fidelity` used to ship inside this skill, under `companion/`. It
then moved to its own repository, and since the consolidation both live in
`mcp-audit` as siblings: [`../mcp-data-fidelity/`](../mcp-data-fidelity/). The
pointer directory is gone with it — a pointer to the folder next door is not a
pointer, it is a detour.

The two divide the work by phase. `mcp-data-source-probe` covers what happens
*before and around* the build: probing the source, choosing an architecture,
measuring recall against ground truth. `mcp-data-fidelity` covers the query
code itself — it complements Anthropic's `mcp-builder` with rules for tools
that query an external source, from sending scope parameters explicitly to
declaring how many rows a sum silently dropped.

**The rules are not restated here, deliberately.** This section listed six of
them, written when there were six; there are fourteen now, and the list had
been wrong for months without anyone noticing — nothing held it against its
source. A neighbouring directory needs no copy:
[its README](../mcp-data-fidelity/README.md) carries the current list, and
[its SKILL.md](../mcp-data-fidelity/SKILL.md) the rules themselves.

It exists as a companion rather than a patch because `mcp-builder` is a
vendored Anthropic skill: editing it in place would be overwritten on the next
sync, and forking it would cut off upstream improvements. Installing both means
the generic build guidance and these rules apply together.

## The four disciplines

1. Live probe **before** design
2. Dump fallback **before** API dependency
3. Retry **before** defeatism
4. Ground truth **before** self-confidence

And the portfolio's mnemonic for the two time values that get confused most often — freshness inside, shelf life outside: *«Frische innen (`source_freshness`), Haltbarkeit aussen (`ttlMs`).»* One says how old the data is and looks backwards, at whoever reads the answer. The other says how long the answer stays valid and looks forwards, at the client's cache. They are never the same number.

## Related repositories

### The MCP quality chain

Four skills, one lifecycle. Each answers a different question, in the order they come up — this one comes first. Since the consolidation they live in **one** repository — this one; `mcp-continuous-auditor` is the runtime that keeps re-running them. The shared GitHub topic is [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain), which lists both repositories on one page.

| Stage | Skill | Question it answers |
|---|---|---|
| before the build | **`mcp-data-source-probe`** | **This skill:** is the source usable, and what does it hold? |
| in the build | [`mcp-data-fidelity`](../mcp-data-fidelity/) | Does it return what the source actually holds? Shipped under this skill's `companion/` until it got its own repository — and since the consolidation it sits right next door, which is why that pointer directory is gone. |
| in the build | [`mcp-transport-hardening`](../mcp-transport-hardening/) | Does it come up, and does it turn away the right callers? |
| after the build | [`mcp-audit`](../../) | Does it hold up against the catalogue? |

Running the chain, not a link in it: [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor). It asks no question in a server's lifecycle — it asks all four again, on a schedule, and answers «does it still hold up tomorrow?» — step 1.4's recall ground truth, kept running instead of measured once

Alongside, not part of the chain: [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) — Anthropic's generic build guidance, complemented rather than replaced. It is someone else's repository and cannot carry the topic.

Plus the server the fourth discipline came from: [`termdat-mcp`](https://github.com/malkreide/termdat-mcp), whose [issue #11](https://github.com/malkreide/termdat-mcp/issues/11) produced it.

Probe by this skill and build by `mcp-data-fidelity`, and you pass the `FID` checks; fail them in an audit and the remediation is there.

Membership is declared once, in [`docs/quality-chain.json`](../../docs/quality-chain.json) — `members` names the four skills, `repos` the two repositories that carry them. A check holds all eleven copies of this table against it — eight READMEs and three `SKILL.md` — so a fifth member cannot be added in one place and forgotten in ten.

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
pip install ruff==0.16.1 pytest pyyaml
pip install -r requirements-reference.txt
bash scripts/validate.sh
```

It is the same file CI invokes, so there is no second copy to drift out of step.
That now includes `ruff check` and `ruff format --check`: until 1.7.0 they ran
only in CI, which left the local runner able to report green on a tree CI
rejects. Every check runs even after one fails, so a red run names every problem
at once. Worth knowing before editing the frontmatter: the `description` limit
is 1024 characters and the current one leaves single digits of headroom — the
script prints what is left.

Changing or adding a check needs one more command:

```bash
pytest
```

The checks are ordinary functions under [`tools/suites/mcp_data_source_probe/`](../../tools/suites/mcp_data_source_probe/),
registered into the shared harness — `python -m tools.harness --suite probe`
runs exactly this skill's nine. The reason the suite matters at all is written
down in `ruff.toml`: it once held `select = []`, both ruff steps reported "All
checks passed!", and nobody noticed, because nothing went red.

**One thing has not moved yet, and it is worth naming rather than glossing
over:** in this skill's former standalone repository every check had at least
one tree in `tests/mutations.py` that it **must** go red on, together with an
assertion about *what it then says*. Those mutation suites are still in the
origin repositories; moving them is the last open step of the consolidation
(see [`docs/consolidation/MERGE-PLAN.md`](../../docs/consolidation/MERGE-PLAN.md)).
Until then that is an intention, not a guarantee — which is exactly the kind of
claim these skills exist to catch, so it says so here.

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

MIT License — see [LICENSE](../../LICENSE)

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)
