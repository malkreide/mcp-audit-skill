---
id: IDENT-005
title: "Fallback-Version darf nicht wie ein Release aussehen"
category: IDENT
severity: medium
applies_when: 'sdk_language == "Python"'
pdf_ref: "Custom (Portfolio-Sweep 2026-07-29, 30 Server)"
evidence_required: 1
---

# IDENT-005 — Fallback-Marker statt plausibler Platzhalter

## Description

Wer `__version__` aus den Paket-Metadaten liest (IDENT-002), braucht einen Zweig für den Fall ohne Installation — den reinen Quell-Checkout. Was dort steht, entscheidet, ob der Umbau die Drift wirklich beseitigt oder sie nur verschiebt.

`swiss-statistics-mcp` hatte:

```python
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
```

`0.0.0` ist syntaktisch eine gültige Version. In einem Upstream-Log, in einer Fehlermeldung, in einem User-Agent ist sie von einer echten Release-Nummer nicht zu unterscheiden. Damit meldet der Server ohne Installation eine Zahl, die etwas behauptet — genau das, was der Umbau vermeiden sollte.

Die Konvention im Portfolio ist ein **lokales Segment** nach `+`:

```python
    __version__ = "0.0.0+source"
```

Das Segment ist PEP-440-konform, überlebt Versionsvergleiche und ist auf einen Blick als «keine Version bekannt» lesbar.

**Der Fallback kann auch im installierten Paket feuern — und dann ist er ein Befund, kein Fallback.** Dieser Check prüft die *Form* des Markers, eine reine Quell-Eigenschaft, und das ist richtig so. Er sagt aber nichts darüber, ob der Zweig im ausgelieferten Artefakt greift. Sind die Metadaten im publizierten Wheel beschädigt oder fehlt der Distributionsname, den `version()` nachschlägt, dann meldet das installierte Paket `0.0.0+source` auf der Leitung — korrekt geformt, und trotzdem ein kaputtes Artefakt.

Genau dafür ist der Marker gebaut: Er macht diesen Zustand **sichtbar**, statt ihn als plausible Release-Nummer zu tarnen. Gemessen wird er anderswo — `IDENT-001` Modus 3 löst den User-Agent am aus dem Index installierten Paket auf, und `0.0.0+source` dort ist ein Befund gegen `IDENT-002`, nicht gegen diesen Check.

**Der zweite Grund ist maschineller Natur:** Ein Check, der hartkodierte Versionen in `src/` findet (IDENT-002), muss den Fallback ausnehmen — und zwar am Aufbau, nicht am Wert. Das `+`-Segment ist das einzige verlässliche Unterscheidungsmerkmal. Ein Fallback `"0.0.0"` ist von einem echten Literal nicht trennbar und wird korrekt als Befund gemeldet.

Im Sweep war das mehr als Theorie: Meine erste Fassung des Checks nahm `0+unknown` als Marker an (die Form eines einzelnen Servers) und meldete daraufhin **neun Fehlalarme** gegen die Portfolio-Form `0.0.0+source`. Erst die Umstellung auf «enthält `+`» statt «gleicht diesem String» war robust.

## Verification

```bash
# Fallback-Zweige finden und ihre Form prüfen
grep -rn -A3 "except PackageNotFoundError" src/ | grep "__version__"
```

**Pass-Pattern:**

```python
except PackageNotFoundError:
    # Quell-Checkout ohne Installation. Bewusst kein plausibel aussehender
    # Platzhalter: ein erkennbar nicht-release-förmiger Marker ist besser
    # als eine falsche Version im User-Agent.
    __version__ = "0.0.0+source"
```

**Fail-Pattern:**

```python
except PackageNotFoundError:
    __version__ = "0.0.0"        # sieht wie ein Release aus
    __version__ = "0.1.0"        # noch schlimmer: plausibel und falsch
    __version__ = "unknown"      # bricht Versionsvergleiche
```

## Pass Criteria

- [ ] Der Fallback trägt ein lokales Segment nach `+` (z. B. `0.0.0+source`)
- [ ] Der Marker ist portfolioweit einheitlich
- [ ] Ein Kommentar erklärt, **warum** kein plausibler Platzhalter gewählt wurde
- [ ] Der Drift-Check erkennt Fallbacks am `+`-Segment, nicht am konkreten String
- [ ] Bei Repos mit Coverage-Gate trägt der Zweig `# pragma: no cover` (er ist per Definition nicht abgedeckt)

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| `"0.0.0"` | Von echter Version nicht unterscheidbar |
| `"0.1.0"` oder die letzte bekannte Nummer | Plausibel und falsch — die Drift, nur verschoben |
| `"unknown"` ohne Ziffernanteil | Bricht Versionsvergleiche und PEP-440-Parsing |
| Check vergleicht gegen einen festen Marker-String | Fehlalarme, sobald ein Repo eine andere Form nutzt |
| Fallback ohne `pragma: no cover` bei 100-%-Gate | CI rot, obwohl der Code korrekt ist |

## Remediation

```diff
  except PackageNotFoundError:  # pragma: no cover
-     __version__ = "0.0.0"
+     # Bewusst mit lokalem Segment: "0.0.0" allein sieht wie ein echtes
+     # Release aus. Der Marker macht sichtbar, dass hier keine Version
+     # bekannt ist — Portfolio-Konvention.
+     __version__ = "0.0.0+source"
```

Und im Check die Erkennung am Aufbau festmachen:

```diff
- if value == "0.0.0+source":       # nur diese eine Form
+ if "+" in value:                  # jedes lokale Segment ist ein Fallback
      continue
```

## Effort

XS — Minuten pro Server.

## References

- Portfolio-Sweep 2026-07-29: `swiss-statistics-mcp#20`
- Neun Fehlalarme durch marker-spezifische statt struktureller Erkennung
- IDENT-002 — der Zweig, um den es geht
- `IDENT-001` Modus 3 — wo sich zeigt, ob der Marker im *installierten* Paket feuert; dort ist er ein Befund, kein Fallback
- PEP 440, Abschnitt «Local version identifiers»
