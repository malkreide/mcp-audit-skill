---
id: SCALE-002
title: "Stateful Load Balancing für Streamable HTTP / SSE"
category: SCALE
severity: high
applies_when: 'transport == "HTTP/SSE" or transport == "dual"'
pdf_ref: "Sec 5.2"
evidence_required: 2
---

# SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

## Description

MCP-Verbindungen über Streamable HTTP / SSE sind **fundamental zustandsbehaftet**. Bei der Verbindungsinitialisierung verhandeln Client und Server Protokollversionen, Capability-Flags und etablieren Abonnements für Ressourcenänderungen.

In horizontal skalierten Deployments (Kubernetes, mehrere Pods, Cloudflare Workers, Railway-Replicas) routen Standard-Load-Balancer naive Anfragen ohne Affinität zu unterschiedlichen Backend-Instanzen. Wenn eine MCP-Session mitten im Lifecycle auf einen anderen Pod springt, geht der Sitzungskontext verloren — der Agent bricht ab, Konversation kollabiert.

Es gibt zwei legitime Lösungsmuster: Sticky Sessions (infrastrukturell) oder Shared State (cloud-native).

## Verification

### Modus 1: config_check (Deployment-Konfiguration)

Je nach Deployment-Plattform anders zu prüfen:

**Railway / Render / Heroku (klassische Container-Deployments):**

```bash
# Suche nach Sticky-Session-Konfiguration
grep -rE "stick|session.affinity|cookie.*affinity" .
cat railway.toml render.yaml docker-compose.yml 2>/dev/null
```

**Kubernetes:**

```bash
# Service oder Ingress muss Session-Affinity haben
grep -rE "sessionAffinity|stick" k8s/ helm/ deploy/
# Muss mindestens eines davon enthalten:
#   sessionAffinity: ClientIP
#   nginx.ingress.kubernetes.io/affinity: "cookie"
```

**Cloudflare Workers / Durable Objects:**

```bash
# Durable Objects als Shared-State-Indikator
grep -rE "DurableObject|durable_object" src/ wrangler.toml
```

### Modus 2: code_review (Session-Manager-Pattern)

Wenn kein infrastruktureller Sticky-Session-Mechanismus, dann muss Session-State extern persistiert werden.

```bash
# Suche nach Redis / externer Session-Store
grep -rE "redis|memcached|session_manager|SessionStore" src/
```

**Akzeptabel — Lösung A (Sticky Session):**

```yaml
# HAProxy-Config-Snippet
backend mcp_servers
    balance roundrobin
    stick-table type string len 64 size 100k expire 24h
    stick on hdr(Mcp-Session-Id)
    server mcp1 10.0.0.1:8080 check
    server mcp2 10.0.0.2:8080 check
```

**Akzeptabel — Lösung B (Shared State):**

```python
import redis.asyncio as redis
from mcp.server.session import SessionManager

session_store = redis.from_url("redis://session-redis:6379")

class RedisSessionManager(SessionManager):
    async def get(self, session_id: str) -> Session | None:
        data = await session_store.get(f"mcp:session:{session_id}")
        return Session.from_json(data) if data else None

    async def set(self, session: Session) -> None:
        await session_store.setex(
            f"mcp:session:{session.id}",
            ttl=3600,
            value=session.to_json(),
        )

mcp = FastMCP("server", session_manager=RedisSessionManager())
```

### Modus 3: runtime_test (Failover-Verhalten)

Wenn möglich live testen:

```bash
# Pod-Identifier in Response-Header einbauen, dann mehrere Requests
SESSION_ID=$(curl -s -X POST https://server/mcp/init | jq -r .session_id)

# 5 Folge-Requests sollten alle zum selben Pod
for i in 1 2 3 4 5; do
    curl -s -H "Mcp-Session-Id: $SESSION_ID" https://server/mcp/call \
         -o /dev/null -w "Pod: %{header.x-served-by}\n"
done
# Erwartung: alle 5 Zeilen zeigen denselben Pod-Identifier
```

## Pass Criteria

- [ ] Mindestens **eines** der folgenden Muster ist nachweisbar implementiert:
  - Sticky Sessions auf Edge-LB-Ebene (HAProxy/Nginx/K8s-Ingress) basierend auf `Mcp-Session-Id`
  - Shared-State-Session-Manager mit Redis, Cloudflare Durable Objects oder vergleichbarem
- [ ] Session-Lifetime ist explizit gesetzt (TTL definiert)
- [ ] Failover-Test (Modus 3) zeigt korrektes Verhalten ODER wurde nachgewiesen über Tests

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Standard-Load-Balancer ohne Affinity-Konfiguration | Sessions brechen bei jedem Pod-Switch |
| Session-State im Pod-Memory ohne Persistenz | Pod-Neustart killt alle Sessions |
| Sticky Sessions per IP statt per Header | Hinter NAT/Proxy bricht Routing |
| `Mcp-Session-Id`-Header wird vom LB nicht gelesen | Affinity wird nie aktiviert |

## Remediation

### Variante A: Sticky Sessions mit HAProxy

```haproxy
frontend mcp_frontend
    bind *:443 ssl crt /etc/ssl/server.pem
    mode http
    # Backend-Selection nach Mcp-Session-Id
    default_backend mcp_backend

backend mcp_backend
    mode http
    balance roundrobin
    stick-table type string len 64 size 200k expire 24h peers mycluster
    stick on hdr(Mcp-Session-Id)
    option httpchk GET /healthz
    server mcp1 10.0.1.1:8080 check
    server mcp2 10.0.1.2:8080 check
    server mcp3 10.0.1.3:8080 check
```

### Variante B: Redis-basierter Session-Manager

```python
# pyproject.toml
# dependencies = ["fastmcp", "redis>=5.0", "structlog"]

from contextlib import asynccontextmanager
from fastmcp import FastMCP
from redis.asyncio import Redis
import json

@asynccontextmanager
async def lifespan(app):
    redis_client = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    app.state.session_store = redis_client
    try:
        yield
    finally:
        await redis_client.aclose()

mcp = FastMCP("zurich-opendata", lifespan=lifespan)
```

### Effort-Empfehlung

- **Variante A** schneller bei vorhandener LB-Infrastruktur (1–2 Tage)
- **Variante B** robuster langfristig, vermeidet Sticky-Session-Komplikationen (3–5 Tage)

## Effort

M — 1–3 Tage je nach Komplexität der bestehenden Infrastruktur.

## References

- PDF Sec 5.2 — Stateful Load Balancing
- [TheNewStack: Load Balance Streamable MCP Servers](https://thenewstack.io/scaling-ai-interactions-how-to-load-balance-streamablemcp/)
- [MCP Spec: Transports](https://modelcontextprotocol.io/specification/draft/basic/transports)
