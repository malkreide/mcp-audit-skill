---
id: ARCH-002
title: "Tool-Beschreibung mit Use-Case-Tags"
category: ARCH
severity: medium
applies_when: 'always'
pdf_ref: "Sec 2.2"
evidence_required: 2
---

# ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

## Description

LLMs wählen Tools nicht über exakte Namens-Treffer, sondern über semantische Embeddings der Tool-Beschreibung. Eine Beschreibung wie `"Searches database"` lässt das Modell zwischen drei `getX`-Tools rätseln. Eine Beschreibung mit explizitem Use-Case-Tag, Trigger-Phrasen und Negativ-Hinweisen («NICHT verwenden für…») reduziert Halluzinationen drastisch.

Die Best-Practice-Konvention im PDF nutzt XML-artige Tags innerhalb der Description:

- `<use_case>` — Wann soll das Tool verwendet werden?
- `<important_notes>` — Caveats, Side-Effects, Limitierungen
- `<example>` — Konkrete Beispiel-Inputs

Das LLM sieht diese Tags zwar nicht als HTML, aber die strukturierte Information erhöht semantische Trennschärfe.

## Verification

### Modus 1: code_review (Description-Länge)

```bash
# Extrahiere alle description-Strings, prüfe Mindestlänge
grep -rE "description=" src/ | grep -oP 'description=["\x27][^"\x27]*["\x27]' | awk -F'"' '{ print length($2) }'
```

**Pass:** Median-Länge ≥ 100 Zeichen, kein Tool unter 50 Zeichen.
**Fail:** Tool mit nur einem Wort oder einem kurzen Satz als Description.

### Modus 2: code_review (Use-Case-Tags vorhanden)

```bash
grep -rE "<use_case>|<important_notes>|<example>" src/
```

**Pass-Pattern:**

```python
@mcp.tool(
    name="searchParlamentaryMotions",
    description=(
        "Sucht in Curia-Vista nach parlamentarischen Vorstössen "
        "(Motionen, Postulate, Interpellationen, parlamentarische Initiativen).\n\n"
        "<use_case>Politische Recherche zu Bildungs-, Datenschutz-, "
        "Verwaltungsthemen. Identifikation von Vorstössen einzelner "
        "Parlamentarier:innen oder Kommissionen.</use_case>\n\n"
        "<important_notes>Liefert nur Vorstösse seit 2019 (frühere Daten "
        "über das Tool `searchHistoricalMotions`). Maximale Trefferanzahl "
        "pro Aufruf: 50.</important_notes>\n\n"
        "<example>query='künstliche Intelligenz Volksschule', from_date='2024-01-01'</example>"
    ),
)
async def search_parlamentary_motions(...): ...
```

## Pass Criteria

- [ ] Tool-Beschreibungen sind ≥ 100 Zeichen im Median
- [ ] Use-Case-Tag (`<use_case>` oder Äquivalent) in mindestens 80% der Tools vorhanden
- [ ] Wo relevant: Important-Notes-Tag mit Caveats / Limitierungen
- [ ] Bei mehreren ähnlichen Tools: Description macht Differenzierung explizit

## Common Failures

| Pattern | Konsequenz |
|---|---|
| `description="Search."` | LLM kann nicht zwischen verschiedenen Such-Tools differenzieren |
| Description wiederholt nur den Tool-Namen | Keine zusätzliche semantische Information |
| Caveats nur im README, nicht in Description | LLM sieht Caveats nicht zur Tool-Wahl-Zeit |

## Remediation

```diff
  @mcp.tool(
      name="searchEducationStats",
-     description="Search education statistics."
+     description=(
+         "Sucht in den städtischen Bildungsstatistiken nach Kennzahlen "
+         "(Klassengrösse, Lehrer-Schüler-Verhältnis, Anteil DaZ, etc.).\n\n"
+         "<use_case>Politische / journalistische Recherche, "
+         "Schulamts-interne Reportings, Pädagogik-Analysen.</use_case>\n\n"
+         "<important_notes>Daten werden quartalsweise aktualisiert. "
+         "Personendaten sind nicht abrufbar — nur aggregierte "
+         "Kennzahlen.</important_notes>"
+     ),
  )
```

## Effort

S — Pro Tool 5–10 Minuten. Bei 10 Tools: ~1 Tag.

## References

- PDF Sec 2.2 — Tool-Beschreibungen
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
