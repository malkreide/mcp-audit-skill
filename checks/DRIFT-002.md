---
id: DRIFT-002
title: "Fallback verengt, erweitert nie — lieber ein Fehler als ein anderer Datensatz"
category: DRIFT
severity: high
applies_when: 'tools_make_external_requests == true'
pdf_ref: "Custom (Portfolio-Fundstück meteoswiss-mcp#33, 2026-07-30)"
evidence_required: 2
---

# DRIFT-002 — Ein Fallback darf lockern, *wie* man an dieselbe Sache kommt, nie *welche*

## Description

Resilienz-Fallbacks sind Pflicht (Probe-Skill 3.1/3.5): Retry, Dump statt API, Cache statt Live. Alle diese lockern den **Weg** zum selben Datensatz. Es gibt aber eine zweite, verwandt aussehende Sorte, die etwas ganz anderes tut — sie lockert, **welcher Datensatz** geliefert wird:

```python
# gesucht: die 10-Minuten-Werte von heute
if not now_url:
    for _key, asset in assets.items():          # sonst halt irgendein CSV
        if asset["href"].endswith(".csv"):
            now_url = asset["href"]
            break
```

Das ist kein Fallback, sondern eine stille Substitution. Der Aufruf gelingt, die Antwort ist wohlgeformt, die Provenance stimmt formal — und der Inhalt beantwortet eine andere Frage als die gestellte. Für ein Modell ist das nicht erkennbar; es liest Tageswerte als Momentaufnahme.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Der Selektor suchte `/now/` im Pfad, doch die Granularität steckt im Dateinamen (`ogd-smn_klo_t_now.csv`) — ein Verzeichnis `/now/` gibt es nicht, die Bedingung war unerfüllbar. Der Fallback nahm daraufhin das *erste* CSV im Item: `d_historical`, Tageswerte zurück bis 1980, ausgegeben unter der Überschrift «Aktuelle Beobachtungen». Verdeckt wurde das nur dadurch, dass ein URL-Fehler den Aufruf ohnehin vorher abbrechen liess (`DRIFT-001`). Ohne diesen zweiten Fehler hätte der Server jahrzehntealte Tageswerte als aktuelle Messung ausgeliefert.

Die Regel, die daraus folgt, ist unbequem, weil sie gegen den Reflex «lieber irgendwas als nichts» steht: **Wo die Semantik nicht mehr stimmt, ist ein Fehler das bessere Ergebnis.** Ein Fehler ist sichtbar und wird gemeldet. Ein semantisch falscher Datensatz wird zitiert.

## Verification

### Modus 1: code_review

```bash
# Auswahl-Fallbacks: erste Übereinstimmung, break, next(iter(...))
grep -rnE 'break$|next\(iter\(|\[0\]\s*$|else:\s*$' src/ -B4 \
  | grep -iE 'asset|item|result|candidate|fallback|first' | head -20
```

Für jeden Treffer die Frage stellen: *Liefert der Fallback dieselbe Art Datensatz wie der Primärpfad — oder nur irgendeinen?*

**Pass-Pattern:**

```python
def _select_smn_now_asset(assets: dict[str, Any]) -> str | None:
    """10-Minuten-Werte: `t_now` (seit Mitternacht), sonst `t_recent`.

    Bewusst ohne Fallback auf ein beliebiges CSV — die Assets enthalten auch
    Tages-, Monats- und Jahreswerte bis 1980 zurück, und die als «aktuelle
    Beobachtung» auszugeben wäre schlimmer als ein sauberer Fehler.
    """
    for suffix in ("_t_now.csv", "_t_recent.csv"):
        for asset in assets.values():
            if asset.get("href", "").endswith(suffix):
                return asset["href"]
    return None
```

Der Aufrufer eskaliert:

```python
now_url = _select_smn_now_asset(item.get("assets", {}))
if not now_url:
    raise ValueError(f"Kein 10-Minuten-CSV-Asset für Station '{station}' gefunden.")
```

**Fail-Pattern:**

```python
# Der Primärpfad sucht 10-Minuten-Werte, der Fallback irgendein CSV.
# Beide Zweige führen zu derselben Überschrift «Aktuelle Beobachtungen».
if not now_url:
    now_url = next(a["href"] for a in assets.values() if a["href"].endswith(".csv"))
```

Zulässige Erweiterung, sofern **ausgewiesen** — eine gröbere Auflösung ist eine andere Antwort und muss als solche erkennbar sein:

```python
rows, granularity = _fetch_with_granularity(station)   # "10min" | "hourly"
envelope = _ogd_envelope(payload, granularity=granularity)
```

### Modus 2: runtime_test

```python
async def test_missing_ten_minute_asset_is_an_error_not_an_archive_grab():
    """Ohne t_now/t_recent darf nichts geliefert werden — auch kein d_historical."""
    item = {"assets": {"ogd-smn_klo_d_historical.csv": {"href": ".../d_historical.csv"}}}
    assert _select_smn_now_asset(item["assets"]) is None
```

## Pass Criteria

- [ ] Jeder Auswahl-Fallback liefert denselben Datensatz-Typ wie der Primärpfad (gleiche Granularität, gleicher Zeitbezug, gleiche Entität)
- [ ] Fallbacks, die die Semantik ändern, sind entweder entfernt oder in der Antwort ausgewiesen (Feld, nicht nur Prosa)
- [ ] Wo kein semantisch gleichwertiger Kandidat existiert, wird eskaliert statt substituiert
- [ ] Ein Test hält fest, dass der Nicht-Fund ein Fehler ist — nicht nur, dass der Fund funktioniert
- [ ] Die Auswahlfunktion begründet im Docstring, was sie bewusst **nicht** nimmt

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| «Erstes passendes Element» als Fallback | Liefert die falsche Granularität/Periode unter der richtigen Überschrift |
| Fallback auf gecachte Daten ohne Altersangabe | Stale wird als aktuell gelesen |
| Fallback auf eine andere Region/Entität («nächstgelegene Station») ohne Ausweis | Antwort bezieht sich auf etwas anderes als die Frage |
| Gröbere Auflösung stillschweigend | Modell rechnet mit Tageswerten wie mit Momentanwerten |
| Nur der Erfolgsfall getestet | Der Substitutionszweig ist genau der ungetestete |

## Remediation

### Schritt 1: Fallbacks klassifizieren

Zwei Spalten: *lockert den Weg* (Retry, Dump, Cache — in Ordnung) und *lockert die Sache* (anderes Asset, andere Periode, andere Entität — prüfen).

### Schritt 2: Substitutionen auflösen

Entweder eskalieren oder ausweisen. Ausweisen heisst: ein Feld in der Antwort, das die Abweichung benennt — nicht ein Satz im Markdown, den ein JSON-Konsument nie sieht.

### Schritt 3: Den Nicht-Fund testen

Der Test, der fehlt, ist fast immer der über den leeren Kandidatensatz.

## Effort

S–M — ein halber Tag pro Server. Das Klassifizieren geht schnell; die Entscheidung «eskalieren oder ausweisen» ist die eigentliche Arbeit.

## References

- Portfolio-Fundstück `meteoswiss-mcp#33` — Fallback lieferte Tageswerte ab 1980 als «aktuelle Beobachtung»
- `ARCH-003` — «Not Found»-Anti-Pattern (Heuristiken statt leerer Antworten — dieser Check zieht die Grenze)
- `DRIFT-001` — URL-Konstruktion an einer Stelle (der Fehler, der diesen hier verdeckte)
- `FID-003` — Leermenge von Abwesenheit unterscheidbar
- `DRIFT-003` — Assertions müssen den Degradationspfad ausschliessen
