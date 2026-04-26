---
id: ARCH-004
title: "Inversion of Control: Transport-agnostische Server-Logik"
category: ARCH
severity: high
applies_when: 'always'
pdf_ref: "Sec 2.1"
evidence_required: 3
---

# ARCH-004 — Inversion of Control

## Description

Die MCP-Spezifikation trennt strikt zwischen Data Layer (JSON-RPC 2.0, Tools/Resources/Prompts) und Transport Layer (stdio / Streamable HTTP / SSE). Der Best-Practice-Standard verlangt, dass die Geschäftslogik des Servers diese Trennung respektiert: Tool-Handler müssen **transport-agnostisch** sein. Derselbe `searchData()`-Tool-Handler muss identisch funktionieren, egal ob er via stdio (Claude Desktop) oder SSE (Cloud-Deployment) aufgerufen wird.

**Warum:**

1. **Dual-Transport-Support:** Portfolio-Server müssen sowohl lokal (stdio) als auch in der Cloud (SSE) laufen. Ohne IoC braucht man zwei Codebasen.
2. **Testbarkeit:** Transport-spezifische Logik in Handlern macht Unit-Tests fragil (mocking von HTTP-Internals).
3. **Sicherheit:** Auth-, Rate-Limit- und Logging-Middleware soll generisch funktionieren — unabhängig vom Transport.

Das praktische Pattern: Konfiguration und Capabilities werden via **Dependency Injection** (Lifespan-Setup, Settings-Objekt, Context-Parameter) in die Handler reingereicht. Handler greifen niemals direkt auf Transport-Internals (`request.headers`, `connection.remote_addr`) zu.

## Verification

### Modus 1: code_review (Transport-Internals in Tool-Handlern)

```bash
# Suche nach Transport-Spezifika in Tool-Handlern
grep -rA20 "@mcp\.tool\|@server\.tool" src/ | grep -E "request\.|websocket\.|stdin|stdout"
```

**Pass:** Keine direkten Zugriffe auf HTTP-Request- oder stdio-spezifische Objekte in Tool-Handlern.

**Fail-Pattern:**

```python
@mcp.tool()
async def search(query: str, request: Request):  # ← Transport-Leak
    user_agent = request.headers["User-Agent"]   # ← spezifisch für HTTP
    if "claude-desktop" in user_agent:
        return await search_optimized(query)
    return await search_standard(query)
```

**Pass-Pattern:**

```python
@mcp.tool()
async def search(query: str, ctx: Context):
    # ctx ist transport-agnostisch
    client_info = ctx.client_info  # via MCP-Protocol, nicht HTTP
    if client_info.name == "claude-desktop":
        return await search_optimized(query)
    return await search_standard(query)
```

### Modus 2: code_review (Konfiguration via Env-Vars / Settings)

```bash
grep -rE "BaseSettings|Settings|os\.environ" src/
```

**Pass-Pattern:**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    transport: str = "stdio"           # stdio | sse
    host: str = "127.0.0.1"
    port: int = 8000
    upstream_api_base: str
    log_level: str = "INFO"

settings = Settings()

mcp = FastMCP("zurich-opendata", lifespan=create_lifespan(settings))

if __name__ == "__main__":
    if settings.transport == "stdio":
        mcp.run(transport="stdio")
    elif settings.transport == "sse":
        mcp.settings.host = settings.host
        mcp.settings.port = settings.port
        mcp.run(transport="sse")
```

**Fail-Pattern:**

```python
# FAIL: hartcodiert auf einen Transport
mcp = FastMCP("zurich-opendata")

@mcp.tool()
async def search(query: str): ...

if __name__ == "__main__":
    mcp.run(transport="stdio")  # nur stdio, kein SSE-Support
```

### Modus 3: runtime_test (Beide Transports liefern identisches Verhalten)

```bash
# Stdio-Mode
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test"}}}' | python -m my_mcp > stdio_output.json

# SSE-Mode
MCP_TRANSPORT=sse python -m my_mcp &
SERVER_PID=$!
sleep 2
curl -s -X POST http://localhost:8000/mcp -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test"}}}' > sse_output.json
kill $SERVER_PID

# Vergleich: Tool-Result muss identisch sein (modulo Transport-Metadaten)
diff <(jq '.result' stdio_output.json) <(jq '.result' sse_output.json)
```

**Pass:** Beide Outputs sind in `result` identisch.

## Pass Criteria

- [ ] Tool-Handler nutzen ausschliesslich `ctx: Context` für Client-/Session-Information (kein direkter `request`-Zugriff)
- [ ] Server-Code unterstützt mindestens stdio + SSE/Streamable-HTTP (per ENV-Var wählbar)
- [ ] Konfiguration läuft über Settings-Objekt (Pydantic-Settings o.ä.), nicht über globale Module-Vars
- [ ] Tools liefern identische Outputs unabhängig vom Transport (ausser explizit transport-spezifische Tools)
- [ ] Lifespan / Setup-Code ist gemeinsam für alle Transports

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| `request.headers` in Tool-Handler | Funktioniert nur via HTTP, bricht bei stdio |
| Globale Variablen statt Settings-Objekt | Tests werden flaky (Test-Reihenfolge beeinflusst Ergebnis) |
| Hartcodierter Transport-Wert | Cloud-Deployment unmöglich ohne Code-Fork |
| Auth-Middleware nur für HTTP | stdio bleibt ungeschützt (oft akzeptabel, aber dokumentieren) |

## Remediation

Migrationsweg von monolithischem Setup zu IoC:

```diff
+ from pydantic_settings import BaseSettings
+ from contextlib import asynccontextmanager
+
+ class Settings(BaseSettings):
+     transport: str = "stdio"
+     host: str = "127.0.0.1"
+     port: int = 8000
+
+ @asynccontextmanager
+ async def lifespan(server):
+     # Shared setup für alle Transports
+     server.state.http_client = httpx.AsyncClient(timeout=30)
+     try:
+         yield
+     finally:
+         await server.state.http_client.aclose()
+
- mcp = FastMCP("server")
+ settings = Settings()
+ mcp = FastMCP("server", lifespan=lifespan)

  @mcp.tool()
- async def search(query: str, request: Request):
-     ua = request.headers["User-Agent"]
-     ...
+ async def search(query: str, ctx: Context):
+     client_name = ctx.client_info.name
+     ...

  if __name__ == "__main__":
-     mcp.run(transport="stdio")
+     if settings.transport == "sse":
+         mcp.settings.host = settings.host
+         mcp.settings.port = settings.port
+     mcp.run(transport=settings.transport)
```

## Effort

M — 1–3 Tage. Refactoring der Transport-Auswahl, Migration aller `request`-Zugriffe auf `ctx`, Testing in beiden Modi.

## References

- PDF Sec 2.1 — Inversion of Control
- [MCP Spec: Architecture](https://modelcontextprotocol.io/specification/draft/architecture)
- [FastMCP Lifespan Docs](https://gofastmcp.com/servers/server)
