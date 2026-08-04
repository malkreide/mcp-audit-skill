---
id: ARCH-017
title: "Zustand nur über server-geprägte Handles als Tool-Argumente"
category: ARCH
severity: high
applies_when: 'always'
spec_baseline: 2026-07-28
adoption: advisory
pdf_ref: "SEP-2567"
spec_ref: "SEP-2567 (PR 2567) — Spec-Changelog 2026-07-28, Major #1"
evidence_required: 3
---

# ARCH-017 — Handle-basierter Zustand

## Description

Die Spec streicht nicht den Zustand, sondern seinen impliziten Kanal:

> Servers that need cross-call state use explicit, server-minted handles passed as ordinary tool arguments.

Drei Worte tragen die Last. **Explicit:** Der Handle steht im Schema des Tools, ein Aufrufer sieht ihn. **Server-minted:** Der Server prägt ihn, der Client denkt ihn sich nicht aus. **As ordinary tool arguments:** Er reist im Argument, nicht in einem Header und nicht in einer Tabelle neben dem Request.

**Dieser Check ist die Ersatzdimension für `SEC-009`.** Dort war die Frage, ob die Sitzungs-ID rateresistent und an eine Identität gebunden ist. Die Sitzungs-ID gibt es nicht mehr, die Frage schon: Ein Handle, der `cursor=42` heisst, ist eine ratbare Referenz auf fremden Zustand. Wer die Sitzung ersatzlos entfernt und den Cursor als Klartext-Integer herausgibt, hat die Angriffsfläche nicht beseitigt, sondern in die Tool-Signatur verschoben — und dort prüft sie kein Auth-Layer mehr.

**Der zweite Fehler ist leiser.** Ein Handle ohne Ablauf ist ein Zustand ohne Ende. Bei der Sitzung erledigte das Aufräumen der Verbindungsabbruch; ohne Sitzung gibt es kein Ereignis mehr, an dem irgendetwas aufräumt. Ein Server, der Handles in einem Dict hält, hat ein Leck, das keine Testsuite bemerkt, weil es sich in Tagen zeigt und nicht in Sekunden.

## Verification

### Modus 1: code_review (Zustand, der Requests überlebt)

Jede Struktur mit Modul- oder Instanzlebensdauer inventarisieren und je Struktur beantworten: Wer adressiert sie, und womit?

```bash
# Modul-Level-Container als Kandidatenliste
grep -rnE "^_?[A-Z_]+(: *(dict|list|set))? *= *(\{\}|\[\]|set\(\)|defaultdict)" \
    src/ --include="*.py"
```

Kandidat ist nicht gleich Befund: Pools, Rate-Limiter und reine Ableitungscaches sind legitim. Befund ist jede Struktur, die **aufruferbezogene** Daten hält.

### Modus 2: code_review (Beschaffenheit des Handles)

```bash
grep -rnE "handle|token|cursor|continuation|page_token" src/ --include="*.py" --include="*.ts"
```

Pro Fundstelle: Wie entsteht der Wert, wie lange gilt er, und was passiert bei einem fremden Wert?

**Pass-Pattern:**

```python
import secrets, time

_HANDLES: dict[str, tuple[float, SearchState]] = {}
HANDLE_TTL_S = 900

def mint_handle(state: SearchState) -> str:
    h = secrets.token_urlsafe(32)          # geprägt, nicht geraten
    _HANDLES[h] = (time.monotonic() + HANDLE_TTL_S, state)
    return h

def resolve_handle(h: str) -> SearchState:
    _evict_expired()                        # Ablauf ist Pflicht, nicht Kür
    entry = _HANDLES.get(h)
    if entry is None:
        raise ToolError("Handle ist abgelaufen oder unbekannt. Suche neu starten.")
    return entry[1]
```

### Modus 3: runtime_test (Fremdheit und Ablauf)

Ein erfundener Handle muss einen sauberen Tool-Execution-Error erzeugen (`OBS-001`), keinen Stacktrace und keinen fremden Datensatz. Ein abgelaufener Handle ebenso — und zwar unterscheidbar formuliert, damit der aufrufende Agent weiss, dass Neuanfang die richtige Reaktion ist.

## Pass Criteria

- [ ] Jeder aufruferbezogene Zustand ist über einen Handle adressiert, der im Tool-Schema steht
- [ ] Handles werden serverseitig mit ≥128 Bit Entropie geprägt (`secrets.token_urlsafe(32)` / `crypto.randomUUID()`), nie fortlaufend und nie aus Nutzereingaben abgeleitet
- [ ] Jeder Handle trägt eine TTL, und es gibt einen Pfad, der abgelaufene Einträge tatsächlich entfernt — nicht nur beim Zugriff prüft
- [ ] Ein unbekannter oder abgelaufener Handle liefert einen Execution-Error mit Handlungsanweisung, nie stillschweigend andere Daten
- [ ] Bei mehr als einer Replica liegt der Handle-Speicher ausserhalb des Prozesses, sonst trifft der Folgeaufruf die falsche Instanz
- [ ] Bei `auth_model != "none"`: Der Handle ist an die authentifizierte Identität gebunden; ein fremder Aufrufer bekommt 401/403 statt Daten
- [ ] **Gegenprobe:** Der Fremd-Handle-Test ist gegen eine Fassung ohne Prüfung gelaufen und hat dort Daten bekommen

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| `cursor` ist ein Offset-Integer | Ratbare Referenz auf fremde Ergebnismengen — `SEC-009` in neuer Verpackung |
| Handle vom Client gewählt | Der Client bestimmt, welchen Zustand er liest |
| Kein TTL, Dict wächst unbegrenzt | Speicherleck, das erst nach Tagen sichtbar wird |
| TTL nur beim Zugriff geprüft | Nie abgerufene Einträge bleiben für immer |
| In-Memory-Dict bei ≥2 Replicas | Folgeaufruf landet auf der Instanz ohne den Handle |
| Unbekannter Handle → leere Ergebnismenge | `FID-003`: Leermenge als Abwesenheit gelesen, Modell konfabuliert |

## Remediation

```diff
 @mcp.tool()
-async def search_next() -> dict:
-    return await _impl.fetch(_LAST_QUERY["cursor"])
+async def search(query: str, continuation: str | None = None) -> dict:
+    """... `continuation`: Handle aus einem vorherigen Aufruf. Gültig 15 Minuten."""
+    state = resolve_handle(continuation) if continuation else SearchState(query)
+    page, nxt = await _impl.fetch(state)
+    return {"results": page, "continuation": mint_handle(nxt) if nxt else None}
```

Der Handle gehört **in die Tool-Description**, nicht nur ins Schema — sonst rät das Modell, wann es ihn mitschicken darf (`FID-005`).

## Effort

M — pro zustandsbehaftetem Tool ein bis zwei Tage. S für Server ohne Blätterung. L, wenn zusätzlich ein prozessexterner Speicher eingeführt werden muss.

## References

- [Spec 2026-07-28 — Changelog, Major #1](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2567](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2567)
- `ARCH-015` (Stateless), `SEC-009` (Vorgänger auf der alten Baseline), `FID-003`, `FID-005`
