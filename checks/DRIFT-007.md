---
id: DRIFT-007
title: "Feldnamen sind Teil des Vertrags"
category: DRIFT
severity: high
applies_when: 'tools_make_external_requests == true'
adoption: advisory
pdf_ref: "Custom (Portfolio-Fundstück zh-education-mcp / BISTA, 2026-08-03)"
evidence_required: 2
---

# DRIFT-007 — Feldnamen sind Teil des Vertrags

## Description

Ein Endpoint kann bleiben, seine Antwort kann wohlgeformt bleiben, ihre Struktur kann bleiben — und der Code findet trotzdem nichts, weil sich die **Schreibweise** eines Feldnamens geändert hat. Das ist kein Sonderfall der Strukturänderung, sondern die kleinste denkbare Vertragsänderung: ein Buchstabe.

**Belegfall (`zh-education-mcp` / BISTA, 2026-08-03).** Eine Quelle wechselte die Schreibweise ihrer CSV-Kopfzeile von `Schulgemeinde` auf `schulgemeinde`. Der Code hatte die Grossschreibung fest verdrahtet:

```python
rows = [r for r in rows if r["Schulgemeinde"] == gemeinde]
```

Danach fand er nichts mehr und meldete «nicht gefunden» — vier von sechs Datensätzen, acht Tools, **alle Unit-Tests grün**. Ein Ausfall, der wie eine Antwort aussieht.

**Und die Schreibweise ist nicht einmal einheitlich.** Am selben Tag lieferten vier der sechs genutzten Endpunkte derselben Quelle klein, zwei gross — und zwei mischten **innerhalb einer einzigen Kopfzeile** (`gebiet_Bezeichnung`, `staatsangehoerigkeit_ISO2_Code`). Das ist der Grund, warum «auf die neue Schreibweise umstellen» keine Behebung ist: Es ist dieselbe feste Verdrahtung, nur in die andere Richtung, und beim nächsten Wechsel reisst sie dasselbe Loch. Wer heute sechs Endpunkte mit sechs verschiedenen Literalen bedient, hat sechs Annahmen, die alle heute stimmen.

**Warum die Tests grün blieben.** Der Mock trägt die Schreibweise, die der Autor beim Schreiben des Mocks für richtig hielt — dieselbe, die der Produktivcode annimmt. Ein Fixture mit `{"Schulgemeinde": …}` bestätigt genau den Irrtum, den es widerlegen müsste. Dieselbe Grenze wie in `DRIFT-004`, eine Ebene weiter innen: Dort kann ein Mock das Verschwinden eines Endpoints nicht bemerken, hier nicht die Umbenennung seiner Felder.

**Abgrenzung zu `FID-006`, und sie ist eng.** `FID-006` verlangt, die **gelesenen Felder** gegen die **echte Antwort** zu bestätigen und bei Abweichung laut zu scheitern. Das fängt den Belegfall — aber es ist nicht dieselbe Behebung, und auf einer Quelle wie BISTA ist es die falsche: Ein Server, der pro Endpunkt streng auf die dort heute geltende Schreibweise prüft, hat sechs korrekte Prüfungen und scheitert beim nächsten Wechsel genauso laut wie vorher leise. `FID-006` sorgt dafür, dass der Ausfall **auffällt**; dieser Check dafür, dass er **nicht eintritt**. Deshalb ist die Normalisierung an der Parse-Grenze hier ein vollwertiger Pass-Weg, und `FID-006` bleibt die Auffanglinie für alles, was sich nicht normalisieren lässt (verschobene Ebenen, umbenannte Felder jenseits der Schreibweise).

**Abgrenzung zu `DRIFT-004`.** Der prüft die Endpoint-**Konstanten** live — eine Ebene darüber. Ein Endpoint kann erreichbar und richtig sein und trotzdem andere Feldnamen liefern als gestern.

**Abgrenzung zu `IDENT-001`.** Dort wird ebenfalls normalisiert, aber zum **Vergleich** eines Tokens mit einem Erwartungswert. Hier wird die **gelesene Datenstruktur** normalisiert, bevor irgendjemand sie anfasst.

`high`: Der Ausfall ist still und vollständig. Ein Tool, das nichts mehr findet, wird vom Modell als «gibt es nicht» gelesen — dieselbe Konfabulations-Einladung wie in `FID-003`, ausgelöst durch einen Grossbuchstaben.

## Verification

### Modus 1: code_review (fest verdrahtete Schreibweisen an der Parse-Grenze)

```bash
# Wo werden Rohzeilen gelesen? Das ist die Grenze, an der normalisiert gehört.
grep -rnE 'csv\.DictReader|csv\.reader|read_csv|\.json\(\)' src/ --include=*.py

# Feldzugriffe mit Grossbuchstaben im Schlüssel — der Fund des Belegfalls.
grep -rnE '\[["'"'"'][A-Za-z_]*[A-Z][A-Za-z_]*["'"'"']\]|\.get\(\s*["'"'"'][A-Za-z_]*[A-Z]' \
  src/ --include=*.py

# Gibt es überhaupt eine Normalisierung, und liegt sie an der Grenze?
grep -rnE '_normalise_keys|_normalize_keys|casefold\(\)|\.lower\(\)\s*:' src/ --include=*.py
```

Ein gemischt geschriebener Schlüssel im Zugriff ist der Befund — nicht, weil Grossschreibung falsch wäre, sondern weil sie eine Annahme über die Quelle ist, die nirgends bestätigt wird.

**Pass-Pattern A — an der Parse-Grenze normalisieren** (der Weg des Belegfalls):

```python
def _normalise_keys(row: dict) -> dict:
    """Senkt die Spaltennamen einer Zeile auf Kleinschreibung.

    Die Quelle schreibt die Kopfzeile nicht einheitlich und hat die
    Schreibweise bereits gewechselt. Hier ist der einzige Ort, an dem es
    einmal geschehen muss; der Rest des Codes wird dadurch gegen den
    nächsten Wechsel unempfindlich.
    """
    return {(k or "").lower(): v for k, v in row.items()}


rows = [_normalise_keys(row) for row in csv.DictReader(io.StringIO(resp.text))]
```

Danach liest der ganze Server nur noch kleingeschriebene Namen, und die Quelle darf ihre Meinung ändern.

**Pass-Pattern B — bestätigen statt normalisieren.** Zulässig, wo Normalisierung nicht geht (die Quelle unterscheidet `id` und `ID` bedeutungstragend) oder nicht reicht. Dann greift `FID-006`: mindestens ein Test hält die gelesenen Feldnamen gegen eine **echte** Antwort, und eine Abweichung endet in einem eigenen Fehlertyp.

**Fail-Pattern:**

```python
rows = list(csv.DictReader(io.StringIO(resp.text)))
hits = [r for r in rows if r["Schulgemeinde"] == gemeinde]   # eine Schreibweise, fest
```

### Modus 2: runtime_test (gegen die echte Antwort, mit Gegenprobe)

Der Mock kann diese Klasse nicht widerlegen (siehe Description). Der Test gehört an die echte Antwort, und ohne Gegenprobe belegt er nur, dass heute nichts kaputt ist.

```python
@pytest.mark.live
async def test_the_field_names_we_read_are_the_field_names_that_arrive():
    """Contract-Canary auf der Ebene der Feldnamen — pro Endpunkt."""
    for endpoint in ALL_ENDPOINTS:
        rows = await _fetch(endpoint)
        assert rows, f"{endpoint}: leer — hier wäre schon das der Befund"
        assert set(_READ_FIELDS[endpoint]) <= set(rows[0]), sorted(rows[0])


def test_a_changed_spelling_still_finds_the_row():
    """Gegenprobe: den echten Wechsel aus dem Belegfall nachstellen."""
    for header in ("Schulgemeinde", "schulgemeinde", "SCHULGEMEINDE"):
        rows = [_normalise_keys({header: "Adliswil", "anzahl": "7"})]
        assert _filter_rows(rows, schulgemeinde="Adliswil"), header
```

Läuft die Live-Suite gar nicht, ist der Ausgang `todo`, nicht `pass` (§2.6). Dass sie auch **ausgeführt** wird, prüft `DRIFT-005`.

## Pass Criteria

- [ ] Für jeden externen Endpunkt gilt **einer** der beiden Wege: die Feldnamen werden an der Parse-Grenze normalisiert, **oder** mindestens ein Test hält die gelesenen Feldnamen gegen eine **echte** Antwort (`FID-006`)
- [ ] Wird normalisiert, geschieht das an **genau einer** Stelle — dort, wo die Rohzeile entsteht, nicht verstreut an den Lesestellen
- [ ] Die Normalisierungsfunktion begründet im Docstring, **warum** sie existiert; ein `.lower()` ohne Grund wird beim nächsten Refactoring wegoptimiert
- [ ] Normalisiert wird nur die **Schreibweise**, nicht die Identität des Namens — `anzahl_total` und `anzahlTotal` bleiben verschieden
- [ ] Kein Feldzugriff im Code trägt eine Schreibweise, die die Quelle bereits gewechselt hat
- [ ] Endpunkte derselben Quelle mit **unterschiedlicher** Schreibweise werden nicht mit je einem eigenen Literal bedient
- [ ] **Gegenprobe:** Der Test ist einmal gegen die jeweils andere Schreibweise gelaufen und hat dort das erwartete Ergebnis geliefert — bei Normalisierung: gefunden; bei Bestätigung: angeschlagen

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Eine Schreibweise fest verdrahtet, die schon einmal gewechselt hat | Der nächste Wechsel erzeugt wieder ein «nicht gefunden» statt eines Fehlers |
| Auf die **neue** Schreibweise umgestellt statt normalisiert | Dieselbe feste Verdrahtung, andere Richtung; der Rückwechsel reisst dasselbe Loch |
| Pro Endpunkt ein eigenes Literal, weil die Quelle uneinheitlich schreibt | Sechs Annahmen, die alle heute stimmen und alle einzeln brechen |
| Verstreut an den Lesestellen normalisiert | Die Stelle, die es vergisst, ist genau die, die niemand testet |
| Nur gegen ein Fixture geprüft | Der Mock trägt die angenommene Schreibweise und bestätigt sie dauerhaft |
| So weit normalisiert, bis irgendetwas passt (Trennzeichen, Umlaute, Präfixe weg) | Zwei verschiedene Felder werden zu einem; erlaubt ist genau die Schreibweise |
| `KeyError` als «nicht gefunden» an das Modell gereicht | Ausfall, der wie eine Antwort aussieht (`FID-003`) |

## Remediation

```diff
+ def _normalise_keys(row: dict) -> dict:
+     """Senkt die Spaltennamen einer Zeile auf Kleinschreibung.
+
+     Die Quelle schreibt ihre Kopfzeile nicht einheitlich und hat die
+     Schreibweise am 2026-08-03 gewechselt. Hier ist der einzige Ort, an
+     dem das einmal geschehen muss.
+     """
+     return {(k or "").lower(): v for k, v in row.items()}
+
+
  async def _fetch_csv(endpoint: str) -> list[dict]:
      resp = await _http_get(f"{BASE}/{endpoint}")
      resp.raise_for_status()
-     return list(csv.DictReader(io.StringIO(resp.text)))
+     reader = csv.DictReader(io.StringIO(resp.text))
+     return [_normalise_keys(row) for row in reader]


- hits = [r for r in rows if r["Schulgemeinde"] == gemeinde]
+ hits = [r for r in rows if r["schulgemeinde"] == gemeinde]
```

## Effort

S — Pro Server 1–3 Stunden. Die Funktion ist drei Zeilen; die Zeit geht in das Auffinden aller Lesestellen und in den Test, der beide Schreibweisen bindet.

## References

- `FID-006` — Antwort**struktur** bestätigen; dort die Auffanglinie, hier die Vermeidung
- `DRIFT-004` — Endpoint-Konstanten live verifiziert: eine Ebene darüber
- `DRIFT-005` — dass die Live-Suite auch läuft
- `FID-003` — ein Ausfall, der wie eine Leermenge aussieht, ist eine Konfabulations-Einladung
- `IDENT-001` — Normalisierung zum Vergleich eines Tokens; hier Normalisierung der gelesenen Daten
- `OPS-001` — Live-Tests gemarkert, damit der Canary überhaupt einen Ort hat
