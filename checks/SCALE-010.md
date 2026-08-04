---
id: SCALE-010
title: "subscriptions/listen statt GET-Endpunkt und resources/subscribe"
category: SCALE
severity: medium
applies_when: 'transport != "stdio-only"'
spec_baseline: 2026-07-28
adoption: advisory
pdf_ref: "SEP-2575"
spec_ref: "SEP-2575 (PR 2575) — Spec-Changelog 2026-07-28, Major #4"
evidence_required: 2
---

# SCALE-010 — `subscriptions/listen`

## Description

`2026-07-28` ersetzt zwei Mechanismen durch einen. Weg sind der HTTP-GET-Endpunkt für serverinitiierte Nachrichten und das Paar `resources/subscribe` / `resources/unsubscribe`. An ihre Stelle tritt `subscriptions/listen`: ein einzelner langlebiger POST-Antwortstrom, in den sich der Client für bestimmte Benachrichtigungstypen einträgt — `toolsListChanged`, `promptsListChanged`, `resourcesListChanged`, `resourceSubscriptions`. Der Server bestätigt und markiert jede Benachrichtigung mit `io.modelcontextprotocol/subscriptionId`.

**Die Trennlinie, an der die Migration schiefgeht:** Nicht alles, was der Server ungefragt sendet, gehört in diesen Strom. Request-bezogene Benachrichtigungen — `notifications/progress`, `notifications/message` — laufen weiterhin auf dem Antwortstrom **des Requests, zu dem sie gehören**. Nur was keinem Request zugeordnet ist, gehört auf `subscriptions/listen`.

Ein Server, der beim Umbau alles in den neuen Strom schiebt, bricht die Fortschrittsmeldung: Der Client wartet auf dem Antwortstrom seines Tool-Calls auf Fortschritt und bekommt dort nichts, während die Meldungen ohne Request-Bezug daneben eintreffen. Nichts wirft einen Fehler; der Fortschrittsbalken bleibt stehen.

**Bedingt anwendbar.** Ein Server ohne Änderungsbenachrichtigungen — die Mehrheit der Read-only-Wrapper im Portfolio — erfüllt diesen Check dadurch, dass er nichts dergleichen führt. Das ist ein `pass` mit einem Satz Evidenz, kein «nicht anwendbar»: Der Unterschied zwischen «führt keine» und «nicht nachgesehen» ist genau der, den §2.6 einfordert.

## Verification

### Modus 1: automated (alte und neue Mechanismen)

```bash
# Alt — auf dieser Baseline ein Befund
grep -rnE "resources/(un)?subscribe|resource_subscribe|@app\.get\(.*mcp|handle_get" \
    src/ --include="*.py" --include="*.ts"

# Neu
grep -rnE "subscriptions/listen|subscriptionId|toolsListChanged|resourcesListChanged" \
    src/ --include="*.py" --include="*.ts"

# Request-bezogene Benachrichtigungen — gehören NICHT in den neuen Strom
grep -rnE "notifications/progress|notifications/message|report_progress|ctx\.info" \
    src/ --include="*.py" --include="*.ts"
```

### Modus 2: runtime_test (GET ist zu, Progress läuft weiter)

```bash
# GET darf nicht mehr bedient werden
curl -sS -i -X GET "$MCP_URL" -H 'Accept: text/event-stream' | head -3   # erwartet 405
```

Und der Gegenbeleg, der leicht vergessen wird: ein Tool mit Fortschrittsmeldung aufrufen und prüfen, dass die Meldungen **auf dem Antwortstrom dieses Aufrufs** eintreffen.

## Pass Criteria

- [ ] Führt der Server keine Änderungsbenachrichtigungen, ist das belegt und im README festgehalten — mit einem Satz, nicht durch Schweigen
- [ ] Kein `resources/subscribe` / `resources/unsubscribe` mehr im Code
- [ ] Kein GET-Endpunkt für serverinitiierte Nachrichten; ein GET auf den MCP-Pfad antwortet `405`
- [ ] Führt der Server Benachrichtigungen: Der Client trägt sich über `subscriptions/listen` je Typ ein, und der Server bestätigt
- [ ] Jede Benachrichtigung trägt `io.modelcontextprotocol/subscriptionId`
- [ ] `notifications/progress` und `notifications/message` laufen weiter auf dem Antwortstrom ihres Requests, **nicht** auf `subscriptions/listen` — mit einem Test belegt
- [ ] Der Reverse Proxy puffert den langlebigen Strom nicht und schliesst ihn nicht vor dem Server

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Fortschrittsmeldungen in `subscriptions/listen` verschoben | Fortschrittsbalken bleibt stehen; kein Fehler, nur Stillstand |
| GET-Endpunkt bleibt neben dem neuen Strom offen | Zwei Wege für dasselbe; `ARCH-013` |
| Benachrichtigungen ohne `subscriptionId` | Client kann sie keinem Abonnement zuordnen |
| Server sendet Typen, für die niemand eingetragen ist | Opt-in ohne Wirkung |
| «keine Benachrichtigungen» ungeprüft angenommen | §2.6: nicht nachgesehen, als bestanden geführt |

## Remediation

```diff
-@app.get("/mcp")
-async def legacy_notification_stream(request: Request):
-    return EventSourceResponse(_pending_notifications())
-
-@server.subscribe_resource()
-async def subscribe(uri: str) -> None:
-    _SUBSCRIBERS.add(uri)
+@server.subscriptions_listen()
+async def listen(types: list[str]) -> SubscriptionStream:
+    stream = await _subs.open(types)          # Server bestätigt das Opt-in
+    return stream                              # Benachrichtigungen tragen subscriptionId
```

Fortschritt bleibt, wo er war:

```python
@mcp.tool()
async def bulk_export(ctx: Context, year: int) -> dict:
    for i, chunk in enumerate(chunks):
        await ctx.report_progress(i, len(chunks))   # Antwortstrom DIESES Requests
    return complete({"rows": total})
```

## Effort

S für Server ohne Benachrichtigungen (Beleg und ein Satz README). M, wenn ein Abonnementpfad umgebaut werden muss — die Zuordnung request-bezogen gegen abonnementbezogen ist der eigentliche Aufwand, nicht der Strom.

## References

- [Spec 2026-07-28 — Changelog, Major #4](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2575](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2575)
- `ARCH-013` (Transportpfade), `SCALE-009` (Legacy-SSE), `ARCH-020` (listChanged und ttlMs)
