---
id: ARCH-003
title: "«Not Found» Anti-Pattern: Heuristiken statt leerer Antworten"
category: ARCH
severity: medium
applies_when: 'always'
pdf_ref: "Sec 2.2"
evidence_required: 2
---

# ARCH-003 — «Not Found» Anti-Pattern

## Description

LLMs reagieren empirisch nachweisbar empfindlich auf negativ-framing in Tool-Responses. Eine Antwort wie `"No results found"` oder `[]` ohne Kontext führt häufig zu einer von zwei Failure-Modes:

1. **Halluzination:** Das Modell konstruiert eine Antwort aus Trainingsdaten, statt zuzugeben, dass es keine Information hat.
2. **Sackgasse:** Das Modell bricht die Aufgabe ab, statt mit alternativen Strategien (verwandte Begriffe, andere Tools) weiterzumachen.

Der Best-Practice-Standard fordert: Wenn ein Tool keine exakten Treffer findet, soll es **partielle / heuristische / verwandte Ergebnisse** zurückgeben, gepaart mit explizitem Hinweis auf die fehlende Exaktheit. Damit kann das Modell:

- Verwandte Resultate dem User anbieten
- Den Suchbegriff verfeinern
- Ein anderes Tool wählen

**Ausnahme:** Bei hochsensiblen Daten (Personendaten, Zugriffskontrollen) ist «not found» korrekt — Heuristiken könnten Information leaken, die das Modell sonst nicht hätte. Beispiel: `getUserMedicalRecord("nonexistent")` darf NICHT «hier ist ein ähnlicher Datensatz» liefern.

## Verification

### Modus 1: code_review (Empty-Result-Pattern)

```bash
# Suche nach typischen "leerer Result"-Patterns
grep -rE "no results|not found|empty|return \[\]|return None|no matches" src/
```

**Pass-Pattern:**

```python
@mcp.tool()
async def search_lehrpersonen(query: str, ctx: Context) -> dict:
    exact = await db.search_exact(query)
    if exact:
        return {
            "results": exact,
            "match_type": "exact",
            "count": len(exact),
        }

    # Kein Treffer — Fuzzy-Search mit Hinweis
    fuzzy = await db.search_fuzzy(query, threshold=0.7)
    if fuzzy:
        return {
            "results": fuzzy[:10],
            "match_type": "fuzzy",
            "count": len(fuzzy),
            "note": (
                f"Keine exakten Treffer für '{query}'. "
                f"Gefundene ähnliche Einträge basieren auf Tippfehler-Toleranz. "
                f"Verfeinere den Begriff für bessere Resultate."
            ),
        }

    # Auch Fuzzy leer — Suggestions
    suggestions = await db.popular_terms_starting_with(query[:3])
    return {
        "results": [],
        "match_type": "none",
        "count": 0,
        "note": (
            f"Keine Einträge für '{query}' gefunden. "
            f"Häufige Suchbegriffe in dieser Kategorie: "
            f"{', '.join(suggestions[:5])}"
        ),
    }
```

**Fail-Pattern:**

```python
async def search_lehrpersonen(query: str):
    results = await db.search(query)
    if not results:
        return "No results found"  # ← klassisches Anti-Pattern
    return results
```

### Modus 2: code_review (Sensitive-Data-Ausnahme respektiert)

Bei sensiblen Operationen muss das Tool «not found» liefern dürfen — Heuristik wäre Information-Leak.

**Pass-Pattern (sensibler Fall):**

```python
@mcp.tool(annotations={"sensitive": True})
async def get_user_personal_data(user_id: str, ctx: Context) -> dict:
    # Keine Heuristik bei Personen-Lookup — sonst leak
    record = await db.get_by_id(user_id)
    if record is None:
        return {
            "found": False,
            "user_id": user_id,
            # Kein "vielleicht meintest du User X"
        }
    return {"found": True, "data": record}
```

## Pass Criteria

- [ ] Bei nicht-sensiblen Such-Tools: leere Ergebnisse triggern Fuzzy-Match oder Suggestion-Mechanismus
- [ ] Response enthält `match_type`-Feld oder ähnlich (exact / fuzzy / none)
- [ ] Bei `match_type == "none"`: ein actionable Hinweis (Vorschläge, andere Tools, Term-Verfeinerung)
- [ ] Bei sensiblen Tools: ausschliesslich exakte Lookups, kein Fuzzy-Fallback (dokumentiert)

## Common Failures

| Pattern | Risiko |
|---|---|
| `return []` ohne Kontext | LLM halluziniert oder bricht ab |
| String `"No results"` als Response | Schlechtes Format, schwer maschinenlesbar |
| Heuristik bei Personen-Lookup | Information-Leak via Existenzbestätigung |
| Suggestions aus User-Input ohne Sanitization | XSS / Prompt-Injection-Vector |

## Remediation

```diff
  @mcp.tool()
  async def find_school(name: str) -> list:
      results = await db.find(name)
-     if not results:
-         return []
+     if not results:
+         fuzzy = await db.find_fuzzy(name, threshold=0.7)
+         suggestions = await db.popular_school_names_starting_with(name[:3])
+         return {
+             "results": fuzzy[:5],
+             "match_type": "fuzzy" if fuzzy else "none",
+             "note": (
+                 f"Keine exakten Treffer für '{name}'. "
+                 f"{'Ähnliche Schulen aufgeführt.' if fuzzy else ''} "
+                 f"Häufige Schulnamen: {', '.join(suggestions[:5])}"
+             ),
+         }
      return {"results": results, "match_type": "exact"}
```

## Effort

S — Pro Tool ~30 Minuten. Bei 10 Such-Tools: 1 Tag.

## References

- PDF Sec 2.2 — Negatives Framing
- [Anthropic: Effective tool use](https://www.anthropic.com/engineering/building-effective-agents)
