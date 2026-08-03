# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2026-08-03

Sechs Regeln, unverändert — dieses Release ändert nichts an dem, was der Skill
lehrt. Es ändert, wohin er zeigt: Die Zuordnung Regel → Audit-Check stand als
Bereichsangabe da und war für drei von sechs Regeln falsch. Wer nach einem
Finding hierher kam, um die Behebung zu finden, landete beim falschen Check —
der teuerste Ort für eine Ungenauigkeit, weil er genau dann gelesen wird, wenn
jemand etwas reparieren will.

### Changed

- **Die Regel-zu-Check-Zuordnung ist eine Tabelle statt einer Bereichsangabe,
  geprüft gegen `mcp-audit` v1.7.0.** Es hiess: «Die Regeln 1–5 erscheinen dort
  als Checks `FID-001`–`FID-005`». Zwei aufsteigende Bereiche nebeneinander
  lesen sich als eins zu eins, und so ist die Zuordnung nicht: Regel 2 ist
  `FID-004`, nicht `FID-002`; die Regeln 3 und 4 teilen sich `FID-003`, weil der
  Check beide Hälften trägt — den fehlenden nächsten Schritt und die
  vorformulierte Ausrede; und Regel 5 braucht zwei Checks, `FID-005` für die
  Syntax und `FID-002` für den Recall.

  Wer die alte Zeile beim Beheben eines Findings gelesen hat, landete für drei
  von sechs Regeln beim falschen Check. Die neue Tabelle steht in `SKILL.md`
  neben der Kettentabelle, an derselben Stelle wie im Schwester-Skill
  `mcp-transport-hardening`, und nennt den Katalogstand, gegen den sie geprüft
  wurde.

  Am Ergebnis für Regel 6 ändert das nichts: Ein `FID-006` existiert nicht, und
  kein anderer Check des Katalogs fragt, ob eine Strukturabweichung upstream im
  Fehlerkanal endet statt in einer leeren Liste. Das steht jetzt als eigene
  Zeile da statt als Nachsatz.

## [1.3.0] - 2026-08-02

Six rules, unchanged — nothing in this release touches what the skill teaches.
What changes is where the family is named and how reliably the figures about it
hold. The related-repositories table becomes the MCP quality chain, five
repositories along the lifecycle with a shared GitHub topic, and the same table
now stands in `SKILL.md` rather than only in the READMEs — that is the file the
model actually receives.

Three figures were wrong and are corrected. Two of them had been wrong since the
sixth rule was added: the guiding question and rule 4 still spoke of five. The
CI counts headings against the README list items and does not read prose, which
is exactly how a number survives three releases.

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

- **`SKILL.md` still said «fünf Regeln» in two places.** The guiding question in
  the introduction and the opening line of rule 4 both carried the count from
  before rule 6 existed. Headings, both READMEs, the CHANGELOG and the CI counter
  all say six — the CI counts `## Regel N` headings against the list items in the
  READMEs and does not read prose, which is why this survived three releases.
  Exactly the drift this repository documents as a hazard: the probe skill
  described this one as "five rules" for two weeks after the sixth was added.

- **The table in `SKILL.md` was still the old five-skill list.** The READMEs
  became the quality chain — five repositories along the lifecycle, with
  `mcp-continuous-auditor` in and `mcp-builder` beside it — and the table the
  model actually reads kept naming the previous set. The CI guard added with the
  chain only reads the READMEs, so nothing caught it. `SKILL.md` now carries the
  same five in the same order, with the stage column, and keeps the two
  detail lines that belong to this skill (the probe's section numbers, the
  rule-to-`FID` mapping).

- **The related-skills row for `mcp-audit` claimed more than it delivers.** It
  read «dieselben Regeln als Checks `FID-001` bis `FID-005`», which reads as if
  all rules had a check. Rules 1–5 do; rule 6 has none. Both READMEs already
  stated it precisely — the table in `SKILL.md` now does too.

## [1.2.0] - 2026-08-02

Two boundaries, both drawn from an incident in a neighbouring skill rather than
from this one. Still six rules — what changes is that two of them now say where
they stop. Rule 3 no longer lets a rejected request pass as an empty set, and
rule 5 names the variant of its own failure that needs no mock at all.

### Changed

- **Rule 3 now draws the line against transport and authorization failures.** The
  rule listed four causes for zero hits, all of them query-level — absent term,
  too narrow a query, restricted scope, wrong syntax. A rejected request is none
  of them: measured case, a request carrying a foreign Host header comes back as
  HTTP 421 with the body `Invalid Host header`, and a layer that only asks "any
  records?" passes that through as an empty set. The hint it then attaches — try
  a wildcard, widen the fields — points away from the actual fix, so a
  configuration error undercuts the very rule that exists to prevent guessing.
  Rule 6 already made this distinction for schema drift, but a request turned away
  at the transport never reaches the parsing layer. One paragraph and one
  checklist item in `SKILL.md`, one sentence on the rule-3 line in both READMEs,
  and a `search_or_raise` block in `reference/patterns.py` that names the
  `except httpx.HTTPError: entries = []` clause as the bug it is. No new rule.

- **Rule 5 now names the mock-free variant of the same failure.** A regression
  test in `mcp-transport-hardening` set the environment variable whose *absence*
  was the actual subject under test, so it passed with a deliberately introduced
  fault in place. Independent confirmation from a different domain — transport
  security rather than data fidelity — of what rule 5 already said about mocks:
  a test that establishes the condition under which the fault cannot occur
  checks nothing. Two sentences, no new rule.

## [1.1.0] - 2026-08-01

Documentation and guards. No rule added, changed or removed — six rules, as in
1.0.0. What changes is that the skill names its place in the family, and that two
figures nothing used to check now have something behind them: the reference file
can no longer drift from the rules it claims to cover, and the version badge can
no longer drift from this file.
### Added

- **The related-skills tables now name all five skills in one order** — builder,
  probe, fidelity, transport-hardening, audit — in `SKILL.md` and both READMEs, so
  the family reads the same way from every repository in it. The new
  [`mcp-transport-hardening`](https://github.com/malkreide/mcp-transport-hardening-skill)
  sits *next to* this skill rather than under it: this one asks whether the answer
  contains what the source holds, that one whether an answer arrives at all. Same
  silent class, one layer down.

  `mcp-builder` is described as Anthropic's without a licence claim:
  `anthropics/skills` carries no LICENSE file and the API reports none, so stating
  one would be a guess in a public README. `termdat-mcp` moved out of the table
  into a sentence below it — it is the server the rules came from, not a skill of
  the family, and in a table of roles it read as if it were.

- Contributing section in both READMEs. It states the bar a new rule has to
  clear: the incident it came from, a counter-example pair, and its Nachweis.
  The skill's own subject applies to the proposal — evidence that comes only from
  a mock is not yet evidence.

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

- **CI now checks `reference/patterns.py` for content, not just syntax.** Until
  now it was verified to exist and to compile; its two claims — the number word
  in the module docstring and that every rule actually appears — were guarded by
  nothing. Both happened to be correct, which is the least reliable reason for a
  value to be right: `mcp-data-source-probe-skill` described this skill as "five
  rules" for two weeks after the sixth was added, for exactly that reason.

  The rule-count step now covers the file as well: the docstring word against the
  count in `SKILL.md`, and the set of rules mentioned (`Rule 1`, `Rules 4 + 5` —
  ranges expanded) against the set that exists. A rule without a pattern is a rule
  nobody can copy, so a gap fails the build.

  Verified against mutations rather than a green run: a wrong docstring word, a
  reworded anchor phrase, and a rule with every mention removed each fail with a
  message naming the problem.

## [1.0.0] - 2026-08-01

First standalone release. The skill was previously distributed as
`companion/mcp-data-fidelity/` inside
[`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill);
this repository makes it the canonical home. The skill content is unchanged from
that copy — packaging only.

### Added

- **Rule 1 — send scope parameters explicitly, never inherit them.** An omitted
  optional filter frequently means an arbitrary slice rather than "unrestricted".
  The fact lives only in the spec's parameter description — not in the response
  schema, not in the documentation example, and not visible from a working call.
  With the table of the usual suspects (CKAN `rows`, WFS `maxFeatures`, SPARQL
  named graphs, Elasticsearch `size`, GraphQL `first`, TERMDAT
  `ClassificationIds`) and the two-call recall delta that proves it.
- **Rule 2 — send parameter groups in full.** Members of a group that are not
  sent keep their server-side default, so the argument can widen but never
  narrow — a no-op that looks like control.
- **Rule 3 — an empty result carries a next step.** Zero hits are ambiguous
  between absent term, too narrow a query, restricted scope, and wrong syntax.
  The `hint` belongs in the tool result, not in the README, because the README is
  not handed to the model.
- **Rule 4 — the tool description is a hallucination surface.** The
  counter-intuitive one: a phrasing that explains an empty result causes
  confabulation more reliably than no phrasing at all. A caveat must ask for a
  retry, never license a conclusion.
- **Rule 5 — query syntax in the description, recall in the tests.** Query
  language plus matching granularity, since whole-word indexes make German
  compounds unfindable from their parts. Recall guarded by live floors rather
  than exact counts, because a test that cries wolf gets switched off.
- **Rule 6 — confirm the response shape before counting it.** Rules 1–5 cover
  what the server *sends* and what it *tells* the model; rule 6 covers what it
  *reads*. `payload.get("servers", [])` turns an upstream shape change into a
  valid-looking empty result — the same confabulation surface as rule 3, one
  layer down. A schema mismatch belongs in the error channel.
- **`reference/patterns.py`** — copy-paste FastMCP / httpx / pydantic v2
  patterns for all six rules, including the `rows_of()` guard, which deliberately
  checks only the envelope and the fields the caller actually reads rather than
  validating a full schema.
- **Release checklist** for a data-querying tool, in `SKILL.md`.
- Bilingual README (EN/DE) with a Security section stating the two deliberate
  limits: the best-effort scope widening in rule 1, which narrows recall rather
  than failing the call when the vocabulary endpoint is unreachable, and the
  `rows_of()` guard in rule 6, which validates the envelope and the fields
  actually read rather than the full schema.

### Context

Rules 1–5 come from a single real incident:
[`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). The
server sent `ClassificationIds` only when the caller supplied them; the upstream
API restricts an ID-less search to one of 23 classifications. Searching for
"Quellensteuer" returned nothing despite several matching entries — past 33 green
offline tests and a passed 68-check audit.

Rule 6 comes from a second case: an MCP Registry query returned nothing for a
while because the fields sit under `servers[].server.*` and the client looked one
level up. Syntactically fine, semantically blind.
