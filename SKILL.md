---
name: mcp-data-fidelity
description: Datentreue-Regeln für MCP-Server-Tools, die eine externe Datenquelle abfragen — damit ein Server nicht still unvollständig liefert. Verwende diesen Skill ergänzend zu mcp-builder immer wenn (1) ein Such-, Query- oder Filter-Tool für einen MCP-Server entworfen oder implementiert wird, (2) eine Tool-Description für ein datenabfragendes Tool geschrieben oder überarbeitet wird, (3) jemand meldet, ein Server finde nichts, zu wenig oder weniger als die offizielle Oberfläche («findet nichts», «leeres Ergebnis», «Web-UI zeigt mehr», «zu wenig Treffer», «Recall», «Scope»), (4) ein Modell auf ein leeres Tool-Result hin eine Antwort erfunden hat, (5) optionale API-Parameter (Filter, Facetten, Feld-Flags, Limits) in Requests übersetzt werden, oder (6) Tests für ein datenabfragendes Tool geschrieben werden. Nicht nötig für Server ohne externe Datenquelle.
---

# MCP Data Fidelity — liefert der Server, was die Quelle hat?

Companion zu `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **liefert er, was die Quelle tatsächlich hat?**

Das ist eine eigene Fehlerklasse, weil sie still ist. HTTP 200, wohlgeformtes JSON, grüne Tests — und inhaltlich falsch. Ein Server, der zwei Prozent des Bestands durchsucht und das nicht meldet, produziert Antworten, die niemand als falsch erkennt.

**Die Leitfrage bei jedem datenabfragenden Tool:** *Wenn dieses Tool nichts findet — kann ich unterscheiden, ob es nichts gibt oder ob ich falsch gefragt habe?* Ist die Antwort nein, greift eine der sechs Regeln unten.

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

Der Hinweis muss **konkret** sein. «Versuchen Sie eine andere Suche» ist kein nächster Schritt. Und er gehört ins Tool-Result, nicht ins README — das wird nicht an das Modell weitergereicht.

**Abgrenzung:** Ein Transport- oder Autorisierungsfehler ist keine Leermenge und darf nie als solche formatiert werden. Ein abgewiesener Request — HTTP 421 auf einen fremden Host-Header, 401, 403, ein Verbindungsabbruch — erreicht die Quelle nie und kommt bei der aufrufenden Schicht trotzdem als «Fehlschlag ohne Daten» an; wer nur auf «keine Datensätze» prüft, reicht ihn als Leermenge durch. Er trägt aber einen anderen nächsten Schritt: **Konfiguration prüfen, nicht Suche verbreitern.** Ein Hinweis, der zur Wildcard rät, während die Abfrage gar nicht angekommen ist, schickt das Modell in die falsche Richtung — und ein Konfigurationsfehler unterläuft genau die Regel, die das Raten verhindern soll. Solche Fälle gehören mit `isError` in den Fehlerkanal, wie die Strukturabweichung in Regel 6.

## Regel 4 — Die Tool-Description ist eine Halluzinations-Oberfläche

Die schwerste der sechs Regeln, weil sie kontraintuitiv ist: **Eine Formulierung, die eine Leermenge erklärt, erzeugt Konfabulation zuverlässiger als gar keine Formulierung.**

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

## Checkliste vor dem Release eines datenabfragenden Tools

- [ ] Jeder optionale Filter-/Scope-Parameter geprüft: Was bedeutet Weglassen? Beleg aus der Parameterbeschreibung
- [ ] Recall-Delta gemessen (weggelassen vs. explizit maximal), Delta ≠ 0 behoben
- [ ] Boolesche Parameter-Gruppen vollständig gesendet, Verengung nachgewiesen
- [ ] Leeres Result trägt ein `hint`-Feld mit konkretem nächstem Schritt
- [ ] Transport- und Autorisierungsfehler enden im Fehlerkanal, nie als Leermenge mit Such-Hinweis (Regel 3)
- [ ] Keine Tool-Description erklärt oder entschuldigt eine Leermenge
- [ ] Query-Syntax samt Matching-Granularität in der Description
- [ ] Recall-Canary als Live-Test mit Untergrenzen
- [ ] Antwortstruktur wird bestätigt, bevor gezählt wird — kein `.get(x, [])` auf dem Hauptpfad (Regel 6)
- [ ] Eine Strukturabweichung upstream endet als Fehler, nicht als leeres Resultat (Regel 6)
- [ ] Gegen die offizielle Oberfläche der Quelle verglichen, jedes Delta erklärt

## Woher diese Regeln stammen

Aus einem einzelnen realen Vorfall: [`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). Der Server sendete `ClassificationIds` nur bei explizitem Aufruf; die API schränkt eine ID-lose Suche auf `VARIA` ein — eine von 23 Klassifikationen. «Quellensteuer» lieferte null Treffer bei mehreren vorhandenen Einträgen, «Pensionskasse» einen statt 21.

Vier Dinge daran sind übertragbar:

1. **33 grüne Offline-Tests haben nichts gefangen** — Mocks können eine falsche Grundannahme prinzipiell nicht widerlegen.
2. **Ein 68-Punkte-Audit war bestanden** — alle Kategorien prüften die Bauweise, keine die Datentreue.
3. **Die eigene Doku hat das Modell zum Konfabulieren gebracht** — siehe Regel 4.
4. **Gefunden hat es ein User mit dem Web-UI daneben** — Ground Truth kommt von aussen, nicht aus der Testsuite.

## Verwandte Skills

| Skill | Rolle |
|---|---|
| `mcp-builder` | Generische Bauanleitung — fremder Skill von Anthropic, dieser hier ergänzt ihn |
| `mcp-data-source-probe` | Vorgehen *vor* dem Bau: Default-Matrix (1.2b), Recall-Ground-Truth (1.4), Leermengen (3.6) |
| `mcp-data-fidelity` | **Dieser Skill:** liefert er, was die Quelle hat? |
| [`mcp-transport-hardening`](https://github.com/malkreide/mcp-transport-hardening-skill) | Kommt er hoch, weist er richtig ab? Dieselbe stille Fehlerklasse eine Schicht tiefer — nicht der Inhalt der Antwort, sondern ob überhaupt eine kommt |
| `mcp-audit` | Prüfung *nach* dem Bau: die Regeln 1–5 erscheinen dort als Checks `FID-001`–`FID-005`; Regel 6 hat keinen Check |

Wer nach diesem Skill baut, besteht die FID-Checks. Wer sie beim Audit reisst, findet hier die Behebung.
