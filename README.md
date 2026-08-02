# mcp-audit-skill

> Claude skill for systematic audits of MCP servers against a curated corpus of best-practice standards. **95 checks**, 12 categories, with a Swiss compliance layer for public administration and a data-fidelity layer for data-source servers.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Checks: 95](https://img.shields.io/badge/Checks-95-blue.svg)](./checks/)
[![Coverage: A1–A9, B1–B12, C1–C4](https://img.shields.io/badge/Best--Practice%20Coverage-A1%E2%80%93A9%2C%20B1%E2%80%93B12%2C%20C1%E2%80%93C4-success)](./CHANGELOG.md)
[![MCP Spec: 2025-06-18](https://img.shields.io/badge/MCP%20Spec-2025--06--18-orange)](https://modelcontextprotocol.io/specification/)

🇩🇪 [Deutsche Version](README.de.md)

---

**What it is:** a Claude skill that audits MCP servers systematically against published best practices. Every check references its source, has clear pass criteria, a remediation path and an effort indicator.

**What it is not:** not an automated code scanner, not a vulnerability tool, not a compliance stamp. The skill makes the methodology reproducible — architectural judgement stays human.

## Architecture model

The checks follow the five-layer security model established as the consensus architecture in the MCP security community. Each layer validates on its own — none trusts the one above it blindly.

```text
┌────────────────────────────────────────────────────────┐
│  LLM host (Claude, ChatGPT, Cursor)                    │
│  Untrusted: may carry prompt injections                │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  MCP gateway / policy layer                            │
│  Rate limit · audit log · DLP · tool allow-list        │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  Authentication & authorisation                        │
│  OAuth 2.1 + PKCE · resource indicators · scopes       │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  MCP server logic                                      │
│  Input validation · schema · idempotency · sandbox     │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  Data source / backend                                 │
│  Read-only service account · least privilege           │
└────────────────────────────────────────────────────────┘
```

## SOLID for MCP servers

The five principles the whole check catalogue is aligned to:

| Principle | Meaning | Key checks |
|---|---|---|
| **S**andbox | Every server in Docker / WASM with an egress filter | [`SEC-007`](./checks/SEC-007.md), [`SEC-021`](./checks/SEC-021.md) |
| **O**Auth 2.1 | OAuth instead of API keys, with PKCE and resource indicators | [`SEC-001`](./checks/SEC-001.md), [`SEC-002`](./checks/SEC-002.md), [`SEC-003`](./checks/SEC-003.md) |
| **L**east privilege | Keep service-account rights minimal | [`SEC-003`](./checks/SEC-003.md), [`SEC-013`](./checks/SEC-013.md) |
| **I**dempotency | Idempotency keys plus compensating actions on every write | [`ARCH-010`](./checks/ARCH-010.md) |
| **D**efense-in-depth | Gateway + auth + schema + sandbox + DLP, stacked | [`SCALE-005`](./checks/SCALE-005.md), [`SEC-018`](./checks/SEC-018.md), [`SEC-023`](./checks/SEC-023.md) |

Cover all five and you are protected against roughly 80% of the attack classes observed today. The remaining ~20% — primarily prompt injection at the tool-description level — is structurally unsolved and needs organisational controls (human-in-the-loop, threat detection, audit reviews).

## Anchor demo

> «Does my `parlament-mcp` server satisfy all 23 security checks that apply to a phase-1 read-only connection to City of Zurich administrative data?»

With the slash command installed:

```
> /audit-mcp .
```

Output: profile-driven selection of the ~30 applicable checks out of 95, automated verification of every `automated` / `config_check` / `documentation_check` mode, findings stubs for `code_review` / `runtime_test` modes, and a full audit report from the template — all under `<repo>/audits/YYYY-MM-DD-<server-name>/`.

## Standards provenance

The 95 checks come from two curated best-practice documents plus five layers of our own (Swiss compliance, data fidelity, identity, upstream drift, dependency resolution), in auditable form. Every check carries a `pdf_ref` reference to its source in the frontmatter.

| Source | Content | Derived checks |
|---|---|---|
| **Main catalogue** «MCP Server-Entwicklung — Best Practices & Standards» | Architecture, SDK patterns, security, scaling, observability, human-in-the-loop | 54 Checks (v0.1–v0.4) |
| **Architecture appendix** «Architektur und Sicherheit von MCP-Servern» | Section A (architecture, A1–A9), section B (security, B1–B12), section C (operational practice, C1–C4); closes the lethal-trifecta, idempotency and egress-control gaps among others | 14 Checks (v0.5) |
| **Swiss compliance layer** | revDSG, EDÖB notification duty, ISDS City of Zurich, OGD licence compliance, data-protection requirements specific to compulsory schooling | 8 Checks (`CH-*`) |
| **Data-fidelity layer** | Scope defaults, recall against ground truth, empty result ≠ absence, query syntax. Derived from a real portfolio incident ([termdat-mcp#11](https://github.com/malkreide/termdat-mcp/issues/11)) | 5 Checks (`FID-*`) |
| **Identity layer** | User agent, `__version__`, manifest version, documented version — what a server claims to be from the outside; plus whether the published artefact still starts at all. Derived from a portfolio sweep across 30 servers and from two dead releases on the index | 7 Checks (`IDENT-*`) |
| **Upstream-drift layer** | The contract with the source changes and nothing notices: retired endpoints, fallbacks that swap the dataset, assertions the failure case satisfies too — and prose in the repo that contradicts the code. Derived from a real portfolio incident ([meteoswiss-mcp#33](https://github.com/malkreide/meteoswiss-mcp/issues/33), #35, #37) and from a CHANGELOG that called merged work pending | 6 Checks (`DRIFT-*`) |
| **Dependency layer** | A range without an upper bound hands the choice of major version to whoever publishes next: the published artefact changes without anyone publishing it. Derived from `mcp` 2.0.0 removing `mcp.server.fastmcp` on 2026-07-28 and killing two releases that had nothing wrong with them | 1 Check (`DEP-*`) |
| **Architecture** | Tool design, annotations, idempotency and repo structure from main catalogue section 2 and appendix A; plus the retry policy toward the source (`ARCH-014`) — our own finding: of ten portfolio servers eight retry, and none reads `Retry-After` or spreads its backoff | 14 Checks (`ARCH-*`) |
| **Observability** | Logging, error classification, SIEM and tracing from main catalogue section 6 and appendix B10; plus error diagnosability (`OBS-007`) — our own finding: an error masked correctly on the way out, with nothing behind the mask on the way in ([swiss-efv-mcp#16](https://github.com/malkreide/swiss-efv-mcp/pull/16)) | 7 Checks (`OBS-*`) |
| **Operational practice** | Test strategy, documentation standard and phase architecture from appendix C; plus audit honesty (`OPS-004`) and pipeline honesty (`OPS-005`) — both our own findings: a report that closed an unexplained remainder with a guess ([termdat-mcp#11](https://github.com/malkreide/termdat-mcp/issues/11)), and a test suite no workflow ever ran ([mcp-continuous-auditor#29](https://github.com/malkreide/mcp-continuous-auditor/pull/29)) | 5 Checks (`OPS-*`) |

## Quickstart

### Prerequisites — cross-platform

| Operating system | Requirement |
|---|---|
| Linux / macOS | Python 3.11+, Bash, `git`, `yq` |
| Windows (Git Bash) | Python 3.11+ with `PYTHONUTF8=1`, Git Bash, `git`, `yq` |

**Windows users:** set the environment variable `PYTHONUTF8=1` in your profile (or per session), otherwise Python crashes when writing umlauts or emoji:

```powershell
# PowerShell
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")

# Git Bash
echo 'export PYTHONUTF8=1' >> ~/.bashrc
```

Path helpers for the skill scripts live in [`tools/paths.sh`](tools/paths.sh) (Bash) and [`tools/path_utils.py`](tools/path_utils.py) (Python). They convert between `/c/Users/foo` (Git Bash) and `C:\Users\foo` (Windows-native, which the Read/Edit/Write tools need).

### As a Claude Code slash command (`/audit-mcp`)

The skill ships a slash command that runs the six-step workflow as a Claude Code workflow — profile load, applicability filter, automated check execution, findings generation and report creation in one pass.

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git
cd mcp-audit-skill
./setup-slash-command.sh
```

The setup script symlinks `.claude/commands/audit-mcp.md` into `~/.claude/commands/`, so that `/audit-mcp` is available globally in every Claude Code session.

Usage:

```bash
# In an MCP server repo or any directory
claude
```

```
> /audit-mcp .
> /audit-mcp /path/to/server-repo
> /audit-mcp https://github.com/malkreide/zh-education-mcp
```

Output lands in `<repo>/audits/YYYY-MM-DD-<server-name>/` with:

- `audit-report.md` — full report from the template
- `findings/<check-id>-*.md` — one finding per fail/partial check
- `raw/<check-id>.txt` — raw output of the bash commands, for the audit trail

Automation depth is **standard**: all `automated` / `config_check` / `documentation_check` modes run automatically, while `code_review` / `runtime_test` modes are written into the report as TODOs with a search pattern (no hallucinated pattern matches).

### Portfolio batch audit (`audit-portfolio.sh`)

To audit several MCP servers in one run, use the top-level script `audit-portfolio.sh`. It reads your `portfolio.yaml` (server list with a profile per server), clones each repo, invokes `claude -p` with the `/audit-mcp` slash command non-interactively, and aggregates the findings into a `portfolio-summary.md`.

```bash
cp portfolio.example.yaml portfolio.yaml
$EDITOR portfolio.yaml          # adapt your server list
./audit-portfolio.sh --dry-run  # verify the plan, no claude call
./audit-portfolio.sh            # real run, all servers sequentially
./audit-portfolio.sh zh-education-mcp foo-mcp   # subset
./audit-portfolio.sh --force    # re-audit servers already done today
```

`portfolio.yaml` is `.gitignore`d — do not commit your server list by accident. Dependencies: `yq` (Mike Farah's Go yq, or kislyuk's Python yq plus `jq`), `git`, and the `claude` CLI. Output lands in `portfolio-logs/<date>/`.

### Notion sync (`audit-notion-sync.py`) — bidirectional tracker integration

If your audit tracker lives in Notion, use `audit-notion-sync.py` for bidirectional synchronisation: pull generates `portfolio.yaml` from the tracker, push writes the findings count and audit status back after each run. Standard library only, no `pip install` needed.

**One-time setup:**

1. In Notion: tracker → `•••` → **Connections** → **+ Add connections** → select your internal integration
2. Add a new property to the tracker: name `Org-Kontext`, type `Multi-select`, options `Stadt Zürich`, `Schulamt`, `Volksschule`, `Enterprise` — then tick what applies per server
3. Token into your shell RC (never commit it):
   ```bash
   export NOTION_TOKEN="ntn_..."
   ```
4. Verify:
   ```bash
   python3 audit-notion-sync.py health
   ```

**Usage:**

```bash
# Pull only (tracker → portfolio.yaml)
python3 audit-notion-sync.py pull --force
./audit-portfolio.sh

# Or combined: pull, audit, push in one run
./audit-portfolio.sh --from-notion --sync-back
```

By default the pull filters to servers with `Audit-Status` ∈ {`Triagiert`, `In Audit`} — `--all` ignores the filter. The push sets `Findings` (number) and `Audit-Status` (to `Findings dokumentiert`), and appends a note with the report path. Formula fields (`Risiko-Score`, `Reife-Score`, `Prio`) are left untouched.

The DB ID defaults to `a2736a65-677d-4cf3-9f94-e874f74a1975` (City of Zurich Schulamt MCP Audit Tracker); the `NOTION_AUDIT_DB_ID` environment variable overrides it.

### As a Claude.ai skill (manual)

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git ~/skills/mcp-audit
```

Then, in Claude.ai: `Verwende mcp-audit-Skill für <server-name>`. The workflow then runs interactively, without slash-command automation.

## Check catalogue at a glance

| Code | Area | Source | Count | Severity profile |
|---|---|---|---:|---|
| `ARCH` | Tool design, annotations, idempotency, upstream retry policy, repo structure, spec versioning | Main catalogue sec 2 + appendix A + custom | 14 | 2 critical · 5 high · 7 medium |
| `SDK` | FastMCP, TypeScript, Zod, lifecycle | Main catalogue sec 3 | 6 | — · 4 high · 2 medium |
| `SEC` | Security (largest category) | Main catalogue sec 4 + appendix B | 24 | 8 critical · 13 high · 3 medium |
| `SCALE` | Transport, load balancing, containers, gateway | Main catalogue sec 5 | 7 | — · 3 high · 4 medium |
| `OBS` | Logging, errors, SIEM, OpenTelemetry | Main catalogue sec 6 + appendix B10 | 7 | 1 critical · 2 high · 4 medium |
| `HITL` | Sampling, human-in-the-loop | Main catalogue sec 7 | 5 | 2 critical · 2 high · 1 medium |
| `CH` | DSG/EDÖB, ISDS City of Zurich, compulsory schooling | Custom | 8 | 2 critical · 4 high · 2 medium |
| `OPS` | Test strategy, documentation standard, phase architecture, audit honesty, pipeline honesty | Appendix C + custom | 5 | — · 4 high · 1 medium |
| `FID` | Data fidelity: scope defaults, recall, empty results, query syntax | Custom | 5 | 1 critical · 2 high · 2 medium |
| `IDENT` | Identity: user agent, `__version__`, manifest, documented version, release gap, artefact health | Custom | 7 | — · 3 high · 3 medium · 1 low |
| `DRIFT` | Upstream contract and repo prose: endpoint drift, fallback semantics, test quality, CHANGELOG vs code | Custom | 6 | — · 3 high · 3 medium |
| `DEP` | Resolution space of the published artefact: upper bounds, major upgrades | Custom | 1 | — · 1 high |
| **Total** | | | **95** | **16 critical · 46 high · 32 medium · 1 low** |

## Severity levels

| Level | Meaning | Consequence |
|---|---|---|
| `critical` | Security hole / compliance breach | Blocks production |
| `high` | Architectural defect with significant risk | Fix in the current sprint |
| `medium` | Best-practice violation | Plan for the next sprint |
| `low` | Polish, optimisation | Backlog |

## Adoption levels

Severity says **how bad** a violation is. The adoption level says **whether the catalogue may already hold the portfolio to it**. Without that second axis, every new check hits 30+ servers as a red pipeline on the day it merges — which is how checks get reverted instead of adopted.

| Level | Meaning | Consequence |
|---|---|---|
| `enforced` | The catalogue holds the portfolio to it | A `fail` on `critical`/`high` blocks production readiness |
| `advisory` | The check reports but does not yet judge | The finding is created, counted and carried at full severity — but does not block |

The field is optional; when absent, `enforced` applies. Of 95 checks exactly two are `advisory`: `ARCH-014` and `OPS-005`. `DEP-001`, `DRIFT-006` and `OBS-007` took the same path and have since been promoted to `enforced` — the bridge is meant to carry a handful of new checks, not to fill up.

**Advisory hides nothing.** Only the veto is dropped. An advisory finding at blocking severity is still named explicitly even when the verdict is green, so that a later promotion is a decision rather than a surprise.

The catalogue is authoritative, not the results file — hence `--checks-dir`:

```bash
python tools/aggregate_results.py aggregate verification-results.json \
    --checks-dir checks/ --out summary.json
```

## Audit workflow (short form)

1. **Load the profile** — server properties from the Notion audit tracker, or inferred from the repo
2. **Load the catalogue** — parse all 95 checks
3. **Applicability filter** — select only the checks that fit (a stdio-only server skips the OAuth checks, for instance)
4. **Run the checks** — automated (grep, AST, config scan) or as a code-review TODO per check
5. **Document findings** — `templates/finding.md`
6. **Audit report** — `templates/audit-report.md`

For details see [`SKILL.md`](./SKILL.md).

## Positioning against related tools

| Tool | Category | Focus |
|---|---|---|
| `apisec-inc/mcp-audit` | Code scanner | Local MCP configs (secrets, shadow APIs, AI-BOM, SARIF) |
| `ModelContextProtocol-Security/mcpserver-audit` (CSA) | Tutorial tool | Teaches CWE/AIVSS methodology using example servers |
| `qianniuspace/mcp-security-audit` | Dependency scanner | npm vulnerability scan for MCP packages |
| **`malkreide/mcp-audit-skill`** | **Audit framework** | **Systematic review against a curated best-practice corpus + Swiss compliance** |

Usable side by side — none of these replaces the others.

## Related repositories

### The skill family

Five skills, one build. Each answers a different question, in the order they come up — this one comes last:

| Skill | Role | Its rules in this catalogue |
|---|---|---|
| [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) | Generic build guidance — Anthropic's skill | — |
| [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | The procedure *before* the build | supplies the ground truth `FID-002` measures against |
| [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill) | Does it return what the source actually holds? | [`FID-001`–`FID-005`](./checks/) |
| [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-transport-hardening-skill) | Does it come up, and does it turn away the right callers? | [`SDK-006`](./checks/SDK-006.md), [`ARCH-013`](./checks/ARCH-013.md), [`SEC-024`](./checks/SEC-024.md) |
| **`mcp-audit-skill`** | **This skill:** auditing *after* the build | — |

Two of the transport-hardening rules have no counterpart here: the one about a
bind reaching the app, and the three on how a control is proven (negative tests,
mutation testing, harness traps). The first is a genuine gap; the second is a
scope boundary — this catalogue checks whether a control exists, not whether its
proof holds.

### Portfolio and trackers

- [`malkreide` MCP server portfolio](https://github.com/malkreide?tab=repositories) — the servers this skill audits
- Notion **MCP Audit Tracker** — running status of all server audits (internal)
- Notion **MCP Server Portfolio** — master inventory of all servers (internal)

## Status

**Version:** v1.5.0 — silence is not an acquittal. CI on Ubuntu + Windows × py3.11 + py3.13. See [CHANGELOG.md](./CHANGELOG.md) for the full release history.

**Completeness:**
- ✅ Methodology (`SKILL.md`) and templates (finding, audit report)
- ✅ Reference summary
- ✅ Check catalogue: **95 checks, all 12 categories complete**
- ✅ Slash command for Claude Code (`/audit-mcp <repo>`)
- ✅ Portfolio batch audit (`audit-portfolio.sh` for multi-server runs)
- ✅ Inventory gate (`./audit-portfolio.sh --verify-inventory`) — finds servers missing from `portfolio.yaml`, including nested ones
- ✅ Notion sync (`audit-notion-sync.py` for bidirectional tracker integration)
- ✅ Full coverage of both standards sources (main catalogue + architecture appendix)

Future additions come from real-world findings during portfolio audits, MCP spec updates, or new compliance requirements (EU AI Act, Swiss AI legislation). For the version roadmap see [`docs/roadmap.md`](./docs/roadmap.md).

## Contributing

Corrections are welcome: a check whose pass criterion does not separate cleanly in practice, a source that has moved on, a remediation path that leads nowhere.

New checks are held to the anatomy of the existing ones: a named source, a pass criterion two auditors answer the same way, a remediation path and an effort indicator. A check without a source is an opinion — and a pass criterion open to interpretation makes the catalogue irreproducible, which is the very thing it exists to prevent.

Particularly welcome are compliance layers for other jurisdictions (GDPR specifics, cantonal data-protection law, sector-specific requirements), and real-world findings from portfolio audits that sharpen an existing check.

Please open an issue before a large pull request, so the shape can be settled first.

### Local setup

The Python helpers are linted and formatted with [Ruff](https://docs.astral.sh/ruff/). One-off step per clone:

```
pip install pre-commit
pre-commit install
```

The hooks in `.pre-commit-config.yaml` mirror the `lint` workflow, so what passes locally passes in CI. Two details worth knowing:

- The hook runs Ruff at the version pinned in `.pre-commit-config.yaml`, in its own isolated environment — not whatever Ruff you happen to have installed. That pin and the `ruff==…` pin in `.github/workflows/lint.yml` must stay in sync; `tools/check_ruff_pin.py` enforces this, in the hook and in CI.
- `ruff format` rewrites your files and then fails the commit. Stage the reformatted files and commit again; `ruff check` only reports.

Run everything over the whole tree without committing:

```bash
pre-commit run --all-files
pytest tests/ -q
```

## Security

This repository ships a methodology, check definitions and helper scripts — no running server, no installable package. Three things matter in operation:

**The audit output contains other people's code.** `audit-portfolio.sh` clones the repos in your server list and invokes `claude -p` on them non-interactively; `audits/` and `portfolio-logs/` collect the raw output of the commands that ran. That is the audit trail and exactly the point — but it can contain internal paths, hostnames or configuration excerpts of the audited servers. Review a report before publishing it.

**Two files never belong in a commit.** `portfolio.yaml` is `.gitignore`d because a server list is an inventory. The `NOTION_TOKEN` belongs in your shell RC, not in the repo — `audit-notion-sync.py` reads it from the environment only.

**A green audit is not a security guarantee.** The catalogue checks against published best practices, not against your threat model, and it is not a vulnerability scanner. The remaining class — prompt injection at the tool-description level — is structurally unsolved and needs organisational controls, as described under SOLID above.

Found an error in a check, or a pass criterion that separates wrongly? Please open an issue.

## License

MIT — see [`LICENSE`](./LICENSE).

## Context

Built as part of the Swiss Public Data MCP portfolio. Freely usable by other public administrations, research institutions or individuals who want to audit MCP servers systematically.

## Author

[Hayal Oezkan](https://github.com/malkreide)
