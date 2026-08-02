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

Eine schärfere Ausprägung ist nicht «noch nicht released», sondern **ein Tag, den der Index nicht hat**: Dann wurde ein Release geschnitten und ist nie angekommen — ein fehlgeschlagener Workflow, oder eine hängende Environment-Freigabe. Die Maintainerin glaubt bereits, es sei publiziert.

### Was dieser Check nicht sagt: dass das Artefakt läuft

Dieser Check misst einen **Abstand**: zwischen dem, was auf `main` steht, und dem, was auf dem Index liegt. Er vergleicht dafür Etiketten — Versionsnummern in `pyproject.toml`, im letzten Tag und in den Index-Metadaten. Stimmen alle drei überein, heisst das genau eines: **Niemand hat vergessen zu publizieren.**

Es heisst nicht, dass das Publizierte installiert, importiert oder antwortet. Diese Frage ist eine eigene Achse, sie ist unabhängig von jedem Abstand, und sie steht als eigener Check: **[`IDENT-007`](IDENT-007.md) — das veröffentlichte Artefakt startet in einer leeren Umgebung.**

Die Trennung ist nicht formal. Der Fall, der sie erzwungen hat (`zurich-opendata-mcp` `0.5.1`, reproduziert am 2026-07-31), bestand **jedes Kriterium dieses Checks**: Repo, Tag und Index standen alle drei auf `0.5.1`, null unveröffentlichte Commits — und das Artefakt starb beim Import, weil sich eine ungedeckelte Abhängigkeit unter ihm bewegt hatte (`DEP-001`). Ein grünes `IDENT-006` war dort die Wahrheit und trotzdem wertlos.

**Für den Audit heisst das:** Ein Pass hier ist kein Teilbeleg für `IDENT-007`, in keiner Richtung. Beide Checks laufen, beide werden einzeln beantwortet. Der häufigste Irrtum der ganzen Kategorie ist, aus gleichen Etiketten auf ein funktionierendes Paket zu schliessen.

## Verification

### Modus 1: automated — die Metadaten-Tiefe

Was der Index führt, welche Releases zurückgezogen sind, wie weit `main` seit dem letzten Release fortgelaufen ist. Zwei HTTP-Requests und etwas Git, ohne venv und ohne Installation.

```bash
python scripts/shipped_probe.py --target <repo> --metadata-only --format json
```

`scripts/shipped_probe.py` stammt aus dem [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor). Mit `--metadata-only` läuft nur die Lücken-Achse; ohne das Flag installiert und startet die Probe zusätzlich, und das ist `IDENT-007`.

| Exit | Bedeutung | Status für `IDENT-006` |
|---|---|---|
| `0` | Artefakt entspricht dem Repo | pass |
| `2` | Befund — nicht auf dem Index, veraltet, Versionsdivergenz | `fail` |
| `127` | Die Harness lief nicht (kein Netz zum Index, Git-Fehler) | `todo` |

Exit `127` ist ausdrücklich **kein** Pass: Ein Vergleich, der nicht stattgefunden hat, ist keine Bestätigung — dieselbe Regel wie in `OPS-005`.

Die Befundcodes dieser Achse: `NOT_ON_INDEX`, `STALE_ON_INDEX`, `PUBLISH_GAP`, `TAG_NOT_ON_INDEX`, `TAG_DIFFERS`, `VERSION_DIFFERS`, `UNTAGGED_VERSION`, `INDEX_AHEAD`, `UNRELEASED`, `CHANGELOG_UNRELEASED`. Die Codes der Gesundheits-Achse (`INSTALL_FAILED`, `DOES_NOT_RUN`, `TOOL_ERROR` …) gehören zu `IDENT-007` und werden dort ausgewertet.

**Zwei Codes werden gern falsch gelesen:** `NOT_ON_INDEX` heisst «nie publiziert» — der Release-Prozess lief für dieses Paket noch nie, und der Fix ist, ihn einzurichten. `STALE_ON_INDEX` heisst «publiziert, aber hinterher» — der Prozess existiert und hat diesmal nicht ausgelöst, und der Fix steht im Workflow-Run, der meist an einer Freigabe oder einer OIDC-Vertrauensstellung scheiterte. Beides als «PyPI ist veraltet» zu melden schickt die Maintainerin an die falsche Stelle.

> `release_gap.py` ist seit dem Zusammenlegen **nur noch ein Kompatibilitäts-Shim** über genau diesen Aufruf — Argument-Weiterleitung und Exit-Code-Übersetzung, keine eigene Logik, im Repo ausdrücklich zur Löschung vorgesehen, sobald niemand mehr darauf zeigt. Es übersetzt ausserdem auf das alte Vokabular zurück (`1` statt `2` für Befunde), was den Unterschied zwischen «Befund» und «Vergleich nicht möglich» wieder einebnet. Für neue Audits deshalb `shipped_probe.py --metadata-only` aufrufen, nicht den Shim.

Ohne diese Werkzeuge von Hand:

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

**Fail-Pattern (eine schärfere Variante):**

```
PyPI 0.5.0 | letzter Tag v0.6.0   → das Release wurde geschnitten und ist nie angekommen
```

**Der Fall, den dieser Modus nicht sehen kann:**

```
PyPI 0.5.1 | pyproject 0.5.1 | letzter Tag v0.5.1 | 0 Commits seit dem Release
```

Nach jedem Kriterium dieses Checks ein Pass — und genau dieser Stand war ein totes Artefakt. Dass er hier durchgeht, ist kein Mangel des Modus, sondern die Grenze der Frage: Deshalb gibt es `IDENT-007`.

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
- [ ] `[Unreleased]` im CHANGELOG ist entweder leer oder jünger als die Release-Kadenz — und beschreibt tatsächlich Unveröffentlichtes (`DRIFT-006`)
- [ ] Der Release-Prozess ist im README oder CONTRIBUTING beschrieben, inklusive des manuellen Schritts, falls es einen gibt
- [ ] Der Vergleich hat stattgefunden — Exit `127` der Probe ist `todo`, nicht Pass
- [ ] `IDENT-007` wurde **separat** beantwortet; ein Pass hier wurde nicht als Beleg dafür verbucht

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Fix auf `main`, Release vergessen | Nutzende laufen weiter in den behobenen Fehler — der teuerste Fall, weil alle Beteiligten ihn für erledigt halten |
| Release geschnitten, Publish-Workflow rot | Niemand schaut nach dem Merge nochmals hin; der Tag suggeriert Erfolg |
| Version in `pyproject.toml` gebumpt, nie getaggt | Vorbereitetes Release, das liegen bleibt |
| «Ist ja nur ein Bugfix, kommt mit dem nächsten Feature» | Verlängert das Fenster genau für die Klasse von Fehlern, die sofort weh tut |
| Aus «Repo, Tag und Index tragen dieselbe Nummer» auf Gesundheit geschlossen | Die Grenze dieses Checks in einem Satz. Drei gleiche Etiketten, ein totes Artefakt — `IDENT-007` |
| `NOT_ON_INDEX` und `STALE_ON_INDEX` beide als «PyPI ist veraltet» gemeldet | Nie publiziert vs. diesmal nicht ausgelöst: zwei verschiedene Fixes an zwei verschiedenen Stellen |
| Exit `127` der Probe als Pass verbucht | Ein Vergleich, der nicht stattfand, ist keine Bestätigung (`OPS-005`) |

## Remediation

### Schritt 1: Zuerst `IDENT-007`, dann die Lücke

Wenn das publizierte Artefakt nicht läuft, ist die Lücke eine Nebenfrage: Es gibt dann nichts «nachzuziehen», sondern etwas zu ersetzen, und zwar sofort. Läuft es, ist die Frage nicht «sind wir vorne», sondern «wie lange schon, und was steckt drin» — `fix:` unveröffentlicht ist eine andere Tatsache als `docs:`.

### Schritt 2: Release nachziehen

Version bumpen, CHANGELOG-Abschnitt aus `[Unreleased]` bilden, taggen, Release erstellen. Danach **aus dem Index verifizieren**, nicht aus dem Build-Log — der Ablauf dafür steht in `IDENT-007`, Remediation. Ein grüner Publish-Job ist ein Zwischenschritt, keine Bestätigung. Ein grünes CI erst recht nicht: Es testet den Branch, nie das Artefakt.

### Schritt 3: Die Lücke klein halten

Kein neuer Mechanismus nötig — nur die Reihenfolge umdrehen: Ein Fix, der einen gemeldeten Bug schliesst, wird nicht «beim nächsten Feature» ausgeliefert, sondern zieht sein eigenes Patch-Release. Bei Servern mit seltener Kadenz gehört das explizit ins CONTRIBUTING.

## Effort

S — Messung Minuten (zwei Requests und etwas Git), Nachziehen eines Releases unter einer Stunde. Der Aufwand liegt in der Disziplin, nicht in der Technik.

## References

- Portfolio-Fundstück `meteoswiss-mcp#31` — `uvx` crasht, Fix lag seit drei Tagen auf `main`
- `IDENT-007` — läuft das Artefakt überhaupt? Die zweite, unabhängige Achse; der Grund, warum dieser Check nur noch den Abstand misst
- `DEP-001` — ungedeckelte Abhängigkeit: die Ursache dafür, dass ein Artefakt ohne Release-Gap trotzdem stirbt
- `DRIFT-006` — `[Unreleased]` darf dem Code nicht widersprechen; der Alterstest hier setzt voraus, dass der Abschnitt stimmt
- `IDENT-002` — `__version__` aus der installierten Distribution (Korrektheit statt Aktualität)
- `IDENT-003` — Werte, die die Pipeline überschreibt
- `OPS-005` — übersprungen ist nicht bestanden; Exit `127` der Probe folgt dieser Regel
- `mcp-continuous-auditor` → `scripts/shipped_probe.py --metadata-only`. `scripts/release_gap.py` ist nur noch ein Kompatibilitäts-Shim darüber und zur Löschung vorgesehen — nicht für neue Audits verwenden
