---
id: ARCH-005
title: "Keine Hardcoded Secrets: Env-Vars / Secret Manager only"
category: ARCH
severity: critical
applies_when: 'always'
pdf_ref: "Sec 2.1"
evidence_required: 3
---

# ARCH-005 — Keine Hardcoded Secrets

## Description

Hardcoded Secrets (API-Keys, Passwörter, Tokens, Connection-Strings, Encryption-Keys) im Source-Code sind die häufigste vermeidbare Sicherheitsschwäche in MCP-Server-Repositories. Sobald das Repo öffentlich ist (oder versehentlich öffentlich wird), oder ein Mitarbeiter aus dem Team ausscheidet, sind alle Secrets kompromittiert.

GitHub's Secret-Scanning fängt einen Teil davon ab — aber: (1) nicht alle Pattern werden erkannt, (2) Custom-API-Keys (z.B. interne Schulamt-APIs) sind unbekannt, (3) selbst nach Erkennung ist der Schlüssel bereits im Git-Verlauf und muss neu ausgestellt werden.

**Risiko-Eskalation:**

1. Klartext im Code → Public Repo → globaler Leak
2. Klartext in Env-Vars im Code → docker-compose.yml im Repo → gleicher Leak
3. Env-Vars-Referenz im Code, .env-Datei nicht in .gitignore → Leak via PR
4. Korrekte .gitignore, aber Klartext in CI-Logs → Leak via Public Actions
5. Korrekte CI-Maskierung, aber Klartext in Container-Image-Layer → Leak via Docker-Hub

Der Best-Practice-Standard für Production ist: **Env-Vars als Minimum, Secret-Manager als Empfehlung.**

## Verification

### Modus 1: automated (Pattern-Suche)

Ein erstes Screening mit pattern-basierten Tools:

```bash
# Generische Pattern
grep -rE "(api[_-]?key|password|secret|token).*=.*[\"'][^\"']{16,}[\"']" src/ \
  --include="*.py" --include="*.ts" --include="*.js" --include="*.go" \
  --exclude-dir=tests --exclude-dir=node_modules

# Schweiz-spezifisch
grep -rE "ZHWEB|stadt-zuerich.*api.*[\"']" src/

# Connection-Strings
grep -rE "(postgres|mysql|mongodb)://[^:]+:[^@]+@" src/

# AWS
grep -rE "AKIA[0-9A-Z]{16}" src/
```

### Modus 2: automated (gitleaks / trufflehog Run)

```bash
# Gitleaks lokal
docker run --rm -v "$(pwd):/repo" zricethezav/gitleaks:latest detect \
  --source /repo --verbose

# Trufflehog (sucht auch im Git-History)
docker run --rm -v "$(pwd):/repo" trufflesecurity/trufflehog:latest \
  filesystem /repo --only-verified
```

**Pass:** Beide Tools liefern keine `verified` Findings.

### Modus 3: code_review (Env-Var-Loading-Pattern)

```bash
grep -rE "os\.environ|process\.env|dotenv" src/
```

**Pass-Pattern (Python mit Pydantic-Settings):**

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """All secrets loaded from environment, never hardcoded."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    api_key: SecretStr
    database_url: SecretStr
    oauth_client_secret: SecretStr

settings = Settings()  # raises if any required var is missing

# Usage
async def call_upstream():
    return await httpx.get(
        "https://api.example.com/data",
        headers={"Authorization": f"Bearer {settings.api_key.get_secret_value()}"},
    )
```

**Pass-Pattern (TypeScript):**

```typescript
import { z } from "zod";

const EnvSchema = z.object({
  API_KEY: z.string().min(16),
  DATABASE_URL: z.string().url(),
  OAUTH_CLIENT_SECRET: z.string().min(32),
});

export const env = EnvSchema.parse(process.env);
// Throws at startup if any var is missing — fail-fast
```

**Fail-Pattern:**

```python
# FAIL: Klartext im Code
API_KEY = "sk-1234567890abcdef..."

# FAIL: Default-Wert mit echtem Schlüssel
api_key = os.environ.get("API_KEY", "fallback-real-key-here")

# FAIL: Schlüssel in Logs
logger.info(f"Using API key: {api_key}")
```

### Modus 4: code_review (.gitignore und .env.example)

```bash
cat .gitignore | grep -E "\.env|secrets|credentials"
ls -la | grep -E "\.env"
```

**Pass:**
- `.gitignore` enthält `.env`, `.env.local`, `*.secrets`
- `.env.example` existiert mit Platzhaltern (kein Klartext)
- Tatsächliche `.env` ist nicht im Repo

### Modus 5: config_check (Secret-Scanning aktiv in CI)

```bash
ls .github/workflows/
grep -rE "gitleaks|trufflehog|secret.scan" .github/workflows/
```

**Pass:** Mindestens ein automatisierter Scan läuft auf jedem PR.

```yaml
# .github/workflows/security.yml
name: Secret Scan
on: [push, pull_request]

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Pass Criteria

- [ ] Keine API-Keys, Passwörter, Tokens, Connection-Strings im Source-Code
- [ ] Keine Default-Werte mit echten Secrets in `os.environ.get(..., default=...)` oder ähnlich
- [ ] Secrets werden zur Startzeit aus Env-Vars / Secret-Manager geladen (Pydantic-Settings o.ä.)
- [ ] In-Memory-Repräsentation als `SecretStr` (Python) oder gleichwertig (kein `str`)
- [ ] Secrets erscheinen **nicht** in Log-Outputs (keine `f"{settings}"`-Logs)
- [ ] `.gitignore` enthält `.env`, `.env.*` (ausser `.env.example`)
- [ ] `.env.example` mit Platzhaltern existiert und ist im Repo
- [ ] CI-Workflow mit Gitleaks oder Trufflehog läuft auf PRs

## Common Failures

| Pattern | Risiko |
|---|---|
| `API_KEY = "sk-real..."` im Code | Repo-Push = globaler Leak |
| `.env` nicht in `.gitignore` | Versehen-Commit committet Secret |
| `print(settings)` ohne Maskierung | Klartext in stdout / CI-Logs |
| Schlüssel im Container-Image-Layer (`ENV API_KEY=...` im Dockerfile) | Image-Pull = Secret-Leak |
| Klartext in `docker-compose.yml` | Repo-File enthält Secret |
| Kein CI-Secret-Scan | Bug findet keiner bevor er Production trifft |

## Remediation

### Schritt 1: Bestehende Secrets identifizieren und ersetzen

```bash
# Lokale Suche (vor jeglichem Push)
gitleaks detect --source . --verbose

# Falls schon committed: History-Rewrite ZUSÄTZLICH zur Schlüssel-Rotation
# Wichtig: rotation FIRST, history-rewrite zweitrangig
```

### Schritt 2: Migration zu Pydantic-Settings

```python
# Vorher
API_KEY = "sk-1234..."

# Nachher
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: SecretStr
    model_config = {"env_file": ".env", "extra": "forbid"}

settings = Settings()
# Im Code: settings.api_key.get_secret_value()
```

### Schritt 3: `.env.example` mit Platzhaltern

```bash
# .env.example (committet)
API_KEY=replace-with-real-key
DATABASE_URL=postgresql://user:pass@localhost/dbname
OAUTH_CLIENT_SECRET=at-least-32-characters-long-secret

# .env (NICHT committet, in .gitignore)
API_KEY=sk-actual-real-key
...
```

### Schritt 4: Production-Secret-Manager (höhere Reife)

| Plattform | Mechanismus |
|---|---|
| Railway | Project-Variables (verschlüsselt at-rest) |
| Render | Environment-Groups |
| Kubernetes | `Secret`-Objects + `secretKeyRef` in Pod-Spec |
| Self-Hosted | HashiCorp Vault, AWS Secrets Manager (EU-Region!), GCP Secret Manager |

```python
# AWS Secrets Manager (EU-Region für DSG, siehe CH-001)
import boto3
import json

def load_secret(name: str) -> dict:
    client = boto3.client("secretsmanager", region_name="eu-central-1")
    response = client.get_secret_value(SecretId=name)
    return json.loads(response["SecretString"])

secrets = load_secret("schulamt-mcp/production")
api_key = secrets["api_key"]
```

### Schritt 5: CI-Scan einrichten

Siehe Modus 5 oben.

### Schritt 6: Pre-Commit-Hook lokal

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

```bash
pre-commit install
# Verhindert Commits mit erkannten Secrets lokal
```

## Effort

S–M — Bei sauberem Repo: < 1 Tag (Settings-Migration + CI-Setup). Bei Repo mit Secret-Leak in History: 2–3 Tage (Rotation aller Schlüssel, History-Rewrite, Audit aller Forks/Clones).

## References

- PDF Sec 2.1 — Inversion of Control
- [GitGuardian State of Secrets Sprawl](https://www.gitguardian.com/state-of-secrets-sprawl-report-2024)
- [Pydantic-Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Gitleaks](https://github.com/gitleaks/gitleaks) / [Trufflehog](https://github.com/trufflesecurity/trufflehog)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
