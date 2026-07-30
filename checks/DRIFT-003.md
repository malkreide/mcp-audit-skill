---
id: DRIFT-003
title: "Kein Test-Assert wird vom Degradationspfad erfüllt"
category: DRIFT
severity: high
applies_when: 'always'
pdf_ref: "Custom (Portfolio-Fundstück meteoswiss-mcp#33/#35/#37, 2026-07-30)"
evidence_required: 3
---

# DRIFT-003 — Assertions müssen den Fehlerfall ausschliessen

## Description

Graceful Degradation ist Pflicht (`ARCH-003`, Probe-Skill 3.5): Fällt die Quelle aus, liefert der Server keine Exception ans Modell, sondern eine wohlgeformte Antwort mit Direktlinks und einem Hinweis. Das ist richtig — und hat einen Preis, den kaum jemand einpreist.

**Die Degradation verwandelt einen Ausfall in eine Antwort, die dem Erfolgsfall ähnelt.** Sie nennt dieselbe Station, denselben Ort, dieselben Stichworte. Jede Assertion, die nur auf solche Stichworte prüft, ist damit gegen genau den Ausfall blind, den sie fangen soll. Der Test läuft grün durch einen Totalausfall.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Drei Tools lieferten nichts — `meteo_current` einen 404 für jede Station, `meteo_forecast` und `meteo_school_check` gar keine Daten. Die Testsuite war grün. Drei separate Tests waren so formuliert, dass der Degradationspfad sie erfüllte:

| Test | Assertion | Warum blind |
|---|---|---|
| `test_live_meteo_current_klo` | `"KLO" in result or "Zürich" in result` | Beides steht auch in der Fehlermeldung |
| `test_live_geocode_leutschenbach` | Koordinaten-Box `8.4 < lon < 8.7` | Die *falsche* Gemeinde (Dübendorf, 8.62) liegt darin |
| `meteo_forecast` | — | Der Erfolgspfad war überhaupt nicht getestet, nur Geocoding-Fehlerpfade |

Der zweite ist der lehrreichste: Die Assertion war nicht zu schwach für einen Ausfall, sondern zu schwach für einen **Fehlgriff**. Sie hätte auch dann bestanden, wenn der Server Wetter aus der Nachbargemeinde geliefert hätte.

## Verification

### Modus 1: code_review

Voraussetzung ist, dass der Degradationspfad überhaupt maschinell erkennbar ist. Zuerst den Marker bestimmen:

```bash
# Wie meldet der Server einen Ausfall? Feld oder Präfix?
grep -rnE 'status\s*[:=]\s*"(degraded|unavailable)"|⚠️|nicht abrufbar|not available' src/ | head
```

Dann die Tests dagegen halten:

```bash
# Tests, die ein Tool aufrufen, aber den Degradationsmarker nirgends ausschliessen
grep -rn "await meteo_\|await client.call_tool\|_tool(" tests/ -l | while read -r f; do
  grep -q 'assert.*not in\|assertNotIn\|status.*==.*"ok"' "$f" || echo "prüfen: $f"
done
```

**Pass-Pattern:**

```python
result = await meteo_current(CurrentInput(station="KLO"))

assert "⚠️" not in result          # zuerst: nicht der Degradationspfad
assert "21.8" in result             # dann erst der Inhalt
assert "30.07.2026 13:20" in result
```

Sauberer, wenn der Server ein strukturiertes Statusfeld führt:

```python
assert payload["status"] == "ok"
assert payload["payload"]["beobachtungen"]
```

**Fail-Pattern:**

```python
result = await meteo_current(CurrentInput(station="KLO"))
# Beide Strings stehen auch in der Fehlermeldung — der Test besteht im Ausfall.
assert "KLO" in result or "Zürich" in result
```

### Modus 2: runtime_test

Die Gegenprobe, die den Test wirklich beweist: Upstream mocken, sodass er scheitert, und prüfen, dass die Erfolgstests **rot** werden.

```python
@pytest.mark.asyncio
async def test_success_assertions_fail_on_the_degradation_path(monkeypatch):
    """Wenn dieser Test scheitert, prüfen die Erfolgstests nichts."""
    with respx.mock(assert_all_called=False) as r:
        r.get(UPSTREAM_URL).respond(503)
        result = await meteo_current(CurrentInput(station="KLO"))
    assert "⚠️" in result   # der Degradationspfad ist erkennbar …
    assert "21.8" not in result   # … und trägt keine Messwerte
```

## Pass Criteria

- [ ] Der Degradationspfad ist maschinell erkennbar (Statusfeld, oder ein dokumentierter, eindeutiger Marker)
- [ ] Jeder Test des Erfolgspfads schliesst den Degradationspfad **explizit** aus, bevor er Inhalt prüft
- [ ] Assertions prüfen Werte, die nur im Erfolgsfall vorkommen — keine Stichworte, die auch in der Fehlermeldung stehen
- [ ] Bereichs-Assertions (Koordinaten, Zeitfenster, Grössenordnungen) sind eng genug, dass ein plausibler Fehlgriff sie reisst
- [ ] Für jedes Tool existiert mindestens ein Test des **Erfolgspfads**, nicht nur der Fehlerpfade

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| `assert <Ortsname> in result` | Der Ortsname steht in der Fehlermeldung; Test besteht im Ausfall |
| Grosszügige Bereichs-Assertion | Der falsche Datensatz liegt im Bereich; Fehlgriff wird durchgewinkt |
| Nur Fehlerpfade getestet | Der Erfolgspfad kann jederzeit brechen, ohne dass es auffällt |
| Degradation nur als Prosa (`⚠️ …`) | Tests müssen auf Strings prüfen; jede Textänderung entwertet sie stillschweigend |
| `assert result` / `assert len(result) > 0` | Die Fehlermeldung ist auch nicht leer |

## Remediation

### Schritt 1: Degradation strukturiert machen

Wenn der Ausfall nur an einem Emoji oder einer deutschen Wendung erkennbar ist, zuerst das beheben — sonst hängt jede Testverschärfung an einem Textliteral:

```python
class ServerResponse(BaseModel):
    status: Literal["ok", "degraded", "unavailable"] = "ok"
    degraded_reason: str | None = None
```

### Schritt 2: Assertions umdrehen

Erst ausschliessen, dann prüfen. Der Ausschluss gehört in die **erste** Zeile nach dem Aufruf, nicht ans Ende.

### Schritt 3: Den Test testen

Einmal pro Tool die Gegenprobe aus Modus 2 schreiben. Sie ist der einzige Beleg, dass die Erfolgstests etwas prüfen — und sie kostet je fünf Zeilen.

## Effort

S–M — pro Server ein halber Tag. Der Aufwand steckt im Durchgehen der bestehenden Assertions, nicht im Schreiben der neuen.

## References

- Portfolio-Fundstück `meteoswiss-mcp#33` — drei Tools tot, Suite grün
- `ARCH-003` — «Not Found»-Anti-Pattern (die Degradation, die dieser Check testbar hält)
- `OPS-001` — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert
- `DRIFT-004` — Endpoint-Konstanten live verifizieren
- `FID-003` — Leermenge von Abwesenheit unterscheidbar (dieselbe Logik auf der Datenseite)
