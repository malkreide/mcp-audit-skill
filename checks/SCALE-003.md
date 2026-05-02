---
id: SCALE-003
title: "Mcp-Session-Id Routing via Edge-LB (HAProxy Stick-Tables)"
category: SCALE
severity: high
applies_when: '(transport == "HTTP/SSE" or transport == "dual") and is_cloud_deployed == true'
pdf_ref: "Sec 5.2"
evidence_required: 2
---

# SCALE-003 — Mcp-Session-Id Routing via Edge-LB

## Description

Dieser Check ergänzt SCALE-002 (Stateful Load Balancing) mit dem konkreten Routing-Layer. Wenn die Architektur-Entscheidung Sticky Sessions ist, muss der Edge-Load-Balancer den `Mcp-Session-Id`-Header **lesen** und für Routing nutzen. Auf K8s-Ingress mit Default-Konfiguration läuft das nicht out-of-the-box — die meisten Ingress-Controller nutzen IP-basierte Affinität, was hinter NAT/Proxy bricht.

Konkrete LB-Optionen: HAProxy mit `stick-table` auf `hdr(Mcp-Session-Id)`, NGINX mit `ngx_http_upstream_module` und `hash $http_mcp_session_id consistent`, oder K8s Ingress mit `nginx.ingress.kubernetes.io/affinity-mode: persistent` plus Cookie-Mapping.

## Verification

### Modus 1: config_check (LB-Konfiguration)

```bash
# HAProxy-Config
grep -rE 'stick.*hdr|hdr.*Mcp-Session' deploy/ haproxy/

# K8s-Ingress
grep -rE 'affinity|sticky|session.affinity' k8s/ helm/

# Generelle Suche
find . -name 'haproxy.cfg' -o -name 'nginx.conf' -o -name 'ingress*.yaml'
```

**Pass-Pattern (HAProxy):**

```
backend mcp_backend
    mode http
    balance roundrobin
    stick-table type string len 64 size 200k expire 24h
    stick on hdr(Mcp-Session-Id)
    server mcp1 10.0.1.1:8080 check
    server mcp2 10.0.1.2:8080 check
```

**Pass-Pattern (NGINX):**

```nginx
upstream mcp_backend {
    hash $http_mcp_session_id consistent;
    server mcp1.internal:8080;
    server mcp2.internal:8080;
}
```

### Modus 2: runtime_test (Affinitäts-Verhalten)

```bash
SESSION=$(curl -s -X POST https://server/mcp/init | jq -r .session_id)
for i in 1 2 3 4 5; do
    curl -s -H "Mcp-Session-Id: $SESSION" https://server/mcp/call \
         -o /dev/null -w "Pod: %{header.x-served-by}\n"
done
# Erwartung: alle 5 Zeilen zeigen denselben Pod-Identifier
```

## Pass Criteria

- [ ] Edge-LB liest `Mcp-Session-Id`-Header explizit
- [ ] Stick-Table / Hash-Mechanismus mit ausreichender Kapazität (≥100k Sessions)
- [ ] TTL ist explizit gesetzt (z.B. 24h, korreliert mit Session-TTL)
- [ ] Failover-Verhalten getestet: bei Backend-Ausfall wird Session nicht auf neuen Backend ohne Shared State geroutet

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| IP-basierte Affinität statt Header | Hinter NAT bricht Routing |
| Stick-Table zu klein | Sessions kollidieren, Hash überschreibt |
| Kein TTL | Speicher-Leak im LB |
| K8s-Ingress-Default ohne explizite Konfiguration | Round-Robin ohne Affinität |

## Remediation

Für K8s-Ingress (NGINX):

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-ingress
  annotations:
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/session-cookie-name: "mcp-route"
    nginx.ingress.kubernetes.io/upstream-hash-by: "$http_mcp_session_id"
spec:
  rules:
  - host: mcp.example.ch
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-server
            port:
              number: 8080
```

## Effort

M — 1–3 Tage. LB-Config + Failover-Tests.

## References

- PDF Sec 5.2
- [HAProxy Stick Tables](https://www.haproxy.com/documentation/haproxy-configuration-tutorials/load-balancing/stick-tables/)
- [NGINX Hash Load Balancing](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#hash)
