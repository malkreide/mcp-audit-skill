# Best-Practices-Referenz (komprimiert)

Diese Datei kondensiert die Kernaussagen des Best-Practices-PDF («Best Practices und Standards für die Entwicklung von Model Context Protocol (MCP) Servern») auf einen schnell durchsuchbaren Index. Sie ersetzt nicht das PDF — bei Detailfragen bleibt das PDF die maßgebende Quelle.

**Quelle:** PDF-Anhang im Projekt, Stand 2026-04.
**Sprache:** Deutsch (Quelle), englische Fachbegriffe wo etabliert.

---

## Sec 1 — Architektur-Fundamente

### Zwei-Schichten-Architektur

| Schicht | Spec | Verantwortung |
|---|---|---|
| Data Layer | JSON-RPC 2.0 | Tools, Resources, Prompts, Lifecycle, Notifications |
| Transport Layer | stdio / Streamable HTTP / SSE | Verbindungsaufbau, Message Framing, Auth-Basis |

### Drei MCP-Primitive

- **Tools** — ausführbare Funktionen (Schreib-/Lesehandlungen)
- **Resources** — strukturierte Daten zum Lesen
- **Prompts** — vorgefertigte Konversations-Templates

---

## Sec 2 — Kognitive Ergonomie & Tool-Design

### Inversion of Control

Server-Logik **transport-agnostisch** halten. Capabilities und externe Konfiguration via Dependency Injection / Env-Vars. Niemals API-Keys hardcoden.

### Naming-Konventionen

- **Bevorzugt:** `camelCase` (LLMs parsen das am besten)
- **Akzeptabel:** `kebab-case`, `snake_case`
- **Verboten:** Spaces, dots (`get.X.Y`), Klammern, Sonderzeichen

### Tool-Beschreibungen

Kurz reicht nicht. Detaillierte, fast instruktionale Beschreibungen mit XML-Tags wie `<use_case>` und `<important_notes>`. Aliase und breite Kontexte angeben, damit das LLM den semantischen Bogen spannen kann.

### «Not Found»-Anti-Pattern

LLMs reagieren empfindlich auf negatives Framing. Statt `"not found"` → teilrelevante Daten oder Heuristiken. Ausnahme: hochsensible Daten.

### Tool-Budget verwalten

API-Endpunkte **nicht 1:1** als Tools mappen. Stattdessen: High-Level-Use-Cases als Makros (z.B. `fetchUserInvoices` statt `auth + getUserId + listInvoices + downloadPdf`). Reduziert Context Window Bloat und Token-Kosten.

---

## Sec 3 — Implementierungs-Standards (SDKs)

### Python (FastMCP)

- **Lifespan Management** via `@asynccontextmanager` und `lifespan`-Param der `FastMCP`-Instanz.
- **AsyncExitStack** für Multi-Server-Setups in einer ASGI-App.
- **Pydantic v2 / TypedDict / Dataclass** als Return-Typen für Tools — strukturiert, typisiert, automatisches Wrapping.
- **Context Injection:** Tool-Parameter `ctx: Context` für `ctx.report_progress()`, `ctx.info()`, `ctx.debug()`.
- **CORS bei HTTP/SSE:** Zwingend `Mcp-Session-Id` in `expose_headers=` der ASGI-CORS-Middleware.

### TypeScript (Node/Bun/Deno)

- **`strict: true`** in `tsconfig.json`. **`any` ist verboten**, `unknown` mit Type Guard verwenden.
- **Zod** als Goldstandard für `inputSchema` von Tools — Schema + Runtime-Validation.
- **Optional Chaining** (`?.`) und **Nullish Coalescing** (`??`) konsequent.
- Metadaten **explizit** im Tool-Deklarations-Objekt — keine JSDoc-Auto-Extraction.

---

## Sec 4 — Sicherheitsarchitektur

> Empirie 2025: 53% der OSS-MCP-Server nutzen langlebige Static API Keys statt OAuth. 0.0.0.0-Bindings ermöglichen NeighborJack-Angriffe. Auch in offiziellen Implementierungen: CVEs für Path Traversal und RCE.

### Confused Deputy (Sec 4.1)

MCP-Proxy mit statischer Client-ID + dynamischer Client-Registrierung → Angreifer kann Consent-Cookie eines legitimen Nutzers ausnutzen.

**Mitigation:**
- Per-Client Consent UI vor Upstream-OAuth
- Single-Use OAuth State Parameter (max 10min TTL)
- Cookies: `__Host-` Prefix, `Secure`, `HttpOnly`, `SameSite=Strict`
- Clickjacking-Schutz: `X-Frame-Options: DENY` oder CSP `frame-ancestors`

### Token Passthrough (Sec 4.2)

**Verboten:** Client-Tokens unvalidiert an Upstream weiterreichen. Bricht Audit-Trails, umgeht Rate-Limits, Vertrauensgrenzen.

**Mitigation:** RFC 8707 Audience-Validation. Nicht passende Tokens → HTTP 401.

### Scope Minimierung (Sec 4.3)

«Omnibus»-Scopes (`files:*`, `db:*`) verbieten. Progressive Least-Privilege:
- Initial: nur Read/Discovery (`mcp:tools-basic`)
- Privilegierte Operation → `WWW-Authenticate scope="..."` Challenge zur inkrementellen Rechteausweitung
- Client cached abgelehnte Scopes (Consent-Abandonment vermeiden)

### SSRF / DNS Rebinding (Sec 4.4)

Cloud-Metadata-Endpunkte (`169.254.169.254`) und private IPs als Risiko.

**Mitigation:**
- HTTPS-Enforcement in Produktion
- IP-Blocklisting via Egress-Proxy (z.B. Smokescreen) — nie String-Parser
- DNS-Resolution-Pinning (Schutz vor TOCTOU)

### Lokale Server (Sec 4.5)

Lokale MCP-Server haben User-Rechte → RCE-Risiko bei kompromittierten Binaries.

**Mitigation:**
- **stdio-Transport** zwingend für lokal (eliminiert Netzwerk)
- **Containerisierung:** Docker / chroot mit minimalen Privilegien
- **Pre-Configuration Consent:** ungekürzten Ausführungsbefehl anzeigen, gefährliche Pattern (`sudo`, `~/.ssh`) hervorheben

### Session Hijacking (Sec 4.6)

In statusbehafteten Setups mit Shared Queues: Angreifer rät Session-ID, injiziert bösartige Events.

**Mitigation:**
- Session-IDs via UUIDv4 oder kryptografisch sicheren RNG
- Session-Rotation, TTL
- **Binding:** `<user_id>:<session_id>` mit user_id aus validiertem OAuth-Token (nicht vom Client)

---

## Sec 5 — Skalierung & Transport

### Transport-Wahl

| Mode | Wann |
|---|---|
| **stdio** | Lokale Entwicklung, Single-User-Apps, Claude Desktop |
| **Streamable HTTP / SSE** | Cloud, Multi-User, verteilte Agenten |

WebSocket-Implementierungen sind veraltet — Streamable HTTP ist Standard 2026.

### Stateful Load Balancing

MCP-Sessions sind zustandsbehaftet → Verbindungs-Affinität nötig.

**Lösung A — Sticky Sessions:** Edge-LB (HAProxy) liest `Mcp-Session-Id`-Header, nutzt Stick Tables für Backend-Routing.

**Lösung B — Shared State (cloud-native):** Session-Manager mit Redis Pub/Sub oder Cloudflare Durable Objects. Pod-Failover ohne Session-Verlust.

### Containerization

- Multi-stage Docker Builds
- Minimale Base Images (`python:3.11-slim`, `node:alpine`)
- Build-Tools im Final-Image entfernen

### MCP Gateway (Anti-Shadow-MCP)

Zentrale Verteidigung gegen unautorisierte lokale Server-Nutzung. Gateway:
- Zentrale OAuth
- Tool-Allow-Lists pro Team
- Pre-Flight gegen Tool-Poisoning / Prompt Injection
- Konsolidiertes Audit-Logging

---

## Sec 6 — Error Handling & Observability

### Protocol vs. Execution Errors

| Typ | Wo | Format |
|---|---|---|
| **Protocol Error** | Routing, Schema-Mismatch | Standard JSON-RPC Error |
| **Execution Error** | Geschäftslogik (Rate-Limit, File-Not-Found) | Tool-Result mit `isError: true`, **niemals** als JSON-RPC-Error |

Sonst halluziniert das LLM «Verbindung kaputt» statt sich selbst zu korrigieren.

### Standardisierte Fehlercodes

| JSON-RPC | HTTP | Konstante |
|---|---|---|
| -32601 | 400 | INVALID_TOOL |
| -32602 | 400 | INVALID_PARAMS |
| -32001 | 403 | INSUFFICIENT_SCOPE |
| -32003 | 429 | RATE_LIMIT_EXCEEDED |
| -32004 | 403 | READ_ONLY_MODE |
| -32603 | 500 | EXECUTION_FAILED |

### Sensitive Detail Masking

Nie Stacktraces, SQL-Syntax oder Hardcoded-Credentials an LLM/User. FastMCP: `mask_error_details=True`.

### Logging

- 8 Severity-Stufen nach RFC 5424 (debug → emergency)
- Lokal: stderr (stdout ist für Protocol)
- Netzwerk: `notifications/message` Events
- Client kann via `logging/setLevel` dynamisch filtern

### SIEM-Integration

| Log-Typ | Inhalt |
|---|---|
| Operational | Performance, Resource-Access, Routine-Errors |
| Audit | Auth-Versuche, Token-Issuance, Scope-Erweiterungen, Tool-Reg-Änderungen |

Audit Logs **immer** mit User-IDs, Correlation-IDs, Client-Signaturen für Tool-Poisoning-Forensik.

---

## Sec 7 — Kognitive Muster & HITL

### Sampling-Protokoll

Server fordert LLM-Inferenz beim Client an (umgekehrte Richtung). Vorteil: Server muss keinen API-Key für OpenAI/Anthropic verwalten.

### Human-in-the-Loop

Pflicht-Checkpoints bei Sampling und destruktiven Tools:
1. **Request Review** — Nutzer sieht Prompt, kann modifizieren/ablehnen
2. **Response Review** — Nutzer sieht Generat, vor Server-Übergabe verifiziert
3. **Data Redaction** — PII filtern vor LLM-Send (Context Leakage Prevention)

### Sequential Thinking

«Thoughtboxes» strukturieren Lösungsfindung in adressierbare Schritte. Features:
- Dynamic Allocation (`nextThoughtNeeded`)
- Branching & Revisionen
- Addressability (jeder Schritt hat ID)
- **Sanitization** — Server-seitiger Filter für Private Keys / Env-Vars in Chain-of-Thought

---

## Mapping PDF-Sektion → Skill-Kategorie

| PDF | Skill-Kategorie | Typische Check-Anzahl |
|---|---|---|
| Sec 1 | (verteilt) | — |
| Sec 2 | `ARCH` | 6–8 |
| Sec 3 | `SDK` | 5–7 |
| Sec 4 | `SEC` | 15–20 |
| Sec 5 | `SCALE` | 5–7 |
| Sec 6 | `OBS` | 5–7 |
| Sec 7 | `HITL` | 4–5 |
| (Custom) | `CH` | 5–8 |

---

## Aktualisierungen & Versionierung

| Datum | Quelle | Aktion |
|---|---|---|
| 2026-04 | Initial-PDF | Katalog v0.1 erstellt |
| (folgend) | PDF-Updates | Neuer Check pro neuer Best Practice; CHANGELOG-Eintrag |

Bei Änderung der PDF-Sektion: alle korrespondierenden Checks neu evaluieren, ggf. Severity anpassen.
