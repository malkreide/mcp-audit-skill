# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Contributing section in both READMEs. It states the bar a new rule has to
  clear: the incident it came from, a counter-example pair, and its Nachweis —
  the same form CI enforces. A plausible-sounding guideline without a scar behind
  it makes the skill longer and weaker.

## [1.0.0] - 2026-08-01

Initial release. Seven rules for MCP servers on a network transport, covering the
gap between "the server is built correctly" and "the server comes up and turns
away who it must turn away" — and, in rules 5–7, how to prove that it does.

### Added

- **Rule 1 — the SDK major bump breaks three things, only one of them
  mechanically.** The module and class rename (`mcp.server.fastmcp.FastMCP` →
  `mcp.server.mcpserver.MCPServer`) is search-and-replace. `mcp.settings` turning
  read-only is not: the assignment raises `ValueError`, a read raises
  `AttributeError`, and a server carrying the old line does not start under HTTP
  at all — the bind goes to `run()` as kwargs instead. Annotations move to
  snake_case for Python-side reads only; camelCase survives as a pydantic alias
  and the wire format is unchanged, which is why a test finds this and no client
  would, and why camelCase remains correct in TypeScript servers. Includes the
  distinction between the standalone PyPI package `fastmcp` and
  `mcp.server.fastmcp` in the official SDK — two projects, one name.
- **Rule 2 — `host` is the seed of the allow-list, not a cosmetic parameter.**
  It defaults to `127.0.0.1` and the SDK derives the inbound allow-list from it,
  so an app builder that never receives it answers HTTP 421 on exactly the
  `0.0.0.0` deployment it is documented for. With the uvicorn trap: a `--factory`
  is called with no arguments, so `--host` configures the listener and never
  reaches the app, and the README must say why the env vars are not redundant
  next to the flags.
- **Rule 3 — every path that builds an ASGI app is wired identically.** A custom
  builder used only when auth or CORS is configured, the SDK-served `run()` path,
  and a deprecated SSE path alongside it. Wire one and arming a security control
  silently depends on unrelated configuration. The port travels with the host —
  one repo passed only the host, so the loopback entries named a port nobody
  serves.
- **Rule 4 — the inbound host allow-list is its own control.** Why CORS, a
  token, and the egress allow-list all miss the question, and the four
  properties that make the list usable: port-exact, loopback always in, CORS
  origins included, no `*`. Fail-open on a non-loopback bind, made visible with a
  startup warning, because a guessed list rejects the deployment it should
  protect.
- **Rule 5 — a negative test must fail for *your* reason, not a default's.**
  Green only says the request was rejected, not that your control rejected it.
  `evil.example.com` is refused by the correct list, by a loopback fallback, and
  by a hostname-only list alike — three states, one green test, no information.
  Right hostname with the wrong port is the case only a port-exact list decides
  correctly, and it needs its positive twin to rule out the fallback state.
- **Rule 6 — the mutation test is the acceptance criterion for a security
  control.** Not "write tests": name the mutation, apply it, record which tests
  fall, and put the table in the PR. Carries all three finds from the source
  PRs — the test that set the allow-list variable itself and so passed *with* the
  mutation applied; the dropped port that failed no test at all because the seam
  was untested; and the removal that made the suite hang instead of fail.
- **Rule 7 — the test harness is itself a source of error on HTTP transports.**
  The bare `httpx.ASGITransport` and its 500s, the instance-versus-class
  `monkeypatch` trap that shadows `mcp.run` and starts real uvicorn mid-suite,
  and the branch test that must assert its branch or hang. With the SSE
  explanation for *why* a missing control hangs rather than fails.
- **Release checklist** with 20 items, split into "Der Server (Regeln 1–4)" and
  "Der Beweis (Regeln 5–7)", and a naming note: two of the source PRs are titled
  `SEC-005` but implement `SEC-024`, the inbound control. `SEC-005` is the
  outbound direction.
- **`reference/patterns.py`** — copy-paste patterns for all seven rules,
  targeting MCP SDK 2.x behind ASGI/uvicorn:
  - `build_transport_security()` with the four properties spelled out at the call
    site — port-exact, loopback always present, configured CORS origins folded in,
    `*` dropped — and the fail-open branch that warns instead of guessing.
  - `create_http_app()` as a uvicorn `--factory` that reads its own bind, with
    the reason in the docstring: a factory is called with no arguments, so
    `--host` never reaches the app.
  - `serve_http()` wiring one policy object into all three branches that can
    serve HTTP — SDK-served `run()`, the custom builder, and the deprecated SSE
    path — and `build_http_app()`, which receives the policy rather than building
    its own.
  - `is_read_only()` plus `test_wire_format_is_unchanged()`, which makes rule
    1(c)'s Nachweis runnable: if the pydantic alias still emits `readOnlyHint`,
    the change is read-side only and no client contract is at stake.
  - The test shapes for rules 5–7: the `client` fixture built through the app
    lifespan; the rule 5 pair plus the `evil.example.com` test written out as a
    comment showing why it is *not* used; `test_real_hostname_is_accepted`, which
    must run without `MCP_ALLOWED_HOSTS` or it passes with the mutation applied;
    `_patch_run()` carrying the patch-level trap and its symptom; both branch
    tests, each asserting which branch ran; and `test_the_sse_path_is_wired`,
    which checks the wiring precisely where an end-to-end test would hang.
  - Rule 6's mutation table as a comment block, and a closing note on running the
    suite under a timeout and each branch test alone *and* in the full suite.
- Bilingual README (EN/DE) and a CI workflow that enforces the skill's own form:
  every rule carries a counter-example pair and a Nachweis, the rule numbers are
  sequential, and the count matches both READMEs.

### Context

The rules come from three pull requests of the same cycle (2026-07):
[`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29),
[`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51) and
[`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25).

Only the first was a bug. The other two were a missing control — defensible for
the intended deployment, but leaving anyone who runs the server differently
without a way in, and failing no test because nothing was wrong.

Two things about the first one generalise beyond its own fix. It was the last
server in the portfolio still on the old SDK major, because it sits *nested*
inside another repository with its own `pyproject.toml`: it fell through every
enumeration that lists top-level repos, and the parent project's dependency
constraint never covered it. And in two of the three repositories the mutation
test corrected the *tests* rather than the code — which is where rules 5–7 come
from, and why they are in this skill at all.
