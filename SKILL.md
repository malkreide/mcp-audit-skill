---
name: mcp-audit
description: Reproduzierbares Audit von MCP-Servern gegen einen versionierten Best-Practice-Katalog. Verwende diesen Skill wenn der User (1) einen MCP-Server gegen Best Practices prüfen will, (2) Sicherheitsfindings für einen Server dokumentieren möchte, (3) den MCP Audit Tracker (Notion) abarbeitet, (4) fragt «ist mein Server sicher / production-ready / standard-konform», (5) den Begriff «Audit», «Findings», «Compliance-Check», «Best Practice»  im MCP-Kontext erwähnt, (6) einen Refactoring-Plan für einen bestehenden Server erstellt, oder (7) für mehrere Server einen vergleichenden Audit-Report erstellen möchte. Auch bei allgemeinen Aussagen wie «ist der Server gut gebaut?», «was muss ich noch fixen?», «entspricht das den Standards?» diesen Skill anwenden.
---

# MCP Audit — Standardisiertes Audit-Vorgehen

Dieser Skill kodiert ein reproduzierbares Audit-Verfahren für MCP-Server gegen den im Anhang dokumentierten Best-Practice-Katalog (PDF-Quelle plus Schweiz-, Datentreue- und Identitäts-Layer sowie den Spec-Migrations-Layer, 115 Checks in zwölf Kategorien auf zwei Spec-Baselines). Ziel: bei 30+ Servern im Portfolio dieselbe Methodik anwenden, ohne dass der menschliche Auditor (oder Claude) bei jedem Server das PDF neu interpretiert.

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
| Run-ID + Output-Dir + audit-meta.json initialisieren | `python tools/audit_init.py init <server> --base-dir audits/ --catalog-dir checks/ --target-repo <repo>` |
| Ziel-Revision am Ende erneut prüfen | `python tools/audit_init.py verify-target <audit_dir>` |
| Profil-Validierung (Placeholder/Schema-Gate) | `python tools/validate_profile.py path/to/profile.yaml` |
| Catalog parsen (Frontmatter aller `*.md`) | `python tools/parse_catalog.py --format json` |
| Catalog vs. Manifest validieren | `python tools/parse_catalog.py --format manifest-check` |
| Portfolio-Inventar gegen die Checkouts prüfen | `python tools/verify_inventory.py --portfolio portfolio.yaml` |
| `applies_when` evaluieren | `python tools/eval_applicability.py catalog profile.yaml` |
| Zwei Applicability-Auswertungen vergleichen | `python tools/eval_applicability.py diff <alt> <neu> --labels alt,neu` |
| Verification-Results aggregieren | `python tools/aggregate_results.py aggregate results.json --checks-dir checks/ --out summary.json` |
| Gegen den Vorlauf vergleichen (Katalog-Epoche) | `python tools/aggregate_results.py aggregate ... --previous audits/<vorlauf>/` |
| Findings-Set vs. Disk validieren (inkl. Leer-Prüfung) | `python tools/aggregate_results.py validate <audit_dir>` |
| Unveränderte Findings aus früheren Läufen übernehmen | `python tools/carry_forward.py <audit_dir> --from <vorheriger_lauf>` |
| Audit-Report generieren | `python tools/build_report.py <audit_dir>` |
| Handgeschriebene Zahlen gegen `summary.json` prüfen | `python tools/check_reported_numbers.py <summary.json> <datei>...` |
| Task-Agent-Output verifizieren | `python tools/verify_raw_outputs.py raw/ --expected-ids ID1,ID2` |
| Task-Agent-Run loggen | `python tools/agent_run_log.py log --meta-path audit-meta.json ...` |
| Release-Vorschlag (Schritt 7) | `python tools/propose_release.py propose <audit_dir> <target_repo>` |
| Release anwenden (CHANGELOG + Tag) | `python tools/propose_release.py apply <audit_dir> <target_repo> --bump <patch\|minor\|major>` |
| Tracker-Update (CSV/Notion) | `python tools/tracker_sync.py update <server> --from-summary <summary.json>` |
| Pfad zu Native/POSIX konvertieren | `python tools/path_utils.py to-native <path>` |

Wenn ein Audit ein Snippet braucht das hier nicht abgedeckt ist: erst Issue im Skill-Repo öffnen, dann Helper-Script bauen, dann verwenden. **Inline-Heredoc ist der Anti-Pattern, der nicht-reproduzierbare Audits erzeugt.**

#### Dieselbe Regel gilt für CI-Guards, und dort wiegt sie schwerer

Ein Workflow-Schritt der Form `run: |` mit `python - <<'PY' … PY` ist ausführbarer Code ohne Testbarkeit: Er lässt sich nicht importieren, nicht mit Grenzfällen aufrufen und vor allem nicht mutationstesten. **Ein Guard, den man nicht kaputtmachen kann, ist kein nachgewiesener Guard** — und anders als ein Audit-Snippet läuft er unbeaufsichtigt weiter, oft jahrelang.

**Der Beleg stammt aus diesem Repo.** `tools/render_description_issue.py` war zuerst als Heredoc im Workflow geschrieben. Als Skript mit Tests fiel sofort auf, dass die naheliegende Zwei-Zustands-Logik — Body geschrieben heisst «Issue öffnen», kein Body heisst «Issue schliessen» — ein offenes Issue geschlossen hätte, obwohl der Vergleich nie stattgefunden hatte. Vier verschiedene Eingaben führten dorthin. Im Heredoc wäre der Fehler ausgeliefert worden, weil es dort keine Stelle gibt, an der man ihn hätte suchen können.

Die Grenze verläuft nicht bei der Zeilenzahl, sondern bei der Frage, **ob der Schritt urteilt**:

| Im YAML zulässig | Gehört in ein Skript mit Tests |
|---|---|
| `echo`, `mkdir`, Datei kopieren, ein Werkzeug aufrufen | Zustände unterscheiden, Schwellen prüfen, Ergebnisse klassifizieren |
| Ein Kommando, dessen Exitcode das Urteil **ist** | Ein Kommando, dessen Ausgabe erst **interpretiert** wird |

`python - <<'PY'` in einem Workflow ist damit fast immer das Signal, dass ein Skript fehlt. Der Katalog führt das als `OPS-008`.

### 0.4 Run-ID + Audit-Meta initialisieren (verbindlich seit Issue #15)

Niemals `date +%Y-%m-%d` für den Output-Verzeichnisnamen — das hat im ersten Audit zu Drift zwischen UTC-Container und lokalem Kalendertag geführt (`2026-04-30` statt `2026-05-01`). Stattdessen:

```bash
# Erzeugt Output-Dir mit ISO-Timestamp + Timezone-Offset, schreibt
# initiale audit-meta.json mit Skill-Version, Catalog-Hash und Ziel-SHA.
python "$SKILL_BASE/tools/audit_init.py" init "$SERVER_NAME" \
    --base-dir "$TARGET/audits/" \
    --skill-version "2.0.0" \
    --catalog-dir "$SKILL_BASE/checks/" \
    --target-repo "$TARGET"
# Output (JSON): { "run_id": "2026-05-02T091245-Z-srgssr-mcp", "output_dir": "...", "meta_path": "..." }
```

Run-ID-Format: `YYYY-MM-DDTHHMMSS-<offset>-<server>`, wobei `<offset>` `Z` (UTC) oder `+HHMM`/`-HHMM` ist. Bei Sekunden-genauer Kollision (Re-Audit unmittelbar danach) wird das Verzeichnis mit `-2`, `-3`, ... gesuffixt; die Run-ID selbst bleibt identisch.

Die initiale `audit-meta.json` enthält:
- `server_name`, `run_id`, `started_at` (ISO mit TZ-Suffix), `timezone_offset`
- `skill_version`, `catalog_hash` (SHA-256 aller `checks/*.md` + `MANIFEST.txt`), `catalog_dir`
- `target_repo`, `target_sha`, `target_dirty`, `target_branch` — die Revision des auditierten Repos (nur mit `--target-repo`)
- Leeres `agent_runs`-Array (wird in Step 4 von `agent_run_log.py` befüllt)

Der `catalog_hash` ist der Reproduzierbarkeits-Anker: jeder Re-Audit kann verifizieren, dass derselbe Katalog-Stand verwendet wurde.

### 0.5 Platzhalter in spitzen Klammern überleben den Weg nach draussen nicht

Diese Datei, `templates/finding.md` und die Finding-Dokumente schreiben Platzhalter als `<ID>`, `<slug>`, `<CHECK-ID>`. Im Repository ist das richtig und bleibt so — Git transportiert Text, nicht HTML.

**Wird derselbe Text von einem Agenten über die GitHub-Werkzeugschicht abgeschickt, ist er weg.** Ein Pull-Request-Body mit dem Satz «suchte `findings/<ID>.md`, während der Lauf `<ID>-<slug>.md` benannt hatte» kommt als «suchte `findings/.md`, während der Lauf `-.md` benannt hatte» an: `<ID>` und `<slug>` werden als unbekannte Tags verworfen. **Backticks schützen nicht** — die Umwandlung läuft vor dem Markdown-Parser.

Gemessen, nicht angenommen: In PR #79 zweimal reproduziert — beim Anlegen und beim Korrekturversuch mit denselben Klammern. Am selben Ort wurde `>` am Zeilenanfang zu `&gt;` escaped, das Blockquote also gleich mit zerstört.

**Wo genau das passiert, ist nicht belegt, und die Vermutung gehört nicht in die Regel.** Der gespeicherte Body enthält `&#39;` für Apostrophe; GitHub escaped die in Issue- und PR-Bodies nicht. Der Verlust entsteht also mit hoher Wahrscheinlichkeit in der Werkzeug- oder Proxy-Schicht des Agenten und **nicht** bei GitHub — ein Mensch, der denselben Text im Web-UI einfügt, dürfte nichts verlieren. Wer das braucht, misst es: Text mit `<ID>` von Hand einfügen, speichern, zurücklesen. Bis dahin gilt die Regel für den Agentenpfad, für den sie gemessen ist.

Bösartig ist der Fall, weil das Ergebnis **plausibel bleibt**. `findings/.md` sieht nicht nach einem Fehler aus, sondern nach einem Dateinamen. Ein Satz über den Unterschied zweier Schreibweisen wurde so zu einem Satz, der beide gleich nennt — ohne Fehlermeldung, ohne rotes Gate. Dieselbe Mechanik trifft das Finding-Template aus §5.1: dessen Überschrift `## Finding: <CHECK-ID> — <CHECK-TITLE>` wird beim Einfügen in ein Issue zu `## Finding:  — `.

**Regel:** Text, den ein Agent in einen PR-Body, ein Issue, einen Review-Kommentar oder den Tracker schreibt, schreibt Platzhalter als `{ID}`, `{slug}`, `{CHECK-ID}` und sagt einmal dazu, dass die geschweifte Form für die spitze steht. Danach **den gespeicherten Body zurücklesen und vergleichen** — die Umwandlung ist still, also ist die Gegenprobe der einzige Beleg. Derselbe Reflex wie beim Gegen-Test einer Mutation: ein Schritt ohne Rückmessung ist kein belegter Schritt.

### 0.6 Die Ziel-Revision festhalten (verbindlich)

`catalog_hash` hält fest, **womit** gemessen wurde. `target_sha` hält fest, **woran** — und erst beide zusammen machen einen Lauf reproduzierbar. Ohne die zweite Zahl teilt ein Commit, der mitten im Audit landet, den Report unbemerkt: Die Checks vor ihm beschreiben einen Baum, die danach einen anderen, und der Report präsentiert die Mischung als ein Urteil. **Ein Audit, dessen Ziel sich während des Laufs bewegt, ist kein Audit** — es ist eine Aussage über keine bestimmte Revision.

`target_dirty` steht daneben, weil ein sauberer SHA über einem verschmutzten Working-Tree einen Baum beschreibt, den es nur auf dieser Maschine gibt. Uncommittete Arbeit zu auditieren ist legitim; der Report darf nur nicht behaupten, er habe den genannten Commit geprüft.

Am Ende des Laufs — vor Schritt 6 — wird erneut geprüft:

```bash
python "$SKILL_BASE/tools/audit_init.py" verify-target "$OUTPUT_DIR"
# Exit 0: unverändert. Exit 1: HEAD bewegt, Working-Tree nachträglich verschmutzt,
#         oder gar keine Ziel-Revision aufgezeichnet.
```

Dieselbe Prüfung läuft automatisch im Pflicht-Gate aus Schritt 5.0 (`aggregate_results.py validate`). Dort gilt sie abgestuft, und die Abstufung ist Absicht:

| Lage | Gate | Warum |
|---|---|---|
| SHA aufgezeichnet, bewegt | **hard fail** | Die Findings beschreiben zwei Bäume |
| SHA aufgezeichnet, unverändert | pass | |
| Kein SHA aufgezeichnet | Warnung, Eintrag `target.status: unrecorded` | Läufe von vor `--target-repo` haben keinen; ein hard fail hier würde nur beibringen, `--skip-target-check` reflexhaft zu setzen — und damit auch den Fall abschalten, auf den es ankommt |
| Repo nicht mehr auffindbar | Warnung mit genanntem Pfad | Nur der Auditor weiss, wohin es verschoben wurde |

Jede dieser Lagen landet in `target.status` im Gate-Report — eine Warnung, die nur nach stderr geht, ist beim Lesen des Run-Verzeichnisses verschwunden.

---

## Schritt 1: Profil laden

**Ziel:** Den Server-Kontext aus dem Notion MCP Audit Tracker (DB-ID `a2736a65-677d-4cf3-9f94-e874f74a1975`) holen, damit nachfolgende Schritte die richtigen Checks filtern können.

### 1.1 Pflichtfelder aus dem Tracker

Bevor ein Audit beginnt, müssen diese Felder in der Audit-Tracker-Karte gesetzt sein:

| Feld | Werte | Verwendung im Audit |
|---|---|---|
| `Transport` | `stdio-only` / `dual` / `HTTP/SSE` | filtert Netzwerk-Checks |
| `SDK-Sprache` | `Python` / `TypeScript` | filtert die SDK-Checks und `IDENT-005` |
| `Auth-Modell` | `none` / `API-Key` / `OAuth-Proxy` | filtert OAuth-Checks |
| `Datenklasse` | `Public Open Data` / `Verwaltungsdaten` / `PII` | filtert PII-Checks und CH-Compliance |
| `Schreibzugriff` | `read-only` / `write-capable` | filtert HITL-Checks |
| `Deployment` | `local-stdio` / `Railway` / `Render` / `andere` | filtert Cloud-Checks |
| `MCP-Spec-Version` | `2025-11-25` / `2026-07-28` | wählt die Baseline — welche Hälfte des Katalogs geprüft wird |
| `Repo URL` | GitHub-URL | für Code-Review-Schritte |

Wenn ein Pflichtfeld fehlt, wird der Audit gestoppt und der User aufgefordert, das Feld zu füllen. **Audits mit unvollständigem Profil sind wertlos** — applicability wird falsch berechnet, die Findings werden unverlässlich.

**`MCP-Spec-Version` ist seit v2.0.0 Pflicht und hat bewusst keinen Default.** Während der Migrationswellen A–D stehen beide Protokollstände gleichzeitig im Portfolio. Ein Default würde die Frage für jedes Profil beantworten, das sie vergessen hat — und zwar still: Fünf Checks messen einen Gegenstand, den `2026-07-28` entfernt hat, vierzehn messen einen, den es davor nicht gab. Die falsche Antwort tauscht die geprüfte Hälfte des Katalogs aus, ohne dass irgendwo etwas rot wird. Das ist der `transport: HTTP`-Vorfall aus §1.3, eine Achse weiter und mit grösserer Reichweite.

### 1.2 Profil-Notation für interne Verwendung

Während des Audits arbeitet Claude mit einem konsolidierten Profil-Objekt:

```yaml
profile:
  name: zurich-opendata-mcp
  repo: https://github.com/malkreide/zurich-opendata-mcp
  transport: dual
  sdk_language: Python             # filtert SDK-001…006 und IDENT-005
  mcp_spec_version: "2025-11-25"   # 2025-11-25 | 2026-07-28 — wählt die Baseline
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
- **Fehlende Pflichtfelder:** alle 16 Profil-Top-Level-Felder plus `data_source.is_swiss_open_data`
- **Type-Mismatches:** `bool`-Feld mit String-Wert, `list`-Feld mit String-Wert, etc.
- **Unbekannte Werte in geschlossenen Vokabularen:** `transport` ausserhalb von `stdio-only` / `dual` / `HTTP/SSE`. Ein Wert, gegen den keine `applies_when`-Klausel je vergleicht, lässt Checks **still** wegfallen — der Evaluator wirft dafür keinen Fehler, weil ein unbekannter *Wert* ein ganz normaler String ist (anders als ein unbekanntes *Feld*, das `UnknownFieldError` auslöst).

Bei Exit-1 wird Step 2 nicht gestartet. Der Output zeigt strukturiert, welche Felder betroffen sind (`missing` / `placeholder` / `type_mismatch` / `enum_mismatch`). Nutze das, um den User zur Korrektur aufzufordern.

**Warum `enum_mismatch` ein eigenes Gate braucht:** Ein Profil mit `transport: HTTP` — eine Schreibweise, die dieses Repo selbst empfohlen hat — verlor `SCALE-002`, `SCALE-003`, `SCALE-007` und `SDK-004`, zwei davon `high`, während jede `transport != "stdio-only"`-Klausel weiterhin griff. Das Profil war halb erkannt, und der Report meldete einen sauberen Lauf über einen kleineren Katalog als behauptet. Genau der Fall aus `OPS-005`: Was nicht gelaufen ist, sieht aus wie bestanden.

---

## Schritt 2: Check-Katalog laden

**Ziel:** Den vollständigen Katalog (`checks/*.md`) parsen und nach `category` + `severity` indizieren.

### 2.1 Zwölf Kategorien

| Kategorie | Quelle | Typische Anzahl Checks | Status |
|---|---|---|---|
| `ARCH` | PDF Sec 2 + Anhang A + Custom + Spec 2026-07-28 — Tool-Design, Annotations, Idempotency, Retry-Politik, Repo-Struktur, Versionsquelle, Spec-Versionierung, Stateless-Konformität, Handles, Extensions | 10–22 | 22 / 22 ✅ |
| `SDK` | PDF Sec 3 — FastMCP, TypeScript, Zod, Lifecycle | 5–7 | 6 / 6 ✅ |
| `SEC` | PDF Sec 4 + Anhang B + Spec 2026-07-28 — Security (grösste Kategorie) | 20–28 | 27 / 27 ✅ |
| `SCALE` | PDF Sec 5 + Spec 2026-07-28 — Transport, LB, Container, Gateway, Pflichtheader, Abkündigungsfristen | 5–11 | 10 / 10 ✅ |
| `OBS` | PDF Sec 6 + Anhang B10 + Custom — Logging, Errors, SIEM, Tracing, Bereitschaftsmarker | 5–8 | 8 / 8 ✅ |
| `HITL` | PDF Sec 7 + Spec 2026-07-28 — Sampling, Human-in-the-Loop, MRTR | 4–6 | 6 / 6 ✅ |
| `CH` | Custom — DSG/EDÖB, Schweiz-Compliance | 5–8 | 8 / 8 ✅ |
| `OPS` | Anhang C + Custom — Test-Strategie, Doku, Phasenarchitektur, Audit-Redlichkeit, Pipeline-Ehrlichkeit, reproduzierbare Urteile, ausfuehrbare Anleitungen, pruefbare Guards | 3–8 | 8 / 8 ✅ |
| `FID` | Custom — Datentreue: Scope, Recall, Leermengen, Antwortstruktur | 4–6 | 6 / 6 ✅ |
| `IDENT` | Custom — Identität: User-Agent, `__version__`, Manifest, Doku-Version, Release-Gap, Gesundheit des Artefakts | 5–8 | 7 / 7 ✅ |
| `DRIFT` | Custom — Upstream-Vertrag und Repo-Prosa: Endpoint-Drift, Fallback-Semantik, Testgüte, CHANGELOG gegen Code | 4–7 | 6 / 6 ✅ |
| `DEP` | Custom — Auflösungsraum des publizierten Artefakts: Obergrenzen, Major-Wechsel | 1–3 | 1 / 1 ✅ |
| **Total** | | **~99** | **115 / 115 ✅** |

### 2.2 Severity-Stufen

| Stufe | Bedeutung | Konsequenz |
|---|---|---|
| `critical` | Sicherheitslücke oder Compliance-Bruch | Blockiert Produktion. Muss vor Release gefixt sein. |
| `high` | Architektureller Mangel mit signifikantem Risiko | Im laufenden Sprint fixen, max. 1 Sprint Karenz. |
| `medium` | Best-Practice-Verletzung, kein akutes Risiko | Im nächsten Sprint planen. |
| `low` | Polish, Optimierung, Stilistik | Backlog. Bei Tippfehler-Audits: low + auto-fix. |

### 2.3 Adoptionsstufen

Severity sagt, **wie schlimm** ein Verstoss ist. Die Adoptionsstufe sagt, **ob der Katalog das Portfolio schon darauf festnageln darf**. Zwei verschiedene Fragen, und ohne die zweite trifft jeder neue Check am Tag des Merges 30+ Server als rote Pipeline — so werden Checks zurückgenommen statt übernommen.

| Stufe | Bedeutung | Konsequenz |
|---|---|---|
| `enforced` | Der Katalog hält das Portfolio daran fest | Ein `fail` auf `critical`/`high` blockiert Production-Readiness |
| `advisory` | Der Check meldet, urteilt aber noch nicht | Finding wird erzeugt, gezählt und mit voller Severity geführt — blockiert aber nicht |

```yaml
adoption: advisory   # optional; fehlt das Feld, gilt `enforced`
```

Die Adoptionsstufe ist die eine von zwei Achsen, auf denen ein Check aufhören kann zu beissen. Die andere ist die **Spec-Baseline** — siehe [§2.7](#27-spec-baseline-welcher-protokollstand-gemessen-wird). Sie beantworten verschiedene Fragen: `adoption` sagt, ob der Katalog **schon** urteilen darf; `spec_baseline` sagt, ob der Check das Protokoll **überhaupt noch** beschreibt.

**Advisory versteckt nichts.** Das Finding entsteht, trägt seine Severity und erscheint im Report. Nur das Veto entfällt. Eine Stufe, die den Befund unterdrückte statt nur sein Veto, wäre schlimmer als gar keine Stufe.

Ein Advisory-Finding auf blockierender Severity wird im Report unter `advisory_findings` **namentlich genannt** — auch bei grünem Verdikt. Wer später promoviert, weiss vorher, was rot würde.

**Der Weg eines neuen Checks:**

1. Als `advisory` mergen. Der Check läuft im nächsten Portfolio-Durchlauf mit und meldet, ohne zu blockieren.
2. Die Advisory-Findings über das Portfolio auswerten: Ist der Check richtig geschnitten? Produziert er Fehlalarme?
3. Wenn die betroffenen Server nachgezogen haben — oder der Rückstand bewusst akzeptiert ist —, auf `enforced` promovieren. Die Promotion gehört in den CHANGELOG, nicht in einen Diff, den niemand liest. Wird sie auf `critical` oder `high` ausgesprochen, ist sie ausserdem ein **Re-Audit-Auslöser** nach [§5d](#versionierung-des-check-katalogs): Ab diesem Moment verlieren Server ihre Production-Readiness, deren letztes Audit dasselbe Finding noch als folgenlos führen durfte.

   - **e) Spec-Baseline verengt oder Prüfkriterium an eine neue Revision angepasst.** Ein Sonderfall von b) und c) mit eigener Auslösebedingung: Wechselt ein Server seine `mcp_spec_version`, ändert sich die geprüfte Katalogmenge in **beide** Richtungen, ohne dass an einem einzigen Check etwas geändert wurde. Das Audit davor hat gegen einen anderen Katalog gemessen als das danach — nicht gegen einen kleineren oder grösseren, sondern gegen einen teilweise anderen. Ein `production_ready: true` von vor der Migration trägt deshalb nicht über sie hinweg. **Die Migration eines Servers ist ein Re-Audit-Auslöser, unabhängig davon, ob der Katalog sich bewegt hat.**

   Wird Schritt 2 übersprungen — Promotion ohne dazwischenliegenden Portfolio-Durchlauf —, stützt sie sich auf «Rückstand bewusst akzeptiert» und **nicht** auf ausgewertete Advisory-Findings. Beides ist zulässig; welches von beidem gilt, gehört in den CHANGELOG-Eintrag. Eine Promotion, die Evidenz behauptet, die nicht erhoben wurde, ist der Fehler aus `OPS-004`.

Ein Tippfehler in `adoption` ist ein **harter Fehler** beim Katalog-Parsen. Eine stille Demotion wäre die leiseste Art, einen Check zu verlieren.

**Der Katalog ist autoritativ**, nicht die Ergebnisdatei:

```bash
python tools/aggregate_results.py aggregate verification-results.json \
    --checks-dir "$SKILL_BASE/checks/" --out summary.json
```

Ohne `--checks-dir` gilt, was in `verification-results.json` steht — und ein fehlendes Feld bekommt dort still den `enforced`-Default. Das ist die sichere Richtung, aber es heisst auch: Eine Advisory-Stufe wirkt nur, wenn der Katalog gelesen wird.

### 2.4 Check-Schema

Jeder Check ist eine eigenständige Markdown-Datei im Format:

```markdown
---
id: SEC-001
title: "Confused Deputy: Per-Client Consent Flow"
category: security
severity: critical
applies_when: 'auth_model == "OAuth-Proxy"'
spec_baseline: beide          # optional; fehlt das Feld, gilt `beide`
adoption: enforced            # optional; fehlt das Feld, gilt `enforced`
pdf_ref: "Sec 4.1"
spec_ref: "SEP-xxxx (PR xxxx)"   # bei Checks aus einem Spec-Changelog
evidence_required: 3
---

# Body mit Description, Verification, Pass Criteria, Remediation
```

Ein Check, der aus einem Spec-Changelog stammt, trägt in `spec_ref` seine **SEP-Nummer**. Das ist keine Zierde: Die Begründung eines solchen Checks liegt nicht im Katalog, sondern in einem Dokument, das sich weiterentwickelt. Ohne die Nummer ist bei der nächsten Revision nicht feststellbar, ob ein Check noch die aktuelle Fassung seiner Quelle wiedergibt — und genau das ist der Zustand, aus dem `OBS-001` acht Monate lang das Gegenteil der Spec gelehrt hat.

Details siehe `templates/finding.md` und beliebige Datei in `checks/`.

### 2.5 Reichweite vor neuer Regel

Ein Fund, den kein Check gemeldet hat, löst einen Reflex aus: einen neuen Check schreiben. Das ist die teure Richtung, und meistens die falsche. Häufiger als eine fehlende Regel ist eine vorhandene Regel, die zu eng angewandt wurde.

**Vor jedem neuen Check drei Fragen, in dieser Reihenfolge:**

1. **Gibt es den Check schon, aber `applies_when` schliesst den Fall aus?** Dann ist die Klausel das Problem, nicht der Katalog. Reichweite korrigieren.
2. **Gibt es den Check schon, aber seine Verification nennt nur *einen* Endpoint, *ein* Artefakt, *eine* Stelle?** Dann prüft er die richtige Sache am falschen Umfang. Verification erweitern.
3. **Fragt wirklich kein Check danach — ist es eine eigene Prüfdimension?** Erst dann ein neuer Check.

Nur die dritte Frage rechtfertigt eine neue Datei in `checks/`.

**Beide Ausgänge sind schon vorgekommen:**

- *Reichweite, nicht Regel:* Die Guard-Tests in `tests/test_skill_counts.py` pinnten Katalogzahlen gegen die Doku — und liessen trotzdem eine Überschrift «Zehn Kategorien» über einer Tabelle mit elf Zeilen durch. Es fehlte kein Test. Der vorhandene reichte nur bis zur Intro-Zeile. Die Korrektur war eine erweiterte Verification, kein neuer Check.
- *Wirklich neu:* Die Kategorie `FID` entstand aus `termdat-mcp#11` an einem Server, der 68 Checks bestanden hatte. Keine der acht damaligen Kategorien stellte die Frage, ob der Server liefert, was die Quelle hat. Das war keine zu enge Klausel, sondern eine fehlende Dimension.

**Warum die Reihenfolge zählt:** Zwei Checks, die einander teilweise überlappen, sind schlimmer als einer mit korrekter Reichweite. Sie doppeln das Finding, und wenn der Server die Ursache behebt, bleibt der zweite rot — der Fix sieht aus, als hätte er nicht gewirkt. Ein Katalog, der per Reflex wächst, wird ausserdem irgendwann nicht mehr vollständig gelesen.

**Der Gegenfehler:** Einen Check so weit dehnen, bis er ein Sammelbehälter wird. Das Signal ist konkret — wenn die Erweiterung ein `oder` in die Pass-Criteria zwingt, das mit dem ursprünglichen Kriterium nichts zu tun hat, ist es ein neuer Check. Ein Check muss in **einem** Schritt behebbar bleiben.

**Eselsbrücke:** *«Zuerst fragen, ob die Regel zu kurz gegriffen hat — nicht, ob sie fehlt.»*

### 2.6 Ein Check, der nichts findet, muss sagen können, ob er gesucht hat

Diese Regel gilt für den **Katalog selbst**, nicht für einen einzelnen Server. Sie ist die Bedingung dafür, dass die Ergebnisse aller anderen Checks etwas bedeuten.

Ein Check hat drei mögliche Ausgänge, nicht zwei:

| Ausgang | Bedeutung |
|---|---|
| `pass` | Gesucht, und der geprüfte Zustand liegt vor |
| `fail` | Gesucht, und ein Verstoss liegt vor |
| `todo` / `unverified` | **Nicht gesucht, oder gesucht und die Form nicht erkannt** |

Die dritte Zeile ist die, die in der Praxis verschwindet. «Nichts gefunden» und «nicht hingeschaut» erzeugen dieselbe Beobachtung — eine leere Ergebnisliste — und werden deshalb ohne Zutun zum selben Ausgang zusammengelegt. Der Ausgang, zu dem sie zusammenfallen, ist immer `pass`, weil ein Werkzeug meldet, was es findet, und nicht, was es nicht gesucht hat.

**Der Beleg** steht in `IDENT-001`: Die erste Fassung der Identitäts-Probe erklärte **24 Pakete für unauffällig, von denen 16 drifteten**. Kein Fehler in der Vergleichslogik — die Probe erkannte die Form des User-Agents nicht (verschachteltes Dict, Literal im Konstruktor, f-String ohne Ziffer) und meldete für diese Pakete nichts. Nichts las sich als «in Ordnung». Zwei Drittel der Befunde gingen an genau dieser Stelle verloren, und die Zusammenfassung war grün.

**Was das für jeden Check im Katalog heisst:**

1. **Jeder `automated`-Modus braucht einen Ausgang für «Harness lief nicht».** Ein Exit-Code, ein Statuswert, irgendetwas Unterscheidbares — und er wird auf `todo` abgebildet, nie auf `pass`. `IDENT-006` und `IDENT-007` tun das mit Exit `127`, `IDENT-001` mit `unverified`.
2. **Eine Pass-Criterion in der Form «kein X gefunden» ist unvollständig.** Sie muss sagen, *wie* gesucht wurde und woran man erkennt, dass die Suche funktioniert hat. Sonst besteht sie jedes Repo, in dem das Werkzeug versagt hat.
3. **Wo die Erkennung selbst scheitern kann, gehört das als eigener Befundwert in den Check** — nicht in eine Fussnote. `IDENT-001` führt `unverified` als Ergebnis mit eigenem Exit-Code, gerade damit es nicht in `pass` fällt.
4. **Gegenprobe beim Schreiben des Checks:** Die Verifikation einmal gegen ein Repo laufen lassen, in dem der Verstoss sicher vorliegt. Meldet sie nichts, prüft sie nichts — dieselbe Gegenprobe wie bei jedem Gate, siehe [§4.1](#41-drei-verifikationsmodi).

**Verhältnis zu `OPS-005`:** Dort geht es um die Pipeline eines auditierten Servers — ein Test, der nie lief, sieht aus wie ein Test, der bestand. Hier geht es eine Ebene höher um die Bauart der Checks selbst. Dieselbe Asymmetrie, zwei verschiedene Adressaten: `OPS-005` prüfen wir an fremden Repos, §2.6 schulden wir dem eigenen Katalog.

**Eselsbrücke:** *«Schweigen ist kein Freispruch.»*

### 2.7 Spec-Baseline: welcher Protokollstand gemessen wird

Seit v2.0.0 trägt jeder Check ein zweites Feld, das über seine Anwendbarkeit entscheidet:

```yaml
spec_baseline: 2026-07-28    # 2025-11-25 | 2026-07-28 | beide (Default)
```

Es wird gegen `mcp_spec_version` aus dem Profil gehalten. Der Anlass ist konkret: `2026-07-28` hat Sitzungen, den `initialize`-Handshake und die SSE-Resumability entfernt. Fünf Checks messen damit einen Gegenstand, den es nicht mehr gibt; vierzehn messen einen, den es vorher nicht gab. Während der Wellen A–D stehen beide Stände gleichzeitig im Portfolio.

| Wert | Bedeutung |
|---|---|
| `2025-11-25` | misst gegen das Protokoll vor der Stateless-Umstellung |
| `2026-07-28` | misst gegen das Protokoll danach |
| `beide` | protokollunabhängig — Default, wenn das Feld fehlt |

**Warum das eine eigene Stufe ist und keine `applies_when`-Klausel.** Technisch ginge beides; `mcp_spec_version == "2026-07-28"` wäre ein gewöhnlicher Feldvergleich. Die Trennung ist die Entscheidung:

- `applies_when` beantwortet: *Ist dieser Server die Art von Server, um die es geht?*
- `spec_baseline` beantwortet: *Beschreibt dieser Check noch das Protokoll, das dieser Server spricht?*

Zusammengefaltet erscheinen beide Ausgänge im Applicability-Report als dasselbe `no-match` — und die Unterscheidung, die §3.4 zwischen «Katalog hat sich geändert» und «Profil hat sich geändert» zieht, verliert ihre dritte Möglichkeit. Ein Check, der wegfällt, weil der Server stdio-only ist, verlangt eine Profilkorrektur; einer, der wegfällt, weil der Server migriert ist, verlangt gar nichts. Der Report muss das sagen können.

**Drei Ausgänge, nicht zwei** — dieselbe Konstruktion wie in §2.6:

| Reason | Bedeutung |
|---|---|
| *(leer)* | Baseline passt, `applies_when` entscheidet |
| `baseline-mismatch` | Geprüft und ausgeschlossen: der Check misst die andere Revision |
| `baseline-unresolved` | **Nicht geprüft** — das Profil sagt nicht, welchen Stand der Server spricht |

Der dritte ist der Grund für den eigenen Wert. Fiele er mit dem zweiten zusammen, sähe ein Profil mit vergessenem Feld exakt aus wie ein sauberer Lauf über einen kleineren Katalog. `eval_applicability.py catalog` exitet deshalb mit **3**, wenn ein Check unresolved bleibt.

**Verengen statt löschen.** Ein Check, dessen Gegenstand verschwunden ist, wird nicht entfernt und nicht umbenannt — er bekommt `spec_baseline: 2025-11-25` und **nennt in seinem Kopf den Nachfolger**. Löschen würde die Frage mit dem Check verschwinden lassen; ohne Nachfolgerangabe wäre nicht auffindbar, wo sie jetzt gestellt wird. Die fünf verengten Checks sind `SCALE-002`, `SCALE-003`, `SCALE-007`, `SDK-004` und `SEC-009`.

**Eselsbrücke:** *«`adoption` sagt, ob schon geurteilt wird. `spec_baseline` sagt, ob noch das Richtige gemessen wird.»*

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

**Vor der Klausel läuft die Baseline-Stufe** ([§2.7](#27-spec-baseline-welcher-protokollstand-gemessen-wird)). Die Reihenfolge ist nicht kosmetisch: Beschreibt ein Check ein Protokoll, das dieser Server nicht spricht, sagt sein `applies_when`-Urteil nichts Berichtenswertes — die verglichenen Profilfelder sind zwar gültig, aber der geprüfte Gegenstand existiert nicht. Der Report nennt dann den gröberen Grund.

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
         MCP spec: 2025-11-25

Spec baseline: 11 check(s) dropped as written for the other revision
  dropped: ARCH-015, ARCH-016, ARCH-017, ARCH-018, ARCH-020, ARCH-021,
           HITL-006, SCALE-008, SCALE-010, SEC-025, SEC-027

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

**Ausnahme: Baseline-Ausfälle werden namentlich genannt.** Sie sind kein Profil-Detail, sondern eine Aussage über den Katalog — und über die Migration eines konkreten Servers bewegen sie zweistellige Zahlen in beide Richtungen. Ein Lauf, der das verschweigt, meldet einen sauberen Durchgang über einen kleineren Katalog, als er behauptet. Das ist der Fehler aus `OPS-005`, gestellt an das Audit selbst.

Bleibt ein Check `baseline-unresolved`, wird Schritt 4 **nicht gestartet**: Das Profil hat nicht gesagt, welchen Protokollstand der Server spricht, und die betroffenen Checks sind weder gelaufen noch ausgeschlossen.

### 3.4 Applicability gegen den Vorlauf vergleichen

Bei einem Re-Audit ist die interessante Frage nicht, welche Checks anwendbar sind, sondern **welche es nicht mehr oder neu sind**. Dieser Vergleich gehört wie jeder andere in ein Skript:

```bash
# Auswertung des laufenden Audits sichern — der Katalog-Stand des Vorlaufs
# liegt vielleicht nicht mehr auf der Platte, die gespeicherte Auswertung schon.
python tools/eval_applicability.py catalog profile.yaml > audits/<run>/applicability.json

# Gegen den Vorlauf halten
python tools/eval_applicability.py diff \
    audits/<vorlauf>/applicability.json \
    audits/<run>/applicability.json \
    --labels vorlauf,jetzt --format table
# Exit 0: identisch. Exit 1: Unterschied. Exit 2: eine Seite war leer.
```

Der Helfer trennt zwei Dinge, die eine reine Anwendbarkeits-Differenz gleich aussehen lässt: **welche Checks überhaupt ausgewertet wurden** (der Katalog hat sich geändert) und **welche anwendbar waren** (das Profil hat sich geändert). Das sind verschiedene Ereignisse mit verschiedenen Konsequenzen.

**Und er verweigert den Vergleich, wenn eine Seite leer parst.** Eine handgeschriebene Fassung dieses Diffs meldete einmal «0 == 0, identisch» — beide Seiten hatten wegen eines falschen Pfads nichts geparst, und die Arithmetik stimmte. Das ist schlimmer als kein Vergleich: Ohne Helfer bleibt die Frage offen und wird irgendwann beantwortet; mit ihm schliesst eine grüne Zeile die Frage mit Belegen, die nie erhoben wurden. Dieselbe Fehlerklasse wie `OPS-005` (was nicht lief, sieht aus wie bestanden) und `FID-003` (eine Leermenge, die der Server für den Aufrufer deutet). Ein leerer Input ist kein Befund von Gleichheit, sondern das Fehlen einer Beobachtung.

Alle Vergleichs-Helfer im Repo laufen deshalb über `tools/compare_guard.py`. Wo eine leere Seite tatsächlich die erwartete Antwort ist, gibt es `--allow-empty` — als Flag und nicht als stille Toleranz, damit die Entscheidung eine Spur hinterlässt.

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

#### Whitespace normalisieren, bevor auf Text geprüft wird

Viele Checks prüfen, ob eine Aussage in einem Text steht: ein Hinweis in einer Tool-Description, ein Abschnitt in einer README, ein Satz in einem Docstring. Der naive Weg schlägt fehl:

```python
assert "not in TERMDAT" in tool.__doc__      # FALSCH
```

Der Docstring enthält den Satz. Er enthält ihn nur mit einem Zeilenumbruch zwischen `in` und `TERMDAT`, weil das Quellformat auf 88 Zeichen umbricht. Der Test meldet «fehlt», die Doku ist da. Das ist genau in diesem Portfolio passiert, beim Verifizieren eines Coverage-Hinweises, der korrekt geschrieben war.

**Falsch-negativ ist hier der teure Fehler.** Ein Fund «Doku fehlt» führt zu einem Finding, einer Remediation-Empfehlung und einer Änderung an etwas, das bereits stimmte — im schlimmsten Fall zu einem Duplikat des vorhandenen Satzes. Ein Prüfergebnis, das an einem Umbruch hängt, prüft die Formatierung, nicht den Inhalt.

**Regel: Zuerst normalisieren, dann vergleichen.**

```python
import re

def flat(text: str) -> str:
    """Zeilenumbrüche und Mehrfach-Leerzeichen zu je einem Leerzeichen."""
    return re.sub(r"\s+", " ", text or "").strip()

assert "not in TERMDAT" in flat(tool.__doc__)        # RICHTIG
```

Auf der Kommandozeile dasselbe — `grep` ist zeilenweise und findet mehrzeilige Phrasen nie:

```bash
# FALSCH: findet nichts, sobald die Phrase über zwei Zeilen läuft
grep -q "not in TERMDAT" src/server.py

# RICHTIG: erst glätten, dann suchen
tr '\n' ' ' < src/server.py | tr -s ' ' | grep -q "not in TERMDAT"

# Oder ripgrep im Multiline-Modus, mit \s+ statt Leerzeichen
rg -U 'not\s+in\s+TERMDAT' src/server.py
```

**Was normalisiert werden muss** — überall dort, wo der Text für Menschen umbricht und die Umbruchstelle keine Bedeutung trägt: Docstrings und Tool-Descriptions, Markdown-Fliesstext, YAML-Folded-Blöcke (`>`), gerenderte Reports, JSON-Felder mit eingebettetem `\n`.

**Was nicht normalisiert werden darf:** Code-Blöcke, Einrückung als Syntax (Python, YAML-Struktur), Diff-Ausgaben, alles wo eine Zeile die Einheit ist — dort ist der Umbruch der Inhalt.

**Gegenprobe, wie bei jedem Gate:** Die Assertion einmal gegen einen Text laufen lassen, in dem die Phrase wirklich fehlt. Eine Prüfung, die nach der Normalisierung *immer* zutrifft, hat nur gelernt, alles zu bestehen.

#### Negative Kontrolle: ein Kommando, das läuft, misst nicht automatisch das Richtige

§2.6 behandelt den Fall, dass ein Werkzeug **nichts** meldet: Hat es gesucht? Dieser Abschnitt behandelt den gefährlicheren Fall — das Werkzeug meldet **etwas**, das Ergebnis ist plausibel, und es misst trotzdem nicht, was der Auditor glaubt. Ein leeres Ergebnis macht misstrauisch; ein gefülltes nicht.

Die Regel gilt für die Ad-hoc-Kommandos, mit denen während Schritt 4 ein Sachverhalt festgestellt wird — nicht für die Checks, die im Katalog stehen. Genau diese Kommandos speisen die Evidenz in die Findings, und genau sie werden nie gegengeprüft, weil sie Wegwerf-Befehle sind.

**Zwei reale Fälle, beide aus einer einzigen Sitzung, beide von der auditierenden Instanz selbst:**

| Kommando | Gemeldet | Tatsächlich |
|---|---|---|
| `grep -E "^\s+- (run\|uses):"` über drei CI-Dateien | «je ein Schritt» → Schluss: die CI tut nichts | Die Dateien haben 9 bis 11 Schritte. Das Muster traf nur `- uses:`-Zeilen, weil die übrigen Schritte mit `- name:` beginnen und `run:` eine Zeile tiefer steht. |
| `pip install "ruff>=0.6,<0.7"` mit unterdrückter Ausgabe | Installation angenommen | Sie schlug fehl. `ruff --version` meldete 0.15.8, und der anschliessende Versionsvergleich lief zweimal unter derselben Version. |

Beide Ergebnisse waren in sich stimmig. Der erste hätte einen Befund über drei fremde Repositories erzeugt, der falsch gewesen wäre; er ist nur aufgefallen, weil vor dem Berichten eine der Dateien gelesen wurde.

**Regel: Jede Zähl- oder Suchprüfung, deren Ergebnis in einen Befund eingeht, braucht eine negative Kontrolle** — die gesuchte Sache absichtlich herstellen und sehen, dass das Kommando sie findet. Nicht «der Befehl lief», sondern «der Befehl schlägt an, wenn es etwas zu finden gibt».

```bash
# Behauptung: "in diesen Dateien steht kein Formatgate"
grep -c "format --check" .github/workflows/*.yml        # → 0

# Negative Kontrolle, drei Sekunden: findet das Muster überhaupt etwas?
printf 'ruff format --check .\n' > /tmp/probe.yml
grep -c "format --check" /tmp/probe.yml                 # → 1, sonst misst das Muster nichts
```

Drei Faustregeln, die die meisten Fälle abdecken:

- **Ausgabe nie unterdrücken, deren Fehlschlag das Ergebnis verfälscht.** `2>/dev/null`, `| tail -0` und `|| true` verbergen genau den Fall, der das Messergebnis kippt.
- **Was ein Werkzeug installiert oder auswählt, danach zurückfragen.** `--version` nach dem Installieren, `git rev-parse HEAD` nach dem Auschecken. Eine Version, die man annimmt, ist keine Version, die man gemessen hat.
- **Eine Null ist eine Behauptung.** «0 Treffer» heisst entweder «nichts da» oder «Muster greift nicht». Ohne negative Kontrolle sind die beiden ununterscheidbar — und die falsche Lesart ist immer die bequeme.

**Wo das im Katalog bereits gelebt wird:** Gemessen **12 von 98** Checks — `ARCH-013`, `DRIFT-003`, `FID-003`, `FID-004`, `IDENT-002`, `IDENT-004`, `OPS-005`, `OPS-006`, `OPS-007`, `OPS-008`, `SCALE-007`, `SEC-024`. Die Zahl ist selbst mit negativer Kontrolle erhoben: Der Detektor lief gegen je eine Datei mit und ohne die Formulierung (1 beziehungsweise 0 Treffer), sonst wäre auch sie nur plausibel. Das ist keine Quote, die man per Gate erzwingt — ein Gate, das bei 86 Checks anschlägt, wird abgeschaltet, und die Zahl misst ohnehin die Erwähnung, nicht die Praxis. Sie steht hier als Ausgangswert, damit sichtbar bleibt, in welche Richtung sie sich bewegt.

#### Jede Zahl trägt ihre Herkunft — und eine abgeleitete speist kein Gate

`build_report.py` zieht jede Zahl aus `summary.json`; der erzeugte Report kann deshalb nicht driften. Driften können die **handgeschriebenen** Zahlen: die `SECURITY.md` des auditierten Repos, ein PR-Body, eine Tracker-Karte, ein Satz im Chat. Sie entstehen aus dem Gedächtnis oder aus einer Vorhersage — und sie überleben den Lauf, den sie beschreiben.

Drei Herkünfte, die auseinandergehalten gehören:

| Herkunft | Bedeutung | Darf ein Gate speisen |
|---|---|---|
| `gemessen` | In diesem Lauf erhoben, steht in `summary.json` | ja |
| `abgeleitet` | Aus anderen Zahlen gefolgert oder vorhergesagt | **nein** |
| `übernommen` | Aus einem früheren Lauf oder fremden Dokument zitiert | nein, und mit Datum des Ursprungslaufs |

**Der Fall, der das erzwungen hat, ist nicht «Summe falsch».** Über diese Sitzung: vier Vorhersagen, zwei exakt, zwei falsch — und eine davon war in der **Zusammensetzung** falsch, während die Summe stimmte. `30 pass / 4 partial / 2 fail` gegen ein gemessenes `30 / 5 / 1`. Beides ergibt 36. Der Satz las sich bestätigt, und das eine Finding, das von `fail` nach `partial` gewandert war, verschwand aus der Wahrnehmung. **Eine Prüfung, die nur die Gesamtzahl vergleicht, lässt genau das durch** — deshalb vergleicht `tools/check_reported_numbers.py` je Status.

```bash
# Vor dem Abschluss: jedes Dokument, das Zahlen dieses Laufs nennt
python tools/check_reported_numbers.py audits/<run>/summary.json \
    <ziel-repo>/SECURITY.md <ziel-repo>/README.md
```

Findet das Werkzeug in einer Datei **gar keine** Angabe, ist das kein Bestehen, sondern der Ausgang `ungeprüft` — meist hat sich ein Wortlaut geändert und das Muster greift ins Leere. Exit 1, mit Nennung der Datei.

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

**Der zweite Punkt wird erzwungen, nicht nur gefordert.** `aggregate --checks-dir`
hält jedes beurteilte Ergebnis an das `evidence_required` seines Checks und
schreibt keine `summary.json`, wenn eines darunter liegt. Das war lange nicht so:
das Feld stand in der Frontmatter aller 90 Checks und diese Regel hier im Text,
gelesen hat es kein Werkzeug — ein `pass` mit leerer `evidence`-Liste kam
unbehelligt durch. Die Asymmetrie ist der Grund, warum das zählt: an einem
unbelegten `fail` arbeitet jemand weiter, ein unbelegtes `pass` **beendet die
Beschäftigung** mit dem Check, und nichts widerspricht ihm je.

`not_verified` schuldet einen Punkt statt der vollen Zahl — es hat
definitionsgemäss keinen Beleg in *keine* Richtung, kann aber immer benennen, was
versucht wurde. `todo` und `n/a` behaupten nichts und schulden nichts. Details in
[`docs/verification-results-schema.md`](docs/verification-results-schema.md).

**Und wenn sich gar nichts feststellen liess: `not_verified`.** Das ist ein eigener Status mit eigenem Zähler, kein Prosa-Begriff. Bis er in `VALID_STATUSES` aufgenommen wurde, stand die Regel in `OPS-004` («ein `pass` beruht auf einem positiven Beleg … sonst `not_verified`»), während `tools/aggregate_results.py` den Wert zurückwies — wer die Regel befolgen wollte, bekam einen Schema-Fehler und trug am Ende `pass` ein. Genau das Ergebnis, das `OPS-004` verbietet. Eine Regel, deren Einhaltung das Werkzeug unmöglich macht, ist keine strenge Regel; sie ist eine Regel, die sich in ihr Gegenteil auflöst.

| Status | Bedeutung | Abgrenzung |
|---|---|---|
| `pass` | Positiver Beleg vorhanden | Nicht: leerer `grep` |
| `not_verified` | Angeschaut, kein Ergebnis erzielt | Werkzeug nicht erreichbar, Verhalten nur produktiv reproduzierbar, Suchmuster nicht als greifend nachweisbar |
| `todo` | Noch nicht angeschaut | Arbeitsliste, nicht «Offen» |

`not_verified` blockiert kein Release — ein unbeantwortbarer Check ist kein fehlgeschlagener — steht aber neben dem Urteil statt darin: `summary.json` führt `not_verified_findings`, der Report nennt sie in der Executive Summary und hängt sie ans Production-Readiness-Flag («YES (über 3 nicht verifizierte Checks)»). Ein grünes Urteil über eine grosse unverifizierte Menge ist eine andere Behauptung als ein grünes Urteil über keine, und `OPS-004` verlangt, dass der Leser die beiden unterscheiden kann.

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

Das Gate prüft drei Dinge, nicht eines: dass pro erwarteter ID eine Datei existiert, dass keine unerwartete ID eine hat, **und dass jede Datei etwas sagt**.

Die dritte Prüfung gibt es, weil ihr Fehlen einen echten False-Pass verursacht hat. Ein Carry-forward-Schritt schrieb in zwei Läufen 16 Findings als Null-Byte-Platzhalter: die älteren Läufe benennen Dateien `<ID>-<slug>.md`, das Skript suchte ein blankes `<ID>.md`, fand nichts und legte einen leeren Stub an, den es nie füllte. Beide Verzeichnisse meldeten `consistent: true`, weil Existenz das Einzige war, wonach gefragt wurde.

**Ein leeres Finding-Dokument ist schlimmer als ein fehlendes.** Ein fehlendes fällt durchs Gate; ein leeres kam durch und sagte einem Leser nichts über eine Findung, die offen ist — und die `SECURITY.md` der auditierten Repos verweisen auf genau diese Verzeichnisse als Beleg für die offene Menge.

**Der Übertrag aus dem Vorlauf gehört ebenfalls in ein Skript.** Bei einem Re-Audit bleiben die meisten Findings unverändert, und sie aus dem vorherigen Lauf zu kopieren ist richtig — aber genau dieser Schritt ist zweimal von Hand gemacht und zweimal falsch gemacht worden. Beim ersten Mal suchte er `findings/<ID>.md`, während der Quell-Lauf `<ID>-<slug>.md` benannt hatte; er fand nichts, schrieb einen leeren Platzhalter und füllte ihn nie. Beim zweiten Mal war der Quell-Lauf falsch gewählt, mit demselben Ergebnis.

`tools/carry_forward.py` löst beide Namensformen auf, überspringt leere Quellen statt sie weiterzureichen, überschreibt handgeschriebene Findings des laufenden Audits **nicht**, ersetzt leere Stubs an Ort und Stelle (statt eine zweite Datei danebenzulegen) und exitet 1 mit den IDs, für die es keine Quelle gab. Was danach fehlt, schreibt der Auditor von Hand — sichtbar, statt als Null-Byte-Datei.

**Die allgemeine Regel dahinter:** Was du zweimal von Hand gemacht hast, wird ein Skript. §0.3 verbietet Inline-Heredocs wegen der Quoting-Fallen; der tiefere Grund ist dieser hier — alle vier realen Fehler dieser Methodik lagen nicht in der Prüflogik, sondern im Transport von Zustand zwischen Läufen.

`--min-substance` zählt Nicht-Whitespace-Zeichen und steht auf 1, fängt per Default also nur den eindeutigen Fall. Höher setzen, wenn ein Lauf auch Stubs ablehnen soll — bewusst nicht höher vorbelegt, weil ein knappes Finding legitim ist und ein Guard, der Fehlalarm schlägt, umgangen wird.

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

# 4. Unveränderte Findings aus dem Vorlauf übernehmen — NIE von Hand kopieren
python tools/carry_forward.py audits/<run>/ --from audits/<vorlauf>/
#    Übrig bleibt, was der Helfer nicht finden konnte: genau das von Hand schreiben.

# 5. Nach dem Schreiben: Validation-Gate (hard fail bei Mismatch ODER leeren Dateien)
python tools/aggregate_results.py validate audits/<run>/

# Strenger, wenn auch Stubs unerwünscht sind:
python tools/aggregate_results.py validate audits/<run>/ --min-substance 400
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

### 5.2 Findings-Anzahl zurück in den Audit-Tracker

Nach Abschluss des Audits wird die `Findings`-Spalte im Tracker aktualisiert. Der Wert MUSS aus `summary.json` gelesen werden, niemals neu gezählt:

```bash
# Korrekt: Single-Source-of-Truth via tracker_sync
python "$SKILL_BASE/tools/tracker_sync.py" update "$name" \
    --from-summary "audits/<run>/summary.json" \
    --set "audit_status=Findings dokumentiert"
```

```python
# FALSCH: separate Re-Computation — riskiert Drift gegen Step 5/6
total_findings = sum(1 for r in check_runs if r.status in ("fail", "partial"))
```

**Backend-Auswahl:** Der Tracker-Sync ist pluggable, damit der Skill nicht an Notion gebunden ist:

| Backend | Aktivierung | Verwendung |
|---|---|---|
| `csv` (Default) | `--backend csv --csv-path tracker.csv` oder `MCP_AUDIT_TRACKER_PATH=...` | Lokal, zero-deps. Perfekt für User ohne Cloud-DB. |
| `notion` | `--backend notion`, plus `NOTION_TOKEN` (+ optional `NOTION_AUDIT_DB_ID`) | Stadt-Zürich-Setup; bestehender Audit-Tracker. |

Das CSV-Backend erzeugt die Datei beim ersten Schreibzugriff inklusive Header-Zeile. Felder sind backend-agnostisch: `server_name`, `audit_status`, `findings`, `last_audit_run`, `last_audit_at`, `production_ready`, `released_version`, `notes`. Wer Airtable oder Google Sheets braucht, fügt einen Adapter in `tools/tracker_sync.py` hinzu — Interface ist `TrackerBackend.get/update/list_all`.

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

# Nicht verifizierte Checks — weder bestanden noch fehlgeschlagen
jq -r '.not_verified_findings[]' audits/<run>/summary.json
```

### 6.2 Vergleich mit dem Vorlauf: nur innerhalb einer Katalog-Epoche

Zwei Audits desselben Servers sind nur dann ein Trend, wenn sie mit demselben Massstab gemessen wurden. Ändert sich der Katalog dazwischen — Checks kommen dazu, fallen weg, werden umgeschrieben —, ist «30 pass / 4 fail / 2 partial → x/y/z» keine Differenz, sondern zwei verschiedene Messungen mit einem Pfeil dazwischen. Im Lauf, aus dem diese Regel stammt, hätte der Pfeil **36 Checks gegen 54** gespannt, und jede Zahl wäre als Bewegung im Server gelesen worden.

Deshalb wird der Vergleich nicht normalisiert, sondern **verweigert**. Es gibt keine richtige Art, eine über einen Katalog gezählte Zahl von einer über einen anderen gezählten abzuziehen, und eine Fussnote überlebt das erste Zitieren nicht.

```bash
python tools/aggregate_results.py aggregate \
    audits/<run>/verification-results.json \
    --checks-dir "$SKILL_BASE/checks/" \
    --previous audits/<vorlauf>/ \
    --out audits/<run>/summary.json
```

Das schreibt `catalog_epoch` nach `summary.json`. Bei `comparable: false` druckt `build_report.py` **keine** gegenübergestellten Status-Zahlen, sondern nur beide Katalog-Hashes, beide Check-Anzahlen und den Grund — die Verweigerung muss das sichtbare Artefakt sein. Bei `comparable: true` erscheint die Delta-Tabelle.

Ein **unbekannter** Hash auf einer der beiden Seiten gilt ebenfalls als `comparable: false`. Nicht zu wissen, ob sich der Massstab geändert hat, ist nicht dasselbe wie zu wissen, dass er gleich geblieben ist, und die sichere Richtung ist die, die keine Linie zieht.

`--checks-dir` schreibt zusätzlich den Hash des Katalogs, der **tatsächlich auf der Platte liegt**, in die Zusammenfassung — und warnt, wenn er vom aufgezeichneten abweicht. Das ist dieselbe Fehlerklasse wie eine wandernde Ziel-Revision (§0.6), eine Ebene höher: Diesmal hat sich nicht das Gemessene bewegt, sondern das Messgerät.

### 6.3 Sprache und Adressaten

- **GL / KI-Fachgruppe:** Deutsch, Executive Summary + Findings-Tabelle reichen
- **Entwickler / Maintainer:** Deutsch oder Englisch, vollständiger Detail-Report
- **Externe Auditoren / Compliance:** Englisch, vollständig + Profile-Snapshot

---

## Schritt 7: Release-Vorschlag (nur bei `production_ready: true`)

**Ziel:** Wenn der Server nach den Audit-/Remediation-Schleifen production-ready ist, einen versionierten Release des **auditierten Server-Repos** vorschlagen — inklusive CHANGELOG-Eintrag und GitHub-Release-Draft. Nicht für das Skill-Repo selbst.

Schritt 7 läuft nur, wenn `summary.production_ready == true` (keine offenen `critical`/`high`-Fails). Bei offenen Blockern wird der Release verweigert; das ist Absicht.

### 7.1 Release-Vorschlag generieren

```bash
# Liest summary.json, ermittelt aktuelle Version (pyproject.toml /
# package.json / git tag) und schlägt einen CHANGELOG-Eintrag vor.
python "$SKILL_BASE/tools/propose_release.py" propose \
    "$OUTPUT_DIR" "$TARGET" \
    --bump patch \
    --notes "Schliesst HITL-005 und SEC-007. Audit run-id wie unten." \
    --format json
# exit 0 = Vorschlag generiert, exit 2 = nicht production-ready (mit Begründung)
```

Der Vorschlag enthält: aktuelle Version + Quelle (`pyproject` / `package` / `git`), nächste Version (semver-Bump), CHANGELOG-Diff, vorgeschlagene `git tag`/`gh release`-Befehle und die Audit-Metadaten (run-id, skill_version, catalog_hash, by_status). **Im Propose-Modus wird nichts geschrieben** — der User sieht den Vorschlag und bestätigt.

### 7.2 Release anwenden (nach Bestätigung)

```bash
# Schreibt CHANGELOG, committet (chore(release): vX.Y.Z), erzeugt
# annotated git tag, optional gh release --draft. Nichts wird gepusht.
python "$SKILL_BASE/tools/propose_release.py" apply \
    "$OUTPUT_DIR" "$TARGET" \
    --bump patch \
    --notes "..." \
    --gh-release
```

Der Apply-Modus ist bewusst defensiv: kein `git push`, kein non-draft Release. Der User entscheidet, wann der Tag und der Release veröffentlicht werden. Die Skill-Verantwortung endet beim Draft.

**Wichtig:** Wenn `pyproject.toml` oder `package.json` eine Version pinnen, ist diese die kanonische Quelle. Der Skill ändert diese Files **nicht** — der Maintainer bumpt die Version-Zahl im Manifest selbst, bevor er den Tag pushed. Begründung: Skill kennt die Bump-Konvention des Projekts nicht (pre-release tags, scope-prefix, etc.).

### 7.3 Tracker-Update nach Release

Nach dem Release wird der Tracker-Eintrag aktualisiert — backend-agnostisch via `tracker_sync.py`:

```bash
# Default: CSV (lokal, zero-deps)
python "$SKILL_BASE/tools/tracker_sync.py" update "$SERVER_NAME" \
    --from-summary "$OUTPUT_DIR/summary.json" \
    --set "audit_status=Released" \
    --set "released_version=$NEXT_VERSION"

# Notion (alternativ, falls NOTION_TOKEN gesetzt)
python "$SKILL_BASE/tools/tracker_sync.py" --backend notion update "$SERVER_NAME" \
    --from-summary "$OUTPUT_DIR/summary.json" \
    --set "audit_status=Released" \
    --set "released_version=$NEXT_VERSION"
```

`--from-summary` zieht `findings`, `production_ready`, `last_audit_run` und `last_audit_at` automatisch aus der Audit-Summary — Single-Source-of-Truth, kein Re-Counting. Felder, die im Notion-Tracker fehlen (z.B. `Released Version`), werden ohne Drama übersprungen, wenn sie via Property-Map nicht definiert sind.

### 7.4 Anti-Patterns

- **Release ohne grünen Audit:** `propose_release.py` weigert sich. `--force` existiert für absolute Notfälle (z.B. Hotfix-Release mit dokumentierter Risiko-Akzeptanz), aber das ist eine Eskalation, nicht Routine.
- **Skill bumpt die Manifest-Version automatisch:** macht er nicht. Versionen in `pyproject.toml`/`package.json` sind Maintainer-Verantwortung; Skill schreibt nur CHANGELOG + Tag.
- **`git push` automatisch:** macht der Skill nicht. Apply-Modus bleibt lokal, Pushen ist eine bewusste Maintainer-Aktion.

---

## Portfolio-Hygiene: ein Commit, 33 Repos

Findings aus diesem Katalog treffen selten einen Server allein. Ein User-Agent aus den Metadaten, eine Obergrenze in der Dependency-Range, ein Header im HTTP-Client — die Remediation ist dann **einmal geschrieben und 33-mal angewandt**. Für diesen Fall gilt eine Regel, die keinem einzelnen Repo ansieht, warum es sie gibt.

### Gemeinsam ausgerollter Code wird auf die schmalste konfigurierte Zeilenbreite geschrieben

Im Portfolio stehen `line-length` 88, 100, 110 und 120 nebeneinander — ausgezählt über die 32 Repos mit einer Kopie des Versions-Checks: 24-mal 100, 5-mal 120, 2-mal 110 (`sbb-opendata-mcp`, `termdat-mcp`), 1-mal 88 (`swiss-snb-mcp`, ohne Eintrag und damit auf dem ruff-Default). Das ist für sich harmlos: Jedes Repo formatiert nach seiner eigenen Konfiguration, und `ruff format --check` in seiner CI ist zufrieden.

Ein identischer Commit über alle Repos ist es nicht. `ruff format` **zieht einen Ausdruck zusammen, sobald er passt**, und bricht ihn um, sobald er nicht mehr passt — beides deterministisch aus der konfigurierten Breite. Derselbe Text kann deshalb nicht gleichzeitig die Ausgabe des Formatters für 88 und für 120 sein, sobald irgendeine Zeile dazwischenliegt:

- Für 120 geschrieben, in ein 88er-Repo kopiert: Der Formatter dort will umbrechen → `--check` rot.
- Für 88 umgebrochen, in ein 120er-Repo kopiert: Der Formatter dort will zusammenziehen → `--check` rot.

Die Formulierung, die überall hält, ist deshalb nicht «für 88 umgebrochen», sondern **kurz genug, dass die zusammengezogene Form in 88 Spalten passt**. Dann hat kein Formatter etwas zu tun, und jede Breite ab 88 erzeugt denselben Text — auch eine, die heute noch niemand konfiguriert hat. Praktisch heisst das: eine Zwischenvariable statt eines langen Ausdrucks, ein kürzerer Bezeichner, ein Aufruf auf zwei Anweisungen verteilt.

**Vor dem Ausrollen prüfen, nicht danach:**

```bash
for W in 88 100 110 120; do
  ruff format --check --line-length "$W" path/to/patch.py \
    || echo "nicht formatkonform bei line-length $W"
done
```

Alle vier müssen still bleiben. Bleibt eine übrig, ist der Patch noch nicht portfolio-tauglich — dann entweder das Fragment kürzen, oder bewusst darauf verzichten, denselben Commit auszurollen, und stattdessen pro Repo formatieren lassen. Das ist zulässig, kostet aber genau die Eigenschaft, wegen der man einen identischen Commit wollte: dass 33 Diffs vergleichbar sind.

**Woher die Regel kommt:** aus einem roten CI-Lauf und 33 Force-Pushes. Der Patch war in einem Repo mit `line-length 120` geschrieben und getestet, sah überall gleich aus und war in jedem 88er-Repo nicht formatkonform. Der Fehler fiel erst in der CI auf, weil lokal jedes Repo mit seiner eigenen Konfiguration grün war.

**Eselsbrücke:** *«Der schmalste Wert im Portfolio schreibt den Code.»*

**Und dieses Repo steht bei 88 — ausgeschrieben, nicht vergessen.** `ruff.toml` trug lange keinen `line-length`-Eintrag und lief damit auf dem ruff-Default. Von aussen ist das nicht von einem Versäumnis zu unterscheiden, und weil 24 der 32 gezählten Repos auf 100 stehen, liest sich die Abwesenheit wie ein Ausreisser. Sie ist das Gegenteil: 88 ist der schmalste im Portfolio konfigurierte Wert, also genau der, den die Regel oben verlangt. Ein Angleichen an die Mehrheit würde 42 der 58 Dateien dieses Repos auf Zeilen bis 100 Spalten bringen — jede davon ein Umbruch in jedem 88er-Repo, also der Bruch aus `OPS-005` neu erzeugt statt beseitigt. Der Wert steht deshalb jetzt explizit in `ruff.toml`, samt Messung und Begründung; `tests/test_ruff_line_length.py` hält ihn am schmalsten Wert der Prüfschleife oben fest. Was der Eintrag *nicht* leistet: Kopiertauglichkeit. Die entsteht erst, wenn die zusammengezogene Form in 88 Spalten passt, und nachweisen kann sie nur die Schleife, nicht die Konfiguration.

**Und die Regel braucht einen Ort, an dem sie rot wird.** Diese Sektion ist Anleitung für den, der ausrollt — sie wirkt nur, solange sie jemand liest. Derselbe Bruch kam prompt zurück, diesmal aus der Gegenrichtung: eine 99 Zeichen lange Zeile, in einem 100er-Repo geschrieben, formatgerecht dort und nicht im 88er-Repo. Erzwungen wird die Regel erst durch einen Pipeline-Schritt, der die Prüfschleife oben ausführt — als Kriterium ist das `OPS-005`, fünfte Ausprägung.

### Ein mechanischer Eingriff braucht einen mechanischen Nachweis

Wer 200 Dateien über 30 Repos umformatiert oder umbenennt, kann das Ergebnis nicht lesen. Die übliche Antwort — «es ist ja nur Formatierung» — ist eine Behauptung, keine Prüfung, und sie ist bei Umbenennungen schlicht falsch. Für diese Klasse von Eingriffen gibt es billige, harte Nachweise; einer je Eingriffsart.

**Formatierung: der Syntaxbaum muss identisch bleiben.** Ein Formatter darf Zeilenumbrüche und Klammern ändern, nichts sonst. Das lässt sich vollständig prüfen, Datei für Datei:

```python
import ast
vorher = {p: ast.dump(ast.parse(p.read_text(encoding="utf-8"))) for p in dateien}
# ... ruff format ...
abweichend = [p for p in dateien
              if ast.dump(ast.parse(p.read_text(encoding="utf-8"))) != vorher[p]]
```

Über 205 umformatierte Dateien meldete das genau zwei Abweichungen — beide Docstrings, die mit vier Anführungszeichen begannen (`""""…`), wo der Formatter ein trennendes Leerzeichen einfügt und damit den Stringinhalt ändert. Ohne die Prüfung wäre das unbemerkt geblieben; mit ihr steht es im Pull Request.

**Umbenennung: die Menge der String-Literale muss identisch bleiben.** Eine Umbenennung per Textsuche greift in Strings und Kommentare hinein. Die Gegenprobe kostet vier Zeilen:

```python
lits = lambda code: sorted(n.value for n in ast.walk(ast.parse(code))
                           if isinstance(n, ast.Constant) and isinstance(n.value, str))
assert lits(alt) == lits(neu), "String-Literal verändert — Abbruch"
```

Bei der Umbenennung eines einbuchstabigen `S` in einer Testdatei hat genau diese Zusicherung angeschlagen: Ein Literal `'[S'` hätte die naive Ersetzung verfälscht. Der saubere Weg führt danach über den Tokenizer für Bezeichner plus eine gezielte Ersetzung in den `{…}`-Platzhaltern der f-Strings — je nach Python-Version tokenisiert `tokenize` deren Inhalt nicht, dann bleiben Referenzen stehen und erzeugen `F821`.

**Und danach trotzdem die Testsuite.** Beide Nachweise decken die Sprache ab, nicht das Verhalten unter Laufzeitannahmen. Sie ersetzen den Testlauf nicht, sie machen ihn nur aussagekräftig: Wenn AST und Literale gleich sind und die Tests durchlaufen, ist der Eingriff belegt verhaltensgleich.

### Ein Gate zu setzen ist ein Rollout, kein Commit

Drei Eigenschaften, die erst beim Ausrollen über viele Repos sichtbar werden:

1. **Die Werkzeugversion gehört zum Gate.** Ohne Pin urteilt es jeden Tag anders — Kriterium und Begründung stehen in `OPS-006`.
2. **Formatieren und Gate gehören in getrennte Commits.** Sonst besteht der Diff aus tausend Zeilen Umbruch, in denen die vier Zeilen Workflow-Änderung verschwinden. Getrennt überspringt der Review den ersten Commit und liest den zweiten.
3. **Danach hängen offene Pull Requests am Zielbranch.** Die CI prüft den Merge-Commit. Nimmt der Zielbranch unformatierten Code auf, wird ein offener Pull Request rot, ohne dass sich an ihm etwas geändert hat. Beim Rollout über 32 Repos traf das zwei von 27 offenen Pull Requests. Wer mehrere Tage lang Pull Requests offen hält, plant den Abgleich mit der Basis als wiederkehrenden Schritt ein — nicht als Störung.

---

## Anti-Patterns (vermeiden)

1. **«Wir machen den Audit, sobald alles fertig ist»** — Audits sind iterativ. Server in Phase 1 auditieren, nicht erst in Phase 3.
2. **«Der Server ist Open Data, also kein Audit nötig»** — falsch. Auch Public-Data-Server haben Tool-Design-, SDK- und Resilienz-Risiken.
3. **«Findings als Issues in GitHub anlegen reicht»** — nein, ohne strukturierte Severity und Effort werden sie ignoriert. Notion-Karte ist Single Source of Truth.
4. **«Ich überspringe `low`-Findings»** — okay, aber dokumentieren als «not-audited», nicht stillschweigend ignorieren.
5. **«Der Check passt nicht ganz, ich mache es einfach so wie ich denke»** — wenn ein Check nicht passt, ist das ein Befund über den Katalog. Im Skill-Repo ein Issue eröffnen — und dort zuerst [§2.5](#25-reichweite-vor-neuer-regel) beantworten: zu enge Reichweite oder wirklich fehlende Dimension?
6. **«Audit-Report ohne Remediation-Plan»** — wertlos. Findings ohne Fix-Vorschlag werden nicht angegangen.
7. **«Kein Check hat das gemeldet, also fehlt ein Check»** — meistens fehlt keiner. Meistens hat einer zu kurz gegriffen. Siehe [§2.5](#25-reichweite-vor-neuer-regel).
8. **«`grep` findet den Satz nicht, also fehlt die Doku»** — `grep` ist zeilenweise. Ein Satz, der umbricht, wird nie gefunden. Vor dem Vergleich normalisieren, siehe [§4.1](#whitespace-normalisieren-bevor-auf-text-geprüft-wird).
9. **«Das Werkzeug hat nichts gemeldet, also ist der Check bestanden»** — nur wenn das Werkzeug gelaufen ist *und* gefunden hätte. Sonst ist es `todo`, nicht `pass`. Siehe [§2.6](#26-ein-check-der-nichts-findet-muss-sagen-können-ob-er-gesucht-hat).
10. **«Der Patch läuft in meinem Repo grün, also überall»** — bei portfolio-weiten Fixes entscheidet die schmalste konfigurierte Zeilenbreite, nicht die eigene. Siehe [Portfolio-Hygiene](#portfolio-hygiene-ein-commit-33-repos).
11. **«Ich habe den Text abgeschickt, also steht er da»** — Platzhalter in spitzen Klammern verschwinden auf dem Weg in PR-Body, Issue oder Tracker, lautlos und plausibel. Body zurücklesen, nicht annehmen. Siehe [§0.5](#05-platzhalter-in-spitzen-klammern-überleben-den-weg-nach-draussen-nicht).
12. **«Das Kommando ist gelaufen, also stimmt die Zahl»** — ein Werkzeug kann sauber laufen, ein plausibles Ergebnis liefern und trotzdem etwas anderes messen als gedacht. Eine Null ist eine Behauptung, kein Befund. Negative Kontrolle fahren, siehe [§4.1](#negative-kontrolle-ein-kommando-das-läuft-misst-nicht-automatisch-das-richtige).
13. **«Die Summe stimmt, also stimmt die Aufteilung»** — eine Vorhersage kann in der Zusammensetzung falsch sein, während das Total passt; das ist der Fall, der wie ein Treffer aussieht. Zahlen tragen ihre Herkunft, und eine abgeleitete speist kein Gate. Siehe [§4.1](#jede-zahl-trägt-ihre-herkunft--und-eine-abgeleitete-speist-kein-gate).
14. **«Prüflogik im Workflow-Heredoc ist auch Code»** — ja, aber nicht testbarer. Was über rot oder grün entscheidet, gehört in ein Skript mit Tests. Siehe [§0.3](#dieselbe-regel-gilt-für-ci-guards-und-dort-wiegt-sie-schwerer) und `OPS-008`.
15. **«Der Guard ist rot, also weiss es jemand»** — ein Guard, der auf `main` läuft, meldet an niemanden. `repo-description` war über sechs Merges rot und wurde nie beantwortet. Ein Befund braucht einen Adressaten, sonst ist er Dekoration.

---

## Eselsbrücken & Metaphern

- **Profile zuerst:** *«Ein Audit ohne Profil ist wie ein Arzt ohne Anamnese — falsche Diagnose garantiert.»*
- **Applicability-Filter:** *«Bei stdio-only ohne Auth ist Confused Deputy genauso relevant wie Erdbebensicherung in Reykjavík — gar nicht.»*
- **Severity-Disziplin:** *«`critical` heisst critical. Wer die Stufe inflationiert, hat irgendwann nur noch `critical`.»*
- **Evidenz-Pflicht:** *«Ein Finding ohne `path/to/file.py:42` ist eine Meinung, kein Befund.»*
- **Katalog-Erweiterung:** *«Zuerst fragen, ob die Regel zu kurz gegriffen hat — nicht, ob sie fehlt.»*
- **Textprüfung:** *«Wer auf Zeilenumbrüche prüft, prüft den Zeilenumbruch — nicht den Satz.»*
- **Leere Ergebnisliste:** *«Schweigen ist kein Freispruch.»*
- **Portfolio-Rollout:** *«Der schmalste Wert im Portfolio schreibt den Code.»*

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
- [ ] Jeder Check ohne Fund belegt, dass gesucht wurde — sonst `todo` statt `pass` (§2.6)
- [ ] Jedes Zähl- oder Suchkommando, dessen Ergebnis in einen Befund eingeht, hat eine negative Kontrolle: es schlägt nachweislich an, wenn es etwas zu finden gibt (§4.1)
- [ ] Keine Messung mit unterdrückter Fehlerausgabe (`2>/dev/null`, `|| true`, `tail -0`) als Beleg verwendet

**Schritt 5 — Findings**
- [ ] Pro fehlgeschlagenem Check ein Finding nach Template
- [ ] Effort-Schätzung S/M/L/XL gesetzt
- [ ] Tracker-Findings-Anzahl aktualisiert
- [ ] Jeder vorgeschlagene neue Check gegen §2.5 geprüft (Reichweite vor neuer Regel)
- [ ] `mcp_spec_version` im Profil gesetzt, und kein Check blieb `baseline-unresolved` (§2.7)
- [ ] Baseline-bedingte Ausfälle im Report namentlich genannt, nicht stillschweigend weggelassen (§3.3)
- [ ] Audit-Status auf `Findings dokumentiert` gesetzt

**Schritt 6 — Report**
- [ ] Executive Summary auf 3 Sätze
- [ ] Findings-Tabelle nach Severity sortiert
- [ ] Remediation-Plan mit Reihenfolge-Vorschlag
- [ ] Audit-Metadata vollständig (Datum, Skill-Version, Katalog-Version)
- [ ] Jede handgeschriebene Zahl gegen `summary.json` geprüft: `python tools/check_reported_numbers.py <summary.json> <datei>...` — keine Datei darf als `ungeprüft` zurückbleiben (§4.1)
- [ ] Keine abgeleitete oder vorhergesagte Zahl speist ein Gate oder steht unmarkiert im Report (§4.1)

---

## Versionierung des Check-Katalogs

Wenn das PDF aktualisiert wird oder neue Best Practices auftauchen:

0. **Zuerst [§2.5 Reichweite vor neuer Regel](#25-reichweite-vor-neuer-regel)** — prüfen, ob ein bestehender Check nur zu eng angewandt wurde. Die Schritte unten gelten erst, wenn das verneint ist.
1. Im Skill-Repo unter `checks/` neue `.md`-Datei mit nächster ID anlegen
2. `evidence_required` und `applies_when` mit Care befüllen
3. CHANGELOG-Eintrag im Repo-Root
4. Bestehende Server, die schon ein Audit hatten, **nicht automatisch reauditiert** — sondern bei nächstem Refactoring oder geplantem Re-Audit
5. **Re-Audit-Auslöser bei `critical` oder `high`** — vier Fälle, in denen ein bestehendes Audit-Ergebnis nicht mehr gilt:
   - **a) Severity angehoben.** Der Verstoss wiegt jetzt schwerer, als das Audit ihn geführt hat.
   - **b) `applies_when` nach oben erweitert.** Der Check gilt jetzt für Server, die beim letzten Audit **nicht** dagegen gemessen wurden. Formal keine Severity-Änderung — für die betroffenen Server aber ununterscheidbar davon, denn ein blockierender Check greift, wo vorher keiner war. Die Gegenrichtung (Reichweite verengt) löst kein Re-Audit aus, kann aber alte Findings gegenstandslos machen; das gehört in den CHANGELOG, nicht in die Warteschlange.
   - **c) Prüfkriterium korrigiert.** Der Check hat die falsche Sache als bestanden ausgewiesen — ein fehlerhaftes Pass-Pattern, ein Kriterium, das am Ziel vorbeiging. Ein „bestanden" aus der Zeit davor belegt nichts.
   - **d) Adoptionsstufe von `advisory` auf `enforced` promoviert.** Der Check hat vorher gemeldet und nicht geurteilt; ab jetzt blockiert er. Formal ändert sich weder Severity noch Reichweite noch Kriterium — für die betroffenen Server ist es trotzdem von a) nicht zu unterscheiden, denn ein blockierender Check greift, wo vorher keiner griff. Ein Audit, dessen `production_ready: true` sich darauf stützte, dass dieses Finding nicht zählte, gilt nicht mehr. Die Gegenrichtung (Demotion auf `advisory`) löst kein Re-Audit aus — sie kann aber ein Verdikt nachträglich grün machen, und das gehört in den CHANGELOG, nicht in die Warteschlange. Bei `medium`/`low` entfällt d) ganz: Dort blockierte auch vorher nichts, die Promotion ändert also an keinem Verdikt etwas.

**Warum b) und c) dazugehören.** Punkt 5 nannte bis v1.3.0 nur die Severity. Dieses Release hatte **keine** einzige Severity-Änderung und trotzdem beide anderen Fälle: `SEC-005` wurde auf stdio-only-Server ausgeweitet, die den `high`-Check nie gesehen hatten, und `SEC-016` lehrte im Pass-Pattern eine SDK-API, die auf der aktuellen Major-Version einen `ValueError` wirft — wer ihn „bestanden" hatte und dem Muster gefolgt war, hatte einen Server, der auf HTTP-Transport nicht startet. Nach der alten Fassung wäre die Re-Audit-Liste leer gewesen. Eine Regel, die genau dann nichts meldet, wenn der Katalog sich geirrt hat, ist die falsche Regel.

**Warum d) dazukam.** Bei der Promotion von `DEP-001` (`high`, `always`) in v1.5.0 nannte Punkt 5 nur a) bis c) — und keiner der drei traf zu: Die Severity blieb, `applies_when` blieb, das Kriterium blieb. Nach dem Buchstaben der Regel wäre die Re-Audit-Liste leer gewesen, während in Wahrheit **jeder** Server mit einer ungedeckelten Range von diesem Moment an seine Production-Readiness verlor. Die Adoptionsstufe war der einzige Hebel im Katalog, der ein Verdikt kippen kann, ohne dass irgendein Feld sich ändert, das die Regel las. Genau dieselbe Lehre wie bei b) und c), eine Achse weiter.

Der Fall ist selten und deshalb leicht zu übersehen: Promotionen sind einzelne, bewusste Entscheidungen. Aber eine Regel, die nur die häufigen Fälle kennt, meldet nichts, wenn es darauf ankommt — sie muss den Fall benennen, gerade weil er selten ist.

Die jeweils offene Warteschlange steht in [`docs/re-audit-queue.md`](docs/re-audit-queue.md) — mit Datum, Auslöser je Server und der Herkunft jeder Zahl. Sie ist eine Momentaufnahme und keine gepflegte Liste: Ein Dokument, das vorgibt immer aktuell zu sein, ist nach dem zweiten Release falsch, ohne dass es jemand merkt.

**Eselsbrücke:** *«Ein neuer Check ist ein neuer Vertrag. Bestehende Audits sind nicht rückwirkend ungültig, aber bei nächstem Audit gilt der neue Katalog.»*

**Zweite Eselsbrücke, für Punkt 5:** *«Re-Audit, wenn sich geändert hat, wie hart geprüft wird (a), wer geprüft wird (b), worauf geprüft wird (c), ob der Befund noch folgenlos bleibt (d) — oder gegen welches Protokoll gemessen wird (e).»*

---

## Übergabe & Folge-Skills

### Die MCP-Qualitätskette

Fünf Repos, ein Lebenszyklus — gemeinsames GitHub-Topic [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain). Dieser Katalog ist das vierte Glied und prüft nach dem Bau, was die drei davor beim Bauen fordern. Ein Finding lässt sich damit an den Skill zurückgeben, der die Behebung beschreibt.

| Phase | Repo | Seine Regeln in diesem Katalog |
|---|---|---|
| vor dem Bau | [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | liefert die Ground Truth, gegen die `FID-002` misst |
| im Bau | [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill) | [`FID-001`–`FID-006`](./checks/) |
| im Bau | [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-transport-hardening-skill) v2.0.0, zwölf Regeln | [`SDK-006`](./checks/SDK-006.md) + [`DEP-001`](./checks/DEP-001.md), [`ARCH-013`](./checks/ARCH-013.md), [`SEC-024`](./checks/SEC-024.md), [`ARCH-015`](./checks/ARCH-015.md)–[`ARCH-017`](./checks/ARCH-017.md), [`SCALE-008`](./checks/SCALE-008.md), [`SCALE-009`](./checks/SCALE-009.md)/[`SCALE-010`](./checks/SCALE-010.md), [`HITL-006`](./checks/HITL-006.md), [`SEC-025`](./checks/SEC-025.md)/[`SEC-026`](./checks/SEC-026.md) — seine Regeln 2, 6 und 7 hat der Katalog nicht, Regel 5 nur teilweise (`DRIFT-003`) |
| nach dem Bau | **`mcp-audit-skill`** | **Dieser Skill** — der Katalog selbst |
| im Betrieb | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | der Vorfall hinter [`OPS-005`](./checks/OPS-005.md) — eine Testsuite, die kein Workflow je ausgeführt hat |

Daneben, nicht Teil der Kette: `mcp-builder` — generische Bauanleitung von Anthropic, wird ergänzt und nicht ersetzt. Fremdes Repo, kann das Topic nicht tragen.

Die Mitgliedschaft steht an einer Stelle: [`docs/quality-chain.json`](./docs/quality-chain.json), wöchentlich geprüft von [`tools/check_quality_chain.py`](./tools/check_quality_chain.py).

### Nach dem Audit

Nach erfolgreichem Audit:

- **Findings als GitHub-Issues** anlegen via [`github-repo`](../github-repo/SKILL.md)-Skill (mit Labels `audit`, `severity:critical`, etc.)
- **DSG/Compliance-Findings** als Notion-Karte im Use-Case-Register, falls relevant
- **Bei Pattern-Wiederholung** über mehrere Server: ein Reference-Template-MCP-Repo bauen, das alle Best Practices erfüllt, und Server iterativ darauf migrieren
