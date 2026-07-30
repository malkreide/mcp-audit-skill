---
id: DRIFT-001
title: "Endpoint- und Ressourcen-URLs an genau einer Stelle konstruiert"
category: DRIFT
severity: medium
applies_when: 'tools_make_external_requests == true'
pdf_ref: "Custom (Portfolio-Fundstück meteoswiss-mcp#33, 2026-07-30)"
evidence_required: 2
---

# DRIFT-001 — Eine URL, eine Konstruktionsstelle

## Description

Die URL einer Upstream-Ressource wird selten nur einmal gebraucht. Typisch sind drei Stellen: der eigentliche Abruf, die Fehlermeldung im Degradationspfad («**STAC-Item:** …») und das `data_source_url`-Feld der Provenance. Wird sie dreimal geschrieben, ist sie dreimal falsch, sobald sie einmal falsch ist — und ein Fix an einer Stelle lässt die anderen stehen.

Der Schaden ist nicht der Tippfehler, sondern die **Widerlegbarkeit**: Die Fehlermeldung zeigt der Nutzerin die URL, die der Server angeblich abgerufen hat. Stimmt die mit der tatsächlich abgerufenen überein, weil beide aus derselben Quelle stammen, ist sie ein Beleg. Sind es Kopien, belegt sie nichts — und im Fehlerfall führt sie die Fehlersuche in die Irre, weil sie plausibel aussieht.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Die STAC-Item-URL war an drei Stellen wortgleich ausgeschrieben, alle drei mit demselben Konstruktionsfehler (Collection-ID als Präfix vor der Item-ID). Jede Station lieferte 404. Die Fehlermeldung nannte dabei brav die falsche URL — sie stammte aus derselben Kopie. Im Issue-Report des Nutzers stand sie als vermeintliche Evidenz.

## Verification

### Modus 1: code_review

```bash
# URL-Literale und f-String-Konstruktionen mit Pfadanteil
grep -rnE '(https?://[^"'"'"']+/[^"'"'"']*|/collections/|/items/|/v[0-9]+/)' src/ \
  | grep -vE '^\s*#' | sort

# Zusammensetzungen aus denselben Konstanten mehrfach?
grep -rnE 'f"\{[A-Z_]+\}/' src/ | head -20
```

Ein Befund ist gegeben, wenn dieselbe Pfadstruktur (nicht dasselbe Literal — f-Strings unterscheiden sich in der Formatierung) an mehr als einer Stelle zusammengesetzt wird.

**Pass-Pattern:**

```python
def _smn_stac_item_url(station: str) -> str:
    """URL des STAC-Items einer SMN-Station.

    Die Item-ID ist der nackte Stationscode in Kleinschreibung — nicht die
    Collection-ID als Präfix. Wird an drei Stellen gebraucht (Fetch,
    Fehlermeldung, Provenance), steht deshalb nur hier.
    """
    return f"{STAC_BASE}/collections/{SMN_COLLECTION}/items/{station.lower()}"
```

Alle drei Aufrufer rufen die Funktion:

```python
resp = await client.get(_smn_stac_item_url(code))
...
stac_url = _smn_stac_item_url(code)             # Fehlermeldung
...
data_source_url=_smn_stac_item_url(code),       # Provenance
```

**Fail-Pattern:**

```python
# Fetch
url = f"{STAC_BASE}/collections/{SMN_COLLECTION}/items/ch.meteoschweiz.ogd-smn-{code.lower()}"
...
# Fehlermeldung — eigene Kopie
stac_url = (f"https://data.geo.admin.ch/api/stac/v1/collections/{SMN_COLLECTION}/items/"
            f"ch.meteoschweiz.ogd-smn-{code.lower()}")
...
# Provenance — nochmals dieselbe Kopie
data_source_url=(f"https://data.geo.admin.ch/api/stac/v1/collections/{SMN_COLLECTION}/items/"
                 f"ch.meteoschweiz.ogd-smn-{code.lower()}")
```

### Modus 2: code_review (Provenance-Kopplung)

Die in der Provenance und in der Fehlermeldung genannte URL muss **dieselbe Funktion** aufrufen wie der Abruf. Ein Test hält das fest:

```python
async def test_provenance_url_is_the_url_that_was_fetched():
    with respx.mock(assert_all_called=True) as r:
        route = r.get(_smn_stac_item_url("KLO")).respond(json=ITEM)
        ...
    payload = json.loads(result)
    assert payload["provenance"]["data_source_url"] == str(route.calls[0].request.url)
```

## Pass Criteria

- [ ] Jede Upstream-Ressourcen-URL wird an genau einer Stelle konstruiert (Funktion oder Methode)
- [ ] Fehlermeldung und Provenance rufen dieselbe Konstruktionsstelle wie der Abruf
- [ ] Basis-URLs liegen als Modul-Konstanten vor, nicht als wiederholte Literale
- [ ] Die Konstruktionsfunktion trägt einen Docstring, der die nicht offensichtlichen Regeln nennt (Kleinschreibung, kein Präfix, Encoding)

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| URL im Fetch und in der Fehlermeldung getrennt gebaut | Ein Fix erwischt nur eine Stelle; die Meldung lügt danach |
| `data_source_url` als Literal | Provenance belegt nichts — sie zitiert eine Absicht, keinen Abruf |
| Basis-URL im Test nochmals ausgeschrieben | Der Test überlebt jede Umstellung und prüft danach die alte URL (siehe `DRIFT-004`) |
| Konstruktionsregeln nur im Commit-Text | Die nächste Person baut die Kopie erneut |

## Remediation

### Schritt 1: Konstruktionsfunktion extrahieren

Eine Funktion pro Ressourcentyp, benannt nach ihr (`_smn_stac_item_url`, `_asset_url`). Die Regeln, die man nicht sieht, in den Docstring — Kleinschreibung, Präfixe, Encoding.

### Schritt 2: Alle Aufrufer umstellen

Auch die in Fehlermeldungen und Provenance. Das sind die, die man vergisst, weil sie nicht am Netzverkehr hängen.

### Schritt 3: Kopplung festhalten

Der Test aus Modus 2 kostet fünf Zeilen und hält die Provenance ehrlich.

## Effort

S — unter einer Stunde pro Ressourcentyp.

## References

- Portfolio-Fundstück `meteoswiss-mcp#33` — dieselbe falsche URL an drei Stellen, Fehlermeldung inklusive
- `DRIFT-002` — Fallback-Semantik (der zweite Fehler auf demselben Codepfad)
- `DRIFT-004` — Endpoint-Konstanten live verifizieren
- `CH-004` — OGD-Provenance (die die URL als Beleg führt)
