---
id: ARCH-014
title: "Retry-Politik gegenüber der Quelle: begrenzt, gestreut, gehorsam"
category: ARCH
severity: high
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

**Adoptionsstufe `enforced` (seit 2026-08-03).** Der Check startete `advisory`, und die Zahlen gaben dem recht: Bei der Erhebung las **keiner von elf** Servern `Retry-After`, **keiner** streute seinen Backoff, und drei hatten überhaupt keine Retry-Schleife. Enforced am ersten Tag wäre ein rotes Portfolio gewesen — so werden Checks zurückgenommen statt übernommen.

Die Bedingung, unter der die Stufe zurückgestellt wurde, ist eingelöst: Alle elf Server erfüllen den Check heute. Damit hat er nichts mehr zu beweisen, indem er nicht blockiert — und ab jetzt ist der teure Fall nicht mehr der Rückstand, sondern der zwölfte Server, der ohne Politik dazukommt.

Der Durchlauf hat den Check zugleich geschärft. Drei Dinge sind erst dabei aufgefallen und stehen jetzt in den Pass-Pattern:

- **Der Deckel muss *nach* dem Jittern greifen.** Sechs Server deckelten davor, womit eine 20-s-Decke auf 30 s wuchs (exponentiell, ×1.5) beziehungsweise auf 25 s (`Retry-After`, ×1.25). Die Konstante behauptete eine Schranke, die sie nicht einhielt.
- **Ein Gesamtbudget aus einem httpx-Timeout ist keines.** httpx begrenzt pro Operation, und sein Read-Timeout beginnt mit jedem Chunk von vorn — eine langsam tröpfelnde Antwort überdauert das Budget, ohne dass ein einzelner Read abläuft. Wer ein Budget verspricht, braucht eine Wanduhr-Deadline (`asyncio.timeout` / `asyncio.wait_for`).
- **Netzwerkfehler sind der Fall, für den man den Retry baut.** Ein Server wiederholte nur Status-Codes: 503 bekam drei Versuche, eine abgelehnte Verbindung aus demselben Ausfall keinen. Der Retry sah vorhanden aus und liess den häufigsten Fall ungedeckt.

## Verification

### Modus 1: code_review (was wiederholt wird)

```bash
grep -rnE 'for attempt|while .*attempt|@retry|tenacity|backoff' src/
grep -rnE 'except Exception|except:' src/ | head        # pauschaler Catch im Retry-Pfad?
grep -rnE 'status_code|raise_for_status' src/
# Netzwerkfehler im Retry-Pfad — bewusst breit, weil der Check fuer jede
# Client-Bibliothek gilt und nicht nur fuer httpx:
grep -rnE 'RequestError|TransportError|ConnectError|ConnectionError|TimeoutError|TimeoutException|ClientError|Timeout\b|retry_if_exception' src/
```

Der letzte Griff ist der wichtigste und der am leichtesten übersehene. Eine Schleife, die nur `status_code` prüft, wiederholt ein 503 aus einem Ausfall dreimal und eine abgelehnte Verbindung aus **demselben** Ausfall kein einziges Mal — sie sieht vorhanden aus und lässt den häufigsten Fall ungedeckt. Genau diese Asymmetrie stand hinter dem Vorfall, der diesen Check ausgelöst hat.

**Ein leeres Ergebnis ist hier kein Befund, sondern eine Leseaufforderung.** Der Check gilt für *jede* Art, externe Requests zu stellen; ein korrekter Retry kann `aiohttp`, `requests`, einen Alias, eine Oberklasse wie `httpx.TransportError` oder ein `tenacity`-Prädikat benutzen, und keiner dieser Namen steht zwangsläufig in der Liste oben. Ein Grep, der Namen kennt statt Verhalten, darf einen Namensunterschied nicht in ein blockierendes Verdikt verwandeln. Findet er nichts, ist die Retry-Schleife **von Hand** zu lesen: Fängt sie ausschliesslich Status-Codes, ist das der Befund — und erst dann.

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

**Pass-Pattern** — die Angabe der Quelle schlägt die eigene Kurve, und der Deckel greift **nach** dem Jittern:

```python
def _delay(attempt: int, resp: httpx.Response | None) -> float:
    hint = parse_retry_after(resp)          # 429/503, Sekundenzahl *und* HTTP-Datum
    if hint is not None:
        jittered = hint * (1.0 + random.random() * 0.25)   # einseitig: später ist höflich
    else:
        jittered = BASE * 2**attempt * (0.5 + random.random())
    return min(jittered, MAX_DELAY)         # Deckel zuletzt, sonst ist er keiner
```

**Fail-Pattern 1** — deterministisch und taub:

```python
await asyncio.sleep(2 ** attempt)   # deterministisch, ignoriert Retry-After
```

**Fail-Pattern 2** — der Deckel, der keiner ist:

```python
capped = min(BASE * 2**attempt, MAX_DELAY)
return capped * (0.5 + random.random())       # MAX_DELAY=20 -> bis 30 s
```

Diese Reihenfolge steckte in **sechs** Servern des Portfolios, weil sie sich beim Lesen richtig anfühlt: erst begrenzen, dann streuen. Sie multipliziert den gedeckelten Wert anschliessend mit bis zu 1.5 — die Konstante behauptet eine Schranke, die sie nicht einhält. Rechne beim Audit nach, statt den Namen der Konstante zu glauben: `MAX_DELAY * (1 + jitter_spread)` ist die tatsächliche Obergrenze.

**Prüfbar mit einer Ziehung, nicht mit einem Blick:**

```python
def test_the_cap_is_a_real_bound_not_a_midpoint():
    for attempt in range(8):
        for _ in range(20):        # Jitter ist zufällig — eine Ziehung beweist nichts
            assert _delay(attempt, None) <= MAX_DELAY
            assert _delay(attempt, _resp(429, "86400")) <= MAX_DELAY
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

**Woran das Budget hängen muss.** Ein `timeout=` an den HTTP-Aufruf ist *kein* Gesamtbudget. `httpx` wendet sein Timeout **pro Operation** an (connect/read/write/pool), und das Read-Timeout beginnt mit **jedem Chunk** von vorn: Eine langsam tröpfelnde Antwort überdauert das Budget, ohne dass ein einzelner Read je abläuft. Wer ein Budget verspricht, braucht eine Wanduhr-Deadline daneben:

```python
async with asyncio.timeout(remaining):        # ab 3.11; sonst asyncio.wait_for
    resp = await http.get(url, timeout=min(per_op_timeout, remaining))
```

**Und der Test dazu darf keine Fake-Uhr benutzen.** Budget-Tests laufen üblicherweise unter einer Uhr, die nur vorrückt, wenn etwas schläft — eine solche Uhr kann eine Zusicherung über *echte* Zeit nicht widerlegen. Sie war der blinde Fleck, unter dem dieser Fehler durch sechs Server gereist ist:

```python
async def test_a_slow_response_is_cut_by_the_wall_clock_deadline(real_sleep):
    async def _slow(request):
        await real_sleep(1.0)              # echte Zeit, keine Fake-Uhr
        return httpx.Response(200)
    respx.get(URL).mock(side_effect=_slow)
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        await client.load("data", total_budget=0.05)
    assert time.monotonic() - started < 0.5
```

**Pass:** Die gemessene Gesamtdauer liegt unter dem Timeout des MCP-Clients, das Budget hängt an einer Wanduhr-Deadline, und nur eine Ebene wiederholt.

## Pass Criteria

- [ ] Wiederholt wird nur bei 5xx, 429, Timeout und Verbindungsfehler — **4xx ausser 429 bricht sofort ab**
- [ ] Der Backoff ist **gestreut** (Jitter), nicht rein deterministisch
- [ ] Wiederholt wird auch bei **Netzwerkfehlern und Timeouts**, nicht nur bei Status-Codes
- [ ] `Retry-After` bei 429/503 wird gelesen und **schlägt** die eigene Kurve, gedeckelt gegen unbrauchbar grosse Werte
- [ ] Der Deckel greift **nach** dem Jittern — nachgerechnet, nicht am Namen der Konstante abgelesen
- [ ] Es gibt ein **Gesamtbudget in Sekunden**, nicht nur eine Anzahl Versuche
- [ ] Das Budget hängt an einer **Wanduhr-Deadline**, nicht am Per-Operation-Timeout der HTTP-Bibliothek
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
+         remaining = deadline - time.monotonic()
+         if remaining <= 0:
+             break
          try:
-             resp = await http.get(url)
-             resp.raise_for_status()
-             return resp
+             # Wanduhr-Deadline um den Request: Das httpx-Timeout greift pro
+             # Operation und beginnt mit jedem Chunk von vorn, begrenzt also
+             # nicht den Aufruf. Ohne diese Zeile ist TOTAL_BUDGET eine
+             # Behauptung, keine Grenze.
+             async with asyncio.timeout(remaining):      # 3.11+; sonst wait_for
+                 resp = await http.get(url, timeout=min(PER_OP_TIMEOUT, remaining))
+                 resp.raise_for_status()
+                 return resp
+         except TimeoutError as exc:   # Budget weg, nicht bloss dieser Versuch
+             last_error = exc
+             break
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
- `SEC-028` — ob der Egress-Guard die Information liefert, an der diese Politik entscheidet
- `OBS-007` — was in der Meldung steht, wenn alle Versuche verbraucht sind
- `FID-003` — ein degradiertes Ergebnis muss als solches erkennbar sein
- `OPS-001` — Live-Suite: dieselbe Retry-Leiter, multipliziert über die Tests
- [RFC 9110 §10.2.3 — `Retry-After`](https://www.rfc-editor.org/rfc/rfc9110#field.retry-after)
- [AWS Architecture Blog — Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
