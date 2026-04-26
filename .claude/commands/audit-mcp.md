---
description: Audit eines MCP-Servers gegen den mcp-audit-skill v0.3.0-Katalog (53 Checks). Lädt Profil, filtert anwendbare Checks, führt automatisierte Verifikation aus, erzeugt Findings-Stubs und Audit-Report.
argument-hint: <repo-url-or-local-path>
allowed-tools: Bash(git:*), Bash(grep:*), Bash(find:*), Bash(curl:*), Bash(ls:*), Bash(cat:*), Bash(wc:*), Bash(head:*), Bash(tail:*), Bash(awk:*), Bash(sed:*), Bash(jq:*), Bash(test:*), Read, Write, Glob
---

# /audit-mcp — MCP-Server Audit-Workflow

Du führst jetzt einen strukturierten Audit eines MCP-Servers durch, basierend auf dem `mcp-audit-skill v0.3.0`-Katalog (53 Checks in 7 Kategorien: ARCH, SDK, SEC, SCALE, OBS, HITL, CH).

Argument: `$ARGUMENTS` (Repo-URL oder lokaler Pfad zum Server-Repo)

## Anweisungen

Arbeite die folgenden sechs Schritte sequenziell ab. Nach jedem Schritt fasst du zusammen, was du herausgefunden hast, **bevor** du den nächsten startest. Bei Mehrdeutigkeit fragst du den User, statt zu raten.

---

### Schritt 0 — Setup und Repo-Zugriff

1. **Skill-Pfad bestimmen.** Setze `SKILL_PATH` in dieser Reihenfolge:
   - Falls die Umgebungsvariable `MCP_AUDIT_SKILL_PATH` gesetzt ist: nutze sie.
   - Sonst prüfe `~/mcp-audit-skill/checks/`.
   - Sonst prüfe `~/.claude/skills/mcp-audit-skill/checks/`.
   - Sonst prüfe `./mcp-audit-skill/checks/` (relativ zum aktuellen Repo).
   - Falls nichts existiert: bitte den User um den absoluten Pfad zum geclonten `mcp-audit-skill`-Repo. Speichere als `SKILL_PATH`.

   Verifiziere: `ls $SKILL_PATH/checks/*.md | wc -l` sollte 53 ergeben.

2. **Target-Repo zugreifen.**
   - Wenn `$ARGUMENTS` mit `https://` beginnt: clone in temp-Verzeichnis: `git clone --depth 1 $ARGUMENTS /tmp/audit-target`. Setze `TARGET=/tmp/audit-target`.
   - Wenn `$ARGUMENTS` ein lokaler Pfad ist: setze `TARGET=$ARGUMENTS` und prüfe Existenz mit `ls $TARGET/`.

3. **Server-Namen identifizieren** aus `pyproject.toml` (`[project] name`), `package.json` (`"name"`), oder Repo-Verzeichnisname als Fallback.

4. **Output-Verzeichnis bestimmen:** `<TARGET>/audits/YYYY-MM-DD-<server-name>/` und erstellen mit `mkdir -p`. Falls bereits existierend, mit `-vN`-Suffix versionieren.

**Output Schritt 0:** Werte von `SKILL_PATH`, `TARGET`, `SERVER_NAME`, `OUTPUT_DIR`. Dann weiter zu Schritt 1.

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

---

### Schritt 2 — Catalog-Load

Lies alle Check-Files aus dem Skill:

```bash
ls $SKILL_PATH/checks/*.md | sort
```

Für jeden Check extrahiere die Frontmatter (zwischen den `---`-Markern am File-Anfang) mit den Feldern:
- `id`
- `title`
- `category`
- `severity`
- `applies_when` (Boolean-Expression über Profil-Variablen)
- `pdf_ref`
- `evidence_required`

Verwende dafür `awk` oder `head -n 10` plus simples Parsing:

```bash
for f in $SKILL_PATH/checks/*.md; do
  awk '/^---$/{c++; next} c==1' "$f" | head -10
  echo "FILE: $f"
  echo "---"
done
```

**Output Schritt 2:** Kurze Zusammenfassung — Anzahl Checks total, Aufschlüsselung pro Kategorie. Sollten 53 Checks sein.

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

Für jeden Check mit Status **Fail** oder **Partial** erstellst du ein Finding-Document basierend auf `$SKILL_PATH/templates/finding.md`.

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

Fülle das `$SKILL_PATH/templates/audit-report.md`-Template mit den gesammelten Daten und schreibe es nach `$OUTPUT_DIR/audit-report.md`.

Pflicht-Sektionen:

1. **Executive Summary** — 3 Sätze max: Anzahl anwendbarer Checks, Anzahl Findings nach Severity, Production-Readiness (✅ ja wenn 0 critical und ≤ 2 high; ❌ sonst).
2. **Profile** — der bestätigte Profil-Block aus Schritt 1.
3. **Coverage** — Tabelle pro Kategorie: Total / Anwendbar / Pass / Fail / Partial / TODO.
4. **Findings** — Liste aller erzeugten Findings, gruppiert nach Severity.
5. **Open TODOs** — Liste aller `TODO`-Status-Checks mit den Such-Pattern aus dem Check-File. Damit kann der menschliche Auditor die manuellen Schritte abarbeiten.
6. **Anhang** — Liste der Roh-Output-Files in `raw/`.

**Output Schritt 6:** Pfad zum Report-File. Plus Klartext-Empfehlung: «Production-Ready ja/nein, nächste Schritte sind: ...».

---

## Persönliche Hinweise

- **Tempo statt Vollständigkeit am Anfang:** Wenn die automatisierten Checks rasch durch sind, bleibt mehr Zeit für die manuellen Code-Reviews. Komplettheit erreichst du im Iterations-Workflow, nicht im Single-Run.
- **Sprache:** Schweizer Rechtschreibung (kein ß) für alle generierten Files. Findings auf Deutsch oder Englisch je nach Repo-Sprache des Targets.
- **Notion-Integration:** Wenn der User dir den Notion-Card-URL gegeben hat, gib am Ende einen Klartext-Block aus mit den Feld-Updates, die er manuell ins Notion eintragen kann (Findings-Anzahl, Audit-Status, Notiz-Link).
- **Nichts überschreiben:** Wenn `$OUTPUT_DIR` bereits existiert (vorheriger Audit-Run), versionierst du mit `-vN`-Suffix (`audits/YYYY-MM-DD-zh-education-mcp-v2/`) statt zu überschreiben.
- **Stop bei Profil-Unsicherheit:** Falls du in Schritt 1 mehr als zwei Default-Werte raten musstest, brichst du ab und fragst den User. Falsches Profil = falscher Filter = falscher Audit.

---

Beginne mit Schritt 0.
