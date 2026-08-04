---
id: ARCH-019
title: "Roots, Sampling und Logging: keine Neuimplementierung, Bestand mit Fristdatum"
category: ARCH
severity: medium
applies_when: 'always'
spec_baseline: beide
adoption: advisory
pdf_ref: "SEP-2577"
spec_ref: "SEP-2577 (PR 2577), SEP-2596 (PR 2596) — Spec-Changelog 2026-07-28, Deprecated #1"
evidence_required: 2
---

# ARCH-019 — Deprecated Features: Roots, Sampling, Logging

## Description

`2026-07-28` erklärt drei Features für deprecated (SEP-2577) und stellt sie unter die neue Feature-Lifecycle-Politik (SEP-2596) mit einem **Fenster von mindestens zwölf Monaten**:

| Feature | Empfohlene Migration laut Spec |
|---|---|
| **Roots** | Verzeichnisse und Dateien über Tool-Parameter, Resource-URIs oder Server-Konfiguration übergeben |
| **Sampling** | Direkt gegen die API des LLM-Anbieters integrieren |
| **Logging** | Auf `stderr` schreiben (stdio) oder OpenTelemetry verwenden |

**Warum `beide` und nicht `2026-07-28`.** Ein Server, der heute auf der alten Baseline steht, wird in Welle A–D migriert. Ein Sampling-Pfad, den er *jetzt* neu baut, ist Arbeit, die in derselben Migration wieder herausfällt. Der Check greift deshalb auf beiden Ständen — auf der alten als Warnung vor Neubau, auf der neuen zusätzlich mit Frist.

**Was dieser Check nicht ist.** Er verlangt keinen Rückbau bestehender Nutzung. Deprecated heisst «bleibt funktionsfähig», und ein Zwölfmonatsfenster ist kein Notfall. Er verlangt zweierlei: dass **nichts Neues** auf diesen drei Features aufsetzt, und dass bestehende Nutzung ein **Datum** hat statt eines Vorsatzes. Ein Rückbau ohne Datum ist kein Plan, sondern eine Absichtserklärung — und die überlebt die nächste Priorisierung nicht.

**Fristdatum.** Die Spec nennt zwölf Monate als Minimum ab `2026-07-28`, also **frühestens 2027-07-28**. Das ist der früheste Entfernungstermin, nicht der angekündigte; wer danach plant, plant knapp. Der Katalog verlangt ein dokumentiertes Datum, nicht dieses Datum.

## Verification

### Modus 1: automated (Nutzung der drei Features)

```bash
# Roots
grep -rnE "roots/list|RootsCapability|list_roots|ListRootsRequest" src/ --include="*.py" --include="*.ts"

# Sampling
grep -rnE "sampling/createMessage|create_message|CreateMessageRequest|samplingCapability" src/

# Logging (Protokoll-Feature, nicht das Anwendungs-Logging)
grep -rnE "logging/setLevel|set_level|LoggingCapability|notifications/message" src/
```

**Abgrenzung, die dieser Grep nicht leistet:** `logging` trifft auch jedes `import logging` und jeden Logger-Aufruf. Gemeint ist ausschliesslich das **MCP-Protokoll-Feature**. Anwendungs-Logging nach `stderr` ist nicht nur erlaubt, sondern die von der Spec empfohlene Migration — und `OBS-003` verlangt es weiterhin. Ein Befund entsteht nur bei `logging/setLevel`, `LoggingCapability` oder serverinitiierten `notifications/message`.

### Modus 2: documentation_check (Frist und Pfad)

Bei vorhandener Nutzung: README oder CHANGELOG nennt je Feature ein Datum und den Zielzustand.

```bash
grep -rniE "deprecat|abkündig|rückbau|2027-07-28" README.md README.de.md CHANGELOG.md
```

Negative Kontrolle: Das Muster einmal gegen eine Datei laufen lassen, in der eines der Wörter sicher steht. Sonst ist «0 Treffer» nicht von «Muster greift nicht» zu unterscheiden.

## Pass Criteria

- [ ] Keine **neue** Nutzung von Roots, Sampling oder dem Logging-Protokoll-Feature seit dem letzten Audit
- [ ] Vorhandene Nutzung ist im README oder CHANGELOG benannt — je Feature mit Zielzustand und Datum
- [ ] Das genannte Datum liegt nicht nach dem frühesten Entfernungstermin (2027-07-28), oder die Abweichung ist begründet
- [ ] Der Zielzustand entspricht der Spec-Empfehlung (Tool-Parameter / Provider-API / `stderr` bzw. OTel), oder die Abweichung ist begründet
- [ ] Anwendungs-Logging nach `stderr` bleibt unberührt und erfüllt weiterhin `OBS-003` und `OBS-004`
- [ ] Auf `spec_baseline: 2026-07-28`: Die Server-Capabilities kündigen keines der drei Features mehr an, sofern nicht bewusst im Restfenster geführt

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Neuer Sampling-Pfad kurz vor der Migration gebaut | Arbeit, die in derselben Welle wieder herausfällt |
| «Wird migriert» ohne Datum | Überlebt die nächste Priorisierung nicht |
| Rückbau von `stderr`-Logging, weil «Logging deprecated ist» | Genau die Migration rückwärts — und `OBS-004` bricht |
| Grep meldet 0 Treffer, weil das Muster nie greift | §2.6: Schweigen als Freispruch gelesen |
| Frist auf «12 Monate» gesetzt, ohne Datum auszurechnen | Niemand weiss, wann sie abläuft |

## Remediation

```diff
-# Roots: Client nach erlaubten Verzeichnissen fragen
-roots = await ctx.session.list_roots()
-base = roots.roots[0].uri
+# Verzeichnis kommt als Konfiguration herein — explizit, prüfbar, ohne Rückkanal
+base = settings.data_root          # aus MCP_DATA_ROOT, validiert gegen SEC-017
```

```diff
-# Sampling: den Host-LLM um eine Zusammenfassung bitten
-summary = await ctx.session.create_message(messages=[...])
+# Direkte Anbindung an den Anbieter, mit eigenem Schlüssel und eigenem Budget
+summary = await anthropic.messages.create(model=..., messages=[...])
```

Beim zweiten Muster wandern zwei Dinge mit, die vorher der Host getragen hat: die Kosten und der Datenabfluss. Ein Server, der neu selbst an einen LLM-Anbieter sendet, wird damit zu einer eigenständigen Bekanntgabe — bei `data_class != "Public Open Data"` ist das ein Fall für `CH-002` und `HITL-003`, nicht nur eine technische Umstellung.

## Effort

S für die Dokumentationspflicht. M–L für den tatsächlichen Rückbau von Sampling, weil Kosten, Schlüssel und Datenschutzfolgen mitwandern.

## References

- [Spec 2026-07-28 — Changelog, Deprecated #1](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2577](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2577), [SEP-2596](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2596)
- [Feature lifecycle and deprecation policy](https://modelcontextprotocol.io/community/feature-lifecycle)
- `HITL-001`–`HITL-003` (Sampling-Pfad), `OBS-003`, `OBS-004`, `CH-002`
