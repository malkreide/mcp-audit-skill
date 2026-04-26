# Roadmap — Verbleibende Checks für v0.2

Stand: v0.1.0 (2026-04-26) liefert 7 Sample-Checks, einer pro Kategorie. Diese Roadmap listet die ~43 verbleibenden Checks aus dem PDF-Anhang sowie zusätzliche CH-Compliance-Checks.

## Format-Validierung

Bevor v0.2 startet, sollte der Format-Standard durch Anwendung der 7 Sample-Checks auf 1-2 echte Server validiert werden. Falls das Format Anpassungen braucht (z.B. zusätzliches Feld in Frontmatter, andere Verifikations-Sektion), wird das vor v0.2 reflektiert.

---

## ARCH — Tool-Design (6 weitere)

| ID | Titel | Severity | Applies When | PDF |
|---|---|---|---|---|
| ARCH-002 | Tool-Beschreibung mit Use-Case-Tags | medium | always | Sec 2.2 |
| ARCH-003 | "Not Found" Anti-Pattern: Heuristiken statt leerer Antworten | medium | always | Sec 2.2 |
| ARCH-004 | Inversion of Control: Transport-agnostische Server-Logik | high | always | Sec 2.1 |
| ARCH-005 | Keine Hardcoded Secrets: Env-Vars / Secret Manager only | critical | always | Sec 2.1 |
| ARCH-006 | Tool-Budget: High-Level-Use-Cases statt API-Mapping 1:1 | high | always | Sec 2.3 |
| ARCH-007 | Capability-Aggregation: ein fetchUserInvoices statt vier Einzel-Tools | medium | always | Sec 2.3 |

## SDK — SDK-Standards (4 weitere)

| ID | Titel | Severity | Applies When | PDF |
|---|---|---|---|---|
| SDK-001 | FastMCP Lifespan via @asynccontextmanager | high | sdk_language == "Python" | Sec 3.1 |
| SDK-002 | Pydantic v2 / TypedDict / Dataclass als Tool-Returns | medium | sdk_language == "Python" | Sec 3.1 |
| SDK-003 | Context Injection für Progress Reports und Logging | medium | sdk_language == "Python" | Sec 3.1 |
| SDK-004 | CORS Mcp-Session-Id Exposure bei HTTP/SSE | high | transport != "stdio-only" and sdk_language == "Python" | Sec 3.1 |

## SEC — Security (17 weitere)

| ID | Titel | Severity | Applies When | PDF |
|---|---|---|---|---|
| SEC-002 | Token Passthrough verboten: RFC 8707 Audience-Validation | critical | auth_model == "OAuth-Proxy" | Sec 4.2 |
| SEC-003 | Progressive Scope-Minimierung: Least-Privilege-Modell | high | auth_model != "none" | Sec 4.3 |
| SEC-004 | SSRF-Prevention: HTTPS-Enforcement + IP-Blocklisting | critical | transport != "stdio-only" | Sec 4.4 |
| SEC-005 | DNS-Rebinding-Prevention: DNS-Pinning gegen TOCTOU | high | transport != "stdio-only" | Sec 4.4 |
| SEC-006 | Lokaler Server: stdio-Transport zwingend (Netzwerk-Isolation) | high | deployment.includes("local-stdio") | Sec 4.5 |
| SEC-007 | Container-Sandboxing: Docker / chroot mit minimalen Privilegien | high | deployment.includes("local-stdio") or deployment.includes("Railway") or deployment.includes("Render") | Sec 4.5 |
| SEC-008 | Pre-Configuration Consent für Local-Server-Installation | medium | deployment.includes("local-stdio") | Sec 4.5 |
| SEC-009 | Session-ID Cryptographic Binding: user_id:session_id | critical | transport != "stdio-only" | Sec 4.6 |
| SEC-010 | OAuth State Parameter: Single-Use, max 10min TTL | critical | auth_model == "OAuth-Proxy" | Sec 4.1 |
| SEC-011 | Cookie-Security: __Host-, Secure, HttpOnly, SameSite | high | auth_model == "OAuth-Proxy" | Sec 4.1 |
| SEC-012 | Clickjacking-Protection: X-Frame-Options / CSP frame-ancestors | high | auth_model == "OAuth-Proxy" | Sec 4.1 |
| SEC-013 | API-Key-Storage: Secret Manager statt Plain-Text Env-Vars | high | auth_model == "API-Key" | Sec 4 (allg.) |
| SEC-014 | Tool-Allow-Listing via MCP-Gateway-Pattern | medium | deployment != "local-stdio" | Sec 5.3 |
| SEC-015 | Pre-Flight Tool-Poisoning Detection | medium | deployment != "local-stdio" | Sec 5.3 |
| SEC-016 | 0.0.0.0-Binding-Prevention (NeighborJack) | critical | transport != "stdio-only" | Sec 4 (Empirie) |
| SEC-017 | Path-Traversal-Prevention bei File-Tools | high | tools_include_filesystem | Sec 4 (CVE-Hist.) |
| SEC-018 | Input-Validation an Boundaries (Zod / Pydantic strict) | high | always | Sec 3 / Sec 4 |

## SCALE — Skalierung (5 weitere)

| ID | Titel | Severity | Applies When | PDF |
|---|---|---|---|---|
| SCALE-001 | Streamable HTTP statt stdio für Cloud-Deployments | high | deployment.includes("Railway") or deployment.includes("Render") or deployment.includes("andere") | Sec 5.1 |
| SCALE-003 | Mcp-Session-Id Routing: HAProxy Stick-Tables | high | transport != "stdio-only" | Sec 5.2 |
| SCALE-004 | Containerization: Docker mit Multi-Stage-Builds | medium | deployment != "local-stdio" | Sec 5.3 |
| SCALE-005 | MCP-Gateway für Enterprise: Anti-Shadow-MCP | medium | enterprise_context | Sec 5.3 |
| SCALE-006 | Resource-Limits per Container (memory, CPU, file-descriptors) | medium | deployment != "local-stdio" | Sec 5.3 |

## OBS — Observability (4 weitere)

| ID | Titel | Severity | Applies When | PDF |
|---|---|---|---|---|
| OBS-002 | Mask Error Details: keine Stacktraces / SQL ans LLM | high | always | Sec 6.2 |
| OBS-003 | Structured Logging RFC 5424: 8 Severity-Stufen | medium | always | Sec 6.3 |
| OBS-004 | stderr für Local-stdio: stdout reserviert für Protocol | critical | deployment.includes("local-stdio") | Sec 6.3 |
| OBS-005 | SIEM-Integration: Audit-Logs nach Datadog/Splunk | medium | deployment != "local-stdio" and data_class != "Public Open Data" | Sec 6.3 |

## HITL — Human-in-the-Loop (4 weitere)

| ID | Titel | Severity | Applies When | PDF |
|---|---|---|---|---|
| HITL-001 | Sampling Request Review: UI vor LLM-Send | high | uses_sampling | Sec 7.2 |
| HITL-002 | Sampling Response Review: Verifikation vor Server-Übergabe | high | uses_sampling | Sec 7.2 |
| HITL-003 | Data Redaction: PII-Filter vor LLM-Send | critical | data_class != "Public Open Data" and uses_sampling | Sec 7.2 |
| HITL-004 | Sequential Thinking Object-Sanitization gegen Key-Leaks | medium | uses_sequential_thinking | Sec 7.3 |

## CH — Schweiz-Compliance (7 weitere)

| ID | Titel | Severity | Applies When | Quelle |
|---|---|---|---|---|
| CH-002 | DSG-konforme Personendaten-Verarbeitung mit Rechtsgrundlage | critical | data_class == "PII" | revDSG Art. 31 |
| CH-003 | Lehrpersonen-Einwilligung bei Volksschule-Daten | high | volksschule_context and data_class == "PII" | DSG + Schulgesetz |
| CH-004 | OGD-CH Lizenz-Compliance: CC BY 4.0 Attribution | medium | data_source.is_swiss_open_data | OGD-CH-Richtlinien |
| CH-005 | ISDS Stadt Zürich Schutzbedarfsklasse-Mapping | high | stadt_zuerich_context | ISDS-Richtlinie |
| CH-006 | Schulamt Klassifikationsschema: BUI/Vertraulich/Streng-Vertraulich | high | schulamt_context | Stadt-ZH-Klassifikation |
| CH-007 | Datenresidenz Backup-Region | medium | data_class != "Public Open Data" | revDSG Art. 16 |
| CH-008 | EDÖB-Meldepflicht bei Datenschutz-Verletzungen | critical | data_class != "Public Open Data" | revDSG Art. 24 |

---

## Neue Profil-Felder für v0.2

Einige der oben gelisteten Checks brauchen Profil-Felder, die im aktuellen Audit Tracker noch nicht existieren. Diese werden bei Bedarf in v0.2 ergänzt:

| Feld | Typ | Werte | Beispiel-Checks |
|---|---|---|---|
| `sdk_language` | Select | Python / TypeScript / Go / Rust | SDK-001, SDK-005 |
| `tools_include_filesystem` | Checkbox | bool | SEC-017 |
| `uses_sampling` | Checkbox | bool | HITL-001, HITL-002 |
| `uses_sequential_thinking` | Checkbox | bool | HITL-004 |
| `enterprise_context` | Checkbox | bool | SCALE-005 |
| `volksschule_context` | Checkbox | bool | CH-003 |
| `stadt_zuerich_context` | Checkbox | bool | CH-005 |
| `schulamt_context` | Checkbox | bool | CH-006 |
| `data_source.is_swiss_open_data` | Checkbox | bool | CH-004 |

---

## Reihenfolge der Implementierung in v0.2

Empfohlene Reihenfolge nach Priorisierung Schulamt-Portfolio:

**Phase v0.2.1 — Critical Security (Schwerpunkt):**
1. SEC-002 (Token Passthrough)
2. SEC-004 (SSRF)
3. SEC-009 (Session-Hijacking)
4. SEC-010 (OAuth State)
5. SEC-016 (0.0.0.0-Binding)
6. ARCH-005 (Hardcoded Secrets)

**Phase v0.2.2 — Architektur & SDK:**
- alle ARCH-Checks
- alle SDK-Checks

**Phase v0.2.3 — Skalierung & Observability:**
- alle SCALE-Checks
- alle OBS-Checks

**Phase v0.2.4 — HITL & CH:**
- alle HITL-Checks
- alle CH-Checks (besonders kritisch sobald erste Verwaltungsdaten-Server kommen)

---

## Bei v0.2-Implementation berücksichtigen

- Jeder Check sollte mit einem konkreten Beispiel aus dem Portfolio illustriert werden, falls möglich
- Bei Pattern-Wiederholung über Server: Anti-Pattern als wiederverwendbares Snippet in `reference/anti-patterns.md`
- CI-Lint im Skill-Repo: prüft Frontmatter-Schema, dass jede `.md`-Datei in `checks/` valide ist
