---
id: ARCH-014
title: "Retry-Politik gegenüber der Quelle: begrenzt, gestreut, gehorsam"
category: ARCH
severity: high
adoption: advisory
applies_when: 'tools_make_external_requests == true'
pdf_ref: "Custom (Katalog-Lücke, aufgefallen bei swiss-efv-mcp#16)"
evidence_required: 3
---

# ARCH-014 — Retry-Politik gegenüber der Quelle

## Description

Fast jeder Server im Portfolio wiederholt fehlgeschlagene Requests, und bis auf `OBS-007` («wie lautet die Meldung, wenn alle Versuche verbraucht sind») stellte der Katalog dazu keine Frage. Nicht *ob* wiederholt wird — das ist richtig —, sondern **was**, **wie schnell** und **wie lange**. Alle drei Antworten sind falsch, wenn niemand sie trifft: Die Voreinstellung ist «alles, sofort, unbegrenzt».

**Was wiederholt wird.** Ein 404 wird beim vierten Versuch kein 200. Ein 401 auch nicht. Wiederholbar sind 5xx, 429, Timeouts und Verbindungsfehler; alles andere im 4xx-Bereich ist eine Aussage über die Anfrage, nicht über den Moment. Wer pauschal auf jede Exception wiederholt, verwandelt einen sofortigen, korrekten Fehler in eine Minute Wartezeit mit demselben Ergebnis — und belastet dabei eine Quelle, die schon geantwortet hat.

**Wie schnell — und warum Jitter kein Detail ist.** `2**attempt` ist deterministisch. Fällt eine Quelle aus, während zehn Server sie abfragen, laufen deren Retries im Gleichtakt: Alle warten 2 s, alle fragen gleichzeitig, alle warten 4 s. Die Last kommt als Welle zurück, und zwar genau in dem Moment, in dem sich die Quelle erholt — der Retry-Sturm verlängert den Ausfall, den er überbrücken sollte. Streuung (`2**attempt * (0.5 + random())`) kostet eine Zeile und löst das.

**`Retry-After` schlägt die eigene Kurve.** Bei 429 und 503 sagt die Quelle im Header, wann sie wieder mag — als Sekundenzahl oder HTTP-Datum. Ein Client, der stattdessen seine eigene Backoff-Kurve fährt, ignoriert eine ausdrückliche Angabe. Für ein Portfolio, das auf fremder, meist unfinanzierter Open-Data-Infrastruktur sitzt, ist das die Grenze zwischen Gast und Last: Wer zweimal ignoriert wird, sperrt.

**Wie lange — und wogegen das Budget bemessen wird.** Vier Versuche à 60 s Timeout plus Backoff sind rund 254 s. Der MCP-Client hat sein eigenes Timeout, oft deutlich darunter. Ist das Retry-Budget grösser, gibt der Client zuerst auf — und die Arbeit läuft weiter, ohne dass sie noch jemand entgegennimmt. Das ist der schlechteste aller Fälle: volle Last auf die Quelle für ein Ergebnis, das ins Leere geht. **Das Gesamtbudget gehört unter das Client-Timeout**, und ein Budget in Sekunden ist die belastbarere Grenze als eine Anzahl Versuche, weil es nicht mit dem Timeout mitwächst.

**Retries stapeln sich multiplikativ.** Transport-Retries (`httpx.HTTPTransport(retries=…)`), eine eigene Schleife darüber und ein wiederholender Aufrufer ergeben nicht 4 + 4 + 4, sondern 4 × 4 × 4. Wiederholt werden darf auf genau einer Ebene; die anderen müssen nachweislich auf null stehen.

**Nach der Erschöpfung.** Ein veralteter Cache-Eintrag ist meist besser als ein Fehler — aber nur, wenn das Tool-Result seine Herkunft und sein Alter benennt. Stillschweigend alte Zahlen auszuliefern ist die Datentreue-Verletzung, gegen die `FID-003` steht.

`high`: Die Wirkung zeigt sich nicht am eigenen Server, sondern bei der Quelle und beim Agenten. Ein falsch bemessener Retry macht aus einer kurzen Störung einen langen Ausfall, und aus einem Gast einen Fall für die Sperrliste — beides bemerkt der Betreiber erst, wenn es passiert ist.

**Abgrenzung.** `ARCH-010` fragt, ob eine Wiederholung *sicher* ist (Idempotency-Keys, kompensierende Aktionen); dieser Check fragt, ob sie *angemessen* ist. `OBS-007` regelt, was in der Meldung steht, wenn alle Versuche verbraucht sind. `FID-003` regelt, wie ein degradiertes Ergebnis gekennzeichnet wird. Die Einordnung unter `ARCH` folgt `ARCH-010` und `ARCH-013`: Dort liegt, wie der ausgehende Pfad verdrahtet ist.

**Adoptionsstufe `advisory`.** Der Check ist neu, hat drei getrennte Pass-Dimensionen und trifft mutmasslich breite Teile des Portfolios — Jitter und `Retry-After` sind genau die zwei Zeilen, die man beim ersten Schreiben weglässt. Er meldet, blockiert aber nicht, bis ein Portfolio-Durchlauf zeigt, ob er richtig geschnitten ist.

## Verification

### Modus 1: code_review (was wiederholt wird)

```bash
grep -rnE 'for attempt|while .*attempt|@retry|tenacity|backoff' src/
grep -rnE 'except Exception|except:' src/ | head        # pauschaler Catch im Retry-Pfad?
grep -rnE 'status_code|raise_for_status' src/
```

**Pass-Pattern** — 4xx ausser 429 bricht sofort ab:

```python
except (httpx.HTTPStatusError, httpx.RequestError) as exc:
    last_error = exc
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is not None and 400 <= status < 500 and status != 429:
        raise                       # eine Aussage über die Anfrage, nicht über den Moment
```

**Fail-Pattern:**

```python
for attempt in range(4):
    try:
        return await http.get(url)
    except Exception:               # 404 und 401 werden mitwiederholt
        await asyncio.sleep(2 ** attempt)
```

### Modus 2: code_review (Jitter und `Retry-After`)

```bash
grep -rnE 'random|jitter|uniform' src/                  # Streuung vorhanden?
grep -rn 'Retry-After' src/ || echo "BEFUND: Retry-After wird nicht gelesen"
```

**Pass-Pattern** — die Angabe der Quelle schlägt die eigene Kurve, mit Deckel gegen absurde Werte:

```python
def _delay(attempt: int, resp: httpx.Response | None) -> float:
    if resp is not None and resp.status_code in (429, 503):
        hint = resp.headers.get("Retry-After")
        if hint and hint.isdigit():
            return min(float(hint), MAX_DELAY)     # Quelle hat das Wort
    return min(BASE * 2**attempt, MAX_DELAY) * (0.5 + random.random())   # sonst gestreut
```

**Fail-Pattern:**

```python
await asyncio.sleep(2 ** attempt)   # deterministisch, ignoriert Retry-After
```

### Modus 3: runtime_test (Budget und Stapelung)

```bash
# Wiederholt noch eine zweite Ebene mit?
grep -rnE 'HTTPTransport\(|transport=|max_retries|Retry\(' src/
```

Und das Budget messen, statt es zu schätzen:

```python
@respx.mock
async def test_retry_budget_is_bounded():
    respx.get(URL).mock(side_effect=httpx.ConnectTimeout(""))
    start = time.monotonic()
    with pytest.raises(RuntimeError):
        await client.load("data")
    assert time.monotonic() - start < CLIENT_TIMEOUT   # unter dem, was der Aufrufer wartet
```

**Pass:** Die gemessene Gesamtdauer liegt unter dem Timeout des MCP-Clients, und nur eine Ebene wiederholt.

## Pass Criteria

- [ ] Wiederholt wird nur bei 5xx, 429, Timeout und Verbindungsfehler — **4xx ausser 429 bricht sofort ab**
- [ ] Der Backoff ist **gestreut** (Jitter), nicht rein deterministisch
- [ ] `Retry-After` bei 429/503 wird gelesen und **schlägt** die eigene Kurve, gedeckelt gegen unbrauchbar grosse Werte
- [ ] Es gibt ein **Gesamtbudget in Sekunden**, nicht nur eine Anzahl Versuche
- [ ] Das Budget liegt **unter dem Timeout des aufrufenden MCP-Clients** — sonst arbeitet der Server für niemanden
- [ ] Wiederholt wird auf **genau einer Ebene**; Transport-Retries der HTTP-Bibliothek stehen nachweislich auf null
- [ ] Schreibende Tools wiederholen nur mit Idempotency-Key (`ARCH-010`)
- [ ] Nach Erschöpfung: Fehler oder **gekennzeichnet** veralteter Cache — kein stilles Ausliefern alter Zahlen (`FID-003`)
- [ ] Die Werte sind im Test gebunden, nicht nur im Kommentar behauptet

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| `except Exception` im Retry-Pfad | 404/401 werden wiederholt: Wartezeit ohne Aussicht, Last ohne Grund |
| `sleep(2 ** attempt)` ohne Jitter | Retry-Sturm im Gleichtakt trifft die Quelle beim Erholen |
| `Retry-After` nicht gelesen | Ausdrückliche Angabe der Quelle ignoriert — Weg zur Sperre |
| Budget nur als Anzahl Versuche | Wächst still mit dem Timeout mit; 4 × 60 s sind vier Minuten |
| Retry-Budget über dem Client-Timeout | Client gibt zuerst auf; Last ohne Empfänger |
| Retries auf Transport **und** in der Schleife | Multiplikativ statt additiv: 4 × 4 statt 4 + 4 |
| Retry auf nicht-idempotentem Write | Doppelte Ausführung (`ARCH-010`) |
| Stiller Fallback auf alten Cache | Alte Zahlen ohne Kennzeichen (`FID-003`) |

## Remediation

```diff
+ MAX_DELAY = 20.0          # Deckel gegen absurde Retry-After-Werte
+ TOTAL_BUDGET = 25.0       # unter dem Timeout des aufrufenden Clients
+
  async def _fetch_with_retry(self, http, url):
+     deadline = time.monotonic() + TOTAL_BUDGET
      for attempt in range(4):
          if attempt > 0:
-             await asyncio.sleep(self.backoff_base ** attempt)
+             delay = self._delay(attempt, getattr(last_error, "response", None))
+             if time.monotonic() + delay > deadline:
+                 break        # der nächste Versuch käme zu spät, um noch zu zählen
+             await asyncio.sleep(delay)
          try:
              resp = await http.get(url)
              resp.raise_for_status()
              return resp
          except (httpx.HTTPStatusError, httpx.RequestError) as exc:
              last_error = exc
              status = getattr(getattr(exc, "response", None), "status_code", None)
              if status is not None and 400 <= status < 500 and status != 429:
                  raise
```

Und die zweite Ebene stilllegen, falls vorhanden:

```python
# httpx wiederholt selbst, wenn ein Transport mit retries= gebaut wird.
# Genau eine Ebene darf wiederholen — diese hier.
httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(retries=0))
```

## Effort

S–M — Pro Server einen halben bis ganzen Tag. Jitter und die `Retry-After`-Auswertung sind je wenige Zeilen; die Zeit geht in das Bemessen des Budgets gegen das Client-Timeout und in den Test, der beides bindet.

## References

- `ARCH-010` — ob eine Wiederholung sicher ist; dieser Check fragt, ob sie angemessen ist
- `ARCH-013` — derselbe ausgehende Pfad, andere Frage
- `OBS-007` — was in der Meldung steht, wenn alle Versuche verbraucht sind
- `FID-003` — ein degradiertes Ergebnis muss als solches erkennbar sein
- `OPS-001` — Live-Suite: dieselbe Retry-Leiter, multipliziert über die Tests
- [RFC 9110 §10.2.3 — `Retry-After`](https://www.rfc-editor.org/rfc/rfc9110#field.retry-after)
- [AWS Architecture Blog — Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
