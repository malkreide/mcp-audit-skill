---
id: IDENT-007
title: "Das veröffentlichte Artefakt startet in einer leeren Umgebung"
category: IDENT
severity: high
applies_when: 'always'
pdf_ref: "Custom (Portfolio-Fundstücke zurich-opendata-mcp 0.5.1, 2026-07-31; swiss-energy-mcp, 2026-08-01)"
evidence_required: 2
---

# IDENT-007 — Was auf dem Index liegt, läuft

## Description

Alles, was ein Repository über sich weiss, weiss es über sich selbst. Die Tests laufen gegen den Checkout, die Linter gegen den Checkout, das Audit liest den Checkout. Was Nutzende bekommen, ist etwas anderes: ein Artefakt vom Index, aufgelöst gegen die Paketwelt von **heute**, in einer Umgebung, die nichts enthält.

Dieser Check stellt genau eine Frage, und er stellt sie am Artefakt: **Installiert es, importiert es, startet es, antwortet es?**

### Abgrenzung zu `IDENT-006`

`IDENT-006` misst den Abstand zwischen `main` und dem Index — ob jemand vergessen hat zu publizieren. Das ist ein Vergleich von Etiketten und eine berechtigte Frage. Es ist aber nicht diese.

**Der Fall** (`swiss-energy-mcp`): Die Versionsnummern stimmten überein — Repo, Tag und Index einig, keine unveröffentlichten Commits. Der Gap-Check war zufrieden, und zwar zu Recht: Es *gab* keine Lücke. Die Installation war trotzdem tot.

Derselbe Ausgang, vier Wochen früher und vollständig protokolliert, bei `zurich-opendata-mcp` `0.5.1` (2026-07-31):

```
$ uv run --with 'zurich-opendata-mcp==0.5.1' python -c "import zurich_opendata_mcp.app"
installed zurich-opendata-mcp: 0.5.1
installed mcp               : 2.0.0
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

Gebrochen hatte in beiden Fällen nichts im Repository. Die Distribution trug `mcp[cli]>=1.28.1` **ohne Obergrenze**; am 2026-07-28 erschien `mcp` 2.0.0 und entfernte `mcp.server.fastmcp` ersatzlos. Von da an löste jede frische Installation eine Major-Version auf, gegen die der Code nicht lief. **Das publizierte Artefakt änderte sich, ohne dass jemand es publizierte.** Die Ursache dieser Klasse trägt `DEP-001`; hier steht die Prüfung, die sie sichtbar macht.

Zwei Konsequenzen, die diesen Check tragen:

1. **Der Befund hängt nicht am Alter.** Ein Artefakt, das *jetzt* nicht startet, ist ein sofortiger Befund — auch bei null unveröffentlichten Commits, auch wenn Repo, Tag und Index dieselbe Nummer tragen. Die Frage ist nicht, wie lange etwas ansteht, sondern ob das, was Nutzende gerade herunterladen, funktioniert. Ein Artefakt, das seit einer Stunde tot ist, ist genauso tot wie eines, das es seit drei Wochen ist; der einzige Unterschied liegt darin, wie viele es schon getroffen hat.
2. **Kein Metadaten-Vergleich kann diese Achse ersetzen.** Die einzige Aussage darüber, ob etwas läuft, entsteht daraus, dass man es installiert und startet.

### Warum «leer» und nicht nur «frisch»

Die Umgebung ist der halbe Check. Drei Umgebungen, die alle plausibel aussehen und die Frage **nicht** beantworten:

| Umgebung | Warum sie nicht zählt |
|---|---|
| Der Checkout mit `pip install -e .` | Prüft den Branch — also genau das, was CI schon prüft. Der blinde Fleck bleibt unberührt |
| Ein venv mit dem Lockfile des Repos | Löst auf, was die Entwicklerin auflöste, nicht was heute aufgelöst wird. Genau die Verschiebung, die den Vorfall ausmachte, ist damit weggepinnt |
| Die eigene Arbeitsumgebung mit `--user`, Cache, vorhandenen Paketen | Ein bereits installiertes `mcp<2` beantwortet die Frage für niemanden ausser die Prüferin selbst |

Leer heisst: neues venv, `--no-cache-dir`, kein Constraint aus dem Repo, Version explizit vom Index. Was der Resolver dann wählt, ist das, was Nutzende heute bekommen — und mehr will dieser Check nicht wissen.

## Verification

### Modus 1: automated — `shipped_probe.py` (der primäre Modus)

`scripts/shipped_probe.py` aus dem [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) installiert die Distribution **aus dem Index in ein frisches venv** — nie aus dem Checkout —, startet den installierten Entry Point und spricht ein echtes `initialize` plus einen echten `tools/call` mit ihm.

```bash
python scripts/shipped_probe.py --dist <dist> --target <repo> --format json
```

Ohne `--metadata-only`: Das Flag schaltet auf die Lücken-Achse zurück und ist `IDENT-006`.

| Exit | Bedeutung | Status für `IDENT-007` |
|---|---|---|
| `0` | Artefakt installiert, importiert, startet und antwortet | pass |
| `2` | Befund — der installierte Server kam nicht hoch oder antwortete nicht | `fail` |
| `127` | Die Harness lief nicht (kein Netz zum Index, venv-Erstellung scheiterte) | `todo` |

Exit `127` ist ausdrücklich **kein** Pass (`OPS-005`). Für diesen Check gilt das schärfer als für die meisten: Er ist der einzige, der die Frage überhaupt stellt, und ein stiller Ausfall der Harness sieht in jeder Zusammenfassung aus wie ein gesundes Paket.

Die Befundcodes dieser Achse: `INSTALL_FAILED`, `NO_ENTRYPOINT`, `DOES_NOT_RUN`, `TOOL_NO_ANSWER`, `TOOL_ERROR`, `TOOL_EMPTY`, `RELEASE_YANKED`. Die Lücken-Codes (`NOT_ON_INDEX`, `STALE_ON_INDEX` …) gehören zu `IDENT-006`.

**`TOOL_ERROR` beweist nicht allein, dass das Artefakt kaputt ist.** Die Probe läuft in einer Umgebung mit Default-Deny-Egress; ein Tool, dessen Upstream nicht auf der Allow-List steht, scheitert genau gleich. Vor dem Finding die Allow-List prüfen — der Report sagt das in seinem eigenen Text.

Hat der Server gar keine publizierte Distribution, meldet die Probe `not_applicable`. Dann ist dieser Check gegenstandslos, und die Lücken-Frage (`IDENT-006`, `NOT_ON_INDEX`) ist die eigentliche.

> Die Exit-Codes sind **nicht** die von `published_probe.py` (dort heisst `2` «nicht installierbar», `1` ist der Befund). Wer beide in einem Skript aufruft, muss sie getrennt auswerten.

### Modus 2: runtime_test — von Hand, vier Schritte

Ohne die Harness, und in dieser Reihenfolge — jeder Schritt kann für sich scheitern:

```bash
# 0. Leere Umgebung
python -m venv /tmp/verify
/tmp/verify/bin/pip install --no-cache-dir "<dist>==<version>"

# 1. Importiert es? Das ist die Stelle, an der 0.5.1 starb.
/tmp/verify/bin/python -c "import <package>; print('import ok')"

# 2. Womit wurde tatsächlich aufgelöst? Gehört ins Protokoll, nicht nur ins Auge.
/tmp/verify/bin/pip freeze | grep -Ei '^(mcp|fastmcp|httpx)'

# 3. Kommt der Entry Point hoch und beantwortet er einen echten Handshake?
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"verify","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | /tmp/verify/bin/<entrypoint> | head -3

# 4. Und ein echter tools/call — ein Server kann listen, ohne zu liefern.
```

**`pip show` gehört hier nicht hin.** Es beweist, dass ein Verzeichnis mit Metadaten angelegt wurde — nicht, dass ein `import` durchläuft. Genau diese Unterscheidung *war* der Vorfall: `0.5.1` installierte sauber und starb erst beim Import.

Zwei Dinge, die den Handshake-Test kaputtmachen:

- **stdin zu früh schliessen.** Der Server fährt herunter, bevor netzgebundene Arbeit fertig ist, und man protokolliert einen Fehler, den es nicht gibt. Das Pipe oben hält stdin bis zum Ende offen; wer die Zeilen einzeln sendet, muss dasselbe tun.
- **Die eigene Umgebung mitbenutzen.** Siehe die Tabelle oben: Ein venv, das die Abhängigkeiten des Checkouts sieht, beantwortet die Frage nicht.

### Modus 3: config_check — läuft die Prüfung wiederkehrend?

Der Vorfall entstand **nach** einem korrekten Release: Das Paket war am Publish-Tag in Ordnung und Tage später tot, weil sich eine Abhängigkeit bewegt hatte. Eine Prüfung, die nur beim Publish läuft, kann diese Klasse prinzipiell nicht sehen.

```bash
grep -l 'schedule:' .github/workflows/*.yml
```

Gesucht ist ein wiederkehrender Lauf, der das **publizierte** Paket installiert und startet — nicht die Testsuite gegen den Branch. Der `mcp-continuous-auditor` fährt `shipped_probe.py` nächtlich über das Portfolio; ein eigener `schedule`-Workflow im Repo tut es auch. Fehlt beides, ist die Antwort auf diesen Check ein Zeitpunkt, kein Zustand.

## Pass Criteria

- [ ] Das auf dem Index liegende Artefakt **installiert** in eine leere Umgebung (frisches venv, `--no-cache-dir`, kein Lockfile, kein Constraint aus dem Repo)
- [ ] Es **importiert**: das Top-Level-Paket lädt
- [ ] Der Entry Point **startet** und beantwortet ein `initialize`
- [ ] Ein echter `tools/call` liefert eine Antwort, die kein `isError` trägt und nicht leer ist
- [ ] Die veröffentlichte Version ist nicht zurückgezogen (`yanked`)
- [ ] Die tatsächlich aufgelösten Versionen der Kern-Abhängigkeiten sind **protokolliert** — sie sind die Evidenz, wenn dasselbe Paket morgen anders auflöst
- [ ] Ein `TOOL_ERROR` wurde gegen die Egress-Allow-List geprüft, bevor er als Artefakt-Defekt geführt wurde
- [ ] Ein wiederkehrender Lauf prüft dies erneut — nicht nur der Release-Tag (Modus 3)
- [ ] Die Prüfung hat **stattgefunden**: nicht gemessen ist `todo`, nicht Pass

Ein Verstoss ist ein sofortiger Befund auf `high`, unabhängig davon, wie alt der Zustand ist und ob `IDENT-006` grün war.

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Aus dem Checkout statt aus dem Index installiert | Prüft den Branch, also genau das, was CI schon prüft — der blinde Fleck bleibt unberührt |
| Mit dem Lockfile des Repos installiert | Pinnt genau die Verschiebung weg, die den Vorfall ausmacht |
| `pip install` + `pip show` als Verifikation | Beweist, dass etwas ausgepackt wurde. Nicht, dass es importiert, und schon gar nicht, dass es startet |
| Nur `import` geprüft, nie gestartet | Ein Server kann importieren und beim Aufbau des Tool-Registry sterben |
| Nur `tools/list` geprüft, nie ein `tools/call` | Listen kostet nichts. Der Vorfall in `meteoswiss-mcp` war drei Tools, die listeten und nichts lieferten |
| Aus «Repo, Tag und Index tragen dieselbe Nummer» auf Gesundheit geschlossen | `IDENT-006` war in beiden Fällen grün und in beiden Fällen wahr |
| Gesundheit nur beim Release geprüft, nie danach | Genau der Fall: am Publish-Tag in Ordnung, Tage später tot, ohne eigenes Zutun |
| `TOOL_ERROR` ungeprüft als Artefakt-Defekt gemeldet | Ein Upstream, der nicht auf der Egress-Allow-List steht, scheitert identisch |
| Exit `127` der Probe als Pass verbucht | Bei diesem Check besonders teuer: Er ist der einzige, der die Frage stellt (`OPS-005`) |
| Aufgelöste Abhängigkeitsversionen nicht protokolliert | Beim nächsten Lauf ist unbeweisbar, was sich bewegt hat |

## Remediation

### Schritt 1: Ersetzen, nicht nachziehen

Ein totes Artefakt auf dem Index ist keine Warteschlangenfrage. Ein Patch-Release, das den Import wieder herstellt, geht allen anderen Findings vor — es ist der einzige Zustand, den jede neue Nutzerin sofort trifft. Ist die Ursache nicht in Minuten zu beheben, ist `yank` der ehrlichere Zwischenschritt als ein Paket, das beim Import stirbt.

### Schritt 2: Die Ursache schliessen, nicht das Symptom

War der Auslöser eine ungedeckelte Dependency-Range, ist das Release die halbe Arbeit. Ohne Obergrenze wiederholt sich derselbe Vorfall beim nächsten Major der Abhängigkeit, wieder ohne Zutun:

```diff
- "mcp[cli]>=1.28.1"
+ "mcp[cli]>=2.0.0,<3"
```

Was gedeckelt gehört und was nicht, steht in `DEP-001`. Ein Lockfile im Repo schützt hier **nicht**: Es gilt für die Entwicklungsumgebung, nicht für die Auflösung beim `pip install` der Nutzenden.

### Schritt 3: Nach dem Release aus dem Index verifizieren

Die vier Schritte aus Modus 2, gegen die soeben publizierte Version. Ein grüner Publish-Job ist ein Zwischenschritt, keine Bestätigung; ein grünes CI erst recht nicht.

### Schritt 4: Wiederkehrend prüfen

Der Zustand kann sich ohne Commit ändern — deshalb ist eine einmalige Messung hier ein Datum, kein Ergebnis. `shipped_probe.py` in einen nächtlichen Lauf, oder ein `schedule`-Workflow, der die vier Schritte fährt.

## Effort

S — die Probe installiert und startet einmal, das sind Minuten. Ein Patch-Release unter einer Stunde. Der wiederkehrende Lauf ist einmalige Einrichtung; die Obergrenze aus Schritt 2 gehört zu `DEP-001`.

## References

- Portfolio-Fundstück `swiss-energy-mcp` — Versionsnummern einig, Gap-Check zufrieden, Installation tot. Der Fall, der diesen Check von `IDENT-006` getrennt hat
- Portfolio-Fundstück [`zurich-opendata-mcp` `0.6.0`](https://github.com/malkreide/zurich-opendata-mcp/blob/main/CHANGELOG.md) — «Release this because 0.5.1 on PyPI is unusable»: derselbe Ausgang, vollständig protokolliert
- Portfolio-Fundstück `meteoswiss-mcp#31` — drei Tools, die listeten und nichts lieferten; der Grund für den `tools/call` im Kriterium
- `IDENT-006` — der Abstand zwischen `main` und Index. Unabhängige Achse, kein Ersatz in beide Richtungen
- `DEP-001` — ungedeckelte Abhängigkeit: die häufigste Ursache dafür, dass dieser Check ohne Commit rot wird
- `OPS-005` — übersprungen ist nicht bestanden; Exit `127` folgt dieser Regel
- `mcp-continuous-auditor` → `scripts/shipped_probe.py` (Modus 1)
