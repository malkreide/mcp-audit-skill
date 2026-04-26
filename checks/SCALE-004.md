---
id: SCALE-004
title: "Containerization mit Multi-Stage-Builds"
category: SCALE
severity: medium
applies_when: 'deployment != "local-stdio"'
pdf_ref: "Sec 5.3"
evidence_required: 2
---

# SCALE-004 — Containerization mit Multi-Stage-Builds

## Description

Container-Images für MCP-Server sind oft 800 MB – 1.5 GB gross, weil Build-Toolchains (gcc, Rust, npm-build-deps) im finalen Image bleiben. Multi-Stage-Builds trennen Build und Runtime: das finale Image enthält nur den fertigen Server plus minimale Runtime-Dependencies (typischerweise 80–150 MB).

Vorteile über Image-Grösse hinaus: kleinere Angriffsfläche (kein gcc, kein curl, keine Test-Tools im Production-Image), schnellere Pull-Zeiten (relevant bei Auto-Scaling), weniger CVE-Treffer im Container-Scan.

## Verification

### Modus 1: automated (Dockerfile-Struktur)

```bash
grep -cE '^FROM ' Dockerfile  # ≥ 2 = multi-stage
grep -E '^FROM .* AS ' Dockerfile  # named stages
docker images | grep mcp  # Grösse < 200 MB?
```

**Pass-Pattern:**

```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --user -e .

# Runtime stage
FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY src/ ./src/
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
USER nobody
EXPOSE 8000
CMD ["python", "-m", "my_mcp_server"]
```

### Modus 2: config_check (User-Privileges + Healthcheck)

```bash
grep -E '^USER |^HEALTHCHECK' Dockerfile
```

**Pass:**
- `USER nobody` oder explizit non-root User gesetzt
- `HEALTHCHECK`-Direktive vorhanden

## Pass Criteria

- [ ] Dockerfile hat ≥ 2 `FROM`-Statements (multi-stage)
- [ ] Stages haben Namen (`AS builder`, `AS runtime`)
- [ ] Final-Image basiert auf `-slim` oder `-alpine` Base
- [ ] Final-Image-Grösse < 200 MB (Python) / < 80 MB (Go/Rust)
- [ ] `USER nobody` oder explizit non-root User gesetzt
- [ ] `HEALTHCHECK`-Direktive für LB-Integration

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Single-stage Dockerfile mit `python:3.11` (full) | Image > 1 GB, mehr CVEs |
| `RUN apt-get install build-essential` ohne nachträgliches Cleanup | Build-Tools bleiben im Image |
| `USER root` (Default) | Container-Escape erleichtert |
| Keine Healthcheck-Direktive | LB kann Pod-Status nicht verifizieren |

## Remediation

```diff
- FROM python:3.11
- WORKDIR /app
- COPY . .
- RUN pip install -e .
- CMD ["python", "-m", "server"]
+ FROM python:3.11-slim AS builder
+ WORKDIR /build
+ COPY pyproject.toml .
+ COPY src/ ./src/
+ RUN pip install --no-cache-dir --user -e .
+
+ FROM python:3.11-slim AS runtime
+ COPY --from=builder /root/.local /root/.local
+ COPY src/ /app/src/
+ WORKDIR /app
+ ENV PATH=/root/.local/bin:$PATH PYTHONUNBUFFERED=1
+ USER nobody
+ HEALTHCHECK CMD curl -f http://localhost:8000/healthz || exit 1
+ CMD ["python", "-m", "server"]
```

## Effort

S — < 1 Tag.

## References

- PDF Sec 5.3
- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
