---
name: mcp-audit
description: Reproduzierbares Audit von MCP-Servern gegen einen versionierten Best-Practice-Katalog. Verwende diesen Skill wenn der User (1) einen MCP-Server gegen Best Practices prüfen will, (2) Sicherheitsfindings für einen Server dokumentieren möchte, (3) den MCP Audit Tracker (Notion) abarbeitet, (4) fragt «ist mein Server sicher / production-ready / standard-konform», (5) den Begriff «Audit», «Findings», «Compliance-Check», «Best Practice»  im MCP-Kontext erwähnt, (6) einen Refactoring-Plan für einen bestehenden Server erstellt, oder (7) für mehrere Server einen vergleichenden Audit-Report erstellen möchte. Auch bei allgemeinen Aussagen wie «ist der Server gut gebaut?», «was muss ich noch fixen?», «entspricht das den Standards?» diesen Skill anwenden.
---

# MCP Audit — Standardisiertes Audit-Vorgehen

Dieser Skill kodiert ein reproduzierbares Audit-Verfahren für MCP-Server gegen den im Anhang dokumentierten Best-Practice-Katalog (PDF-Quelle, ~50 Checks in sieben Kategorien). Ziel: bei 30+ Servern im Portfolio dieselbe Methodik anwenden, ohne dass der menschliche Auditor (oder Claude) bei jedem Server das PDF neu interpretiert.

**Das Mantra in drei Zeilen:**

1. **Profil zuerst, Checks danach** — applicability filtert alles
2. **Evidenz schlägt Vermutung** — jeder Befund braucht Code-Stelle oder konkretes Verhalten
3. **Severity ohne Mitleid** — `critical` blockiert Produktion, Punkt

Jeder Audit folgt sechs Schritten in dieser Reihenfolge. Abweichungen sind möglich, müssen aber im Audit-Report dokumentiert werden.

---

## Schritt 0: Umgebung vorbereiten

Bevor irgendein Schritt beginnt, müssen Cross-Platform-Voraussetzungen erfüllt sein. Diese Sektion existiert, weil bei realen Audit-Läufen auf Windows wiederholt UTF-8- und Pfad-Probleme aufgetreten sind.

### 0.1 UTF-8 für Python

Auf Windows defaultet Python stdout/stderr zu `cp1252` und crasht bei Emojis oder Umlauten. Vor jedem Python-Snippet:

```bash
# Bash/PowerShell — vor Python-Aufrufen exportieren:
export PYTHONUTF8=1            # Bash
$env:PYTHONUTF8 = "1"          # PowerShell
```

Oder im Python-Code direkt:

```python
from tools.path_utils import force_utf8_stdio
force_utf8_stdio()   # idempotent, sicher mehrfach aufzurufen
```

### 0.2 Pfad-Konventionen

| Tool | Erwartetes Pfad-Format |
|---|---|
| Bash (`cat`, `grep`, `ls`) | POSIX (`/c/Users/foo`) |
| Read / Edit / Write | OS-native (`C:\Users\foo` auf Windows) |
| Python `pathlib.Path` | beides, aber konsistent halten |

Helper im Repo:

```bash
# Bash — sourceable
source tools/paths.sh
native_path=$(to_native_path "/c/Users/foo")    # → C:\Users\foo auf Windows
posix_path=$(to_posix_path "C:\\Users\\foo")    # → /c/Users/foo
```

```python
# Python
from tools.path_utils import to_native_path, to_posix_path, is_windows
read_path = to_native_path(skill_base)   # für Read-Tool-Aufrufe
```

### 0.3 Inline-Heredocs sind verboten

Inline-`python3 << 'PYEOF'`-Blöcke crashen auf Windows Git Bash regelmässig durch Quoting (Issue #11, real beobachtet im srgssr-Audit). Für jede nicht-triviale Operation existiert ein dediziertes Helper-Script unter `tools/`. **Verwende diese, schreibe niemals Inline-Python während eines Audits:**

| Aufgabe | Helper-Script |
|---|---|
| Run-ID + Output-Dir + audit-meta.json initialisieren | `python tools/audit_init.py init <server> --base-dir audits/ --catalog-dir checks/` |
| Profil-Validierung (Placeholder/Schema-Gate) | `python tools/validate_profile.py path/to/profile.yaml` |
| Catalog parsen (Frontmatter aller `*.md`) | `python tools/parse_catalog.py --format json` |
| Catalog vs. Manifest validieren | `python tools/parse_catalog.py --format manifest-check` |
| `applies_when` evaluieren | `python tools/eval_applicability.py catalog profile.yaml` |
| Verification-Results aggregieren | `python tools/aggregate_results.py aggregate results.json --out summary.json` |
| Findings-Set vs. Disk validieren | `python tools/aggregate_results.py validate <audit_dir>` |
| Audit-Report generieren | `python tools/build_report.py <audit_dir>` |
| Task-Agent-Output verifizieren | `python tools/verify_raw_outputs.py raw/ --expected-ids ID1,ID2` |
| Task-Agent-Run loggen | `python tools/agent_run_log.py log --meta-path audit-meta.json ...` |
| Pfad zu Native/POSIX konvertieren | `python tools/path_utils.py to-native <path>` |

Wenn ein Audit ein Snippet braucht das hier nicht abgedeckt ist: erst Issue im Skill-Repo öffnen, dann Helper-Script bauen, dann verwenden. **Inline-Heredoc ist der Anti-Pattern, der nicht-reproduzierbare Audits erzeugt.**

### 0.4 Run-ID + Audit-Meta initialisieren (verbindlich seit Issue #15)

Niemals `date +%Y-%m-%d` für den Output-Verzeichnisnamen — das hat im ersten Audit zu Drift zwischen UTC-Container und lokalem Kalendertag geführt (`2026-04-30` statt `2026-05-01`). Stattdessen:

```bash
# Erzeugt Output-Dir mit ISO-Timestamp + Timezone-Offset, schreibt
# initiale audit-meta.json mit Skill-Version + Catalog-Hash.
python "$SKILL_BASE/tools/audit_init.py" init "$SERVER_NAME" \
    --base-dir "$TARGET/audits/" \
    --skill-version "0.9.x" \
    --catalog-dir "$SKILL_BASE/checks/"
# Output (JSON): { "run_id": "2026-05-02T091245-Z-srgssr-mcp", "output_dir": "...", "meta_path": "..." }
```

Run-ID-Format: `YYYY-MM-DDTHHMMSS-<offset>-<server>`, wobei `<offset>` `Z` (UTC) oder `+HHMM`/`-HHMM` ist. Bei Sekunden-genauer Kollision (Re-Audit unmittelbar danach) wird das Verzeichnis mit `-2`, `-3`, ... gesuffixt; die Run-ID selbst bleibt identisch.

Die initiale `audit-meta.json` enthält:
- `server_name`, `run_id`, `started_at` (ISO mit TZ-Suffix), `timezone_offset`
- `skill_version`, `catalog_hash` (SHA-256 aller `checks/*.md` + `MANIFEST.txt`), `catalog_dir`
- Leeres `agent_runs`-Array (wird in Step 4 von `agent_run_log.py` befüllt)

Der `catalog_hash` ist der Reproduzierbarkeits-Anker: jeder Re-Audit kann verifizieren, dass derselbe Katalog-Stand verwendet wurde.

---

## Schritt 1: Profil laden

**Ziel:** Den Server-Kontext aus dem Notion MCP Audit Tracker (DB-ID `a2736a65-677d-4cf3-9f94-e874f74a1975`) holen, damit nachfolgende Schritte die richtigen Checks filtern können.

### 1.1 Pflichtfelder aus dem Tracker

Bevor ein Audit beginnt, müssen diese Felder in der Audit-Tracker-Karte gesetzt sein:

| Feld | Werte | Verwendung im Audit |
|---|---|---|
| `Transport` | `stdio-only` / `dual` / `HTTP/SSE` | filtert Netzwerk-Checks |
| `Auth-Modell` | `none` / `API-Key` / `OAuth-Proxy` | filtert OAuth-Checks |
| `Datenklasse` | `Public Open Data` / `Verwaltungsdaten` / `PII` | filtert PII-Checks und CH-Compliance |
| `Schreibzugriff` | `read-only` / `write-capable` | filtert HITL-Checks |
| `Deployment` | `local-stdio` / `Railway` / `Render` / `andere` | filtert Cloud-Checks |
| `Repo URL` | GitHub-URL | für Code-Review-Schritte |

Wenn ein Pflichtfeld fehlt, wird der Audit gestoppt und der User aufgefordert, das Feld zu füllen. **Audits mit unvollständigem Profil sind wertlos** — applicability wird falsch berechnet, die Findings werden unverlässlich.

### 1.2 Profil-Notation für interne Verwendung

Während des Audits arbeitet Claude mit einem konsolidierten Profil-Objekt:

```yaml
profile:
  name: zurich-opendata-mcp
  repo: https://github.com/malkreide/zurich-opendata-mcp
  transport: dual
  auth_model: none
  data_class: Public Open Data
  write_capable: false              # bool — kanonisches Feld (siehe Migration unten)
  deployment: [local-stdio, Railway]
  is_cloud_deployed: true           # derived: true iff deployment hat irgendwas ausser local-stdio (siehe Issue #16)
  prio: 14  # aus Tracker-Formel
```

Dieses Profil ist die **einzige Wahrheit** für `applies_when`-Auswertung in Schritt 3.

**Schema-Hinweis (seit Issue #13):** Das kanonische Profil-Feld ist `write_capable: bool`. Das frühere `write_access: "read-only" | "write-capable"` (Enum-String) wurde abgelöst. Der Notion-Tracker behält das `Schreibzugriff`-Select-Feld zur besseren Lesbarkeit; `audit-notion-sync.py` mappt es beim `pull` automatisch auf `write_capable: bool`. Profile mit Legacy-Feld `write_access` führen beim Evaluator zu `UnknownFieldError` — das ist beabsichtigt (siehe `docs/applies-when-dsl.md` "loud failure"-Prinzip).

### 1.3 Validation-Gate (verbindlich seit Issue #14)

Bevor Step 2 startet, MUSS das Profil gegen Placeholder und Schema-Lücken geprüft werden. Im ersten realen Audit hatte der User versehentlich das Template mit `...`-Werten reingepastet — Claude hat das zwar erkannt, aber nur dank Defensive-Behavior. Jetzt verbindlich:

```bash
# Profil als YAML/JSON file-validieren (oder als Inline-Block)
python "$SKILL_BASE/tools/validate_profile.py" path/to/profile.yaml
# exit 0 = clean, exit 1 = Placeholder oder Schema-Fehler
```

Der Validator catcht:
- **Placeholder-Werte:** `...`, `<placeholder>`, `<TODO>`, `TODO`, leere Strings, `null`/`None`, leere Listen, Listen mit Placeholder-Members
- **Fehlende Pflichtfelder:** alle 15 Profil-Top-Level-Felder plus `data_source.is_swiss_open_data`
- **Type-Mismatches:** `bool`-Feld mit String-Wert, `list`-Feld mit String-Wert, etc.

Bei Exit-1 wird Step 2 nicht gestartet. Der Output zeigt strukturiert, welche Felder betroffen sind (`missing` / `placeholder` / `type_mismatch`). Nutze das, um den User zur Korrektur aufzufordern.

---

## Schritt 2: Check-Katalog laden

**Ziel:** Den vollständigen Katalog (`checks/*.md`) parsen und nach `category` + `severity` indizieren.

### 2.1 Sieben Kategorien

| Kategorie | Quelle | Typische Anzahl Checks | Status v0.5.0 |
|---|---|---|---|
| `ARCH` | PDF Sec 2 + Anhang A — Tool-Design, Annotations, Idempotency, Repo-Struktur, Spec-Versionierung | 10–12 | 12 / 12 ✅ |
| `SDK` | PDF Sec 3 — FastMCP, TypeScript, Zod, Lifecycle | 5–7 | 5 / 5 ✅ |
| `SEC` | PDF Sec 4 + Anhang B — Security (grösste Kategorie) | 20–25 | 23 / 23 ✅ |
| `SCALE` | PDF Sec 5 — Transport, LB, Container, Gateway | 5–7 | 6 / 6 ✅ |
| `OBS` | PDF Sec 6 + Anhang B10 — Logging, Errors, SIEM, Tracing | 5–7 | 6 / 6 ✅ |
| `HITL` | PDF Sec 7 — Sampling, Human-in-the-Loop | 4–5 | 5 / 5 ✅ |
| `CH` | Custom — DSG/EDÖB, Schweiz-Compliance | 5–8 | 8 / 8 ✅ |
| `OPS` | Anhang C — Test-Strategie, Doku, Phasenarchitektur | 3–5 | 3 / 3 ✅ |
| **Total** | | **~65** | **68 / 68 ✅** |

### 2.2 Severity-Stufen

| Stufe | Bedeutung | Konsequenz |
|---|---|---|
| `critical` | Sicherheitslücke oder Compliance-Bruch | Blockiert Produktion. Muss vor Release gefixt sein. |
| `high` | Architektureller Mangel mit signifikantem Risiko | Im laufenden Sprint fixen, max. 1 Sprint Karenz. |
| `medium` | Best-Practice-Verletzung, kein akutes Risiko | Im nächsten Sprint planen. |
| `low` | Polish, Optimierung, Stilistik | Backlog. Bei Tippfehler-Audits: low + auto-fix. |

### 2.3 Check-Schema

Jeder Check ist eine eigenständige Markdown-Datei im Format:

```markdown
---
id: SEC-001
title: "Confused Deputy: Per-Client Consent Flow"
category: security
severity: critical
applies_when: 'auth_model == "OAuth-Proxy"'
pdf_ref: "Sec 4.1"
evidence_required: 3
---

# Body mit Description, Verification, Pass Criteria, Remediation
```

Details siehe `templates/finding.md` und beliebige Datei in `checks/`.

---

## Schritt 3: Applicability-Filter

**Ziel:** Aus den ~50 Checks nur diejenigen auswählen, die für das aktuelle Server-Profil tatsächlich relevant sind. Ohne diesen Filter überfluten irrelevante Findings den Report (z.B. OAuth-Checks für stdio-only-Server ohne Auth).

### 3.1 Auswertung der `applies_when`-Klausel

Die Klausel ist ein Boolean-Ausdruck gegen die Profil-Felder. Die formale DSL-Spezifikation steht in [`docs/applies-when-dsl.md`](docs/applies-when-dsl.md), die Referenz-Implementierung in [`tools/eval_applicability.py`](tools/eval_applicability.py).

| Operator | Beispiel | Bedeutung |
|---|---|---|
| `==` | `transport == "HTTP/SSE"` | exakter String-Vergleich |
| `!=` | `auth_model != "none"` | Negation |
| `.includes(...)` | `deployment.includes("Railway")` | Multi-Select-Membership |
| `and` / `or` | `transport == "HTTP/SSE" and auth_model == "OAuth-Proxy"` | Verknüpfung |
| `always` | `always` | Check ist universell, läuft immer |

**Pflicht: Verwende den kanonischen Evaluator, niemals Python `eval()` oder ad-hoc-Substitution.** Letzteres hat in der Vergangenheit zu nicht-reproduzierbaren Audits geführt (Listen-vs-String-Vergleiche, `True` vs `true`, etc.).

```bash
# Catalog-Auswertung gegen ein Profil
python tools/eval_applicability.py catalog path/to/profile.yaml --format table

# Einzelner Ausdruck testen
python tools/eval_applicability.py expr 'auth_model != "none"' path/to/profile.yaml
```

### 3.2 Typische Filter-Muster

**stdio-only-Server ohne Auth, Public Open Data, read-only:**
- Anwendbar: alle `ARCH`, alle `SDK`, ~5 `SEC` (basale Best Practices), `OBS`-Logging-Basics, einige `CH`
- Nicht anwendbar: SSRF, OAuth-Flow, Session-Hijacking, Stateful-LB, Sandboxing
- Geschätzt: **~15–20 Checks**

**HTTP/SSE-Server mit OAuth-Proxy, Cloud-Deployment, Verwaltungsdaten:**
- Anwendbar: praktisch alles
- Geschätzt: **~45–55 Checks**

### 3.3 Applicability-Report (vor Audit-Start)

Bevor der eigentliche Audit beginnt, gibt Claude diese Übersicht aus:

```
=== Audit applicability for zurich-opendata-mcp ===
Profile: dual transport, no auth, Public Open Data, read-only,
         Deployment: [local-stdio, Railway]

Applicable checks: 23 / 50
  ARCH: 7/7      (universal)
  SDK:  6/6      (universal)
  SEC:  4/18     (cloud-relevant subset)
  SCALE: 3/6     (Railway-relevant subset)
  OBS:  3/5      (universal subset)
  HITL: 0/4      (no write access, no sampling)
  CH:   0/6      (Public Open Data, no PII)

Severity breakdown of applicable checks:
  critical: 4    high: 11    medium: 6    low: 2
```

**Wichtig:** Wenn ein Check nicht anwendbar ist, erscheint er **gar nicht** im Report — nicht einmal als «N/A». Das hält Reports fokussiert und vermeidet Audit-Müdigkeit.

---

## Schritt 4: Check-Ausführung

**Ziel:** Jeden anwendbaren Check methodisch verifizieren — entweder automatisch (grep, AST, curl) oder via manuellem Code-Review.

### 4.1 Drei Verifikationsmodi

Jeder Check definiert in seiner `verification:`-Sektion einen oder mehrere Modi:

| Modus | Wann | Beispiel |
|---|---|---|
| `automated` | Pattern existiert/fehlt im Repo | `grep -r "expose_headers" src/` für SDK-004 |
| `code_review` | Logische Prüfung erforderlich | OAuth-State-Single-Use bei SEC-010 |
| `config_check` | Repo-Settings, CI, Branch-Protection | `cat .github/workflows/*.yml` für OBS-Checks |
| `runtime_test` | Live-API-Verhalten testen | `curl -H "X-Forwarded-For: 169.254.169.254"` für SEC-004 |

### 4.2 Audit-Reihenfolge: Severity descending

Innerhalb der anwendbaren Checks läuft der Audit in dieser Reihenfolge:

1. Alle `critical`-Checks zuerst (Showstopper früh erkennen)
2. Dann `high`
3. Dann `medium`
4. `low` zuletzt (oder skippen falls knappe Zeit)

**Wenn ein `critical`-Check fehlschlägt, kann der Audit nicht «pass» erhalten** — egal wie gut die anderen Checks ausgehen.

### 4.3 Evidenz-Sammlung pro Check

Für jeden ausgeführten Check wird strukturiert dokumentiert:

```yaml
check_run:
  id: SEC-001
  status: pass | fail | partial | skip
  evidence_collected: 4  # tatsächlich beobachtet
  evidence_required: 3   # Mindestmaß aus Check-Def
  findings:
    - "Per-client consent UI in src/oauth/consent.py:42"
    - "X-Frame-Options: DENY in src/middleware/security.py:18"
    - "State parameter validated single-use in src/oauth/state.py:55"
  gaps:
    - "Cookies nutzen __Secure- prefix statt __Host- — schwächere Subdomain-Isolation"
  evaluator_notes: |
    Die Implementierung ist 90% korrekt. __Host- statt __Secure-
    wäre der vollständige Schutz gemäss Best Practice.
```

### 4.4 Pass-Criteria

Ein Check besteht **nur dann** als `pass`, wenn:
- Alle Pflicht-Pass-Criteria im Check erfüllt sind
- Mindestens `evidence_required` Punkte beobachtet wurden
- Keine `gaps` der Severity ≥ Check-Severity vorliegen

Sonst: `partial` (wenn 50%+ erfüllt) oder `fail`.

### 4.5 Task-Agent-Validation-Gate (verbindlich)

Wenn die Check-Execution per Task-Agent delegiert wird (typisch bei Batch-Verarbeitung mehrerer Checks gleichzeitig), MUSS nach jedem Agent-Aufruf ein Verifikations-Gate laufen. Hintergrund: Im ersten realen Audit hat ein Task-Agent mit `Done (68 tool uses · 0 tokens · 2m 20s)` zurückgegeben — vollständiger stiller Fehlschlag — und der Skill hat das nicht erkannt.

```bash
# 1. Nach jedem Task-Agent-Aufruf: prüfen, dass alle erwarteten raw/-Files
#    existieren UND nicht leer sind (catches the 0-token failure mode).
python "$SKILL_BASE/tools/verify_raw_outputs.py" "$OUTPUT_DIR/raw/" \
    --expected-ids ARCH-001,ARCH-002,SEC-021 \
    --min-bytes 1

# 2. Run-Metadata loggen — Tool-Uses, Tokens, Duration in audit-meta.json.
#    Dieser Befehl exitet 1 wenn der Agent als `empty` oder `incomplete`
#    klassifiziert wird.
python "$SKILL_BASE/tools/agent_run_log.py" log \
    --meta-path "$OUTPUT_DIR/audit-meta.json" \
    --tool-uses 73 --tokens 108100 --duration 640 \
    --expected ARCH-001,ARCH-002,SEC-021 \
    --raw-dir "$OUTPUT_DIR/raw/"
```

**Retry-Policy bei Fehlschlag:**

1. **Erster Aufruf** — alle anwendbaren Checks erwartet
2. **Bei `incomplete_ids`** → erneuter Task-Agent-Aufruf nur mit den fehlenden IDs, Logging mit `--retry-of <run_index>`
3. **Bei `empty`-Status (Tokens=0)** → identisch behandeln, der Aufruf zählt nicht als ausgeführt
4. **Maximal 2 Retries.** Danach harter Abbruch mit der Liste der unfertigen IDs — der menschliche Auditor muss diese Checks manuell ausführen oder den Audit verschieben

```bash
# Am Ende von Step 4: Coverage-Summary
python "$SKILL_BASE/tools/agent_run_log.py" summary \
    --meta-path "$OUTPUT_DIR/audit-meta.json"
# overall_status muss "ok" sein, sonst Step 5 nicht starten
```

Dieses Gate gilt nicht bei Single-Check-Bash-Aufrufen (kein Task-Agent involviert) — dort liefert die Bash-Pipeline ihren eigenen Exit-Code.

---

## Schritt 5: Finding-Dokumentation

**Ziel:** Pro fehlgeschlagenem Check ein strukturiertes Finding erzeugen, das direkt in einen Remediation-Plan überführbar ist.

### 5.0 Findings-Persistenz-Regel (verbindlich)

Ein Finding-Document wird **genau dann** erzeugt, wenn der Check-Status in der **Findings-Policy** enthalten ist. Es gibt drei Policies, dokumentiert in [`tools/aggregate_results.py`](tools/aggregate_results.py):

| Policy | Findings für Status | Wann verwenden |
|---|---|---|
| `fail-or-partial` (Default) | `fail` + `partial` | Standard-Audit, vollständige Remediation-Backlog |
| `fail-only` | `fail` | Schnell-Audit, nur Showstopper |
| `needs-attention` | `fail` + `partial` + `todo` | Pre-Production-Härtung, alles offene |

Die Policy MUSS in jedem Audit-Run explizit gesetzt und in `summary.json` persistiert werden. **Vor Abschluss des Audits ist `tools/aggregate_results.py validate <audit_dir>` Pflicht** — sonst können die Findings-Counts in Step 5 und Step 6 auseinanderdriften (Real-World-Bug aus dem ersten Audit).

```bash
# 1. Verification-Results aus Step 4 in JSON serialisieren
#    (Schema: siehe tools/aggregate_results.py docstring)
# 2. Aggregieren — produziert summary.json als Single-Source-of-Truth
python tools/aggregate_results.py aggregate \
    audits/<run>/verification-results.json \
    --policy fail-or-partial \
    --out audits/<run>/summary.json

# 3. Liste der zu schreibenden Findings ausgeben
python tools/aggregate_results.py expected-findings \
    audits/<run>/verification-results.json --policy fail-or-partial

# 4. Nach dem Schreiben: Validation-Gate (hard fail bei Mismatch)
python tools/aggregate_results.py validate audits/<run>/
```

### 5.1 Finding-Template

Verwendet `templates/finding.md`:

```markdown
## Finding: <CHECK-ID> — <CHECK-TITLE>

**Severity:** critical | high | medium | low
**Status:** open | in-remediation | accepted-risk | closed
**Server:** <server-name>
**Check-Reference:** <ID>
**PDF-Reference:** Sec X.Y

### Observed Behavior
<Was wurde im Code/Verhalten beobachtet?>

### Expected Behavior
<Was würde der Best-Practice-Katalog verlangen?>

### Evidence
- File: `path/to/file.py:42`
- Excerpt: ...
- Test output: ...

### Risk Description
<Welcher konkrete Schaden kann entstehen?>

### Remediation
<Konkrete Schritte, idealerweise mit Code-Diff.>

### Effort Estimate
S (< 1d) | M (1-3d) | L (1-2w) | XL (>2w)
```

### 5.2 Findings-Anzahl zurück in Audit Tracker

Nach Abschluss des Audits wird die `Findings`-Spalte in der Notion-Karte aktualisiert. Der Wert MUSS aus `summary.json` gelesen werden, niemals neu gezählt:

```bash
# Korrekt: Single-Source-of-Truth
total_findings=$(jq '.findings.expected_count' audits/<run>/summary.json)
update_audit_tracker --server "$name" --findings "$total_findings" --status "Findings dokumentiert"
```

```python
# FALSCH: separate Re-Computation — riskiert Drift gegen Step 5/6
total_findings = sum(1 for r in check_runs if r.status in ("fail", "partial"))
```

### 5.3 Audit-Status-Transition

| Vorher | Nach Audit | Bedingung |
|---|---|---|
| `Triagiert` | `In Audit` | Schritt 1-3 abgeschlossen |
| `In Audit` | `Findings dokumentiert` | alle Checks gelaufen, Findings erfasst |
| `Findings dokumentiert` | `In Remediation` | Fix-Arbeit gestartet |
| `In Remediation` | `Abgeschlossen` | alle critical/high Findings closed |

---

## Schritt 6: Audit-Report

**Ziel:** Einen kompakten, an verschiedene Stakeholder versendbaren Bericht produzieren.

### 6.1 Report-Struktur (Template `templates/audit-report.md`)

1. **Executive Summary** (3 Sätze): Server X, Y Findings, Z davon critical/high. Production-ready: ja/nein.
2. **Profile-Snapshot** (aus Audit Tracker)
3. **Applicability-Übersicht** (welche Kategorien/Stufen wurden geprüft)
4. **Findings-Tabelle** (sortiert nach Severity)
5. **Detail-Findings** (eines pro fehlgeschlagenem Check, vollständig)
6. **Remediation-Plan** (Effort-Schätzung pro Finding, Vorschlag-Reihenfolge)
7. **Audit-Metadata** (wer, wann, Skill-Version, Check-Katalog-Version)

**Pflicht:** Alle Zahlen im Report (Status-Counts, Findings-Anzahl, Production-Ready-Flag, Blocking-Findings) MÜSSEN aus `summary.json` gelesen werden. Niemals direkt aus den `raw/`-Files oder über Re-Aggregation neu berechnen — sonst entsteht der Drift-Bug aus dem srgssr-Audit (Step 4 zeigte 8 PASS, Final Report zeigte 13 PASS).

```bash
# Status-Counts im Report
jq '.totals.by_status' audits/<run>/summary.json

# Production-Ready
jq '.production_ready' audits/<run>/summary.json

# Blocking-Findings (failing critical/high)
jq -r '.blocking_findings[]' audits/<run>/summary.json
```

### 6.2 Sprache und Adressaten

- **GL / KI-Fachgruppe:** Deutsch, Executive Summary + Findings-Tabelle reichen
- **Entwickler / Maintainer:** Deutsch oder Englisch, vollständiger Detail-Report
- **Externe Auditoren / Compliance:** Englisch, vollständig + Profile-Snapshot

---

## Anti-Patterns (vermeiden)

1. **«Wir machen den Audit, sobald alles fertig ist»** — Audits sind iterativ. Server in Phase 1 auditieren, nicht erst in Phase 3.
2. **«Der Server ist Open Data, also kein Audit nötig»** — falsch. Auch Public-Data-Server haben Tool-Design-, SDK- und Resilienz-Risiken.
3. **«Findings als Issues in GitHub anlegen reicht»** — nein, ohne strukturierte Severity und Effort werden sie ignoriert. Notion-Karte ist Single Source of Truth.
4. **«Ich überspringe `low`-Findings»** — okay, aber dokumentieren als «not-audited», nicht stillschweigend ignorieren.
5. **«Der Check passt nicht ganz, ich mache es einfach so wie ich denke»** — wenn ein Check nicht passt, ist das ein Indikator dass der Katalog erweitert werden muss. Im Skill-Repo ein Issue eröffnen.
6. **«Audit-Report ohne Remediation-Plan»** — wertlos. Findings ohne Fix-Vorschlag werden nicht angegangen.

---

## Eselsbrücken & Metaphern

- **Profile zuerst:** *«Ein Audit ohne Profil ist wie ein Arzt ohne Anamnese — falsche Diagnose garantiert.»*
- **Applicability-Filter:** *«Bei stdio-only ohne Auth ist Confused Deputy genauso relevant wie Erdbebensicherung in Reykjavík — gar nicht.»*
- **Severity-Disziplin:** *«`critical` heisst critical. Wer die Stufe inflationiert, hat irgendwann nur noch `critical`.»*
- **Evidenz-Pflicht:** *«Ein Finding ohne `path/to/file.py:42` ist eine Meinung, kein Befund.»*

---

## Qualitätschecklist vor Abschluss eines Audits

**Schritt 1 — Profil**
- [ ] Alle 6 Pflichtfelder im Audit Tracker gesetzt
- [ ] Repo-URL erreichbar
- [ ] Audit-Status auf `In Audit` gesetzt

**Schritt 2-3 — Vorbereitung**
- [ ] Check-Katalog Version notiert
- [ ] Applicability-Filter ausgeführt
- [ ] Applicability-Report erstellt

**Schritt 4 — Ausführung**
- [ ] Alle anwendbaren Checks abgearbeitet (kein Skip ohne Begründung)
- [ ] Checks in Severity-Reihenfolge ausgeführt (`critical` zuerst)
- [ ] Pro Check Evidenz mit Datei + Zeilen-Referenz dokumentiert

**Schritt 5 — Findings**
- [ ] Pro fehlgeschlagenem Check ein Finding nach Template
- [ ] Effort-Schätzung S/M/L/XL gesetzt
- [ ] Tracker-Findings-Anzahl aktualisiert
- [ ] Audit-Status auf `Findings dokumentiert` gesetzt

**Schritt 6 — Report**
- [ ] Executive Summary auf 3 Sätze
- [ ] Findings-Tabelle nach Severity sortiert
- [ ] Remediation-Plan mit Reihenfolge-Vorschlag
- [ ] Audit-Metadata vollständig (Datum, Skill-Version, Katalog-Version)

---

## Versionierung des Check-Katalogs

Wenn das PDF aktualisiert wird oder neue Best Practices auftauchen:

1. Im Skill-Repo unter `checks/` neue `.md`-Datei mit nächster ID anlegen
2. `evidence_required` und `applies_when` mit Care befüllen
3. CHANGELOG-Eintrag im Repo-Root
4. Bestehende Server, die schon ein Audit hatten, **nicht automatisch reauditiert** — sondern bei nächstem Refactoring oder geplantem Re-Audit
5. Severity-Änderungen an bestehenden Checks: **immer** Re-Audit bei `critical` oder `high`

**Eselsbrücke:** *«Ein neuer Check ist ein neuer Vertrag. Bestehende Audits sind nicht rückwirkend ungültig, aber bei nächstem Audit gilt der neue Katalog.»*

---

## Übergabe & Folge-Skills

Nach erfolgreichem Audit:

- **Findings als GitHub-Issues** anlegen via [`github-repo`](../github-repo/SKILL.md)-Skill (mit Labels `audit`, `severity:critical`, etc.)
- **DSG/Compliance-Findings** als Notion-Karte im Use-Case-Register, falls relevant
- **Bei Pattern-Wiederholung** über mehrere Server: ein Reference-Template-MCP-Repo bauen, das alle Best Practices erfüllt, und Server iterativ darauf migrieren
