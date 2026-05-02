---
description: Audit eines MCP-Servers gegen den mcp-audit-skill v0.5.0-Katalog. Lädt Profil, filtert anwendbare Checks, führt automatisierte Verifikation aus, erzeugt Findings-Stubs und Audit-Report. Funktioniert mit lokalem Skill-Klon oder via WebFetch von GitHub-Raw (Cloud-Modus).
argument-hint: <repo-url-or-local-path>
allowed-tools: Bash(git:*), Bash(grep:*), Bash(find:*), Bash(curl:*), Bash(ls:*), Bash(cat:*), Bash(wc:*), Bash(head:*), Bash(tail:*), Bash(awk:*), Bash(sed:*), Bash(jq:*), Bash(test:*), Bash(python:*), Bash(python3:*), Read, Write, Glob, WebFetch
---

# /audit-mcp — MCP-Server Audit-Workflow

Du führst jetzt einen strukturierten Audit eines MCP-Servers durch, basierend auf dem `mcp-audit-skill v0.5.0`-Katalog (7 Kategorien: ARCH, SDK, SEC, SCALE, OBS, HITL, CH; vollständige Check-Liste in `checks/MANIFEST.txt`).

Argument: `$ARGUMENTS` (Repo-URL oder lokaler Pfad zum Server-Repo)

## Anweisungen

Arbeite die folgenden sechs Schritte sequenziell ab. Nach jedem Schritt fasst du zusammen, was du herausgefunden hast, **bevor** du den nächsten startest. Bei Mehrdeutigkeit fragst du den User, statt zu raten.

---

### Schritt 0 — Setup und Repo-Zugriff

1. **Skill-Quelle bestimmen.** Setze `SKILL_BASE` und `SKILL_MODE` in dieser Reihenfolge:
   - Falls die Umgebungsvariable `MCP_AUDIT_SKILL_PATH` gesetzt ist und `$MCP_AUDIT_SKILL_PATH/checks/` existiert: `SKILL_BASE=$MCP_AUDIT_SKILL_PATH`, `SKILL_MODE=local`.
   - Sonst prüfe in dieser Reihenfolge `~/mcp-audit-skill/checks/`, `~/.claude/skills/mcp-audit-skill/checks/`, `./mcp-audit-skill/checks/` (relativ zum aktuellen Repo) — beim ersten Treffer: `SKILL_BASE=<dieser Pfad>`, `SKILL_MODE=local`.
   - **Fallback (Cloud-Modus):** Falls kein lokaler Pfad existiert, setze `SKILL_BASE=https://raw.githubusercontent.com/malkreide/mcp-audit-skill/main` und `SKILL_MODE=remote`. Dieser Modus nutzt `WebFetch` und benötigt keinen lokalen Klon des Skills.

   **Verifiziere:**
   - `local`: `ls $SKILL_BASE/checks/MANIFEST.txt && wc -l $SKILL_BASE/checks/MANIFEST.txt` — Manifest muss existieren und ≥ 50 Check-IDs enthalten.
   - `remote`: WebFetch `$SKILL_BASE/checks/MANIFEST.txt` mit dem Prompt «Gib den Inhalt unverändert zurück» — Antwort muss ≥ 50 Zeilen mit Check-IDs (z.B. `ARCH-001`) liefern. Falls WebFetch fehlschlägt: brich ab und bitte den User, das Skill-Repo lokal zu klonen oder `MCP_AUDIT_SKILL_PATH` zu setzen.

2. **Target-Repo zugreifen.**
   - Wenn `$ARGUMENTS` mit `https://` beginnt: clone in temp-Verzeichnis: `git clone --depth 1 $ARGUMENTS /tmp/audit-target`. Setze `TARGET=/tmp/audit-target`.
   - Wenn `$ARGUMENTS` ein lokaler Pfad ist: setze `TARGET=$ARGUMENTS` und prüfe Existenz mit `ls $TARGET/`.

3. **Server-Namen identifizieren** aus `pyproject.toml` (`[project] name`), `package.json` (`"name"`), oder Repo-Verzeichnisname als Fallback.

4. **Output-Verzeichnis bestimmen:** `<TARGET>/audits/YYYY-MM-DD-<server-name>/` und erstellen mit `mkdir -p`. Falls bereits existierend, mit `-vN`-Suffix versionieren.

**Output Schritt 0:** Werte von `SKILL_BASE`, `SKILL_MODE`, `TARGET`, `SERVER_NAME`, `OUTPUT_DIR`. Dann weiter zu Schritt 1.

---

### Schritt 1 — Profil-Load

Du brauchst das Server-Profil mit den Variablen, die `applies_when`-Filter verwenden. Drei Beschaffungswege in absteigender Präferenz:

**Weg A — User Memory / Conversation:** Falls der User dir das Profil zu Beginn der Konversation explizit übergeben hat (typisch: «audit zh-education-mcp, Profil: stadt_zuerich_context=true, schulamt_context=true, data_class=Public Open Data, ...»), nutze diese Werte direkt.

**Weg B — Notion-Audit-Tracker:** Bitte den User, dir den Notion-Card-URL zum Server zu geben (Database `a2736a65-677d-4cf3-9f94-e874f74a1975`). Du kannst die Notion-API nicht selbst aufrufen — der User soll die relevanten Felder copy-pasten oder selbst extrahieren.

**Weg C — Inferenz aus Repo:** Falls beide nicht verfügbar, leite das Profil aus dem Repo-Inhalt ab. Lies dafür:

```bash
cat $TARGET/README.md $TARGET/README.de.md 2>/dev/null
cat $TARGET/pyproject.toml $TARGET/package.json 2>/dev/null
ls $TARGET/.github/workflows/ 2>/dev/null
grep -rE "transport|MCP_TRANSPORT|sse|stdio|streamable" $TARGET/src/ 2>/dev/null | head -20
grep -rE "auth|oauth|bearer|token" $TARGET/src/ 2>/dev/null | head -10
grep -rE "ctx\.sample|sequential.thinking" $TARGET/src/ 2>/dev/null | head -5
```

Daraus baust du das Profil mit folgenden Variablen (Defaults bei Unsicherheit):

| Variable | Mögliche Werte | Default bei Unsicherheit |
|---|---|---|
| `transport` | `stdio-only`, `dual`, `HTTP`, `SSE` | `dual` |
| `auth_model` | `none`, `API-Key`, `OAuth-Proxy`, `OIDC` | `none` |
| `data_class` | `Public Open Data`, `Verwaltungsdaten`, `PII` | `Public Open Data` |
| `write_capable` | `true`, `false` | `false` |
| `deployment` | Liste: `local-stdio`, `Railway`, `Render`, `Kubernetes`, `Docker` | `["local-stdio"]` |
| `uses_sampling` | `true`, `false` | `false` |
| `uses_sequential_thinking` | `true`, `false` | `false` |
| `tools_include_filesystem` | `true`, `false` | `false` |
| `tools_make_external_requests` | `true`, `false` | `true` |
| `stadt_zuerich_context` | `true`, `false` | `false` (User-Frage falls unklar) |
| `schulamt_context` | `true`, `false` | `false` (User-Frage falls unklar) |
| `volksschule_context` | `true`, `false` | `false` |
| `enterprise_context` | `true`, `false` | `false` |
| `data_source.is_swiss_open_data` | `true`, `false` | inferiert aus Quellen-URLs |

**Output Schritt 1:** Vollständiges Profil als YAML-Block. **Bestätige mit dem User**, dass das Profil korrekt ist, bevor du weiter machst. Profil falsch = ganzer Audit falsch.

**Headless-Modus (Batch-Audit via `audit-portfolio.sh`):** Falls die Konversation **vor** dem `/audit-mcp`-Aufruf bereits einen vollständigen Profil-YAML-Block enthält, der explizit als «autoritativ» oder «Headless-Modus» markiert ist, übernimm das Profil unverändert und überspringe die User-Bestätigung. Gehe direkt zu Schritt 2. Diesen Modus erkennst du am Marker-Text «Headless-Modus für /audit-mcp» oder «Profil ist autoritativ».

---

### Schritt 2 — Catalog-Load

Lade die Check-Liste aus dem Manifest und parse für jeden Check die Frontmatter (zwischen den ersten beiden `---`-Markern) mit den Feldern: `id`, `title`, `category`, `severity`, `applies_when`, `pdf_ref`, `evidence_required`.

**Modus `local` — bevorzugt: Helper-Script aufrufen, niemals Inline-Heredocs:**

```bash
# Single-Source-of-Truth-Parser. Ersetzt frühere awk/heredoc-Loops, die
# auf Windows Git Bash mehrfach an Quoting-Bugs gecrasht sind.
python "$SKILL_BASE/tools/parse_catalog.py" --checks-dir "$SKILL_BASE/checks" --format json > catalog.json

# Konsistenz-Gate (MANIFEST.txt vs *.md):
python "$SKILL_BASE/tools/parse_catalog.py" --checks-dir "$SKILL_BASE/checks" --format manifest-check
# exit 0 = consistent, exit 1 = drift (siehe in_manifest_only / in_catalog_only)
```

Für eine schnelle visuelle Übersicht: `--format table` zeigt ID, Kategorie, Severity, applies_when in einer Spalten-Ansicht.

**Modus `remote`:**

1. WebFetch `$SKILL_BASE/checks/MANIFEST.txt` mit Prompt «Gib den Inhalt zeilenweise unverändert zurück.» Daraus die Check-ID-Liste bauen.
2. Für jede ID: WebFetch `$SKILL_BASE/checks/<ID>.md` mit Prompt «Gib die YAML-Frontmatter zwischen den ersten beiden `---`-Markern unverändert zurück, plus alle Abschnitte `## Verification`, `## Pass Criteria` und `## Remediation` falls vorhanden.» Cache nutzen ist OK.
3. Aus dem Ergebnis Frontmatter parsen.

**Wichtig — kein Pattern-Erfinden im Cache:** WebFetch gibt teils zusammengefasste Antworten. Falls die zurückgegebene Frontmatter unvollständig wirkt (z.B. fehlt `applies_when`), wiederhole den Fetch mit explizitem Prompt «Gib den vollständigen Markdown-Quelltext der Datei wortgetreu zurück, ohne Zusammenfassung.»

**Output Schritt 2:** Kurze Zusammenfassung — Anzahl Checks total (= Anzahl IDs im Manifest), Aufschlüsselung pro Kategorie. Falls die Anzahl der erfolgreich geladenen Checks vom Manifest abweicht: brich ab und liste die fehlenden IDs.

---

### Schritt 3 — Applicability-Filter

Werte für jeden Check die `applies_when`-Expression gegen das Profil aus Schritt 1 aus.

`applies_when` ist eine Python-artige Boolean-Expression. Beispiele aus dem Katalog:

| Expression | Bedeutung |
|---|---|
| `'always'` | immer anwendbar |
| `'auth_model != "none"'` | nur wenn Auth aktiv |
| `'transport != "stdio-only"'` | nur wenn Netzwerk-Transport |
| `'data_class == "PII"'` | nur bei PII |
| `'auth_model == "OAuth-Proxy"'` | nur bei OAuth-Proxy |
| `'data_class != "Public Open Data" and uses_sampling == true'` | UND-Verknüpfung |
| `'enterprise_context == true or stadt_zuerich_context == true'` | ODER-Verknüpfung |
| `'deployment.includes("local-stdio")'` | Liste-Membership |
| `'data_source.is_swiss_open_data == true'` | nested attribute |

Werte jede Expression aus, indem du die Profil-Variablen einsetzt. Bei `deployment.includes("X")`: prüfe ob `X` in der Liste enthalten ist.

Erstelle eine Tabelle:

```
| ID | Title | Category | Severity | Applicable | Reason |
|---|---|---|---|---|---|
| ARCH-001 | ... | ARCH | high | ✅ | applies_when=always |
| SEC-003 | Progressive Scope... | SEC | high | ❌ | auth_model = none |
```

**Output Schritt 3:** Tabelle aller 53 Checks mit Applicable-Spalte. Plus Zusammenfassung «X von 53 Checks anwendbar».

---

### Schritt 4 — Check-Execution

Für jeden anwendbaren Check führst du die Verifikation aus, **soweit automatisierbar**. Die Tiefe ist **Standard**: automatisierte Pattern-Suchen werden ausgeführt, manuelle Code-Reviews bleiben TODOs mit konkreten Such-Anweisungen.

Pro Check die folgenden Verification-Modi unterscheiden:

| Modus | Was tun |
|---|---|
| `code_review` | TODO-Stub erzeugen mit Such-Pattern aus Check-File |
| `automated` | Bash-Befehl direkt ausführen, Output erfassen |
| `config_check` | Bash-Befehl gegen Config-Files, Output erfassen |
| `runtime_test` | TODO-Stub mit dem curl/Test-Snippet aus Check-File |
| `documentation_check` | `find` und `grep` auf Doku-Files ausführen, Output erfassen |

Lies pro anwendbarem Check das Check-File und identifiziere die Verification-Modi (typisch unter `## Verification` mit `### Modus 1: <name>` etc.). Für jeden Modus extrahiere die Bash-Snippets in den ` ```bash`-Blöcken und führe sie aus.

**Modus-spezifischer Datenzugriff:**
- `SKILL_MODE=local`: lies das Check-File direkt mit `Read $SKILL_BASE/checks/<ID>.md` (vollständiger Inhalt nötig, nicht nur Frontmatter aus Schritt 2).
- `SKILL_MODE=remote`: WebFetch `$SKILL_BASE/checks/<ID>.md` mit Prompt «Gib alle ` ```bash`-Codeblöcke aus den Abschnitten `## Verification` / `### Modus *` wortgetreu zurück, plus die Abschnitte `## Pass Criteria`, `## Remediation`, `## Effort`.»

**Wichtig — kein Pattern-Erfinden:** Nutze ausschliesslich die Bash-Snippets aus den Check-Files. Wenn kein Snippet vorhanden ist, markiere den Modus als `MANUAL` und lass den User entscheiden.

**Wichtig — Output-Klassifikation:** Pro Check klassifizierst du das Ergebnis als:

- ✅ **Pass** — alle Pass-Criteria erfüllbar aus den automatisierten Befehlen
- ❌ **Fail** — mindestens ein automatisierter Befehl zeigt klares Anti-Pattern
- ⚠️ **Partial** — automatisierte Befehle zeigen das eine, aber `code_review`/`runtime_test`-Modi bleiben offen
- 🔍 **TODO** — kein Modus war automatisierbar, vollständige manuelle Review nötig

Speichere die rohen Befehl-Outputs pro Check in `$OUTPUT_DIR/raw/<check-id>.txt` für Audit-Trail.

**Output Schritt 4:** Tabelle aller anwendbaren Checks mit Status (Pass/Fail/Partial/TODO). Plus Anzahl-Aufschlüsselung.

---

### Schritt 5 — Findings-Generation

Für jeden Check mit Status **Fail** oder **Partial** erstellst du ein Finding-Document basierend auf dem Finding-Template:
- `SKILL_MODE=local`: `Read $SKILL_BASE/templates/finding.md`.
- `SKILL_MODE=remote`: WebFetch `$SKILL_BASE/templates/finding.md` mit Prompt «Gib den vollständigen Markdown-Quelltext wortgetreu zurück.»

Pro Finding ein File: `$OUTPUT_DIR/findings/<check-id>-<short-slug>.md` mit:

- Header mit Check-ID, Titel, Severity (aus Frontmatter)
- Beobachtung: was hat der Befehl gezeigt? (Roh-Output kürzen auf Wesentliches)
- Erwartung: was wäre korrekt? (aus dem Pass-Pattern des Check-Files)
- Risiko-Bewertung: wie wirkt sich das Finding aus? (aus dem `## Description`-Abschnitt des Check-Files)
- Remediation: konkrete Schritte (aus dem `## Remediation`-Abschnitt des Check-Files)
- Effort-Schätzung (aus dem `## Effort`-Abschnitt)
- Status: `Open` (initial)

**Wichtig — keine Halluzination:** Wenn das Check-File keine konkrete Remediation für den beobachteten Sub-Fall enthält, schreibe das explizit: «Remediation aus Check-File generisch übernommen, sub-fall-spezifische Anpassung nötig.»

**Output Schritt 5:** Liste aller erzeugten Finding-Files mit Severity-Aufschlüsselung.

---

### Schritt 6 — Report-Output

**Bevorzugt: Helper-Script aufrufen, niemals Inline-Python-Heredocs.** Letztere sind in der Vergangenheit auf Windows Git Bash an Quoting-Bugs gecrasht. Der Generator liest `summary.json` (Single-Source-of-Truth aus Step 5) und alle Files in `findings/` und produziert deterministisch denselben Report.

```bash
# 1. Vor Step 6: Validation-Gate sicherstellen (siehe Step 5)
python "$SKILL_BASE/tools/aggregate_results.py" validate "$OUTPUT_DIR"

# 2. Report aus summary.json + findings/ rendern
python "$SKILL_BASE/tools/build_report.py" "$OUTPUT_DIR" \
    --profile path/to/profile.yaml
```

Der Output landet als `$OUTPUT_DIR/audit-report.md`. Sektionen werden aus `summary.json` gelesen — wenn dort etwas fehlt, ist `tools/aggregate_results.py` falsch aufgerufen worden, NICHT manuell den Report patchen.

**Pflicht-Sektionen (vom Generator automatisch befüllt):**

1. **Executive Summary** — Server, Anzahl Checks, Findings-Counts, Production-Readiness, Blocking-Findings.
2. **Profile-Snapshot** — relevante Profil-Felder.
3. **Applicability** — Tabelle pro Kategorie: Pass/Fail/Partial/TODO/N/A.
4. **Findings-Übersicht** — alle Findings nach Severity sortiert.
5. **Detail-Findings** — Inhalt der `findings/<ID>-*.md`-Files eingebettet.
6. **Remediation-Plan** — Reihenfolge nach Severity.
7. **Audit-Metadata** — Skill-Version, Catalog-Version, Policy.

**Output Schritt 6:** Pfad zum Report-File. Plus Klartext-Empfehlung: «Production-Ready ja/nein, nächste Schritte sind: ...».

---

## Persönliche Hinweise

- **Tempo statt Vollständigkeit am Anfang:** Wenn die automatisierten Checks rasch durch sind, bleibt mehr Zeit für die manuellen Code-Reviews. Komplettheit erreichst du im Iterations-Workflow, nicht im Single-Run.
- **Sprache:** Schweizer Rechtschreibung (kein ß) für alle generierten Files. Findings auf Deutsch oder Englisch je nach Repo-Sprache des Targets.
- **Notion-Integration:** Wenn der User dir den Notion-Card-URL gegeben hat, gib am Ende einen Klartext-Block aus mit den Feld-Updates, die er manuell ins Notion eintragen kann (Findings-Anzahl, Audit-Status, Notiz-Link).
- **Nichts überschreiben:** Wenn `$OUTPUT_DIR` bereits existiert (vorheriger Audit-Run), versionierst du mit `-vN`-Suffix (`audits/YYYY-MM-DD-zh-education-mcp-v2/`) statt zu überschreiben.
- **Stop bei Profil-Unsicherheit:** Falls du in Schritt 1 mehr als zwei Default-Werte raten musstest, brichst du ab und fragst den User. Falsches Profil = falscher Filter = falscher Audit.
- **Cloud-Modus (`SKILL_MODE=remote`):** Wenn der Skill via WebFetch geladen wird, erwähne das einmal früh im Output (z.B. nach Schritt 0) und im Audit-Report unter «Audit-Metadata», damit für die Reproduzierbarkeit klar ist, dass der Katalog-Stand aus `main` von `github.com/malkreide/mcp-audit-skill` kam. Bei flakigen WebFetch-Antworten (Cache-Zusammenfassung statt Quelltext) wiederhole mit explizitem «wortgetreu»-Prompt.

---

Beginne mit Schritt 0.
