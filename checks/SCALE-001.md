---
id: SCALE-001
title: "Streamable HTTP statt stdio für Cloud-Deployments"
category: SCALE
severity: high
applies_when: 'deployment.includes("Railway") or deployment.includes("Render") or deployment.includes("andere")'
pdf_ref: "Sec 5.1"
evidence_required: 2
---

# SCALE-001 — Streamable HTTP statt stdio für Cloud-Deployments

## Description

stdio-Transport ist für lokale Single-User-Sessions konzipiert: ein Subprozess, eine Stdin/Stdout-Pipe, ein Client. Cloud-Deployments mit Multi-User-Zugriff können stdio nicht sinnvoll bedienen — der TCP-Bruch killt die Pipe, kein Failover möglich. Streamable HTTP / SSE sind die Cloud-Standards 2026; sie unterstützen Reconnect via Event-IDs, Multi-User, Standard-HTTP-Infrastruktur. WebSocket-Implementierungen sind veraltet.

Symptom bei Fehlkonfiguration: Server startet, Health-Check grün, aber Client-Verbindungen schlagen fehl. Häufig übersehen, weil viele Tutorials `transport="stdio"` als Default zeigen.

## Verification

### Modus 1: code_review (Transport-Selektion)

```bash
grep -rE 'transport\s*=\s*["\x27](stdio|sse|streamable-http)' src/
grep -rE 'mcp\.run\(' src/
```

**Pass-Pattern:**

```python
transport = os.environ.get("MCP_TRANSPORT", "stdio")
if transport in ("sse", "streamable-http"):
    mcp.settings.host = os.environ.get("MCP_HOST", "0.0.0.0")
    mcp.settings.port = int(os.environ.get("MCP_PORT", "8000"))
mcp.run(transport=transport)
```

### Modus 2: runtime_test (Cloud-Endpoint antwortet)

```bash
curl -s -X POST https://my-mcp.railway.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  -w "\nHTTP %{http_code}\n"
# Erwartet: HTTP 200 mit Capabilities-Response
```

### Modus 3: config_check (Deployment-Manifest)

```bash
# Railway / Render
cat railway.toml render.yaml 2>/dev/null | grep -E "MCP_TRANSPORT"
```

**Pass:** Deployment-Manifest setzt `MCP_TRANSPORT=streamable-http` oder `=sse` explizit.

## Pass Criteria

- [ ] ENV-basierte Transport-Selektion (stdio + streamable-http/sse)
- [ ] Cloud-Deployment nutzt streamable-http oder sse, nicht stdio
- [ ] Keine WebSocket-Implementierung mehr im Code
- [ ] Cloud-Endpoint antwortet auf `initialize` mit HTTP 200

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| `transport="stdio"` hartcodiert in Cloud-Deployment | Server startet, alle Verbindungen brechen |
| WebSocket statt Streamable HTTP | Veraltet, oft Probleme mit Reverse Proxies |
| ENV-Var fehlt im Deployment-Manifest | Cloud-Default greift nicht |

## Remediation

```diff
- mcp.run(transport="stdio")
+ transport = os.environ.get("MCP_TRANSPORT", "stdio")
+ if transport in ("sse", "streamable-http"):
+     mcp.settings.host = os.environ.get("MCP_HOST", "0.0.0.0")
+     mcp.settings.port = int(os.environ.get("MCP_PORT", "8000"))
+ mcp.run(transport=transport)
```

Plus Deployment-Config (Railway):

```toml
[deploy.environment]
MCP_TRANSPORT = "streamable-http"
MCP_HOST = "0.0.0.0"
MCP_PORT = "8000"
```

## Effort

S — < 1 Tag.

## References

- PDF Sec 5.1 — Transport
- [MCP Spec: Transports](https://modelcontextprotocol.io/specification/draft/basic/transports)
