---
id: ARCH-015
title: "Stateless-Konformität: kein initialize-Handshake, keine Server-Sitzung"
category: ARCH
severity: high
applies_when: 'always'
spec_baseline: 2026-07-28
adoption: advisory
pdf_ref: "SEP-2575, SEP-2567"
spec_ref: "SEP-2575 (PR 2575), SEP-2567 (PR 2567) — Spec-Changelog 2026-07-28, Major #1 und #2"
evidence_required: 3
---

# ARCH-015 — Stateless-Konformität

## Description

Mit `2026-07-28` fällt der Lebenszyklus weg, um den herum jeder MCP-Server bisher gebaut wurde. Zwei Entscheidungen, die zusammengehören:

- **`initialize` / `notifications/initialized` sind entfernt** (SEP-2575). Es gibt keinen Handshake mehr, in dem einmal Protokollversion und Capabilities verhandelt werden. Jede Anfrage trägt beides selbst: `io.modelcontextprotocol/protocolVersion` und `io.modelcontextprotocol/clientCapabilities` in `_meta`.
- **Die Protokoll-Sitzung ist entfernt** (SEP-2567). Kein `Mcp-Session-Id`-Header, keine serverseitige Sitzungstabelle, und `tools/list` / `resources/list` / `prompts/list` dürfen nicht mehr pro Verbindung variieren.

**Warum das ein `high` ist und kein `medium`.** Der gefährliche Fall ist nicht der Server, der abstürzt — der fällt beim ersten Aufruf auf. Der gefährliche Fall ist der Server, der **weiterläuft und stillschweigend degradiert**: Er hält seinen Zustand weiter in einer prozesslokalen Struktur, die per Konvention über die Sitzung adressiert war. Ohne Sitzung landet jeder Request auf demselben Eimer. Bei einem Server mit einem Nutzer merkt das niemand; bei zweien ist es ein Datenleck zwischen Aufrufern, und zwar eines, das keinen Fehler wirft.

**Abgrenzung.** Dieser Check fragt nach dem *Verschwinden* des Handshakes und der Sitzung. Was an ihre Stelle tritt, prüfen zwei andere: `ARCH-016` den `server/discover`-RPC, `ARCH-017` den handle-basierten Zustand. Ein Server kann diesen Check bestehen und an `ARCH-017` scheitern — dann ist er zustandslos verdrahtet und trotzdem zustandsbehaftet gebaut.

## Verification

### Modus 1: automated (Rückstände des Lebenszyklus im Code)

```bash
# Handshake-Reste. Treffer in eigenem Code sind Befunde;
# Treffer unter .venv/ oder node_modules/ sind es nicht.
grep -rnE "initialize|notifications/initialized|InitializeResult|InitializationOptions" \
    src/ --include="*.py" --include="*.ts"

# Sitzungs-Reste
grep -rniE "mcp[-_]session[-_]id|session_manager|SessionManager|sessionId" \
    src/ --include="*.py" --include="*.ts"
```

**Negative Kontrolle, verbindlich:** Beide Muster einmal gegen eine Datei laufen lassen, in der der Begriff sicher vorkommt (z.B. das SDK selbst unter `.venv/`). Meldet der Lauf dort nichts, greift das Muster nicht, und «0 Treffer» im `src/` bedeutet nichts. Siehe SKILL.md §4.1.

### Modus 2: code_review (wo der Zustand tatsächlich liegt)

Der Grep findet Namen, nicht Semantik. Ein Server, der seine Sitzungstabelle `_connections` oder `_ctx_by_client` nennt, hat denselben Fehler ohne einen einzigen Treffer. Zu prüfen ist jede Struktur mit Modul- oder Instanz-Lebensdauer, die **zwischen** Tool-Aufrufen etwas behält:

```python
# ANTI-PATTERN — überlebt den Request und gehört keinem Aufrufer
_LAST_QUERY: dict[str, Any] = {}
_CURSOR_BY_CLIENT: dict[str, str] = {}

@mcp.tool()
async def search_next() -> dict:
    return await fetch(_LAST_QUERY["cursor"])   # wessen Cursor?
```

Erlaubt bleiben Strukturen ohne Aufrufer-Bezug: Verbindungs-Pools, Caches mit reiner Ableitung aus der Quelle, Rate-Limiter-Zähler.

### Modus 3: runtime_test (Reihenfolgeunabhängigkeit)

Zwei Aufrufe desselben Tools mit vertauschter Reihenfolge und dazwischen einem fremden Aufruf müssen dasselbe liefern. Und: `tools/list` zweimal über getrennte Verbindungen aufgerufen liefert dieselbe Menge in derselben Reihenfolge (Reihenfolge selbst prüft `ARCH-020`).

## Pass Criteria

- [ ] Kein `initialize`- / `initialized`-Handler im eigenen Code
- [ ] Kein `Mcp-Session-Id` gelesen, gesetzt oder geroutet
- [ ] Protokollversion und Client-Capabilities werden **pro Request** aus `_meta` gelesen, nicht aus gespeichertem Verhandlungsergebnis
- [ ] Bei nicht unterstützter Version antwortet der Server mit `UnsupportedProtocolVersionError` (`-32022`), nicht mit einem generischen Fehler
- [ ] Keine prozesslokale Struktur trägt Aufrufer-bezogenen Zustand über Requests hinweg — geprüft am Code, nicht nur am Namen
- [ ] Die List-Antworten variieren nicht pro Verbindung
- [ ] **Gegenprobe:** Der Reihenfolge-Test ist einmal gegen eine absichtlich zustandsbehaftete Fassung gelaufen und hat dort angeschlagen. Ein Test, der nur die grüne Richtung kennt, belegt nichts

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Sitzungstabelle bleibt, wird nur nicht mehr über den Header adressiert | Alle Aufrufer teilen einen Eimer — Leck ohne Fehlermeldung |
| Capabilities werden beim ersten Request gemerkt und danach wiederverwendet | Ein zweiter Client mit anderen Capabilities bekommt die des ersten |
| `UnsupportedProtocolVersionError` als `-32603 Internal error` | Client kann nicht auf eine ältere Version zurückfallen |
| Migration nur im HTTP-Pfad, `stdio` behält den Handshake | `ARCH-013`: zwei Transportpfade, zwei Protokolle |
| Grep sauber, weil der Zustand `_cache` heisst | Der Check misst Namen statt Lebensdauer |

## Remediation

```diff
-_SESSIONS: dict[str, SessionState] = {}
-
-@server.initialize()
-async def on_init(params: InitializeParams) -> InitializeResult:
-    _SESSIONS[params.session_id] = SessionState(caps=params.capabilities)
-    return InitializeResult(capabilities=SERVER_CAPS)
-
 @mcp.tool()
-async def search(query: str) -> dict:
-    state = _SESSIONS[current_session_id()]
-    return await _impl.search(query, page=state.page)
+async def search(query: str, cursor: str | None = None) -> dict:
+    # Zustand kommt als Argument herein und geht als Handle hinaus (ARCH-017)
+    return await _impl.search(query, cursor=cursor)
```

Der Umbau hat eine Reihenfolge, und sie ist nicht beliebig: **zuerst** den Zustand in Handles überführen (`ARCH-017`), **dann** den Handshake entfernen. Andersherum steht der Server zwischendurch ohne Adressierung für einen Zustand da, den er noch hält.

## Effort

L — 1–2 Wochen pro Server mit echtem Sitzungszustand. S–M für die Mehrheit des Portfolios: Read-only-Wrapper ohne Zustand verlieren nur den Handshake-Code, und der ist im SDK, nicht im Server.

## References

- [Spec 2026-07-28 — Changelog, Major #1, #2](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2567 — Remove protocol-level sessions](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2567)
- [SEP-2575 — Make MCP stateless](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2575)
- `ARCH-016` (server/discover), `ARCH-017` (Handles), `ARCH-013` (Transportpfade)
