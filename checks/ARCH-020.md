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

**Der teure Fehler ist `cacheScope: "public"` an der falschen Stelle.** Bei einem Server mit `data_class != "Public Open Data"` erlaubt `"public"` einer Zwischeninstanz, die Antwort für andere Aufrufer aufzubewahren. Wenn `resources/read` mandantenbezogene Inhalte liefert, ist das kein Performance-Detail, sondern eine Freigabe. Das ist der Grund, warum dieser Check trotz `medium` eine `critical`-Nachbarschaft hat: Der Schaden liegt nicht in der Kategorie Caching, sondern in `CH-001` und `SEC-023`.

## Verification

### Modus 1: automated (Felder vorhanden)

```bash
grep -rnE "ttlMs|ttl_ms|cacheScope|cache_scope|CacheableResult" src/ --include="*.py" --include="*.ts"
```

### Modus 2: runtime_test (Felder auf allen fünf Methoden)

```bash
for m in tools/list prompts/list resources/list resources/templates/list; do
  echo "== $m"
  curl -sS -X POST "$MCP_URL" -H 'Content-Type: application/json' \
    -H "Mcp-Method: $m" -H "Mcp-Name: $m" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"$m\",\"params\":{}}" \
    | jq '{ttlMs: .result.ttlMs, cacheScope: .result.cacheScope}'
done
```

`null` bei einer der Methoden ist ein Befund. `resources/read` separat prüfen, es braucht eine URI.

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

## Pass Criteria

- [ ] `ttlMs` und `cacheScope` liegen auf allen fünf Methoden an, sofern der Server sie bedient
- [ ] `ttlMs` ist begründet gewählt, nicht 0 und nicht willkürlich gross — ein Wert oberhalb der Änderungsfrequenz der Quelle liefert veraltete Werkzeuglisten
- [ ] `cacheScope: "public"` steht ausschliesslich über aufruferunabhängigen Inhalten
- [ ] Bei `data_class != "Public Open Data"`: `resources/read` liefert `"private"`, und ein Test hält das fest
- [ ] `tools/list` liefert eine deterministische Reihenfolge, über **Prozessgrenzen** hinweg geprüft
- [ ] Die Reihenfolge stammt aus einer expliziten Sortierung, nicht aus der Registrierungsreihenfolge — letztere ändert sich mit jedem Refactoring des Imports
- [ ] **Gegenprobe:** Der Reihenfolgetest ist einmal gegen eine Fassung mit `set`-Iteration gelaufen und hat dort angeschlagen

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| `cacheScope: "public"` pauschal gesetzt | Zwischeninstanz gibt mandantenbezogene Inhalte weiter |
| `ttlMs` grösser als der Änderungstakt der Quelle | Client arbeitet mit einer Werkzeugliste, die es nicht mehr gibt |
| `ttlMs: 0` als «sicherer Wert» | Kein Caching, jeder Aufruf trifft den Server — die Änderung verpufft |
| Reihenfolge aus `set` oder Registry-Dict | Wechselt beim Neustart; Prompt-Cache trifft nie |
| Stabilitätstest im selben Prozess | Bestätigt eine Stabilität, die es nicht gibt |
| Nur `tools/list` versorgt | Die vier anderen Methoden bleiben schemawidrig |

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

## Effort

S — eine Sortierung und zwei Felder je Methode. Die Entscheidung über `cacheScope` je Ressource kostet mehr Nachdenken als Code.

## References

- [Spec 2026-07-28 — Changelog, Minor #3 und #5](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2549](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2549)
- `CH-001` (Datenresidenz), `SEC-023` (DLP auf Outputs), `ARCH-008` (Resources)
