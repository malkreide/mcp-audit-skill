---
id: ARCH-018
title: "resultType auf allen Results — «complete» ist kein Default, den man weglässt"
category: ARCH
severity: medium
applies_when: 'always'
spec_baseline: 2026-07-28
adoption: advisory
pdf_ref: "SEP-2322"
spec_ref: "SEP-2322 (PR 2322) — Spec-Changelog 2026-07-28, Major #8"
evidence_required: 2
---

# ARCH-018 — `resultType` auf allen Results

## Description

Seit `2026-07-28` trägt **jedes** Result ein Pflichtfeld `resultType`, mit genau zwei Werten: `"complete"` für ein fertiges Ergebnis und `"input_required"` für den Zwischenstand eines Multi-Round-Trip-Requests (`HITL-006`).

Die Falle steckt im zweiten Satz des Changelog-Eintrags:

> Clients **MUST** treat results from earlier-protocol servers that omit the field as `"complete"`.

Das ist eine Rückwärtskompatibilitäts-Regel für den Client, und sie macht diesen Check leise. Ein Server, der `resultType` schlicht weglässt, funktioniert bei jedem korrekten Client — der ergänzt `"complete"` und macht weiter. Nichts wird rot. Der Server behauptet damit aber, `2026-07-28` zu sprechen, und verlässt sich für seine Korrektheit auf eine Klausel, die es für **ältere** Server gibt.

Teuer wird das erst, wenn der Server irgendwann MRTR braucht: Dann ist `resultType` plötzlich bedeutungstragend, und die Stelle, an der es hätte gesetzt werden müssen, ist über alle Tool-Rückgaben verteilt. Deshalb `medium` statt `high` — es bricht heute nichts, aber es ist Schuld, die verzinst wird.

## Verification

### Modus 1: automated (Feld vorhanden)

```bash
grep -rnE "resultType|result_type" src/ --include="*.py" --include="*.ts"
```

Kommt das Feld nirgends vor und steuert das SDK es nicht selbst bei, ist das ein Befund. Steuert das SDK es bei, gehört der Beleg in die Evidenz — mit SDK-Version.

### Modus 2: runtime_test (das Feld ist wirklich draussen)

```bash
curl -sS -X POST "$MCP_URL" -H 'Content-Type: application/json' \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: searchDocuments' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"searchDocuments","arguments":{"query":"test"}}}' \
  | jq '.result.resultType'
```

Erwartet: `"complete"`. `null` ist ein Befund — und zwar einer, den nur dieser Aufruf sichtbar macht, weil ein Client ihn wegkompensiert.

Gegen **jeden** Ergebnisweg prüfen, nicht nur gegen den Erfolgspfad: auch der Fehlerpfad mit `isError: true` ist ein Result und trägt `resultType`.

## Pass Criteria

- [ ] `resultType` liegt auf jedem Result an — Erfolgs- **und** Fehlerpfad
- [ ] Der Wert ist `"complete"`, solange der Server kein MRTR führt
- [ ] Wird MRTR geführt, ist `"input_required"` ausschliesslich dem Zwischenstand vorbehalten (`HITL-006`)
- [ ] Stammt das Feld aus dem SDK, ist dessen Mindestversion im Manifest gepinnt
- [ ] Ein Test prüft das Feld am tatsächlichen Wire-Format, nicht am Rückgabewert der Python-Funktion — dazwischen liegt die Serialisierung, und genau dort geht es verloren

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Feld weggelassen, «Client ergänzt das» | Server stützt seine Konformität auf eine Regel für Alt-Server |
| Nur auf dem Erfolgspfad gesetzt | Fehler-Results sind schemawidrig |
| Test prüft die Funktionsrückgabe | Die Serialisierungsschicht ist ungeprüft — dort verschwindet das Feld |
| `"input_required"` als Sammelwert für «unvollständig» | Client wartet auf eine Eingabeaufforderung, die nie kommt |

## Remediation

```python
def complete(payload: dict) -> dict:
    return {"resultType": "complete", **payload}

@mcp.tool()
async def search_documents(query: str) -> dict:
    try:
        return complete({"content": await _impl.search(query)})
    except UpstreamError as e:
        return complete({"isError": True, "content": [text(mask(e))]})
```

Eine Hilfsfunktion statt eines Feldes an 30 Stellen: Das Feld an jeder Rückgabe von Hand zu setzen ist genau die Sorte Pflicht, die beim 31. Tool vergessen wird.

## Effort

S — eine Hilfsfunktion und ein Durchgang durch die Tool-Rückgaben. Entfällt ganz, wenn das SDK das Feld setzt.

## References

- [Spec 2026-07-28 — Changelog, Major #8](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2322](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2322)
- `HITL-006` (MRTR), `OBS-001` (Fehlerpfad)
