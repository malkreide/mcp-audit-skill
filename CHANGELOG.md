# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`reference/patterns.py`** — copy-paste patterns for all five rules, targeting
  MCP SDK 2.x behind ASGI/uvicorn:
  - `build_transport_security()` with the four properties spelled out at the call
    site — port-exact, loopback always present, configured CORS origins folded in,
    `*` dropped — and the fail-open branch that warns instead of guessing.
  - `create_http_app()` as a uvicorn `--factory` that reads its own bind, with
    the reason in the docstring: a factory is called with no arguments, so
    `--host` never reaches the app.
  - `serve_http()` wiring one policy object into all three branches that can
    serve HTTP — SDK-served `run()`, the custom builder, and the deprecated SSE
    path — and `build_http_app()` which receives the policy rather than building
    its own.
  - `is_read_only()` plus `test_wire_format_is_unchanged()`, which makes rule
    1(c)'s Nachweis runnable: if the pydantic alias still emits `readOnlyHint`,
    the change is read-side only and no client contract is at stake.
  - The four test shapes from rule 5, each carrying the mistake it corrects:
    the regression test that must run *without* `MCP_ALLOWED_HOSTS`, the
    right-host-wrong-port case, the valid token that must not save a foreign
    host, and the branch assertion that makes a wrong branch fail instead of
    hang. With the mutation table as a comment block and a closing note on
    `TestClient` versus a bare `httpx.ASGITransport`.

## [1.0.0] - 2026-07-31

Initial release. Five rules for MCP servers on a network transport, covering the
gap between "the server is built correctly" and "the server comes up and turns
away who it must turn away".

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
- **Rule 5 — a control is unproven until removing it turns something red.**
  Mutation testing as the acceptance criterion, with the two failure shapes
  observed: a regression test that passes *with* the mutation applied because it
  set the allow-list env var itself, and a control whose removal makes the suite
  *hang* rather than fail. Covers the seam rule (test where the value travels,
  not the function that already has it) and the bare `httpx.ASGITransport` that
  returns 500 because it never runs the app lifespan.
- **Deployment checklist** with 17 items, and a naming note: two of the source
  PRs are titled `SEC-005` but implement `SEC-024`, the inbound control.

### Context

The rules come from three pull requests of the same cycle (2026-07):
[`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29),
[`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51) and
[`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25).

Only the first was a bug. The other two were a missing control — defensible for
the intended deployment, but leaving anyone who runs the server differently
without a way in, and failing no test because nothing was wrong. In two of the
three repositories the mutation test corrected the tests rather than the code,
which is where rule 5 comes from.
