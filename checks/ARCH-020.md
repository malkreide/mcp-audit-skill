---
id: ARCH-020
title: "ttlMs und cacheScope auf List- und Read-Ergebnissen, deterministische Reihenfolge"
category: ARCH
severity: medium
applies_when: 'always'
spec_baseline: 2026-07-28
adoption: advisory
pdf_ref: "SEP-2549"
spec_ref: "SEP-2549 (PR 2549) — Spec-Changelog 2026-07-28, Minor #5; Reihenfolge: Minor #3"
evidence_required: 3
---

# ARCH-020 — `ttlMs` / `cacheScope` und deterministische Reihenfolge

## Description

Zwei Änderungen, die dieselbe Sache betreffen — was ein Client mit einer Antwort tun darf, nachdem er sie erhalten hat.

**`CacheableResult` (SEP-2549, Pflicht).** Fünf Methoden tragen neu zwei Felder: `tools/list`, `prompts/list`, `resources/list`, `resources/read` und `resources/templates/list`. `ttlMs` ist ein Frischehinweis in Millisekunden; `cacheScope` ist `"public"` oder `"private"` und entscheidet, ob eine zwischengeschaltete Instanz mitcachen darf. Die beiden ersetzen `listChanged` nicht, sie ergänzen es.

**Deterministische Reihenfolge (Minor #3, SHOULD).** `tools/list` soll eine stabile Reihenfolge liefern, damit clientseitiges Caching und Prompt-Caching greifen.

**Warum das zusammen einen Check bildet und nicht zwei.** Beide Anforderungen sind wertlos, solange die andere fehlt: Ein `ttlMs` von 300 000 über einer Liste, die bei jedem Aufruf anders sortiert ist, veranlasst den Client, fünf Minuten lang eine Reihenfolge zu behalten, die keine Aussage trägt — und das Prompt-Caching bricht bei jedem Aufruf trotzdem. Umgekehrt nützt eine stabile Reihenfolge wenig, wenn kein Frischehinweis das Nachfragen bremst. Der Fix ist derselbe Handgriff an derselben Stelle, und §2.5 verlangt, dass ein Check in **einem** Schritt behebbar bleibt.

**Der stille Fehler ist ein dritter Wert.** `cacheScope` ist ein geschlossener Vorrat aus zwei Einträgen. Wer `"session"`, `"caller"` oder `"none"` sendet, meint meistens etwas Vernünftiges — «enger als öffentlich» — und liefert trotzdem etwas Schemawidriges: Eine Zwischeninstanz kennt den Wert nicht und behandelt ihn wie ein fehlendes Feld. Der vorsichtig gemeinte Wert ist damit **weiter** als `"private"`, nicht enger. Ein erfundener Wert ist kein vorsichtiger Wert.

Bis v2.1.0 hat dieser Check das nicht gesehen: Seine Kriterien fragten, ob `"public"` an der richtigen Stelle steht — ein Wert, der weder `"public"` noch `"private"` ist, bestand sie deshalb ohne Weiteres, und zwar auf allen fünf Methoden. **Belegfall (Portfolio, 2026-08):** `mcp-data-fidelity-skill` lieferte in `reference/patterns.py` einen Copy-Paste-Baustein mit `Literal["public", "session"]` aus, samt Testrezept `assert result.cache_scope == "session"`. Dieser Baustein ist für die datenabfragenden Server des Portfolios der Einstieg; dort korrigiert in PR #10. Kein Kriterium dieses Katalogs hätte einen Server gemeldet, der ihm gefolgt ist — das ist die Lücke, die diese Fassung schliesst.

**Der teure Fehler ist `cacheScope: "public"` an der falschen Stelle.** Bei einem Server mit `data_class != "Public Open Data"` erlaubt `"public"` einer Zwischeninstanz, die Antwort für andere Aufrufer aufzubewahren. Wenn `resources/read` mandantenbezogene Inhalte liefert, ist das kein Performance-Detail, sondern eine Freigabe. Das ist der Grund, warum dieser Check trotz `medium` eine `critical`-Nachbarschaft hat: Der Schaden liegt nicht in der Kategorie Caching, sondern in `CH-001` und `SEC-023`.

### Dieselben zwei Grössen auf Datenresultaten — und dort schärfer

Beide Anforderungen sind oben an den Protokoll-Methoden formuliert. Dieselben zwei Grössen — **ein totaler Sortierschlüssel** und **ein begründeter `ttlMs`** — entscheiden bei Query-Resultaten über die Vollständigkeit der Antwort, und dort kostet ihr Fehlen mehr als einen kalten Cache. Das ist keine zweite Regel, sondern derselbe Handgriff an derselben Stelle mit grösserer Wirkung; deshalb steht es hier und nicht in einem eigenen Check.

**Der Pagination-Schnitt.** Bei instabiler Ordnung wechselt ein Datensatz zwischen dem Abruf von Seite 1 und dem von Seite 2 seine Position — und erscheint dadurch **doppelt oder gar nicht**. Das ist Recall-Verlust: dieselbe stille Unvollständigkeit wie in `FID-001`, nur beim Blättern statt beim Filtern, und sie tritt bei **korrekt gesendeten Parametern** auf. Kein Fehler wird gemeldet, keine Zahl sieht falsch aus; der fehlende Datensatz hinterlässt keine Spur. Ein Sortierschlüssel, der nicht total ist (`ORDER BY datum` bei mehreren Einträgen pro Tag), genügt dafür bereits — bei Gleichstand entscheidet die Quelle je Abruf neu.

**`ttlMs` aus der Quellen-Frische.** Für Datenresultate reicht «kein Wert oberhalb der Änderungsfrequenz» nicht als Begründung, weil die Frequenz hier nicht geschätzt, sondern erhoben wird: aus `source_freshness` — publizierte Kadenz, `Last-Modified`, `Cache-Control` —, gedeckelt auf die **nächste Publikation**. Eine Quelle, die dienstags um 09:00 publiziert, verträgt am Montag einen langen und am Dienstag um 08:55 einen sehr kurzen Wert; ein fester Mittelwert ist an beiden Tagen falsch. **Unbekannte Kadenz heisst kurzer Wert, nicht komfortabler** — die andere Richtung liefert veraltete Daten unter dem Anschein von Frische.

**Bekannte Lücke, ausdrücklich benannt.** Dieser Check trägt `spec_baseline: 2026-07-28`. Der Pagination-Verlust existiert aber auch auf `2025-11-25`: Er hängt an der Quelle und am Sortierschlüssel, nicht am Protokollstand. Ein Server der alten Baseline wird deshalb **nicht** dagegen gemessen, obwohl der Fehler dort auftreten kann. Die Lücke bleibt bewusst offen, statt sie durch `spec_baseline: beide` zu schliessen: Das Feld gilt pro Datei, nicht pro Kriterium — der ganze Check auf `beide` würde `ttlMs` und `cacheScope` gegen Server messen, deren Protokoll diese Felder nicht kennt, und dort einen Falsch-Fail erzeugen, genau wo der Check schweigen soll. Wenn die Reihenfolge-Hälfte eine eigene Reichweite verdient, wird sie ein eigener Check — beim Abschluss von Migrations-Welle D, wenn ohnehin über den Verbleib der Kohorte entschieden wird, und nicht als stille Ausweitung heute.

## Verification

### Modus 1: automated (Felder vorhanden)

```bash
grep -rnE "ttlMs|ttl_ms|cacheScope|cache_scope|CacheableResult" src/ --include="*.py" --include="*.ts"

# Welche Werte kennt der Quelltext? Mit Kontext, weil der Wert regelmässig in
# einer ANDEREN Zeile steht als das Feld — Enum-Deklaration, Mapping, Rückgabe
# einer Hilfsfunktion.
grep -rnE -A2 "cacheScope|cache_scope|CacheScope" src/ --include="*.py" --include="*.ts"
```

**Dieser Modus sieht den Wertevorrat an, er entscheidet ihn nicht** — und das ist keine Bequemlichkeit, sondern eine gemessene Grenze. Eine Fassung des Belegfalls:

```python
def cache_scope(*, requires_credentials: bool) -> Literal["public", "session"]:
    return "session" if requires_credentials else "public"
```

Jeder Filter, der die Zeile mit `cacheScope` auf ein festes Fenster kürzt, verfehlt hier beide Vorkommen von `"session"`: In der Signatur steht es hinter dem Fenster, in der `return`-Zeile kommt der Feldname gar nicht vor. Wer daraus «keine Abweichung gefunden» liest, hat §2.6 verletzt, bevor der Check anfängt. Deshalb: gelesen wird der Kontext, **entschieden wird in Modus 2** am ausgelieferten Result. Bleibt Modus 1 ohne jeden Treffer, ist der Ausgang `todo` — der Server setzt das Feld anderswo oder in einer anderen Sprache.

### Modus 2: runtime_test (Felder auf allen fünf Methoden)

```bash
for m in tools/list prompts/list resources/list resources/templates/list; do
  echo "== $m"
  curl -sS -X POST "$MCP_URL" -H 'Content-Type: application/json' \
    -H "Mcp-Method: $m" -H "Mcp-Name: $m" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"$m\",\"params\":{}}" \
    | jq '{
        ttlMs: .result.ttlMs,
        cacheScope: .result.cacheScope,
        scopeOk: (.result.cacheScope | . == "public" or . == "private")
      }'
done
```

Drei unterscheidbare Ausgänge, und sie kosten Verschiedenes:

| Beobachtung | Ausgang | Bedeutung |
|---|---|---|
| `cacheScope: null` | Befund | Feld fehlt — schemawidrig, aber sichtbar |
| `scopeOk: false` | Befund | Wert ausserhalb des Vorrats; eine Zwischeninstanz liest ihn wie ein fehlendes Feld, also **weiter** als gemeint |
| `scopeOk: true` | weiter zur Angemessenheit | Der Wert ist zulässig — ob er der richtige ist, entscheiden die zwei Kriterien darunter |

`scopeOk: false` ist der Ausgang, den die Kriterien vor v2.1.0 nicht kannten. `resources/read` separat prüfen, es braucht eine URI.

### Modus 3: runtime_test (Reihenfolge ist stabil)

```bash
a=$(curl -sS -X POST "$MCP_URL" -H 'Content-Type: application/json' \
      -H 'Mcp-Method: tools/list' -H 'Mcp-Name: tools/list' \
      -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
      | jq -c '[.result.tools[].name]')
b=$(... derselbe Aufruf, neuer Prozess ...)
[ "$a" = "$b" ] && echo "stabil" || echo "BEFUND: Reihenfolge wechselt"
```

**Zwei getrennte Prozesse, nicht zwei Aufrufe im selben.** Die häufigste Ursache instabiler Reihenfolge ist Iteration über ein `set` oder ein Registry-Dict, dessen Ordnung von der Hash-Randomisierung abhängt — und die ist **innerhalb** eines Prozesses konstant. Ein Test, der zweimal im selben Interpreter fragt, bestätigt eine Stabilität, die es über Neustarts nicht gibt. Unter Python zusätzlich mit gesetztem `PYTHONHASHSEED=random` in beiden Läufen.

### Modus 4: runtime_test (der Pagination-Schnitt)

Nur anwendbar, wenn der Server Query-Resultate paginiert. Zwei aufeinanderfolgende Seiten holen und die beiden Mengen gegeneinander halten — der Befund steckt in der Überlappung und in der Summe, nicht im Statuscode.

```python
@pytest.mark.live
async def test_two_pages_neither_repeat_nor_lose_a_record():
    p1 = await client.search(QUERY, offset=0, limit=50)
    p2 = await client.search(QUERY, offset=50, limit=50)
    ids1, ids2 = {r.id for r in p1}, {r.id for r in p2}

    assert not (ids1 & ids2), f"doppelt geblättert: {sorted(ids1 & ids2)}"
    assert len(ids1 | ids2) == len(ids1) + len(ids2), "Datensätze verloren"
```

Beide Assertions sind nötig und messen Verschiedenes: Die Schnittmenge fängt den doppelt gelieferten Datensatz, die Vereinigung den verlorenen. Wer nur die erste schreibt, prüft die harmlosere Hälfte — ein Datensatz, den niemand je sieht, taucht in keiner Schnittmenge auf.

**Gegen einen Bestand ausführen, der grösser ist als eine Seite.** Bei zwanzig Datensätzen und `limit=50` ist `p2` leer, beide Assertions sind erfüllt, und der Test hat nichts geprüft. Ist kein ausreichend grosser Bestand erreichbar, wird das `limit` verkleinert — nicht der Test weggelassen.

### Modus 5: code_review (woher der `ttlMs` eines Datenresultats stammt)

```bash
# Jeder ttlMs-Wert auf einem Datenpfad — und die Frage, was ihn begründet.
grep -rnE 'ttlMs|ttl_ms|max_age|cache_ttl' src/ --include="*.py" --include="*.ts"

# Wird die Frische der Quelle überhaupt gelesen?
grep -rniE 'source_freshness|last-modified|cache-control|publication|kadenz' src/
```

Ein literaler Wert ohne Kommentar, der die Kadenz nennt, ist ein Befund: Er mag zufällig richtig sein, aber niemand kann das prüfen, und beim nächsten Publikationswechsel merkt es niemand.

## Pass Criteria

- [ ] `ttlMs` und `cacheScope` liegen auf allen fünf Methoden an, sofern der Server sie bedient
- [ ] `ttlMs` ist begründet gewählt, nicht 0 und nicht willkürlich gross — ein Wert oberhalb der Änderungsfrequenz der Quelle liefert veraltete Werkzeuglisten
- [ ] Jeder gesetzte `cacheScope` trägt **einen der zwei Werte aus SEP-2549** — `"public"` oder `"private"`. Erhoben am ausgelieferten Result (Modus 2), nicht nur am Quelltext: Ein Literal kann auf dem Weg nach draussen noch durch ein Mapping laufen
- [ ] `cacheScope: "public"` steht ausschliesslich über aufruferunabhängigen Inhalten
- [ ] Bei `data_class != "Public Open Data"`: `resources/read` liefert `"private"`, und ein Test hält das fest
- [ ] `tools/list` liefert eine deterministische Reihenfolge, über **Prozessgrenzen** hinweg geprüft
- [ ] Die Reihenfolge stammt aus einer expliziten Sortierung, nicht aus der Registrierungsreihenfolge — letztere ändert sich mit jedem Refactoring des Imports
- [ ] Sofern der Server Query-Resultate paginiert: Der Sortierschlüssel ist **total** — bei Gleichstand entscheidet ein eindeutiger Zusatzschlüssel, nicht die Quelle
- [ ] Sofern paginiert: Ein Test über zwei aufeinanderfolgende Seiten belegt leere Schnittmenge **und** vollständige Vereinigung, gegen einen Bestand grösser als eine Seite
- [ ] Sofern der Server Datenresultate mit `ttlMs` versieht: Der Wert ist aus `source_freshness` abgeleitet (publizierte Kadenz, `Last-Modified`, `Cache-Control`) und auf die nächste Publikation gedeckelt — bei unbekannter Kadenz kurz, nicht komfortabel
- [ ] **Gegenprobe:** Der Reihenfolgetest ist einmal gegen eine Fassung mit `set`-Iteration gelaufen und hat dort angeschlagen; wo paginiert wird, ist der Seitentest einmal gegen einen nicht-totalen Sortierschlüssel gelaufen und hat dort angeschlagen; und die Werteprüfung ist einmal gegen ein Result mit `cacheScope: "session"` gelaufen und hat dort angeschlagen

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| `cacheScope: "public"` pauschal gesetzt | Zwischeninstanz gibt mandantenbezogene Inhalte weiter |
| `cacheScope` mit einem selbst erfundenen Wert (`"session"`, `"caller"`, `"none"`) | Schemawidrig, und die Wirkung ist die Gegenrichtung der Absicht: Eine Zwischeninstanz liest den unbekannten Wert wie ein fehlendes Feld |
| Wertevorrat nur am Quelltext geprüft | Ein `Literal[...]` kann korrekt aussehen und trotzdem über ein Mapping als etwas anderes hinausgehen |
| `ttlMs` grösser als der Änderungstakt der Quelle | Client arbeitet mit einer Werkzeugliste, die es nicht mehr gibt |
| `ttlMs: 0` als «sicherer Wert» | Kein Caching, jeder Aufruf trifft den Server — die Änderung verpufft |
| Reihenfolge aus `set` oder Registry-Dict | Wechselt beim Neustart; Prompt-Cache trifft nie |
| Stabilitätstest im selben Prozess | Bestätigt eine Stabilität, die es nicht gibt |
| Nur `tools/list` versorgt | Die vier anderen Methoden bleiben schemawidrig |
| Sortierschlüssel nicht total (`ORDER BY datum`) | Bei Gleichstand entscheidet die Quelle je Abruf neu — beim Blättern doppelt oder gar nicht |
| Seitentest prüft nur die Schnittmenge | Fängt den doppelten Datensatz, nicht den verlorenen — und der ist der stille |
| Seitentest gegen einen Bestand unter einer Seitenlänge | Zweite Seite leer, beide Assertions erfüllt, nichts geprüft |
| `ttlMs` als literale Zahl ohne begründende Kadenz | Mag heute stimmen; beim nächsten Publikationswechsel merkt es niemand |
| Unbekannte Kadenz mit einem grosszügigen Wert überbrückt | Veraltete Daten unter dem Anschein von Frische — die teure Richtung des Irrtums |

## Remediation

```python
TOOLS_TTL_MS = 300_000          # 5 min: Werkzeugliste ändert sich mit Releases

@server.list_tools()
async def list_tools() -> ToolsListResult:
    return ToolsListResult(
        tools=sorted(REGISTRY.values(), key=lambda t: t.name),   # explizit
        ttlMs=TOOLS_TTL_MS,
        cacheScope="public",     # Werkzeugliste ist für alle Aufrufer gleich
    )

@server.read_resource()
async def read_resource(uri: str) -> ResourceReadResult:
    return ResourceReadResult(
        contents=await _impl.read(uri),
        ttlMs=60_000,
        # Inhalte sind aufruferbezogen — keine geteilte Zwischenspeicherung
        cacheScope="private",
    )
```

```python
def test_tool_order_survives_a_restart(run_in_fresh_process):
    a = run_in_fresh_process("tools/list", env={"PYTHONHASHSEED": "random"})
    b = run_in_fresh_process("tools/list", env={"PYTHONHASHSEED": "random"})
    assert [t["name"] for t in a] == [t["name"] for t in b]
```

Und dieselben zwei Grössen auf dem Datenpfad — ein totaler Schlüssel, ein aus der Quelle abgeleiteter Frischewert:

```python
# Total: der fachliche Schlüssel plus ein eindeutiger Zusatz für den Gleichstand.
ORDER = ("publiziert_am", "id")


async def search(query: str, offset: int, limit: int) -> QueryResult:
    rows = await _impl.search(query, order_by=ORDER, offset=offset, limit=limit)
    return QueryResult(
        rows=rows,
        # Aus source_freshness abgeleitet, nicht geschätzt: gedeckelt auf die
        # nächste Publikation, bei unbekannter Kadenz bewusst kurz.
        ttlMs=ttl_until_next_publication(SOURCE_FRESHNESS, fallback_ms=60_000),
        cacheScope="public",     # Open Data, aufruferunabhängig
    )
```

## Effort

S für die fünf Protokoll-Methoden — eine Sortierung und zwei Felder je Methode. Die Entscheidung über `cacheScope` je Ressource kostet mehr Nachdenken als Code.

Auf dem Datenpfad ebenfalls S, solange die Quelle einen eindeutigen Schlüssel anbietet und ihre Kadenz publiziert. Bietet sie keinen, wird es M: Dann muss ein stabiler Zusatzschlüssel erst hergestellt werden, und das ist eine Entscheidung über die Abfrage, nicht über die Ausgabe.

## References

- [Spec 2026-07-28 — Changelog, Minor #3 und #5](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2549](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2549)
- `CH-001` (Datenresidenz), `SEC-023` (DLP auf Outputs), `ARCH-008` (Resources)
- `FID-001` — dieselbe stille Unvollständigkeit beim Filtern, die der Pagination-Schnitt beim Blättern erzeugt
- `FID-004` — Parameter-Gruppen vollständig senden; `offset` und `limit` sind eine solche Gruppe, und dieser Check verlangt zusätzlich die Ordnung darunter
- Portfolio-Fundstück zum Wertevorrat: [`mcp-data-fidelity-skill` PR #10](https://github.com/malkreide/mcp-data-fidelity-skill/pull/10) — der Link zeigt bewusst weiter ins **archivierte** Repo: Ein Pull Request ist ein datierter Vorgang und hat dort stattgefunden. Die Regel selbst steht heute in [`skills/mcp-data-fidelity/`](../skills/mcp-data-fidelity/) — der Copy-Paste-Baustein des Portfolios lieferte `Literal["public", "session"]` aus. Dort korrigiert; hier ist der Grund, warum es kein Check gemeldet hat
