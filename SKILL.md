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

Jeder neue `*-mcp`-Server durchläuft die drei Schritte unten in dieser Reihenfolge; die vierte Disziplin ist kein eigener Schritt, sondern verläuft quer durch Schritt 1 (1.2b, 1.2d, 1.3b, 1.4, 1.5) und Schritt 3 (3.6). Abweichungen erfordern eine explizite Begründung, die im README unter «Architektur-Entscheid» dokumentiert wird.

---

## Schritt 1: Live-Probe (vor dem Coden) [Kern]

**Ziel:** Empirisch feststellen, was die Datenquelle tatsächlich liefert — nicht was die Dokumentation verspricht. Und zweitens: festhalten, was sie hat, das der geplante Server nicht anfassen wird. Beides ist hier billig und später teuer.

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

### 1.2c Struktur-Assertion — eine leere Probe ist noch kein Befund

Bevor eine Null in die Befund-Tabelle wandert, muss feststehen, dass die Probe **an der richtigen Stelle** gesucht hat. Sonst dokumentiert das Protokoll einen Bedienfehler als Eigenschaft der Quelle — und zwar dauerhaft, denn die Tabelle ist später die Referenz.

Belegfall aus dem Portfolio (2026-07): Eine Abfrage der MCP Registry lieferte konsequent nichts. Die Felder liegen dort unter `servers[].server.*`; die Probe suchte sie eine Ebene höher. Kein Fehler, kein Status-Code, keine Warnung — nur eine leere Liste, die exakt so aussieht wie «diese Quelle kennt den Eintrag nicht».

```bash
# FALSCH — unterscheidet nicht zwischen «nichts da» und «falsch gelesen»
curl -s "$URL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('servers',[])))"

# RICHTIG — erst die Struktur bestätigen, dann zählen
curl -s "$URL" | python3 - <<'EOF'
import json, sys
d = json.load(sys.stdin)
assert "servers" in d, f"Antwort hat kein 'servers' — Keys: {list(d)[:10]}"
rows = d["servers"]
assert rows, "Huelle vorhanden, aber leer — das ist ein echter Nullbefund"
sample = rows[0]
assert "name" in sample or "name" in sample.get("server", {}), \
    f"'name' weder oben noch unter 'server' — Struktur: {json.dumps(sample)[:200]}"
print(len(rows))
EOF
```

**Regel:** Jede Probe, die null meldet, druckt bei null zusätzlich die **obersten Schlüssel der Antwort** und einen gekürzten Rohauszug. Das kostet zwei Zeilen und trennt die beiden Fälle sofort.

In der Befund-Tabelle bekommt jede Null eine Spalte «Struktur bestätigt»:

| Endpoint | HTTP | Records | Struktur bestätigt | Bemerkung |
|---|---|---:|---|---|
| `/v0/servers?search=x` | 200 | 0 | ✅ Hülle + Beispielzeile geprüft | echter Nullbefund |
| `/v0/servers?search=y` | 200 | 0 | ❌ noch offen | **kein** Befund, Probe nachziehen |

Das ist dieselbe Regel wie 3.6 («Leermenge ≠ Abwesenheit»), eine Ebene höher: Dort schützt sie das Modell vor dem Tool, hier die Probe vor sich selbst.

**Verwandt — aggregierte Endpoints hinken nach.** Liefert eine Quelle dieselbe Information über mehrere Wege, sind sie nicht gleich aktuell. Bei PyPI meldete der JSON-Sammel-Endpoint (`/pypi/<pkg>/json`) **dreimal in Folge** nach einem Release noch die Vorversion, während der Simple Index und eine echte Installation sofort korrekt waren. Für jede Freshness-Aussage im Protokoll gehört deshalb dazu, **welcher** Endpoint befragt wurde — und für die belastbare Aussage der autoritative, nicht der bequeme.

### 1.2d Feldnamen-Inventar — die Schreibweise ist Teil des Befunds

**Regel:** Die Live-Probe protokolliert die **tatsächlichen** Feld- bzw. Spaltennamen jeder Antwort, **samt Schreibweise** — Gross-/Kleinschreibung, Umlaute, Trennzeichen, Leerzeichen, BOM. Und sie legt die rohe Antwort als **aufgezeichnete Fixture** ab, aus der später die Tests lesen.

Das ist die einzige Regel in Schritt 1, die nicht die Menge der Daten betrifft, sondern ihre Beschriftung. Sie steht hier, weil die Beschriftung genau einmal billig zu messen ist: in dem Moment, in dem die Probe die Antwort ohnehin in der Hand hat.

**Belegfall aus dem Portfolio (2026-08-03).** Eine Quelle wechselte die Schreibweise ihrer CSV-Kopfzeile von `Schulgemeinde` auf `schulgemeinde`. Vier von sechs Datensätzen eines Servers lieferten daraufhin nichts mehr. **Alle Unit-Tests blieben grün** — ihre von Hand geschriebenen Fixtures pinnten die alte Schreibweise, also prüften sie den Server gegen eine Welt, die es nicht mehr gab. Der Ausfall war live sichtbar und im Testlauf unsichtbar, und das ist die teure Kombination: Ein handgeschriebenes Fixture ist eine Behauptung über die Quelle, kein Beleg. Es kann per Konstruktion nicht auffallen, wenn die Quelle sich bewegt.

```bash
# Feldnamen-Inventar: was die Quelle WIRKLICH schreibt, nicht was die Doku sagt.
# repr() statt print(): macht Leerzeichen am Rand, BOM und NBSP sichtbar —
# genau die Zeichen, an denen ein Lookup scheitert, ohne sich zu zeigen.
curl -sS "$URL" -o fixtures/raw/quelle_2026-08-03.csv     # aufgezeichnet, nicht getippt
python3 - fixtures/raw/quelle_2026-08-03.csv <<'PY'
import csv, sys
with open(sys.argv[1], encoding="utf-8-sig", newline="") as fh:
    header = next(csv.reader(fh))
for name in header:
    print(repr(name))
PY

# JSON: dieselbe Frage, eine Ebene tiefer
curl -sS "$URL" -o fixtures/raw/quelle_2026-08-03.json
python3 - fixtures/raw/quelle_2026-08-03.json <<'PY'
import json, sys
rows = json.load(open(sys.argv[1], encoding="utf-8"))
rows = rows if isinstance(rows, list) else rows.get("results", [])
assert rows, "keine Zeile — erst 1.2c klaeren, dann hier weiter"
for name in rows[0]:
    print(repr(name))
PY
```

Ins Probe-Protokoll kommt die Liste vollständig, nicht als «wie dokumentiert»:

| Datensatz | Feld laut Doku | Feld gemessen (`repr`) | Aufgezeichnet am | Fixture |
|---|---|---|---|---|
| Schulliste | `Schulgemeinde` | `'schulgemeinde'` | 2026-08-03 | `fixtures/raw/schulen_2026-08-03.csv` |
| Schulliste | `PLZ` | `'PLZ'` | 2026-08-03 | `fixtures/raw/schulen_2026-08-03.csv` |
| Klassen | — | `'﻿Jahr'` | 2026-08-03 | `fixtures/raw/klassen_2026-08-03.csv` |

**Aufgezeichnet, nicht getippt.** Ein Fixture wird aus der echten Antwort gespeichert und mit dem Abrufdatum im Namen abgelegt; es wird nicht von Hand nachgebaut. Ein nachgebautes Fixture erbt die Erwartung des Schreibenden — das ist derselbe Fehler wie in 1.4, nur eine Schicht tiefer: Der grüne Test beweist dann, dass der Server tut, was erwartet wurde, nicht dass die Erwartung noch stimmt.

**Was daraus für Schritt 3 folgt.** Feldnamen sind Fremddaten, kein Vertrag. Ein Lookup, der genau eine Schreibweise kennt, ist ein Ausfall mit Ankündigung; entweder wird beim Einlesen normalisiert (`strip()`, casefold, BOM weg) oder die akzeptierten Schreibweisen stehen explizit im Code. Und mindestens ein Test liest die aufgezeichnete Fixture, damit ein Schreibweisen-Wechsel beim nächsten Aufzeichnen als Diff auffällt, statt als Nullbefund in der Produktion.

### 1.3 Befund-Tabelle erstellen

Ausgabe von Schritt 1 ist **immer** eine Tabelle in diesem Format:

| Endpoint | HTTP | Status | Records | Bemerkung |
|---|---|---|---|---|
| `/table/X/list` | 200 | ✅ funktioniert | 139 | wie dokumentiert |
| `/table/Y/list` | 200 | ⚠️ leer | 0 | SQL-Filter zu restriktiv |
| `/table/Z/id/1` | 404 | ❌ existiert nicht | – | Doku veraltet |
| `/search/default/Foo` | 200 | ✅ funktioniert | ~5 | |

### 1.3b Abdeckungs-Matrix — welcher Teil des Bestands bleibt unerreichbar

**Ziel:** Die Befund-Tabelle hält fest, was die geprobten Endpoints liefern. Sie hält damit noch nicht fest, welcher Teil des Bestands über die **geplanten Tools** gar nicht erreichbar ist. Genau diese Zeile fehlt später, wenn jemand den Scope begründen muss.

Der Unterschied zu 1.2b: Dort liefert ein befragter Endpoint weniger als erwartet, und ein Delta beweist es. Hier gibt es kein Delta, weil niemand gefragt hat — Bestandsteile, die kein geplanter Endpoint anfasst, erzeugen keinen Fehler, keine Auffälligkeit und keine Zeile. Aus der Probe heraus sind sie per Konstruktion unsichtbar.

**Warum das in Schritt 1 gehört und nicht in Schritt 2.** Der Scope wird später begründet: im README, im Audit, gegenüber einem User, der etwas vermisst. Wer erst dann begründet, rekonstruiert — und Rekonstruktion liefert plausible Gründe, nicht gemessene. Portfolio-Fall: Ein Audit-Befund (`ARCH-003`) verlangte die Begründung des Architektur-Entscheids. Die nachgelieferte Begründung erklärte Konkurse und Baugesuche für ausserhalb der Quelle. Tatsächlich liegen sie in der Quelle und nur ausserhalb der geplanten Tools. Der Scope war richtig, die Begründung falsch — und falsch auf die teure Art, weil sie die Quelle kleiner macht, als sie ist. Zwei Zeilen im Probe-Protokoll hätten den Fehler unmöglich gemacht: Wer den Scope begründet, zitiert dann Gemessenes.

**Die Achse kommt aus der Quelle, nicht aus dem Plan.** Fast jede Quelle trägt eine explizite Bestandsachse — Rubriken, Publikationstypen, Registerarten, Themen, Datasets — und diese Liste ist meist selbst ein Endpoint (`/categories`, `/types`) oder eine Facetten-Aggregation. Sie wird vollständig enumeriert, danach werden die geplanten Tools **hineinmarkiert**. Der umgekehrte Weg — die Liste aus dem Tool-Entwurf bilden — kann nichts finden, was der Entwurf übersieht.

```bash
# Bestandsachse der Quelle enumerieren, vollständig, vor der Tool-Planung
curl -s "$BASE/categories" -o cats.json
python3 - cats.json <<'PY'
import json, sys
cats = json.load(open(sys.argv[1], encoding="utf-8"))
COVERED = {"hr", "sh"}          # von Hand: was die geplanten Tools abfragen
for c in cats:
    key = c["id"]
    mark = "erreichbar" if key in COVERED else "NICHT erreichbar"
    print(f"{key:<20} {c.get('count', '?'):>9}  {mark}")
PY
```

Ohne Kategorien-Endpoint: Facetten einer leeren Suche, das Typ-Feld des Bulk-Dumps auszählen, oder die Rubrikenliste der offiziellen Oberfläche — dieselbe Ground Truth wie in 1.4, eine Frage früher gestellt.

| Bestandsteil | in der Quelle | über geplante Tools | Beleg | Grund |
|---|---:|---|---|---|
| Handelsregister-Meldungen | 812'000 | ✅ | `/search?rubric=HR`, 200 | Kern der Anchor-Query |
| Konkurse | 96'000 | ❌ | Rubrik enumeriert, kein Tool | bewusst ausserhalb Scope (Phase 1) |
| Baugesuche | 41'000 | ❌ | Rubrik enumeriert, kein Tool | bewusst ausserhalb Scope (kantonal uneinheitlich) |
| Betreibungen | ? | ❌ | Auth nötig (401) | technisch nicht erreichbar |

**Drei zulässige Gründe für ein ❌, mehr nicht:**

1. **bewusst ausserhalb des Scopes** — mit dem Grund, nicht nur mit dem Wort
2. **technisch nicht erreichbar** — kein Endpoint, Auth, Lizenz, Rate-Limit
3. **noch offen** — nicht geprüft; ein offener Befund, kein Freibrief

Nicht zulässig ist die vierte Möglichkeit, die in der Praxis die häufigste ist: gar nicht erwähnt. Eine Zeile ohne Grund ist ein offener Befund und gehört ins README, nicht in den Papierkorb — dieselbe Regel wie beim unerklärten Delta in 1.4b.

**Wohin das Ergebnis geht:** in die Rationale des Architektur-Entscheids (2.3) und ins README unter «Known limitations» / «Scope». Ein Server, der ein Viertel des Bestands abdeckt, ist völlig in Ordnung; ein Server, der nicht sagen kann, welches Viertel, ist es nicht.

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

### 1.5 Widening-Schedule gegen die Live-API messen

**Ziel:** Wenn ein Tool bei null Treffern den Suchbegriff verkürzt und erneut fragt, ist diese Staffel eine Annahme über die Quelle — über ihre Matching-Granularität, ihre Stemming-Regeln, ihre Mindestlänge. Die Quelle beantwortet die Frage selbst, in einer Handvoll Calls: **ab welcher Präfixlänge liefert sie Treffer?** Das ist billig zu messen, solange man ohnehin an der API hängt, und teuer zu raten, weil eine zu früh abgebrochene Staffel wie ein sauberer Nullbefund aussieht (3.6).

**Belegfall.** Eine Staffel kürzte den Suchbegriff in Schritten von 30 % und hatte ihre unterste Stufe bei acht Zeichen. Für `Betonsanierungsarbeiten` endete sie damit bei `Betonsan`; Treffer lieferte die Quelle erst ab `Beton`. Drei Zeichen Abstand, und die Antwort lautete «nichts gefunden» für einen Bestand, der die Einträge hatte. Der Prozentsatz war nicht knapp daneben — er war die falsche Grösse. Deutsche Komposita brechen an Morphemgrenzen (`Beton|sanierungs|arbeiten`), und eine Prozentstaffel trifft eine Morphemgrenze nur zufällig. Die brauchbare Zahl steht nicht in der Formel, sondern in der Quelle.

**Die Messung** — pro Testbegriff jede Präfixlänge einmal abfragen:

```bash
widening_probe() {
    # $1 = Testbegriff. Eine Zeile pro Präfixlänge: ab wo liefert die Quelle?
    local term="$1" n p hits
    for (( n=${#term}; n>=3; n-- )); do
        p="${term:0:n}"
        hits=$(curl -s --get --data-urlencode "q=$p" "$BASE/search" \
            | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('data') or []))")
        printf "  %2d  %-28s %s\n" "$n" "$p" "$hits"
    done
}
widening_probe "Betonsanierungsarbeiten"
```

3–5 Begriffe, bewusst gewählt: ein langes Kompositum, einer mit Bindestrich (bricht die Staffel am Trennzeichen?), einer mit Umlaut (Encoding über die Kürzung hinweg), einer aus einer anderen Sprachregion. **Nicht** die Anchor-Demo-Query — sie funktioniert immer, aus demselben Grund wie in 1.4b.

Das sind rund zwanzig Aufrufe pro Begriff. Bei engen Rate-Limits in Zweierschritten laufen und die Grenze danach binär einkreisen — die gesuchte Zahl ist ein einzelner Übergang von 0 auf n, keine Kurve.

| Testbegriff | Länge | kürzestes Präfix mit Treffern | Treffer | Morphemgrenze | Wildcard-Alternative |
|---|---:|---|---:|---|---|
| `Betonsanierungsarbeiten` | 23 | `Beton` (5) | 143 | ✅ | `Beton*` → 143 |
| `Gebäudeversicherung` | 19 | `Gebäude` (7) | 88 | ✅ | `Gebäude*` → 88 |
| `Baubewilligung` | 14 | `Baubewilligung` (14) | 12 | – | `Baubewilligung*` → 19 |

Die dritte Zeile ist der Fall, den eine Staffel nicht lösen kann: Kürzen hilft nicht, weil kein Präfix ein ganzes Wort ist — Treffer bringt hier nur die Wildcard. Wer nur die Staffel baut, hat für diese Begriffsklasse gar keinen zweiten Versuch.

**Drei Dinge entscheidet diese Messung, die vorher geschätzt wurden:**

1. **Die unterste Stufe.** Sie kommt aus der Spalte «kürzestes Präfix», nicht aus einem Prozentsatz. Eine Staffel, die diesen Wert nicht erreicht, meldet Abwesenheit für vorhandene Daten — und zwar leise.
2. **Ob die Staffel überhaupt das richtige Mittel ist.** Beherrscht die Quelle Präfix-Wildcards, liefert `Beton*` dasselbe in einem einzigen Aufruf. Dann ist die Staffel ein Workaround für eine vorhandene Funktion, mit N-fachem Verkehr und N-facher Latenz. Die Wildcard-Spalte gehört deshalb in dieselbe Messung: Steht sie, ist der Entscheid schon getroffen.
3. **Wo die Präzision kippt.** Nach unten hin trifft jedes Präfix irgendwann alles — `Be` fängt die halbe Quelle. Die Messung zeigt beide Enden. Eine Staffel braucht nicht nur einen Boden, sondern auch die Stufe, ab der sie besser abbricht und einen `hint` zurückgibt (3.6), statt 4'000 unspezifische Treffer als Erfolg auszugeben.

**Was ins Protokoll geht:** die Tabelle oben, und die gemessene unterste Stufe zusätzlich als Kommentar an die Staffel im Code — mit Begriff und Datum. Ohne diesen Kommentar wird die Zahl beim nächsten Refactoring auf einen runden Wert «vereinfacht», und die Messung war umsonst. Analog zum Recall-Canary aus 1.4c lohnt ein Live-Test, der den gemessenen Begriff über die Staffel schickt und Treffer verlangt: Er fängt sowohl eine gekürzte Staffel als auch eine Upstream-Änderung an der Matching-Granularität.

Führt der Server das Widening automatisch aus, gilt zusätzlich 3.6: Die Antwort muss sagen, **welche** Begriffe versucht wurden. Sonst ist die Leermenge nach fünf stillen Versuchen von der Leermenge nach einem nicht unterscheidbar.

### 1.6 Dump-Verfügbarkeit prüfen

Parallel zu den API-Probes **immer** prüfen, ob die Quelle einen Bulk-Download anbietet:

- CSV / JSON / XML / SQL-Dump
- Datenmenge und Update-Frequenz
- Lizenz gleich wie API (meistens ja, sicherheitshalber prüfen)

**Faustregel:** Jede Schweizer Behörden- oder NGO-Datenquelle, die «seriös» ist, bietet einen Dump. Wenn keiner auffindbar ist, gezielt nachfragen oder in GitHub-Issues suchen.

### 1.7 Aktualisierungsrhythmus messen — die Grundlage für `ttlMs` und `cacheScope`

**Ziel:** Festhalten, **wann** sich der Bestand ändert. Diese eine Beobachtung entscheidet später, wie lange ein Client eine Antwort behalten darf — und sie ist nach dem Bau nicht mehr billig zu bekommen, weil sie eine Serie über Tage ist und kein einzelner Call.

Der Schritt fragt genau eine Frage und variiert genau eine Grösse: die Zeit. Endpoint, Parameter und Abfrage bleiben über alle Messpunkte identisch — sonst misst man Parameterwirkung statt Rhythmus. Deshalb ist er ein eigener Schritt und kein Anhängsel an 1.6: Dort geht es darum, **ob** es einen Dump gibt, hier darum, **wann** die Quelle neu ist, und das gilt für Dump und Live-API gleichermassen.

**Die Behauptung steht in der Doku, die Messung im Header.** «Täglich aktualisiert» im Katalogeintrag ist derselbe Typ Aussage wie ein dokumentierter Parameter-Default aus 1.2b: plausibel, oft richtig, nie belegt. Belegt wird sie mit einer Serie — dieselbe Ressource, mehrfach, über mindestens zwei erwartete Zyklen:

```bash
# Eine Zeile pro Messpunkt. Ein einzelner Abruf zeigt einen Zeitstempel,
# keine Periode — und die Periode ist das Gesuchte.
freshness_probe() {
    printf '%s  ' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    curl -sI "$1" | python3 -c "
import sys
h = {k.strip().lower(): v.strip()
     for k, v in (l.split(':', 1) for l in sys.stdin.read().splitlines() if ':' in l)}
print('last-modified:', h.get('last-modified', '—'), '| etag:', h.get('etag', '—'))
"
}
freshness_probe "$BASE/dump/current.json"
```

Liefert die Quelle weder `Last-Modified` noch `ETag`, trägt eine andere Stelle dieselbe Information — in dieser Reihenfolge, weil sie unterschiedlich nah an der Wahrheit sind:

1. ein Datums- oder Versionsfeld **im Payload** (`stand`, `updated_at`, `data_version`),
2. das Dateidatum des Bulk-Dumps oder der Verzeichnisindex, der ihn listet,
3. der Katalogeintrag (opendata.swiss, CKAN `metadata_modified`),
4. die Angabe der offiziellen Oberfläche — dieselbe Ground Truth wie in 1.4, eine andere Frage gestellt.

Der Vorbehalt aus 1.2c gilt hier besonders: **aggregierte Endpoints hinken nach.** Ein Katalogeintrag, der die Aktualisierung meldet, bevor der Dump sie hat, ist für `ttlMs` schlimmer als gar keine Angabe — er verspricht eine Frische, die der ausgelieferte Datenstand nicht hat.

**Wo die Felder sitzen.** `ttlMs` und `cacheScope` stehen auf der **obersten Ebene des Result-Objekts**, nicht in `_meta`. Die Spec bündelt sie in `CacheableResult`:

```typescript
export interface CacheableResult extends Result {
  ttlMs: number;
  cacheScope: "public" | "private";
}
```

Sechs Result-Typen erben davon: `ListToolsResult`, `ListPromptsResult`, `ListResourcesResult`, `ListResourceTemplatesResult`, `ReadResourceResult` und `DiscoverResult` — Letzterer für den optionalen `server/discover`-RPC aus 2.4. **`CallToolResult` gehört nicht dazu:** Ein Tool-Ergebnis trägt keine Cache-Angabe, und wer eine hineinschreibt, hat sie erfunden.

`ttlMs` ist in dieser Schnittstelle **nicht optional**. Es gibt kein Weglassen und Offenlassen — jede List-, Read- und Discover-Antwort nennt eine Zahl. Damit ist diese Messung keine Kür: Die Alternative zur gemessenen Zahl ist nicht «keine Zahl», sondern eine geratene.

**Zwei `ttlMs`-Familien, nicht eine.** Die sechs Typen zerfallen in zwei Haltbarkeiten mit zwei verschiedenen Uhren:

| Response | Was veraltet | Uhr | Woher die Zahl kommt |
|---|---|---|---|
| `resources/list`, `resources/templates/list`, `resources/read` | die **Daten** | Aktualisierungsrhythmus der Quelle | diese Messung |
| `tools/list`, `prompts/list`, `server/discover` | die **Oberfläche** des Servers | Deployment-Rhythmus | Release-Kadenz, nicht die Quelle |

Wer beiden dieselbe Zahl gibt, trifft eine von zwei Fehlentscheidungen: Er hält eine Tool-Liste über ein Release hinweg fest, oder er wirft stündlich einen Katalog weg, der sich zweimal im Jahr ändert. Für die Oberfläche ist ein Tagesdeckel die brauchbare Faustregel — sie ändert sich beim Deployment, und ein Deployment kündigt sich einem Client nicht an.

**Die Ableitung für die Datenseite:**

| Rhythmus der Quelle | Beispiel | Empfohlenes `ttlMs` | Warum |
|---|---|---|---|
| periodisch, Zeitpunkt bekannt | MADD, täglich gegen 05:30 CET | Rest bis zum nächsten Lauf **plus Karenz**, pro Response berechnet | die Antwort weiss, wo im Zyklus sie steht — ein fixer Wert weiss es nie |
| periodisch, Zeitpunkt unbekannt | «wöchentlich», ohne Wochentag | halbe Periode, statisch (wöchentlich → 302'400'000) | ohne Zeitpunkt ist die halbe Periode der schlechteste Fall, den man garantieren kann |
| unregelmässig, ereignisgetrieben | Meldungsstrom, Störungsmeldungen | kurz, Minuten (z. B. 300'000) — und die Kürze begründet | es gibt keine Periode; ein langes TTL wäre eine Behauptung über die Zukunft |
| selten bis statisch | Jahresstatistik, Nomenklatur | lang, aber gedeckelt (86'400'000) | jenseits eines Tages hängt die Gültigkeit am Deployment, nicht mehr an der Quelle |

**Die Karenz kommt aus der Serie, nicht aus einem runden Wert.** Ein Nachtlauf, der meist um 05:30 fertig ist, ist an manchen Tagen um 06:07 fertig. Ein `ttlMs`, das exakt um 05:30 abläuft, holt an diesen Tagen den alten Stand und hält ihn einen ganzen Zyklus — der Fehler ist nicht 37 Minuten gross, sondern 24 Stunden. Die Karenz ist deshalb die grösste in der Messreihe beobachtete Verspätung, aufgerundet; dieselbe Logik wie bei der untersten Staffelstufe in 1.5, wo die brauchbare Zahl auch in der Quelle steht und nicht in der Formel.

**`cacheScope` hat zwei Werte, und dahinter steht eine einzige Frage:** Darf diese Antwort über **Autorisierungskontexte hinweg** geteilt werden? Die Semantik ist die von HTTP `Cache-Control`, mitsamt der Falle, die dort dieselbe ist — der Wert sagt nicht, wie vertraulich die Daten sind, sondern wer die gecachte Kopie zu sehen bekommt.

- **`"public"`** — die Antwort ist in jedem Autorisierungskontext dieselbe und darf von einem gemeinsamen Zwischenspeicher geteilt werden. Öffentliche Behördendaten ohne Auth: der Normalfall in Phase 1, und genau das Erwünschte. Ein 17-MB-Dump, den jede Sitzung neu zieht, ist die Kostenseite von 2.3.
- **`"private"`** — die Antwort hängt am Autorisierungskontext und bleibt in ihm. Sobald Auth im Spiel ist (Phase 2), ist das der Default, auch wenn der Inhalt zufällig für alle gleich aussieht: Die Frage ist nicht, ob die Daten geheim sind, sondern ob der Server garantieren kann, dass jeder Kontext dieselbe Antwort bekäme.

Der Entscheid fällt **pro Response-Typ, nicht pro Server**: Eine öffentliche Tool-Liste und eine auth-abhängige Resource-Liste im selben Server sind kein Widerspruch. Handles als Tool-Argumente (Stateless Core, 2.4) ändern daran nichts — Tool-Ergebnisse tragen die Felder gar nicht. Wer die Frage falsch beantwortet, baut den einen Fehler, den ein Cache machen kann und den kein TTL repariert: die Antwort für den falschen Aufrufer.

**Frische innen, Haltbarkeit aussen.** Zwei Zahlen, zwei Richtungen, und sie werden regelmässig verwechselt:

- `retrieved_at` und `source_freshness` im Response-Envelope — neben `source` und `provenance` aus 3.2 — sagen, **wie alt die Daten sind**. Eine Aussage über die Vergangenheit, gerichtet an den Leser der Antwort.
- `ttlMs` sagt, **wie lange die Antwort gültig bleibt**. Eine Aussage über die Zukunft, gerichtet an den Cache des Clients.

**Merksatz fürs Portfolio:** *«Frische innen (`source_freshness`), Haltbarkeit aussen (`ttlMs`).»*

Sie sind nie dieselbe Zahl, und die eine ersetzt die andere nicht. Ein `ttlMs` von zwölf Stunden auf einem Datenstand von gestern ist kein Widerspruch — es heisst «diese Antwort bleibt zwölf Stunden korrekt, und korrekt ist: Stand gestern». Fehlt die innere Angabe, liest der Client die äussere als Datenalter und irrt sich um einen ganzen Zyklus.

**Deterministische Reihenfolge gehört in dieselbe Messung.** Die Spec verlangt sie für List-Responses, und ohne sie ist ein `ttlMs` wertlos: Wer bei jedem Aufruf eine andere Reihenfolge bekommt, kann zwei Antworten nicht vergleichen und cacht eine Momentaufnahme statt eines Zustands. Quellen ohne `ORDER BY` (SQL-über-HTTP, Solr ohne `sort`, viele SPARQL-Endpoints) garantieren upstream nichts — dann sortiert der Server, und der Sortierschlüssel gehört ins Protokoll. Die Probe dazu ist eine Zeile: denselben Listen-Call zweimal, die IDs vergleichen.

**Was ins Protokoll geht** — eine Zeile pro Ressource, die eine List- oder Read-Response bedient:

| Ressource | dokumentierter Rhythmus | gemessene Serie | grösste Verspätung | empfohlenes `ttlMs` | `cacheScope` | Reihenfolge stabil |
|---|---|---|---|---|---|---|
| Tages-Dump | «täglich» | 05:28 / 05:31 / 06:07 CET | +37 min | bis 05:30 + 45 min, dynamisch | `"public"` | ✅ upstream nach `id` |
| Katalog-Endpoint | «laufend» | 4 Änderungen in 14 Tagen | – | 300'000 | `"public"` | ⚠️ Server sortiert nach `id` |
| Nomenklatur | «jährlich» | unverändert über 14 Tage | – | 86'400'000 (Deckel) | `"public"` | ✅ upstream |

**Wohin das Ergebnis geht:** in die Konsequenzen des Architektur-Entscheids (2.3), zusammen mit der internen Cache-TTL, die dort schon steht — die beiden sind nicht dasselbe und stehen bewusst nebeneinander. Die interne TTL sagt, wann der Server neu holt; `ttlMs` sagt, wann der Client neu fragt. Ein Server, dessen interne TTL länger ist als das `ttlMs`, das er verspricht, beantwortet die neue Anfrage aus demselben alten Cache und hat die Zusage gebrochen, ohne dass es jemand merkt.

---

## Schritt 2: Architektur-Entscheid [Kern]

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

Scope (measured, see coverage matrix in step 1.3b):
- Reachable: rubrics HR and SH — 812'000 of roughly 950'000 records.
- Out of scope by decision: bankruptcies, building permits — present in the
  source, not covered by any tool of this server.
- Out of reach: debt-enforcement records — the endpoint requires authentication.

Spec target: MCP 2026-07-28 (portfolio default, no deviation — see step 2.4).

Consequences:
- Transports: stdio and streamable-http.
- Dump is cached on disk with Z hours TTL — one cache per process under stdio,
  one shared cache per instance under streamable-http.
- Cache lifetime advertised to clients: ttlMs is derived from the source's daily
  05:30 CET refresh and computed per response; the same answer is served to
  every caller. Measured in step 1.7, not estimated.
- Library functions / retry / provenance behaviour: see docstrings.
```

**Der Transport gehört in die Konsequenzen.** Unterstützt werden immer beide —
`stdio` für Claude Desktop, `streamable-http` für Cloud-Deployments. Damit ist
bei ARCH B und C eine zweite Entscheidung getroffen, ohne dass sie jemand
ausgesprochen hat: Unter `stdio` startet pro Client ein eigener Prozess, der
Cache lebt genau eine Sitzung und der Dump wird pro Sitzung neu geladen. Unter
`streamable-http` bedient ein Prozess viele Clients, derselbe Cache lebt so
lange wie die Instanz und wird geteilt. Dieselbe TTL bedeutet also zwei
verschiedene Dinge — bei einem 17-MB-Dump die Frage, ob jede Sitzung ihn zieht
oder keine.

**Der Scope gehört in dieselbe Begründung, mit Zahlen.** Ein Architektur-Entscheid
sagt, *wie* die Daten geholt werden; ohne den Scope-Absatz sagt er nicht, *welche*.
Die Zeilen dafür stehen bereits in der Abdeckungs-Matrix aus 1.3b und müssen nur
übernommen werden — genau darum wurde sie beim Proben angelegt und nicht hier.
Wer sie erst hier schreibt, schreibt sie aus dem Gedächtnis.

Das ändert auch, was `provenance: cached` aus 3.2 aussagt: unter `stdio` «in
dieser Sitzung schon geholt», unter `streamable-http` «womöglich Stunden alt und
für jemand anderen geholt». Den Zeitstempel des letzten erfolgreichen Abrufs
verlangt 3.5 bereits — dort für den Ausfall. Bei geteiltem Cache braucht ihn
auch die erfolgreiche Antwort, sonst hängt das Alter der Daten an der
Deployment-Konfiguration statt an der Antwort.

### 2.4 Spec-Ziel-Entscheid — welche `mcp_spec_version` der Server spricht

**Ziel:** Neben A/B/C trägt jeder neue Server einen zweiten Pflicht-Entscheid: gegen welche MCP-Spec-Version er gebaut wird. Er wird gleich behandelt wie der Architektur-Entscheid — hier getroffen, im README begründet, im Portfolio eingetragen. Ein Entscheid, der nur im Code steht, ist kein Entscheid, sondern ein Zustand.

**Standard neu: `2026-07-28`.** Das ist kein Vorschlag, sondern der Default. Die Tier-1-SDKs (Python, TypeScript, Go, C#) sprechen die Version; für Variante A des Portfolios (`mcp` 2.x mit `MCPServer`) gibt es damit keinen technischen Abweichungsgrund.

**Die zulässigen Abweichungsgründe, abschliessend:**

1. **Ein SDK-Pin blockiert.** Standalone `fastmcp` 3.x pinnt `mcp` unterhalb 2.0, `fastmcp` 4.0 ist erschienen und bringt Breaking Changes. Wer auf dieser Variante baut, trägt drei Dinge ein: die Version, die das SDK tatsächlich spricht, den Pin, der sie erzwingt, und die Bedingung, unter der die Abweichung endet.
2. **Eine belegte Upstream-Abhängigkeit.** Ein Client oder eine Deployment-Plattform, die nachweislich noch nicht so weit ist — mit Beleg, nicht mit Vermutung.

Nicht zulässig: «das Beispiel im Tutorial sah anders aus», «der letzte Server im Portfolio macht es so», «wir migrieren später ohnehin». Der dritte ist der teuerste, weil er stimmt und trotzdem falsch ist: Ein neuer Server auf altem Stand vergrössert genau die Migrationswelle, deren Ende er abwarten will.

**Kein neuer Server auf deprecated Bausteinen.** Vier Bausteine stehen im 12-Monats-Fenster. Ein bestehender Server darf sie tragen, bis seine Welle dran ist; ein neuer fängt nicht damit an. Das Fenster ist eine Frist für Bestehendes, kein Budget für Neues.

| Deprecated | Ersatz | Was das konkret heisst |
|---|---|---|
| Roots | explizite Handles als Tool-Argumente | Der Server fragt den Kontext nicht ab, er bekommt ihn übergeben |
| Sampling (und serverinitiierte Elicitation) | MRTR: `resultType: "input_required"` plus Retry mit `inputResponses` | Der Server initiiert nichts; er meldet, was ihm fehlt, und wird erneut gerufen |
| Logging | maschinenlesbarer Status im Response-Envelope | 3.5 verlangt ihn ohnehin: Die Fehlerklasse gehört in die Antwort, nicht in einen Nebenkanal |
| Legacy HTTP+SSE | Streamable HTTP mit `Mcp-Method` und `Mcp-Name` | Beide Header sind Pflicht, nicht optional — fehlen sie, ist der Aufruf keiner. Die Umsetzung im Einstiegspunkt gehört in `mcp-transport-hardening` |

**Stateless Core schärft 2.3, es weicht ihn nicht auf.** `initialize`/`initialized` und `Mcp-Session-Id` sind abgeschafft; jede Anfrage trägt Protokollversion, `clientInfo` und Capabilities im `_meta`, und Anwendungszustand existiert nur als explizites Handle in einem Tool-Argument. Für einen Dump-Cache (ARCH B und C) heisst das: Der Cache ist ein Prozess-Detail, kein Sitzungszustand. Die Unterscheidung aus 2.3 — eine Sitzung unter `stdio`, eine Instanz unter `streamable-http` — bleibt richtig; sie darf nur nicht über eine Session-ID modelliert werden, die es nicht mehr gibt. Wer den optionalen `server/discover`-RPC anbietet, behandelt ihn wie eine List-Response: `ttlMs` und `cacheScope` aus 1.7, deterministische Reihenfolge.

**Extensions sind nicht Teil der Basis.** Tasks, MCP Apps und Enterprise Managed Authorization laufen als versionierte Extensions unter `io.modelcontextprotocol/*`. Für einen neuen Portfolio-Server der Phase 1 heisst das: nicht bauen. «Keine neuen Features während der Migration» gilt für sie zuerst — sie sehen wie Spec aus, sind aber eine zusätzliche Abhängigkeit mit eigener Version und eigenem Lebenszyklus.

**Auth-Härtung — der Vorbehalt für Phase 2.** Phase 1 ist No-Auth (1.1), der Punkt bleibt deshalb meist theoretisch. Sobald ein Server Auth trägt, gelten drei Dinge sofort: `iss`-Validierung nach RFC 9207, CIMD statt Dynamic Client Registration, und issuer-gebundene Client-Credentials. Ein Server, der Auth «nur ein bisschen» dazunimmt, ist Anti-Pattern 6 — daran ändert die neue Spec nichts.

**Wo der Entscheid landet — drei Orte, wie beim Architektur-Entscheid:**

1. **README**, im selben Abschnitt «Architecture decision». Der Spec-Entscheid ist Teil derselben Begründung und kein zweiter Abschnitt darunter: Wer die Architektur liest, liest auch, wogegen sie gebaut ist.
2. **`portfolio.json`** im Index-Repo `swiss-public-data-mcp`: `mcp_spec_version`, dazu `sdk_flavour`, `sdk_constraint`, `migration_wave` und `migration_status`. Ein neuer Server wird auf dem Ziel geboren und trägt trotzdem alle fünf Felder — sonst fehlt er in jeder Auswertung, die über sie läuft, und «fehlt» liest sich dort wie «noch nicht migriert».
3. **Die menschenlesbare Hälfte des Portfolio-Registers** (5.2) — bei diesem Portfolio die Notion-Karte, anderswo, was dort dieselbe Rolle spielt.

---

## Schritt 3: Resilienz-Defaults (nicht-verhandelbar) [Kern]

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

**Zwei Fehlerklassen, zwei nächste Schritte.** Der Satz oben gilt für den **Ausfall** — Timeout, Verbindungsabbruch, 5xx. Eine **Abweisung** ist etwas anderes: Bei `401`, `403` oder `421 Invalid Host header` antwortet die Quelle und nimmt den Aufruf nicht an. Warten behebt das nie, und 3.1 retried 4xx aus genau diesem Grund nicht — `429` ist die Ausnahme, dort ist Warten tatsächlich der richtige Schritt. Für die übrigen muss die Meldung auf die Konfiguration zeigen: *«Die Quelle hat den Abruf abgewiesen (HTTP 421). Endpoint, Host-Header und Credentials prüfen — ein erneuter Versuch ändert daran nichts.»*

Ein nächster Schritt, der nicht zum Fehler passt, ist derselbe Fehler wie ein Leermengen-Hinweis, der zur Wildcard rät, während die Abfrage nie angekommen ist (3.6). «In 10 Minuten nochmal» auf einen falschen Host-Header schickt den Aufrufer in eine Schleife, die per Konstruktion nicht terminiert.

Implementation: `dump_status()`-Tool gibt immer einen auswertbaren Status zurück — nie einfach leere Records. Die Klasse gehört maschinenlesbar in den Status, nicht nur in den Meldungstext: Wer bloss einen Satz bekommt, kann «später nochmal» nicht von «so nie» unterscheiden.

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

## Schritt 4: Übergabe an `github-repo`-Skill [Übergabe]

Nach Abschluss der Probe (Schritt 1-3) erfolgt die Repo-Erstellung via [`github-repo`](../github-repo/SKILL.md)-Skill. Als Input dafür bereitstellen:

1. **Repo-Name** (Pattern: `{quelle}-mcp`, z. B. `lobbywatch-mcp`)
2. **Repo-Description** (max. 100 Zeichen, Stil-parallel zu `parlament-mcp`):
   - Template: `MCP server for the {Quelle}.{xyz} — {Domäne in einem Satz}`
3. **Topics/Tags** (5–8): immer `mcp`, `model-context-protocol`, `llm`, `python`, `swiss-open-data` + domänenspezifische
4. **Befund-Tabelle** aus Schritt 1.3 → gehört ins README unter «Known limitations» falls nicht alle Endpoints funktionieren
5. **Abdeckungs-Matrix** aus Schritt 1.3b → ins README unter «Scope» bzw. «Known limitations»; sie ist die Quelle für jede spätere Scope-Begründung
6. **Architektur-Entscheid** aus Schritt 2.3 → ins README
7. **Anchor Demo Query** aus Schritt 3.3 → prominent ins README
8. **Spec-Ziel** aus Schritt 2.4 → in denselben README-Abschnitt wie der Architektur-Entscheid, samt Begründung bei Abweichung vom Standard
9. **`ttlMs`/`cacheScope`-Empfehlung** aus Schritt 1.7 → in die Konsequenzen des Entscheids und in den Code, der die List-Responses baut

---

## Schritt 5: Portfolio-Register nachführen [Übergabe]

Nach Release (Tag `v0.1.0`) wird der Server im Portfolio-Register eingetragen. Das Register hat zwei Hälften, und nur eine davon ist normativ.

### 5.1 `portfolio.json` — die normative Hälfte

Liegt im Index-Repo `swiss-public-data-mcp`, maschinenlesbar und versioniert:

| Feld | Inhalt |
|---|---|
| `name` | Repo-Name nach dem Muster `{quelle}-mcp` |
| `cluster` | Transport / Environment / Legal / Statistics / Education / Economics / Culture / Health / Registers / Parliament |
| `status` | Phase 1 / Phase 2 / Phase 3 / Deprecated |
| `mcp_spec_version` | Spec-Ziel aus 2.4, Standard `2026-07-28` |
| `sdk_flavour`, `sdk_constraint` | erhobene SDK-Lage, samt Pin, falls er das Spec-Ziel bestimmt |
| `migration_wave`, `migration_status` | auch bei einem neuen Server gesetzt — ein leeres Feld liest sich in jeder Auswertung wie «noch nicht migriert» |
| `pypi_package` | Paketname, oder leer, wenn kein Release vorgesehen ist |
| `requires_credentials` | bei Phase-1-Servern `false`; steht dort `true`, ist Anti-Pattern 6 zu prüfen |

**Warum diese Hälfte normativ ist:** Sie liegt im Repo, also im Diff, im Review und in der CI. Ein Feld, das jemand still ändert, ist ein Commit. Ein Feld, das fehlt, ist ein roter Check. Und sie braucht kein Konto bei niemandem — wer dieses Vorgehen ausserhalb dieses Portfolios anwendet, übernimmt sie unverändert.

### 5.2 Die menschenlesbare Hälfte — Darstellung, frei wählbar

Dieses Portfolio führt zusätzlich eine Karte in der Notion-Datenbank `aa6b672a-e5e3-4608-b4e4-b380dc735b9e`, mit Name, Cluster, Status, Datenquelle-URL, Lizenz (CC BY 4.0 / CC BY-SA 4.0 / OGD-CH / proprietary), Anchor Demo Query, Architektur (A / B / C), Spec-Ziel, GitHub-URL, PyPI-Status und Notizen zu Known Limitations.

**Notion ist dabei eine Wahl und keine Anforderung.** Gleichwertig, je nach Werkzeuglage:

| Variante | Wofür sie taugt | Was sie kostet |
|---|---|---|
| Notion-Datenbank | Ansichten, Filter, Kommentare, Zugriff für Nicht-Techniker | Konto und Vendor-Bindung, und der Inhalt steht in keinem Diff |
| generierte Markdown-Tabelle im README des Index-Repos | öffentlich lesbar, im Diff, kein zusätzliches Werkzeug | keine Ansichten, keine Filter |
| GitHub Issues oder Projects, ein Label pro Cluster | Diskussion am Objekt, Benachrichtigungen inklusive | jenseits von ein paar Dutzend Servern unübersichtlich |
| gar keine zweite Hälfte | bei wenigen Servern völlig ausreichend | ab etwa zehn Servern fehlt der Überblick, den 2.2 voraussetzt |

**Die Regel, die für alle Varianten gilt:** genau eine normative Quelle, und das ist `portfolio.json`. Jede Darstellung wird daraus abgeleitet, im Idealfall generiert, und nie parallel gepflegt. Zwei von Hand gepflegte Register driften, und ein gedriftetes Register ist schlechter als gar keines: Es beantwortet die Frage «welche Server stehen noch auf der alten Spec?» falsch, statt sie offen zu lassen. Dieselbe Überlegung wie bei den Checks dieses Repos, wo die CI `scripts/validate.sh` aufruft, statt die Prüfungen ein zweites Mal hinzuschreiben.

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
- Ein ganzer Bestandsteil wird von keinem geplanten Tool berührt und fällt deshalb nirgends auf → nur 1.3b fängt das ab
- Die Quelle liefert erst ab einer kürzeren Präfixlänge Treffer, als jede geschätzte Staffel erreicht → nur 1.5 fängt das ab
- Die Quelle aktualisiert nachts um 05:30, der Server verspricht seinen Clients 24 Stunden Haltbarkeit → nur 1.7 fängt das ab

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

**Immer beide:** `stdio` (Claude Desktop) + `streamable-http` (Cloud, Railway, Render). Legacy HTTP+SSE steht im 12-Monats-Fenster und ist für einen neuen Server kein Ziel mehr (2.4); unter Streamable HTTP sind `Mcp-Method` und `Mcp-Name` Pflicht-Header. Was die Transportwahl für den Cache bedeutet, steht in 2.3, was sie für die zugesagte Haltbarkeit bedeutet, in 1.7. Die Umsetzung im Einstiegspunkt und das Abweis-Verhalten gehören in `mcp-transport-hardening`.

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
9. **«Meine Probe fand nichts, also hat die Quelle nichts»** — erst wenn die Antwortstruktur bestätigt ist. Eine falsch gelesene Verschachtelung liefert dieselbe leere Liste wie ein echter Nullbefund, nur ohne Fehler. Siehe 1.2c.
10. **«Ein Endpoint reicht»** — aggregierte Endpoints hinken hinter den autoritativen her. Welcher befragt wurde, gehört ins Protokoll. Siehe 1.2c.
11. **«Was wir nicht abdecken, ist offensichtlich»** — beim Bauen ja, beim Begründen nicht mehr. Wer den Scope erst im Audit begründet, rekonstruiert ihn und erfindet dabei Gründe, die die Quelle kleiner machen, als sie ist. Die Abdeckungs-Matrix wird geprobt, nicht erinnert. Siehe 1.3b.
12. **«Die Staffel ist eine Formel»** — 30 % pro Schritt ist eine Annahme über die Matching-Granularität der Quelle, kein Messwert. Ab welcher Präfixlänge Treffer kommen, sagt nur die Quelle, und sie sagt es für ein paar Calls. Siehe 1.5.
13. **«Die Spec-Version ergibt sich aus dem SDK»** — sie ergibt sich aus einem Entscheid, den jemand trifft und begründet. Das SDK ist eine Randbedingung, kein Entscheider: Ein Pin, der `mcp` unterhalb 2.0 hält, ist ein Abweichungsgrund, den man aufschreibt — kein Zustand, in den man hineinrutscht und der später niemandem gehört. Siehe 2.4.
14. **«Die Feldnamen stehen in der Doku»** — sie stehen auf der Leitung, und die Doku hinkt hinterher. Ein Wechsel von `Schulgemeinde` auf `schulgemeinde` legte vier von sechs Datensätzen lahm, während alle Unit-Tests grün blieben: Ihre handgeschriebenen Fixtures pinnten die alte Schreibweise. Ein Fixture wird aufgezeichnet, nicht getippt. Siehe 1.2d.
15. **«`ttlMs` schätze ich»** — dieselbe Fehlerklasse wie die geratene Staffel, eine Ebene höher. Zu lang, und der Cache verschweigt einen ganzen Zyklus, ohne dass irgendwo ein Fehler auftaucht; zu kurz, und er greift nie, während der Verkehr bleibt. Weglassen ist keine dritte Möglichkeit: Das Feld ist in `CacheableResult` nicht optional, die Wahl steht also nur zwischen gemessen und geraten. Der Rhythmus der Quelle ist messbar, und zwar bevor gebaut wird. Siehe 1.7.

---

## Qualitätschecklist vor Release

Vor `v0.1.0`-Tag alle folgenden Punkte abhaken:

**Schritt 1 – Live-Probe**
- [ ] Alle Endpoints mit 5 Probe-Calls getestet (inkl. Scope-Probe)
- [ ] Befund-Tabelle im PR / README vorhanden
- [ ] **Default-Matrix**: jeder optionale Parameter geprüft, Recall-Delta gemessen (1.2b)
- [ ] **Struktur-Assertion**: jede Null in der Befund-Tabelle ist als echter Nullbefund bestätigt, nicht als ungeprüfte Leermenge (1.2c)
- [ ] Bei mehreren Wegen zur selben Information: der befragte Endpoint ist protokolliert und autoritativ (1.2c)
- [ ] **Feldnamen-Inventar**: tatsächliche Feld-/Spaltennamen samt Schreibweise protokolliert, Rohantwort als aufgezeichnete Fixture abgelegt (1.2d)
- [ ] **Abdeckungs-Matrix**: Bestandsachse aus der Quelle enumeriert, jede nicht erreichbare Zeile trägt einen der drei zulässigen Gründe (1.3b)
- [ ] Homepage-Zahlen vs. API-Zahlen verglichen
- [ ] **Recall-Ground-Truth**: 3–5 Referenzbegriffe gegen das offizielle Web-UI, jedes Delta erklärt (1.4b)
- [ ] **Widening-Schedule**: kürzestes Treffer-Präfix pro Testbegriff gemessen, Wildcard-Alternative geprüft (1.5)
- [ ] Dump-Verfügbarkeit geprüft
- [ ] **Aktualisierungsrhythmus**: über mindestens zwei erwartete Zyklen gemessen, nicht nur der Doku entnommen (1.7)
- [ ] **`ttlMs`/`cacheScope`-Paar** je Response-Familie abgeleitet und begründet, Karenz aus der Messreihe statt gerundet (1.7)
- [ ] Reihenfolge der List-Responses deterministisch — upstream garantiert oder serverseitig sortiert, Sortierschlüssel im Protokoll (1.7)

**Schritt 2 – Architektur**
- [ ] Architektur-Entscheid (A/B/C) explizit getroffen
- [ ] Portfolio-Synergie-Check durchgeführt
- [ ] Entscheid im README dokumentiert
- [ ] **Scope-Absatz** im Entscheid, mit den Zahlen aus der Abdeckungs-Matrix statt aus dem Gedächtnis (2.3)
- [ ] **Transport**: beide unterstützt, und bei ARCH B/C die Cache-Lebensdauer pro Transport im Entscheid benannt (2.3)
- [ ] **Spec-Ziel** explizit entschieden; Standard `2026-07-28`, jede Abweichung mit einem der zwei zulässigen Gründe (2.4)
- [ ] Kein deprecated Baustein im Entwurf — Roots, Sampling, Logging, Legacy HTTP+SSE (2.4)
- [ ] Zugesagtes `ttlMs` nie kürzer als die interne Cache-TTL des Servers (1.7, 2.3)
- [ ] **`portfolio.json`** im Index-Repo trägt `mcp_spec_version` samt SDK- und Wellenfeldern (2.4)

**Schritt 3 – Resilienz**
- [ ] Retry mit exponentiellem Backoff für alle HTTP
- [ ] Pydantic-Envelope mit `source` + `provenance` in jeder Response
- [ ] Anchor Demo Query im README prominent
- [ ] Tests für Happy / Retry / Timeout
- [ ] **Recall-Canary** als `@pytest.mark.live`-Test mit Untergrenzen (1.4c)
- [ ] **Widening-Boden**: gemessene unterste Stufe als Kommentar am Code und als Live-Test, nicht als runde Zahl (1.5)
- [ ] Graceful-Degradation-Pfad
- [ ] **Leermenge trägt `hint`**, keine Tool-Description erklärt oder entschuldigt ein leeres Resultat (3.6)
- [ ] **Query-Syntax** (Lucene/CQL/SQL) samt Matching-Granularität in der Tool-Description, nicht nur im README

**Schritt 4 – Repo**
- [ ] Repo-Description parallel zu anderen Portfolio-Servern
- [ ] Topics / Tags gesetzt
- [ ] README bilingual (EN + DE, Schweizer Rechtschreibung)
- [ ] CI grün (`pytest -m "not live"` + ruff)

**Schritt 5 – Portfolio**
- [ ] `portfolio.json` im Index-Repo nachgeführt, alle Felder gesetzt (5.1)
- [ ] Menschenlesbare Darstellung nachgeführt oder bewusst weggelassen — aus `portfolio.json` abgeleitet, nicht parallel gepflegt (5.2)
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

### Fundstück: die geratene Staffel (2026-08)

Ein Tool kürzte bei null Treffern den Suchbegriff um jeweils 30 % und gab bei acht Zeichen auf. Für `Betonsanierungsarbeiten` war die letzte Stufe `Betonsan`, Treffer begannen bei `Beton`. Die Staffel stoppte drei Zeichen vor dem ersten Begriff, der funktioniert hätte, und meldete «nichts gefunden».

Zwei Dinge daran sind übertragbar:

1. **Der Prozentsatz war nicht ungenau, sondern die falsche Grösse.** Was die Quelle findet, hängt an Morphemgrenzen und Index-Granularität, nicht an der Länge der Eingabe. Eine relative Staffel trifft eine Morphemgrenze nur zufällig — und bei längeren Komposita immer seltener, weil ihre Schritte mitwachsen.
2. **Die Messung kostete weniger als die Annahme.** Zwanzig Präfixe eines Begriffs sind zwanzig Calls an einer API, an der man ohnehin hängt. Der geratene Wert kostete einen stillen Recall-Verlust, der wie eine Eigenschaft des Bestands aussah.

**Metapher:** *«Eine Prozentstaffel ist ein Dietrich, der nach Gefühl gefeilt wurde — er passt in jedes Schloss ausser in das, vor dem man steht.»*

Kodifiziert in 1.5.

**Querverweis:** Als Audit-Checks kodifiziert in `mcp-audit` unter `FID-001` bis `FID-005`. Wer diesen Skill korrekt anwendet, besteht sie; wer sie beim Audit reisst, findet hier das Vorgehen zur Behebung.

---

## Verwandte Skills

Fünf Repos, ein Lebenszyklus — gemeinsames GitHub-Topic [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain). Dieser Skill kommt zuerst.

| Phase | Repo | Frage, die es beantwortet |
|---|---|---|
| vor dem Bau | **`mcp-data-source-probe`** | **Dieser Skill:** taugt die Quelle, und was hat sie? |
| im Bau | [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill) | Liefert er, was die Quelle hat? Sechs Regeln für den Abfrage-Code; als Audit-Checks `FID-001`–`FID-005`. Wurde hier unter `companion/` ausgeliefert, bis er ein eigenes Repo bekam |
| im Bau | [`mcp-transport-hardening`](https://github.com/malkreide/mcp-transport-hardening-skill) | Kommt er hoch, weist er richtig ab? Die Umsetzung im Einstiegspunkt und das Abweis-Verhalten (siehe «Welchen Transport-Modus unterstützen?») |
| nach dem Bau | [`mcp-audit`](https://github.com/malkreide/mcp-audit-skill) | Hält er gegen den Katalog? |
| im Betrieb | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Hält er morgen noch? Die Recall-Ground-Truth aus 1.4, laufend statt einmalig gemessen |

Daneben, nicht Teil der Kette: `mcp-builder` — generische Bauanleitung von Anthropic, wird ergänzt und nicht ersetzt. Fremdes Repo, kann das Topic nicht tragen.
