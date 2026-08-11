# Entwurf: README für ein Hub-Repo `mcp-quality-chain`

Dieser Entwurf liegt hier, weil das Hub-Repo noch nicht existiert. Ein Repo
anzulegen und öffentlich zu stellen ist eine Entscheidung, die einem Menschen
gehört — der Text ist fertig, das Anlegen nicht automatisiert.

**Ist das Hub-Repo nötig?** Nein. Die Topic-Seite
<https://github.com/topics/mcp-quality-chain> listet die beiden Repos, sobald
das Topic gesetzt ist, und GitHub pflegt sie von selbst. Das Hub-Repo lohnt
sich dann, wenn die Kette einen Einstieg mit *Reihenfolge* braucht — eine
Topic-Seite sortiert nach Sternen, nicht nach Lebenszyklus.

**Wenn es angelegt wird**, danach in `docs/quality-chain.json` die Zeile
`"homepage"` von der Topic-Seite auf `https://github.com/malkreide/mcp-quality-chain`
umstellen und die beiden Repos entsprechend nachziehen. Der Guard
(`tools/check_quality_chain.py`) meldet die Abweichung, bis das geschehen ist —
das ist beabsichtigt.

Vorgeschlagene Repo-Metadaten:

- **Description:** `Five repositories, one lifecycle — building MCP servers that do not fail silently`
- **Topics:** `mcp-quality-chain`, `mcp`, `model-context-protocol`, `claude-skill`, `anthropic`
- **Homepage:** `https://github.com/topics/mcp-quality-chain`

---

Ab hier der Text für `README.md` des Hub-Repos.

---

# MCP Quality Chain

> Five repositories, one lifecycle: how to build an MCP server that does not
> fail silently — and how to notice when it starts to.

🇩🇪 [Deutsche Version](README.de.md)

## What this is

Five repositories that were written in the order the problems appeared, each
answering a different question about the same server. They are usable
separately; together they cover the path from "is this data source any good?"
to "does the server still work three weeks after the last merge?".

The connective tissue is the shared GitHub topic
[`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain).

| Stage | Repository | Question it answers |
|---|---|---|
| before the build | [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-audit-skill/tree/main/skills/mcp-data-source-probe) | Is the source usable, and what does it hold? |
| in the build | [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-audit-skill/tree/main/skills/mcp-data-fidelity) | Does it return what the source actually holds? |
| in the build | [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-audit-skill/tree/main/skills/mcp-transport-hardening) | Does it come up, turn away the right callers, and stay stateless? |
| after the build | [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Does it hold up against the catalogue? |
| in operation | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Does it still hold up tomorrow? |

Alongside, not part of the chain:
[`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder)
— Anthropic's generic build guidance, complemented rather than replaced. It is
someone else's repository and cannot carry the topic.

## The thread running through all five

Every one of these came out of a failure that produced **no signal**. That is
the reason they belong together, and it is more specific than "MCP tooling":

- A server searched one 23rd of its database for weeks. HTTP 200, well-formed
  JSON, 33 green tests. Found by a user with the official web UI open beside it
  → `mcp-data-fidelity-skill`.
- A server answered every request under its real hostname with HTTP 421. Green
  unit tests, clean linter — the transport path is what a stdio test suite never
  touches → `mcp-transport-hardening-skill`.
- A package shipped an import error to every fresh install for three days with
  `main` already fixed, because CI tests the branch and not the artifact
  → `mcp-continuous-auditor`.

None of these is a crash. Each is a system reporting success while being wrong,
which is why they need deliberate instrumentation rather than better tests of
the usual kind.

## Where to start

- **Building a new server?** Start at
  [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-audit-skill/tree/main/skills/mcp-data-source-probe)
  and work down the table.
- **Server exists and you want to know where it stands?** Start at
  [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) — 95 checks
  in 12 categories, each with a source, pass criteria and a remediation path.
- **Server returns too little and you don't know why?**
  [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-audit-skill/tree/main/skills/mcp-data-fidelity),
  rule 1.
- **Server answers 421 or won't start in deployment?**
  [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-audit-skill/tree/main/skills/mcp-transport-hardening),
  rules 2 and 3.

## The portfolio these came from

All five were written while building and maintaining the
[Swiss Public Data MCP](https://github.com/malkreide/swiss-public-data-mcp)
portfolio — 40+ MCP servers for Swiss public and open data. The findings are
real ones from that portfolio, and each rule names the incident it came from.

The servers themselves carry the topic
[`swiss-public-data-mcp`](https://github.com/topics/swiss-public-data-mcp); the
five repositories here carry `mcp-quality-chain`. Only `mcp-audit-skill` carries
both, because it is the one whose catalogue includes a Swiss compliance layer.

## License

MIT — see each repository for its own copy.

## Author

[Hayal Oezkan](https://github.com/malkreide)
