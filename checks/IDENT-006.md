---
id: IDENT-006
title: "Veröffentlichte Version ist der aktuelle Stand — kein Release-Gap"
category: IDENT
severity: high
applies_when: 'always'
pdf_ref: "Custom (Portfolio-Fundstück meteoswiss-mcp#31, 2026-07-30)"
evidence_required: 2
---

# IDENT-006 — Kein Release-Gap zwischen `main` und dem Artefakt

## Description

`IDENT-001` bis `IDENT-005` prüfen, ob die gemeldete Version **korrekt** ist. Dieser Check prüft, ob sie **aktuell** ist.

Das ist eine eigene Fehlerklasse, und die unbequemste der Kategorie: Ein Repository kann grün, auditiert und vollständig korrigiert sein, während jedes `pip install` weiterhin das kaputte Release ausliefert. Nichts widerspricht dem, denn CI testet den Branch, nie das Artefakt. Der Server ist repariert; die Nutzenden merken nichts davon.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Die Migration auf das `mcp`-2.x-SDK war am 29. auf `main` gemergt. PyPI führte weiter `0.4.0`, das `mcp.server.fastmcp` importiert — ein Modul, das `mcp` 2.0.0 am Tag zuvor entfernt hatte. Jede frische Installation starb drei Tage lang beim Import:

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

Gefunden hat es ein aussenstehender Nutzer, nicht die Testsuite, nicht das Audit. Und es wiederholte sich am selben Nachmittag: `0.5.0` wurde publiziert, drei weitere Fixes landeten auf `main`, und bis zum nächsten Release lieferte PyPI einen Server aus, dessen `meteo_current`, `meteo_forecast` und `meteo_school_check` allesamt nichts zurückgaben — drei von sechs Tools.

Die schärfste Ausprägung ist nicht «noch nicht released», sondern **ein Tag, den der Index nicht hat**: Dann wurde ein Release geschnitten und ist nie angekommen — ein fehlgeschlagener Workflow, oder eine hängende Environment-Freigabe. Die Maintainerin glaubt bereits, es sei publiziert.

## Verification

### Modus 1: automated

Deterministisch prüfbar mit `release_gap.py` aus dem [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor):

```bash
python scripts/release_gap.py --target <repo> --format json
```

Ohne dieses Werkzeug von Hand:

```bash
# Was der Index führt
curl -s "https://pypi.org/pypi/<dist>/json" | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"

# Was das Repo führt
grep -E '^version' pyproject.toml

# Was seit dem letzten Release aufgelaufen ist
git fetch --tags
LAST=$(git tag --list --sort=-v:refname | head -1)
git log "$LAST..HEAD" --no-merges --format='%cs %s'
```

**Pass-Pattern:**

```
PyPI 0.6.0 | pyproject 0.6.0 | letzter Tag v0.6.0 | 0 Commits seit dem Release
```

**Fail-Pattern (der Vorfall):**

```
PyPI 0.4.0 | pyproject 0.4.0 | letzter Tag v0.4.0
5 Commits seit v0.4.0, ältester 3.7 Tage alt, darunter 1× fix, 1× feat
```

**Fail-Pattern (die schärfere Variante):**

```
PyPI 0.5.0 | letzter Tag v0.6.0   → das Release wurde geschnitten und ist nie angekommen
```

### Modus 2: config_check

Der Publish-Workflow muss überhaupt auslösen können. Ein `on: release`-Trigger, den niemand auslöst, ist kein Automatismus, sondern ein manueller Schritt mit Extraaufwand.

```bash
grep -A3 '^on:' .github/workflows/publish.yml
```

Prüfen: Löst der Workflow auf `release: published` oder auf Tag-Push aus? Bei `release: published` bleibt das Erstellen des GitHub-Releases ein menschlicher Schritt — das ist zulässig und oft gewollt, muss aber im Release-Prozess dokumentiert sein, sonst bleibt es liegen.

## Pass Criteria

- [ ] Die auf dem Index veröffentlichte Version entspricht dem letzten Release-Tag
- [ ] Kein Release-Tag existiert, den der Index nicht hat (kein fehlgeschlagener Publish)
- [ ] Keine nutzerwirksamen Commits (`fix`, `feat`, `perf`, `revert`) älter als 7 Tage unveröffentlicht
- [ ] `[Unreleased]` im CHANGELOG ist entweder leer oder jünger als die Release-Kadenz
- [ ] Der Release-Prozess ist im README oder CONTRIBUTING beschrieben, inklusive des manuellen Schritts, falls es einen gibt

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Fix auf `main`, Release vergessen | Nutzende laufen weiter in den behobenen Fehler — der teuerste Fall, weil alle Beteiligten ihn für erledigt halten |
| Release geschnitten, Publish-Workflow rot | Niemand schaut nach dem Merge nochmals hin; der Tag suggeriert Erfolg |
| Version in `pyproject.toml` gebumpt, nie getaggt | Vorbereitetes Release, das liegen bleibt |
| «Ist ja nur ein Bugfix, kommt mit dem nächsten Feature» | Verlängert das Fenster genau für die Klasse von Fehlern, die sofort weh tut |

## Remediation

### Schritt 1: Die Lücke messen, nicht schätzen

`release_gap.py` gegen das Repo laufen lassen. Die Frage ist nicht «sind wir vorne», sondern «wie lange schon, und was steckt drin» — `fix:` unveröffentlicht ist eine andere Tatsache als `docs:`.

### Schritt 2: Release nachziehen

Bei nutzerwirksamen unveröffentlichten Commits: Version bumpen, CHANGELOG-Abschnitt aus `[Unreleased]` bilden, taggen, Release erstellen. Danach **aus dem Index verifizieren**, nicht aus dem Build-Log:

```bash
python -m venv /tmp/verify && /tmp/verify/bin/pip install --no-cache-dir <dist>
/tmp/verify/bin/pip show <dist> | head -2
```

Ein grüner Publish-Job ist ein Zwischenschritt, keine Bestätigung.

### Schritt 3: Die Lücke klein halten

Kein neuer Mechanismus nötig — nur die Reihenfolge umdrehen: Ein Fix, der einen gemeldeten Bug schliesst, wird nicht «beim nächsten Feature» ausgeliefert, sondern zieht sein eigenes Patch-Release. Bei Servern mit seltener Kadenz gehört das explizit ins CONTRIBUTING.

## Effort

S — Messung Minuten, Nachziehen eines Releases unter einer Stunde. Der Aufwand liegt in der Disziplin, nicht in der Technik.

## References

- Portfolio-Fundstück `meteoswiss-mcp#31` — `uvx` crasht, Fix lag seit drei Tagen auf `main`
- `IDENT-002` — `__version__` aus der installierten Distribution (Korrektheit statt Aktualität)
- `IDENT-003` — Werte, die die Pipeline überschreibt
- `mcp-continuous-auditor` → `scripts/release_gap.py`, `skills/release-gap/SKILL.md`
