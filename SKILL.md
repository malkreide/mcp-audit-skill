---
name: mcp-data-fidelity
description: Datentreue-Regeln für MCP-Server-Tools, die eine externe Datenquelle abfragen — damit ein Server nicht still unvollständig liefert. Verwende diesen Skill ergänzend zu mcp-builder immer wenn (1) ein Such-, Query- oder Filter-Tool für einen MCP-Server entworfen oder gebaut wird, (2) eine Tool-Description dafür geschrieben wird, (3) jemand meldet, ein Server finde nichts, zu wenig oder weniger als die offizielle Oberfläche («findet nichts», «leeres Ergebnis», «Web-UI zeigt mehr», «Recall», «Scope»), (4) ein Modell auf ein leeres Tool-Result hin etwas erfunden hat oder ein Fuzzy-Fallback entworfen wird, (5) optionale API-Parameter (Filter, Facetten, Feld-Flags) in Requests übersetzt werden, (6) Tests dafür geschrieben werden, (7) ein Server auf MCP-Spec 2026-07-28 migriert wird (Sortierreihenfolge, `ttlMs`/`cacheScope`, MRTR), oder (8) eine Antwort geparst wird — Kopfzeilen, Spaltennamen, Schreibweise, Zahlenspalten mit unterdrückten Werten («1 bis 5»), Summen. Nicht nötig für Server ohne externe Datenquelle.
---

# MCP Data Fidelity — liefert der Server, was die Quelle hat?

Companion zu `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **liefert er, was die Quelle tatsächlich hat?**

Das ist eine eigene Fehlerklasse, weil sie still ist. HTTP 200, wohlgeformtes JSON, grüne Tests — und inhaltlich falsch. Ein Server, der zwei Prozent des Bestands durchsucht und das nicht meldet, produziert Antworten, die niemand als falsch erkennt.

**Die Leitfrage bei jedem datenabfragenden Tool:** *Wenn dieses Tool nichts findet — kann ich unterscheiden, ob es nichts gibt oder ob ich falsch gefragt habe?* Ist die Antwort nein, greift eine der vierzehn Regeln unten.

Seit Regel 10 steht die Stufe darunter daneben: *und wenn ich falsch gefragt habe — komme ich von hier zur richtigen Frage?* Die erste Frage entscheidet, ob das Modell schweigen darf. Die zweite, ob es weiterkommt, ohne sich einen Treffer zu erfinden.

Regel 11 liefert das Material für die erste Frage: Wer nicht mitliest, **welche Anfrage** die Leermenge erzeugt hat, kann «nichts da» von «falsch gefragt» prinzipiell nicht trennen — er kann die Leitfrage nur raten. Regel 12 stellt beide Fragen eine Ebene tiefer, am einzelnen Feld: Ein `null` beantwortet sie genauso wenig wie ein `[]`.

Die Regeln 13 und 14 setzen dort an, wo die Antwort die Quelle bereits verlassen hat und der eigene Code sie liest: Regel 13 am Namen des Feldes, Regel 14 an seinem Inhalt. Beide erzeugen einen Ausfall, der wie eine Antwort aussieht — die eine eine leere Trefferliste, die andere eine Zahl, die zu tief ist.

Die Regeln 1–6 und 10–14 stammen aus Vorfällen, die Regeln 7–9 aus der Spec 2026-07-28. Der Unterschied ist ausgewiesen und nicht kosmetisch — siehe den Abschnitt vor Regel 7. Die Nummerierung folgt der Reihenfolge, in der die Regeln dazugekommen sind, nicht dieser Gruppierung.

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

Belegfall ([`amtsblatt-mcp`, ARCH-003-Finding vom 2026-07-30](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md)): Version 0.20.0 lehnte einen Vorschlags- oder Fuzzy-Mechanismus ausdrücklich ab und begründete das mit «bankruptcy notices, debt-collection summonses, estate calls, construction objections» — dem Schaden, die falsche Firma als konkurs zu benennen. **Jede Rubrik dieser Liste ist rot und über kein Tool erreichbar:** `KK`, `SB`, `SR`, `LS`, `NA`, `ES`, `TE-*`, `GB-*`, `GE-*`, `BP-*` liegen sämtlich ausserhalb der `GREEN_RUBRICS` — einer Allow-Liste, die genau dafür existiert, systematische Personendaten auszuschliessen.

Die Verkehrung ist der Punkt: Weil der durchsuchbare Bestand der **nicht-sensible** ist, wurde die Ausnahme für sensible Daten für genau die Menge beansprucht, auf die das Kriterium anzuwenden gewesen wäre. Die Begründung klang zwingend, stand in beiden `SECURITY`-Dateien und im CHANGELOG — und war an nichts gekoppelt, was der Server je ausliefert. Es ist die vorformulierte Ausrede aus Regel 4, eine Stufe früher: Regel 4 fängt sie dort, wo das Modell sie liest, hier wird sie dort gefangen, wo jemand sie schreibt.

Was von der Begründung übrig bleibt, ist schmaler und echt — und zeigt, wozu die Prüffrage dient: `HR`/`BH` (Handelsregister) und `OB-*` (Beschaffungen) **sind** erreichbar und nennen juristische Personen, ein verbreiterter Firmenname liefert also Meldungen über andere Firmen. Das ist ein Argument darüber, *wie* verbreitert wird, keine Ausnahme dagegen, überhaupt etwas anzubieten. Der Unterschied zwischen den beiden Begründungen ist nicht die Sorgfalt, mit der sie formuliert sind, sondern ob eine erreichbare Rubrik darunter steht.

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

Konkret ist er allerdings erst zusammen mit der Anfrage, auf die er sich bezieht. Ein `hint`, der auf jeder Leermenge dieselbe Konstante ist, sagt nichts über *diese* Abfrage — er ist eine Formulierung des Nulls, keine Auskunft über sie. Was daneben stehen muss, damit der nächste Schritt überhaupt überprüfbar wird, steht in Regel 11.

**Abgrenzung:** Ein Transport- oder Autorisierungsfehler ist keine Leermenge und darf nie als solche formatiert werden. Ein abgewiesener Request — HTTP 421 auf einen fremden Host-Header, 401, 403, ein Verbindungsabbruch — erreicht die Quelle nie und kommt bei der aufrufenden Schicht trotzdem als «Fehlschlag ohne Daten» an; wer nur auf «keine Datensätze» prüft, reicht ihn als Leermenge durch. Er trägt aber einen anderen nächsten Schritt: **Konfiguration prüfen, nicht Suche verbreitern.** Ein Hinweis, der zur Wildcard rät, während die Abfrage gar nicht angekommen ist, schickt das Modell in die falsche Richtung — und ein Konfigurationsfehler unterläuft genau die Regel, die das Raten verhindern soll. Solche Fälle gehören mit `isError` in den Fehlerkanal, wie die Strukturabweichung in Regel 6.

Eine dritte Tür hat die Spec 2026-07-28 aufgemacht: die MRTR-Rückfrage. Sie sieht erfolgreich aus und ist trotzdem keine Leermenge — Regel 9.

## Regel 4 — Die Tool-Description ist eine Halluzinations-Oberfläche

Die schwerste der neun incident-belegten Regeln, weil sie kontraintuitiv ist: **Eine Formulierung, die eine Leermenge erklärt, erzeugt Konfabulation zuverlässiger als gar keine Formulierung.**

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

**Vergleiche: exakt, nicht Teilzeichenkette.** Der Satz oben — *ein Test, der die Bedingung herstellt, unter der der Fehler nicht auftreten kann, prüft nichts* — hat eine zweite, unauffälligere Ausprägung: den Vergleich, der nicht scheitern kann. **Auf einem strukturierten Feld gilt exakte Gleichheit, nicht Teilzeichenkette.** Ein Präfix-Assert besteht, bis der Feldwert wächst — und dann besteht er weiter und meint etwas anderes. Er prüft ab da nur noch den Teil, der sich nie ändert.

```python
# ✗ besteht auch, wenn das Feld längst etwas anderes sagt
assert MARKER in result["message"]
assert result["status"].startswith("ready")

# ✓ die Zusicherung ist so breit wie das Feld, das sie zusichert
assert result["message"] == MARKER
assert result["status"] == "ready"
```

Gemessener Fall: Ein Marker war als «Lifespan gestartet» deklariert, das Feld lautete «Lifespan gestartet — geteilter HTTP-Client bereit». Der exakte Vergleich schlug fehl, obwohl der Server korrekt lief — und zeigte damit genau auf die Stelle, die schief stand: die veraltete Deklaration. Ein `in`-Vergleich wäre grün geblieben, hätte die Deklaration konserviert und wäre auch dann noch grün gewesen, wenn der Rumpf des Feldes irgendwann etwas ganz anderes meldet. Der exakte Vergleich kostet einmal einen roten Lauf mit klarer Ursache; der unscharfe kostet die Prüfung.

**Abgrenzung gegen Regel 1.** Dort geht es um «exakt statt Wildcard» beim **Abfragen der Quelle** — eine Verengung des Recalls, die begründet und belegt werden muss. Hier geht es um den Vergleich eines **zurückgekommenen Feldwerts**, und da ist nichts abzuwägen: Die Teilzeichenkette behauptet weniger, als der Test in seinem Namen verspricht. Ebenso wenig widerspricht das dem Präfix-Wildcard weiter oben — der richtet sich gegen einen **Textbestand**, der Vergleich hier gegen einen **Wert**. Volltext will unscharf sein, ein Statusfeld nicht.

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

Die Regeln 1–6 stehen hier, weil etwas kaputtgegangen ist: eine Suche über 1 von 23 Klassifikationen, eine Registry-Abfrage eine Ebene daneben. Die Regeln 10 bis 14 stehen hinter diesem Abschnitt und gehören trotzdem zur ersten Gruppe — sie sind später dazugekommen, nicht anders belegt. Wie weit der Beleg bei 11 und 12 trägt, steht bei ihnen: der eine ist in einem Nachbarwerkzeug gemessen, der andere im Review abgefangen statt ausgeliefert. Die Regeln 13 und 14 sind wieder ausgeliefert gewesen, in einem Server des Portfolios, und ihre Zahlen sind an der laufenden Quelle gemessen. Für die Regeln 7–9 gilt das nicht, und das gehört gesagt, statt sie stillschweigend danebenzustellen. Ihr Beleg ist der **Mechanismus**: Die Spec 2026-07-28 hat drei Felder eingeführt oder abgeschafft, aus denen sich dieselbe stille Unvollständigkeit ableiten lässt wie aus einem vergessenen Filter — nachrechenbar, aber noch nicht nachgemessen. Fällt einer der drei in freier Wildbahn auf, gehört der Vorfall hierher; bis dahin sind es Regeln mit Herleitung statt mit Narbe.

Das Contributing-Kriterium dieses Repos bleibt davon unberührt: Ein **Vorschlag** von aussen braucht weiterhin einen eingetretenen Schaden. Was hier über die tiefere Latte kommt, ist eine Protokolländerung, die alle 42 Server des Portfolios gleichzeitig betrifft — nicht eine plausible Empfehlung.

**Geltungsbereich.** Regel 7 gilt unabhängig von der Spec-Version; instabile Sortierung zerlegt Pagination auch auf 2025-06-18. Dasselbe gilt für die Regeln 10 bis 14 und für alles vor Regel 7. Die Regeln 8 und 9 setzen 2026-07-28 voraus — `ttlMs`/`cacheScope` auf den List-Responses und MRTR (`resultType: "input_required"`) existieren vorher nicht. Wer einen Server der Wave D oder ein eingefrorenes Repo prüft, hakt sie als nicht anwendbar ab, statt sie zu erfüllen.

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

Zurück zur ersten Gruppe: Diese Regel hat wieder einen Vorfall hinter sich, keine Herleitung — denselben wie der Zusatz zu Regel 1, von der anderen Seite her.

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

**Drei Details aus der Umsetzung**, die in [`amtsblatt-mcp` 0.22.0](https://github.com/malkreide/amtsblatt-mcp/blob/main/SECURITY.md#suggestions-not-silent-widening-arch-003) aufgefallen sind und je einen eigenen Test tragen:

1. **Zu kurze Vorschläge verwerfen.** Unter etwa vier Zeichen matcht ein Präfix den halben Bestand — das ist kein nächster Schritt, sondern die Leermenge in anderer Form. «AG» ist kein Suchbegriff.
2. **Das Resultat sagt, dass nicht verbreitert wurde.** Ohne diesen Satz muss das Modell aus dem Schweigen schliessen, und es schliesst falsch: Eine Antwort ohne Treffer sieht aus wie eine, in der schon alles versucht wurde. Der Hinweis nach Regel 3 trägt beides — was nicht getan wurde und was der Aufrufer als Nächstes tun kann.
3. **Der breiteste Vorschlag kommt zuletzt.** Die Reihenfolge ist die empfohlene Reihenfolge; wer den breitesten zuerst nennt, bekommt ihn zuerst probiert und damit den unschärfsten Treffer.

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

Genau so ist der Belegfall entstanden: `amtsblatt-mcp` hatte die zweite Hälfte lange vor der ersten (`test_no_search_tool_widens_the_callers_term`, ein Upstream-Request mit unverändertem Begriff) — und war damit nachweislich unschädlich und nachweislich nutzlos. Eine Hälfte allein liest sich wie Disziplin und ist keine.

Der Zähler auf der Route ist der eigentliche Prüfgegenstand und darum bewusst offline: Er misst, was rausgegangen ist, nicht was zurückkam. Ein Live-Test kann das nicht — dort ist eine Suche mit einem Treffer von einer Suche mit einem nachgereichten Ersatz-Begriff nicht zu unterscheiden. Genau deshalb greift hier ausnahmsweise der Mock: Prüfgegenstand ist das eigene Verhalten des Servers, nicht eine Annahme über die Quelle.

## Regel 11 — Die Leermenge trägt die Anfrage, die sie erzeugt hat

Regel 3 verlangt auf der Leermenge einen nächsten Schritt. Diese Regel verlangt die andere Hälfte derselben Auskunft: **womit** nichts gefunden wurde. Ein leeres Tool-Result trägt die effektiv abgesetzte Anfrage — Scope, Filter, Limits, so wie sie rausgegangen sind —, nicht bloss `[]` und einen Hinweistext.

Der Grund ist die Leitfrage dieses Skills, wörtlich genommen. «Nichts da» und «falsch gefragt» unterscheiden sich in genau einer Sache: in der Anfrage. Steht die nicht im Resultat, hat das Modell zum Unterscheiden nichts in der Hand — und tut dann, was Regel 4 beschreibt, nur ohne dass es diesmal eine Description dazu eingeladen hätte.

**Der Belegfall stammt aus einem anderen Werkzeug, hat aber dieselbe Form.** Eine Prüfstufe meldete für 38 von 42 Servern wortgleich «lief 6s, stürzte nicht ab, kündigte nichts an». Der Befund führte nicht mit, *was stattdessen zu sehen war*. Damit waren «schweigt» und «formuliert es anders» dieselbe Meldung. Eine Prüfung, die fast überall dieselbe Zeile schreibt, wird weggeklickt — und übersieht dann den einen echten Fall, hier einen Server, der überhaupt nicht startete. Nach der Behebung, also mit dem tatsächlich Beobachteten im Befund, standen 26 bestätigte Fälle und 16 mit belegtem Grund da, wo vorher 38 identische Zeilen standen.

Zwei Eigenschaften folgen daraus, und die zweite ist die schärfere:

1. **Die Leermenge sagt, was rausging.** Ohne das ist sie nicht überprüfbar, sondern nur lesbar.
2. **Uniformität ist selbst der Befund.** Ein Feld, das auf fast jeder Antwort denselben Text trägt, transportiert kein Bit. Es sieht aus wie Sorgfalt und ist Tapete — und der eine Fall, der anders liegt, verschwindet darin. Das ist der Grund, warum Regel 3 einen *konkreten* Hinweis verlangt und warum «konkret» ohne die mitgeführte Anfrage nicht prüfbar ist.

**Was «effektiv» heisst:** die Werte, wie sie rausgegangen sind, nicht wie sie hereinkamen. Der Unterschied ist genau Regel 1. Dort wird ein weggelassener Scope-Parameter zur Laufzeit zum vollen Scope aufgelöst — **best effort**, das heisst: Die Auflösung darf ausfallen, und dann läuft die Suche unerweitert weiter. Die Leermenge danach liest sich wie «im ganzen Bestand nichts», während ein Teilausschnitt durchsucht wurde. Diese stille Rückstufung ist im Resultat erst sichtbar, wenn es die tatsächlich gesendeten Scope-IDs führt. Regel 1 sendet den vollen Scope, Regel 11 weist im Resultat nach, dass er gesendet wurde.

```python
# ✗ Die Antwort sagt, dass nichts kam. Worauf sich das Nichts bezieht, steht nirgends.
return SearchResult(returned=0, hint=_EMPTY_HINT, entries=[])

# ✓ Dieselbe Leermenge, mit der Anfrage, die sie erzeugt hat.
return SearchResult(
    returned=0,
    hint=_EMPTY_HINT,
    entries=[],
    request=EffectiveRequest(
        search_term=term,
        scope_ids=scope_ids,                 # aufgelöst, nicht das None des Aufrufers
        scope_source="resolved" if widened else "upstream_default",
        fields=sorted(requested),
        limit=max_results,
    ),
)
```

`scope_source` ist bereits ein Anwendungsfall von Regel 12: Der Wert unterscheidet «vom Aufrufer gewählt», «vom Server aufgelöst» und «Default der Quelle, weil die Auflösung ausfiel» — drei Sachverhalte, die als eine Liste von IDs identisch aussehen.

**Abgrenzung, drei Teile.** Erstens: **Credentials gehören nicht ins Echo.** Mitgeführt werden Scope, Filter und Limits, nicht die Authentisierung — ein Request-Echo mit dem API-Key darin ist ein Leck, und über ein zu weites `cacheScope` (Regel 8) ein weitergereichtes. Zweitens: Das Echo gehört **ins Tool-Result**, nicht nur ins Log; das Log liest das Modell nicht, und das ist dasselbe Argument wie bei Regel 3. Drittens: **Die Rückfrage trägt kein Echo.** Ein `input_required` nach Regel 9 hat keine Anfrage abgesetzt, also hat es keine zu berichten — dieselbe Begründung, aus der dort `entries` fehlt und nicht leer ist. Der Fehlerkanal dagegen trägt es sehr wohl: Was versucht wurde, ist dort der nächste Schritt (Regel 3, Abgrenzung, und Regel 6).

Pflicht ist das Echo auf der Leermenge. Auf einer Antwort mit Treffern ist es billig und schadet nicht — und sobald überhaupt eine Verengung angewendet wurde, verlangt `FID-001` es ohnehin.

**Nachweis / Test.** Ein **Paar**, aus demselben Grund wie bei Regel 10 — und offline aus demselben Grund: Prüfgegenstand ist, was der Server sendet, nicht was die Quelle hat.

```python
@respx.mock
async def test_the_empty_result_carries_what_actually_went_out():
    """Regel 11, Hälfte 1: Das Echo stimmt mit dem Request überein, nicht mit der Eingabe."""
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=_EMPTY_PAGE)
    )
    result = await search_tool(term="Quellensteuer")        # ohne Scope aufgerufen
    assert result.entries == []
    sent = route.calls[-1].request.url.params
    assert result.request.scope_ids == [int(i) for i in sent.get_list("ScopeIds")]
    assert result.request.limit == int(sent["MaxEntryCount"])

@respx.mock
async def test_two_runs_that_went_out_differently_read_differently():
    """Regel 11, Hälfte 2: Ein Echo, das immer gleich lautet, ist keines."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_EMPTY_PAGE))
    vocabulary = respx.get(VOCABULARY_URL).mock(
        return_value=httpx.Response(200, json=_SCOPES)
    )
    widened = await search_tool(term="Quellensteuer")

    vocabulary.mock(side_effect=httpx.ConnectError("Vokabular nicht erreichbar"))
    degraded = await search_tool(term="Quellensteuer")       # Regel 1, best effort fällt aus

    assert widened.entries == degraded.entries == []
    assert widened.request != degraded.request, (
        "beide Leermengen lesen sich gleich — das Echo ist eine Konstante"
    )
    assert degraded.request.scope_source == "upstream_default"
```

Wie bei Regel 10 ist keine Hälfte für sich brauchbar. Ohne die erste besteht ein Server die zweite mit einem Echo, das zwar variiert, aber nicht das beschreibt, was rausging. Ohne die zweite besteht ein Server die erste mit einem fest verdrahteten Echo — und das ist genau der Zustand der 38 wortgleichen Zeilen, gegen den diese Regel geschrieben ist.

## Regel 12 — Abwesenheit ist dreiwertig: nicht erhoben / erhoben und leer / zurückgehalten

Regel 11 stellt die Leitfrage an die Antwort als ganze. Am einzelnen Feld stellt sie sich noch einmal — und wird dort fast immer mit einem einzigen `null` beantwortet, das drei verschiedene Sachverhalte zusammenfasst:

| Zustand | Was er heisst | Was der Aufrufer daraufhin tun kann |
|---|---|---|
| **nicht erhoben** | Der Server hat den Wert nicht abgefragt — Feld-Flag aus (Regel 2), Projektion, Unter-Abfrage nicht gelaufen | erneut abfragen, diesmal mit dem Feld |
| **erhoben und leer** | Die Quelle wurde gefragt und führt keinen Wert | die Aussage steht: dieser Datensatz hat keinen |
| **zurückgehalten** | Der Wert existiert, wird aber nicht ausgeliefert — Allow-Liste, Personendaten, Berechtigung | über dieses Tool nicht erreichbar; nachfassen ist zwecklos |

Ein `null` für alle drei ist dieselbe Verwechslung wie eine Leermenge für einen Transportfehler (Regel 3, Abgrenzung), nur ein Feld statt ein Result gross. Folgenreich ist sie, weil «nicht erhoben», gelesen als «hat keinen», eine Tatsachenbehauptung über einen Datensatz ist, die niemand gemessen hat.

**Belegfall, im Review abgefangen statt ausgeliefert.** Im Portfolio-Manifest heisst `null` ausdrücklich «nicht erhoben» und nicht «hat keins» — und die Semantik ist bewusst **pro Feld verschieden**: Ein fehlendes `pypi_dist` ist ein Abbruch, ein fehlendes `start_event` ein Rückfall auf die Vorgabe. Der Unterschied hat einen Grund: Bei `pypi_dist` färbt Stillschweigen alles grün. Genau darauf lief der Review-Befund hinaus — ein **umbenanntes** Feld hätte jeden Eintrag zur «begründeten Auslassung» gemacht: nichts gemessen, Exit 0.

Das ist Regel 6 am Feld statt an der Hülle, und die Parallele trägt bis in den Code: `payload.get("servers", [])` macht aus einer Strukturänderung eine Leermenge, `entry.get("pypi_dist")` aus einer Umbenennung eine Reihe begründeter Auslassungen. Beide Male ist der Rückfallwert eines Lookups die ganze Ursache.

Daraus die zwei Hälften:

1. **Der dritte Wert wird gesetzt, nicht abgeleitet.** «Nicht erhoben» entsteht an der Stelle, die entschieden hat, nicht zu erheben — nie als Default eines Lookups. Ein Schlüssel, der fehlt, obwohl er erhoben werden sollte, ist ein Schema-Fehler nach Regel 6 und gehört in den Fehlerkanal.
2. **Die Bedeutung steht am Feld, samt Handlungsanweisung.** Wer ein dreiwertiges Feld einführt, dokumentiert dort, was der dritte Wert bedeutet **und** was der Aufrufer daraufhin tun muss. Eine hausweite Konvention «`null` = unbekannt» genügt nicht: Sie verdeckt gerade das, worauf es ankommt — dass Stillschweigen bei einem Feld einen Abbruch verlangt und beim nächsten folgenlos ist.

```python
# ✗ Drei Sachverhalte, ein Wert — und der dritte entsteht aus Versehen.
#   Wird `pypi_dist` upstream umbenannt, ist ab sofort jeder Eintrag
#   «hat keins», nichts ist gemessen, und der Lauf endet mit Exit 0.
return {"pypi_dist": entry.get("pypi_dist")}

# ✓ Der Zustand wird entschieden und benannt; ein unerwartet fehlender
#   Schlüssel ist ein Fehler, kein Zustand.
class FieldValue(BaseModel):
    state: Literal["present", "empty_in_source", "not_collected", "withheld"]
    value: str | None = None

def pypi_dist_of(entry: dict, *, collected: bool) -> FieldValue:
    if not collected:
        return FieldValue(state="not_collected")       # gesetzt, wo entschieden wurde
    if "pypi_dist" not in entry:
        raise UpstreamSchemaError(                     # Regel 6, am Feld
            f"'pypi_dist' fehlt. Vorhandene Schlüssel: {sorted(entry)[:10]}"
        )
    return FieldValue(state="present", value=entry["pypi_dist"]) \
        if entry["pypi_dist"] else FieldValue(state="empty_in_source")
```

Und die Dokumentation am Feld, die den Unterschied trägt, den keine Konvention tragen kann:

```python
pypi_dist: FieldValue = Field(description=(
    "PyPI-Distribution. state='not_collected' heisst NICHT «hat keine»: dann "
    "wurde nicht gemessen, und der Aufrufer bricht ab, statt den Eintrag als "
    "geprüft zu zählen. state='empty_in_source' heisst, die Quelle führt keine."
))
start_event: FieldValue = Field(description=(
    "Startmarker. state='not_collected' fällt hier bewusst auf die Vorgabe "
    "zurück — anders als bei `pypi_dist` kostet Stillschweigen hier nichts. "
    "Dass beide Felder dasselbe `null` und zwei verschiedene Pflichten haben, "
    "ist der Grund, warum das hier und nicht in einer Konvention steht."
))
```

**Nachweis / Test.** Wieder ein Paar, wieder offline — Prüfgegenstand ist die eigene Kodierung, nicht der Bestand der Quelle:

```python
@respx.mock
async def test_a_field_that_was_not_requested_is_not_reported_as_absent():
    """Regel 12, Hälfte 1: «nicht gefragt» und «gefragt und leer» sind zwei Werte."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_PAGE))
    lean = await search_tool(term="Quellensteuer", fields=["Terminus"])
    assert lean.entries[0].definition.state == "not_collected"
    full = await search_tool(term="Quellensteuer", fields=["Terminus", "Definition"])
    assert full.entries[0].definition.state in {"present", "empty_in_source"}

@respx.mock
async def test_a_renamed_upstream_key_is_a_finding_not_an_omission():
    """Regel 12, Hälfte 2: Der dritte Wert wird gesetzt, nicht gefunden."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_PAGE_RENAMED))
    with pytest.raises(UpstreamSchemaError):
        await search_tool(term="Quellensteuer", fields=["Terminus", "Definition"])
```

Ohne die zweite besteht ein Server die erste, der jedes Feld als `not_collected` ausweist — er hat nie etwas gemessen und meldet das formal korrekt. Ohne die erste besteht ein Server die zweite, der die Umbenennung sauber meldet und trotzdem «nicht gefragt» und «nichts vorhanden» in dasselbe `null` legt. Das ist die Testform aus den Regeln 9 und 10: Die Trennung wird in beide Richtungen assertiert.

## Regel 13 — Der Feldname ist Teil des Vertrags, samt Schreibweise

Regel 6 fragt, ob der Schlüssel **da** ist. Diese Regel fragt das, was direkt daneben liegt und genauso still ausfällt: ob er da ist **in der Schreibweise, die der Code liest**.

Belegfall (3.8.2026, [`www.bista.zh.ch`](https://www.bista.zh.ch)): Der Code las `r["Schulgemeinde"]`, die Quelle lieferte `schulgemeinde`. Kein Fehler, keine Exception, kein Log-Eintrag — eine leere Trefferliste mit der Meldung «Schulgemeinde nicht gefunden». Das ist dieselbe Konfabulations-Einladung wie Regel 3, aus einer neuen Richtung: **ein Ausfall, der wie eine Antwort aussieht.**

Der Umfang entscheidet über die Behebung. Betroffen waren 4 von 6 genutzten Endpunkten derselben Quelle, und zwei davon mischen die Schreibweise **innerhalb einer Kopfzeile** (`gebiet_Bezeichnung`, `staatsangehoerigkeit_ISO2_Code`). Damit fällt der naheliegende Handgriff aus: Eine Schreibweise fest zu verdrahten hätte beim nächsten Wechsel dasselbe Loch gerissen, nur in die andere Richtung — und die Quelle hat ihn innerhalb eines Bestands bereits vollzogen.

Muster: **an der Parse-Grenze normalisieren, einmal, für alle Leser.**

```python
# ✗ Jeder Leser trägt seine eigene Annahme über die Kopfzeile. Ein Wechsel
#   upstream trifft sie einzeln, und keiner von ihnen meldet etwas.
rows = list(csv.DictReader(io.StringIO(resp.text)))
hits = [r for r in rows if r.get("Schulgemeinde", "") == gemeinde]

# ✓ Eine Stelle kennt die Schreibweise, und danach kennt sie niemand mehr.
rows = [_normalise_keys(r) for r in csv.DictReader(io.StringIO(resp.text))]
hits = [r for r in rows if r.get("schulgemeinde", "") == gemeinde]
```

**Nur der Schlüssel, nie der Wert.** Die Normalisierung fasst Feldnamen an, nicht Feldinhalte. Ein Wert kleinzuschreiben, um einen Vergleich «robuster» zu machen, ist eine Recall-Verbreiterung, die niemand angefordert hat — sie gehört unter Regel 1 begründet und nicht in eine Hilfsfunktion an der Parse-Grenze.

**Zwei Schlüssel, die zusammenfallen, sind ein Befund.** `{k.lower(): v for k, v in row.items()}` verliert stillschweigend einen von zwei Schlüsseln, die sich nur in der Schreibweise unterscheiden — und der Verlust sieht aus wie eine Zeile, die das Feld nie hatte. Das ist `payload.get("servers", [])` in klein: Der Rückfallwert einer Operation wird zur ganzen Ursache. Die Kollision gehört in den Fehlerkanal, wie jede andere Strukturabweichung.

**Abgrenzung gegen Regel 6, und sie ist der Grund für eine eigene Regel.** Regel 6 kennt genau zwei Ausgänge: gefunden oder Schema-Fehler. Auf eine Schreibweisen-Abweichung angewandt, liefert sie den lauten Ausgang — richtig gegenüber dem stillen Nullbefund und trotzdem falsch, denn das Feld **ist** da. Ein Server nach Regel 6 allein hätte am 3.8.2026 auf 4 von 6 Endpunkten einen Upstream-Defekt gemeldet, den es nicht gab. Die beiden Regeln stehen deshalb in einer Reihenfolge und nicht in Konkurrenz: **erst normalisieren, dann bestätigen.** Nach der Normalisierung gilt Regel 6 unverändert und mit voller Schärfe — ein Schlüssel, der dann noch fehlt, fehlt wirklich. Wer normalisiert, *statt* zu bestätigen, hat Regel 6 abgeschafft und nicht erfüllt: `.get(k, "")` über einer normalisierten Zeile ist genau der stille Ausfall, mit dem dieser Abschnitt anfängt.

Dieselbe Reihenfolge gilt gegenüber Regel 12: Dort ist ein unerwartet fehlender Schlüssel ein Schema-Fehler und kein Zustand. Das bleibt so — die Normalisierung entscheidet nur, welche Schlüssel als «vorhanden» gelten, nicht, was mit den fehlenden geschieht.

**Warum Mocks das nicht fangen:** aus demselben Grund wie bei den Regeln 5 und 6. Die Fixture kodiert die Kopfzeile, die der Autor angenommen hat. Ein Mock, dessen Header `Schulgemeinde` schreibt, bestätigt den Fehler, statt ihn zu finden — und er tut es umso zuverlässiger, je sorgfältiger er aus der Doku der Quelle abgeschrieben wurde.

**Nachweis / Test.** Ein **Paar**, aus demselben Grund wie bei den Regeln 10 bis 12:

```python
@respx.mock
async def test_the_reader_does_not_care_how_the_header_is_spelled():
    """Regel 13, Hälfte 1: Zwei Schreibweisen, ein Ergebnis."""
    for header in ("Schulgemeinde", "schulgemeinde", "SchulGemeinde"):
        respx.get(CSV_URL).mock(
            return_value=httpx.Response(200, text=f"{header},anzahl\nUster,12\n")
        )
        result = await search_tool(schulgemeinde="Uster")
        assert result.entries, f"{header!r} liefert nichts — Schreibweise verdrahtet"

@respx.mock
async def test_a_genuinely_missing_column_is_still_a_finding():
    """Regel 13, Hälfte 2: Normalisiert wird der Name, nicht der Befund."""
    respx.get(CSV_URL).mock(
        return_value=httpx.Response(200, text="gemeinde,anzahl\nUster,12\n")
    )
    with pytest.raises(UpstreamSchemaError):
        await search_tool(schulgemeinde="Uster")
```

Ohne die zweite besteht ein Server die erste, der jede Abfrage über `.get(k, "")` laufen lässt — er ist gegen jede Schreibweise unempfindlich, weil er gegen jede Kopfzeile unempfindlich ist, und meldet die verschwundene Spalte als Leermenge. Ohne die erste besteht ein Server die zweite, der eine Schreibweise verdrahtet und die andere korrekt als Schema-Fehler meldet — genau der Zustand, den der Belegfall als «Upstream-Defekt» ausgewiesen hätte, obwohl die Quelle in Ordnung war.

**`@pytest.mark.live`.** Die gemischte Kopfzeile ist nur an der echten Antwort zu sehen — der Mock hat sie per Konstruktion nicht. Ein Canary über alle genutzten Endpunkte, der die Rohheader gegen ihre normalisierte Form hält, meldet den nächsten Wechsel als Information statt als Ausfall:

```python
@pytest.mark.live
@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_the_raw_header_is_reported_not_assumed(endpoint):
    raw = await client.raw_header(endpoint)
    assert raw, f"{endpoint}: keine Kopfzeile"
    normalised = [k.lower() for k in raw]
    assert len(set(normalised)) == len(normalised), (
        f"{endpoint}: {raw} fällt nach der Normalisierung zusammen"
    )
```

## Regel 14 — Eine Zahlenspalte, die keine Zahlen enthält

Quellen unterdrücken kleine Fallzahlen aus Datenschutzgründen und schreiben statt einer Zahl einen Bereich: «1 bis 5», «<5». Dazu kommen «NULL» und die leere Zelle. Das ist kein Randfall, sondern eine Eigenschaft amtlicher Statistik — gemessen am 3.8.2026 auf [`www.bista.zh.ch`](https://www.bista.zh.ch): **18.6 %** einer Sek-I-Tabelle (13902 Zeilen), **18.1 %** einer zweiten (62684 Zeilen), **1.0 %** «NULL» in einer dritten (35903 Zeilen).

Die Bewertung ist der Kern der Regel, und der mittlere Ausgang ist der, der überrascht:

| Umgang | Was er kostet |
|---|---|
| `int("1 bis 5")` | Absturz. Laut, schlecht — aber ehrlich: Der Aufrufer bekommt keine Zahl und weiss es |
| als `0` zählen | Die Summe bleibt plausibel, ist still zu tief und durch nichts als falsch erkennbar. **Schlimmer als der Absturz** |
| ausnehmen und **kennzeichnen** | richtig |

**Eine Summe, aus der ein Fünftel der Zeilen stillschweigend fehlt, ist keine Summe — sie ist eine Untergrenze, die sich als Summe ausgibt.**

Dass die Null schlechter abschneidet als der Absturz, ist die ganze Ordnung dieser Tabelle: Ein Absturz kostet einen Vorfall, eine stille Null kostet jede Entscheidung, die danach auf der Zahl beruht. Es ist die Fehlerklasse dieses Skills, angewandt auf einen Skalar statt auf eine Trefferliste — HTTP 200, wohlgeformtes JSON, eine Zahl, die niemand als falsch erkennt.

```python
# ✗ Zwei Zeilen, zwei Fehler. Die erste stürzt ab, die zweite ist schlimmer.
total = sum(int(r["anzahl"]) for r in rows)
total = sum(int(r["anzahl"]) if r["anzahl"].isdigit() else 0 for r in rows)

# ✓ Ausnehmen und kennzeichnen — die Zahl der ausgenommenen Zeilen ist Teil
#   des Resultats, nicht ein Detail im Log.
counted = [_parse_count(r.get("anzahl")) for r in rows]
total = sum(n for n in counted if n is not None)
suppressed = sum(1 for n in counted if n is None)
note = _suppression_note(suppressed, len(rows))   # None, wenn es keine gibt
```

**Der Hinweis gehört ins Tool-Result**, aus demselben Grund wie bei Regel 3 — das Log liest das Modell nicht. Und er trägt die **tatsächlichen Zahlen** (`{suppressed} von {total}`), nicht eine Konstante: Ein Satz, der unter jeder Tabelle gleich lautet, ist die Tapete aus Regel 11 und sagt nichts über *diese* Summe.

**Abgrenzung gegen Regel 12, und sie ist die Naht zwischen beiden.** Regel 12 ordnet die **einzelne Zelle** ein, und ein unterdrückter Wert ist dort bereits benannt: `withheld` — der Wert existiert, wird aber nicht ausgeliefert. Was Regel 12 nicht beantwortet, ist die Frage eine Verarbeitungsstufe später: **was eine Summe, eine Quote oder eine Rangfolge mit diesen Zellen tut.** Ein Server kann die drei Zustände am Feld mustergültig auseinanderhalten und sie in der nächsten Zeile mit `or 0` wieder zusammenfallen lassen. Regel 12 hält sie auseinander, Regel 14 hält sie auseinander *im abgeleiteten Wert* — und verlangt, dass die Ableitung sagt, wie viele Zeilen sie nicht enthält.

Ebenso wenig deckt Regel 3 den Fall: Sie verlangt einen nächsten Schritt auf der **Leermenge**. Hier ist die Trefferliste voll, und falsch ist eine Zahl darin.

**Warum Mocks das nicht fangen:** dieselbe Antwort wie bei den Regeln 5, 6 und 13, mit einem Zusatz. Die Fixture enthält die Werte, die der Autor erwartet hat, und «1 bis 5» erwartet niemand, der die Feldbeschreibung «Anzahl (Integer)» gelesen hat. Der Zusatz ist der Anteil: Eine handgeschriebene Fixture mit einer unterdrückten Zeile unter zwanzig bildet 5 % ab, gemessen sind 18.6 % — die Grössenordnung des Fehlers ist am Mock prinzipiell nicht abzulesen. Sie kommt aus der Probe (siehe `mcp-data-source-probe`, Abschnitt 1.2c) oder gar nicht.

**Nachweis / Test.** Wieder ein Paar, und die zweite Hälfte ist die, die den trivialen Server aussortiert:

```python
@respx.mock
async def test_a_suppressed_value_is_excluded_and_declared():
    """Regel 14, Hälfte 1: ausgenommen, gezählt und im Resultat genannt."""
    respx.get(CSV_URL).mock(return_value=httpx.Response(
        200, text="gemeinde,anzahl\nUster,12\nBonstetten,1 bis 5\nAffoltern,NULL\n"
    ))
    result = await counts_tool()
    assert result.total == 12, "unterdrückte Zeile in der Summe — als 0 gezählt?"
    assert result.suppressed == 2
    assert "2 von 3" in result.note, "der Hinweis nennt die Zahl nicht"

@respx.mock
async def test_a_clean_table_carries_no_note_and_loses_no_row():
    """Regel 14, Hälfte 2: Der Hinweis ist eine Messung, keine Floskel."""
    respx.get(CSV_URL).mock(return_value=httpx.Response(
        200, text="gemeinde,anzahl\nUster,12\nBonstetten,7\n"
    ))
    result = await counts_tool()
    assert result.total == 19 and result.suppressed == 0
    assert result.note is None, "Hinweis ohne Anlass — er trägt kein Bit mehr"
```

Ohne die zweite besteht ein Server die erste, der jede Zeile für unterdrückt hält: Seine Summe ist 0, sein Hinweis steht immer da, und beides ist formal korrekt. Ohne die erste besteht ein Server die zweite, der auf einer sauberen Tabelle richtig rechnet und auf einer unterdrückten still zu tief summiert. Das ist die Testform aus den Regeln 9 bis 12 — die Trennung wird in beide Richtungen assertiert.

**`@pytest.mark.live`.** Der Anteil unterdrückter Zeilen ist eine Eigenschaft der Quelle und bewegt sich. Als Canary taugt er trotzdem, mit einer Ober- und einer Untergrenze statt einer Zahl: Fällt er auf null, hat entweder die Quelle ihre Praxis geändert — oder der eigene Parser hat angefangen, etwas als Zahl zu lesen, was keine ist.

```python
@pytest.mark.live
async def test_the_suppressed_share_stays_in_the_expected_band():
    result = await counts_tool()
    share = result.suppressed / result.rows
    assert 0.05 < share < 0.40, (
        f"{share:.1%} unterdrückt — Quelle umgestellt oder Parser zu grosszügig?"
    )
```

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
- [ ] Vergleiche auf strukturierte Felder assertieren exakte Gleichheit, keine Teilzeichenkette und kein Präfix (Regel 5)
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
- [ ] Die Leermenge trägt die effektiv abgesetzte Anfrage — Scope, Filter, Limits, wie sie rausgingen, nicht wie sie hereinkamen (Regel 11)
- [ ] Zwei Läufe, die verschieden rausgingen, lesen sich im Resultat verschieden — insbesondere der Lauf, in dem die Scope-Erweiterung aus Regel 1 ausgefallen ist (Regel 11)
- [ ] Kein Request-Echo führt Credentials mit, und die MRTR-Rückfrage trägt keines, weil keine Anfrage rausging (Regel 11, Regel 9)
- [ ] Jedes Feld, das fehlen kann, unterscheidet «nicht erhoben», «erhoben und leer» und «zurückgehalten» — nicht ein `null` für alle drei (Regel 12)
- [ ] «Nicht erhoben» wird dort gesetzt, wo entschieden wurde, nie als Rückfallwert eines Lookups; ein unerwartet fehlender Schlüssel endet im Fehlerkanal (Regel 12, Regel 6)
- [ ] Am Feld dokumentiert, was der dritte Wert bedeutet und was der Aufrufer daraufhin tun muss — pro Feld, nicht als hausweite Konvention (Regel 12)
- [ ] Feldnamen werden an der Parse-Grenze normalisiert, einmal für alle Leser; keine Schreibweise steht in einem Leser fest verdrahtet (Regel 13)
- [ ] Nach der Normalisierung wird die Struktur weiterhin bestätigt — normalisieren *und* bestätigen, nicht statt (Regel 13, Regel 6)
- [ ] Zwei Schlüssel, die nach der Normalisierung zusammenfallen, enden im Fehlerkanal statt in einem stillen Überschreiber (Regel 13)
- [ ] Jede Zahlenspalte auf Nicht-Zahlen geprüft — unterdrückte Fallzahlen («1 bis 5», «<5»), «NULL», leere Zelle — und keiner dieser Werte wird als `0` gezählt (Regel 14)
- [ ] Jede Summe, Quote und Rangfolge weist im Tool-Result aus, wie viele Zeilen sie nicht enthält, mit der gemessenen Zahl statt einer Konstante (Regel 14, Regel 11)
- [ ] Gegen die offizielle Oberfläche der Quelle verglichen, jedes Delta erklärt

## Woher diese Regeln stammen

Aus einem einzelnen realen Vorfall: [`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). Der Server sendete `ClassificationIds` nur bei explizitem Aufruf; die API schränkt eine ID-lose Suche auf `VARIA` ein — eine von 23 Klassifikationen. «Quellensteuer» lieferte null Treffer bei mehreren vorhandenen Einträgen, «Pensionskasse» einen statt 21.

Vier Dinge daran sind übertragbar:

1. **33 grüne Offline-Tests haben nichts gefangen** — Mocks können eine falsche Grundannahme prinzipiell nicht widerlegen.
2. **Ein 68-Punkte-Audit war bestanden** — alle Kategorien prüften die Bauweise, keine die Datentreue.
3. **Die eigene Doku hat das Modell zum Konfabulieren gebracht** — siehe Regel 4.
4. **Gefunden hat es ein User mit dem Web-UI daneben** — Ground Truth kommt von aussen, nicht aus der Testsuite.

Regel 6 kam nach einem zweiten Fall dazu: Eine Abfrage der MCP Registry lieferte eine Zeit lang nichts, weil die Felder unter `servers[].server.*` liegen und der Client eine Ebene höher suchte.

Regel 10 und der Zusatz zu Regel 1 kommen aus einem dritten Fall, [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp) — und der ist ausgeliefert gewesen, nicht im Entwurf gefangen. Version 0.20.0 hat einen Vorschlagsmechanismus ausdrücklich abgelehnt und die Ablehnung mit Konkursmeldungen, Betreibungen, Erbschaftsaufrufen und Baueinsprachen begründet: Rubriken, die die Allow-Liste des Servers gerade ausschliesst. Die Begründung stand in beiden `SECURITY`-Dateien, im CHANGELOG und im PR, der die Arbeit abschloss. Aufgefallen ist sie erst im [Re-Audit vom 2026-07-30](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md), das `ARCH-003` weiterhin auf `partial` liess; behoben hat sie 0.22.0.

Zwei Fehler, die sich gegenseitig gedeckt haben. Der eine ist die Begründung ohne erreichbaren Gegenstand — das ist der Zusatz zu Regel 1. Der andere steckt in der Gegenrichtung: Der Vorschlagsmechanismus, den der Check verlangt, ist als Erlaubnis lesbar, die Vorschläge gleich abzufragen — und dann liefert der Server Meldungen unter einem Begriff aus, den niemand gewählt hat. Weil beide Wege in dieselbe Falle laufen, ist die Auflösung keine Wahl zwischen ihnen, sondern die Aufteilung: vorschlagen ja, abfragen nein.

Was daran übertragbar ist: Ein Argument, das für jede beliebige Quelle wortgleich dastünde, ist noch keines — und ein Server, der die halbe Regel erfüllt, ist nachweislich unschädlich und nachweislich nutzlos. `amtsblatt-mcp` hatte den Test «es geht genau ein Request mit dem unveränderten Begriff raus» lange, bevor es überhaupt etwas vorzuschlagen gab.

Regel 11 kommt aus einem vierten Fall, und der liegt ausserhalb dieses Skills: eine Prüfstufe im Portfolio, die für 38 von 42 Server wortgleich «lief 6s, stürzte nicht ab, kündigte nichts an» meldete, ohne mitzuführen, was stattdessen zu sehen war. Der Schaden ist dort gemessen — die 38 identischen Zeilen wurden weggeklickt, und darin ging der eine Server unter, der überhaupt nicht startete; nach der Behebung standen 26 bestätigte Fälle und 16 mit belegtem Grund da. Übertragbar auf das Tool-Result ist die **Form**, nicht derselbe Vorfall: Eine Leermenge ohne die Anfrage, die sie erzeugt hat, ist dieselbe Zeile in anderer Umgebung. Das gehört dazugesagt, weil dieses Repo den Unterschied zwischen gemessen und hergeleitet sonst mitführt — hier ist gemessen worden, aber im Nachbarwerkzeug.

Regel 12 ist der einzige Eintrag dieser Liste, der **im Review abgefangen** wurde statt draussen aufzufallen: ein gültiger Befund an eigenem Code, an dem ein umbenanntes Feld jeden Eintrag zur begründeten Auslassung gemacht hätte — nichts gemessen, Exit 0. Belegt ist damit der Mechanismus, und zwar am laufenden Objekt; nicht belegt ist, dass ihn draussen jemand übersieht. Der Unterschied ist kleiner als der zu einer Herleitung aus der Spec und grösser als keiner, und deshalb steht er hier.

Die Regeln 13 und 14 kommen aus einem fünften Fall, und der ist wie der dritte ausgeliefert gewesen: [`zh-education-mcp`](https://github.com/malkreide/zh-education-mcp) gegen [`www.bista.zh.ch`](https://www.bista.zh.ch), aufgefallen am 3.8.2026. Zweimal dieselbe Form, an zwei verschiedenen Stellen derselben Zeile.

Der eine ist der **Feldname**: Der Code las `r["Schulgemeinde"]`, die Quelle lieferte `schulgemeinde`. Das Ergebnis war keine Exception, sondern eine leere Trefferliste mit der Meldung «Schulgemeinde nicht gefunden» — ein Ausfall, der wie eine Antwort aussieht. Betroffen waren 4 von 6 genutzten Endpunkten, und zwei davon mischen die Schreibweise innerhalb einer Kopfzeile (`gebiet_Bezeichnung`, `staatsangehoerigkeit_ISO2_Code`). Das ist der Grund, warum die Behebung nicht «auf die neue Schreibweise umstellen» heisst, sondern «an der Parse-Grenze normalisieren»: Die Quelle hat den Wechsel innerhalb eines Bestands bereits vollzogen, und die verdrahtete Gegenrichtung wäre dasselbe Loch gewesen.

Der andere ist der **Wert**: Die Quelle unterdrückt kleine Fallzahlen und schreibt «1 bis 5» in eine Spalte, die eine Anzahl heisst. Gemessen 18.6 % und 18.1 % in zwei Tabellen, 1.0 % «NULL» in einer dritten. Übertragbar daran ist die Rangfolge der drei Umgänge, und dass der mittlere überrascht: Der Absturz ist laut und ehrlich, die stille `0` ist beides nicht. Eine Summe, aus der ein Fünftel der Zeilen stillschweigend fehlt, ist keine Summe, sondern eine Untergrenze, die sich als Summe ausgibt.

Was beide mit `termdat-mcp#11` teilen: Keiner der Fälle war ein Fehler im Aufbau des Servers, und keiner hätte sich an einer Fixture zeigen können. Der eine kodiert die Kopfzeile, die der Autor angenommen hat, der andere die Werte, die er erwartet hat.

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

Stand des Katalogs: `mcp-audit` auf `main` — 113 Checks in zwölf Kategorien auf zwei Spec-Baselines, davon sechs in der Kategorie `FID`. Geschnitten ist v2.0.0 (112 Checks); die drei Änderungen, die diese Tabelle zuletzt bewegt haben, stehen drüben unter `[Unreleased]` und sind dort als v2.1.0 eingestuft. Die Zuordnung ist nicht eins zu eins — `FID-003` trägt vier Regeln, `ARCH-020` zwei, Regel 5 braucht zwei Checks und Regel 9 drei. Ohne Check sind seit `FID-006` die Regeln 12, 13 und 14, und Regel 10 bringt mit `ARCH-003` den einzigen **`enforced`** Check dieser Tabelle mit — alle anderen sind `advisory`:

| Regel | Check |
|---|---|
| 1 — Scope-Parameter explizit senden | [`FID-001`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-001.md) — «Scope-Defaults: Filter-Parameter explizit senden, nie erben». **Reichweite:** Der Check verlangt, dass eine bewusst gewählte Einschränkung im Tool-Result **sichtbar** ist. Dass ihre **Begründung** den erreichbaren Scope zitiert — die Rubriken nennen, die das Risiko tragen, und sie in der Scope-Aufzählung nachweisen —, verlangt drüben keiner der 113 Checks; das steht allein hier |
| 2 — Parameter-Gruppen vollständig senden | [`FID-004`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-004.md) — «Teilmengen erben Server-Defaults», im Check als die feinere Ausprägung von `FID-001` geführt |
| 3 — Leermenge trägt einen nächsten Schritt | [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md). Die Abgrenzung gegen Transport- und Autorisierungsfehler steht dort ausdrücklich, mit `HTTP 421` als gemessenem Fall und Querverweis auf `SEC-016`/`SEC-024` |
| 4 — Tool-Description als Halluzinations-Oberfläche | ebenfalls [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md) — der Check trägt beide Hälften: den fehlenden nächsten Schritt und die vorformulierte Ausrede |
| 5 — Syntax in der Description, Recall in den Tests | [`FID-005`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-005.md) für die Syntax, [`FID-002`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-002.md) für den Recall gegen die offizielle Oberfläche. **Reichweite:** Der dritte Teil der Regel — exakte Gleichheit statt Teilzeichenkette beim Vergleich auf ein strukturiertes Feld — wird von keinem der beiden gemessen. Beide lesen die Antwort des Servers; dass eine Zusicherung *über* sie schwächer formuliert ist, als ihr Name behauptet, steht in keinem Check-Kriterium |
| 6 — Antwortstruktur bestätigen, bevor gezählt wird | [`FID-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-006.md) — «Antwortstruktur bestätigen, bevor gezählt wird», `severity: high`, `spec_baseline: beide`, `adoption: advisory`. Belegfall ist derselbe wie oben: MCP Registry, Felder unter `servers[].server.*`, gelesen eine Ebene höher. Fail-Pattern `payload.get("servers", [])`, Pass-Pattern ein `UpstreamSchemaError`, dessen Meldung die **tatsächlich vorhandenen** Schlüssel nennt. **Reichweite:** ausdrücklich keine vollständige Schema-Validierung — geprüft wird nur, was der Code anfasst, und ein zusätzliches optionales Feld upstream lässt den Check grün. Dass Mocks diese Klasse prinzipiell nicht fangen, steht dort als Querverweis auf `DRIFT-004`. `DRIFT-002` («Fallback verengt, erweitert nie») liegt weiterhin daneben, nicht darauf: dort wird ein *anderer* Datensatz geliefert, hier *keiner* |
| 7 — Deterministische Reihenfolge | [`ARCH-020`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-020.md) — «`ttlMs` und `cacheScope` auf List- und Read-Ergebnissen, deterministische Reihenfolge», `spec_baseline: 2026-07-28`, `adoption: advisory`. **Reichweite:** Der Check prüft die Reihenfolge von `tools/list` über Prozessgrenzen hinweg mit `PYTHONHASHSEED=random` — schärfer als das Testrezept oben — und seit seiner Erweiterung auch den Pagination-Schnitt auf Query-Resultaten: zwei aufeinanderfolgende Seiten, leere Schnittmenge **und** vollständige Vereinigung, gegen einen Bestand grösser als eine Seite. Offen bleibt die **Baseline**: `ARCH-020` misst auf `2026-07-28`, der Pagination-Verlust tritt aber auch auf `2025-11-25` auf — er hängt an der Quelle und am Sortierschlüssel, nicht am Protokollstand, und Regel 7 gilt hier ausdrücklich unabhängig von der Spec-Version. Ein Server der alten Baseline wird drüben also nicht dagegen gemessen. Der Check benennt diese Lücke in seiner Description und lässt sie bewusst offen: `spec_baseline` gilt pro Datei, und `beide` würde `ttlMs`/`cacheScope` gegen Server messen, deren Protokoll diese Felder nicht kennt |
| 8 — Ehrliches `ttlMs` | ebenfalls [`ARCH-020`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-020.md) — der Check trägt beide Hälften, samt dem Kriterium «kein Wert oberhalb der Änderungsfrequenz der Quelle» und `cacheScope: "public"` nur über aufruferunabhängigen Inhalten. **Reichweite:** Er misst die fünf `CacheableResult`-Methoden, knüpft `cacheScope` an `data_class` und fragt seit seiner Erweiterung auch die Ableitung für **Datenresultate** ab — aus `source_freshness`, gedeckelt auf die nächste Publikation, unbekannte Kadenz kurz statt komfortabel. Dieses Kriterium ist **bedingt** formuliert: Es greift, «sofern der Server Datenresultate mit `ttlMs` versieht». Ein Datenresultat ganz **ohne** `ttlMs` fällt drüben damit nicht auf — dass eines hingehört, verlangt nur diese Regel |
| 9 — `input_required` ist keine leere Antwort | [`HITL-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/HITL-006.md) — «MRTR statt serverinitiierter Requests», dazu [`ARCH-018`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-018.md) für `resultType` auf allen Results und, seit dessen Erweiterung, [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md) für die Abgrenzung gegen den Null-Treffer. Die Aufteilung steht drüben in beiden Checks ausgeschrieben: `HITL-006` prüft die Retry-Idempotenz und dass `input_required` nicht für gewöhnliche **Fehler** benutzt wird, `FID-003` die Disjunktheit gegen die **Leermenge** — kein `hint` auf einer Rückfrage, kein `inputRequests` auf einem Null-Treffer, und `entries` fehlt bei der Rückfrage, statt leer zu sein. **Reichweite:** Die drei Kriterien in `FID-003` sind doppelt bedingt — auf `2026-07-28` und darauf, dass das Tool `input_required` überhaupt zurückgeben kann; `FID-003` selbst trägt unverändert kein `spec_baseline`. Und dass der beantwortete Retry tatsächlich **Treffer** liefert, verlangt drüben nur der Idempotenz-Test bei `write_capable: true`; für lesende Server steht dieser Nachweis allein hier |
| 10 — Vorschlagen ist nicht Erweitern | [`ARCH-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-003.md) — «‹Not Found›-Anti-Pattern: Heuristiken statt leerer Antworten», `severity: medium`, `applies_when: always`, ohne `adoption`-Feld und damit **`enforced`**. Der Check ist der Grund für diese Regel und zugleich ihre Gegenprobe: Er verlangt auf der Leermenge einen Fuzzy-Match **oder** einen Vorschlagsmechanismus plus `match_type`, und der Vorschlags-Arm erfüllt beide Seiten. **Reichweite:** Was drüben fehlt, ist die Disjunktheit — beide Modi lesen die **Antwort**, keiner misst den **Request**. Kein Kriterium verbietet, den Vorschlag gleich abzufragen und seine Treffer unter `results` zu mischen; das Pass-Pattern des Checks tut es sogar (`match_type: "fuzzy"` auf einer gemeinsamen Liste). Der Zähler auf der Upstream-Route steht bis auf Weiteres allein hier — als dritter Modus vorgeschlagen in [`mcp-audit-skill#102`](https://github.com/malkreide/mcp-audit-skill/issues/102), mit §2.5 beantwortet (Frage 2: Reichweite, nicht neue Regel). Nebenan liegt [`DRIFT-002`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/DRIFT-002.md) («Fallback verengt, erweitert nie») — dieselbe Form eine Ebene weiter: dort wird ein anderer *Datensatz* substituiert, hier eine andere *Abfrage* |
| 11 — Die Leermenge trägt die Anfrage | [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md) für die Leermenge selbst, dazu [`FID-001`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-001.md) für die eine Hälfte, die drüben schon steht: Eine **bewusst gewählte** Einschränkung muss im Tool-Result sichtbar sein. **Reichweite:** Das deckt die Verengung ab, die jemand gewählt hat — nicht die, die *passiert* ist. Der Anlassfall dieser Regel ist die ausgefallene Scope-Erweiterung aus Regel 1: Sie steht in keinem Argument, niemand hat sie gewählt, und kein Kriterium von `FID-001` misst sie. Ebenso wenig geprüft ist die zweite Hälfte — dass zwei verschieden abgesetzte Läufe sich verschieden lesen. Ein `hint`, der auf jeder Leermenge derselbe ist, erfüllt `FID-003` heute; dass er damit kein Bit trägt, steht allein hier |
| 12 — Abwesenheit ist dreiwertig | **Kein Check deckt sie ab** — die erste von drei Zeilen, für die das gilt. Am nächsten liegen [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md) und [`ARCH-018`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-018.md): Beide trennen Zustände eines **Results** — Leermenge, Fehler, `resultType` —, keiner die Zustände eines **Feldes**. Am nächsten in der Form liegt [`FID-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-006.md), und der Abstand ist genau eine Ebene: `payload.get("servers", [])` ist drüben ein Fail-Pattern, `entry.get("pypi_dist")` ist keines. **Reichweite:** Ob daraus eine Erweiterung von `FID-006` wird oder ein eigener Check, ist nach [§2.5 «Reichweite vor neuer Regel»](https://github.com/malkreide/mcp-audit-skill/blob/main/SKILL.md) zu entscheiden und hier **nicht** entschieden — anders als bei Zeile 10, wo die drei Fragen beantwortet unten stehen. Bis dahin ist das ein fehlender Check und kein benannter Rand, und es steht so da |
| 13 — Der Feldname samt Schreibweise | **Kein Check deckt sie ab.** Am nächsten liegt [`FID-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-006.md), und der Abstand ist nicht eine Ebene wie bei Zeile 12, sondern eine Fallunterscheidung: Sein Fail-Pattern ist `payload.get("servers", [])`, sein Pass-Pattern der `UpstreamSchemaError`, dessen Meldung die tatsächlich vorhandenen Schlüssel nennt. Auf eine Schreibweisen-Abweichung angewandt ist das Pass-Pattern die **richtige Diagnose mit der falschen Folge** — es meldet einen Upstream-Defekt, den es nicht gibt, für ein Feld, das die Quelle liefert. Ein Server, der nach `FID-006` gebaut ist und keine Normalisierung hat, besteht den Check heute und wäre am 3.8.2026 auf 4 von 6 Endpunkten rot geworden. **Reichweite:** Kein Kriterium des Katalogs verlangt, dass Feldnamen an genau einer Stelle normalisiert werden, und keines verbietet die verdrahtete Schreibweise im einzelnen Leser. Ob daraus eine Erweiterung von `FID-006` wird oder ein eigener Check, ist nach [§2.5 «Reichweite vor neuer Regel»](https://github.com/malkreide/mcp-audit-skill/blob/main/SKILL.md) zu entscheiden und hier **nicht** entschieden — wie bei Zeile 12 |
| 14 — Eine Zahlenspalte ohne Zahlen | **Kein Check deckt sie ab.** Am nächsten liegt [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md): Der Hinweis auf die ausgenommenen Zeilen ist genau der «nächste Schritt im Tool-Result», den der Check verlangt — nur verlangt er ihn auf der **Leermenge**, und hier ist die Trefferliste voll und eine Zahl darin falsch. Daneben liegt [`ARCH-018`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-018.md), der Zustände eines Results trennt, nicht Werte in einer Spalte. **Reichweite:** Kein Kriterium misst einen **abgeleiteten** Wert — Summe, Quote, Rangfolge — gegen die Zeilen, die nicht in ihn eingegangen sind. Die Rangfolge der drei Umgänge (Absturz ehrlich, stille `0` schlimmer, ausnehmen und kennzeichnen richtig) steht in keinem Check-Kriterium; ein Server, der `or 0` rechnet, besteht drüben alles. Auch diese Zuordnung ist nach §2.5 offen und hier nicht entschieden |

Wer nach den Regeln 1–5 baut, besteht die `FID`-Checks; Regel 6 liegt seit `FID-006` ebenfalls dort, allerdings `advisory` — der Check verlässt diesen Stand erst nach dem ersten Portfolio-Durchlauf, der zeigt, wie viele Server die Antwortstruktur überhaupt bestätigen. Die Regeln 7–9 laufen über `ARCH-020`, `HITL-006`, `ARCH-018` und die `2026-07-28`-Kriterien von `FID-003` und sind ebenfalls durchweg `advisory` — sie blockieren also nicht, sie werden gezählt. Regel 10 ist die Ausnahme: `ARCH-003` ist `enforced` und gilt `always`, ein Verstoss dagegen blockiert. Regel 11 liegt zur Hälfte auf `FID-001` und `FID-003`, die Regeln 12, 13 und 14 auf keinem Check — was je Zeile offen bleibt, steht dort unter «Reichweite», und bei diesen drei Zeilen ist es ausdrücklich eine Lücke und kein Rand.

**Warum die Zeilen 7–9 nicht in `FID` liegen:** Die drei Regeln kommen aus der Spec, und der Katalog ordnet Spec-Checks nach dem Ort der Änderung ein — Caching und Reihenfolge nach `ARCH`, MRTR nach `HITL`. Die Datentreue-Hälfte davon stand hier bis zuletzt als offen und ist inzwischen abgedeckt — aber nicht durch neue `FID`-Checks: `ARCH-020` hat den Pagination-Schnitt und die `ttlMs`-Ableitung in sich aufgenommen, statt ein `FID-007` zu eröffnen, weil beides an denselben zwei Grössen hängt wie der bestehende Check; und die Disjunktheit gegen den Null-Treffer ist nach `FID-003` gegangen, weil sie an der Leermenge hängt und nicht am Rückfrageprotokoll.

**Und warum Zeile 10 nicht:** Aus einem anderen Grund, und die Frage ist inzwischen beantwortet statt offen. `ARCH-003` ist älter als die `FID`-Kategorie — er stammt aus den ursprünglichen 68 Checks, `FID` entstand erst danach aus `termdat-mcp#11` — und beschreibt die Leermenge aus der Perspektive des **Antwortformats**: Gibt es einen Mechanismus, trägt die Antwort `match_type`, ist der Hinweis handlungsfähig. Die Datentreue-Hälfte liegt eine Ebene daneben, weil sie nicht an der Antwort hängt, sondern am **Request**: Ist der Vorschlag abgefragt worden?

Der Katalog hat für diese Frage ein eigenes Verfahren, [§2.5 «Reichweite vor neuer Regel»](https://github.com/malkreide/mcp-audit-skill/blob/main/SKILL.md), drei Fragen in fester Reihenfolge. Beantwortet:

1. *Gibt es den Check, aber `applies_when` schliesst den Fall aus?* Nein — `ARCH-003` gilt `always`.
2. *Gibt es den Check, aber seine Verification prüft die richtige Sache am zu kleinen Umfang?* **Ja, hier liegt es.** Beide Modi von `ARCH-003` lesen die **Antwort**; kein Modus misst, was rausgegangen ist. Ein Server, der jeden Vorschlag still selbst absucht, besteht ihn heute — sein Pass-Pattern führt es sogar vor.
3. *Eigene Prüfdimension?* Nein. Der Zähler auf der Upstream-Route wird in demselben Handgriff gesetzt wie der Mechanismus selbst — `amtsblatt-mcp` hat Mechanismus und beide Tests in **einem** Release ausgeliefert —, und §2.5 verlangt, dass ein Check in einem Schritt behebbar bleibt. Das Gegensignal für einen eigenen Check greift ebenfalls nicht: Die Erweiterung erzwingt kein `oder` in den Pass-Criteria, das mit Kriterium 1 nichts zu tun hätte. Sie schärft Kriterium 1.

**Also kein `FID-007`, sondern ein dritter Modus in `ARCH-003`** — derselbe Ausgang wie bei den Regeln 7 und 8, wo `ARCH-020` den Pagination-Schnitt und die `ttlMs`-Ableitung aufgenommen hat, statt einen Check zu eröffnen. Der Vorschlag liegt drüben als [`mcp-audit-skill#102`](https://github.com/malkreide/mcp-audit-skill/issues/102); bis er umgesetzt ist, steht der Rand in Zeile 10, wie überall sonst in dieser Tabelle.

**Zur Haltbarkeit dieser Tabelle:** Der Katalog bewegt sich schneller als dieser Skill. Zwischen v1.7.0 (97 Checks) und v2.0.0 (112, dual baseline) lagen vier Tage, und mit v2.0.0 sind aus vier angeblich fehlenden Checks drei vorhandene geworden. Der nächste Beleg kam einen Tag später: Zwischen v2.0.0 und dem Katalogstand oben liegt ein Tag, und in ihm ist aus «Regel 6 hat keinen Check» ein `FID-006` geworden — plus zwei Reichweite-Sätze, die von «prüft er nicht» auf «prüft er» gekippt sind. Wer hier eine Zeile liest, um ein Finding zu beheben, prüft besser den Katalogstand oben mit — eine falsche Zuordnung kostet an genau der Stelle am meisten, an der jemand etwas reparieren will.
