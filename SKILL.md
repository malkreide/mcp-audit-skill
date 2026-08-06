---
name: mcp-data-fidelity
description: Datentreue-Regeln für MCP-Server-Tools, die eine externe Datenquelle abfragen — damit ein Server nicht still unvollständig liefert. Verwende diesen Skill ergänzend zu mcp-builder immer wenn (1) ein Such-, Query- oder Filter-Tool für einen MCP-Server entworfen oder implementiert wird, (2) eine Tool-Description dafür geschrieben oder überarbeitet wird, (3) jemand meldet, ein Server finde nichts, zu wenig oder weniger als die offizielle Oberfläche («findet nichts», «leeres Ergebnis», «Web-UI zeigt mehr», «zu wenig Treffer», «Recall», «Scope»), (4) ein Modell auf ein leeres Tool-Result hin eine Antwort erfunden hat oder ein Fuzzy-/Vorschlags-Fallback entworfen wird, (5) optionale API-Parameter (Filter, Facetten, Feld-Flags, Limits) in Requests übersetzt werden, (6) Tests dafür geschrieben werden, oder (7) ein Server auf MCP-Spec 2026-07-28 migriert wird und dabei Sortierreihenfolge, `ttlMs`/`cacheScope` oder MRTR-Rückfragen (`input_required`) festgelegt werden. Nicht nötig für Server ohne externe Datenquelle.
---

# MCP Data Fidelity — liefert der Server, was die Quelle hat?

Companion zu `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **liefert er, was die Quelle tatsächlich hat?**

Das ist eine eigene Fehlerklasse, weil sie still ist. HTTP 200, wohlgeformtes JSON, grüne Tests — und inhaltlich falsch. Ein Server, der zwei Prozent des Bestands durchsucht und das nicht meldet, produziert Antworten, die niemand als falsch erkennt.

**Die Leitfrage bei jedem datenabfragenden Tool:** *Wenn dieses Tool nichts findet — kann ich unterscheiden, ob es nichts gibt oder ob ich falsch gefragt habe?* Ist die Antwort nein, greift eine der zehn Regeln unten.

Seit Regel 10 steht die Stufe darunter daneben: *und wenn ich falsch gefragt habe — komme ich von hier zur richtigen Frage?* Die erste Frage entscheidet, ob das Modell schweigen darf. Die zweite, ob es weiterkommt, ohne sich einen Treffer zu erfinden.

Die Regeln 1–6 und 10 stammen aus Vorfällen, die Regeln 7–9 aus der Spec 2026-07-28. Der Unterschied ist ausgewiesen und nicht kosmetisch — siehe den Abschnitt vor Regel 7. Die Nummerierung folgt der Reihenfolge, in der die Regeln dazugekommen sind, nicht dieser Gruppierung.

---

## Regel 1 — Scope-Parameter explizit senden, nie erben

Ein optionaler Filter-Parameter bedeutet beim Weglassen oft **nicht** «unbeschränkt», sondern einen willkürlichen Teilausschnitt. Diese Tatsache steht ausschliesslich in der **Parameterbeschreibung** der Spec — nicht im Response-Schema, nicht im Doku-Beispiel, und an einem funktionierenden Call ist sie nicht erkennbar.

Verbreitete Vertreter:

| Quelle | Parameter | Default bei Weglassen |
|---|---|---|
| CKAN `package_search` | `rows` | 10 Treffer |
| WFS `GetFeature` | `count` / `maxFeatures` | serverseitiges Limit |
| SPARQL | `FROM` / Named Graphs | nur Default-Graph |
| Elasticsearch / Solr | `size`, `fq`, `df` | 10 Hits, eingeschränktes Default-Feld |
| GraphQL (Relay) | `first` | schema-abhängig, oft klein |
| TERMDAT `/v2/Search` | `ClassificationIds` | 1 von 23 Sachgebieten |

```python
# ✗ Der Parameter geht nur raus, wenn der Aufrufer ihn kennt.
if classification_ids:
    params["ClassificationIds"] = classification_ids

# ✓ Kein Filter vom Aufrufer → voller Scope, explizit gesendet.
if classification_ids is None:
    classification_ids = await self._all_classification_ids()
if classification_ids:
    params["ClassificationIds"] = classification_ids
```

Muss der volle Scope zur Laufzeit ermittelt werden (Vokabular-Endpoint), dann **best-effort**: Fällt die Ermittlung aus, läuft die Suche unerweitert weiter. Eine Erweiterung darf nie brechen, was sie erweitert.

**Nachweis:** Zwei Calls, exakt eine Variable geändert — Parameter weggelassen vs. explizit maximal. Delta ≠ 0 heisst, der Server muss ihn senden.

**Wer den Recall verengt, zitiert den Scope.** Eine bewusste Verengung — exakt statt Wildcard, kein Fuzzy-Matching, kein Prefix — wird fast immer mit einem Risiko begründet: Eine falsche Zuordnung wäre *hier* besonders teuer. Das Argument trägt nur, wenn die Datenklasse, die das Risiko trägt, über diesen Server überhaupt erreichbar ist.

Fallgeschichte (2026-08, im Entwurf gefangen, nicht ausgeliefert): Exakt-only wurde mit dem Schaden falsch zugeordneter **Konkursmeldungen** begründet — einer Rubrik, die der Server gar nicht bedient. Die Begründung klang zwingend und war an nichts gekoppelt; sie hätte wortgleich für jede beliebige Quelle dagestanden, und genau das ist ihr Erkennungsmerkmal. Es ist die vorformulierte Ausrede aus Regel 4, eine Stufe früher: Regel 4 fängt sie dort, wo das Modell sie liest, hier wird sie dort gefangen, wo jemand sie schreibt.

**Prüffrage, zwei Teile:** *Nenne die Rubriken oder Datenklassen, die das Risiko tragen — und weise nach, dass sie erreichbar sind.* Der Nachweis ist derselbe wie oben: die Aufzählung des vollen Scopes, gegen die diese Regel ohnehin misst. Steht die Klasse nicht darin, fällt die Begründung. Die Verengung kann trotzdem richtig sein — aber sie muss aus dem neu begründet werden, was tatsächlich in Reichweite liegt. Ist die riskante Klasse erreichbar, gilt die Umkehrung: Dann ist Exakt-only richtig (die Ausnahme für sensible Daten in `ARCH-003`), und die Klasse gehört namentlich in die Tool-Description — sonst liest das Modell die Verengung als Lücke und rät sich darüber hinweg.

## Regel 2 — Parameter-Gruppen vollständig senden

Sendet man von einer zusammengehörigen Gruppe (`Field.*`, `include_*`, Facetten-Schalter) nur einige Mitglieder, behalten die übrigen ihren **serverseitigen Default**. Das Argument kann dann nur erweitern, nie einschränken — ein No-op, der wie Steuerung aussieht.

```python
# ✗ Nicht gesendete Flags bleiben upstream auf true → `fields` wirkt nicht.
for field in fields:
    params[f"Field.{field}"] = "true"

# ✓ Jedes Mitglied explizit — erst dadurch kann `fields` verengen.
requested = set(fields)
for field in SEARCH_FIELDS:
    params[f"Field.{field}"] = "true" if field in requested else "false"
```

**Nachweis:** Ein Call mit explizitem `false` für ein Default-true-Flag muss weniger liefern. Tut er das nicht, geht die Gruppe unvollständig raus.

## Regel 3 — Leermenge trägt einen nächsten Schritt

Ein leeres Result ist mehrdeutig: Begriff existiert nicht / Query zu eng / Scope eingeschränkt / Syntax passte nicht. Das Modell muss raten.

```python
_EMPTY_HINT = (
    "No entry matched. `search_term` is Lucene syntax: try a prefix wildcard "
    "(e.g. 'Quellensteuer*') to catch compounds, or the fuzzy operator ('~'). "
    "Widen `fields`. Only then conclude the term is absent — and never "
    "substitute a guess for the official designation."
)

class SearchResult(BaseModel):
    returned: int
    hint: str | None = None    # gesetzt, wenn returned == 0
    entries: list[TermEntry]
```

Der Hinweis muss **konkret** sein. «Versuchen Sie eine andere Suche» ist kein nächster Schritt. Und er gehört ins Tool-Result, nicht ins README — das wird nicht an das Modell weitergereicht. Wie konkret er werden darf, ohne selbst zum Treffer zu werden, steht in Regel 10: vorschlagen ja, abfragen nein.

**Abgrenzung:** Ein Transport- oder Autorisierungsfehler ist keine Leermenge und darf nie als solche formatiert werden. Ein abgewiesener Request — HTTP 421 auf einen fremden Host-Header, 401, 403, ein Verbindungsabbruch — erreicht die Quelle nie und kommt bei der aufrufenden Schicht trotzdem als «Fehlschlag ohne Daten» an; wer nur auf «keine Datensätze» prüft, reicht ihn als Leermenge durch. Er trägt aber einen anderen nächsten Schritt: **Konfiguration prüfen, nicht Suche verbreitern.** Ein Hinweis, der zur Wildcard rät, während die Abfrage gar nicht angekommen ist, schickt das Modell in die falsche Richtung — und ein Konfigurationsfehler unterläuft genau die Regel, die das Raten verhindern soll. Solche Fälle gehören mit `isError` in den Fehlerkanal, wie die Strukturabweichung in Regel 6.

Eine dritte Tür hat die Spec 2026-07-28 aufgemacht: die MRTR-Rückfrage. Sie sieht erfolgreich aus und ist trotzdem keine Leermenge — Regel 9.

## Regel 4 — Die Tool-Description ist eine Halluzinations-Oberfläche

Die schwerste der sieben incident-belegten Regeln, weil sie kontraintuitiv ist: **Eine Formulierung, die eine Leermenge erklärt, erzeugt Konfabulation zuverlässiger als gar keine Formulierung.**

Realer Fall (`termdat-mcp`, 2026-07). Die Description enthielt:

> *«Scope caveat: an empty result usually means the term is out of scope, not that it is wrong.»*

Als Ehrlichkeit gemeint. Faktisch eine vorformulierte Ausrede für das eigene Schweigen. Das Modell hat sie genommen und eine plausible, vollständig erfundene Erklärung geliefert — für einen Begriff, der die ganze Zeit in der Datenbank stand. Es hat nicht halluziniert, weil es schlecht war, sondern weil das Werkzeug ihm eine Erklärung mitgab und keinen nächsten Schritt.

```python
# ✗ lizenziert eine Schlussfolgerung
"""An empty result usually means the term is out of scope, not that it is wrong."""

# ✓ fordert zum Nachfassen auf und schliesst das Raten aus
"""Scope caveat: the source holds administrative nomenclature, so a term may
genuinely be absent. Establish that with a wildcard retry, not from a single
empty result, and never fill the gap with a guessed designation."""
```

Faustregel: Jeder Satz in einer Tool-Description, der mit «usually means», «likely», «wahrscheinlich» oder «bedeutet meist» anfängt und ein leeres Resultat deutet, gehört gestrichen oder in eine Handlungsanweisung umgeschrieben.

Ein `not_found`-Verdikt (QA-/Check-Tools) heisst «nicht in dieser Quelle», nie «falsch». Der Server masst sich sonst eine Aussage an, die die Datenlage nicht trägt.

## Regel 5 — Query-Syntax in die Description, Recall in die Tests

**Syntax.** Spricht ein Such-Argument eine eigene Abfragesprache (Lucene, CQL, SQL-Fragmente, Regex, Glob), gehört sie in die Tool-Description. Zwingend dazu die **Matching-Granularität**: Die meisten Volltextindizes matchen auf ganzen Wörtern, womit deutsche Komposita von ihren Bestandteilen nicht gefunden werden.

```python
"""Search the terminology database for official designations.

`search_term` is **Lucene query syntax**: `*` and `?` wildcards and the `~` fuzzy
operator work. Matching is on whole words, so a compound is not found by its
parts — «Quellensteuer» does not match «Quellensteuerverordnung», but
«Quellensteuer*» does. Reach for a wildcard before concluding a term is absent.
"""
```

Wildcards serverseitig automatisch anhängen ist **kein** Ersatz — es macht Phrasensuche unmöglich und verschiebt das Problem.

**Recall.** Mocks bilden die eigene Annahme ab. Ist die Annahme falsch, ist der Mock falsch, und der Test bestätigt den Fehler, statt ihn zu finden. Scope- und Recall-Bugs sind für Mocks strukturell unsichtbar.

Dieselbe Fehlerform tritt auch ohne Mock auf: In `mcp-transport-hardening` setzte ein Regressionstest die Umgebungsvariable, deren *Fehlen* der eigentliche Prüfgegenstand war — und bestand deshalb auch mit absichtlich eingebautem Fehler. **Ein Test, der die Bedingung herstellt, unter der der Fehler nicht auftreten kann, prüft nichts.**

```python
@pytest.mark.live
async def test_recall_floor():
    """Recall-Canary: fängt Scope-Regressionen und Upstream-Default-Änderungen."""
    for term, floor in [("Pensionskasse", 10), ("Quellensteuer", 1)]:
        entries, _ = await client.search(term, max_results=100)
        assert len(entries) >= floor, f"{term}: {len(entries)} < {floor} — Scope geschrumpft?"
```

Untergrenzen, keine exakten Zahlen — grosszügig unter dem Ist-Wert, Faustregel Hälfte. Der Test soll einen Kollaps von 21 auf 1 fangen, nicht bei jeder Bestandspflege rot werden. Ein Test, der ständig falsch anschlägt, wird abgeschaltet und fängt dann gar nichts mehr.

---

## Regel 6 — Die Antwort auf Struktur prüfen, nicht durchgreifen

Die Regeln 1–5 betreffen, was der Server **sendet** und was er dem Modell **sagt**. Es gibt eine dritte Stelle mit derselben Fehlerklasse: was er **liest**.

Eine falsch angenommene Verschachtelung liefert exakt dieselbe leere Liste wie ein echter Nullbefund — ohne Exception, ohne Status-Code, ohne Log-Eintrag. Aus Sicht des Modells ist das nicht von «die Quelle kennt das nicht» zu unterscheiden, und damit ist es dieselbe Konfabulations-Einladung wie Regel 3.

Belegfall (2026-07): Eine Abfrage der MCP Registry lieferte konsequent nichts. Die Felder liegen unter `servers[].server.*`, gesucht wurde eine Ebene höher. Der Code war syntaktisch einwandfrei und semantisch blind.

```python
# ✗ greift durch die Struktur hindurch — jede Änderung upstream wird zur Leermenge
rows = payload.get("servers", [])
names = [r.get("name", "") for r in rows]     # bleibt leer, wenn name eine Ebene tiefer liegt

# ✓ Struktur bestätigen, bevor gezählt wird
rows = payload.get("servers")
if rows is None:
    raise UpstreamSchemaError(
        f"Antwort ohne 'servers'. Vorhandene Schlüssel: {sorted(payload)[:10]}"
    )
if rows and "name" not in rows[0]:
    raise UpstreamSchemaError(
        f"Zeile ohne 'name'. Struktur: {json.dumps(rows[0])[:200]}"
    )
```

Der Unterschied liegt in der Behandlung des **unerwarteten** Falls: `.get(x, [])` macht aus einer Strukturänderung stillschweigend ein gültiges leeres Ergebnis. Ein Schema-Fehler ist aber ein Fehler und gehört als solcher gemeldet — laut, mit `isError`, wie jeder andere Upstream-Defekt. Eine Leermenge nach Regel 3 ist etwas anderes: dort war die Abfrage korrekt und die Quelle hat nichts.

**Abgrenzung:** Das ist keine vollständige Schema-Validierung. Geprüft wird nur, was der Code tatsächlich anfasst — die Hülle und die gelesenen Felder. Alles darüber hinaus ist Aufwand ohne Ertrag und bricht bei jeder harmlosen Erweiterung upstream.

**Warum Mocks das nicht fangen:** aus demselben Grund wie bei Regel 5. Der Mock bildet die angenommene Struktur ab. Ist die Annahme falsch, ist der Mock falsch. Diese Klasse fällt nur gegen die echte Antwort auf — im Live-Test oder in der Probe (siehe `mcp-data-source-probe`, Abschnitt 1.2c).

---

## Regeln aus der Spec 2026-07-28 — belegt durch den Mechanismus, nicht durch einen Schaden

Die Regeln 1–6 stehen hier, weil etwas kaputtgegangen ist: eine Suche über 1 von 23 Klassifikationen, eine Registry-Abfrage eine Ebene daneben. Regel 10 steht hinter diesem Abschnitt und gehört trotzdem zur ersten Gruppe — sie ist später dazugekommen, nicht anders belegt. Für die Regeln 7–9 gilt das nicht, und das gehört gesagt, statt sie stillschweigend danebenzustellen. Ihr Beleg ist der **Mechanismus**: Die Spec 2026-07-28 hat drei Felder eingeführt oder abgeschafft, aus denen sich dieselbe stille Unvollständigkeit ableiten lässt wie aus einem vergessenen Filter — nachrechenbar, aber noch nicht nachgemessen. Fällt einer der drei in freier Wildbahn auf, gehört der Vorfall hierher; bis dahin sind es Regeln mit Herleitung statt mit Narbe.

Das Contributing-Kriterium dieses Repos bleibt davon unberührt: Ein **Vorschlag** von aussen braucht weiterhin einen eingetretenen Schaden. Was hier über die tiefere Latte kommt, ist eine Protokolländerung, die alle 42 Server des Portfolios gleichzeitig betrifft — nicht eine plausible Empfehlung.

**Geltungsbereich.** Regel 7 gilt unabhängig von der Spec-Version; instabile Sortierung zerlegt Pagination auch auf 2025-06-18. Dasselbe gilt für Regel 10 und für alles vor Regel 7. Die Regeln 8 und 9 setzen 2026-07-28 voraus — `ttlMs`/`cacheScope` auf den List-Responses und MRTR (`resultType: "input_required"`) existieren vorher nicht. Wer einen Server der Wave D oder ein eingefrorenes Repo prüft, hakt sie als nicht anwendbar ab, statt sie zu erfüllen.

## Regel 7 — Deterministische Reihenfolge, dokumentiert

`tools/list`, `prompts/list`, `resources/list` und jedes Query-Resultat gehen in einer **stabilen, dokumentierten** Sortierung raus. Die Spec verlangt deterministische Reihenfolge, aber der Grund steht nicht dort: Sie hat `initialize`/`initialized` und `Mcp-Session-Id` abgeschafft. Jede Anfrage steht für sich, Reconnect ist der Normalfall statt der Ausnahme — und jede neu sortierte `tools/list` invalidiert den Prompt-Cache des Clients bei unverändertem Server. Nicht falsch, nur teuer, und niemand sieht warum.

Die scharfe Ausprägung liegt eine Ebene tiefer, und dort ist sie Datentreue: **Bei instabiler Sortierung über Seitengrenzen hinweg verliert Pagination Treffer.** Ein Datensatz, der zwischen dem Abruf von Seite 1 und Seite 2 die Position wechselt, erscheint zweimal oder gar nicht. Das ist stille Unvollständigkeit derselben Klasse wie Regel 1 — nur entstanden beim Blättern statt beim Filtern, und im Gegensatz zum Filter-Fall auch bei korrekt gesendeten Parametern.

Ein Relevanz-Score allein ist keine Ordnung. Er hat Ties, und was bei Ties passiert, entscheidet der Sortieralgorithmus der Quelle — nicht selten der Zufall der Shard-Verteilung.

```python
# ✗ Ties fallen beliebig — zwei identische Abfragen, zwei Reihenfolgen.
rows.sort(key=lambda r: -r["score"])

# ✓ Eindeutiger Schlüssel als letztes Glied: die Ordnung ist total.
rows.sort(key=lambda r: (-r["score"], r["id"]))
```

Dasselbe gilt für die Tool-Registry selbst: Eine Liste im Quelltext ist stabil, ein `set`, ein Verzeichnis-Glob oder ein über mehrere Module eingesammeltes Dict sind es nicht. Und wenn sortiert wird, gehört der Schlüssel in die Tool-Description **und** in den Envelope (`sort_key`) — eine Reihenfolge, die man nicht benennen kann, ist keine, auf die sich jemand stützen darf.

**Nachweis / Test (respx offline).** Der Mock muss permutieren, sonst prüft der Test die eigene Fixture:

```python
@respx.mock
async def test_order_survives_upstream_permutation():
    """Regel 7: Der Server sortiert, nicht die Quelle."""
    payloads = itertools.cycle([_PAGE, _permuted(_PAGE)])   # gleiche Menge, andere Ordnung
    respx.get(SEARCH_URL).mock(
        side_effect=lambda _req: httpx.Response(200, json=next(payloads))
    )
    first = await client.search("Steuer")
    second = await client.search("Steuer")
    assert [e["id"] for e in first] == [e["id"] for e in second]
```

Zweimal dieselbe Reihenfolge zu mocken und dann Gleichheit zu behaupten, ist die Fehlerform aus Regel 5: Der Test stellt die Bedingung her, unter der der Fehler nicht auftreten kann.

**`@pytest.mark.live`.** Zwei identische Calls gegen die echte Quelle, plus der Pagination-Schnitt — den fängt kein Offline-Test, weil er von der Seitenaufteilung der Quelle abhängt:

```python
@pytest.mark.live
async def test_pagination_is_disjoint():
    page1 = await client.search("Steuer", offset=0, limit=50)
    page2 = await client.search("Steuer", offset=50, limit=50)
    ids1, ids2 = {e.id for e in page1.entries}, {e.id for e in page2.entries}
    assert not ids1 & ids2, f"{len(ids1 & ids2)} Treffer doppelt — Ordnung nicht total"
    assert len(ids1 | ids2) == len(page1.entries) + len(page2.entries)
```

## Regel 8 — Ehrliches `ttlMs`

`ttlMs` auf einer List- oder Read-Response ist eine Zusage: So lange darf der Client diese Antwort weiterverwenden, ohne zu fragen. Ein `ttlMs`, das die nächste Quellen-Aktualisierung überdauert, lässt den Client eine Antwort ausliefern, von der der Server im Moment des Sendens schon weiss, dass sie überholt sein wird.

Das ist **dieselbe Klasse wie ein verlorener Filter-Parameter**. Regel 1 verliert Treffer im Raum — der Bestand, der ausserhalb des Default-Scopes liegt. Regel 8 verliert sie in der Zeit — die Datensätze, die nach dem Abruf dazugekommen sind. In beiden Fällen ist die Antwort formal einwandfrei, inhaltlich unvollständig und für den Aufrufer nicht als solche erkennbar. Ein zu grosszügiges `ttlMs` ist ausserdem schlimmer als gar keines: Ohne Angabe fragt der Client neu, mit falscher Angabe fragt er begründet nicht.

`ttlMs` wird **abgeleitet, nicht geschätzt** — aus derselben Frische-Information, die der Response-Envelope nach den Portfolio-Konventionen ohnehin führt (`source_freshness`): publizierte Update-Kadenz, `Last-Modified`, `Cache-Control` der Quelle. Ist die Kadenz unbekannt, ist das kein Argument für einen grosszügigen Wert, sondern für einen kurzen — den Boden, nicht die Null. Eine Quelle, die unangekündigt aktualisiert, hat keine lange Frische — sie hat eine unbekannte, und Nichtwissen wird konservativ aufgelöst.

**`ttlMs: 0` ist nicht die konservative Auflösung, als die es aussieht.** Es schaltet das Feld ab, statt kurz die Wahrheit zu sagen: Jeder Aufruf trifft die Quelle, und der Zweck von SEP-2549 verpufft. `ARCH-020` führt es aus genau diesem Grund als Anti-Pattern («`ttlMs: 0` als «sicherer Wert»») und verlangt einen begründeten Wert. Eine Null gehört an eine einzige Stelle: als **abgeleitetes** Ergebnis, wenn die Quelle ihre eigene Publikation bereits überschritten hat — dann ist die verbleibende Frist tatsächlich null. Das ist eine Messung, keine Wahl, und so rechnet `ttl_from_freshness` in `reference/patterns.py`.

```python
# ✗ eine Zahl, die sich sicher anfühlt und nichts über die Quelle weiss
ttl_ms = 3_600_000

# ✓ aus der gemessenen Frische, gedeckelt auf die nächste Publikation
ttl_ms = ttl_from_freshness(
    last_modified=resp.headers.get("Last-Modified"),
    cadence=timedelta(days=1),      # publizierter Rhythmus, sonst None
    now=now,
)
```

`cacheScope` gehört zur selben Entscheidung und hat schärfere Folgen. Hängt das Resultat von den Credentials des Aufrufers ab — jeder Server mit `requires_credentials: true` —, dann ist ein zu weiter `cacheScope` kein Frischeproblem mehr, sondern ein Datenleck: Antwort A wird an Aufrufer B ausgeliefert. Öffentlich cachebar ist nur, was für alle Aufrufer identisch ist.

Das Feld kennt nach SEP-2549 **genau zwei Werte**: `"public"` und `"private"`. Einen dritten, enger klingenden gibt es nicht — wer «nur für diesen einen Aufrufer» meint, schreibt `"private"`. Ein erfundener Wert ist kein vorsichtiger Wert: Er fällt an der Schema-Validierung, und bis dahin liest ihn eine Zwischeninstanz als unbekannt.

**Nachweis / Test (respx offline).** Zwei Fälle, beide mit fixierter Uhr — die Kadenz ist bekannt, also ist der Sollwert berechenbar:

```python
@respx.mock
async def test_ttl_does_not_outlive_the_next_publication():
    """Regel 8: Die Zusage endet vor der nächsten Aktualisierung, nicht danach."""
    now = datetime(2026, 8, 5, 5, 30, tzinfo=UTC)          # Publikation täglich 06:00
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(
        200, json=_PAGE, headers={"Last-Modified": "Tue, 04 Aug 2026 06:00:00 GMT"}
    ))
    result = await client.search("Steuer", now=now)
    assert 0 < result.ttl_ms <= 30 * 60 * 1000              # höchstens bis 06:00

@respx.mock
async def test_ttl_falls_back_to_the_floor_without_freshness():
    """Unbekannte Frische heisst kurz, nicht komfortabel."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_PAGE))
    result = await client.search("Steuer")
    assert result.ttl_ms <= TTL_FLOOR_MS
    assert result.cache_scope == "private"                  # nie weiter als nötig
```

**`@pytest.mark.live`.** Als Obergrenzen-Canary, gespiegelt zur Untergrenze aus Regel 5 — und aus demselben Grund grosszügig: gegen den echten Header der Quelle prüfen, nicht gegen eine erwartete Zahl.

```python
@pytest.mark.live
async def test_ttl_against_real_source_freshness():
    result = await client.search("Steuer")
    head = await client.head(SEARCH_URL)
    age = _parse_http_date(head.headers["Last-Modified"])
    assert result.ttl_ms <= _remaining_until_next_publication(age), (
        "ttlMs überdauert die nächste Publikation — Kadenz upstream geändert?"
    )
```

## Regel 9 — `input_required` ist keine leere Antwort

MRTR hat in der Spec 2026-07-28 die serverinitiierten `elicitation`/`sampling`/`roots` ersetzt: Fehlt dem Server ein Argument, antwortet er mit `resultType: "input_required"`, und der Client wiederholt den Aufruf mit `inputResponses`. Damit steht neben Leermenge und Fehler ein dritter Ausgang — und er ist der gefährlichste, weil er **erfolgreich aussieht**: HTTP 200, wohlgeformtes Result, keine Treffer darin.

Wer die Rückfrage als Leermenge formatiert, bekommt exakt die Konfabulation aus Regel 4 — diesmal über eine Frage, die der Server gestellt und niemand beantwortet hat. Die Umkehrung ist ebenso schädlich: Ein echter Null-Treffer als `input_required` verpackt schickt den Client in eine Retry-Schleife für Daten, die es nicht gibt, und der Nachschub an Argumenten ändert daran nichts.

Drei disjunkte Zustände, unterscheidbar an genau einem Feld:

| Zustand | Marker | `entries` | Träger des nächsten Schritts |
|---|---|---|---|
| Rückfrage | `resultType: "input_required"` | fehlt | `inputRequests` — welches Argument, welche zulässigen Werte |
| Null-Treffer | normales Result | `[]` | `hint` nach Regel 3 |
| Fehler | `isError` | — | Konfiguration prüfen (Regel 3, Abgrenzung) |

«Fehlt» ist wörtlich zu nehmen: Eine Rückfrage mit `entries: []` daneben ist bereits die Verwechslung. Das Feld gar nicht zu senden, ist der Unterschied zwischen «ich habe nicht gesucht» und «ich habe gesucht und nichts gefunden».

```python
# ✗ Die Rückfrage fällt in denselben Zweig wie der Nulltreffer — samt Such-Hinweis.
entries = await client.search(term, scope=scope)
if not entries:
    return build_result([], hint=_EMPTY_HINT)

# ✓ Zustand vor Menge: erst die Rückfrage, dann erst die Leermenge.
if missing := _unresolved_arguments(term=term, scope=scope):
    return InputRequired(input_requests=[_ask(name) for name in missing])
entries = await client.search(term, scope=scope)
if not entries:
    return build_result([], hint=_EMPTY_HINT)
```

Die Reihenfolge ist der ganze Punkt: Wird zuerst gesucht und danach auf Vollständigkeit der Argumente geprüft, ist die Rückfrage bereits durch die Leermengen-Behandlung gelaufen.

**Nachweis / Test (respx offline).** Drei Fälle gegen dasselbe Tool, plus die Retry-Runde — die Assertions prüfen die Trennung in beide Richtungen, nicht bloss die Existenz der Felder:

```python
@respx.mock
async def test_the_three_outcomes_stay_disjoint():
    """Regel 9: Rückfrage, Leermenge und Fehler teilen kein Feld."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_EMPTY_PAGE))

    asked = await search_tool(term="Quellensteuer")            # scope fehlt
    assert asked.result_type == "input_required"
    assert asked.input_requests and asked.entries is None
    assert asked.hint is None, "Rückfrage trägt einen Such-Hinweis — Regel 3 fehlgeleitet"

    empty = await search_tool(term="Quellensteuer", scope="VARIA")
    assert empty.result_type is None and empty.entries == []
    assert empty.hint and empty.input_requests is None, (
        "Null-Treffer als Rückfrage verpackt — der Client retryt ins Leere"
    )

@respx.mock
async def test_retry_with_input_responses_returns_data():
    """Die Rückfrage ist erst richtig, wenn die Antwort darauf Treffer liefert."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_PAGE))
    asked = await search_tool(term="Quellensteuer")
    answered = await search_tool(
        term="Quellensteuer",
        input_responses={r.name: "VARIA" for r in asked.input_requests},
    )
    assert answered.result_type is None and answered.entries
```

**`@pytest.mark.live`.** Gegen den laufenden Server, weil der Zustandsübergang nur dort vollständig ist:

```python
@pytest.mark.live
async def test_input_required_resolves_against_the_live_source():
    asked = await session.call_tool("search_terms", {"term": "Pensionskasse"})
    assert asked.result_type == "input_required"
    answered = await session.call_tool(
        "search_terms",
        {"term": "Pensionskasse", "input_responses": {"scope": "ALL"}},
    )
    assert answered.entries, "nach der beantworteten Rückfrage immer noch leer"
```

---

## Regel 10 — Vorschlagen ist nicht Erweitern

Zurück zur ersten Gruppe: Diese Regel hat wieder einen Vorfall hinter sich, keine Herleitung.

Regel 3 verlangt einen nächsten Schritt auf der Leermenge. Der naheliegende Weg, ihn konkret zu machen, ist eine **kürzere Variante des Begriffs, den der Aufrufer selbst geschickt hat** — bei deutschen Komposita die Kürzung, die Regel 5 ohnehin erklärt: `Quellensteuerverordnung` → `Quellensteuer*`. Der Schritt danach ist der, der bricht: diese Variante selbst abzufragen und ihre Treffer zurückzugeben.

**Die Sicherheitseigenschaft:** *Keine Meldung im Resultat darf einem Begriff zuzuschreiben sein, den der Aufrufer nicht gewählt hat.* Alles in `entries` beantwortet den Begriff, der reingegangen ist — und sonst nichts.

Sie lässt sich in beide Richtungen verletzen, und beide Male sieht das Ergebnis brauchbar aus:

| Verletzung | Was das Modell daraus macht |
|---|---|
| Server sucht die gekürzte Variante und mischt deren Treffer unter `entries` | «Zu *Quellensteuerverordnung* gibt es diese Meldungen» — für Meldungen, die zu einem anderen Begriff gehören |
| Server schlägt gar nichts vor | Der Aufrufer weiss, dass die Abfrage nichts ergab, aber nicht, wie er zur richtigen kommt — der Ausfall aus Regel 3 |

Der Konflikt zwischen «hilf dem Modell weiter» und «erfinde keine Treffer» wird damit nicht zugunsten einer Seite entschieden, sondern aufgeteilt: **vorschlagen ja, abfragen nein.**

```python
# ✗ Der Vorschlag wird gleich mitgesucht — die Treffer landen unter dem Begriff
#   des Aufrufers, obwohl sie einen anderen beantworten.
entries = await client.search(term)
if not entries:
    for variant in shorter_variants(term):
        entries = await client.search(variant)
        if entries:
            return build_result(entries, hint=f"Keine Treffer für {term!r}.")

# ✓ Der Vorschlag bleibt ein Vorschlag. Gesucht wird genau einmal, genau das,
#   was der Aufrufer geschickt hat.
entries = await client.search(term)
if not entries:
    return build_result(
        [],
        match_type="none",
        suggestions=shorter_variants(term),   # abgeleitet, nicht abgefragt
        hint=(
            f"Keine Meldung zu {term!r}. Volltextsuche matcht auf ganzen Wörtern; "
            "die Vorschläge unter `suggestions` sind Kürzungen deines Begriffs "
            "und ungeprüft — rufe das Tool damit erneut auf, wenn einer passt."
        ),
    )
```

Die Vorschläge werden **aus der Eingabe abgeleitet**, nicht aus einem fremden Vokabular geholt. Eine Liste «häufiger Begriffe» aus der Quelle ist ein zweiter Treffertyp mit eigenem Recall-Risiko und wieder eine Abfrage, die niemand angefordert hat.

**Abgrenzung gegen `ARCH-003`.** Der Katalog-Check verlangt auf einer Leermenge einen **Fuzzy-Match *oder* einen Vorschlagsmechanismus**, dazu ein `match_type`-Feld und einen handlungsfähigen Hinweis. Der Vorschlags-Arm erfüllt beides — den Check und diese Regel. Wer den Fuzzy-Arm nimmt, hält die Sicherheitseigenschaft nur, wenn die heuristischen Treffer in einem **eigenen Feld** stehen, mit dem Begriff, der sie erzeugt hat, und `match_type` sie als das ausweist. Verboten ist die Vermischung, nicht die Hilfe. Umgekehrt gilt die Ausnahme von `ARCH-003` weiter: Wo eine Fehlzuordnung teuer ist — Personendaten, Zugriffskontrollen —, ist «nichts gefunden» richtig, und die Begründung dafür steht unter Regel 1: die riskante Klasse nennen und zeigen, dass sie erreichbar ist.

**Nachweis / Test.** Ein **Paar**, und beide Hälften sind Pflicht:

```python
@respx.mock
async def test_empty_result_offers_variants_of_the_callers_own_term():
    """Regel 10, Hälfte 1: Der nächste Schritt ist konkret und kommt aus der Eingabe."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_EMPTY_PAGE))
    result = await search_tool(term="Quellensteuerverordnung")
    assert result.entries == [] and result.match_type == "none"
    assert result.suggestions, "Leermenge ohne Vorschlag — Regel 3 bleibt unerfüllt"
    assert all(s.rstrip("*") in "Quellensteuerverordnung" for s in result.suggestions), (
        "Vorschlag stammt nicht aus dem Begriff des Aufrufers"
    )

@respx.mock
async def test_suggestions_are_never_searched():
    """Regel 10, Hälfte 2: Vorgeschlagen wird viel, abgefragt genau eines."""
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=_EMPTY_PAGE)
    )
    result = await search_tool(term="Quellensteuerverordnung")
    assert result.suggestions
    assert route.call_count == 1, (
        f"{route.call_count} Abfragen für einen Begriff — Vorschläge wurden gesucht"
    )
    sent = route.calls[0].request.url.params["SearchTerm"]
    assert sent == "Quellensteuerverordnung", f"gesucht wurde {sent!r}"
```

Fällt eine der beiden weg, ist die andere wertlos: Ohne die erste besteht ein Server, der nie etwas vorschlägt, die zweite mühelos. Ohne die zweite besteht ein Server die erste, der jeden seiner Vorschläge sofort selbst abfragt. Das ist dieselbe Testform wie bei Regel 9 — die Trennung wird in beide Richtungen assertiert, nicht bloss die Existenz eines Feldes.

Der Zähler auf der Route ist der eigentliche Prüfgegenstand und darum bewusst offline: Er misst, was rausgegangen ist, nicht was zurückkam. Ein Live-Test kann das nicht — dort ist eine Suche mit einem Treffer von einer Suche mit einem nachgereichten Ersatz-Begriff nicht zu unterscheiden. Genau deshalb greift hier ausnahmsweise der Mock: Prüfgegenstand ist das eigene Verhalten des Servers, nicht eine Annahme über die Quelle.

---

## Checkliste vor dem Release eines datenabfragenden Tools

- [ ] Jeder optionale Filter-/Scope-Parameter geprüft: Was bedeutet Weglassen? Beleg aus der Parameterbeschreibung
- [ ] Recall-Delta gemessen (weggelassen vs. explizit maximal), Delta ≠ 0 behoben
- [ ] Jede bewusste Recall-Verengung (exakt statt Wildcard, kein Fuzzy) nennt die Rubriken/Datenklassen, die das Risiko tragen — und belegt aus der Scope-Aufzählung, dass sie erreichbar sind (Regel 1)
- [ ] Boolesche Parameter-Gruppen vollständig gesendet, Verengung nachgewiesen
- [ ] Leeres Result trägt ein `hint`-Feld mit konkretem nächstem Schritt
- [ ] Transport- und Autorisierungsfehler enden im Fehlerkanal, nie als Leermenge mit Such-Hinweis (Regel 3)
- [ ] Keine Tool-Description erklärt oder entschuldigt eine Leermenge
- [ ] Query-Syntax samt Matching-Granularität in der Description
- [ ] Recall-Canary als Live-Test mit Untergrenzen
- [ ] Antwortstruktur wird bestätigt, bevor gezählt wird — kein `.get(x, [])` auf dem Hauptpfad (Regel 6)
- [ ] Eine Strukturabweichung upstream endet als Fehler, nicht als leeres Resultat (Regel 6)
- [ ] Sortierschlüssel ist total (eindeutiges letztes Glied), dokumentiert in Description und Envelope (Regel 7)
- [ ] Zwei aufeinanderfolgende Seiten sind überschneidungsfrei und decken die Gesamtmenge (Regel 7)
- [ ] `ttlMs` aus `source_freshness` abgeleitet, nie über die nächste Publikation hinaus; unbekannte Kadenz → Boden statt Default, und `ttlMs: 0` nur abgeleitet, nie gewählt (Regel 8)
- [ ] `cacheScope` gegen `requires_credentials` geprüft — credential-abhängige Resultate nie über den Aufrufer hinaus, und nur die beiden Werte `"public"` / `"private"` (Regel 8)
- [ ] `input_required` und Leermenge sind disjunkt: kein `hint` auf einer Rückfrage, kein `inputRequests` auf einem Null-Treffer (Regel 9)
- [ ] Die beantwortete Rückfrage liefert im Retry tatsächlich Treffer (Regel 9)
- [ ] Die Leermenge trägt Vorschläge, abgeleitet aus dem Begriff des Aufrufers — und der Zähler auf der Upstream-Route beweist, dass keiner davon abgefragt wurde (Regel 10, beide Hälften)
- [ ] Kein Eintrag in `entries` beantwortet einen anderen Begriff als den geschickten; heuristische Treffer stehen in einem eigenen Feld, mit `match_type` (Regel 10)
- [ ] Gegen die offizielle Oberfläche der Quelle verglichen, jedes Delta erklärt

## Woher diese Regeln stammen

Aus einem einzelnen realen Vorfall: [`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). Der Server sendete `ClassificationIds` nur bei explizitem Aufruf; die API schränkt eine ID-lose Suche auf `VARIA` ein — eine von 23 Klassifikationen. «Quellensteuer» lieferte null Treffer bei mehreren vorhandenen Einträgen, «Pensionskasse» einen statt 21.

Vier Dinge daran sind übertragbar:

1. **33 grüne Offline-Tests haben nichts gefangen** — Mocks können eine falsche Grundannahme prinzipiell nicht widerlegen.
2. **Ein 68-Punkte-Audit war bestanden** — alle Kategorien prüften die Bauweise, keine die Datentreue.
3. **Die eigene Doku hat das Modell zum Konfabulieren gebracht** — siehe Regel 4.
4. **Gefunden hat es ein User mit dem Web-UI daneben** — Ground Truth kommt von aussen, nicht aus der Testsuite.

Regel 6 kam nach einem zweiten Fall dazu: Eine Abfrage der MCP Registry lieferte eine Zeit lang nichts, weil die Felder unter `servers[].server.*` liegen und der Client eine Ebene höher suchte.

Regel 10 kam nach einem dritten dazu, und der unterscheidet sich in einem Punkt von den beiden davor: Er ist **im Entwurf** aufgefallen, nicht im Betrieb. Beim Anwenden von `ARCH-003` auf ein Such-Tool des Portfolios (2026-08) sind zwei Fehler zusammengefallen, die sich gegenseitig gedeckt haben. Erstens wurde der Vorschlagsmechanismus, den der Check verlangt, als Erlaubnis gelesen, die Vorschläge auch gleich abzufragen — das Resultat hätte Meldungen unter einem Begriff ausgeliefert, den niemand gewählt hat. Zweitens wurde die Gegenrichtung, Exakt-only, mit falsch zugeordneten Konkursmeldungen begründet — einer Rubrik ausserhalb des bedienten Scopes. Beide Fehler klangen nach Sorgfalt, und keiner war an eine überprüfbare Grösse gekoppelt. Was daran übertragbar ist: Ein Argument, das für jede beliebige Quelle wortgleich dastünde, ist noch keines. Der Schaden ist hier nicht eingetreten, weil der Entwurf vorher gelesen wurde — festgehalten ist er trotzdem, an derselben Stelle wie die anderen.

Die Regeln 7–9 haben diese Herkunft **nicht**. Sie kommen aus der Spec 2026-07-28 und sind aus deren Mechanik hergeleitet: stateless Core ohne `initialize` (Regel 7), `ttlMs`/`cacheScope` auf den List-Responses (Regel 8), MRTR statt serverinitiierter Elicitation (Regel 9). Hergeleitet, nicht gemessen — was in diesem Repo ein Unterschied ist und deshalb dabeisteht.

## Verwandte Skills

Fünf Repos, ein Lebenszyklus — gemeinsames GitHub-Topic [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain).

| Phase | Repo | Frage, die es beantwortet |
|---|---|---|
| vor dem Bau | [`mcp-data-source-probe`](https://github.com/malkreide/mcp-data-source-probe-skill) | Taugt die Quelle, und was hat sie? Default-Matrix (1.2b), Recall-Ground-Truth (1.4), Leermengen (3.6) |
| im Bau | **`mcp-data-fidelity`** | **Dieser Skill:** liefert er, was die Quelle hat? |
| im Bau | [`mcp-transport-hardening`](https://github.com/malkreide/mcp-transport-hardening-skill) | Kommt er hoch, weist er richtig ab? Dieselbe stille Fehlerklasse eine Schicht tiefer — nicht der Inhalt der Antwort, sondern ob überhaupt eine kommt |
| nach dem Bau | [`mcp-audit`](https://github.com/malkreide/mcp-audit-skill) | Hält er gegen den Katalog? Die Zuordnung Regel → Check steht unten |
| im Betrieb | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Hält er morgen noch? Seine Recall-Floors sind Regel 5, laufend gegen die echte Quelle gemessen |

Daneben, nicht Teil der Kette: `mcp-builder` — generische Bauanleitung von Anthropic, wird ergänzt und nicht ersetzt. Fremdes Repo, kann das Topic nicht tragen.

### Welche Regel welcher Check ist

Stand des Katalogs: `mcp-audit` auf `main` — 113 Checks in zwölf Kategorien auf zwei Spec-Baselines, davon sechs in der Kategorie `FID`. Geschnitten ist v2.0.0 (112 Checks); die drei Änderungen, die diese Tabelle zuletzt bewegt haben, stehen drüben unter `[Unreleased]` und sind dort als v2.1.0 eingestuft. Die Zuordnung ist nicht eins zu eins — `FID-003` trägt drei Regeln, `ARCH-020` zwei, Regel 5 braucht zwei Checks und Regel 9 drei. Ohne Check ist seit `FID-006` keine mehr, und Regel 10 bringt mit `ARCH-003` den einzigen **`enforced`** Check dieser Tabelle mit — alle anderen sind `advisory`:

| Regel | Check |
|---|---|
| 1 — Scope-Parameter explizit senden | [`FID-001`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-001.md) — «Scope-Defaults: Filter-Parameter explizit senden, nie erben». **Reichweite:** Der Check verlangt, dass eine bewusst gewählte Einschränkung im Tool-Result **sichtbar** ist. Dass ihre **Begründung** den erreichbaren Scope zitiert — die Rubriken nennen, die das Risiko tragen, und sie in der Scope-Aufzählung nachweisen —, verlangt drüben keiner der 113 Checks; das steht allein hier |
| 2 — Parameter-Gruppen vollständig senden | [`FID-004`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-004.md) — «Teilmengen erben Server-Defaults», im Check als die feinere Ausprägung von `FID-001` geführt |
| 3 — Leermenge trägt einen nächsten Schritt | [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md). Die Abgrenzung gegen Transport- und Autorisierungsfehler steht dort ausdrücklich, mit `HTTP 421` als gemessenem Fall und Querverweis auf `SEC-016`/`SEC-024` |
| 4 — Tool-Description als Halluzinations-Oberfläche | ebenfalls [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md) — der Check trägt beide Hälften: den fehlenden nächsten Schritt und die vorformulierte Ausrede |
| 5 — Syntax in der Description, Recall in den Tests | [`FID-005`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-005.md) für die Syntax, [`FID-002`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-002.md) für den Recall gegen die offizielle Oberfläche |
| 6 — Antwortstruktur bestätigen, bevor gezählt wird | [`FID-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-006.md) — «Antwortstruktur bestätigen, bevor gezählt wird», `severity: high`, `spec_baseline: beide`, `adoption: advisory`. Belegfall ist derselbe wie oben: MCP Registry, Felder unter `servers[].server.*`, gelesen eine Ebene höher. Fail-Pattern `payload.get("servers", [])`, Pass-Pattern ein `UpstreamSchemaError`, dessen Meldung die **tatsächlich vorhandenen** Schlüssel nennt. **Reichweite:** ausdrücklich keine vollständige Schema-Validierung — geprüft wird nur, was der Code anfasst, und ein zusätzliches optionales Feld upstream lässt den Check grün. Dass Mocks diese Klasse prinzipiell nicht fangen, steht dort als Querverweis auf `DRIFT-004`. `DRIFT-002` («Fallback verengt, erweitert nie») liegt weiterhin daneben, nicht darauf: dort wird ein *anderer* Datensatz geliefert, hier *keiner* |
| 7 — Deterministische Reihenfolge | [`ARCH-020`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-020.md) — «`ttlMs` und `cacheScope` auf List- und Read-Ergebnissen, deterministische Reihenfolge», `spec_baseline: 2026-07-28`, `adoption: advisory`. **Reichweite:** Der Check prüft die Reihenfolge von `tools/list` über Prozessgrenzen hinweg mit `PYTHONHASHSEED=random` — schärfer als das Testrezept oben — und seit seiner Erweiterung auch den Pagination-Schnitt auf Query-Resultaten: zwei aufeinanderfolgende Seiten, leere Schnittmenge **und** vollständige Vereinigung, gegen einen Bestand grösser als eine Seite. Offen bleibt die **Baseline**: `ARCH-020` misst auf `2026-07-28`, der Pagination-Verlust tritt aber auch auf `2025-11-25` auf — er hängt an der Quelle und am Sortierschlüssel, nicht am Protokollstand, und Regel 7 gilt hier ausdrücklich unabhängig von der Spec-Version. Ein Server der alten Baseline wird drüben also nicht dagegen gemessen. Der Check benennt diese Lücke in seiner Description und lässt sie bewusst offen: `spec_baseline` gilt pro Datei, und `beide` würde `ttlMs`/`cacheScope` gegen Server messen, deren Protokoll diese Felder nicht kennt |
| 8 — Ehrliches `ttlMs` | ebenfalls [`ARCH-020`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-020.md) — der Check trägt beide Hälften, samt dem Kriterium «kein Wert oberhalb der Änderungsfrequenz der Quelle» und `cacheScope: "public"` nur über aufruferunabhängigen Inhalten. **Reichweite:** Er misst die fünf `CacheableResult`-Methoden, knüpft `cacheScope` an `data_class` und fragt seit seiner Erweiterung auch die Ableitung für **Datenresultate** ab — aus `source_freshness`, gedeckelt auf die nächste Publikation, unbekannte Kadenz kurz statt komfortabel. Dieses Kriterium ist **bedingt** formuliert: Es greift, «sofern der Server Datenresultate mit `ttlMs` versieht». Ein Datenresultat ganz **ohne** `ttlMs` fällt drüben damit nicht auf — dass eines hingehört, verlangt nur diese Regel |
| 9 — `input_required` ist keine leere Antwort | [`HITL-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/HITL-006.md) — «MRTR statt serverinitiierter Requests», dazu [`ARCH-018`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-018.md) für `resultType` auf allen Results und, seit dessen Erweiterung, [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md) für die Abgrenzung gegen den Null-Treffer. Die Aufteilung steht drüben in beiden Checks ausgeschrieben: `HITL-006` prüft die Retry-Idempotenz und dass `input_required` nicht für gewöhnliche **Fehler** benutzt wird, `FID-003` die Disjunktheit gegen die **Leermenge** — kein `hint` auf einer Rückfrage, kein `inputRequests` auf einem Null-Treffer, und `entries` fehlt bei der Rückfrage, statt leer zu sein. **Reichweite:** Die drei Kriterien in `FID-003` sind doppelt bedingt — auf `2026-07-28` und darauf, dass das Tool `input_required` überhaupt zurückgeben kann; `FID-003` selbst trägt unverändert kein `spec_baseline`. Und dass der beantwortete Retry tatsächlich **Treffer** liefert, verlangt drüben nur der Idempotenz-Test bei `write_capable: true`; für lesende Server steht dieser Nachweis allein hier |
| 10 — Vorschlagen ist nicht Erweitern | [`ARCH-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-003.md) — «‹Not Found›-Anti-Pattern: Heuristiken statt leerer Antworten», `severity: medium`, `applies_when: always`, ohne `adoption`-Feld und damit **`enforced`**. Der Check ist der Grund für diese Regel und zugleich ihre Gegenprobe: Er verlangt auf der Leermenge einen Fuzzy-Match **oder** einen Vorschlagsmechanismus plus `match_type`, und der Vorschlags-Arm erfüllt beide Seiten. **Reichweite:** Was drüben fehlt, ist die Disjunktheit — kein Kriterium verbietet, den Vorschlag gleich abzufragen und seine Treffer unter `results` zu mischen; das Pass-Pattern des Checks tut es sogar (`match_type: "fuzzy"` auf einer gemeinsamen Liste). Der Zähler auf der Upstream-Route steht allein hier. Nebenan liegt [`DRIFT-002`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/DRIFT-002.md) («Fallback verengt, erweitert nie») — dieselbe Form eine Ebene weiter: dort wird ein anderer *Datensatz* substituiert, hier eine andere *Abfrage* |

Wer nach den Regeln 1–5 baut, besteht die `FID`-Checks; Regel 6 liegt seit `FID-006` ebenfalls dort, allerdings `advisory` — der Check verlässt diesen Stand erst nach dem ersten Portfolio-Durchlauf, der zeigt, wie viele Server die Antwortstruktur überhaupt bestätigen. Die Regeln 7–9 laufen über `ARCH-020`, `HITL-006`, `ARCH-018` und die `2026-07-28`-Kriterien von `FID-003` und sind ebenfalls durchweg `advisory` — sie blockieren also nicht, sie werden gezählt. Regel 10 ist die Ausnahme: `ARCH-003` ist `enforced` und gilt `always`, ein Verstoss dagegen blockiert. Ohne Check ist keine Regel mehr; was offen bleibt, steht je Zeile in der Reichweite und ist damit ein benannter Rand, kein fehlender Check.

**Warum die Zeilen 7–9 nicht in `FID` liegen:** Die drei Regeln kommen aus der Spec, und der Katalog ordnet Spec-Checks nach dem Ort der Änderung ein — Caching und Reihenfolge nach `ARCH`, MRTR nach `HITL`. Die Datentreue-Hälfte davon stand hier bis zuletzt als offen und ist inzwischen abgedeckt — aber nicht durch neue `FID`-Checks: `ARCH-020` hat den Pagination-Schnitt und die `ttlMs`-Ableitung in sich aufgenommen, statt ein `FID-007` zu eröffnen, weil beides an denselben zwei Grössen hängt wie der bestehende Check; und die Disjunktheit gegen den Null-Treffer ist nach `FID-003` gegangen, weil sie an der Leermenge hängt und nicht am Rückfrageprotokoll.

**Und warum Zeile 10 nicht:** Aus einem anderen Grund. `ARCH-003` ist älter als die `FID`-Kategorie und beschreibt das Verhalten auf der Leermenge aus der Perspektive des Antwortformats, nicht der Datentreue. Die Datentreue-Hälfte — dass ein Vorschlag nie zum Treffer werden darf — ist dort nicht als Kriterium formuliert. Ob das ein `FID-007` verdient, entscheidet der erste Portfolio-Durchlauf, der zeigt, wie viele Server auf der Leermenge überhaupt etwas anbieten. Bis dahin steht der Rand in der Zeile, wie überall sonst in dieser Tabelle.

**Zur Haltbarkeit dieser Tabelle:** Der Katalog bewegt sich schneller als dieser Skill. Zwischen v1.7.0 (97 Checks) und v2.0.0 (112, dual baseline) lagen vier Tage, und mit v2.0.0 sind aus vier angeblich fehlenden Checks drei vorhandene geworden. Der nächste Beleg kam einen Tag später: Zwischen v2.0.0 und dem Katalogstand oben liegt ein Tag, und in ihm ist aus «Regel 6 hat keinen Check» ein `FID-006` geworden — plus zwei Reichweite-Sätze, die von «prüft er nicht» auf «prüft er» gekippt sind. Wer hier eine Zeile liest, um ein Finding zu beheben, prüft besser den Katalogstand oben mit — eine falsche Zuordnung kostet an genau der Stelle am meisten, an der jemand etwas reparieren will.
