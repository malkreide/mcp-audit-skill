---
id: SCALE-008
title: "Mcp-Method und Mcp-Name sind Pflichtheader auf Streamable-HTTP-POSTs"
category: SCALE
severity: high
applies_when: 'transport != "stdio-only"'
spec_baseline: 2026-07-28
adoption: advisory
pdf_ref: "SEP-2243"
spec_ref: "SEP-2243 (PR 2243) — Spec-Changelog 2026-07-28, Minor #4"
evidence_required: 3
---

# SCALE-008 — Pflichtheader `Mcp-Method` / `Mcp-Name`

## Description

Streamable HTTP verlangt auf jedem POST zwei Header: `Mcp-Method` mit der JSON-RPC-Methode und `Mcp-Name` mit dem Namen des adressierten Tools, Prompts oder der Ressource. Weichen Header und Body voneinander ab, ist die Antwort `HeaderMismatchError` — Code **`-32020`**, umnummeriert von `-32001` durch die neue Fehlercode-Politik (Minor #12).

**Warum das eine Schicht betrifft, die keinen Body liest.** Bisher musste jede Instanz zwischen Client und Server den JSON-RPC-Body parsen, um zu wissen, was durchläuft — ein Gateway, das nur `searchDocuments` durchlassen soll (`SEC-014`), ein Rate-Limiter mit Grenzen je Werkzeug, ein Logpfad, der Methoden zählt. Mit den Headern steht das im Klartext an der Anfrage.

**Und genau daraus entsteht der Angriff, den dieser Check abwehrt.** Wenn eine Zwischenschicht ihre Entscheidung am Header trifft und der Server seine am Body, entscheiden zwei Instanzen über zwei verschiedene Anfragen. Ein Client schickt `Mcp-Name: searchDocuments` im Header und `deleteRecord` im Body: Das Gateway erlaubt, der Server führt aus. Die Header sind deshalb nicht bloss Metadaten — **die Prüfung ihrer Übereinstimmung ist eine Sicherheitsgrenze**, und sie muss serverseitig stattfinden, weil nur dort beide Seiten vorliegen.

Deshalb `high`, obwohl der Changelog den Punkt unter «Minor changes» führt: Für die Spec ist es eine kleine Ergänzung, für ein Deployment mit Gateway ist es die Naht, an der Allow-Listing hält oder reisst.

`x-mcp-header` — Custom-Header aus Tool-Parametern, im selben SEP — ist eine eigene Angriffsfläche und steht in `SEC-027`.

## Verification

### Modus 1: automated (Prüfung vorhanden)

```bash
grep -rniE "mcp-method|mcp_method|mcp-name|mcp_name|HeaderMismatch|-32020" \
    src/ --include="*.py" --include="*.ts"
```

Negative Kontrolle: dasselbe Muster gegen das installierte SDK laufen lassen. Bringt es dort auch nichts, greift es nicht, und «0 Treffer» im `src/` sagt nichts.

### Modus 2: runtime_test (Übereinstimmung wird erzwungen)

Drei Aufrufe, und alle drei gehören in die Evidenz:

```bash
# a) Header passt zum Body → 200, Ergebnis
curl -sS -X POST "$MCP_URL" -H 'Content-Type: application/json' \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: searchDocuments' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"searchDocuments","arguments":{"query":"x"}}}'

# b) Header widerspricht dem Body → -32020, KEINE Ausführung
curl -sS -X POST "$MCP_URL" -H 'Content-Type: application/json' \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: searchDocuments' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"deleteRecord","arguments":{}}}'

# c) Header fehlt ganz → Fehler, nicht stille Annahme
curl -sS -X POST "$MCP_URL" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"searchDocuments","arguments":{"query":"x"}}}'
```

**Fall (a) ist nicht optional.** Ohne ihn belegt ein abgelehntes (b) nur, dass der Server irgendetwas ablehnt — womöglich alles. Erst das Paar zeigt, dass er die Übereinstimmung prüft und nicht bloss kaputt ist. Dieselbe Konstruktion wie das Port-Paar in `SEC-024`.

### Modus 3: code_review (macht der Client es auch?)

Ruft der Server selbst MCP-Server auf, setzt er die Header auf ausgehenden Requests.

## Pass Criteria

- [ ] Der Server liest `Mcp-Method` und `Mcp-Name` auf eingehenden POSTs
- [ ] Widerspruch zwischen Header und Body → `-32020` **vor** jeder Ausführung
- [ ] Fehlende Header werden abgelehnt, nicht aus dem Body ergänzt
- [ ] **Evidence-Paar:** Ein Test belegt die Ablehnung bei Widerspruch **und** die Bedienung bei Übereinstimmung
- [ ] Der Fehlercode ist `-32020`, nicht das alte `-32001`
- [ ] Gibt es ein Gateway oder eine Allow-List (`SEC-014`, `SCALE-005`), entscheidet es am Header — und der Server prüft trotzdem gegen den Body
- [ ] Ausgehende Requests des Servers tragen beide Header
- [ ] Der Reverse Proxy reicht die Header durch und filtert sie nicht als unbekannt heraus

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Header werden gelesen, aber nicht gegen den Body geprüft | Gateway und Server entscheiden über verschiedene Anfragen |
| Fehlender Header wird aus dem Body ergänzt | Die Prüfung ist tautologisch und schützt nichts |
| Fehlercode `-32001` beibehalten | Client erkennt den Fall nicht; `-32001` ist jetzt implementierungsdefiniert |
| Nur der Negativtest existiert | Ein Server, der alles ablehnt, besteht |
| Ingress filtert `Mcp-*` als unbekannte Header | Jeder Request scheitert am Pflichtheader — und zwar erst in Produktion |

## Remediation

```python
HEADER_MISMATCH = -32020

async def enforce_mcp_headers(request: Request) -> None:
    method = request.headers.get("Mcp-Method")
    name = request.headers.get("Mcp-Name")
    if not method or not name:
        raise JsonRpcError(HEADER_MISMATCH, "Mcp-Method und Mcp-Name sind erforderlich")
    body = await request.json()
    body_method = body.get("method")
    body_name = (body.get("params") or {}).get("name", body_method)
    if method != body_method or name != body_name:
        raise JsonRpcError(
            HEADER_MISMATCH,
            f"Header ({method}/{name}) widerspricht dem Body "
            f"({body_method}/{body_name})",
        )
```

```python
def test_header_mismatch_is_rejected(client):
    r = client.post_raw(headers={"Mcp-Method": "tools/call", "Mcp-Name": "searchDocuments"},
                        body={"method": "tools/call", "params": {"name": "deleteRecord"}})
    assert r.json()["error"]["code"] == -32020

def test_matching_header_is_served(client):
    # Ohne diesen Test belegt der obige nur, dass irgendetwas abgelehnt wird
    r = client.post_raw(headers={"Mcp-Method": "tools/call", "Mcp-Name": "searchDocuments"},
                        body={"method": "tools/call", "params": {"name": "searchDocuments",
                                                                 "arguments": {"query": "x"}}})
    assert "result" in r.json()
```

## Effort

S — eine Middleware und zwei Tests, sofern das SDK die Prüfung nicht mitbringt. M mit Gateway, weil dessen Regeln von Body- auf Header-Auswertung umgestellt werden.

## References

- [Spec 2026-07-28 — Changelog, Minor #4 und #12](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2243](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2243)
- `SEC-027` (x-mcp-header), `SEC-014` (Tool-Allow-Listing), `SCALE-005` (Gateway), `SEC-024`
