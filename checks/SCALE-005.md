---
id: SCALE-005
title: "MCP-Gateway für Enterprise (Anti-Shadow-MCP)"
category: SCALE
severity: medium
applies_when: 'enterprise_context == true or stadt_zuerich_context == true'
pdf_ref: "Sec 5.3"
evidence_required: 2
---

# SCALE-005 — MCP-Gateway für Enterprise (Anti-Shadow-MCP)

## Description

In Organisationen mit vielen MCP-Servern entsteht «Shadow MCP»: Teams installieren lokale Server eigenmächtig, ohne zentralen Audit. Sicherheitsteams haben keine Sichtbarkeit auf Tools, die LLMs in der Organisation aufrufen. Bei Stadt Zürich / Schulamt heisst das: jeder Mitarbeiter könnte einen MCP-Server starten, der Schulamts-Daten an externe LLMs leakt — ohne dass IT/CISO es bemerkt.

MCP-Gateway-Pattern: zentrale Vermittlungsschicht, durch die alle MCP-Aufrufe laufen. Funktionen: Tool-Allow-Listing pro Team, zentrale OAuth-Authentifizierung, konsolidiertes Audit-Logging, Pre-Flight-Detection für Tool-Poisoning, Rate-Limiting. Bekannte Implementierungen 2026: LangGraph MCP Gateway, Pomerium, Self-Hosted Open-Source-Gateways.

Für Schulamt-Portfolio: aktuell `medium`, weil noch wenige Server in Production. Wird `high`, sobald > 5 Server gleichzeitig aktiv sind.

## Verification

### Modus 1: documentation_check (Architektur-Eintrag)

```bash
grep -rE 'gateway|proxy|allowlist' README.md docs/
find . -iname 'tool-allowlist*' -o -iname 'mcp-policy*'
```

**Pass-Pattern (im README):**

```markdown
## Deployment Architecture

This server is registered with the Stadt Zürich MCP Gateway at
`https://mcp-gateway.zh.ch`. Tool calls from internal LLM clients route
through the Gateway, which enforces:

- Tool allow-listing per team (Schulamt: tools `search*`, `getStats*`)
- OAuth authentication via SwitchAAI
- Audit logging to internal SIEM
- Rate limiting: 100 calls/minute per user
```

### Modus 2: config_check (Gateway-Routing aktiv)

```bash
# Direkter Server-Zugang vs. Gateway-only
grep -rE 'allow_direct_access|gateway_only|require_gateway' src/ config/
```

## Pass Criteria

- [ ] Bei `enterprise_context`: Gateway-Architektur ist im README dokumentiert
- [ ] Tool-Allow-List für den eigenen Server ist im Gateway konfiguriert
- [ ] Pre-Flight-Detection auf Tool-Definitionen aktiviert
- [ ] Audit-Logs fliessen ins zentrale SIEM
- [ ] Bei direkter Verbindung (nicht via Gateway): Begründung dokumentiert

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Direkter Server-Zugang ohne Gateway in Enterprise | Shadow-MCP-Risiko |
| Allow-List zu permissiv (`*`) | Anti-Shadow-MCP-Schutz wertlos |
| Audit-Logs nur lokal, kein SIEM-Export | Forensik bei Vorfall unmöglich |

## Remediation

Konkrete Schritte für Stadt Zürich Schulamt-Kontext:

1. KI-Fachgruppe zur Gateway-Beschaffung konsultieren (mögliche Bestandskomponenten der Stadtverwaltung wie SwitchAAI für OAuth)
2. Pilot: ein einzelner MCP-Server (z.B. `zh-education-mcp`) hinter Gateway-Endpoint
3. Allow-Liste für Schulamt-Use-Cases definieren
4. Audit-Logs an Stadtverwaltungs-SIEM (siehe OBS-005)
5. Rollout über Portfolio: alle Server hinter Gateway

## Effort

L — 1–4 Wochen für Pilot + Rollout.

## References

- PDF Sec 5.3
- [Pomerium MCP Gateway](https://www.pomerium.com/docs/mcp/)
- [LangGraph MCP Gateway](https://langchain-ai.github.io/langgraph/)
