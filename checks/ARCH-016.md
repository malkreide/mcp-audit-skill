---
id: ARCH-016
title: "server/discover ist implementiert — der RPC ist MUSS, nicht Kür"
category: ARCH
severity: high
applies_when: 'always'
spec_baseline: 2026-07-28
adoption: advisory
pdf_ref: "SEP-2575"
spec_ref: "SEP-2575 (PR 2575) — Spec-Changelog 2026-07-28, Major #3"
evidence_required: 3
---

# ARCH-016 — `server/discover`

## Description

Wenn der `initialize`-Handshake wegfällt (`ARCH-015`), fehlt der Ort, an dem ein Server bisher gesagt hat, wer er ist und was er kann. `server/discover` ist dieser Ort — und die Spec ist an dieser Stelle asymmetrisch formuliert:

> Servers **MUST** implement this RPC to advertise their supported protocol versions, capabilities, and identity. Clients **MAY** call it before any other request.

**Diese Asymmetrie ist der ganze Check.** Weil Clients den RPC nicht rufen müssen, funktioniert ein Server ohne ihn im Alltag scheinbar tadellos: Tools laufen, Aufrufe kommen an, nichts ist rot. Der Fehler wird erst sichtbar, wenn ein Client Versionsauswahl betreiben will — oder auf `stdio`, wo `server/discover` als Rückwärtskompatibilitäts-Sonde dient, um überhaupt herauszufinden, ob das Gegenüber die neue Spec spricht. Dann antwortet der Server mit «Methode unbekannt», und der Client kann nicht unterscheiden, ob er einen alten Server vor sich hat oder einen neuen mit einer Lücke.

Ein fehlendes `server/discover` ist damit kein fehlendes Feature, sondern eine **falsche Auskunft über die eigene Protokollversion**. Genau deshalb `high` und nicht `medium`.

## Verification

### Modus 1: automated (Handler vorhanden)

```bash
grep -rnE "server/discover|server_discover|def discover|DiscoverResult" \
    src/ --include="*.py" --include="*.ts"
```

Findet das nichts, ist der Ausgang **nicht** `pass`. Er ist `fail`, wenn der Server auf `2026-07-28` steht — oder `not_verified`, wenn nicht feststellbar ist, ob das SDK den RPC selbst beisteuert. Viele Tier-1-SDKs implementieren ihn im Transport; dann liegt der Beleg in der SDK-Version, nicht im Server-Code.

### Modus 2: config_check (SDK stellt ihn bereit?)

```bash
python -c "import mcp, importlib.metadata as m; print(m.version('mcp'))"
grep -rn "discover" "$(python -c 'import mcp,pathlib;print(pathlib.Path(mcp.__file__).parent)')" \
    --include="*.py" -l | head
```

Beisteuert das SDK den RPC, ist die Pass-Bedingung eine **gepinnte Untergrenze** der SDK-Version im Manifest — sonst hängt die Konformität an dem, was zufällig installiert ist.

### Modus 3: runtime_test (die Antwort ist vollständig)

```bash
# Streamable HTTP
curl -sS -X POST "$MCP_URL" \
  -H 'Content-Type: application/json' \
  -H 'Mcp-Method: server/discover' -H 'Mcp-Name: server/discover' \
  -d '{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{}}' | jq .
```

Die Antwort muss **alle drei** Teile tragen: unterstützte Protokollversionen, Capabilities, Identität. Zwei von dreien ist kein Teilerfolg — ein Client, der die Versionsliste nicht findet, kann nicht auswählen.

## Pass Criteria

- [ ] `server/discover` antwortet, über **jeden** bedienten Transportpfad (`ARCH-013`)
- [ ] Die Antwort nennt die unterstützten Protokollversionen als Liste, nicht als einzelnen String
- [ ] Die Antwort nennt die Server-Capabilities, inklusive `extensions` sofern welche geführt werden (`ARCH-021`)
- [ ] Die Antwort nennt die Server-Identität (Name, Version) — und die Version stammt aus den Paket-Metadaten, nicht aus einem Literal (`IDENT-002`)
- [ ] Stammt der RPC aus dem SDK, ist dessen Mindestversion im Manifest gepinnt
- [ ] Ein Test ruft `server/discover` auf und prüft alle drei Bestandteile einzeln — nicht nur, dass ein 200 zurückkam
- [ ] **Gegenprobe:** Der Test ist einmal gegen einen Server ohne den Handler gelaufen und hat dort angeschlagen

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| RPC fehlt, «Client ruft ihn ja nicht» | Versionsaushandlung unmöglich; auf `stdio` ununterscheidbar von einem Alt-Server |
| Antwort nennt eine Version als String statt als Liste | Client kann keine gemeinsame Version wählen |
| Identität mit hartkodierter Versionsnummer | `IDENT-002`: Version driftet gegen das publizierte Artefakt |
| Handler nur im HTTP-Pfad registriert | `ARCH-013`: der `stdio`-Pfad kann nicht sondiert werden |
| Test prüft nur den Statuscode | Eine leere Antwort besteht |

## Remediation

```python
from importlib.metadata import version

SUPPORTED_PROTOCOL_VERSIONS = ["2026-07-28"]

@server.discover()
async def discover() -> DiscoverResult:
    return DiscoverResult(
        protocolVersions=SUPPORTED_PROTOCOL_VERSIONS,
        capabilities=SERVER_CAPABILITIES,          # inkl. extensions, s. ARCH-021
        serverInfo={
            "name": "zurich-opendata-mcp",
            "version": version("zurich-opendata-mcp"),   # nie ein Literal
        },
    )
```

```python
def test_discover_reports_all_three_parts(client):
    result = client.call("server/discover")
    assert result["protocolVersions"] == ["2026-07-28"]
    assert "tools" in result["capabilities"]
    assert result["serverInfo"]["version"] == version("zurich-opendata-mcp")
```

## Effort

S — wenige Zeilen, sofern das SDK den RPC nicht ohnehin mitbringt. M, wenn die Capability-Struktur erst aufgebaut werden muss.

## References

- [Spec 2026-07-28 — Changelog, Major #3](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2575](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2575)
- `ARCH-015` (Stateless), `ARCH-021` (Extensions), `IDENT-002` (Version aus Metadaten)
