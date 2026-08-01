# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed

- **CI checks the version badge against the CHANGELOG.** It was the last figure
  in the README with nothing behind it, and it is the one most likely to be
  forgotten: the release is cut, the badge stays. In `mcp-audit-skill` it sat
  three releases behind before anyone noticed.

  Source is the topmost `## [X.Y.Z]` heading — `[Unreleased]` carries no version
  and is skipped by the pattern. The READMEs come from `glob("README*.md")`
  rather than a maintained list, so a third language is covered automatically.
  Both anchors are asserted separately: a CHANGELOG without a release heading and
  a README without a badge each fail, because a check that finds nothing is green.

  Mutation-tested four ways. One of them changed the design: removing the topmost
  release heading does not report a missing anchor, it silently falls back to the
  next release and blames the badge. The check still goes red, but the diagnosis
  pointed at the wrong file — so the failure message now names the CHANGELOG line
  it derived the expected version from, and says that either side may have moved.

## [1.1.0] - 2026-08-01

Documentation and guards. No rule added, changed or removed — seven rules, as in
1.0.0. What changes is that the skill now says where each rule is audited, and
that the reference file can no longer drift from the rules it claims to cover.

### Added

- **Rule-to-check mapping against the `mcp-audit` catalogue.** `SKILL.md` gains a
  table saying which rule corresponds to which check, verified by reading the
  check files rather than inferring from titles: rule 1 is `SDK-006`, rule 3 is
  `ARCH-013`, rule 4 is `SEC-024` with `SEC-005` as its outbound counterpart.

  It also names the two gaps rather than stretching a near-match over them. Rule 2
  has no check: `SEC-016` looks like one and is the opposite case — it treats
  `0.0.0.0` as an *unintended* bind (NeighborJack), while rule 2 assumes a
  deliberate one and asks whether it reaches the app. Rules 5–7 have no check
  either, which is a scope boundary: the catalogue verifies that a control exists,
  not that its proof holds.

- **The related-skills tables now name all five skills in one order** — builder,
  probe, fidelity, transport-hardening, audit — in `SKILL.md` and both READMEs, so
  the family reads the same way from every repository in it. `mcp-builder` is
  described as Anthropic's without a licence claim: `anthropics/skills` carries no
  LICENSE file and the API reports none, so stating one would be a guess in a
  public README.

- Contributing section in both READMEs. It states the bar a new rule has to
  clear: the incident it came from, a counter-example pair, and its Nachweis —
  the same form CI enforces. A plausible-sounding guideline without a scar behind
  it makes the skill longer and weaker.

### Changed

- **CI now checks `reference/patterns.py` for content, not just syntax.** Until
  now it was verified to exist and to compile; its two claims — the number word
  in the module docstring and that every rule actually appears — were guarded by
  nothing. Both happened to be correct, which is the least reliable reason for a
  value to be right.

  The rule-count step now covers the file as well: the docstring word against the
  count in `SKILL.md`, and the set of rules mentioned (`Rule 4`, `Rules 2 + 3`,
  `Rules 5-7` — ranges expanded) against the set that exists. A rule without a
  pattern is a rule nobody can copy, so a gap fails the build.

  Verified against three mutations rather than a green run: docstring reverted to
  "six" → *docstring says 'six' rules, SKILL.md defines 7*; the anchor phrase
  reworded → *anchor removed or reworded, so this check would silently stop
  checking*; every mention of rule 7 renamed → *nothing for rule(s) [7]*. All
  three reverted, green again.

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
