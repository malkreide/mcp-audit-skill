---
id: SCALE-009
title: "Legacy HTTP+SSE abgeschaltet — mit Datum, nicht mit Vorsatz"
category: SCALE
severity: high
applies_when: 'transport != "stdio-only"'
spec_baseline: beide
adoption: advisory
pdf_ref: "SEP-2596"
spec_ref: "SEP-2596 (PR 2596) — Spec-Changelog 2026-07-28, Deprecated #2"
evidence_required: 3
---

# SCALE-009 — Legacy HTTP+SSE mit Abschaltdatum

## Description

Der HTTP+SSE-Transport ist seit `2025-03-26` deprecated. Was `2026-07-28` ändert, ist nicht die Empfehlung, sondern ihre Verbindlichkeit: SEP-2596 stellt ihn unter die neue Feature-Lifecycle-Politik und gibt ihm damit den formalen Zustand **Deprecated** — mit einem Fenster von mindestens zwölf Monaten, also einem frühesten Entfernungstermin von **2027-07-28**.

**Warum es diesen Check braucht, obwohl «deprecated seit 2025-03» seit anderthalb Jahren im Raum steht.** Genau deswegen. Eine Empfehlung ohne Termin erzeugt keinen Vorgang; sie erzeugt einen Kompatibilitätspfad, den niemand abschaltet, weil er niemanden stört. Der Legacy-Pfad ist dabei nicht neutral: Er ist ein zweiter Netzweg mit eigener Verdrahtung, und die Erfahrung aus `ARCH-013` ist, dass der zweite Pfad die Härtung des ersten nicht mitbekommt. Ein Server, dessen Streamable-HTTP-Endpunkt Host-Allow-Listing (`SEC-024`) und Header-Prüfung (`SCALE-008`) durchsetzt, während der SSE-Endpunkt daneben weiterläuft, hat beides nicht.

**`beide` als Baseline**, weil die Abschaltung nicht auf die Migration wartet: Ein Server auf der alten Baseline soll den Legacy-Pfad heute schliessen, nicht erst mit dem Sprung auf `2026-07-28`.

**Auf `2026-07-28` verschärft sich die Lage zusätzlich**, denn dort ist auch der GET-Endpunkt weg (siehe `SCALE-010`). Ein verbliebener SSE-Pfad spricht dann ein Protokoll, das der Server nach eigener Aussage nicht mehr führt.

## Verification

### Modus 1: automated (Legacy-Pfad im Code)

```bash
# Eigener SSE-Endpunkt neben dem Streamable-HTTP-Pfad
grep -rnE "sse_app|SseServerTransport|/sse|text/event-stream|EventSourceResponse" \
    src/ --include="*.py" --include="*.ts"

# Route-Registrierungen gegenhalten
grep -rnE "mount|add_route|@app\.(get|post)|router\." src/ --include="*.py"
```

Der zweite Grep ist der wichtigere: Ein Legacy-Pfad, der über `mount("/sse", ...)` hereinkommt, trägt das Wort `sse` genau einmal — in einer Zeile, die der erste Grep findet, aber nicht als Transport erkennbar macht.

### Modus 2: runtime_test (antwortet er noch?)

```bash
curl -sS -i -H 'Accept: text/event-stream' "$MCP_BASE/sse" | head -5
```

Erwartet: `404` oder `410`. Ein `200` mit `Content-Type: text/event-stream` ist der Befund — unabhängig davon, was der Code nahelegt.

**Gegen die tatsächlich ausgelieferte Instanz prüfen, nicht gegen den lokalen Start.** Der Legacy-Pfad überlebt typischerweise dort, wo ihn niemand sucht: in einer älteren Deployment-Konfiguration, hinter einem Ingress-Eintrag, in einer Umgebungsvariable, die den Transport auf `dual` stellt.

### Modus 3: documentation_check (Datum vorhanden)

Bei noch offenem Pfad: README oder CHANGELOG nennt ein Abschaltdatum.

## Pass Criteria

- [ ] Der Server bedient keinen HTTP+SSE-Legacy-Endpunkt mehr — geprüft an der ausgelieferten Instanz, nicht nur am Code
- [ ] Ist er noch offen, nennt README oder CHANGELOG ein **Datum**, nicht «demnächst»
- [ ] Das Datum liegt nicht nach dem frühesten Entfernungstermin (2027-07-28), oder die Abweichung ist begründet
- [ ] Ist er noch offen, gelten dort dieselben Kontrollen wie am Streamable-HTTP-Pfad: `SEC-024` (Host-Allow-List), `SEC-016` (Bind-Adresse), Auth — belegt je einzeln, nicht behauptet
- [ ] Das README nennt Streamable HTTP als den unterstützten Transport, ohne SSE als gleichwertige Alternative zu führen
- [ ] Die Deployment-Konfiguration (Ingress, Railway/Render, Compose) enthält keine Route mehr auf den Legacy-Pfad
- [ ] **Gegenprobe:** Der `curl`-Aufruf ist einmal gegen einen Server mit offenem SSE-Pfad gelaufen und hat dort `200` bekommen — sonst belegt ein `404` nur, dass die URL falsch war

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Code entfernt, Ingress-Route bleibt | Pfad antwortet weiter, nur nicht mehr aus dem Repo erklärbar |
| Legacy-Pfad ohne Host-Allow-List | `SEC-024` gilt für einen Endpunkt und nicht für den zweiten |
| «deprecated» im README ohne Datum | Nach anderthalb Jahren immer noch offen — der Ist-Zustand |
| Abschaltung nur lokal geprüft | Die ausgelieferte Instanz ist die, die zählt |
| `404` als Beleg ohne Gegenprobe | Ein Tippfehler in der URL besteht den Check |

## Remediation

```diff
-app.mount("/sse", sse_app())          # Legacy, deprecated seit 2025-03-26
 app.mount("/mcp", streamable_http_app())
```

Und im README, Sektion «MCP Protocol Version»:

> **Transport:** Streamable HTTP (`/mcp`). Der HTTP+SSE-Pfad wurde am 2026-09-30 abgeschaltet.

Bleibt der Pfad im Restfenster offen, gehört er in dieselbe Härtungskette wie der neue — nicht in eine Ausnahme. Ein Kompatibilitätspfad, der die Kontrollen des Hauptpfads nicht trägt, ist die Umgehung dieser Kontrollen.

## Effort

S, wenn nur eine Route zu entfernen ist. M, wenn Clients daran hängen: dann braucht es eine Ankündigung mit Frist und eine Prüfung, wer den Pfad noch nutzt — Zugriffszahlen vor dem Abschalten, nicht danach.

## References

- [Spec 2026-07-28 — Changelog, Deprecated #2](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2596](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2596)
- [Feature lifecycle and deprecation policy](https://modelcontextprotocol.io/community/feature-lifecycle)
- `ARCH-013` (alle Transportpfade), `SCALE-010`, `SEC-024`, `SEC-016`
