# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2026-08-03

Sieben Regeln, unverändert — dieses Release ändert nichts an dem, was der Skill
lehrt. Es ändert eine Zeile in der Zuordnung Regel → Audit-Check: Die drei
Beweisregeln standen zusammengefasst als «kein Check», obwohl für Regel 5 einer
danebenliegt, der dieselbe Fehlerklasse fängt. Eine Sammelzeile ist bequem und
selten falsch genug, um aufzufallen — genau die Eigenschaft, gegen die diese
Tabelle geschrieben wurde.

### Changed

- **Die Regel-zu-Check-Zuordnung führt die Regeln 5, 6 und 7 einzeln,
  nachgeführt gegen `mcp-audit` v1.7.0.** Sie standen in einer Zeile als
  «5–7 — die Beweisführung: kein Check». Für Regel 6 stimmt das weiterhin, für
  Regel 5 nicht: [`DRIFT-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/DRIFT-003.md)
  — «Kein Test-Assert wird vom Degradationspfad erfüllt» — ist dieselbe Klasse,
  ein Test, der aus dem falschen Grund besteht. Seine Ausprägungen sind andere
  (Degradationsantwort, zu weite Koordinaten-Box, `match=` als Regex statt als
  Literal), und der Transportfall steht nicht darin — der Negativtest, den auch
  eine Loopback-Fallback-Policy grün macht. Bei Regel 7 liegt `OPS-005`
  benachbart, ohne die Harness-Fälle zu treffen.

  Der Fehler war keine Veralterung: `DRIFT-003` (Katalog v1.2.0) und `OPS-005`
  (v1.3.0) existierten bereits, als die Tabelle geschrieben wurde. Eine
  zusammengefasste Zeile verdeckt genau das, was die Tabelle sichtbar machen
  soll — deshalb stehen die drei Regeln jetzt einzeln da, auch wenn zwei davon
  leer bleiben.

  Dazu der Katalogstand im Text (v1.7.0, 97 Checks in zwölf Kategorien), damit
  beim nächsten Wachstum erkennbar ist, wogegen zuletzt geprüft wurde.

## [1.3.0] - 2026-08-02

Seven rules, unchanged — nothing here touches what the skill teaches. The
related-repositories table becomes the MCP quality chain, five repositories
along the lifecycle with a shared GitHub topic, and the same table now stands in
`SKILL.md` rather than only in the READMEs.

One figure was wrong: the rule-to-check mapping claimed four of seven rules
where it covers three. Four is the count of the rules the catalogue does *not*
see — the sentence directly below the table said so all along.

### Changed

- **The related-repositories table is now the MCP quality chain, and it names all
  five members.** The table listed four skills plus `mcp-builder` and left
  `mcp-continuous-auditor` out. It is not a skill, but it is the fifth link:
  the only one that keeps checking after the audit has passed. The table now runs
  along the lifecycle — before the build, in the build, after the build, in
  operation — and `mcp-builder` sits beside it rather than in it, because it is
  someone else's repository and cannot carry the shared topic.

- **The five now share a GitHub topic,
  [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain).** They
  referenced each other in prose already; on GitHub the intersection of their
  topics was empty, so nothing tied them together for anyone who had not already
  found one of them. The topic is verified weekly by
  `tools/check_quality_chain.py` in `mcp-audit-skill`, which carries the manifest
  — that metadata lives outside every working copy and is unreachable from here.

### Added

- **A CI step asserting the chain table names all five members** — the chain table is the only place the five are named together,
  so a check makes sure it has not quietly lost a member, in both language
  versions, and that it links the topic page.

### Fixed

- **The table in `SKILL.md` was still the old five-skill list.** The READMEs
  became the quality chain — five repositories along the lifecycle, with
  `mcp-continuous-auditor` in and `mcp-builder` beside it — while the table the
  model actually reads still named the previous set. The CI guard added with the
  chain only reads the READMEs, so nothing caught it. `SKILL.md` now carries the
  same five in the same order, with the stage column, and keeps the pointer from
  the audit row to the rule-to-check mapping below it.

- **The rule-to-check mapping said four rules where it covers three.** The table
  maps rule 1 to `SDK-006`, rule 3 to `ARCH-013` and rule 4 to `SEC-024` — and
  the sentence directly below it already read «Wer nach den Regeln 1, 3 und 4
  baut» and «Für die Regeln 2 und 5–7 gilt das nicht». Four is the count of the
  rules the catalogue does *not* see; it had been stated as the number it covers.
  Corrected in `SKILL.md` and both READMEs. Cross-checked from the other side:
  the row for this skill in `mcp-audit-skill`'s README lists exactly three
  checks.

## [1.2.0] - 2026-08-02

Two documentation changes, no rule added, changed or removed — seven rules, as
in 1.1.0. Both are about the same thing seen from two sides: a fault that
produces no signal. Rule 6 names the variant that needs no network at all, a
test that establishes the very condition under which the fault cannot occur. The
introduction drops the assurance that a 421 gets noticed, because one layer up
it can arrive as an ordinary empty result.

### Changed

- **The introduction no longer promises that a 421 is noticed.** It distinguished
  this skill's silence from the one in `mcp-data-fidelity` — there a plausible
  but wrong answer, here no answer at all. One layer up the two classes
  converge: a caller that measures the 421 only by "no records came back" passes
  it on as an empty set, and then it *is* a plausible, substantively wrong
  answer after all. Measured case: a request with a foreign Host header returns
  HTTP 421 with the body `Invalid Host header`, and nobody upstream saw it as
  anything but zero hits.

  This sharpens the skill's own thesis rather than importing a neighbour's rule.
  The reason the transport path needs a test of its own was stated as "a stdio
  suite never touches it"; the stronger reason is that the failure can be
  swallowed above, so the transport test is the only place it reliably becomes
  visible. Counterpart to rule 3 in
  [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill)
  v1.2.0 and `FID-003` in `mcp-audit` v1.5.0, cited from this side. Two
  sentences, no new rule — seven rules, unchanged.

- **Rule 6 now names the mock as the same failure outside the transport.** The
  first of the three findings — a test that set the environment variable whose
  absence was the subject under test, and passed with the mutation applied —
  generalises beyond a network transport: a mock pins its own assumption, so a
  wrong assumption produces a test that confirms the fault instead of finding
  it. Counterpart to the same addition in
  [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill)
  rule 5, cited from the other side. Two sentences, no new rule.

## [1.1.1] - 2026-08-01

CI only. No rule, no pattern, no documentation changed — seven rules, as in
1.1.0. The version badge is simply no longer a figure that nothing checks.
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
