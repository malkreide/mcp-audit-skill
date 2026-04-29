# Changelog

Alle wesentlichen Änderungen am Skill und am Check-Katalog werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Versionierung: [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

Pilot-Audit-Findings, organische Erweiterungen aus Real-World-Anwendung. Geplante Themen:

- `reference/anti-patterns.md` mit wiederverwendbaren Code-Snippets aus wiederkehrenden Findings
- CI-Lint im Skill-Repo, der das Frontmatter aller Check-Files validiert
- Audit-Findings-Sub-DB unter dem Notion-Audit-Tracker

## [v0.5.0] — 2026-04-26

### Hinzugefügt — Anhang-Coverage (Architektur-Disziplin + Security-Verstärkung + Operative Disziplin)

Lücken-Analyse gegen `mcp-server-architecture-best-practice.pdf` zeigte, dass v0.4.0 etwa 65–70% des Anhang-Inhalts vollständig deckte. v0.5.0 schliesst die identifizierten Lücken mit 14 neuen Checks in drei Clustern.

**Cluster 1 — Architektur-Disziplin (5 Checks):**
- `ARCH-008` — Drei MCP-Primitive nutzen (Tools, Resources, Prompts)
- `ARCH-009` — Tool Annotations explizit (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`)
- `ARCH-010` — **Idempotency-Keys + Compensating Actions** (CRITICAL bei Write-Servern, schliesst die SOLID-Idempotency-Lücke)
- `ARCH-011` — Standardisierte Repo-Struktur (Sormena-Pattern)
- `ARCH-012` — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

**Cluster 2 — Security-Verstärkung (5 Checks):**
- `SEC-019` — **Lethal Trifecta vermeiden** (CRITICAL, Server-Separation Read vs Write/Send)
- `SEC-020` — **Command Injection Prevention** (CRITICAL, 43%-Lücke gemäss Equixly 2025)
- `SEC-021` — Egress-Allow-List auf Code- und Network-Layer
- `SEC-022` — Tool-Hash-Pinning + Namespace-Präfix gegen Rug Pull
- `SEC-023` — DLP-Scanning auf Tool-Outputs (ergänzt HITL-003 für Non-Sampling-Pfad)

**Cluster 3 — Operative Disziplin (4 Checks, neue Kategorie OPS):**
- `OBS-006` — OpenTelemetry Distributed Tracing pro Tool-Call
- `OPS-001` — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert
- `OPS-002` — Doku-Standard: bilingualer README, ASCII-Diagramm, Limits-Sektion
- `OPS-003` — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

### Status

Check-Katalog: **68 Checks**, alle 8 Kategorien.

- `ARCH`: 12 / 12 ✅
- `SDK`: 5 / 5 ✅
- `SEC`: 23 / 23 ✅
- `SCALE`: 6 / 6 ✅
- `OBS`: 6 / 6 ✅
- `HITL`: 5 / 5 ✅
- `CH`: 8 / 8 ✅
- `OPS`: 3 / 3 ✅ (neue Kategorie)

**Severity-Verteilung:**
- critical: 15 (22%)
- high: 31 (46%)
- medium: 22 (32%)

### Gap-Coverage gegen Anhang

Vollständige Abdeckung der drei Anhang-Sektionen:
- A (Architektur): A1, A2, A3, A4, A5, A6, A7, A8, A9 — alle abgedeckt
- B (Sicherheit): B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12 — alle abgedeckt
- C (Operative Praxis): C1, C2, C3, C4 — alle abgedeckt

Plus die SOLID-Eselsbrücke ist nun komplett: **S**andbox (SEC-007), **O**Auth (SEC-001/2/3), **L**east Privilege (SEC-003), **I**dempotency (ARCH-010), **D**efense-in-Depth (über alle Layer).

---

## [v0.4.0] — 2026-04-26

### Hinzugefügt — Claude-Code-Slash-Command-Integration

Der Audit-Workflow ist nun als Claude-Code-Slash-Command `/audit-mcp <repo>` ausführbar. Standard-Automatisierungstiefe: alle `automated`/`config_check`/`documentation_check`-Modi laufen automatisch, `code_review`/`runtime_test`-Modi werden als TODOs mit Such-Pattern in den Report geschrieben.

> **Erratum (nachträglich, 2026-04-29):** Im ursprünglichen v0.4.0-Eintrag wurde die Anzahl Checks fälschlich mit 53 angegeben — tatsächlicher Stand zum Release-Zeitpunkt war 54. Die Diskrepanz entstand durch einen Off-by-one-Zählfehler beim Übergang von v0.3.0 zu v0.4.0. v0.5.0 baut korrekt auf 54 + 14 = 68 Checks auf.

**Neue Files:**
- `.claude/commands/audit-mcp.md` — Slash-Command-Definition (orchestriert die 6 Schritte aus `SKILL.md`)
- `setup-slash-command.sh` — installiert den Symlink nach `~/.claude/commands/audit-mcp.md` für globale Verfügbarkeit

**Architektur-Entscheidungen:**
- File wohnt im Skill-Repo (versioniert mit Skill-Updates), wird via Symlink user-global verfügbar gemacht
- `allowed-tools` strikt limitiert auf `Bash(grep|find|curl|git|ls|cat|...)`, `Read`, `Write`, `Glob` — keine Tool-Surface jenseits der Audit-Operationen
- Profil-Load mit drei Fallback-Wegen: User-Conversation → Notion-Card-Copy-Paste → Repo-Inferenz (mit konservativen Defaults)
- Bei mehr als zwei geratenen Profil-Werten bricht der Command ab und fragt — falsches Profil = falscher Audit
- Nutzt ausschliesslich Bash-Snippets aus den Check-Files, kein erfundenes Pattern-Match
- Output-Verzeichnis pro Audit: `<repo>/audits/YYYY-MM-DD-<server-name>/` mit `audit-report.md`, `findings/`, `raw/`
- Bei wiederholtem Audit am gleichen Tag: `-vN`-Suffix statt Überschreiben

**Setup:**
```bash
git clone https://github.com/malkreide/mcp-audit-skill.git
cd mcp-audit-skill
./setup-slash-command.sh
```

Danach in jeder Claude-Code-Session: `/audit-mcp <repo-url-or-path>`.

---

## [v0.3.0] — 2026-04-26

### Hinzugefügt — SEC Edge-Cases (Final)

Elf SEC-Checks komplettieren die Security-Kategorie. Geordnet nach Portfolio-Relevanz für das Schulamt-Portfolio (Universal → Lokal → File → DNS → OAuth → Multi-Server).

**Cluster 1 — Universal (alle Server):**
- `SEC-018` — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)
- `SEC-013` — API-Key-Storage: Secret Manager statt Plain-Text Env-Vars

**Cluster 2 — Lokale stdio-Server:**
- `SEC-006` — stdio-Transport zwingend für lokale Server (Netzwerk-Isolation)
- `SEC-007` — Container-Sandboxing mit minimalen Privilegien
- `SEC-008` — Pre-Configuration Consent für Local-Server-Installation

**Cluster 3 — File-Tools:**
- `SEC-017` — Path-Traversal-Prevention (Allow-List + safe_resolve)

**Cluster 4 — DNS:**
- `SEC-005` — DNS-Rebinding-Prevention via DNS-Pinning (TOCTOU-Schutz)

**Cluster 5 — OAuth-Proxy:**
- `SEC-003` — Progressive Scope-Minimierung mit WWW-Authenticate-Challenges
- `SEC-011` — Cookie-Security: __Host-Prefix, Secure, HttpOnly, SameSite
- `SEC-012` — Clickjacking-Protection: X-Frame-Options + CSP frame-ancestors

**Cluster 6 — Multi-Server-Cluster:**
- `SEC-014` — Tool-Allow-Listing via MCP-Gateway-Pattern
- `SEC-015` — Pre-Flight Tool-Poisoning Detection

### Status

Check-Katalog: **53 von ~50 Checks** vollständig (Plan war ~50, finale Zählung +3 durch granularere Aufteilung mancher PDF-Themen). Alle sieben Kategorien komplett.

- `ARCH`: 7 / 7 ✅
- `SDK`: 5 / 5 ✅
- `SEC`: **18 / 18 ✅**
- `SCALE`: 6 / 6 ✅
- `OBS`: 5 / 5 ✅
- `HITL`: 5 / 5 ✅
- `CH`: 8 / 8 ✅

### v0.3 markiert das vollständige Skill

Der Check-Katalog ist nun produktiv einsatzbereit für alle Server-Profile im Schulamt-Portfolio. Künftige Erweiterungen kommen aus zwei Quellen:
1. Real-World-Findings beim Audit der 29 Server, die neue Pattern aufzeigen
2. PDF-Updates mit neuen Best Practices (z.B. neue Specs der MCP-Steering-Group)

---

## [v0.2.4] — 2026-04-26

### Hinzugefügt — HITL & Schweiz-Compliance Wave (Final)

Vier HITL-Checks und sieben CH-Checks. Komplettiert die Kategorien `HITL` und `CH`. Damit ist der Check-Katalog operativ einsatzbereit für das Schulamt-Portfolio.

**Human-in-the-Loop (4):**
- `HITL-001` — Sampling Request Review: User-UI vor LLM-Send
- `HITL-002` — Sampling Response Review: Output-Validation vor Server-Übergabe
- `HITL-003` — **Data Redaction**: PII-Filter vor LLM-Send (CRITICAL bei nicht-public + Sampling)
- `HITL-004` — Sequential Thinking Object-Sanitization gegen Key-Leaks

**Schweiz-Compliance (7):**
- `CH-002` — **DSG-konforme Personendaten-Verarbeitung** mit Rechtsgrundlage (CRITICAL bei PII)
- `CH-003` — Lehrpersonen-Einwilligung bei Volksschule-Daten (Auskunfts-/Berichtigungsrecht)
- `CH-004` — OGD-CH Lizenz-Compliance: CC BY 4.0 Attribution
- `CH-005` — ISDS Stadt Zürich Schutzbedarfsklasse-Mapping (3 Schutzziele)
- `CH-006` — Schulamt Klassifikationsschema (BUI/VERT/SVERT, Aggregations-Risiko)
- `CH-007` — Datenresidenz Backup-Region (Backups als gleichwertige Verarbeitung)
- `CH-008` — **EDÖB-Meldepflicht** bei Datenschutz-Verletzungen (CRITICAL, 72h-Frist)

### Status

Check-Katalog: **42 von ~50 Checks** vollständig. Alle sieben Kategorien mit operativ einsetzbarem Check-Set abgedeckt.

- `ARCH`: 7 / ~7 ✅ vollständig
- `SDK`: 5 / ~5 ✅ vollständig
- `SEC`: 6 / ~18 (kritische Subset komplett, Rest in Roadmap für v0.3)
- `SCALE`: 6 / ~6 ✅ vollständig
- `OBS`: 5 / ~5 ✅ vollständig
- `HITL`: 5 / ~5 ✅ vollständig
- `CH`: 8 / ~8 ✅ vollständig

### Verbleibend für v0.3

Nicht-kritische SEC-Checks (~11): SEC-003 (Scope-Minimierung), SEC-005 (DNS-Pinning), SEC-006/007/008 (Local-Server / Container-Sandbox / Pre-Config-Consent), SEC-011/012 (Cookie-Security / Clickjacking), SEC-013 (API-Key-Storage), SEC-014/015 (Tool-Allow-Listing / Tool-Poisoning), SEC-017 (Path-Traversal), SEC-018 (Input-Validation).

Diese Checks decken Edge-Cases ab, die im Schulamt-Portfolio aktuell noch nicht produktionsrelevant sind. Werden ergänzt, sobald Server in Production gehen, die OAuth-Proxy nutzen oder File-Tools exponieren.

---

## [v0.2.3] — 2026-04-26

### Hinzugefügt — Skalierung & Observability Wave

Fünf SCALE-Checks und vier OBS-Checks. Komplettiert die Kategorien `SCALE` und `OBS` aus dem PDF.

**Skalierung (5):**
- `SCALE-001` — Streamable HTTP statt stdio für Cloud-Deployments
- `SCALE-003` — Mcp-Session-Id Routing via Edge-LB (HAProxy Stick-Tables / NGINX Hash)
- `SCALE-004` — Containerization mit Multi-Stage-Builds (Image-Grösse + Non-Root-User)
- `SCALE-005` — MCP-Gateway für Enterprise (Anti-Shadow-MCP)
- `SCALE-006` — Resource-Limits per Container (Memory, CPU, FDs)

**Observability (4):**
- `OBS-002` — Mask Error Details (keine Stacktraces / SQL ans LLM)
- `OBS-003` — Structured Logging mit RFC 5424 Severity-Stufen
- `OBS-004` — **stderr für stdio-Server** (CRITICAL — stdout reserviert für Protocol)
- `OBS-005` — SIEM-Integration für Audit-Logs (Datadog EU / Splunk)

### Status

Check-Katalog: 31 von ~50 Checks vollständig. Verbleibend: ~10 Checks in v0.2.4 (HITL + CH).
- `ARCH`: 7 / ~7 ✅ vollständig
- `SDK`: 5 / ~5 ✅ vollständig
- `SEC`: 7 / ~18 (kritische Subset komplett)
- `SCALE`: 6 / ~6 ✅ vollständig
- `OBS`: 5 / ~5 ✅ vollständig
- `HITL`: 1 / ~4
- `CH`: 1 / ~7

---

## [v0.2.2] — 2026-04-26

### Hinzugefügt — Architektur & SDK Wave

Fünf Architektur-Checks und vier SDK-Checks. Komplettiert die Kategorien `ARCH` und `SDK` aus dem PDF.

**Architektur (5):**
- `ARCH-002` — Tool-Beschreibung mit Use-Case-Tags (`<use_case>`, `<important_notes>`)
- `ARCH-003` — «Not Found» Anti-Pattern: Fuzzy-Match + Suggestions statt leerer Antworten
- `ARCH-004` — Inversion of Control: Transport-agnostische Server-Logik (stdio + SSE identisch)
- `ARCH-006` — Tool-Budget: High-Level-Use-Cases statt API-Mapping 1:1
- `ARCH-007` — Capability-Aggregation: Composability intern, Atomarität extern

**SDK (4):**
- `SDK-001` — FastMCP Lifespan via `@asynccontextmanager` + AsyncExitStack
- `SDK-002` — Pydantic v2 / TypedDict / Dataclass als Tool-Returns
- `SDK-003` — Context Injection für Progress-Reports und Logging
- `SDK-004` — CORS `Mcp-Session-Id` Exposure bei HTTP/SSE-Deployments

### Status

Check-Katalog: 22 von ~50 Checks vollständig. Verbleibend: ~28 Checks in v0.2.3 + v0.2.4.
- `ARCH`: 7 / ~7 ✅ vollständig
- `SDK`: 5 / ~5 ✅ vollständig
- `SEC`: 7 / ~18 (kritische Subset komplett)
- `SCALE`: 1 / ~6
- `OBS`: 1 / ~5
- `HITL`: 1 / ~4
- `CH`: 1 / ~7

---

## [v0.2.1] — 2026-04-26

### Hinzugefügt — Critical Security Wave

Sechs kritische Security-Checks aus dem PDF-Anhang. Alle haben Severity `critical` und müssen vor Production-Release bestanden sein.

- `SEC-002` — Token Passthrough Prohibition (RFC 8707 Audience Validation)
- `SEC-004` — SSRF-Prevention: HTTPS-Enforcement + IP-Blocklisting (mit DNS-Rebinding-Schutz)
- `SEC-009` — Session-ID Cryptographic Binding an validierte user_id
- `SEC-010` — OAuth State Parameter: Single-Use, max 10min TTL (Redis GETDEL)
- `SEC-016` — 0.0.0.0-Binding-Prevention (NeighborJack-Schutz)
- `ARCH-005` — Keine Hardcoded Secrets (Pydantic SecretStr + Gitleaks/Trufflehog CI)

### Status

Check-Katalog: 13 von ~50 Checks vollständig (v0.1.0: 7 Sample + v0.2.1: 6 Critical). Verbleibend: ~37 Checks in v0.2.2 bis v0.2.4.

---

## [v0.1.0] — 2026-04-26

### Hinzugefügt — Initial Release

**Skill-Methodik:**
- `SKILL.md` mit 6-Schritte-Audit-Verfahren
- Profil-getriebene Applicability-Logik
- Severity-Disziplin: critical / high / medium / low
- Sieben Check-Kategorien: ARCH, SDK, SEC, SCALE, OBS, HITL, CH

**Templates:**
- `templates/finding.md` — Finding-Dokumentation
- `templates/audit-report.md` — Server-Gesamtreport

**Reference:**
- `reference/best-practices-summary.md` — komprimiertes PDF

**Sample-Checks (7 von ~50 geplant):**
- `ARCH-001` — Tool Naming Convention (medium, universal)
- `SDK-005` — TypeScript Strict Mode + Zod (high, TypeScript-only)
- `SEC-001` — Confused Deputy: Per-Client Consent Flow (critical, OAuth-Proxy)
- `SCALE-002` — Stateful Load Balancing für Streamable HTTP/SSE (high, HTTP/SSE)
- `OBS-001` — Protocol vs. Execution Errors (high, universal)
- `HITL-005` — Destructive Operation Confirmation (critical, write-capable)
- `CH-001` — DSG/EDÖB Datenresidenz Schweiz/EU (high, non-public-data)

### Bekannt unvollständig

Der Check-Katalog enthält in v0.1 nur 7 Sample-Checks zur Format-Validierung. Die verbleibenden ~43 Checks sind in `docs/roadmap.md` dokumentiert und werden in v0.2 ergänzt:

- ARCH: 6 weitere Checks (Inversion of Control, Tool-Beschreibungen, Tool-Budget, etc.)
- SDK: 4 weitere Checks (Lifespan-Management, Pydantic-Returns, Context-Injection, CORS)
- SEC: 17 weitere Checks (Token Passthrough, SSRF, Session-Hijacking, etc.)
- SCALE: 5 weitere Checks (Streamable HTTP, Container, MCP-Gateway, etc.)
- OBS: 4 weitere Checks (Mask-Error-Details, Structured Logging, SIEM, etc.)
- HITL: 4 weitere Checks (Sampling-Review, Data-Redaction, Sequential Thinking, etc.)
- CH: 7 weitere Checks (Personendaten-Verarbeitung, OGD-Lizenz, ISDS, etc.)

---

## Versions-Historie

Das Repository wurde mit **v0.5.0** publiziert. Frühere Versionen (v0.1.0 bis
v0.4.0) sind in diesem CHANGELOG dokumentiert, existieren aber nicht als
separate Git-Tags — sie repräsentieren Iterationsstände während der
initialen Skill-Entwicklung vor dem GitHub-Push.

[Unreleased]: https://github.com/malkreide/mcp-audit-skill/compare/v0.5.0...HEAD
[v0.5.0]: https://github.com/malkreide/mcp-audit-skill/releases/tag/v0.5.0
