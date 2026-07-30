---
id: DRIFT-004
title: "Endpoint-Konstanten live verifiziert — ein Mock pinnt die eigene Annahme"
category: DRIFT
severity: high
applies_when: 'tools_make_external_requests == true'
pdf_ref: "Custom (Portfolio-Fundstück meteoswiss-mcp#35, 2026-07-30)"
evidence_required: 2
---

# DRIFT-004 — Der Mock kann das Abschalten eines Endpoints nicht bemerken

## Description

`FID-002` und der Recall-Canary decken ab, dass ein Mock eine falsche Annahme über den **Umfang** einer Antwort nicht widerlegen kann. Derselbe Mechanismus gilt eine Ebene tiefer, für die **Existenz** des Endpoints.

Ein `respx`-Mock wird gegen die eigene Konstante registriert:

```python
r.get(OPEN_METEO_BASE).respond(200, json=FIXTURE)
```

Verschwindet der Endpoint upstream, antwortet der Mock unverändert. Die Konstante zeigt ins Leere, die Testsuite bleibt grün, und zwar dauerhaft — es gibt keinen Zeitpunkt, an dem dieser Aufbau den Ausfall bemerken könnte. Der Test prüft die Konsistenz des Servers mit sich selbst.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Open-Meteo hat die provider-eigenen Pfade abgeschafft. `https://api.open-meteo.com/v1/meteoswiss` antwortete mit 404, womit `meteo_forecast` und `meteo_school_check` gar keine Daten mehr lieferten — zwei von sechs Tools. Die Unit-Tests waren grün und mockten dieselbe tote URL. Aufgefallen ist es erst, als jemand die Live-Suite ausführte, die aus CI ausgeschlossen ist (siehe `DRIFT-005`).

Der Punkt ist nicht, dass Mocks falsch sind. Er ist, dass die Frage «existiert dieser Endpoint noch» prinzipiell nicht gemockt beantwortet werden kann, und dass es keinen anderen Test gibt, der sie stellt.

## Verification

### Modus 1: code_review

Erst die Endpoint-Konstanten sammeln, dann prüfen, ob irgendein Test sie unmockt anfasst:

```bash
# Endpoint-Konstanten
grep -rnE '^[A-Z_]+(_BASE|_URL|_ENDPOINT|_API)\s*=\s*"https?://' src/

# Werden sie irgendwo live verifiziert?
grep -rn "pytest.mark.live" tests/ | wc -l
grep -rnE '_BASE|_URL|_ENDPOINT' tests/ | grep -i "live\|smoke" | head
```

**Pass-Pattern** — ein Test, der die Konstante selbst gegen den Upstream hält:

```python
@pytest.mark.live
@pytest.mark.parametrize("url", [OPEN_METEO_BASE, GEOCODING_BASE, STAC_BASE])
async def test_endpoint_constants_are_reachable(url):
    """Contract-Canary: fängt abgeschaltete und umbenannte Endpoints.

    Prüft die Konstante, nicht eine Kopie davon — sonst prüft der Test
    wieder nur sich selbst.
    """
    async with httpx.AsyncClient(timeout=15) as c:
        resp = await c.get(url, params=MINIMAL_VALID_PARAMS[url])
    assert resp.status_code != 404, f"{url} → 404: Endpoint abgeschafft oder umbenannt?"
```

**Fail-Pattern** — die URL steht im Test nochmals als Literal:

```python
# Ändert sich die Konstante, prüft der Test weiterhin die alte URL.
r.get("https://api.open-meteo.com/v1/meteoswiss").respond(200, json=FIXTURE)
```

Mocks gegen die **importierte Konstante** registrieren, nicht gegen ein wiederholtes Literal. Das ist keine Stilfrage: Die Kopie überlebt jede Umstellung und dokumentiert danach einen Zustand, den es nicht mehr gibt.

### Modus 2: automated

Ausserhalb der Testsuite geht es auch ohne Zielrepo-Code — der Raw-URL-Probe aus dem [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) macht genau das wöchentlich:

```bash
python scripts/live_probe.py --manifest scripts/live_probe.manifest.json
```

## Pass Criteria

- [ ] Jede Endpoint-Konstante wird von mindestens einem Live-Test oder einem Probe-Manifest abgedeckt
- [ ] Mocks registrieren gegen die importierte Konstante, nicht gegen ein wiederholtes URL-Literal
- [ ] Der Live-Test unterscheidet 404 (Endpoint weg) von 5xx (transient) — nur Ersteres ist ein Befund
- [ ] Die Abdeckung ist vollständig: kein Endpoint, der nur in Mocks vorkommt

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| URL als Literal im Test wiederholt | Konstante ändert sich, Test prüft die alte URL weiter |
| Nur der Haupt-Endpoint live geprüft | Sekundäre Endpoints (Geocoding, Assets, Vokabular) sterben unbemerkt |
| Live-Test prüft nur `status_code == 200` gegen die Basis-URL | Fängt das Abschalten, nicht die Umbenennung eines Pfad-Segments |
| Kein Live-Test, weil «CI hat kein Netz» | Der Ort dafür ist ein geplanter Lauf, nicht keiner (siehe `DRIFT-005`) |

## Remediation

### Schritt 1: Konstanten inventarisieren

Jede `*_BASE`/`*_URL` in `src/` auflisten. Erfahrungsgemäss sind es mehr als erinnert — Geocoding, Asset-Hosts und Vokabular-Endpoints werden beim ersten Zählen übersehen.

### Schritt 2: Contract-Canary schreiben

Ein parametrisierter `@pytest.mark.live`-Test über alle Konstanten. Er braucht pro Endpoint ein minimales gültiges Parameter-Set — das ist der eigentliche Aufwand und lohnt sich, weil es zugleich dokumentiert, was ein gültiger Aufruf ist.

### Schritt 3: Mocks auf die Konstante umstellen

```diff
- r.get("https://api.open-meteo.com/v1/meteoswiss").respond(...)
+ r.get(OPEN_METEO_BASE).respond(...)
```

### Schritt 4: Dafür sorgen, dass er läuft

Ein Live-Test, den niemand ausführt, ist kein Schutz. Siehe `DRIFT-005`.

## Effort

S — ein bis zwei Stunden pro Server. Der Canary ist kurz; das minimale Parameter-Set pro Endpoint kostet die Zeit.

## References

- Portfolio-Fundstück `meteoswiss-mcp#35` — `/v1/meteoswiss` abgeschafft, zwei Tools tot, Unit-Tests grün
- `OPS-001` — Test-Strategie
- `DRIFT-005` — Live-Tests laufen geplant
- `FID-002` — Recall-Ground-Truth (dieselbe Mock-Grenze auf der Umfangs-Ebene)
- `mcp-continuous-auditor` → `scripts/live_probe.py`
