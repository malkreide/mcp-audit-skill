# mcp-transport-hardening

![Version](https://img.shields.io/badge/version-2.4.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill for MCP servers — so that a server comes up at all under the transport it is configured for, says so on stderr, turns away who it must turn away, and holds up once the session is gone.

🇩🇪 [Deutsche Version](README.de.md)

## Overview

Companion to Anthropic's `mcp-builder`. That skill covers whether a server is *built* correctly — naming, annotations, pagination, transport, error handling. This one covers the question next to it: **does it come up under the configured transport, does it turn away who it must turn away, and does that survive the removal of the session?**

That is a class of bug in its own right, because it is silent — differently silent from [`mcp-data-fidelity`](../mcp-data-fidelity/). There, the server returns a plausible answer that is wrong in substance. Here it returns none at all: green unit tests, a clean linter, and in production the process does not start, or answers every request under a real hostname with HTTP 421. The startup path is exactly the part a suite that imports modules never touches.

Three guiding questions:

- *If I change the bind, does the inbound allow-list follow — on every path that builds an app — and does a test go red when it doesn't?* (rules 1–4)
- *If two callers share nothing — no handshake, no session, no connection — does one still see the other's state, and does a test go red when it does?* (rules 8–12)
- *If I start the published artifact and ask it nothing — how do I see that it is serving?* If the answer is "by the absence of an error", rule 14 applies. This one needs no transport at all.

### Scope: where the line sits, not the transport it runs

Up to `2.2.0` this skill excluded stdio-only servers. That boundary was **refuted**, not merely imprecise: `zh-education-mcp` `0.2.4` carried the 1.x settings assignment from rule 1(b), and that line sits *before* the transport branch — so the server was just as dead under stdio as under HTTP. Anyone who had skipped this skill because their server runs stdio would have kept the bug, and the published version stayed unusable for months because nothing ever started the installed artifact.

So the question is not "does this server speak HTTP?" but "does this line sit before or behind the transport branch?". Everything ahead of it — imports, settings assignments, the lifespan, the readiness marker — runs under **every** transport. Only rules 2–4 and 9 require a network transport; rule 14 is the one where a stdio server is the main case rather than the edge case.

## How the fourteen rules are ordered

| Block | Rules | Question |
|---|---|---|
| Bind and wiring | 1–4 | Does it come up, and does it refuse correctly? |
| The proof | 5–7, 13 | How do you know it holds, and who does the proof cover? Applies to 8–12 as well |
| The stateless world, spec `2026-07-28` | 8–12 | Does it hold without a session, and does it speak the new envelope? |
| The serving state | 14 | Does it announce that it is listening, or do you have to assume it? |

The proof block sits in the middle rather than at the end because it is older than the third block, and because this repository, its own CHANGELOG and four sibling repositories cite "rule 6" and "rules 5–7" by number. Renumbering would make that history retroactively wrong, so new rules are appended rather than inserted — rules 13 and 14 belong further up (with the proof block and with block 1 respectively) and still sit at the end for exactly that reason.

Rules 1–7 hold on **both** spec baselines: bind, wiring, the host allow-list and the way you prove them hang off the transport, not off the lifecycle. Rules 8–12 apply on `2026-07-28`. And the two baselines stand next to each other, not one after the other — measured in the portfolio, one process can serve a legacy `initialize` handshake capped at `2025-11-25` while also serving a per-request envelope that reaches `2026-07-28`. A stateless bug is therefore invisible to every client still on the old era.

## The fourteen rules

1. **The SDK major bump breaks three things, only one of them mechanically.** Module and class rename is search-and-replace; `mcp.settings` turning read-only stops the process from starting at all; annotations moving to snake_case breaks only Python-side reads, because the wire format is unchanged — which is why camelCase stays correct in TypeScript servers. The version cap is load-bearing at both ends, and the standalone `fastmcp` package pins `mcp<2.0`, so it is a fork in the road rather than a formality. And a bound only bites once the lock is re-resolved: setting it in `pyproject.toml` alone leaves the deployment installing what it installed before.
2. **`host` is the seed of the allow-list, not a cosmetic parameter.** It defaults to `127.0.0.1`, and the SDK derives the inbound allow-list from it. Not passing it through means HTTP 421 on exactly the `0.0.0.0` deployment the server is documented for. uvicorn calls a `--factory` with no arguments, so `--host` never reaches the app; on a PaaS the port arrives at boot, so the allow-list has to be composed from it rather than written as a literal.
3. **Every path that builds an ASGI app is wired identically.** A custom builder used only when auth or CORS happens to be set, the SDK-served `run()` path, a deprecated SSE path — wire one and arming a security control silently depends on unrelated configuration. The port travels with the host, and since `2026-07-28` so does the header check from rule 9.
4. **The inbound host allow-list is its own control.** CORS does not help (same-origin from the browser's view), a token does not help (the attacking page holds one), the egress allow-list is the opposite direction. Port-exact, loopback always in, CORS origins included, no `*`, and fail-open on non-loopback made visible with a startup warning. It is the one inbound control that did not disappear with the lifecycle.
5. **A negative test must fail for *your* reason, not a default's.** Green only means the request was rejected — not that your control rejected it. `evil.example.com` is refused in every state, including a fallback loopback policy; right hostname with the *wrong port* is the case only a port-exact list decides correctly. Every negative test needs its positive twin.
6. **The mutation test is the acceptance criterion for a security control.** Not "write tests" — name the mutation, apply it, *prove by diff that it landed*, then record which tests fall, and put the table in the PR. A row with zero red tests is a finding: either the test is missing, or the control does nothing, or the mutation never applied — and a replacement that hit nothing looks exactly like a surviving mutant.
7. **The test harness is itself a source of error on HTTP transports.** A bare `httpx.ASGITransport` returns 500 on everything because it never runs the app lifespan; an instance-level `monkeypatch` can shadow `mcp.run` permanently and start real uvicorn mid-suite; and a branch test that does not assert its branch hangs instead of failing. The fourth trap has no symptom at all: an autouse fixture that patches a *foreign* module — `monkeypatch.setattr(mod.asyncio, "sleep", …)` reads as local but reaches into `asyncio` itself, so it holds for every import in the process and every test in the suite — can defuse a concurrency check by removing the yield to the event loop, leaving a green test with nothing left to check. Patch a module alias the repository owns, and replace the duration, not the handover.
8. **Without a session, state is shared silently rather than missing.** `initialize` and `Mcp-Session-Id` are gone; every request carries protocol version, client info and capabilities in `_meta`. The dangerous server is not the one that crashes but the one that keeps running with process-local state that used to be addressed per session — one caller notices nothing, two get a data leak that raises no error. State travels as explicit, server-minted, expiring handles in ordinary tool arguments, and `server/discover` is a MUST for servers even though it is a MAY for clients.
9. **The address is now written on the outside of the envelope, and both sides must read the same one.** `Mcp-Method` and `Mcp-Name` are mandatory on Streamable-HTTP POSTs, and a mismatch is `-32020`. A gateway deciding on the header while the server decides on the body means two parties ruling on two different requests, so comparing them server-side is a security boundary — including the omission case, because a check that only runs when the headers are present is bypassed by leaving them out.
10. **Legacy HTTP+SSE now has a date: `2027-07-28`.** Deprecated since `2025-03-26`, but only now under the feature-lifecycle policy with a twelve-month window. A recommendation without a date produces no work item, only a compatibility path nobody switches off — and that second network path does not inherit the first one's hardening. The detection recipe runs over three places: code, what the deployment actually starts, and the wire.
11. **MRTR: the server answers and holds nothing open — in exchange, the work runs more than once.** `resultType: "input_required"` ends the processing; the client repeats the whole request with `inputResponses`. Everything before the question point happens again on every retry, which turns a UI concern into a correctness one: side effects belong behind the question point or behind an idempotency key. And no retry is guaranteed, so nothing may be reserved without a way to release it.
12. **Auth hardening — and the negative finding this portfolio records instead of omitting.** RFC-9207 `iss` validated before the code is redeemed (including a *missing* `iss` from an issuer that advertises it), CIMD instead of DCR, credentials keyed by issuer. For this read-only portfolio the rule does not apply, for a nameable reason: no server redeems an authorization code. Written out rather than left out, because an omitted section is indistinguishable from an overlooked one.
13. **A guard does not check what branched off before it.** From the merge commit onward, and only forward: the state already on `main` was never run against it, and every branch cut before the merge lands without it. Trigger the workflow on `push` to `main` as well as on pull requests, look at that run once after merging, and pull the open branches up to `main` (`git branch -r --no-contains <merge-sha>`). It belongs with rules 5–7 and is numbered last so the existing numbers survive.
14. **The server announces that it is listening.** Every server has a moment where it stops being a process and starts being a server. From the outside both states look identical — a PID doing nothing — so "it runs" is an assumption rather than an observation. On stdio there is exactly one channel to tell them apart: stderr (stdout belongs to the protocol, an exit code arrives too late, and there is no port). Survey of 2026-08-03, 42 published servers: 15 say nothing of their own — 13 nothing at all, 2 only the banner the SDK writes. Four properties make a log line a marker: the `event`/`msg` field of a structured log is compared for **equality** and not by prefix (`openlex-mcp` was documented as «Lifespan gestartet» and actually read «Lifespan gestartet — geteilter HTTP-Client bereit»); plain text gets a stable substring; never a timestamp, port, PID or config-dependent count; and the FastMCP banner does not count, because it is the SDK talking and it disappears on the next SDK release. Everything that can fail sits **before** the marker, and the marker is documented in the README in the spelling that gets compared.

## Prerequisites

- Claude Code, Claude Desktop, or claude.ai with skill support
- The concrete code targets the Python MCP SDK 2.x (`mcp.server.mcpserver`) behind an ASGI server; the reasoning in rules 3–14 is stack-independent

## Installation

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git
cp -r mcp-audit-skill/skills/mcp-transport-hardening ~/.claude/skills/mcp-transport-hardening
```

The directory name must be `mcp-transport-hardening` — skill discovery uses it.

The four skills of the chain live in **one** repository since the
consolidation; copy whichever ones you want, they are independent at install
time. `mcp-audit` itself sits at the repository root and additionally ships as
a packaged `mcp-audit.skill`.

## Usage / Quickstart

The skill triggers on its own when a server is migrated to a new SDK major or to spec `2026-07-28`, switched from stdio to a network transport, reported to answer with HTTP 421, or found to say nothing on stderr at startup. To invoke it explicitly:

```
> Migrier diesen Server auf Spec 2026-07-28
> Warum antwortet mein Server mit 421, obwohl der Bind auf 0.0.0.0 steht?
> Hat dieser Server noch einen Legacy-SSE-Pfad?
```

## Project Structure

```
skills/mcp-transport-hardening/
├── SKILL.md                              # the fourteen rules, each with a Nachweis
├── CHANGELOG.md                          # this skill's own version history
├── README.md / README.de.md
└── reference/
    └── patterns.py                       # copy-paste MCP SDK 2.x / ASGI / uvicorn patterns
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
├── tools/suites/mcp_transport_hardening/ # this skill's own six checks
└── tests/                                # runs them, and holds them against the tree
```

`python -m tools.harness --suite transport` runs only this skill's checks;
`bash scripts/validate.sh` runs all four suites in one go.

## Where these rules come from

**Rules 1–7 come from three pull requests of the same cycle (2026-07):**

| PR | Starting point |
|---|---|
| [`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29) | Migration 1.x → 2.x, as the **last server in the portfolio** still on the old major. A real startup failure plus a 421 in the HTTP path, reproduced against the real ASGI stack before the fix |
| [`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51) | No 421 bug — the bind arrived correctly. What was missing was any way to say under which names the server may be addressed |
| [`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25) | No 421 bug. An egress allow-list existed, nothing inbound — and the port fell out on the way to the app builder |

What generalises:

1. **Only one of the three was a bug.** The other two were a missing control — defensible for the intended deployment, but anyone running the server differently had no way in. Missing configurability fails no test, because nothing is wrong.
2. **Green tests and a clean linter, and the process does not start.** Tool tests import modules and never touch the startup path. Up to `2.2.0` this line ended with "the fault waits for the first HTTP deployment" — that is wrong, see `zh-education-mcp` below: it waits for the first *start*, under whichever transport.
3. **The last server on the old major was the one no list knew about.** `openparldata-mcp` sits *nested* inside another repository with its own `pyproject.toml`, so it fell through every enumeration that lists top-level repos — and the parent project's dependency constraint never covered it either. An inventory that counts repositories rather than deployable units misses exactly the cases that stay unmigrated longest.
4. **The mutation test corrected the tests in two of three repos, not the code** — which is where rule 6 comes from.
5. **A test that hangs instead of failing is worse than none** — which is where rule 7 comes from. Without the control the forbidden request is *allowed*, and for a stream, allowed means waiting.

**Rules 8–12 have no scar, they have a date.** That distinction is stated rather than glossed over, because the contributing section below asks every new rule for a concrete failure that actually happened. Their occasion is spec revision `2026-07-28` — an external, dated event whose changes are not plausible-sounding but citable. What they share with the first seven is the form: a ✗/✓ pair and a Nachweis naming the mutation that turns it red.

Two things about them are *measured* rather than assumed, both on `zurich-opendata-mcp`: that one mcp 2.x process serves the legacy handshake and the new per-request envelope side by side, and that the rule 10 detection recipe comes back negative on all three places for a server that has no legacy path. Both are measurements on one repository, and the rules claim no more than that.

**Rule 14 and the corrected scope come from `zh-education-mcp` `0.2.4` (2026-08).** The server still carried the 1.x settings assignment from rule 1(b); measured against the artifact installed from PyPI into an empty venv it died with `ValueError: "Settings" object has no field "host"`. Three things generalise, and the second is the point:

1. **The published version was unusable for months and nobody noticed** — because nothing ever started the installed artifact. What gets tested is the checkout; what ships is the distribution. That axis is `IDENT-007` in the catalogue.
2. **The fault was transport-independent, and this skill's own scope claimed the opposite.** The assignment sat *before* the transport branch, so the server was as dead under stdio as under HTTP — while the description said "not needed for servers that only run over stdio". The boundary was not imprecise, it was refuted: it excluded the case that occurred.
3. **It would have started silently in the healthy case too** — which is where rule 14 comes from. There was no difference to notice: a server that says nothing at startup looks the same whether it succeeded or died.

The measurement that found it costs nothing and is now part of rule 1(b)'s Nachweis: start the console script under stdio with stdin closed, wait six seconds, look at the exit code.

**On naming:** two of the three PRs carry `SEC-005` in the title but implement the *inbound* control, which is `SEC-024` in the audit catalogue. `SEC-005` is the outbound direction (DNS pinning against TOCTOU). Two attacks, one name.

## Related repositories

### The MCP quality chain

Four skills, one lifecycle. Each answers a different question, in the order they come up. Since the consolidation they live in **one** repository — this one; `mcp-continuous-auditor` is the runtime that keeps re-running them. The shared GitHub topic is [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain), which lists both repositories on one page.

| Stage | Skill | Question it answers |
|---|---|---|
| before the build | [`mcp-data-source-probe`](../mcp-data-source-probe/) | Is the source usable, and what does it hold? |
| in the build | [`mcp-data-fidelity`](../mcp-data-fidelity/) | Does it return what the source actually holds? |
| in the build | **`mcp-transport-hardening`** | **This skill:** does it come up, turn away the right callers, and stay stateless? |
| after the build | [`mcp-audit`](../../) | Does it hold up against the catalogue? |

Running the chain, not a link in it: [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor). It asks no question in a server's lifecycle — it asks all four again, on a schedule, and answers «does it still hold up tomorrow?»

Alongside, not part of the chain: [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) — Anthropic's generic build guidance, complemented rather than replaced. It is someone else's repository and cannot carry the topic.

Membership is declared once, in [`docs/quality-chain.json`](../../docs/quality-chain.json) — `members` names the four skills, `repos` the two repositories that carry them. A check holds all eleven copies of this table against it — eight READMEs and three `SKILL.md` — so a fifth member cannot be added in one place and forgotten in ten.

### Boundary: this skill, the catalogue, the live probe

The three repositories touch the same subjects and ask different questions. Without that separation there is duplication, and duplication ages apart.

**Here is how you wire it and how you see that it holds. The catalogue asks whether it is there. The auditor asks whether it is still there today.**

Against `mcp-audit` v2.3.0 (120 checks in twelve categories, two spec baselines): rule 1 is `SDK-006` plus `DEP-001`, rule 3 is `ARCH-013`, rule 4 is `SEC-024` (the outbound counterpart is two checks, `SEC-005` and `SEC-028`), rule 6 is `OPS-010`, rule 8 is `ARCH-015`/`ARCH-016`/`ARCH-017`, rule 9 is `SCALE-008`, rule 10 is `SCALE-009`/`SCALE-010`, rule 11 is `HITL-006`, rule 12 is `SEC-025`/`SEC-026`, rule 14 is `OBS-008` (with `IDENT-007` next to rule 1(b)). Rules 2 and 7 have no check; for rules 5 and 13 a check sits next to the rule or covers one half of it — the full mapping in [SKILL.md](SKILL.md) names the gaps rather than papering over them, together with the five checks that measure something `2026-07-28` removed and the spec changes this skill deliberately leaves to the catalogue.

Rule 6 changed sides in this pass, and the direction is worth naming: `OPS-010` was written *against the gap this table declared*, and its `pdf_ref` says so. A mapping ages from both ends — until now only this repository's rule set had moved. One reservation stays in the row: `OPS-010` is `advisory`, so a server can miss it and still pass the audit.

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## Contributing

Corrections are welcome: a rule that is wrong, a case it decides badly, an SDK
detail that has moved on.

New rules have a higher bar. A rule earns its place through a specific failure
that actually happened, or through a dated external change that can be cited —
and which of the two it is has to be stated, as it is for rules 8–12. A
plausible-sounding guideline with neither behind it makes the skill longer and
weaker. A proposal should name its occasion, carry a ✗/✓ pair, and state its
**Nachweis**: how someone would demonstrate the rule holds, and what they would
break to see it fail. CI enforces that shape.

Rules 5–7 and 13 apply to the proposal itself. If a rule cannot be violated in a way
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

Rule 12 records a **negative finding** rather than guidance: this portfolio is
read-only and redeems no authorization code, so RFC-9207 `iss` validation, CIMD
and issuer-bound credentials do not currently apply. The condition that lifts
it is named in the rule. Anyone reusing this material with an authenticating
server should treat rule 12 as in scope from the first credential onwards.

Found an error in the rules, or a case they get wrong? Please open an issue.

## License

MIT License — see [LICENSE](../../LICENSE)

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)
