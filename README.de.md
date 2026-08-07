# mcp-audit-skill

> Claude-Skill für systematische Audits von MCP-Servern gegen einen kuratierten Best-Practice-Standards-Korpus. **117 Checks**, 12 Kategorien, auf doppelter Spec-Baseline (`2025-11-25` und `2026-07-28`), mit Schweiz-Compliance-Layer für die öffentliche Verwaltung und Datentreue-Layer für Datenquellen-Server.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Checks: 117](https://img.shields.io/badge/Checks-117-blue.svg)](./checks/)
[![Coverage: A1–A9, B1–B12, C1–C4](https://img.shields.io/badge/Best--Practice%20Coverage-A1%E2%80%93A9%2C%20B1%E2%80%93B12%2C%20C1%E2%80%93C4-success)](./CHANGELOG.md)
[![MCP Spec: 2025-11-25 + 2026-07-28](https://img.shields.io/badge/MCP%20Spec-2025--11--25%20%2B%202026--07--28-orange)](https://modelcontextprotocol.io/specification/)

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

Output: Profil-getriebene Auswahl der ~30 anwendbaren Checks aus 117, automatisierte Verifikation aller `automated`/`config_check`/`documentation_check`-Modi, Findings-Stubs für `code_review`/`runtime_test`-Modi, vollständiger Audit-Report nach Template — alles in `<repo>/audits/YYYY-MM-DD-<server-name>/`.

## Standards-Provenance

Die 117 Checks stammen aus zwei kuratierten Best-Practice-Dokumenten plus fünf eigenen Layern (Schweiz-Compliance, Datentreue, Identität, Upstream-Drift, Abhängigkeitsauflösung) in auditierbarer Form. Jeder Check trägt im Frontmatter eine `pdf_ref`-Referenz auf seine Quelle.

| Quelle | Inhalt | Abgeleitete Checks |
|---|---|---|
| **Hauptkatalog** «MCP Server-Entwicklung — Best Practices & Standards» | Architektur, SDK-Patterns, Security, Skalierung, Observability, Human-in-the-Loop | 54 Checks (v0.1–v0.4) |
| **Architektur-Anhang** «Architektur und Sicherheit von MCP-Servern» | Sektion A (Architektur, A1–A9), Sektion B (Sicherheit, B1–B12), Sektion C (Operative Praxis, C1–C4); schliesst u.a. Lethal-Trifecta-, Idempotency- und Egress-Control-Lücken | 14 Checks (v0.5) |
| **Schweiz-Compliance-Layer** | revDSG, EDÖB-Meldepflicht, ISDS Stadt Zürich, OGD-Lizenz-Compliance, Volksschule-spezifische Datenschutz-Anforderungen | 8 Checks (`CH-*`) |
| **Datentreue-Layer** | Scope-Defaults, Recall gegen Ground Truth, Leermenge ≠ Abwesenheit, Query-Syntax, Antwortstruktur bestätigen bevor gezählt wird. Abgeleitet aus einem realen Portfolio-Vorfall ([termdat-mcp#11](https://github.com/malkreide/termdat-mcp/issues/11)) und aus einer Registry-Abfrage, die eine Ebene über den Feldern las | 6 Checks (`FID-*`) |
| **Identitäts-Layer** | User-Agent, `__version__`, Manifest-Version, dokumentierte Version — als was sich ein Server nach aussen ausgibt; dazu die Frage, ob das publizierte Artefakt überhaupt noch startet. Abgeleitet aus einem Portfolio-Sweep über 30 Server und aus zwei toten Releases auf dem Index | 7 Checks (`IDENT-*`) |
| **Upstream-Drift-Layer** | Der Vertrag mit der Quelle ändert sich, und nichts bemerkt es: abgeschaffte Endpoints, Fallbacks die den Datensatz austauschen, Assertions die auch der Fehlerfall erfüllt — dazu Prosa im Repo, die dem Code widerspricht. Abgeleitet aus einem realen Portfolio-Vorfall ([meteoswiss-mcp#33](https://github.com/malkreide/meteoswiss-mcp/issues/33), #35, #37) und aus einem CHANGELOG, das Gemergtes als ausstehend führte | 7 Checks (`DRIFT-*`) |
| **Dependency-Layer** | Eine Range ohne Obergrenze überlässt die Wahl der Major-Version dem, der als Nächstes publiziert: Das veröffentlichte Artefakt ändert sich, ohne dass jemand es publiziert. Abgeleitet daraus, dass `mcp` 2.0.0 am 2026-07-28 `mcp.server.fastmcp` entfernte und zwei Releases tötete, an denen nichts falsch war | 1 Check (`DEP-*`) |
| **Architektur** | Tool-Design, Annotations, Idempotency und Repo-Struktur aus Hauptkatalog Sec 2 und Anhang A; dazu die Retry-Politik gegenüber der Quelle (`ARCH-014`) — Eigenbefund: zum Zeitpunkt der Erhebung wiederholten von elf Portfolio-Servern acht, keiner las `Retry-After` und keiner streute seinen Backoff; heute erfüllen alle elf den Check; dazu die sieben Stateless-Checks aus der Spec-Migration; dazu die Versionsquelle (`ARCH-022`) — Eigenbefund: ein Submodul, das `__version__` aus dem Paket-Root zurückliest und allein durch die Zeilenreihenfolge in `__init__.py` zusammenhält, gemessen kalt und warm in getrennten Interpretern | 22 Checks (`ARCH-*`) |
| **Spec-Migrations-Layer** (`2026-07-28`) | Zustandslosigkeit, `server/discover`, handle-basierter Zustand, `resultType`, abgekündigte Roots/Sampling/Logging, `ttlMs`/`cacheScope`, Extensions, Pflichtheader `Mcp-Method`/`Mcp-Name`, Frist für Legacy-SSE, `subscriptions/listen`, MRTR, RFC-9207-`iss`, CIMD statt DCR, `x-mcp-header`. Jeder Check nennt seine SEP-Nummer im Frontmatter | 14 Checks über `ARCH`, `SCALE`, `HITL`, `SEC` |
| **Security** | Bedrohungsmodell, Secrets, SSRF, DNS-Pinning, Auth und die eingehende Host-Allow-List aus Hauptkatalog Sec 4 und Anhang B, dazu drei Checks aus der Spec-Migration; dazu die Fehler-Taxonomie des Egress-Guards (`SEC-028`) — Eigenbefund: ein Exception-Typ für Policy-Verstoss und transienten Auflösungsfehler, womit die Retry-Politik die beiden nicht unterscheiden kann und dem Aufrufer die falsche Ursache genannt wird (`zh-education-mcp`, 2026-08-03) | 28 Checks (`SEC-*`) |
| **Observability** | Logging, Fehler-Klassifikation, SIEM und Tracing aus Hauptkatalog Sec 6 und Anhang B10; dazu Fehler-Diagnostizierbarkeit (`OBS-007`) — Eigenbefund: ein Fehler, nach aussen korrekt maskiert, nach innen mit nichts dahinter ([swiss-efv-mcp#16](https://github.com/malkreide/swiss-efv-mcp/pull/16)); dazu der Bereitschaftsmarker (`OBS-008`) — Eigenbefund: von 42 veröffentlichten Servern sagen 15 in sechs Sekunden bei geschlossenem stdin überhaupt nichts, womit kein Werkzeug einen laufenden Server von einem beim Import gestorbenen unterscheiden kann | 8 Checks (`OBS-*`) |
| **Operative Praxis** | Test-Strategie, Doku-Standard und Phasenarchitektur aus Anhang C; dazu Audit-Redlichkeit (`OPS-004`), Pipeline-Ehrlichkeit (`OPS-005`) ausführbare Anleitungen (`OPS-007`) und überhaupt prüfbare Guards (`OPS-008`) — Eigenbefunde: ein Report, der einen unerklärten Rest mit einer Vermutung schloss ([termdat-mcp#11](https://github.com/malkreide/termdat-mcp/issues/11)), eine Testsuite, die kein Workflow ausführte ([mcp-continuous-auditor#29](https://github.com/malkreide/mcp-continuous-auditor/pull/29)), und eine Setup-Anleitung, die in PowerShell ein Syntaxfehler ist | 8 Checks (`OPS-*`) |

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
2. Im Tracker drei Properties anlegen. Jede hat einen Default, auf den der Sync zurückfällt — eine fehlende Spalte scheitert also nicht, sie entscheidet still etwas für dich:

   | Property | Type | Optionen | Was der Default kostet |
   |---|---|---|---|
   | `Org-Kontext` | Multi-select | `Stadt Zürich`, `Schulamt`, `Volksschule`, `Enterprise` | Alle Org-Flags `False` — die meisten CH-Compliance-Checks fallen weg |
   | `MCP-Spec-Version` | Select | `2025-11-25`, `2026-07-28` | Jeder Server wird gegen die `2025-11-25`-Hälfte des Katalogs geprüft |
   | `SDK-Sprache` | Select | `Python`, `TypeScript` | Jeder Server gilt als Python — `SDK-001…006` und `IDENT-005` messen das falsche SDK |

   Danach pro Server ausfüllen. Eine **leere Zelle** verhält sich genau wie eine fehlende Spalte; `pull` nennt die betroffenen Server namentlich, damit es nicht unbemerkt durchgeht.

3. Token in deine Shell-RC (niemals committen):

   ```bash
   # bash / zsh
   export NOTION_TOKEN="ntn_..."
   ```

   ```powershell
   # PowerShell — nur diese Session
   $env:NOTION_TOKEN = "ntn_..."
   # PowerShell — dauerhaft, wirkt im nächsten Terminal
   [Environment]::SetEnvironmentVariable("NOTION_TOKEN", "ntn_...", "User")
   ```

4. Verifizieren — die Ausgabe muss für alle drei Properties `present ✓` zeigen:

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
| `ARCH` | Tool-Design, Annotations, Idempotency, Retry-Politik, Repo-Struktur, Versionsquelle, Spec-Versionierung, Stateless-Konformität, Handles, Extensions | Hauptkatalog Sec 2 + Anhang A + Custom + Spec 2026-07-28 | 22 | 2 critical · 8 high · 12 medium |
| `SDK` | FastMCP, TypeScript, Zod, Lifecycle | Hauptkatalog Sec 3 | 6 | — · 4 high · 2 medium |
| `SEC` | Security (grösste Kategorie) | Hauptkatalog Sec 4 + Anhang B + Spec 2026-07-28 | 28 | 8 critical · 17 high · 3 medium |
| `SCALE` | Transport, Load Balancing, Container, Gateway, Pflichtheader, Abkündigungsfristen | Hauptkatalog Sec 5 + Spec 2026-07-28 | 10 | — · 5 high · 5 medium |
| `OBS` | Logging, Errors, SIEM, OpenTelemetry, Bereitschaftsmarker | Hauptkatalog Sec 6 + Anhang B10 + Custom | 8 | 1 critical · 2 high · 5 medium |
| `HITL` | Sampling, Human-in-the-Loop, Multi Round-Trip Requests | Hauptkatalog Sec 7 + Spec 2026-07-28 | 6 | 2 critical · 3 high · 1 medium |
| `CH` | DSG/EDÖB, ISDS Stadt Zürich, Volksschule | Custom | 8 | 2 critical · 4 high · 2 medium |
| `OPS` | Test-Strategie, Doku-Standard, Phasenarchitektur, Audit-Redlichkeit, Pipeline-Ehrlichkeit, reproduzierbare Urteile, ausführbare Anleitungen, prüfbare Guards | Anhang C + Custom | 8 | — · 5 high · 3 medium |
| `FID` | Datentreue: Scope-Defaults, Recall, Leermengen, Query-Syntax, Antwortstruktur | Custom | 6 | 1 critical · 3 high · 2 medium |
| `IDENT` | Identität: User-Agent, `__version__`, Manifest, Doku-Version, Release-Gap, Gesundheit des Artefakts | Custom | 7 | — · 3 high · 3 medium · 1 low |
| `DRIFT` | Upstream-Vertrag und Repo-Prosa: Endpoint-Drift, Fallback-Semantik, Testgüte, CHANGELOG gegen Code, Feldnamen-Schreibweise | Custom | 7 | — · 4 high · 3 medium |
| `DEP` | Auflösungsraum des publizierten Artefakts: Obergrenzen, Major-Wechsel | Custom | 1 | — · 1 high |
| **Total** | | | **117** | **16 critical · 59 high · 41 medium · 1 low** |

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

Das Feld ist optional; fehlt es, gilt `enforced`. Von 117 Checks sind genau zweiundzwanzig `advisory`: `ARCH-022`, `DRIFT-007`, `FID-006`, `OBS-008`, `OPS-005`, `OPS-006`, `OPS-007`, `OPS-008` — dazu die vierzehn Migrations-Checks `ARCH-015`, `ARCH-016`, `ARCH-017`, `ARCH-018`, `ARCH-019`, `ARCH-020`, `ARCH-021`, `HITL-006`, `SCALE-008`, `SCALE-009`, `SCALE-010`, `SEC-025`, `SEC-026` und `SEC-027`. `DEP-001`, `DRIFT-006`, `OBS-007` und `ARCH-014` gingen denselben Weg und sind inzwischen auf `enforced` promoviert — die Brücke soll eine Handvoll neuer Checks tragen, nicht volllaufen.

**Neunzehn sind nicht neunzehn gewöhnliche Checks auf der Brücke.** Vierzehn davon sind die Migrations-Kohorte, die geschlossen abgeht; fünf sind gewöhnlich, und vier Checks sind bereits auf `enforced` hinübergegangen. Das ist der Mechanismus bei der Arbeit, nicht die volllaufende Brücke — und der Wächter misst es genauso: Die Quote in `tests/test_adoption_stage.py` zählt den Rest ohne die Kohorte.

Die vierzehn kamen gemeinsam auf die Brücke, weil sie ein Protokoll messen, auf das das Portfolio noch nicht migriert ist: Die Wellen A–D laufen erst an. Die Verteilung je Server steht in `portfolio.json` (`mcp_spec_version`, `migration_wave`), nicht hier — diese Datei nennt den Grund, keine Zahl, die sie nicht belegen kann. Sie verlassen `advisory` als Abschluss-Gate von Welle D, nicht einzeln.

`FID-006` gehört nicht zu dieser Kohorte und geht nicht mit ihr ab. Er ist aus dem gewöhnlichen Grund `advisory`: Sein Fail-Pattern — `payload.get("servers", [])` — ist das normale Idiom, `enforced` auf `high` am Merge-Tag hätte also fast jeden Datenquellen-Server rot gefärbt, für eine Eigenschaft, nach der nie jemand gefragt hat. Er verlässt `advisory` nach dem ersten Portfolio-Durchlauf, der zeigt, wie viele Server die Antwortstruktur bestätigen.

**Advisory versteckt nichts.** Nur das Veto entfällt. Ein Advisory-Finding auf blockierender Severity wird auch bei grünem Verdikt namentlich genannt, damit eine spätere Promotion eine Entscheidung ist und keine Überraschung.

Der Katalog ist autoritativ, nicht die Ergebnisdatei — deshalb `--checks-dir`:

```bash
python tools/aggregate_results.py aggregate verification-results.json \
    --checks-dir checks/ --out summary.json
```

## Audit-Workflow (Kurzform)

1. **Profil laden** — Server-Eigenschaften aus Notion-Audit-Tracker oder via Inferenz aus dem Repo
2. **Katalog laden** — alle 117 Checks parsen
3. **Applicability-Filter** — nur passende Checks selektieren (z.B. stdio-only-Server überspringt OAuth-Checks)
4. **Check-Ausführung** — automatisiert (grep, AST, Config-Scan) oder als Code-Review-TODO pro Check
5. **Findings dokumentieren** — `templates/finding.md`
6. **Audit-Report** — `templates/audit-report.md`

Details siehe [`SKILL.md`](./SKILL.md).

## Woran ein Lauf verankert ist

Ein Ergebnis ist nur dann reproduzierbar, wenn beides festgehalten ist: der Massstab und das Gemessene.

| Anker | Wo | Was ohne ihn kaputtgeht |
|---|---|---|
| `catalog_hash` | `audit-meta.json` | Niemand kann sagen, welcher Katalog das Urteil erzeugt hat |
| `target_sha` | `audit-meta.json`, via `audit_init.py init --target-repo` | Ein Commit mitten im Lauf teilt den Report: Die früheren Checks beschreiben einen Baum, die späteren einen anderen, und die Mischung wird als ein Urteil präsentiert |

Beide werden vor dem Report erneut geprüft. `audit_init.py verify-target <run>` und das Pflicht-Gate `aggregate_results.py validate <run>` schlagen bei bewegtem Ziel fehl; `aggregate ... --previous <vorlauf>` hält fest, ob beide Läufe überhaupt denselben Katalog-Stand hatten.

**Wo sie abweichen, wird die Trendlinie verweigert statt korrigiert.** Zwei Audits desselben Servers sind nur dann ein Trend, wenn sie mit demselben Massstab gemessen wurden. Sonst ist «30 pass / 4 fail / 2 partial → x/y/z» nicht eine Differenz, sondern zwei verschiedene Messungen mit einem Pfeil dazwischen — im Lauf, aus dem diese Regel stammt, hätte der Pfeil einen Katalog von 36 gegen einen von 54 gespannt. Es gibt keine richtige Art, eine über einen Katalog gezählte Zahl von einer über einen anderen gezählten abzuziehen, und eine Fussnote überlebt das erste Zitieren nicht.

## Status-Werte

`pass`, `fail`, `partial`, `not_verified`, `todo`, `n/a` — siehe [`docs/verification-results-schema.md`](./docs/verification-results-schema.md).

`not_verified` ist der eine, der hier eine Erwähnung verdient. `OPS-004` verlangt ihn, seit der Check geschrieben wurde — ein `pass` beruht auf einem positiven Beleg, nicht auf der Abwesenheit eines Negativbelegs —, während das Schema den Wert nicht kannte: Wer die Regel befolgen wollte, bekam einen Schema-Fehler und trug am Ende `pass` ein, genau das Ergebnis, das der Check verbietet. Er hat jetzt einen eigenen Zähler und wird nirgends zu den bestandenen Checks addiert. Er blockiert kein Release, steht aber neben dem Urteil: Ein grünes Ergebnis über eine grosse unverifizierte Menge ist eine andere Behauptung als ein grünes Ergebnis über keine.

## Vergleiche verweigern leere Eingaben

Jeder Vergleichs-Helfer läuft über [`tools/compare_guard.py`](./tools/compare_guard.py) und wirft, statt zwei leere Mengen zu vergleichen. Ein Applicability-Diff meldete einmal «0 == 0, identisch» — beide Seiten hatten wegen eines falschen Pfads nichts geparst. Die Arithmetik stimmte, alles übrige nicht.

Das ist schlimmer als kein Vergleich. Ohne einen bleibt die Frage offen und wird irgendwann beantwortet; mit einem schliesst eine grüne Zeile sie mit Belegen, die nie erhoben wurden. Wo eine leere Seite tatsächlich die erwartete Antwort ist, sagt `--allow-empty` das ausdrücklich.

## Positionierung gegenüber verwandten Tools

| Tool | Kategorie | Fokus |
|---|---|---|
| `apisec-inc/mcp-audit` | Code-Scanner | Lokale MCP-Configs (Secrets, Shadow-APIs, AI-BOM, SARIF) |
| `ModelContextProtocol-Security/mcpserver-audit` (CSA) | Tutorial-Tool | Lehrt CWE/AIVSS-Methodik anhand von Beispiel-Servern |
| `qianniuspace/mcp-security-audit` | Dependency-Scanner | npm-Vulnerability-Scan für MCP-Pakete |
| **`malkreide/mcp-audit-skill`** | **Audit-Framework** | **Systematische Prüfung gegen kuratierten Best-Practice-Korpus + CH-Compliance** |

Komplementär nutzbar — keiner der Genannten ersetzt die anderen.

## Verwandte Repos

### Die MCP-Qualitätskette

Fünf Repos, ein Lebenszyklus. Jedes beantwortet eine andere Frage, in der Reihenfolge, in der sie aufkommt — dieses kommt als viertes von fünf. Das gemeinsame GitHub-Topic ist [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain) und listet alle fünf auf einer Seite.

| Phase | Repo | Seine Regeln in diesem Katalog |
|---|---|---|
| vor dem Bau | [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | liefert die Ground Truth, gegen die `FID-002` misst |
| im Bau | [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill) | [`FID-001`–`FID-006`](./checks/) |
| im Bau | [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-transport-hardening-skill) | [`SDK-006`](./checks/SDK-006.md) + [`DEP-001`](./checks/DEP-001.md), [`ARCH-013`](./checks/ARCH-013.md), [`SEC-024`](./checks/SEC-024.md); seit seiner v2.0.0 zusätzlich [`ARCH-015`](./checks/ARCH-015.md)–[`ARCH-017`](./checks/ARCH-017.md), [`SCALE-008`](./checks/SCALE-008.md), [`SCALE-009`](./checks/SCALE-009.md)/[`SCALE-010`](./checks/SCALE-010.md), [`HITL-006`](./checks/HITL-006.md), [`SEC-025`](./checks/SEC-025.md)/[`SEC-026`](./checks/SEC-026.md) |
| nach dem Bau | **`mcp-audit-skill`** | **Dieser Skill** — der Katalog selbst |
| im Betrieb | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | der Vorfall hinter [`OPS-005`](./checks/OPS-005.md) — eine Testsuite, die kein Workflow je ausgeführt hat ([#29](https://github.com/malkreide/mcp-continuous-auditor/pull/29)) |

Daneben, nicht Teil der Kette: [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) — generische Bauanleitung von Anthropic, wird ergänzt und nicht ersetzt. Fremdes Repo, kann das Topic nicht tragen.

Die Mitgliedschaft steht an einer Stelle: [`docs/quality-chain.json`](./docs/quality-chain.json). [`tools/check_quality_chain.py`](./tools/check_quality_chain.py) prüft wöchentlich, ob alle fünf das Topic auf GitHub tatsächlich tragen — Metadaten, die keine Arbeitskopie testen kann, und genau deshalb hatten die fünf bis zum ersten Hinsehen kein einziges Topic gemeinsam.

Jener Skill ist mit seiner v2.0.0 auf zwölf Regeln gegangen, entlang der Spec
`2026-07-28` — die beiden Seiten überlappen sich damit fast überall. Drei der
zwölf haben hier weiterhin kein Gegenstück: die über den Bind, der die App
erreichen muss — `SEC-016` sieht danach aus und ist der umgekehrte Fall, ein
*unbeabsichtigtes* `0.0.0.0` —, und zwei der drei zur Beweisführung,
Mutationstest und Harness-Fallen. Eine vierte, die Regel über Negativtests, ist
nur teilweise abgedeckt: `DRIFT-003` fängt die Klasse, einen Test der aus dem
falschen Grund besteht, aber nicht den Transportfall.

Das erste ist eine echte Lücke, der Rest eine Bereichsgrenze. Jener Skill sagt,
wie man eine Kontrolle verdrahtet und woran man sieht, dass sie trägt; dieser
Katalog prüft, ob sie da ist.

### Portfolio und Tracker

- [`malkreide` MCP-Server-Portfolio](https://github.com/malkreide?tab=repositories) — die Server, gegen die dieses Skill auditiert wird
- Notion **MCP Audit Tracker** — laufender Status aller Server-Audits (intern)
- Notion **MCP Server Portfolio** — Master-Inventar aller Server (intern)

## Status

**Version:** v2.2.0 — Plausibel, und über die falsche Sache. CI auf Ubuntu + Windows × py3.11 + py3.13. Siehe [CHANGELOG.md](./CHANGELOG.md) für die vollständige Release-History.

**Vollständigkeit:**
- ✅ Methodik (`SKILL.md`) und Templates (Finding, Audit-Report)
- ✅ Reference-Summary
- ✅ Check-Katalog: **117 Checks, alle 12 Kategorien vollständig**
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

### Lokales Setup

Die Python-Helfer werden mit [Ruff](https://docs.astral.sh/ruff/) gelintet und formatiert. Einmalig pro Clone:

```
pip install pre-commit
pre-commit install
```

Die Hooks aus `.pre-commit-config.yaml` spiegeln den `lint`-Workflow — was lokal durchkommt, kommt auch in der CI durch. Zwei Details, die man kennen sollte:

- Der Hook nutzt Ruff in der Version, die in `.pre-commit-config.yaml` gepinnt ist, in einer eigenen isolierten Umgebung — nicht das lokal installierte Ruff. Dieser Pin und der `ruff==…`-Pin in `.github/workflows/lint.yml` müssen übereinstimmen; `tools/check_ruff_pin.py` erzwingt das, im Hook wie in der CI.
- `ruff format` formatiert die Dateien direkt um und lässt den Commit dann fehlschlagen. Die umformatierten Dateien stagen und erneut committen; `ruff check` meldet nur.

Alles über den ganzen Baum laufen lassen, ohne zu committen:

```bash
pre-commit run --all-files
pytest tests/ -q
```

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
