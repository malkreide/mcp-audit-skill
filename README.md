# mcp-audit-skill

> Claude-Skill für systematische Audits von MCP-Servern gegen einen kuratierten Best-Practice-Standards-Korpus. **68 Checks**, 8 Kategorien, mit Schweiz-Compliance-Layer für die öffentliche Verwaltung.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Checks: 68](https://img.shields.io/badge/Checks-68-blue.svg)](./checks/)
[![Coverage: A1–A9, B1–B12, C1–C4](https://img.shields.io/badge/Best--Practice%20Coverage-A1%E2%80%93A9%2C%20B1%E2%80%93B12%2C%20C1%E2%80%93C4-success)](./CHANGELOG.md)
[![MCP Spec: 2025-06-18](https://img.shields.io/badge/MCP%20Spec-2025--06--18-orange)](https://modelcontextprotocol.io/specification/)

---

**Was es ist:** Ein Claude-Skill, der MCP-Server systematisch gegen veröffentlichte Best Practices auditiert. Jeder Check referenziert seine Quelle, hat klare Pass-Kriterien, einen Remediation-Pfad und einen Aufwands-Indikator.

**Was es nicht ist:** Kein automatischer Code-Scanner, kein Vulnerability-Tool, kein Compliance-Stempel. Der Skill macht die Methodik reproduzierbar — Architektur-Urteile bleiben menschlich.

## Architektur-Modell

Die Checks orientieren sich am Fünf-Schichten-Sicherheitsmodell, das in der MCP-Sicherheits-Community als Konsens-Architektur etabliert ist. Jede Schicht prüft eigenständig — keine vertraut der nächsthöheren blind.

```text
┌────────────────────────────────────────────────────────┐
│  LLM-Host (Claude, ChatGPT, Cursor)                    │
│  Untrusted: kann Prompt-Injektionen enthalten          │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  MCP-Gateway / Policy Layer                            │
│  Rate-Limit · Audit-Log · DLP · Tool-Allowlist         │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  Authentifizierung & Autorisierung                     │
│  OAuth 2.1 + PKCE · Resource Indicators · Scopes       │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  MCP-Server-Logik                                      │
│  Input-Validierung · Schema · Idempotenz · Sandbox     │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  Datenquelle / Backend                                 │
│  Read-only Service-Account · Least Privilege           │
└────────────────────────────────────────────────────────┘
```

## SOLID für MCP-Server

Die fünf Prinzipien, an denen sich der gesamte Check-Katalog ausrichtet:

| Prinzip | Bedeutung | Schlüssel-Checks |
|---|---|---|
| **S**andbox | Jeder Server in Docker / WASM mit Egress-Filter | [`SEC-007`](./checks/SEC-007.md), [`SEC-021`](./checks/SEC-021.md) |
| **O**Auth 2.1 | OAuth statt API-Keys, mit PKCE und Resource Indicators | [`SEC-001`](./checks/SEC-001.md), [`SEC-002`](./checks/SEC-002.md), [`SEC-003`](./checks/SEC-003.md) |
| **L**east Privilege | Service-Account-Rechte minimal halten | [`SEC-003`](./checks/SEC-003.md), [`SEC-013`](./checks/SEC-013.md) |
| **I**dempotency | Idempotency-Keys + Compensating Actions bei jedem Write | [`ARCH-010`](./checks/ARCH-010.md) |
| **D**efense-in-Depth | Gateway + Auth + Schema + Sandbox + DLP gestapelt | [`SCALE-005`](./checks/SCALE-005.md), [`SEC-018`](./checks/SEC-018.md), [`SEC-023`](./checks/SEC-023.md) |

Wer alle fünf abdeckt, ist gegen ~80% der heute beobachteten Angriffsklassen geschützt. Die übrigen ~20% — primär Prompt-Injection auf Tool-Description-Ebene — sind strukturell ungelöst und brauchen organisatorische Kontrollen (Human-in-the-Loop, Threat Detection, Audit-Reviews).

## Anchor-Demo

> «Erfüllt mein `parlament-mcp`-Server alle 23 Security-Checks für eine Phase-1-Read-only-Anbindung an Stadt-Zürich-Verwaltungsdaten?»

Mit installiertem Slash-Command:

```
> /audit-mcp .
```

Output: Profil-getriebene Auswahl der ~30 anwendbaren Checks aus 68, automatisierte Verifikation aller `automated`/`config_check`/`documentation_check`-Modi, Findings-Stubs für `code_review`/`runtime_test`-Modi, vollständiger Audit-Report nach Template — alles in `<repo>/audits/YYYY-MM-DD-<server-name>/`.

## Standards-Provenance

Die 68 Checks sind systematische Übersetzungen aus zwei kuratierten Best-Practice-Dokumenten in auditierbare Form. Jeder Check trägt im Frontmatter eine `pdf_ref`-Referenz auf seine Quelle.

| Quelle | Inhalt | Abgeleitete Checks |
|---|---|---|
| **Hauptkatalog** «MCP Server-Entwicklung — Best Practices & Standards» | Architektur, SDK-Patterns, Security, Skalierung, Observability, Human-in-the-Loop | 54 Checks (v0.1–v0.4) |
| **Architektur-Anhang** «Architektur und Sicherheit von MCP-Servern» | Sektion A (Architektur, A1–A9), Sektion B (Sicherheit, B1–B12), Sektion C (Operative Praxis, C1–C4); schliesst u.a. Lethal-Trifecta-, Idempotency- und Egress-Control-Lücken | 14 Checks (v0.5) |
| **Schweiz-Compliance-Layer** | revDSG, EDÖB-Meldepflicht, ISDS Stadt Zürich, OGD-Lizenz-Compliance, Volksschule-spezifische Datenschutz-Anforderungen | 8 Checks (`CH-*`) |

## Schnellstart

### Als Claude-Code-Slash-Command (`/audit-mcp`)

Der Skill bringt einen Slash-Command mit, der den 6-Schritte-Workflow als Claude-Code-Workflow ausführt — Profil-Load, Applicability-Filter, automatisierte Check-Ausführung, Findings-Generierung und Report-Erstellung in einem Lauf.

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git
cd mcp-audit-skill
./setup-slash-command.sh
```

Das Setup-Script symlinkt `.claude/commands/audit-mcp.md` nach `~/.claude/commands/`, damit `/audit-mcp` global in jeder Claude-Code-Session verfügbar ist.

Verwendung:

```bash
# In einem MCP-Server-Repo oder beliebigen Verzeichnis
claude
```

```
> /audit-mcp .
> /audit-mcp /pfad/zum/server-repo
> /audit-mcp https://github.com/malkreide/zh-education-mcp
```

Output landet in `<repo>/audits/YYYY-MM-DD-<server-name>/` mit:

- `audit-report.md` — Gesamtreport nach Template
- `findings/<check-id>-*.md` — pro Fail/Partial-Check ein Finding
- `raw/<check-id>.txt` — Roh-Output der Bash-Befehle für Audit-Trail

Automatisierungstiefe ist **Standard**: alle `automated`/`config_check`/`documentation_check`-Modi laufen automatisch, `code_review`/`runtime_test`-Modi werden als TODO mit Such-Pattern in den Report geschrieben (kein Pattern-Match-Halluzinieren).

### Als Claude.ai-Skill (manuell)

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git ~/skills/mcp-audit
```

Dann in Claude.ai: `Verwende mcp-audit-Skill für <server-name>`. Der Workflow läuft dann interaktiv ohne Slash-Command-Automatisierung.

## Check-Katalog im Überblick

| Code | Bereich | Quelle | Anzahl | Severity-Profil |
|---|---|---|---:|---|
| `ARCH` | Tool-Design, Annotations, Idempotency, Repo-Struktur, Spec-Versionierung | Hauptkatalog Sec 2 + Anhang A | 12 | 1 critical · 7 high · 4 medium |
| `SDK` | FastMCP, TypeScript, Zod, Lifecycle | Hauptkatalog Sec 3 | 5 | — · 3 high · 2 medium |
| `SEC` | Security (grösste Kategorie) | Hauptkatalog Sec 4 + Anhang B | 23 | 14 critical · 8 high · 1 medium |
| `SCALE` | Transport, Load Balancing, Container, Gateway | Hauptkatalog Sec 5 | 6 | — · 3 high · 3 medium |
| `OBS` | Logging, Errors, SIEM, OpenTelemetry | Hauptkatalog Sec 6 + Anhang B10 | 6 | 1 critical · 1 high · 4 medium |
| `HITL` | Sampling, Human-in-the-Loop | Hauptkatalog Sec 7 | 5 | 1 critical · 4 high · — |
| `CH` | DSG/EDÖB, ISDS Stadt Zürich, Volksschule | Custom | 8 | 3 critical · 4 high · 1 medium |
| `OPS` | Test-Strategie, Doku-Standard, Phasenarchitektur | Anhang C | 3 | — · 2 high · 1 medium |
| **Total** | | | **68** | **15 critical · 31 high · 22 medium** |

## Severity-Stufen

| Stufe | Bedeutung | Konsequenz |
|---|---|---|
| `critical` | Sicherheitslücke / Compliance-Bruch | Blockiert Produktion |
| `high` | Architektureller Mangel mit signifikantem Risiko | Im laufenden Sprint fixen |
| `medium` | Best-Practice-Verletzung | Im nächsten Sprint planen |
| `low` | Polish, Optimierung | Backlog |

## Audit-Workflow (Kurzform)

1. **Profil laden** — Server-Eigenschaften aus Notion-Audit-Tracker oder via Inferenz aus dem Repo
2. **Katalog laden** — alle 68 Checks parsen
3. **Applicability-Filter** — nur passende Checks selektieren (z.B. stdio-only-Server überspringt OAuth-Checks)
4. **Check-Ausführung** — automatisiert (grep, AST, Config-Scan) oder als Code-Review-TODO pro Check
5. **Findings dokumentieren** — `templates/finding.md`
6. **Audit-Report** — `templates/audit-report.md`

Details siehe [`SKILL.md`](./SKILL.md).

## Positionierung gegenüber verwandten Tools

| Tool | Kategorie | Fokus |
|---|---|---|
| `apisec-inc/mcp-audit` | Code-Scanner | Lokale MCP-Configs (Secrets, Shadow-APIs, AI-BOM, SARIF) |
| `ModelContextProtocol-Security/mcpserver-audit` (CSA) | Tutorial-Tool | Lehrt CWE/AIVSS-Methodik anhand von Beispiel-Servern |
| `qianniuspace/mcp-security-audit` | Dependency-Scanner | npm-Vulnerability-Scan für MCP-Pakete |
| **`malkreide/mcp-audit-skill`** | **Audit-Framework** | **Systematische Prüfung gegen kuratierten Best-Practice-Korpus + CH-Compliance** |

Komplementär nutzbar — keiner der Genannten ersetzt die anderen.

## Verwandte Repos

- [`malkreide` MCP-Server-Portfolio](https://github.com/malkreide?tab=repositories) — die Server, gegen die dieses Skill auditiert wird
- Notion **MCP Audit Tracker** — laufender Status aller Server-Audits (intern)
- Notion **MCP Server Portfolio** — Master-Inventar aller Server (intern)

## Status

**Version:** v0.5.0 (vollständige Anhang-Coverage)

**Vollständigkeit:**
- ✅ Methodik (`SKILL.md`) und Templates (Finding, Audit-Report)
- ✅ Reference-Summary
- ✅ Check-Katalog: **68 Checks, alle 8 Kategorien vollständig**
- ✅ Slash-Command für Claude Code
- ✅ Vollständige Abdeckung beider Standards-Quellen (Hauptkatalog + Architektur-Anhang)

Künftige Erweiterungen kommen aus Real-World-Findings beim Portfolio-Audit, MCP-Spec-Updates oder neuen Compliance-Anforderungen (EU AI Act, Schweizer KI-Gesetz). Versions-Roadmap siehe [`docs/roadmap.md`](./docs/roadmap.md).

## Lizenz

MIT — siehe [`LICENSE`](./LICENSE).

## Kontext

Entwickelt im Rahmen des Swiss Public Data MCP Portfolio. Frei verwendbar von anderen Verwaltungen, Forschungsinstituten oder Privatpersonen, die MCP-Server systematisch auditieren wollen.

Pull Requests willkommen — insbesondere für ergänzende Compliance-Layer anderer Jurisdiktionen (DSGVO-Spezifika, kantonale Datenschutzgesetze, sektorspezifische Vorgaben).

---

**Autor:** [Hayal Oezkan](https://github.com/malkreide)
