---
id: ARCH-012
title: "protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin"
category: ARCH
severity: medium
applies_when: 'always'
pdf_ref: "Anhang A9"
evidence_required: 3
---

# ARCH-012 — Spec-Versionierung und SDK-Update-Disziplin

## Description

Die MCP-Spec hat in 21 Monaten fünf Major-Updates erlebt (2024-11, 2025-03, 2025-06, 2025-11, 2026-07). Das ist eine ungewöhnlich hohe Velocity für einen Industriestandard. Konkrete Folgen für Server-Maintainer:

1. **Tool Annotations** kamen erst 2025-03-26
2. **OAuth Resource Server** mit RFC 8707 wurde erst 2025-06-18 verpflichtend
3. **WebSocket-Transport** wurde 2025-03 abgeschafft, durch Streamable HTTP ersetzt
4. **Sitzungen und der `initialize`-Handshake** sind mit 2026-07-28 ersatzlos entfallen

Wer die `protocolVersion` als «latest» (oder gar nicht) pinnt, riskiert dass:

- Ein SDK-Update auf einer neuen Spec-Version den Server bricht (Client erwartet altes Protokoll)
- Sicherheits-Erweiterungen unbemerkt aktiviert oder deaktiviert werden
- Compliance-Anforderungen (z.B. RFC 8707 für DSG-konforme Multi-Tenant-Setups) ohne dokumentierten Übergang verloren gehen

Der Anhang verlangt drei Disziplinen:

1. **`protocolVersion` explizit gepinnt** im Server-Code, nicht «latest»
2. **`CHANGELOG.md`** im Keep-a-Changelog-Format mit Spec-Version-Referenzen pro Release
3. **Breaking-Change-Policy** im README dokumentiert
4. **Monatliche SDK-Update-Prüfung**, Breaking-Changes auf Branch testen vor Major-Update

Severity ist `medium`, weil Verstösse meist über Tests oder CI sichtbar werden — nicht stille Sicherheitslücken, sondern offene Brüche, die behoben werden.

### Wo die Version steht, hängt an der Baseline

Punkt 1 hat mit `2026-07-28` seinen Ort gewechselt, und das ist keine Feinheit — es ist der Unterschied zwischen einer Konstruktor-Konstante und einem Feld an jeder Anfrage:

| | `2025-11-25` | `2026-07-28` |
|---|---|---|
| Wo verhandelt | einmal im `initialize`-Handshake | gar nicht — jede Anfrage trägt die Version selbst |
| Wo im Code | `protocol_version=` am Server-Objekt | `io.modelcontextprotocol/protocolVersion` in `_meta`, pro Request gelesen |
| Wie ausgewiesen | Capabilities aus dem Handshake | `server/discover` (`ARCH-016`), als **Liste** unterstützter Versionen |
| Bei Nichtübereinstimmung | Handshake scheitert | `UnsupportedProtocolVersionError` (`-32022`) je Anfrage |

**Was dabei kippt:** Auf der alten Baseline war eine gepinnte Version eine Zusicherung — der Handshake liess nichts anderes zu. Auf der neuen ist eine im Konstruktor gepinnte Version bestenfalls Dekoration und schlimmstenfalls eine Lüge: Sie hindert niemanden daran, eine Anfrage mit einer anderen Version zu schicken, und wenn der Server das `_meta`-Feld nicht liest, bearbeitet er sie trotzdem. Der Server behauptet dann eine Version, die er nicht durchsetzt.

Deshalb prüft Modus 1 unten **je Baseline etwas anderes**. Dieselbe Frage, zwei Orte.

## Verification

### Modus 1: code_review (protocolVersion gepinnt)

```bash
grep -rnE 'protocolVersion|protocol_version|PROTOCOL_VERSION|SUPPORTED_PROTOCOL' src/
```

**Auf `mcp_spec_version: 2026-07-28`** ist das Pass-Pattern ein anderes — die Liste plus das Lesen aus `_meta`:

```python
SUPPORTED_PROTOCOL_VERSIONS = ["2026-07-28"]

def negotiate(meta: dict) -> str:
    requested = meta.get("io.modelcontextprotocol/protocolVersion")
    if requested not in SUPPORTED_PROTOCOL_VERSIONS:
        raise UnsupportedProtocolVersionError(-32022, supported=SUPPORTED_PROTOCOL_VERSIONS)
    return requested
```

Fail auf dieser Baseline: eine Konstante, die nirgends gegen `_meta` verglichen wird. Sie sieht wie ein Pin aus und ist keiner.

**Auf `mcp_spec_version: 2025-11-25` gilt weiterhin das Pattern darunter:**

```python
from mcp.server import FastMCP

# Explizit gepinnt auf eine bekannte, getestete Spec-Version
PROTOCOL_VERSION = "2025-06-18"

mcp = FastMCP(
    name="zh-education-mcp",
    protocol_version=PROTOCOL_VERSION,
    # ...
)
```

**Fail-Pattern:**

```python
# FAIL: keine explizite Version, nimmt SDK-Default (kann bei Update kippen)
mcp = FastMCP(name="zh-education-mcp")

# FAIL: "latest" oder unspezifisch
mcp = FastMCP(name="zh-education-mcp", protocol_version="latest")
```

### Modus 2: documentation_check (CHANGELOG vorhanden und maintained)

```bash
test -f CHANGELOG.md && echo "exists" || echo "MISSING"
head -30 CHANGELOG.md

# Letzter Eintrag wie alt?
git log -1 --format="%ai" CHANGELOG.md
```

**Pass-Pattern (`CHANGELOG.md` Keep-a-Changelog):**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0] — 2026-04-15
### Changed
- MCP protocolVersion bumped to 2025-11-05 (was 2025-06-18)
- Tool annotations now required per ARCH-009

### Added
- New tool `aggregate_by_district` (ARCH-007)

### Security
- API-Key migrated from plain env-var to AWS Secrets Manager (SEC-013)

## [0.3.0] — 2026-02-01
### Changed
- MCP protocolVersion locked to 2025-06-18
- ...
```

### Modus 3: documentation_check (Breaking-Change-Policy)

```bash
grep -iE 'breaking|spec.version|protocol.version|migration' README.md README.de.md
```

**Pass:** README enthält eine Sektion zur Spec-Version und Update-Policy:

```markdown
## MCP Protocol Version

This server pins MCP protocol version `2025-06-18`. The version is explicit
in `src/zh_education_mcp/server.py` and tracked per release in CHANGELOG.md.

### Update-Policy
- Spec-Updates werden zuerst auf einem Feature-Branch gegen die SDK-Beta getestet
- Breaking-Changes lösen ein Major-Release aus (semver)
- Compatibility-Window: alte Spec-Versionen werden für 6 Monate weiter unterstützt
```

### Modus 4: code_review (Dependency-Update-Hygiene)

Über Dependabot oder Renovate werden SDK-Updates automatisch als PR vorgeschlagen.

```bash
ls .github/dependabot.yml .github/renovate.json renovate.json 2>/dev/null
```

**Pass-Pattern (`.github/dependabot.yml`):**

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "monthly"
    labels:
      - "dependencies"
    groups:
      mcp-sdk:
        patterns:
          - "mcp"
          - "fastmcp"
```

## Pass Criteria

- [ ] `protocolVersion` ist im Server-Code explizit gepinnt (kein «latest», kein Default)
- [ ] Auf `2026-07-28`: Die gepinnte Version wird **pro Request** gegen `io.modelcontextprotocol/protocolVersion` aus `_meta` geprüft — eine Konstante ohne diesen Vergleich zählt nicht
- [ ] Auf `2026-07-28`: Nichtübereinstimmung liefert `UnsupportedProtocolVersionError` (`-32022`), und `server/discover` nennt dieselbe Versionsliste (`ARCH-016`)
- [ ] `CHANGELOG.md` vorhanden, im Keep-a-Changelog-Format
- [ ] CHANGELOG-Einträge nennen explizit Spec-Version-Bumps
- [ ] README hat Sektion «MCP Protocol Version» mit aktuell unterstützter Version
- [ ] Update-Policy im README dokumentiert
- [ ] Dependabot oder Renovate aktiv für monatliche SDK-Update-PRs

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Keine explizite `protocolVersion` | Stiller Bruch bei SDK-Update |
| CHANGELOG fehlt | Maintainer kennen Release-Historie nicht |
| Spec-Version-Bumps werden nicht im CHANGELOG erwähnt | Audit-Trail-Lücke bei Breaking Changes |
| SDK-Updates manuell und sporadisch | Sicherheits-Patches kommen verspätet |

## Remediation

### Schritt 1: protocolVersion pinnen

```diff
+ from importlib.metadata import version

  mcp = FastMCP(
      name="zh-education-mcp",
+     protocol_version="2025-06-18",
  )
```

### Schritt 2: CHANGELOG initialisieren

Wenn nicht vorhanden, mit Template starten und retroaktiv Major-Versionen dokumentieren (mindestens letzte 3).

### Schritt 3: Dependabot konfigurieren

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "monthly"
    open-pull-requests-limit: 5
```

### Schritt 4: Quartalsweise Spec-Review

Im Audit-Tracker (Notion) oder GitHub Issues ein recurring Reminder für quartalsweise Spec-Velocity-Review:

- Was hat sich an der MCP-Spec geändert seit letztem Release?
- Welche Server müssen ihre `protocolVersion` aktualisieren?
- Gibt es Compliance-relevante Spec-Änderungen?

## Effort

S — < 1 Tag pro Server. Pinning + CHANGELOG-Template + Dependabot-Setup.

## References

- [Spec 2026-07-28 — Changelog, Major #2 und #3](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- `ARCH-015` (Stateless), `ARCH-016` (server/discover), `ARCH-021` (Extensions)

- Anhang A9 — Versionierung und Spec-Velocity
- [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)
- [Semantic Versioning 2.0.0](https://semver.org/)
- [MCP Spec Releases](https://modelcontextprotocol.io/specification/draft/changelog)
- ARCH-011 — Repo-Struktur (Synergie über CHANGELOG.md)
