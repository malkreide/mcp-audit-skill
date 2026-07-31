---
id: SCALE-007
title: "Wiederaufnahme abgerissener Streams via Last-Event-ID"
category: SCALE
severity: medium
applies_when: '(transport == "HTTP/SSE" or transport == "dual") and is_cloud_deployed == true'
pdf_ref: "Sec 5.1"
evidence_required: 2
---

# SCALE-007 — Wiederaufnahme abgerissener Streams via Last-Event-ID

## Description

Streamable HTTP kann eine abgerissene Verbindung fortsetzen, statt sie neu zu beginnen. Der Server hängt an jedes SSE-Event ein `id:`-Feld; der Client schickt beim Reconnect die zuletzt gesehene ID im `Last-Event-ID`-Header, und der Server spielt genau die Events danach nach. Ohne diesen Mechanismus ist ein Reconnect ein Neuanfang mit leerem Stream.

Der Abriss ist der Normalfall, nicht der Ausnahmefall. Reverse Proxies schliessen im Leerlauf (Railway, Render und die meisten Ingress-Defaults liegen im Bereich von Minuten), ein Rolling Deploy beendet den Pod, ein Mobilfunkwechsel wechselt die IP, ein zugeklappter Laptop schliesst die Verbindung. Genau währenddessen läuft der lange Tool-Call, für den sich Streaming überhaupt lohnt.

**Was dabei verloren geht, ist nicht die Sitzung, sondern die Antwort.** Der Request wurde angenommen, die Arbeit ist möglicherweise getan — nur die Bytes kommen nie an. Für den Client sieht das aus wie ein geschlossener Stream, nicht wie ein Fehler: kein JSON-RPC-Error, kein Statuscode, nichts, was eine Fehlerbehandlung greifen liesse. Der übliche Reflex des Clients ist, den Tool-Call erneut zu senden. Bei einem schreibenden Tool ohne Idempotency-Key (siehe `ARCH-010`) ist das eine zweite Ausführung.

**Abgrenzung zu `SCALE-002` / `SCALE-003`.** Affinität und Resumability lösen zwei verschiedene Hälften desselben Reconnects und ersetzen einander nicht:

| | Frage | Ohne sie |
|---|---|---|
| `SCALE-002` / `SCALE-003` | Landet der Reconnect auf **derselben Instanz**? | Richtiger Zustand, falscher Pod — Session weg |
| `SCALE-007` | Bekommt der Client die **verpassten Events**? | Richtiger Pod, richtige Session — Antwort weg |

Sticky Sessions sind korrekt konfiguriert, die `Mcp-Session-Id` ist gültig, der Reconnect landet auf der richtigen Instanz — und die Antwort auf den laufenden Request ist trotzdem verloren, weil niemand sie aufbewahrt hat. Das ist eine eigene Prüfdimension, kein zu enger Fall der beiden anderen.

**Der Replay ist stream-gebunden.** Event-IDs sind innerhalb einer Session eindeutig, aber jeder Stream hat seine eigene Folge. Beim Resume darf nur nachgespielt werden, was zu dem Stream gehört, aus dem die `Last-Event-ID` stammt. Ein Store, der nach ID sucht und alles Jüngere nachspielt, mischt die Antwort eines fremden Requests in die wiederaufgenommene Verbindung — im besten Fall ein Protokollfehler beim Client, im schlechteren ein Leck zwischen zwei Anfragen derselben Session.

`medium`: Die Spec stellt Resumability als **MAY**, und ein Client, der den Tool-Call wiederholt, kommt bei lesenden Tools ans Ziel. Ein Server ohne Event-Store ist degradiert, nicht kaputt. Auf Cloud-Deployments mit Idle-Timeout tritt der Fall aber nicht gelegentlich auf, sondern regelmässig — und die Wiederholung ist genau dann teuer, wenn der Call lange lief oder schrieb.

## Verification

### Modus 1: code_review (Event-Store verdrahtet)

```bash
# Python SDK — StreamableHTTPSessionManager bzw. FastMCP
grep -rnE "event_store|EventStore|StreamableHTTPSessionManager" src/

# TypeScript SDK
grep -rnE "eventStore|StreamableHTTPServerTransport" src/
```

**Pass-Pattern (Python):**

```python
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

session_manager = StreamableHTTPSessionManager(
    app=server,
    event_store=RedisEventStore(url=os.environ["REDIS_URL"]),   # persistiert
    json_response=False,
)
```

**Pass-Pattern (TypeScript):**

```typescript
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: () => randomUUID(),
  eventStore,                    // ohne dieses Feld: keine Resumability
});
```

**Fail-Pattern** — Transport ohne Store; die Events existieren nur, solange die Verbindung steht:

```python
session_manager = StreamableHTTPSessionManager(app=server)   # event_store=None
```

Ist ein Store verdrahtet, den zweiten Punkt prüfen: **Wo liegen die Events?** Ein reiner In-Memory-Store (`InMemoryEventStore` aus den SDK-Beispielen) überlebt weder den Pod-Neustart noch einen Reconnect, der bei einer anderen Replica landet — also genau die beiden Fälle, für die Resumability gedacht ist. Für Single-Replica-Deployments ist er vertretbar; ab zwei Replicas gehört der Store dorthin, wo auch der Session-State liegt (`SCALE-002`).

### Modus 2: runtime_test (Reconnect spielt nach)

```bash
BASE=https://my-mcp.railway.app/mcp
SID=$(curl -sD - -o /dev/null -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | grep -i '^mcp-session-id:' | tr -d '\r' | cut -d' ' -f2)

# Stream mitschneiden und nach ein paar Sekunden hart abbrechen
curl -sN -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{...}}' \
  --max-time 5 | tee stream.log

# 1. Tragen die Events überhaupt eine ID?
grep -c '^id:' stream.log || echo "BEFUND: keine Event-IDs — Resume unmöglich"
LAST=$(grep '^id:' stream.log | tail -1 | cut -d' ' -f2)

# 2. Nimmt der Server die Verbindung an der Abbruchstelle wieder auf?
curl -sN "$BASE" \
  -H "Accept: text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -H "Last-Event-ID: $LAST" --max-time 10
```

**Pass:** Der zweite Aufruf liefert die Events **nach** `$LAST` — nicht von vorn, nicht leer, und keine Events aus einem anderen Request derselben Session.

Die Gegenprobe gehört dazu: einmal mit einer erfundenen `Last-Event-ID` aufrufen. Der Server muss das erkennbar behandeln (Fehler oder frischer Stream) — nicht stillschweigend alles nachspielen, was er hat.

### Modus 3: config_check (Proxy hält den Stream offen)

Ein korrekter Event-Store nützt nichts, wenn die Schicht davor SSE puffert oder zu früh schliesst.

```bash
grep -rnE "proxy_buffering|proxy_read_timeout|X-Accel-Buffering" nginx/ deploy/ k8s/
grep -rnE "idle.?timeout|keep.?alive" railway.toml render.yaml k8s/ helm/ 2>/dev/null
```

**Pass-Pattern (nginx als Ingress vor dem MCP-Endpoint):**

```nginx
location /mcp {
    proxy_buffering off;           # sonst kommt kein Event einzeln durch
    proxy_read_timeout 3600s;
    proxy_set_header Connection '';
}
```

## Pass Criteria

- [ ] SSE-Events tragen ein `id:`-Feld — ohne IDs ist Resume grundsätzlich unmöglich
- [ ] Der Transport ist mit einem Event-Store verdrahtet (`event_store=` / `eventStore:`), nicht mit dem Default `None`
- [ ] Der Store liegt bei ≥ 2 Replicas ausserhalb des Prozesses (Redis o. ä.), nicht nur im Speicher
- [ ] Ein Reconnect mit `Last-Event-ID` liefert die verpassten Events, nicht den Stream von vorn und nicht einen leeren Stream
- [ ] Der Replay ist auf den Stream der übergebenen ID begrenzt — keine Events fremder Requests derselben Session
- [ ] Eine unbekannte `Last-Event-ID` wird erkennbar behandelt statt still ignoriert
- [ ] Die Proxy-/Ingress-Schicht puffert SSE nicht und schliesst nicht vor dem Server
- [ ] Event-Store und Session-State liegen in derselben Schicht — beides muss denselben Reconnect überleben

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Transport ohne `event_store` / `eventStore` | Jeder Abriss verliert die laufende Antwort — stumm, ohne Fehler beim Client |
| Events ohne `id:` | `Last-Event-ID` hat keinen Bezugspunkt; Resume ist nicht implementierbar |
| `InMemoryEventStore` bei mehreren Replicas | Der Reconnect landet auf einer Instanz, die die Events nie gesehen hat |
| Replay über alle Streams einer Session | Fremde Antwort im wiederaufgenommenen Stream — Protokollfehler oder Leck |
| Unbekannte `Last-Event-ID` → kompletter Replay | Der Client verarbeitet Events doppelt |
| `proxy_buffering on` vor dem MCP-Endpoint | Events kommen gebündelt am Schluss; der Abriss verliert alles auf einmal |
| Sticky Sessions ohne Event-Store | Richtiger Pod, verlorene Antwort — die halbe Lösung sieht aus wie die ganze |

## Remediation

1. Klären, ob die Events überhaupt IDs tragen — ohne das ist alles Weitere gegenstandslos. Im Python-SDK entstehen die IDs im Event-Store; im TS-SDK ebenso. Kein Store, keine IDs.
2. Store verdrahten. Für Single-Replica genügt die In-Memory-Variante aus den SDK-Beispielen als Zwischenschritt.
3. Ab zwei Replicas den Store dorthin legen, wo `SCALE-002` bereits den Session-State hinlegt. Ein Deployment mit geteiltem Session-State und lokalem Event-Store ist inkonsistent — der Reconnect findet die Session und verliert trotzdem die Antwort.
4. TTL setzen. Events sind nur bis zum Reconnect-Fenster interessant; ohne Ablauf wächst der Store mit jedem Tool-Call.
5. Proxy-Konfiguration nachziehen: Buffering aus, Read-Timeout über die längste erwartete Tool-Laufzeit.
6. Den Abriss einmal wirklich auslösen — Verbindung hart trennen, mit `Last-Event-ID` wiederaufnehmen, nachgespielte Events zählen. Ein nie ausgelöster Resume-Pfad ist unbelegt.

```diff
- session_manager = StreamableHTTPSessionManager(app=server)
+ session_manager = StreamableHTTPSessionManager(
+     app=server,
+     event_store=RedisEventStore(url=os.environ["REDIS_URL"], ttl=900),
+ )
```

## Effort

M — 1–3 Tage. Der Store ist schnell verdrahtet; die Zeit geht in die geteilte Ablage bei mehreren Replicas und in die Gegenprobe mit echtem Verbindungsabriss.

## References

- PDF Sec 5.1 — Transport, Reconnect via Event-IDs
- [MCP Spec: Transports — Resumability and Redelivery](https://modelcontextprotocol.io/specification/draft/basic/transports)
- `SCALE-001` — Transportwahl; dieser Check prüft, was der gewählte Transport bei Abriss leistet
- `SCALE-002` / `SCALE-003` — Affinität beim Reconnect; die andere Hälfte desselben Problems
- `ARCH-010` — Idempotency-Keys; ohne sie wird der wiederholte Tool-Call nach verlorenem Stream zur zweiten Ausführung
- `ARCH-009` — `idempotentHint`; die Annotation, auf die der Host seine Retry-Logik stützt, wenn ein Stream abreisst
