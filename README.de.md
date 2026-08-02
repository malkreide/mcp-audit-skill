# mcp-audit-skill

> Claude-Skill für systematische Audits von MCP-Servern gegen einen kuratierten Best-Practice-Standards-Korpus. **93 Checks**, 12 Kategorien, mit Schweiz-Compliance-Layer für die öffentliche Verwaltung und Datentreue-Layer für Datenquellen-Server.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Checks: 93](https://img.shields.io/badge/Checks-93-blue.svg)](./checks/)
[![Coverage: A1–A9, B1–B12, C1–C4](https://img.shields.io/badge/Best--Practice%20Coverage-A1%E2%80%93A9%2C%20B1%E2%80%93B12%2C%20C1%E2%80%93C4-success)](./CHANGELOG.md)
[![MCP Spec: 2025-06-18](https://img.shields.io/badge/MCP%20Spec-2025--06--18-orange)](https://modelcontextprotocol.io/specification/)

🇬🇧 [English Version](README.md)

---

**Was es ist:** Ein Claude-Skill, der MCP-Server systematisch gegen veröffentlichte Best Practices auditiert. Jeder Check referenziert seine Quelle, hat klare Pass-Kriterien, einen Remediation-Pfad und einen Aufwands-Indikator.

**Was es nicht ist:** Kein automatischer Code-Scanner, kein Vulnerability-Tool, kein Compliance-Stempel. Der Skill macht die Methodik reproduzierbar — Architektur-Urteile bleiben menschlich.

## Architektur-Modell

Die Checks orientieren sich am Fünf-Schichten-Sicherheitsmodell, das in der MCP-Sicherheits-Community als Konsens-Architektur etabliert ist. Jede Schicht prüft eigenständig — keine vertraut der nächsthöheren blind.

```text
┌────────────────────────────────────────────────────────┐
│  LLM-Host (Claude, ChatGPT, Cursor)                    │
│  Untrusted: kann Prompt-Injektionen enthalten          │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  MCP-Gateway / Policy Layer                            │
│  Rate-Limit · Audit-Log · DLP · Tool-Allowlist         │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  Authentifizierung & Autorisierung                     │
│  OAuth 2.1 + PKCE · Resource Indicators · Scopes       │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  MCP-Server-Logik                                      │
│  Input-Validierung · Schema · Idempotenz · Sandbox     │
└────────────────────────┬───────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────┐
│  Datenquelle / Backend                                 │
│  Read-only Service-Account · Least Privilege           │
└────────────────────────────────────────────────────────┘
```

## SOLID für MCP-Server

Die fünf Prinzipien, an denen sich der gesamte Check-Katalog ausrichtet:

| Prinzip | Bedeutung | Schlüssel-Checks |
|---|---|---|
| **S**andbox | Jeder Server in Docker / WASM mit Egress-Filter | [`SEC-007`](./checks/SEC-007.md), [`SEC-021`](./checks/SEC-021.md) |
| **O**Auth 2.1 | OAuth statt API-Keys, mit PKCE und Resource Indicators | [`SEC-001`](./checks/SEC-001.md), [`SEC-002`](./checks/SEC-002.md), [`SEC-003`](./checks/SEC-003.md) |
| **L**east Privilege | Service-Account-Rechte minimal halten | [`SEC-003`](./checks/SEC-003.md), [`SEC-013`](./checks/SEC-013.md) |
| **I**dempotency | Idempotency-Keys + Compensating Actions bei jedem Write | [`ARCH-010`](./checks/ARCH-010.md) |
| **D**efense-in-Depth | Gateway + Auth + Schema + Sandbox + DLP gestapelt | [`SCALE-005`](./checks/SCALE-005.md), [`SEC-018`](./checks/SEC-018.md), [`SEC-023`](./checks/SEC-023.md) |

Wer alle fünf abdeckt, ist gegen ~80% der heute beobachteten Angriffsklassen geschützt. Die übrigen ~20% — primär Prompt-Injection auf Tool-Description-Ebene — sind strukturell ungelöst und brauchen organisatorische Kontrollen (Human-in-the-Loop, Threat Detection, Audit-Reviews).

## Anchor-Demo

> «Erfüllt mein `parlament-mcp`-Server alle 23 Security-Checks für eine Phase-1-Read-only-Anbindung an Stadt-Zürich-Verwaltungsdaten?»

Mit installiertem Slash-Command:

```
> /audit-mcp .
```

Output: Profil-getriebene Auswahl der ~30 anwendbaren Checks aus 93, automatisierte Verifikation aller `automated`/`config_check`/`documentation_check`-Modi, Findings-Stubs für `code_review`/`runtime_test`-Modi, vollständiger Audit-Report nach Template — alles in `<repo>/audits/YYYY-MM-DD-<server-name>/`.

## Standards-Provenance

Die 93 Checks stammen aus zwei kuratierten Best-Practice-Dokumenten plus fünf eigenen Layern (Schweiz-Compliance, Datentreue, Identität, Upstream-Drift, Abhängigkeitsauflösung) in auditierbarer Form. Jeder Check trägt im Frontmatter eine `pdf_ref`-Referenz auf seine Quelle.

| Quelle | Inhalt | Abgeleitete Checks |
|---|---|---|
| **Hauptkatalog** «MCP Server-Entwicklung — Best Practices & Standards» | Architektur, SDK-Patterns, Security, Skalierung, Observability, Human-in-the-Loop | 54 Checks (v0.1–v0.4) |
| **Architektur-Anhang** «Architektur und Sicherheit von MCP-Servern» | Sektion A (Architektur, A1–A9), Sektion B (Sicherheit, B1–B12), Sektion C (Operative Praxis, C1–C4); schliesst u.a. Lethal-Trifecta-, Idempotency- und Egress-Control-Lücken | 14 Checks (v0.5) |
| **Schweiz-Compliance-Layer** | revDSG, EDÖB-Meldepflicht, ISDS Stadt Zürich, OGD-Lizenz-Compliance, Volksschule-spezifische Datenschutz-Anforderungen | 8 Checks (`CH-*`) |
| **Datentreue-Layer** | Scope-Defaults, Recall gegen Ground Truth, Leermenge ≠ Abwesenheit, Query-Syntax. Abgeleitet aus einem realen Portfolio-Vorfall ([termdat-mcp#11](https://github.com/malkreide/termdat-mcp/issues/11)) | 5 Checks (`FID-*`) |
| **Identitäts-Layer** | User-Agent, `__version__`, Manifest-Version, dokumentierte Version — als was sich ein Server nach aussen ausgibt; dazu die Frage, ob das publizierte Artefakt überhaupt noch startet. Abgeleitet aus einem Portfolio-Sweep über 30 Server und aus zwei toten Releases auf dem Index | 7 Checks (`IDENT-*`) |
| **Upstream-Drift-Layer** | Der Vertrag mit der Quelle ändert sich, und nichts bemerkt es: abgeschaffte Endpoints, Fallbacks die den Datensatz austauschen, Assertions die auch der Fehlerfall erfüllt — dazu Prosa im Repo, die dem Code widerspricht. Abgeleitet aus einem realen Portfolio-Vorfall ([meteoswiss-mcp#33](https://github.com/malkreide/meteoswiss-mcp/issues/33), #35, #37) und aus einem CHANGELOG, das Gemergtes als ausstehend führte | 6 Checks (`DRIFT-*`) |
| **Dependency-Layer** | Eine Range ohne Obergrenze überlässt die Wahl der Major-Version dem, der als Nächstes publiziert: Das veröffentlichte Artefakt ändert sich, ohne dass jemand es publiziert. Abgeleitet daraus, dass `mcp` 2.0.0 am 2026-07-28 `mcp.server.fastmcp` entfernte und zwei Releases tötete, an denen nichts falsch war | 1 Check (`DEP-*`) |
| **Operative Praxis** | Test-Strategie, Doku-Standard und Phasenarchitektur aus Anhang C; dazu Audit-Redlichkeit (`OPS-004`) und Pipeline-Ehrlichkeit (`OPS-005`) — beides Eigenbefunde: ein Report, der einen unerklärten Rest mit einer Vermutung schloss ([termdat-mcp#11](https://github.com/malkreide/termdat-mcp/issues/11)), und eine Testsuite, die kein Workflow ausführte ([mcp-continuous-auditor#29](https://github.com/malkreide/mcp-continuous-auditor/pull/29)) | 5 Checks (`OPS-*`) |

## Schnellstart

### Voraussetzungen — Cross-Platform

| Betriebssystem | Voraussetzung |
|---|---|
| Linux / macOS | Python 3.11+, Bash, `git`, `yq` |
| Windows (Git Bash) | Python 3.11+ mit `PYTHONUTF8=1`, Git Bash, `git`, `yq` |

**Windows-User:** Setze die Env-Var `PYTHONUTF8=1` in deinem Profil (oder pro Session), sonst crasht Python beim Schreiben von Umlauten/Emojis:

```powershell
# PowerShell
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")

# Git Bash
echo 'export PYTHONUTF8=1' >> ~/.bashrc
```

Pfad-Helpers für Skill-Scripts liegen unter [`tools/paths.sh`](tools/paths.sh) (Bash) und [`tools/path_utils.py`](tools/path_utils.py) (Python). Sie konvertieren zwischen `/c/Users/foo` (Git Bash) und `C:\Users\foo` (Windows-native, was die Read/Edit/Write-Tools brauchen).

### Als Claude-Code-Slash-Command (`/audit-mcp`)

Der Skill bringt einen Slash-Command mit, der den 6-Schritte-Workflow als Claude-Code-Workflow ausführt — Profil-Load, Applicability-Filter, automatisierte Check-Ausführung, Findings-Generierung und Report-Erstellung in einem Lauf.

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git
cd mcp-audit-skill
./setup-slash-command.sh
```

Das Setup-Script symlinkt `.claude/commands/audit-mcp.md` nach `~/.claude/commands/`, damit `/audit-mcp` global in jeder Claude-Code-Session verfügbar ist.

Verwendung:

```bash
# In einem MCP-Server-Repo oder beliebigen Verzeichnis
claude
```

```
> /audit-mcp .
> /audit-mcp /pfad/zum/server-repo
> /audit-mcp https://github.com/malkreide/zh-education-mcp
```

Output landet in `<repo>/audits/YYYY-MM-DD-<server-name>/` mit:

- `audit-report.md` — Gesamtreport nach Template
- `findings/<check-id>-*.md` — pro Fail/Partial-Check ein Finding
- `raw/<check-id>.txt` — Roh-Output der Bash-Befehle für Audit-Trail

Automatisierungstiefe ist **Standard**: alle `automated`/`config_check`/`documentation_check`-Modi laufen automatisch, `code_review`/`runtime_test`-Modi werden als TODO mit Such-Pattern in den Report geschrieben (kein Pattern-Match-Halluzinieren).

### Portfolio-Batch-Audit (`audit-portfolio.sh`)

Wenn du mehrere MCP-Server in einem Run auditieren willst, nutze das Top-Level-Script `audit-portfolio.sh`. Es liest deine `portfolio.yaml` (Server-Liste mit Profil pro Server), klont jedes Repo, ruft `claude -p` mit dem `/audit-mcp`-Slash-Command non-interactive auf und aggregiert die Findings in eine `portfolio-summary.md`.

```bash
cp portfolio.example.yaml portfolio.yaml
$EDITOR portfolio.yaml          # deine Server-Liste anpassen
./audit-portfolio.sh --dry-run  # Plan verifizieren, kein claude-Call
./audit-portfolio.sh            # echter Run, alle Server sequenziell
./audit-portfolio.sh zh-education-mcp foo-mcp   # Subset
./audit-portfolio.sh --force    # auch heute schon auditierte Server neu
```

`portfolio.yaml` ist `.gitignore`d — committe deine Server-Liste nicht versehentlich. Dependencies: `yq` (Mike Farahs Go-yq oder kislyuks Python-yq + `jq`), `git`, `claude` CLI. Output landet in `portfolio-logs/<datum>/`.

### Notion-Sync (`audit-notion-sync.py`) — bidirektionale Tracker-Integration

Wenn dein Audit-Tracker in Notion lebt, nutze `audit-notion-sync.py` für bidirektionale Synchronisation: Pull generiert `portfolio.yaml` aus dem Tracker, Push schreibt Findings-Anzahl und Audit-Status nach jedem Lauf zurück. Stdlib-only, kein `pip install` nötig.

**Einmaliges Setup:**

1. In Notion: Tracker → `•••` → **Connections** → **+ Add connections** → deine Internal Integration auswählen
2. Im Tracker eine neue Property anlegen: Name `Org-Kontext`, Type `Multi-select`, Optionen `Stadt Zürich`, `Schulamt`, `Volksschule`, `Enterprise` — dann pro Server ankreuzen, was zutrifft
3. Token in deine Shell-RC (niemals committen):
   ```bash
   export NOTION_TOKEN="ntn_..."
   ```
4. Verifizieren:
   ```bash
   python3 audit-notion-sync.py health
   ```

**Verwendung:**

```bash
# Nur Pull (Tracker → portfolio.yaml)
python3 audit-notion-sync.py pull --force
./audit-portfolio.sh

# Oder kombiniert: Pull, Audit, Push in einem Run
./audit-portfolio.sh --from-notion --sync-back
```

Der Pull filtert standardmässig auf Server mit `Audit-Status` ∈ {`Triagiert`, `In Audit`} — `--all` ignoriert den Filter. Der Push setzt `Findings` (number), `Audit-Status` (auf `Findings dokumentiert`) und appendet eine Notiz mit dem Report-Pfad. Formula-Felder (`Risiko-Score`, `Reife-Score`, `Prio`) bleiben unangetastet.

Die DB-ID ist als Default auf `a2736a65-677d-4cf3-9f94-e874f74a1975` (Stadt Zürich Schulamt MCP Audit Tracker) gesetzt; `NOTION_AUDIT_DB_ID` env var überschreibt.

### Als Claude.ai-Skill (manuell)

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git ~/skills/mcp-audit
```

Dann in Claude.ai: `Verwende mcp-audit-Skill für <server-name>`. Der Workflow läuft dann interaktiv ohne Slash-Command-Automatisierung.

## Check-Katalog im Überblick

| Code | Bereich | Quelle | Anzahl | Severity-Profil |
|---|---|---|---:|---|
| `ARCH` | Tool-Design, Annotations, Idempotency, Repo-Struktur, Spec-Versionierung | Hauptkatalog Sec 2 + Anhang A | 13 | 2 critical · 4 high · 7 medium |
| `SDK` | FastMCP, TypeScript, Zod, Lifecycle | Hauptkatalog Sec 3 | 6 | — · 4 high · 2 medium |
| `SEC` | Security (grösste Kategorie) | Hauptkatalog Sec 4 + Anhang B | 24 | 8 critical · 13 high · 3 medium |
| `SCALE` | Transport, Load Balancing, Container, Gateway | Hauptkatalog Sec 5 | 7 | — · 3 high · 4 medium |
| `OBS` | Logging, Errors, SIEM, OpenTelemetry | Hauptkatalog Sec 6 + Anhang B10 | 6 | 1 critical · 2 high · 3 medium |
| `HITL` | Sampling, Human-in-the-Loop | Hauptkatalog Sec 7 | 5 | 2 critical · 2 high · 1 medium |
| `CH` | DSG/EDÖB, ISDS Stadt Zürich, Volksschule | Custom | 8 | 2 critical · 4 high · 2 medium |
| `OPS` | Test-Strategie, Doku-Standard, Phasenarchitektur, Audit-Redlichkeit, Pipeline-Ehrlichkeit | Anhang C + Custom | 5 | — · 4 high · 1 medium |
| `FID` | Datentreue: Scope-Defaults, Recall, Leermengen, Query-Syntax | Custom | 5 | 1 critical · 2 high · 2 medium |
| `IDENT` | Identität: User-Agent, `__version__`, Manifest, Doku-Version, Release-Gap, Gesundheit des Artefakts | Custom | 7 | — · 3 high · 3 medium · 1 low |
| `DRIFT` | Upstream-Vertrag und Repo-Prosa: Endpoint-Drift, Fallback-Semantik, Testgüte, CHANGELOG gegen Code | Custom | 6 | — · 3 high · 3 medium |
| `DEP` | Auflösungsraum des publizierten Artefakts: Obergrenzen, Major-Wechsel | Custom | 1 | — · 1 high |
| **Total** | | | **93** | **16 critical · 45 high · 31 medium · 1 low** |

## Severity-Stufen

| Stufe | Bedeutung | Konsequenz |
|---|---|---|
| `critical` | Sicherheitslücke / Compliance-Bruch | Blockiert Produktion |
| `high` | Architektureller Mangel mit signifikantem Risiko | Im laufenden Sprint fixen |
| `medium` | Best-Practice-Verletzung | Im nächsten Sprint planen |
| `low` | Polish, Optimierung | Backlog |

## Adoptionsstufen

Severity sagt, **wie schlimm** ein Verstoss ist. Die Adoptionsstufe sagt, **ob der Katalog das Portfolio schon darauf festnageln darf**. Ohne die zweite Achse trifft jeder neue Check am Tag des Merges 30+ Server als rote Pipeline — so werden Checks zurückgenommen statt übernommen.

| Stufe | Bedeutung | Konsequenz |
|---|---|---|
| `enforced` | Der Katalog hält das Portfolio daran fest | Ein `fail` auf `critical`/`high` blockiert Production-Readiness |
| `advisory` | Der Check meldet, urteilt aber noch nicht | Finding wird erzeugt, gezählt und mit voller Severity geführt — blockiert aber nicht |

Das Feld ist optional; fehlt es, gilt `enforced`. Von 93 Checks ist genau einer `advisory`: `OPS-005`. `DEP-001` und `DRIFT-006` gingen denselben Weg und sind inzwischen auf `enforced` promoviert — die Brücke soll die meiste Zeit leer sein.

**Advisory versteckt nichts.** Nur das Veto entfällt. Ein Advisory-Finding auf blockierender Severity wird auch bei grünem Verdikt namentlich genannt, damit eine spätere Promotion eine Entscheidung ist und keine Überraschung.

Der Katalog ist autoritativ, nicht die Ergebnisdatei — deshalb `--checks-dir`:

```bash
python tools/aggregate_results.py aggregate verification-results.json \
    --checks-dir checks/ --out summary.json
```

## Audit-Workflow (Kurzform)

1. **Profil laden** — Server-Eigenschaften aus Notion-Audit-Tracker oder via Inferenz aus dem Repo
2. **Katalog laden** — alle 93 Checks parsen
3. **Applicability-Filter** — nur passende Checks selektieren (z.B. stdio-only-Server überspringt OAuth-Checks)
4. **Check-Ausführung** — automatisiert (grep, AST, Config-Scan) oder als Code-Review-TODO pro Check
5. **Findings dokumentieren** — `templates/finding.md`
6. **Audit-Report** — `templates/audit-report.md`

Details siehe [`SKILL.md`](./SKILL.md).

## Positionierung gegenüber verwandten Tools

| Tool | Kategorie | Fokus |
|---|---|---|
| `apisec-inc/mcp-audit` | Code-Scanner | Lokale MCP-Configs (Secrets, Shadow-APIs, AI-BOM, SARIF) |
| `ModelContextProtocol-Security/mcpserver-audit` (CSA) | Tutorial-Tool | Lehrt CWE/AIVSS-Methodik anhand von Beispiel-Servern |
| `qianniuspace/mcp-security-audit` | Dependency-Scanner | npm-Vulnerability-Scan für MCP-Pakete |
| **`malkreide/mcp-audit-skill`** | **Audit-Framework** | **Systematische Prüfung gegen kuratierten Best-Practice-Korpus + CH-Compliance** |

Komplementär nutzbar — keiner der Genannten ersetzt die anderen.

## Verwandte Repos

### Die Skill-Familie

Fünf Skills, ein Bau. Jeder beantwortet eine andere Frage, in der Reihenfolge, in der sie aufkommt — dieser kommt zuletzt:

| Skill | Rolle | Seine Regeln in diesem Katalog |
|---|---|---|
| [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) | Generische Bauanleitung — fremder Skill von Anthropic | — |
| [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | Vorgehen *vor* dem Bau | liefert die Ground Truth, gegen die `FID-002` misst |
| [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill) | Liefert er, was die Quelle hat? | [`FID-001`–`FID-005`](./checks/) |
| [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-transport-hardening-skill) | Kommt er hoch, weist er richtig ab? | [`SDK-006`](./checks/SDK-006.md), [`ARCH-013`](./checks/ARCH-013.md), [`SEC-024`](./checks/SEC-024.md) |
| **`mcp-audit-skill`** | **Dieser Skill:** Prüfung *nach* dem Bau | — |

Zwei der Transport-Hardening-Regeln haben hier kein Gegenstück: die über den
Bind, der die App erreichen muss, und die drei zur Beweisführung (Negativtests,
Mutationstest, Harness-Fallen). Das erste ist eine echte Lücke, das zweite eine
Bereichsgrenze — dieser Katalog prüft, ob eine Kontrolle vorhanden ist, nicht ob
ihr Nachweis trägt.

### Portfolio und Tracker

- [`malkreide` MCP-Server-Portfolio](https://github.com/malkreide?tab=repositories) — die Server, gegen die dieses Skill auditiert wird
- Notion **MCP Audit Tracker** — laufender Status aller Server-Audits (intern)
- Notion **MCP Server Portfolio** — Master-Inventar aller Server (intern)

## Status

**Version:** v1.5.0 — Schweigen ist kein Freispruch. CI auf Ubuntu + Windows × py3.11 + py3.13. Siehe [CHANGELOG.md](./CHANGELOG.md) für die vollständige Release-History.

**Vollständigkeit:**
- ✅ Methodik (`SKILL.md`) und Templates (Finding, Audit-Report)
- ✅ Reference-Summary
- ✅ Check-Katalog: **93 Checks, alle 12 Kategorien vollständig**
- ✅ Slash-Command für Claude Code (`/audit-mcp <repo>`)
- ✅ Portfolio-Batch-Audit (`audit-portfolio.sh` für Multi-Server-Runs)
- ✅ Inventar-Gate (`./audit-portfolio.sh --verify-inventory`) — findet Server, die in `portfolio.yaml` fehlen, inklusive verschachtelter
- ✅ Notion-Sync (`audit-notion-sync.py` für bidirektionale Tracker-Integration)
- ✅ Vollständige Abdeckung beider Standards-Quellen (Hauptkatalog + Architektur-Anhang)

Künftige Erweiterungen kommen aus Real-World-Findings beim Portfolio-Audit, MCP-Spec-Updates oder neuen Compliance-Anforderungen (EU AI Act, Schweizer KI-Gesetz). Versions-Roadmap siehe [`docs/roadmap.md`](./docs/roadmap.md).

## Mitwirken

Korrekturen sind willkommen: ein Check, dessen Pass-Kriterium in der Praxis nicht trennscharf ist, eine Quelle, die sich weiterbewegt hat, ein Remediation-Pfad, der ins Leere führt.

Für neue Checks gilt die Anatomie der bestehenden: eine benannte Quelle, ein Pass-Kriterium, das zwei Auditoren gleich beantworten, ein Remediation-Pfad und ein Aufwands-Indikator. Ein Check ohne Quelle ist eine Meinung — und ein Pass-Kriterium, das Auslegung zulässt, macht den Katalog unreproduzierbar, also genau das, was er verhindern soll.

Besonders willkommen sind ergänzende Compliance-Layer anderer Jurisdiktionen (DSGVO-Spezifika, kantonale Datenschutzgesetze, sektorspezifische Vorgaben) sowie Real-World-Findings aus Portfolio-Audits, die einen bestehenden Check nachschärfen.

Vor einem grösseren Pull Request bitte ein Issue eröffnen, damit die Form vorher geklärt ist.

## Sicherheit

Dieses Repo liefert eine Methodik, Check-Definitionen und Helfer-Scripts — keinen laufenden Server und kein installierbares Paket. Drei Dinge sind beim Betrieb relevant:

**Der Audit-Output enthält fremden Code.** `audit-portfolio.sh` klont die Repos deiner Server-Liste und ruft `claude -p` darauf non-interactive auf; unter `audits/` und `portfolio-logs/` landet Roh-Output der ausgeführten Befehle. Das ist der Audit-Trail und genau so gewollt — aber es kann interne Pfade, Hostnames oder Konfigurationsauszüge der auditierten Server enthalten. Vor dem Veröffentlichen eines Reports durchsehen.

**Zwei Dateien gehören nie in einen Commit.** `portfolio.yaml` ist `.gitignore`d, weil eine Server-Liste ein Inventar ist. Der `NOTION_TOKEN` gehört in die Shell-RC, nicht ins Repo — `audit-notion-sync.py` liest ihn ausschliesslich aus der Umgebung.

**Ein grünes Audit ist keine Sicherheitszusage.** Der Katalog prüft gegen veröffentlichte Best Practices, nicht gegen dein Bedrohungsmodell; er ist kein Vulnerability-Scanner. Die verbleibende Klasse — Prompt-Injection auf Tool-Description-Ebene — ist strukturell ungelöst und braucht organisatorische Kontrollen, wie oben unter SOLID beschrieben.

Fehler in einem Check gefunden, oder ein Pass-Kriterium, das falsch trennt? Bitte ein Issue eröffnen.

## Lizenz

MIT — siehe [`LICENSE`](./LICENSE).

## Kontext

Entwickelt im Rahmen des Swiss Public Data MCP Portfolio. Frei verwendbar von anderen Verwaltungen, Forschungsinstituten oder Privatpersonen, die MCP-Server systematisch auditieren wollen.

## Autor

[Hayal Oezkan](https://github.com/malkreide)
