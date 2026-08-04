---
id: ARCH-021
title: "Extensions deklariert und versioniert — Tasks sind kein Kern-Feature mehr"
category: ARCH
severity: medium
applies_when: 'always'
spec_baseline: 2026-07-28
adoption: advisory
pdf_ref: "SEP-2663"
spec_ref: "SEP-2663 (PR 2663) — Spec-Changelog 2026-07-28, Major #6; extensions-Feld: Minor #1"
evidence_required: 2
---

# ARCH-021 — Extensions-Deklaration

## Description

`2026-07-28` zieht eine Trennlinie zwischen Kernprotokoll und Erweiterungen. `ClientCapabilities` und `ServerCapabilities` bekommen ein `extensions`-Feld; was darüber hinaus geht, läuft als versionierte Extension mit einer Kennung im Namensraum `io.modelcontextprotocol/*`.

Der erste Umzugskandidat ist **Tasks**. In `2025-11-25` waren sie experimenteller Teil des Kerns; jetzt sind sie `io.modelcontextprotocol/tasks` — und die Extension ist nicht dieselbe API:

| `2025-11-25` (Kern, experimentell) | `2026-07-28` (Extension) |
|---|---|
| `tasks/result` blockiert bis fertig | `tasks/get`, aktiv gepollt |
| — | `tasks/update` für Client→Server-Eingaben |
| `tasks/list` | entfernt |
| Task-Handle nur nach Opt-in pro Request | Server darf unaufgefordert einen Handle liefern |

**Der letzte Punkt ist der, der Server bricht, die nichts geändert haben.** Ein Server auf der neuen Baseline darf einen Task-Handle zurückgeben, ohne dass der Client ihn angefordert hat. Ein Client, der das nicht erwartet, liest ihn als Ergebnis. Wer Tasks nutzt, muss deshalb wissen und deklarieren, welche Fassung er spricht — die Deklaration ist hier keine Formalie, sondern der einzige Weg, wie das Gegenüber die Frage beantworten kann.

**Für die Mehrheit des Portfolios ist die korrekte Antwort: keine Extensions.** Dann ist dieser Check in einem Satz erfüllt — und das ist Absicht. Er existiert, damit die Server, die eine führen, sie nicht stillschweigend führen.

## Verification

### Modus 1: automated (Extensions im Code)

```bash
grep -rnE "io\.modelcontextprotocol/|extensions" src/ --include="*.py" --include="*.ts"

# Tasks in beiden Fassungen
grep -rnE "tasks/(get|update|result|list)|TaskHandle|task_id" src/ --include="*.py" --include="*.ts"
```

Findet der zweite Grep `tasks/result` oder `tasks/list`, spricht der Server die **alte** Fassung — auf `spec_baseline: 2026-07-28` ein Befund, unabhängig davon, ob es funktioniert.

### Modus 2: runtime_test (Deklaration deckt die Realität)

`server/discover` (`ARCH-016`) abfragen und die genannten Extensions gegen den Code halten. Beide Richtungen sind Befunde:

- **Deklariert, nicht implementiert** — der Client wählt einen Pfad, den der Server nicht bedient.
- **Implementiert, nicht deklariert** — das gefährlichere. Der Client kann sich nicht darauf einstellen, und bei Tasks heisst das: ein unerwarteter Handle statt eines Ergebnisses.

## Pass Criteria

- [ ] Führt der Server keine Extension, ist das im README in einem Satz festgehalten — nicht bloss unerwähnt
- [ ] Jede geführte Extension erscheint mit vollständiger, versionierter Kennung (`io.modelcontextprotocol/tasks`) in den Server-Capabilities
- [ ] Die Deklaration deckt sich in **beide** Richtungen mit dem Code
- [ ] Bei Tasks: Der Server spricht die Extension-Fassung (`tasks/get` / `tasks/update`), nicht `tasks/result` oder `tasks/list`
- [ ] Bei Tasks: Das README sagt, ob unaufgeforderte Task-Handles zurückgegeben werden, und die Tool-Descriptions sagen es bei den betroffenen Tools
- [ ] Eigene, nicht-offizielle Erweiterungen laufen unter einem eigenen Namensraum, nie unter `io.modelcontextprotocol/*`

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Tasks weiter über `tasks/result` | Blockierender Aufruf gegen eine API, die Polling erwartet |
| Extension implementiert, nicht deklariert | Client bekommt einen Handle, wo er ein Ergebnis erwartet |
| Eigene Erweiterung unter `io.modelcontextprotocol/` | Namensraum-Anmassung; kollidiert mit einer künftigen offiziellen Extension |
| Kennung ohne Version | Zwei inkompatible Fassungen unter einem Namen |
| README schweigt zu Extensions | «keine» und «nicht dokumentiert» sind ununterscheidbar — §2.6 |

## Remediation

```python
SERVER_CAPABILITIES = {
    "tools": {},
    "resources": {},
    # Leer ist eine Aussage. Weglassen ist keine.
    "extensions": {},
}
```

Mit Tasks:

```python
SERVER_CAPABILITIES = {
    "tools": {},
    "extensions": {
        "io.modelcontextprotocol/tasks": {"version": "1"},
    },
}
```

Im README, Sektion «MCP Protocol Version»:

> Dieser Server spricht `2026-07-28` und führt keine Extensions.

## Effort

S — für Server ohne Extensions ein Feld und ein Satz. M, wenn Tasks von der Kern-Fassung auf die Extension umzustellen sind: blockierender Abruf wird zu Polling, und das betrifft auch den aufrufenden Agenten.

## References

- [Spec 2026-07-28 — Changelog, Major #6, Minor #1](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2663](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2663)
- [Extensions overview](https://modelcontextprotocol.io/docs/extensions/overview)
- `ARCH-016` (server/discover), `ARCH-012` (Spec-Versionierung)
