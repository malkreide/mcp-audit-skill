# Changelog

Alle wesentlichen Änderungen am Skill und am Check-Katalog werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Versionierung: [Semantic Versioning](https://semver.org/lang/de/).

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

## [Geplant für v0.2.0]

- Vollständiger Check-Katalog (~50 Checks)
- Slash-Command-Integration für Claude Code (`/audit-mcp <repo>`)
- Automated Check-Runner Script (Python) für statische Checks
- CI-Workflow im Skill-Repo: Lint von Check-Markdown auf Schema-Konformität
