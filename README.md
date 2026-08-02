# mcp-transport-hardening-skill

![Version](https://img.shields.io/badge/version-1.2.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill for MCP servers on a network transport — so that a server comes up at all under the transport it is configured for, and turns away who it must turn away.

🇩🇪 [Deutsche Version](README.de.md)

## Overview

Companion to Anthropic's `mcp-builder`. That skill covers whether a server is *built* correctly — naming, annotations, pagination, transport, error handling. This one covers the question next to it: **does it come up under the configured transport, and does it turn away who it must turn away?**

That is a class of bug in its own right, because it is silent — differently silent from [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill). There, the server returns a plausible answer that is wrong in substance. Here it returns none at all: green unit tests, a clean linter, and in production the process does not start, or answers every request under a real hostname with HTTP 421. The transport path is exactly the part a stdio test suite never touches.

The guiding question for every server on a network transport: *if I change the bind, does the inbound allow-list follow — on every path that builds an app — and does a test go red when it doesn't?*

Rules 1–4 concern the server, rules 5–7 the proof. The second half is the more expensive one: transport rules can be looked up, the way you prove them cannot.

## The seven rules

1. **The SDK major bump breaks three things, only one of them mechanically.** Module and class rename is search-and-replace; `mcp.settings` turning read-only stops the process from starting at all; annotations moving to snake_case breaks only Python-side reads, because the wire format is unchanged — which is why camelCase stays correct in TypeScript servers.
2. **`host` is the seed of the allow-list, not a cosmetic parameter.** It defaults to `127.0.0.1`, and the SDK derives the inbound allow-list from it. Not passing it through means HTTP 421 on exactly the `0.0.0.0` deployment the server is documented for. uvicorn calls a `--factory` with no arguments, so `--host` never reaches the app.
3. **Every path that builds an ASGI app is wired identically.** A custom builder used only when auth or CORS happens to be set, the SDK-served `run()` path, a deprecated SSE path — wire one and arming a security control silently depends on unrelated configuration. The port travels with the host.
4. **The inbound host allow-list is its own control.** CORS does not help (same-origin from the browser's view), a token does not help (the attacking page holds one), the egress allow-list is the opposite direction. Port-exact, loopback always in, CORS origins included, no `*`, and fail-open on non-loopback made visible with a startup warning.
5. **A negative test must fail for *your* reason, not a default's.** Green only means the request was rejected — not that your control rejected it. `evil.example.com` is refused in every state, including a fallback loopback policy; right hostname with the *wrong port* is the case only a port-exact list decides correctly. Every negative test needs its positive twin.
6. **The mutation test is the acceptance criterion for a security control.** Not "write tests" — name the mutation, apply it, record which tests fall, and put the table in the PR. A row with zero red tests is a finding: either the test is missing or the control does nothing.
7. **The test harness is itself a source of error on HTTP transports.** A bare `httpx.ASGITransport` returns 500 on everything because it never runs the app lifespan; an instance-level `monkeypatch` can shadow `mcp.run` permanently and start real uvicorn mid-suite; and a branch test that does not assert its branch hangs instead of failing.

## Prerequisites

- Claude Code, Claude Desktop, or claude.ai with skill support
- The concrete code targets the Python MCP SDK 2.x (`mcp.server.mcpserver`) behind an ASGI server; the reasoning in rules 3–5 is stack-independent

## Installation

```bash
git clone https://github.com/malkreide/mcp-transport-hardening-skill.git
cp -r mcp-transport-hardening-skill ~/.claude/skills/mcp-transport-hardening
```

The directory name must be `mcp-transport-hardening` — skill discovery uses it.

## Usage / Quickstart

The skill triggers on its own when a server is migrated to a new SDK major, switched from stdio to a network transport, or reported to answer with HTTP 421. To invoke it explicitly:

```
> Migrier diesen Server auf mcp 2.x
> Warum antwortet mein Server mit 421, obwohl der Bind auf 0.0.0.0 steht?
```

## Project Structure

```
.
├── SKILL.md                  # the seven rules, with the release checklist
└── reference/
    └── patterns.py           # copy-paste MCP SDK 2.x / ASGI / uvicorn patterns
```

## Where these rules come from

Three pull requests from the same cycle (2026-07):

| PR | Starting point |
|---|---|
| [`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29) | Migration 1.x → 2.x, as the **last server in the portfolio** still on the old major. A real startup failure plus a 421 in the HTTP path, reproduced against the real ASGI stack before the fix |
| [`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51) | No 421 bug — the bind arrived correctly. What was missing was any way to say under which names the server may be addressed |
| [`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25) | No 421 bug. An egress allow-list existed, nothing inbound — and the port fell out on the way to the app builder |

What generalises:

1. **Only one of the three was a bug.** The other two were a missing control — defensible for the intended deployment, but anyone running the server differently had no way in. Missing configurability fails no test, because nothing is wrong.
2. **Green tests and a clean linter, and the process does not start.** Tool tests run over stdio and never touch the transport path. The fault waits for the first HTTP deployment.
3. **The last server on the old major was the one no list knew about.** `openparldata-mcp` sits *nested* inside another repository with its own `pyproject.toml`, so it fell through every enumeration that lists top-level repos — and the parent project's dependency constraint never covered it either. An inventory that counts repositories rather than deployable units misses exactly the cases that stay unmigrated longest.
4. **The mutation test corrected the tests in two of three repos, not the code** — which is where rule 6 comes from.
5. **A test that hangs instead of failing is worse than none** — which is where rule 7 comes from. Without the control the forbidden request is *allowed*, and for a stream, allowed means waiting.

**On naming:** two of the three PRs carry `SEC-005` in the title but implement the *inbound* control, which is `SEC-024` in the audit catalogue. `SEC-005` is the outbound direction (DNS pinning against TOCTOU). Two attacks, one name.

## Related repositories

### The MCP quality chain

Five repositories, one lifecycle. Each answers a different question, in the order they come up. The shared GitHub topic is [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain), which lists all five on one page.

| Stage | Repository | Question it answers |
|---|---|---|
| before the build | [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | Is the source usable, and what does it hold? |
| in the build | [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill) | Does it return what the source actually holds? |
| in the build | **`mcp-transport-hardening-skill`** | **This skill:** does it come up, and does it turn away the right callers? |
| after the build | [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Does it hold up against the catalogue? |
| in operation | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Does it still hold up tomorrow? |

Alongside, not part of the chain: [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) — Anthropic's generic build guidance, complemented rather than replaced. It is someone else's repository and cannot carry the topic.

The audit catalogue covers three of the seven rules: rule 1 is `SDK-006`, rule 3 is
`ARCH-013`, rule 4 is `SEC-024` (with `SEC-005` as its outbound counterpart).
Rules 2 and 5–7 have no check — see the mapping in [SKILL.md](SKILL.md), which
names the gaps rather than papering over them.

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## Contributing

Corrections are welcome: a rule that is wrong, a case it decides badly, an SDK
detail that has moved on.

New rules have a higher bar. Every rule here comes from a specific failure that
actually happened, and that is the only reason the set is worth reading — a
plausible-sounding guideline without a scar behind it makes the skill longer and
weaker. A proposal should name the incident, carry a ✗/✓ pair, and state its
**Nachweis**: how someone would demonstrate the rule holds, and what they would
break to see it fail. CI enforces that shape.

Rules 5–7 apply to the proposal itself. If a rule cannot be violated in a way
that something notices, it is not yet a rule.

Open an issue before a large pull request, so the shape can be settled first.

## Security

This repository ships documentation and reference code — no running server, no
package to install. `reference/patterns.py` is material to adapt, not a library
to import: the names stand in for whatever the target project calls them, and
the fixtures it references come from the target project's own `conftest.py`.

Two points matter when applying rule 4. The allow-list is **fail-open** on a
non-loopback bind when nothing is configured; that is deliberate, because a
guessed list rejects the deployment it is meant to protect, but it means an
unconfigured server on `0.0.0.0` has no inbound Host check. The startup warning
is the signal that this is the state you are in. And the inbound allow-list does
not replace authentication or an egress allow-list — it answers a different
question, as the rule sets out.

Found an error in the rules, or a case they get wrong? Please open an issue.

## License

MIT License — see [LICENSE](LICENSE)

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)
