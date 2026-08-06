---
id: ARCH-003
title: "«Not Found» Anti-Pattern: Heuristiken statt leerer Antworten"
category: ARCH
severity: medium
applies_when: 'always'
pdf_ref: "Sec 2.2"
evidence_required: 3
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

### Vorschlagen ist nicht Erweitern — und bis v2.1.0 hat dieser Check nur das eine geprüft

Die Forderung oben lässt offen, **wie** das Tool zu seinen Vorschlägen kommt. Der bequeme Weg ist, die kürzere Variante des Begriffs gleich selbst abzufragen und ihre Treffer zurückzugeben. Die Antwort sieht dann besser aus, und sie beantwortet einen Begriff, den der Aufrufer nie gewählt hat.

**Die Eigenschaft, die dabei bricht:** *Keine Zeile im Resultat darf einem Begriff zuzuschreiben sein, den der Aufrufer nicht geschickt hat.* Für das Modell ist ein so entstandener Treffer von einem echten nicht zu unterscheiden — `match_type: "fuzzy"` steht daneben, aber es sagt *dass* geraten wurde, nicht *welche Zeile zu welchem Begriff gehört*. Liegen beide Sorten in derselben Liste, fehlt die Zuordnung, und der Hinweis daneben ändert daran nichts.

Dieselbe Fehlerform wie in `DRIFT-002` («Fallback verengt, erweitert nie»), eine Ebene weiter: dort wird ein anderer **Datensatz** substituiert, hier eine andere **Abfrage**.

**Beide Modi dieses Checks lasen bis v2.1.0 die Antwort** — Empty-Result-Pattern im Quelltext, `match_type`-Feld, handlungsfähiger Hinweis. Keiner mass, was **rausgegangen** ist. Ein Server, der seine eigenen Vorschläge still selbst absucht, bestand den Check; das Pass-Pattern von Modus 1 führte es sogar vor, indem es `fuzzy` unter `results` mischte und Vorschläge über `popular_terms_starting_with(query[:3])` aus einem Korpus holte — eine zweite Abfrage, die niemand angefordert hatte. Beides ist unten korrigiert.

**Belegfall (Portfolio, 2026-08):** [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp), beide Hälften desselben Vorgangs. **0.20.0** lehnte Kriterium 1 ausdrücklich ab und begründete das mit «bankruptcy notices, debt-collection summonses, estate calls, construction objections» — Rubriken, die die Allow-Liste `GREEN_RUBRICS` des Servers gerade ausschliesst und die über kein Tool erreichbar sind. Die Ausnahme aus Kriterium 4 wurde damit für genau die Menge beansprucht, auf die Kriterium 1 anzuwenden gewesen wäre. Die Begründung stand in beiden `SECURITY`-Dateien, im CHANGELOG und im abschliessenden PR; gefangen hat sie erst das [Re-Audit vom 2026-07-30](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md), und zwar nicht durch einen Modus, sondern durch Lesen der Rubrik-Listen. **0.22.0** hat es umgesetzt — Vorschläge sind Kürzungen des eigenen Begriffs, der Server fragt keine davon ab.

**Bemerkenswert an der Reihenfolge dort:** Der Test «es geht genau ein Request mit dem unveränderten Begriff raus» existierte **lange vor** dem Vorschlagsmechanismus. Der Server war damit nachweislich unschädlich und nachweislich nutzlos. Eine Hälfte allein liest sich wie Disziplin und ist keine — deshalb verlangt Modus 3 unten beide, sonst prämiert der Check den Zustand, der Kriterium 1 gerade verfehlt.

**Abgrenzung.** `FID-003` prüft, ob die Leermenge **eindeutig und handlungsfähig** ist; dort ist Verbreitern der ausdrücklich empfohlene nächste Schritt — nur trifft die Entscheidung darüber der Aufrufer. Dieser Check prüft, ob der Server sie ihm abnimmt. `DRIFT-004` warnt umgekehrt davor, mit einem Mock die eigene Annahme über die Quelle festzuschreiben; das gilt hier nicht, denn Prüfgegenstand ist das Verhalten des Servers, nicht die Quelle — siehe die Begründung unter Modus 3.

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

    # Kein Treffer — heuristische Treffer in ein EIGENES Feld, mit dem Begriff,
    # der sie erzeugt hat. Nie unter `results`: dort steht ausschliesslich, was
    # den Begriff des Aufrufers beantwortet.
    fuzzy = await db.search_fuzzy(query, threshold=0.7)
    if fuzzy:
        return {
            "results": [],
            "match_type": "fuzzy",
            "count": 0,
            "heuristic": {
                "produced_by": fuzzy.term,      # der Begriff, nicht deiner
                "entries": fuzzy.entries[:10],
            },
            "note": (
                f"Keine exakten Treffer für '{query}'. Unter `heuristic` stehen "
                f"Einträge zu '{fuzzy.term}' — ein anderer Begriff, "
                f"tippfehlertolerant abgeleitet. Gesucht wurde nur '{query}'."
            ),
        }

    # Auch heuristisch nichts — Vorschläge, ABGELEITET aus dem Begriff des
    # Aufrufers. Nicht aus einem Korpus geholt: das wäre eine zweite Abfrage.
    suggestions = [v for v in shorter_variants(query) if len(v) >= 4]
    return {
        "results": [],
        "match_type": "none",
        "count": 0,
        "suggestions": suggestions,             # breitester Vorschlag zuletzt
        "note": (
            f"Keine Einträge für '{query}'. Gesucht wurde genau einmal, mit "
            f"deinem Begriff — es wurde nicht selbstständig verbreitert. "
            f"Die Vorschläge sind Kürzungen davon und ungeprüft; rufe das "
            f"Tool damit erneut auf, wenn einer passt."
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

### Modus 3: runtime_test (Request-Zähler — was rausgegangen ist)

Gegen ein Such-Tool mit garantierter Leermenge, **Upstream gemockt**. Gezählt wird auf der Route, nicht im Rückgabewert:

```python
@respx.mock
async def test_empty_result_offers_variants_of_the_callers_own_term():
    """Hälfte 1: Der nächste Schritt ist konkret und kommt aus der Eingabe."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_EMPTY_PAGE))
    result = await search_tool(term="Quellensteuerverordnung")

    assert result.entries == [] and result.match_type == "none"
    assert result.suggestions, "Leermenge ohne Vorschlag — Kriterium 1 unerfüllt"
    assert all(s.rstrip("*") in "Quellensteuerverordnung" for s in result.suggestions), (
        "Vorschlag stammt nicht aus dem Begriff des Aufrufers"
    )


@respx.mock
async def test_suggestions_are_never_searched():
    """Hälfte 2: Vorgeschlagen wird viel, abgefragt genau eines."""
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=_EMPTY_PAGE)
    )
    result = await search_tool(term="Quellensteuerverordnung")

    assert result.suggestions
    assert route.call_count == 1, (
        f"{route.call_count} Abfragen für einen Begriff — Vorschläge wurden gesucht"
    )
    sent = route.calls[0].request.url.params["SearchTerm"]
    assert sent == "Quellensteuerverordnung", f"gesucht wurde {sent!r}"
```

**Beide Hälften sind Pflicht, und je eine allein ist wertlos.** Ohne die erste besteht ein Server, der nie etwas vorschlägt, die zweite mühelos — genau der Zustand des Belegfalls vor 0.22.0. Ohne die zweite besteht ein Server die erste, der jeden seiner Vorschläge sofort selbst abfragt. Ein Auditor, der nur eine Hälfte vorfindet, hat **nicht** die halbe Erfüllung gesehen, sondern gar keine.

**Warum hier gemockt wird, obwohl `DRIFT-004` davor warnt.** Dort pinnt ein Mock eine Annahme über die **Quelle** und verbirgt deren Drift. Hier ist der Prüfgegenstand das **eigene Verhalten des Servers** — was er rausschickt —, und das kann ein Live-Test prinzipiell nicht sehen: Gegen die echte Quelle ist eine Suche mit einem Treffer von einer Suche mit einem still nachgereichten Ersatz-Begriff nicht zu unterscheiden. Der Zähler auf der Route ist die einzige Stelle, an der die Unterscheidung überhaupt existiert.

**Ausgang, wenn keine Route zählbar ist** — der Server kapselt seinen Client so, dass kein Zähler ansetzt: `todo`, nicht `pass`. Nach §2.6 ist «nicht gemessen» ein eigener Ausgang; ein Server, dessen Abfragen unbeobachtbar sind, hat diesen Modus nicht bestanden, sondern ihn verhindert.

## Pass Criteria

- [ ] Bei nicht-sensiblen Such-Tools: leere Ergebnisse triggern Fuzzy-Match oder Suggestion-Mechanismus
- [ ] Response enthält `match_type`-Feld oder ähnlich (exact / fuzzy / none)
- [ ] Bei `match_type == "none"`: ein actionable Hinweis (Vorschläge, andere Tools, Term-Verfeinerung)
- [ ] Bei sensiblen Tools: ausschliesslich exakte Lookups, kein Fuzzy-Fallback (dokumentiert)
- [ ] Pro Tool-Aufruf geht **genau ein** Upstream-Request raus, und sein Suchbegriff ist der des Aufrufers, **unverändert** — erhoben am Zähler der Route (Modus 3), nicht am Rückgabewert
- [ ] Vorschläge sind aus der Eingabe **abgeleitet** (Kürzung, Präfix), nicht aus einem Korpus-Vokabular geholt — letzteres ist eine zweite Abfrage in anderer Verpackung, mit eigenem Recall-Risiko
- [ ] Vorschläge unterhalb weniger Zeichen werden verworfen — ein Präfix, das den halben Bestand matcht, ist kein nächster Schritt («AG» ist kein Suchbegriff)
- [ ] Heuristische Treffer stehen in einem **eigenen** Feld, zusammen mit dem Begriff, der sie erzeugt hat — nie in derselben Liste wie die exakten
- [ ] Die Antwort **sagt**, dass nicht verbreitert wurde; ohne diesen Satz schliesst das Modell aus dem Schweigen, es sei schon alles versucht
- [ ] Das Testpaar aus Modus 3 ist **vollständig** vorhanden — eine Hälfte belegt, dass Vorschläge erscheinen, die andere, dass keiner davon abgefragt wurde
- [ ] **Gegenprobe:** Der Zähler ist einmal gegen eine Fassung gelaufen, die ihre Vorschläge selbst absucht, und hat dort angeschlagen. Ein Modus, der nur am korrigierten Server grün wird, prüft die Fixture

## Common Failures

| Pattern | Risiko |
|---|---|
| `return []` ohne Kontext | LLM halluziniert oder bricht ab |
| String `"No results"` als Response | Schlechtes Format, schwer maschinenlesbar |
| Heuristik bei Personen-Lookup | Information-Leak via Existenzbestätigung |
| Suggestions aus User-Input ohne Sanitization | XSS / Prompt-Injection-Vector |
| Der Vorschlag wird gleich mitgesucht, seine Treffer landen unter `results` | Die Antwort beantwortet einen Begriff, den der Aufrufer nie gewählt hat — für das Modell nicht erkennbar |
| Fuzzy-Treffer in derselben Liste wie die exakten, `match_type` daneben | Das Feld sagt *dass* geraten wurde, nicht *welche Zeile zu welchem Begriff gehört* |
| Vorschläge aus einem Korpus-Vokabular (`popular_terms_starting_with`) | Zweiter Treffertyp mit eigenem Recall-Risiko — und eine Abfrage, die niemand angefordert hat |
| Vorschlag aus zwei, drei Zeichen | Präfix matcht den halben Bestand; das ist die Leermenge in anderer Form |
| Die Antwort schweigt darüber, dass nicht verbreitert wurde | Das Modell schliesst aus dem Schweigen, es sei bereits alles versucht worden |
| Nur die Zähler-Hälfte des Testpaars vorhanden | Server ist nachweislich unschädlich und nachweislich nutzlos — Kriterium 1 bleibt unerfüllt |
| Nur die Vorschlags-Hälfte vorhanden | Ein Server, der jeden Vorschlag sofort selbst absucht, besteht sie mühelos |
| Der Zähler live gegen die echte Quelle geprüft | Ein still nachgereichter Ersatz-Begriff ist dort von einem echten Treffer nicht zu unterscheiden |

## Remediation

```diff
  @mcp.tool()
  async def find_school(name: str) -> list:
      results = await db.find(name)
-     if not results:
-         return []
+     if not results:
+         # Vorschläge sind Kürzungen des eigenen Begriffs — abgeleitet, nicht
+         # abgefragt. Es geht genau ein Request raus, und der trug `name`.
+         suggestions = [v for v in shorter_variants(name) if len(v) >= 4]
+         return {
+             "results": [],
+             "match_type": "none",
+             "suggestions": suggestions,
+             "note": (
+                 f"Keine exakten Treffer für '{name}'. Es wurde nicht "
+                 f"selbstständig verbreitert — gesucht wurde nur '{name}'. "
+                 f"Die Vorschläge sind Kürzungen davon und ungeprüft."
+             ),
+         }
      return {"results": results, "match_type": "exact"}
```

Wer statt des Vorschlags-Arms den **Fuzzy-Arm** nimmt, hält die Eigenschaft nur mit einem getrennten Feld:

```diff
- return {"results": fuzzy[:5], "match_type": "fuzzy"}
+ return {
+     "results": [],                       # leer: nichts beantwortet `name`
+     "match_type": "fuzzy",
+     "heuristic": {"produced_by": fuzzy.term, "entries": fuzzy.entries[:5]},
+ }
```

Verboten ist die Vermischung, nicht die Hilfe.

## Effort

S — Pro Tool ~30 Minuten. Bei 10 Such-Tools: 1 Tag.

Modus 3 kostet einmalig mehr, wenn der Server noch keinen Mock-Layer für seinen Upstream-Client hat: Dann ist der Zähler nicht zwei Assertions, sondern erst eine Testverdrahtung. Existiert der Layer, sind es zwei Tests von je zehn Zeilen — und ohne sie ist der Rest dieses Checks am Rückgabewert erhoben, also an der Seite, die der Fehler nicht berührt.

## References

- PDF Sec 2.2 — Negatives Framing
- [Anthropic: Effective tool use](https://www.anthropic.com/engineering/building-effective-agents)
- `FID-003` — die Leermenge eindeutig und handlungsfähig machen; dort verbreitert der **Aufrufer**, hier darf es der Server nicht für ihn tun
- `DRIFT-002` — dieselbe Fehlerform mit einem anderen Datensatz statt einer anderen Abfrage
- `DRIFT-004` — warum der Mock dort die Annahme pinnt und hier der einzige Messpunkt ist
- Herkunft von Modus 3: [`mcp-data-fidelity-skill` Regel 10](https://github.com/malkreide/mcp-data-fidelity-skill/blob/main/SKILL.md) («Vorschlagen ist nicht Erweitern») und der Vorschlag in [`mcp-audit-skill#102`](https://github.com/malkreide/mcp-audit-skill/issues/102)
- Belegfall: [`amtsblatt-mcp` 0.22.0](https://github.com/malkreide/amtsblatt-mcp/blob/main/SECURITY.md#suggestions-not-silent-widening-arch-003) — und das [Re-Audit vom 2026-07-30](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md), das den Fall gefunden hat, ohne dass ein Modus danach fragte
