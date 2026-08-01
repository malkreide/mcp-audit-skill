---
id: IDENT-006
title: "Veröffentlichte Version ist der aktuelle Stand — kein Release-Gap"
category: IDENT
severity: high
applies_when: 'always'
pdf_ref: "Custom (Portfolio-Fundstücke meteoswiss-mcp#31, 2026-07-30; zurich-opendata-mcp 0.5.1, 2026-07-31)"
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

### Versionsgleichheit ist keine Aussage über die Gesundheit des Artefakts

Das ist die eigentliche Lehre, und sie ist unbequemer als die Lücke. **Der zweite Fall** (`zurich-opendata-mcp` `0.5.1`, reproduziert am 2026-07-31): Repo-Version, letzter Git-Tag und PyPI standen **alle drei auf `0.5.1`**. Jeder Versionsvergleich, den dieser Check bis dahin kannte, meldete «in sync» — und das Artefakt war tot:

```
$ uv run --with 'zurich-opendata-mcp==0.5.1' python -c "import zurich_opendata_mcp.app"
installed zurich-opendata-mcp: 0.5.1
installed mcp               : 2.0.0
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

Gebrochen hat es nichts im Repository. `0.5.1` hatte `mcp[cli]>=1.28.1` **ohne Obergrenze**; am 2026-07-28 erschien `mcp` 2.0.0 und entfernte `mcp.server.fastmcp` ersatzlos. Von da an löste jede frische Installation eine Major-Version auf, gegen die der Code nicht lief. Das publizierte Artefakt änderte sich, ohne dass jemand es publizierte.

Daraus folgen zwei Dinge, die den Check tragen:

1. **Der Schweregrad hängt nicht am Alter der Lücke.** Zwischen dem `mcp`-2.0.0-Release und dem Vorfall lagen ein bis drei Tage — die lückenbasierten Kriterien unten waren erfüllt, und zwar zu Recht. Ein Artefakt, das *jetzt* nicht startet, ist unabhängig davon ein sofortiger Befund. Wäre die Lücke null Tage alt, wäre es derselbe Befund.
2. **Gleiche Versionsnummern an drei Stellen sind ein Vergleich von Etiketten.** Sie sagen, dass niemand vergessen hat zu publizieren. Über das, was auf dem Index liegt, sagen sie nichts — nicht ob es installiert, nicht ob es importiert, nicht ob es antwortet. Die einzige Aussage darüber kommt daher, dass man es installiert und startet.

Der Check hat deshalb **zwei Achsen**: Ist der Abstand zwischen `main` und dem Artefakt klein (Lücke), und läuft das Artefakt überhaupt (Gesundheit). Sie sind unabhängig. Ein Server kann auf beiden bestehen, auf einer, oder auf keiner — und der häufigste Irrtum ist, aus der ersten auf die zweite zu schliessen.

## Verification

### Modus 1: automated — das Artefakt installieren und starten lassen (Achse Gesundheit)

**Der primäre Modus.** `scripts/shipped_probe.py` aus dem [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) installiert die Distribution **aus dem Index in ein frisches venv** — nie aus dem Checkout —, startet den installierten Entry Point und spricht ein echtes `initialize` plus einen echten `tools/call` mit ihm.

```bash
python scripts/shipped_probe.py --dist <dist> --target <repo> --format json
```

| Exit | Bedeutung | Status für `IDENT-006` |
|---|---|---|
| `0` | Artefakt entspricht dem Repo **und lief** | pass |
| `2` | Befund — nicht auf dem Index, veraltet, Versionsdivergenz, oder der installierte Server antwortete nicht | `fail` |
| `127` | Die Harness lief nicht (kein Netz zum Index, venv-Erstellung scheiterte) | `todo` |

Exit `127` ist ausdrücklich **kein** Pass: Ein Vergleich, der nicht stattgefunden hat, ist keine Bestätigung — dieselbe Regel wie in `OPS-005`.

Die Befundcodes trennen sich sauber auf die zwei Achsen:

| Achse | Codes |
|---|---|
| **Gesundheit** — das Artefakt läuft nicht | `INSTALL_FAILED`, `NO_ENTRYPOINT`, `DOES_NOT_RUN`, `TOOL_NO_ANSWER`, `TOOL_ERROR`, `TOOL_EMPTY`, `RELEASE_YANKED` |
| **Lücke** — Abstand zwischen `main` und Index | `NOT_ON_INDEX`, `STALE_ON_INDEX`, `PUBLISH_GAP`, `TAG_NOT_ON_INDEX`, `TAG_DIFFERS`, `VERSION_DIFFERS`, `UNTAGGED_VERSION`, `INDEX_AHEAD`, `UNRELEASED`, `CHANGELOG_UNRELEASED` |

**Zwei Codes werden gern falsch gelesen:**

- `NOT_ON_INDEX` heisst «nie publiziert» — der Release-Prozess lief für dieses Paket noch nie, und der Fix ist, ihn einzurichten. `STALE_ON_INDEX` heisst «publiziert, aber hinterher» — der Prozess existiert und hat diesmal nicht ausgelöst, und der Fix steht im Workflow-Run, der meist an einer Freigabe oder einer OIDC-Vertrauensstellung scheiterte. Beides als «PyPI ist veraltet» zu melden schickt die Maintainerin an die falsche Stelle.
- Ein `TOOL_ERROR` **beweist nicht allein**, dass das Artefakt kaputt ist. Die Probe läuft in einer Umgebung mit Default-Deny-Egress; ein Tool, dessen Upstream nicht auf der Allow-List steht, scheitert genau gleich. Vor dem Finding die Allow-List prüfen — der Report sagt das in seinem eigenen Text.

Hat der Server gar keine publizierte Distribution, meldet die Probe `not_applicable`. Dann entfällt die Gesundheits-Achse, die Lücken-Achse gilt weiter.

### Modus 2: automated — die Metadaten-Tiefe (Achse Lücke)

Die billige Hälfte: was der Index führt, welche Releases zurückgezogen sind, wie weit `main` seit dem letzten Release fortgelaufen ist. Zwei HTTP-Requests und etwas Git, ohne venv und ohne Installation.

```bash
python scripts/shipped_probe.py --target <repo> --metadata-only --format json
```

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

Nach jedem Metadaten-Kriterium ein Pass — und genau dieser Stand war der Vorfall oben. Modus 2 kann das nicht finden, weil er nur Etiketten vergleicht. Deshalb ist Modus 1 der primäre und nicht dieser.

### Modus 3: config_check

Der Publish-Workflow muss überhaupt auslösen können. Ein `on: release`-Trigger, den niemand auslöst, ist kein Automatismus, sondern ein manueller Schritt mit Extraaufwand.

```bash
grep -A3 '^on:' .github/workflows/publish.yml
```

Prüfen: Löst der Workflow auf `release: published` oder auf Tag-Push aus? Bei `release: published` bleibt das Erstellen des GitHub-Releases ein menschlicher Schritt — das ist zulässig und oft gewollt, muss aber im Release-Prozess dokumentiert sein, sonst bleibt es liegen.

## Pass Criteria

Zwei Achsen, beide müssen bestehen. Sie sind unabhängig — ein Pass auf der einen sagt nichts über die andere.

### Achse 1 — Gesundheit des Artefakts (nicht altersabhängig)

- [ ] Das auf dem Index liegende Artefakt **installiert** in eine frische Umgebung
- [ ] Es **importiert und startet**: der Entry Point kommt hoch und beantwortet ein `initialize`
- [ ] Ein echter `tools/call` liefert eine Antwort, die kein `isError` trägt und nicht leer ist
- [ ] Die veröffentlichte Version ist nicht zurückgezogen (`yanked`)

**Ein Verstoss hier ist ein sofortiger Befund auf `high`, unabhängig vom Alter der Lücke** — auch bei null unveröffentlichten Commits, auch wenn Repo, Tag und Index dieselbe Nummer tragen. Die Frage ist nicht, wie lange etwas ansteht, sondern ob das, was Nutzende gerade herunterladen, funktioniert. Ein Artefakt, das seit einer Stunde tot ist, ist genauso tot wie eines, das es seit drei Wochen ist; der einzige Unterschied liegt darin, wie viele es schon getroffen hat.

Diese Achse braucht eine **Installation aus dem Index**, kein Metadaten-Vergleich kann sie ersetzen. Ist sie nicht gelaufen, ist der Check nicht bestanden, sondern ungeprüft (`todo`).

### Achse 2 — Abstand zwischen `main` und dem Artefakt

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
| Aus «Repo, Tag und Index tragen dieselbe Nummer» auf Gesundheit geschlossen | Der Vorfall oben in einem Satz. Drei gleiche Etiketten, ein totes Artefakt |
| `pip install` + `pip show` als Verifikation | Beweist, dass etwas ausgepackt wurde. Nicht, dass es importiert, und schon gar nicht, dass es startet |
| Ungedeckelte Dependency-Range (`>=x`, kein `<y`) | Das publizierte Artefakt ändert sich, ohne dass jemand es publiziert — beim nächsten Major der Abhängigkeit |
| Gesundheit nur beim Release geprüft, nie danach | Genau der Fall: `0.5.1` war am Publish-Tag in Ordnung und vier Tage später tot, ohne eigenes Zutun |
| Exit `127` der Probe als Pass verbucht | Ein Vergleich, der nicht stattfand, ist keine Bestätigung (`OPS-005`) |
| `TOOL_ERROR` ungeprüft als Artefakt-Defekt gemeldet | Ein Upstream, der nicht auf der Egress-Allow-List steht, scheitert identisch — erst die Allow-List prüfen |
| Aus dem Checkout statt aus dem Index installiert | Prüft den Branch, also genau das, was CI schon prüft — der blinde Fleck bleibt unberührt |

## Remediation

### Schritt 1: Zuerst das Artefakt, dann die Lücke

`shipped_probe.py --dist <dist> --target <repo>` laufen lassen — die volle Tiefe, nicht `--metadata-only`. Wenn das publizierte Artefakt nicht läuft, ist die Lücke eine Nebenfrage: Es gibt dann nichts «nachzuziehen», sondern etwas zu ersetzen, und zwar sofort.

Läuft es, ist die Frage nicht «sind wir vorne», sondern «wie lange schon, und was steckt drin» — `fix:` unveröffentlicht ist eine andere Tatsache als `docs:`.

### Schritt 2: Release nachziehen — und den Start beweisen, nicht die Installation

Version bumpen, CHANGELOG-Abschnitt aus `[Unreleased]` bilden, taggen, Release erstellen. Danach **aus dem Index verifizieren**, nicht aus dem Build-Log:

```bash
python -m venv /tmp/verify
/tmp/verify/bin/pip install --no-cache-dir "<dist>==<version>"

# 1. Importiert es? Das ist die Stelle, an der 0.5.1 starb.
/tmp/verify/bin/python -c "import <package>; print('import ok')"

# 2. Kommt der Entry Point hoch und beantwortet einen echten Handshake?
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"verify","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | /tmp/verify/bin/<entrypoint> | head -3
```

**`pip show` gehört hier nicht hin.** Es beweist, dass ein Verzeichnis mit Metadaten angelegt wurde — nicht, dass ein `import` durchläuft. Genau diese Unterscheidung *war* der Vorfall: `0.5.1` installierte sauber und starb erst beim Import.

Zwei Dinge, die den Handshake-Test kaputtmachen:

- **stdin zu früh schliessen.** Der Server fährt herunter, bevor netzgebundene Arbeit fertig ist, und man protokolliert einen Fehler, den es nicht gibt. Das Pipe oben hält stdin bis zum Ende offen; wer die Zeilen einzeln sendet, muss dasselbe tun.
- **Die eigene Umgebung mitbenutzen.** Ein venv, das die Abhängigkeiten des Checkouts sieht, beantwortet die Frage nicht — es installiert nicht, was Nutzende installieren. Frisches venv, `--no-cache-dir`, Version explizit gepinnt.

Ein grüner Publish-Job ist ein Zwischenschritt, keine Bestätigung. Ein grünes CI erst recht nicht: Es testet den Branch, nie das Artefakt.

### Schritt 2b: Die Ursache schliessen, nicht nur das Symptom

War der Auslöser eine ungedeckelte Dependency-Range, ist das Nachziehen des Releases die halbe Arbeit. Ohne Obergrenze wiederholt sich derselbe Vorfall beim nächsten Major der Abhängigkeit, wieder ohne Zutun:

```diff
- "mcp[cli]>=1.28.1"
+ "mcp[cli]>=2.0.0,<3"
```

Ein Lockfile im Repo schützt hier **nicht**: Es gilt für die Entwicklungsumgebung, nicht für die Auflösung beim `pip install` der Nutzenden.

### Schritt 3: Die Gesundheit wiederkehrend prüfen, nicht nur beim Release

Der Vorfall entstand **nach** einem korrekten Release: `0.5.1` war am Publish-Tag in Ordnung und vier Tage später tot, weil sich eine Abhängigkeit bewegt hatte. Eine Prüfung, die nur beim Publish läuft, kann diese Klasse prinzipiell nicht sehen. `shipped_probe.py` gehört deshalb in einen wiederkehrenden Lauf — der `mcp-continuous-auditor` fährt ihn nächtlich; ein `schedule`-Workflow im eigenen Repo tut es auch.

### Schritt 4: Die Lücke klein halten

Kein neuer Mechanismus nötig — nur die Reihenfolge umdrehen: Ein Fix, der einen gemeldeten Bug schliesst, wird nicht «beim nächsten Feature» ausgeliefert, sondern zieht sein eigenes Patch-Release. Bei Servern mit seltener Kadenz gehört das explizit ins CONTRIBUTING.

## Effort

S — Messung Minuten (die Probe installiert und startet einmal), Nachziehen eines Releases unter einer Stunde. Dazu einmalig der wiederkehrende Lauf aus Schritt 3 und, falls die Ursache eine offene Range war, die Obergrenze aus Schritt 2b. Der Aufwand liegt in der Disziplin, nicht in der Technik.

## References

- Portfolio-Fundstück `meteoswiss-mcp#31` — `uvx` crasht, Fix lag seit drei Tagen auf `main`
- Portfolio-Fundstück [`zurich-opendata-mcp` `0.6.0`](https://github.com/malkreide/zurich-opendata-mcp/blob/main/CHANGELOG.md) — «Release this because 0.5.1 on PyPI is unusable»: Repo, Tag und Index einig, Artefakt tot. Der Beleg für die Gesundheits-Achse
- `IDENT-002` — `__version__` aus der installierten Distribution (Korrektheit statt Aktualität)
- `IDENT-003` — Werte, die die Pipeline überschreibt
- `OPS-005` — übersprungen ist nicht bestanden; Exit `127` der Probe folgt dieser Regel
- `mcp-continuous-auditor` → `scripts/shipped_probe.py` (Modus 1 und 2). `scripts/release_gap.py` ist nur noch ein Kompatibilitäts-Shim darüber und zur Löschung vorgesehen — nicht für neue Audits verwenden
