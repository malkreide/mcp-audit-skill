---
name: mcp-data-source-probe
description: Standardisiertes 3-Schritte-Vorgehen zur Evaluation, Architektur-Entscheidung und Implementation von `*-mcp`-Servern im Swiss Public Data MCP Portfolio. Verwende diesen Skill IMMER wenn der User (1) einen neuen MCP-Server plant oder baut, (2) eine neue Datenquelle für einen bestehenden Server evaluiert, (3) einen Server um zusätzliche Tools erweitern will, (4) fragt ob eine bestimmte API/Datenquelle geeignet ist, (5) einen bestehenden MCP-Server refaktoriert, (6) Begriffe wie «MCP-Server», «neue Datenquelle anbinden», «API prüfen», «Live-Probe», «Datenquelle evaluieren», «welche Tools», «kann ich das nutzen» erwähnt, (7) für einen `*-mcp`-Server einen Scaffold anfordert, oder (8) meldet, dass ein Server zu wenige oder keine Treffer liefert, obwohl die Daten in der Quelle vorhanden sind («findet nichts», «zu wenig Resultate», «Web-UI zeigt mehr», «leeres Ergebnis», «Recall», «Scope»). Auch bei allgemeinen Aussagen wie «ich würde gerne X via MCP anbinden» oder «gibt es Daten von Y» diesen Skill anwenden.
---

# MCP Data Source Probe — Standard-Vorgehen

Dieser Skill kodiert vier Disziplinen, die das Swiss Public Data MCP Portfolio vor den häufigsten MCP-Fehlern schützen: Tools gegen nicht-funktionierende Endpoints zu bauen, fragile Single-Path-Architekturen zu wählen, Resilienz-Basics zu vergessen — und, am schwersten zu bemerken, unvollständig zu liefern, ohne es zu merken.

**Das Mantra in vier Zeilen:**

1. Live-Probe **vor** Design
2. Dump-Fallback **vor** API-Abhängigkeit
3. Retry **vor** Defaitismus
4. Ground Truth **vor** Selbstvertrauen

Jeder neue `*-mcp`-Server durchläuft die drei Schritte unten in dieser Reihenfolge; die vierte Disziplin ist kein eigener Schritt, sondern verläuft quer durch Schritt 1 (1.2b, 1.4) und Schritt 3 (3.6). Abweichungen erfordern eine explizite Begründung, die im README unter «Architektur-Entscheid» dokumentiert wird.

---

## Schritt 1: Live-Probe (vor dem Coden)

**Ziel:** Empirisch feststellen, was die Datenquelle tatsächlich liefert — nicht was die Dokumentation verspricht.

### 1.1 Dokumentation vollständig lesen

- OpenAPI-Spec, Datenmodell-PDFs, Merkblätter, Lizenz-Hinweise.
- Alle Endpoint-Patterns extrahieren (REST-Pfade, GraphQL-Schemas, SPARQL-Endpoints, Dump-URLs).
- Auth-Anforderungen prüfen: API-Key nötig? Rate-Limits? OAuth? Nur bei No-Auth weitermachen (Phase-1-Prinzip des Portfolios).
- Lizenz-Check: CC BY? CC BY-SA? OGD Schweiz? Proprietär? → bestimmt Attribution-Pflicht.

### 1.2 Endpoint-Matrix systematisch abarbeiten

Für jeden dokumentierten Endpoint **mindestens fünf Probe-Calls**:

| # | Probe | Zweck |
|---|---|---|
| 1 | Einfacher Basis-Call (z.B. Liste ohne Parameter) | Baseline |
| 2 | Das offiziell dokumentierte Beispiel | Doku-Treue |
| 3 | Mit Filter / Limit / Sortierung | Parameter-Validität |
| 4 | Fehlerfall (invalide ID, fehlender Parameter) | Error-Verhalten |
| 5 | **Scope-Probe: Filter weggelassen vs. explizit maximal** | **Recall-Delta** |

Probe 5 ist neu und der wichtigste der fünf. Sie beantwortet die Frage, die weder Probe 1 noch Probe 3 stellt: *Deckt ein Call ohne Filter-Parameter wirklich alles ab?* Siehe 1.2b.

**Konkret mit `curl` und `python3 -c`:**

```bash
BASE="https://example.ch/api/v1"

# 1. Baseline
curl -sL -w "\nHTTP %{http_code} | %{size_download}B | %{time_total}s\n" \
  "$BASE/table/entity/list?limit=3" -o probe.json
python3 -c "import json; d=json.load(open('probe.json')); print('success:', d.get('success'), 'count:', d.get('count'))"

# 2. Das Doku-Beispiel
curl -sL "$BASE/table/entity/id/1" | python3 -m json.tool | head -30

# 3. Mit Filter
curl -sL "$BASE/table/entity/list?filter_status=active&limit=5" -o f.json
python3 -c "import json; d=json.load(open('f.json')); print('keys:', list((d.get('data') or [{}])[0].keys())[:15])"

# 4. Fehlerfall
curl -sL -w "HTTP %{http_code}\n" "$BASE/table/entity/id/999999"
```

### 1.2b Default-Matrix — was bedeutet Weglassen?

**Ziel:** Für jeden optionalen Parameter feststellen, was passiert, wenn der Server ihn *nicht* sendet. Die Antwort steht ausschliesslich in der **Parameterbeschreibung** der Spec — nicht im Response-Schema, nicht im Doku-Beispiel, und sie ist an einem funktionierenden Call nicht erkennbar.

Der Portfolio-Fall: `termdat-mcp` sendete `ClassificationIds` nur bei explizitem Aufruf. Die Spec dazu: *«If no ID is given, a default set of classifications will be included (=VARIA)»* — eine von 23 Klassifikationen, ausgerechnet die Restkategorie. Jede Default-Suche lief gegen ein Dreiundzwanzigstel des Bestands und meldete das als gewöhnliche Leermenge. Alle Tests waren grün. Gefunden hat es ein User mit dem Web-UI daneben.

**Beschreibungen aller optionalen Parameter extrahieren:**

```bash
curl -s "$SPEC_URL" -o spec.json
python3 - spec.json <<'PY'
import json, sys
spec = json.load(open(sys.argv[1], encoding="utf-8"))
for path, ops in spec.get("paths", {}).items():
    for op in ops.values():
        if not isinstance(op, dict):
            continue
        for prm in op.get("parameters", []):
            if prm.get("required"):
                continue
            desc = (prm.get("description") or "").replace("\n", " ")
            print(f"{path} | {prm['name']} | {desc[:160]}")
PY
```

Jede Beschreibung mit «default», «if no … is given», «standard set», «unless specified» ist ein Fund. Verdächtige Parameternamen quer durch die üblichen Quellen:

| Quelle | Parameter | Default bei Weglassen |
|---|---|---|
| CKAN `package_search` | `rows` | 10 Treffer, nicht alle |
| WFS `GetFeature` | `count` / `maxFeatures` | serverseitiges Limit |
| SPARQL | `FROM` / Named Graphs | nur der Default-Graph |
| Elasticsearch / Solr | `size`, `fq`, `df` | 10 Hits, eingeschränktes Default-Feld |
| GraphQL (Relay) | `first` | schema-abhängig, oft klein |
| SQL-über-HTTP | `LIMIT` | Gateway-Zeilenlimit |

**Empirisch bestätigen — Delta ≠ 0 ist ein Befund:**

```bash
# A: Parameter weggelassen
curl -s "$BASE/search?q=Testbegriff" | python3 -c "import json,sys; print('A:', len(json.load(sys.stdin)))"
# B: Parameter explizit maximal (alle IDs, alle Felder, hohes Limit)
curl -s "$BASE/search?q=Testbegriff&classIds=1&classIds=2&..." | python3 -c "import json,sys; print('B:', len(json.load(sys.stdin)))"
```

Ausgabe ist eine Zeile pro Parameter in der Befund-Tabelle:

| Parameter | Weglassen bedeutet | Beleg | Server muss senden? |
|---|---|---|---|
| `ClassificationIds` | ⚠️ nur `VARIA` (1 von 23) | Spec + Delta 0→3 | ✅ voller Satz |
| `MaxEntryCount` | ⚠️ 25 statt alles | Spec-Beschreibung | ✅ immer explizit |
| `OutLanguageCode` | ✅ rein additiv | live verifiziert | n/a |

**Verwandter Fall — Teilmengen boolescher Flags.** Sendet man von einer Flag-Gruppe (`Field.*`, `include_*`) nur einige, behalten die übrigen ihren serverseitigen Default. Ein `fields`-Argument kann dann nur erweitern, nie einschränken — es ist ein No-op, der wie Steuerung aussieht. Gegenprobe: ein Call mit explizitem `false` für ein Default-true-Flag muss weniger liefern. Tut er das nicht, sendet der Server die Gruppe unvollständig.

### 1.3 Befund-Tabelle erstellen

Ausgabe von Schritt 1 ist **immer** eine Tabelle in diesem Format:

| Endpoint | HTTP | Status | Records | Bemerkung |
|---|---|---|---|---|
| `/table/X/list` | 200 | ✅ funktioniert | 139 | wie dokumentiert |
| `/table/Y/list` | 200 | ⚠️ leer | 0 | SQL-Filter zu restriktiv |
| `/table/Z/id/1` | 404 | ❌ existiert nicht | – | Doku veraltet |
| `/search/default/Foo` | 200 | ✅ funktioniert | ~5 | |

### 1.4 Reality-Check gegen die offizielle Oberfläche

**Gilt für Listen- UND für Such-Endpoints.** Diese Erweiterung ist die Lehre aus `termdat-mcp`: Dort wurde der Reality-Check korrekt auf die Listen-Endpoints angewandt — 140 Collections, 23 Classifications, beide Zahlen stimmten — und nie auf den Such-Endpoint. Nicht die Regel fehlte, sondern ihre Reichweite. Recall entsteht in der Suche, also muss er dort gemessen werden.

**(a) Bestandszahlen.** Die Homepage behauptet in der Regel Zahlen («246 Parlamentarier:innen», «139 Lobbygruppen»). Live-Probe damit abgleichen. Liefert die API nur einen Bruchteil, ist das ein Alarm-Signal — entweder ist die API defekt, oder ein Filter ist restriktiver als dokumentiert.

**(b) Recall-Ground-Truth für Such-Endpoints.** Das offizielle Web-UI ist die einzige verfügbare Ground Truth. **3–5 Referenzbegriffe** wählen und in beiden Oberflächen am selben Tag abfragen:

- einer mit vielen Treffern (fängt Limit- und Scope-Defaults),
- einer mit wenigen (fängt Feld-Abdeckung),
- einer als Kompositum oder mit Sonderzeichen (fängt Matching-Granularität und Encoding),
- **nicht** der Anchor-Demo-Query — der funktioniert immer, er wurde beim Bau optimiert.

| Referenzbegriff | Web-UI | API | Delta | Erklärung |
|---|---:|---:|---:|---|
| `Quellensteuer` | 12 | 7 | −5 | UI zählt Benennungen, API zählt Entries |
| `Pensionskasse` | 25 (gekürzt) | 28 | +3 | UI-Anzeige gekürzt |
| `Bundeskanzlei` | 4 | 4 | 0 | — |

Ein Delta ist zulässig — **aber nur erklärt**. «Weiss ich nicht» ist ein offener Befund und gehört ins README, nicht in den Papierkorb. Typische legitime Erklärungen: das UI zählt Benennungen statt Datensätze, das UI kürzt die Anzeige, das UI sucht über alle Sprachen, das UI durchsucht mehr Felder.

**(c) Als Regressionstest festschreiben.** Der Vergleich ist einmalig nur die Hälfte wert. Untergrenzen — grosszügig unter dem Ist-Wert, Faustregel Hälfte — als Live-Test:

```python
@pytest.mark.live
async def test_recall_floor():
    """Recall-Canary: fängt Scope-Regressionen und Upstream-Default-Änderungen."""
    for term, floor in [("Pensionskasse", 10), ("Quellensteuer", 1)]:
        entries, _ = await client.search(term, max_results=100)
        assert len(entries) >= floor, f"{term}: {len(entries)} < {floor} — Scope geschrumpft?"
```

Keine exakten Zahlen als Assertion: Der Test soll einen Kollaps von 21 auf 1 fangen, nicht bei jeder Bestandspflege rot werden. Ein Test, der ständig falsch anschlägt, wird abgeschaltet und fängt dann gar nichts mehr.

Bei Quellen **ohne** offizielles Web-UI: Ersatz-Ground-Truth dokumentieren — Zeilenzahl des Bulk-Dumps, veröffentlichte Bestandszahlen, Angaben im Katalogeintrag.

### 1.5 Dump-Verfügbarkeit prüfen

Parallel zu den API-Probes **immer** prüfen, ob die Quelle einen Bulk-Download anbietet:

- CSV / JSON / XML / SQL-Dump
- Datenmenge und Update-Frequenz
- Lizenz gleich wie API (meistens ja, sicherheitshalber prüfen)

**Faustregel:** Jede Schweizer Behörden- oder NGO-Datenquelle, die «seriös» ist, bietet einen Dump. Wenn keiner auffindbar ist, gezielt nachfragen oder in GitHub-Issues suchen.

---

## Schritt 2: Architektur-Entscheid

**Ziel:** Basierend auf den Probe-Befunden die richtige Architektur wählen — und den Entscheid **schriftlich** im README festhalten.

### 2.1 Der Entscheidungsbaum

```
Live-Probe-Ergebnisse
   │
   ├─ Alle nötigen Endpoints funktionieren stabil
   │     └─ ARCH A: Live-API-only
   │
   ├─ Einige Endpoints broken/leer, Dump vorhanden
   │     └─ ARCH B: Hybrid (Dump-first, API-Fallback)   ⭐ Häufigster Fall
   │
   ├─ Keine nutzbaren Endpoints, nur Dump
   │     └─ ARCH C: Dump-only
   │
   ├─ Weder stabile API noch Dump
   │     └─ BLOCKER: An Datenanbieter eskalieren,
   │                 Portfolio-Karte als «geblockt» markieren
   │
   └─ Auth nötig
         └─ Phase 2 verschoben, Phase 1 skippen ODER
            No-Auth-Teil isolieren und nur diesen bauen
```

### 2.2 Portfolio-Synergie-Check

**Bevor ein neuer Server gebaut wird, prüfen:**

- Passt die Datenquelle in ein bestehendes Cluster? (Transport, Environment, Legal, Statistics, Education, Economics, Culture, Health, Registers, Parliament)
- Gibt es einen existierenden `*-mcp`-Server, der diese Daten logisch ergänzt? → **Tool-Extension statt neuer Server.**
- Wenn neuer Server: Was ist die «anchor demo query», die die Komplementarität zum Portfolio zeigt?

**Entscheidungsfrage:** *«Wenn der User beide Server in derselben Konversation nutzt, was wird dadurch möglich, was vorher nicht ging?»* → Wenn die Antwort schwach ist, ist es wahrscheinlich eine Tool-Extension.

### 2.3 Architektur-Entscheid im README dokumentieren

Zwingend in jedem neuen Server-README unter einem Abschnitt **«Architecture decision»** oder **«Architektur-Entscheid»** (bilingual):

```markdown
## Architecture decision

This server uses **Architecture B (Hybrid: Dump-first, API-fallback)**.

Rationale (verified live on YYYY-MM-DD):
- The weekly JSON dump contains X records with Y fields, refreshed every …
- Live endpoint `/table/Z` returns empty results at release time.
- The ABC endpoint works reliably for lookups, so it is used for single-entity
  calls.

Consequences:
- Dump is cached on disk with Z hours TTL.
- Library functions / retry / provenance behaviour: see docstrings.
```

---

## Schritt 3: Resilienz-Defaults (nicht-verhandelbar)

**Ziel:** Jeder `*-mcp`-Server erfüllt dieselben Minimal-Standards, damit er im Produktivbetrieb nicht am ersten Upstream-Blip kippt.

### 3.1 Retry mit exponentiellem Backoff für ALLE HTTP-Aufrufe

Minimum: 3 Retries mit 2s/4s/8s Wait. 5xx und Netzwerkfehler werden retried, 4xx (ausser 429) nicht.

**Referenz-Implementierung:**

```python
async def _fetch_with_retry(http: httpx.AsyncClient, url: str) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(4):
        if attempt > 0:
            await asyncio.sleep(2 ** attempt)  # 2s, 4s, 8s
        try:
            resp = await http.get(url)
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_error = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            # 4xx ausser 429 nicht retry
            if status is not None and 400 <= status < 500 and status != 429:
                raise
    assert last_error is not None
    raise RuntimeError(f"Upstream unreachable after retries: {last_error}")
```

### 3.2 Provenance + Attribution in JEDER Response

Pydantic-v2-Envelope macht das Weglassen unmöglich:

```python
from pydantic import BaseModel, Field

ATTRIBUTION = "Data: {Quelle} — {Lizenz}. {Disclaimer falls nötig}."

class ServerResponse(BaseModel):
    source: str = Field(default=ATTRIBUTION)
    provenance: str = Field(description="weekly_dump | live_api | cached")
    # ... payload fields
```

**Provenance-Werte (einheitlich über das Portfolio):**
- `weekly_dump` – aus gecachtem Bulk-Download
- `live_api` – direkt von der REST/GraphQL/SPARQL-API geholt
- `cached` – aus lokalem In-Memory-Cache, nicht neu gefetcht

### 3.3 Anchor Demo Query ZUERST definieren

Bevor Tools gebaut werden, **eine konkrete Frage festlegen**, die der Server beantworten können muss. Diese Frage:

- ist für Schulamt / KI-Fachgruppe / GL unmittelbar verständlich,
- kombiniert idealerweise mehrere Tools des Servers,
- wird im README prominent an Position «🎯 Anchor Demo Query» platziert.

**Beispiele aus dem Portfolio:**

| Server | Anchor Demo Query |
|---|---|
| `parlament-mcp` | *«Welche Vorstösse zu KI in der Volksschule der letzten 12 Monate?»* |
| `lobbywatch-mcp` | *«Welche WBK-N-Mitglieder haben Interessenbindungen zu Bildungsverlagen?»* |
| `bag-health-mcp` | *«Wie ist die aktuelle Grippesituation im Kanton Zürich?»* |
| `zh-education-mcp` | *«Wie entwickelt sich die Klassengrösse in der Volksschule Stadt Zürich?»* |

### 3.4 Tests gegen Fehlerzustände

Jeder Server hat **mindestens** diese drei Test-Klassen (mit `respx`-Mocking):

1. **Happy Path** – dokumentierter Normalfall
2. **Retry bei 503** – transienter Server-Fehler, nach zweitem Versuch erfolgreich
3. **Timeout / Network Error** – vollständiger Ausfall, sauberer Error statt Stacktrace

Plus `@pytest.mark.live`-Tests gegen die echte Quelle, via `pytest -m "not live"` aus CI ausgeschlossen.

**Grenze der Mocks — bitte ernst nehmen.** Ein `respx`-Mock bildet genau die Annahme ab, die man beim Schreiben hatte. Ist die Annahme falsch, ist der Mock falsch, und der Test bestätigt den Fehler statt ihn zu finden. Scope- und Recall-Bugs sind für Mocks strukturell unsichtbar. Deshalb gehört der Recall-Canary aus 1.4(c) zwingend zu den Live-Tests — er ist die einzige Testklasse, die eine falsche Grundannahme fangen kann.

### 3.5 Graceful Degradation

Wenn die Datenquelle trotz Retries nicht erreichbar ist, muss die Response sprechen können: *«Die Quelle ist aktuell nicht erreichbar. Zuletzt erfolgreicher Abruf: TIMESTAMP. Bitte in 10 Minuten erneut versuchen.»*

Implementation: `dump_status()`-Tool gibt immer einen auswertbaren Status zurück — nie einfach leere Records.

### 3.6 Leermenge ≠ Abwesenheit

3.5 behandelt den Ausfall — laut, sichtbar, mit Status-Code. Dieser Punkt behandelt den **erfolgreichen Aufruf mit null Treffern**. Der ist gefährlicher, weil ihn nichts als Problem markiert.

Ein leeres Result ist mehrdeutig: Begriff existiert nicht / Query zu eng / Scope eingeschränkt / Syntax passte nicht. Das Modell muss raten — und es rät entlang dessen, was die Tool-Description nahelegt.

**Die Tool-Description ist damit eine Halluzinations-Oberfläche.** Im `termdat-mcp`-Vorfall enthielt sie:

> *«An empty result usually means the term is out of scope, not that it is wrong.»*

Als Ehrlichkeit gemeint, faktisch eine vorformulierte Ausrede für das eigene Schweigen. Das Modell hat sie genommen und eine erfundene Erklärung geliefert — für einen Begriff, der die ganze Zeit in der Datenbank stand. Es hat nicht halluziniert, weil es schlecht war, sondern weil das Werkzeug ihm eine Erklärung mitgab und keinen nächsten Schritt.

**Zwei nicht verhandelbare Regeln:**

1. **Keine Formulierung in einer Tool-Description, die eine Leermenge erklärt oder entschuldigt.** Statt «X bedeutet meist Y» → «versuche Z, dann melde Abwesenheit». Ein Scope-Caveat darf zum Nachfassen auffordern, nie eine Schlussfolgerung lizenzieren.
2. **Ein leeres Result trägt ein `hint`-Feld** mit dem konkreten nächsten Versuch — Wildcard, weitere Felder, andere Sprache. Nicht im README: das wird nicht an das Modell weitergereicht.

```python
_EMPTY_HINT = (
    "No entry matched. `search_term` is Lucene syntax: try a prefix wildcard "
    "(e.g. 'Quellensteuer*') to catch compounds. Widen `fields`. Only then "
    "conclude the term is absent — and never substitute a guess for it."
)

class SearchResult(ServerResponse):
    returned: int
    hint: str | None = None   # gesetzt, wenn returned == 0
```

**Query-Syntax gehört in die Tool-Description**, nicht ins README — sonst existiert sie für das Modell nicht. Bei Volltextindizes zwingend die Matching-Granularität nennen: Die meisten matchen auf ganzen Wörtern, womit deutsche Komposita von ihren Bestandteilen nicht gefunden werden. «Quellensteuer» findet «Quellensteuerverordnung» nicht, «Quellensteuer\*» schon. Für ein Portfolio aus deutschsprachigen Verwaltungsquellen ist das der Normalfall, nicht der Randfall.

Wildcards serverseitig automatisch anhängen ist **kein** Ersatz: Es macht Phrasensuche unmöglich und verschiebt das Problem, statt es zu dokumentieren.

---

## Schritt 4: Übergabe an `github-repo`-Skill

Nach Abschluss der Probe (Schritt 1-3) erfolgt die Repo-Erstellung via [`github-repo`](../github-repo/SKILL.md)-Skill. Als Input dafür bereitstellen:

1. **Repo-Name** (Pattern: `{quelle}-mcp`, z. B. `lobbywatch-mcp`)
2. **Repo-Description** (max. 100 Zeichen, Stil-parallel zu `parlament-mcp`):
   - Template: `MCP server for the {Quelle}.{xyz} — {Domäne in einem Satz}`
3. **Topics/Tags** (5–8): immer `mcp`, `model-context-protocol`, `llm`, `python`, `swiss-open-data` + domänenspezifische
4. **Befund-Tabelle** aus Schritt 1.3 → gehört ins README unter «Known limitations» falls nicht alle Endpoints funktionieren
5. **Architektur-Entscheid** aus Schritt 2.3 → ins README
6. **Anchor Demo Query** aus Schritt 3.3 → prominent ins README

---

## Schritt 5: Notion-Portfolio-Karte anlegen

Nach Release (Tag `v0.1.0`) wird die Karte in der Notion-Datenbank `aa6b672a-e5e3-4608-b4e4-b380dc735b9e` angelegt. Pflichtfelder:

- Name
- Cluster (Transport / Environment / Legal / Statistics / Education / Economics / Culture / Health / Registers / Parliament)
- Status (Phase 1 / Phase 2 / Phase 3 / Deprecated)
- Datenquelle-URL
- Lizenz (CC BY 4.0 / CC BY-SA 4.0 / OGD-CH / proprietary)
- Anchor Demo Query
- Architektur (A / B / C)
- GitHub-URL
- PyPI-Status
- Notizen zu Known Limitations

---

## Entscheidungshilfen (Schnellreferenz)

### Soll ich diesen Schritt überspringen?

**Nie.** Selbst bei «offensichtlich einfachen» Quellen wie einer simplen REST-API tritt mindestens einer dieser Fälle auf:

- Die API liefert andere Feldnamen als dokumentiert → Probe fängt das ab
- Ein Endpoint gibt konsistent leere Arrays zurück → Probe fängt das ab
- Rate-Limits, die in der Doku nicht erwähnt werden → Probe fängt das ab
- Bool-Felder mit inkonsistenten Werten (`0/1` vs. `"Y"/"N"` vs. `true/false`) → Probe fängt das ab
- Ein weggelassener Filter-Parameter schränkt still auf einen Teilausschnitt ein → nur 1.2b fängt das ab
- Der Suchindex matcht auf ganzen Wörtern, Komposita bleiben unauffindbar → nur 1.4b fängt das ab

**Eselsbrücke:** *«Dokumentation ist ein Foto, Live-Probe ist der aktuelle Zustand. Wir bauen auf dem aktuellen Zustand.»*

**Zweite Eselsbrücke, für 1.2b und 1.4:** *«Ein grüner Test beweist, dass der Server tut, was du erwartet hast. Nur die Ground Truth beweist, dass deine Erwartung stimmte.»*

### Wann ist eine Tool-Extension besser als ein neuer Server?

| Kriterium | Neuer Server | Tool-Extension |
|---|---|---|
| Unterschiedliche Lizenz | ✅ | ❌ |
| Unterschiedlicher Trust-Level (amtlich vs. NGO) | ✅ | ❌ |
| Unterschiedliche Update-Frequenz | ✅ | — |
| Logisch gleiches Domänenfeld | ❌ | ✅ |
| User würde beide zusammen nutzen | — | ✅ |
| Unabhängiges PyPI-Release sinnvoll | ✅ | ❌ |

### Welchen Transport-Modus unterstützen?

**Immer beide:** `stdio` (Claude Desktop) + `streamable-http` / `sse` (Cloud, Railway, Render). Auswahl via `ENV_VAR_TRANSPORT`-Variable im `__main__.py`.

---

## Anti-Patterns (vermeiden)

1. **«Die Doku sagt es geht, also baue ich»** — ohne Live-Probe. Immer ein Fehler.
2. **«Retry braucht man nicht für Bulk-Downloads»** — falsch, gerade wöchentliche Exports sind während Generation oft 503.
3. **«Attribution kommt ins README»** — nein, in jede Response. README wird nicht weitergereicht.
4. **«Ich baue erst, Anchor-Query überlege ich später»** — führt zu Tool-Designs, die nie mit Demo-Szenarien getestet wurden.
5. **«Der Fehler ist Upstream, nicht mein Problem»** — Graceful Degradation ist MCP-Server-Verantwortung.
6. **«Dieser Server hat Auth, aber nur ein bisschen»** — entweder No-Auth-Teil isolieren oder Phase 2 machen. Kein Mischen.
7. **«Optional heisst unbeschränkt»** — der teuerste Irrtum der Liste. Ein weggelassener Filter-Parameter bedeutet oft einen willkürlichen Teilausschnitt, nicht «alles». Nur die Parameterbeschreibung der Spec sagt es, und nur ein Recall-Delta beweist es. Siehe 1.2b.
8. **«Null Treffer heisst, es gibt nichts»** — nicht ohne Wildcard-Retry und geprüften Scope. Und die Tool-Description darf diese Schlussfolgerung dem Modell nie nahelegen. Siehe 3.6.

---

## Qualitätschecklist vor Release

Vor `v0.1.0`-Tag alle folgenden Punkte abhaken:

**Schritt 1 – Live-Probe**
- [ ] Alle Endpoints mit 5 Probe-Calls getestet (inkl. Scope-Probe)
- [ ] Befund-Tabelle im PR / README vorhanden
- [ ] **Default-Matrix**: jeder optionale Parameter geprüft, Recall-Delta gemessen (1.2b)
- [ ] Homepage-Zahlen vs. API-Zahlen verglichen
- [ ] **Recall-Ground-Truth**: 3–5 Referenzbegriffe gegen das offizielle Web-UI, jedes Delta erklärt (1.4b)
- [ ] Dump-Verfügbarkeit geprüft

**Schritt 2 – Architektur**
- [ ] Architektur-Entscheid (A/B/C) explizit getroffen
- [ ] Portfolio-Synergie-Check durchgeführt
- [ ] Entscheid im README dokumentiert

**Schritt 3 – Resilienz**
- [ ] Retry mit exponentiellem Backoff für alle HTTP
- [ ] Pydantic-Envelope mit `source` + `provenance` in jeder Response
- [ ] Anchor Demo Query im README prominent
- [ ] Tests für Happy / Retry / Timeout
- [ ] **Recall-Canary** als `@pytest.mark.live`-Test mit Untergrenzen (1.4c)
- [ ] Graceful-Degradation-Pfad
- [ ] **Leermenge trägt `hint`**, keine Tool-Description erklärt oder entschuldigt ein leeres Resultat (3.6)
- [ ] **Query-Syntax** (Lucene/CQL/SQL) samt Matching-Granularität in der Tool-Description, nicht nur im README

**Schritt 4 – Repo**
- [ ] Repo-Description parallel zu anderen Portfolio-Servern
- [ ] Topics / Tags gesetzt
- [ ] README bilingual (EN + DE, Schweizer Rechtschreibung)
- [ ] CI grün (`pytest -m "not live"` + ruff)

**Schritt 5 – Portfolio**
- [ ] Notion-Portfolio-Karte angelegt
- [ ] Known Limitations offen dokumentiert
- [ ] PyPI-Veröffentlichung via OIDC Trusted Publisher

---

## Fundstück-Dokumentation (kultureller Baustein)

**Wenn ein nicht-offensichtlicher Fund aus der Live-Probe stammt** — z. B. «Bool-Felder wechseln wild zwischen `0/1`, `"Y"/"N"` und Boolean» —, diesen Fund im Server-Code-Kommentar UND im CHANGELOG unter «Known findings» festhalten. Damit die gleiche Erkenntnis beim nächsten ähnlichen Server direkt verfügbar ist.

**Metapher:** *«Schweizer Verwaltungs-Booleans sind wie Ampeln in Rom — zeigen alle Farben gleichzeitig.»*

Solche Metaphern dürfen (und sollen) in die Server-Dokumentation. Sie machen Portfolio-Wissen teilbar und im Gedächtnis haftend.

### Fundstück: der VARIA-Default (`termdat-mcp`, 2026-07)

Das Fundstück, aus dem 1.2b, 1.4 und 3.6 entstanden sind — und der Grund, warum es sich lohnt, diesen Abschnitt zu pflegen.

`termdat-mcp` sendete `ClassificationIds` nur bei explizitem Aufruf. Die TERMDAT-Spec: *«If no ID is given, a default set of classifications will be included (=VARIA)»*. Ergebnis: Jede Default-Suche lief gegen 1 von 23 Sachgebieten. «Quellensteuer» → 0 Treffer bei mehreren vorhandenen Einträgen; «Pensionskasse» → 1 statt 21.

Was der Fall über das Vorgehen gezeigt hat, in absteigender Unbequemlichkeit:

1. **Der Skill hatte die Prüfung bereits.** Abschnitt 1.4 «Reality-Check» hätte gereicht. Er wurde auf die Listen-Endpoints angewandt und nie auf den Such-Endpoint. Nicht die Regel fehlte, sondern ihre Reichweite. Wenn eine Regel einmal versagt, zuerst fragen, ob sie zu eng angewandt wurde — nicht sofort eine neue schreiben.
2. **33 grüne Offline-Tests haben nichts gefangen.** Mocks bilden die eigene Annahme ab. Gegen eine falsche Grundannahme sind sie prinzipiell blind.
3. **Der Server hat ein 68-Punkte-Audit bestanden.** Alle Kategorien prüften, ob er korrekt gebaut ist. Keine, ob er die Wahrheit sagt. Daraus entstand die Kategorie `FID` im `mcp-audit`-Skill.
4. **Die eigene Doku hat das Modell zum Konfabulieren gebracht.** Der Satz «an empty result usually means the term is out of scope» war als Ehrlichkeit gemeint und wirkte als Freibrief.

**Metapher:** *«Ein optionaler Filter ist wie ein Museumswärter, der ungefragt entscheidet, welchen Flügel du zu sehen bekommst — und dich freundlich versichert, du habest alles gesehen.»*

**Querverweis:** Als Audit-Checks kodifiziert in `mcp-audit` unter `FID-001` bis `FID-005`. Wer diesen Skill korrekt anwendet, besteht sie; wer sie beim Audit reisst, findet hier das Vorgehen zur Behebung.
