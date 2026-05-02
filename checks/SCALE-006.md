---
id: SCALE-006
title: "Resource-Limits per Container (Memory, CPU, FDs)"
category: SCALE
severity: medium
applies_when: 'is_cloud_deployed == true'
pdf_ref: "Sec 5.3"
evidence_required: 2
---

# SCALE-006 — Resource-Limits per Container

## Description

Ohne explizite Resource-Limits kann ein einzelner MCP-Server-Bug das ganze System destabilisieren: ein Memory-Leak frisst die Host-Ressourcen, ein File-Descriptor-Leak öffnet Tausende dangling Connections, ein CPU-bound Query starvt nachbar-Pods. In Multi-Tenant-Cloud-Umgebungen (Railway, Render, K8s) müssen Memory, CPU, FDs explizit gedeckelt werden.

Faustregeln für MCP-Server: 256 MB – 1 GB RAM (je nach Daten-Cache), 0.5–1 CPU, FD-Limit 1024 (Standard reicht meistens). Bei Hybrid-Servern mit lokalem Dump-Cache eher 1–2 GB RAM einplanen.

## Verification

### Modus 1: config_check (Limits in Manifest)

```bash
# K8s
grep -rE 'resources:|limits:|requests:' k8s/ helm/

# Docker-Compose
grep -E 'mem_limit|cpus|deploy.resources' docker-compose.yml

# Railway / Render — über UI gesetzt, prüfen ob dokumentiert
grep -rE 'memory|cpu' railway.toml render.yaml 2>/dev/null
```

**Pass-Pattern (K8s):**

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: mcp-server
        image: malkreide/zh-education-mcp:v0.1.0
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

**Pass-Pattern (Docker-Compose):**

```yaml
services:
  mcp:
    image: malkreide/mcp-server
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 256M
          cpus: '0.25'
```

### Modus 2: runtime_test (OOM-Verhalten)

Stress-Test mit absichtlich grossen Anfragen, prüfen ob Container OOM-killed wird (statt Host-OOM):

```bash
# Container muss restart-policy haben
docker inspect <container_id> | grep -E "RestartPolicy|OOMKilled"
```

## Pass Criteria

- [ ] Memory-Limit ist explizit gesetzt (nicht Default)
- [ ] CPU-Limit ist gesetzt (Multi-Tenant-Scheduling-Schutz)
- [ ] Requests sind kleiner als Limits (Burst-Erlaubnis)
- [ ] FD-Limit prüfen: bei vielen ausgehenden Connections `ulimit -n` ≥ 4096
- [ ] OOM-Verhalten getestet: Server stürzt sauber ab, restart-policy aktiv

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Keine Limits → unbegrenzter Verbrauch | OOM des ganzen Hosts möglich |
| Limits zu knapp gesetzt | Unnötige OOMs bei Lastspitzen |
| Requests = Limits | Kein Burst-Headroom |
| FD-Limit Default (1024) bei vielen ausgehenden Connections | EMFILE-Errors |

## Remediation

Für Railway: in der Web-UI unter Project Settings → Resources die Limits setzen.

Für Docker-Compose-Production:

```yaml
services:
  mcp:
    image: malkreide/mcp-server:v0.1.0
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    ulimits:
      nofile:
        soft: 4096
        hard: 8192
```

## Effort

S — < 1 Tag pro Server.

## References

- PDF Sec 5.3
- [K8s Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
