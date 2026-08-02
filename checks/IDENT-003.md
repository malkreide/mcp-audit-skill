---
id: IDENT-003
title: "Werte, die die Pipeline überschreibt, brauchen einen eigenen Check"
category: IDENT
severity: medium
applies_when: 'always'
pdf_ref: "Custom (Portfolio-Sweep 2026-07-29, 30 Server)"
evidence_required: 2
---

# IDENT-003 — Pipeline-überschriebene Werte prüfen

## Description

`server.json` ist das Manifest für die MCP Registry. Beim Veröffentlichen synchronisiert `publish.yml` die Version daraus **aus dem Tag-Namen** — die committete Fassung erreicht das publizierte Artefakt also nie.

Genau deshalb kann sie beliebig lange falsch sein. Bei `swiss-environment-mcp` stand sie von v0.2.3 bis v0.5.0 auf einer veralteten Nummer: funktional folgenlos, denn in der Registry landete jedes Mal korrekt die Tag-Version. Aufgefallen ist es niemandem, weil nichts brach.

Der Sweep fand vier Server mit dieser Abweichung (`news-monitor`, `swiss-courts`, `swiss-cultural-heritage`, `swiss-statistics` — letzterer 0.3.0 bei Paketversion 0.6.0).

**Der verallgemeinerbare Kern — und der eigentliche Grund für diesen Check:**

> Ein Wert, den die Pipeline zur Laufzeit überschreibt, wird nie geprüft. Er kann beliebig lange falsch sein, ohne dass etwas bricht.

Das gilt über `server.json` hinaus: überall dort, wo CI/CD einen committeten Wert ersetzt (Image-Tags, Chart-Versionen, generierte Manifeste, `.env.example`-Defaults), fehlt der Rückkanal. Der committete Wert wirkt dann nur noch auf **Menschen**, die ihn lesen — und führt sie in die Irre, ohne dass eine Maschine widerspricht.

## Verification

### Modus 1: code_review

```bash
# Alle Versionsfelder im Manifest gegen pyproject.toml
python - <<'EOF'
import json, tomllib
py = tomllib.load(open("pyproject.toml","rb"))["project"]["version"]
d = json.load(open("server.json"))
vals = [("version", d.get("version"))] + [
    (f"packages[{i}].version", p.get("version")) for i, p in enumerate(d.get("packages", []))
]
for where, v in vals:
    print(("OK  " if v == py else "!!  ") + f"{where} = {v!r} (pyproject {py!r})")
EOF
```

Beide Ebenen prüfen: das Server-Objekt **und** jeden Package-Eintrag. Ein Bump nur an einer der beiden Stellen bleibt sonst unentdeckt — im Sweep der ursprüngliche Auslöser für den Check.

### Modus 2: Inventar der überschriebenen Werte

Über das Manifest hinaus: Welche Werte ersetzt die Pipeline?

```bash
grep -rn "sed -i\|jq '\.\|yq -i\|::set-output\|GITHUB_REF_NAME" .github/workflows/
```

Jeder Treffer bezeichnet einen Wert, der im Repo steht, aber im Artefakt anders lautet. Für jeden davon gilt die Frage: Prüft irgendetwas die committete Fassung?

### Modus 3: runtime_test — das Ergebnis der Überschreibung zurücklesen

Die Modi 1 und 2 prüfen die **Eingangsseite**: den committeten Wert und die Stelle, an der die Pipeline ihn ersetzt. Was dabei herauskommt, kommt in beiden nicht vor — und damit trifft die These dieses Checks ihn selbst:

> Ein Wert, den die Pipeline zur Laufzeit überschreibt, wird nie geprüft.

Der committete Wert ist geprüft. Der geschriebene nicht. Zwei Wege, das zu schliessen:

**a) Die beiden publizierten Seiten gegeneinander.** Registry-Manifest und Paket-Index tragen dieselbe Version, weil dieselbe Pipeline sie aus demselben Tag ableitet. Weichen sie ab, hat genau ein Schritt nicht gegriffen. Die Index-Seite liefert `shipped_probe.py` (siehe `IDENT-006`), die Registry-Seite die Oberfläche, unter der der Server dort geführt wird.

**b) Die Transformation selbst nachvollziehen.** Das `jq`/`sed`-Kommando aus dem Workflow lokal gegen einen Tag-Namen laufen lassen und das Ergebnis ansehen — nicht den Workflow lesen, sondern ausführen. Hier zeigt sich, ob es **jedes** Vorkommen erfasst:

```bash
# Die Transformation aus publish.yml, mit einem Tag durchgespielt
VERSION=1.2.3
jq --arg v "$VERSION" '.version = $v | .packages[0].version = $v' server.json |
  python3 -c "
import json,sys,os
d=json.load(sys.stdin); v=os.environ['VERSION']
bad=[('version',d.get('version'))]+[(f'packages[{i}]',p.get('version')) for i,p in enumerate(d.get('packages',[]))]
for w,x in bad: print(('OK  ' if x==v else '!!  ')+f'{w} = {x!r} (erwartet {v!r})')"
```

**Das ist keine erfundene Sorge.** Genau diese Zeile steht so in den Publish-Workflows des Portfolios — sie schreibt `.version` und `.packages[0].version`, also **nur den ersten** Package-Eintrag. Kriterium 2 dieses Checks verlangt für die committete Fassung ausdrücklich «**jeder** `packages[*]`». Die Pipeline, die diese Fassung ersetzt, erfüllt das nicht. Bei einem Server mit zwei Einträgen wäre der zweite im *publizierten* Manifest desynchronisiert — und kein Kriterium dieses Checks hätte es je gesehen, weil alle nur die Datei im Repo ansehen. Solange ein Server genau einen Eintrag führt, ist es folgenlos; das ist ein Zustand, keine Eigenschaft.

Ist die publizierte Seite nicht erreichbar, ist das Ergebnis `todo`, nicht `pass` — ein Vergleich, der nicht stattgefunden hat, ist keine Bestätigung (`OPS-005`).

## Pass Criteria

- [ ] `server.json → version` stimmt mit `pyproject.toml` überein
- [ ] **Jeder** `packages[*].version` stimmt überein, nicht nur der erste
- [ ] Ein CI-Check erzwingt das, nicht nur eine Konvention
- [ ] Der Check läuft ohne Projekt-Installation (schlanker Lint-Job genügt)
- [ ] Die Werte, die `publish.yml` zur Laufzeit überschreibt, sind dokumentiert
- [ ] Für jeden überschriebenen Wert existiert ein Check auf die committete Fassung
- [ ] **Und einer auf die geschriebene**: Der publizierte Wert wurde zurückgelesen — Registry gegen Index, oder die Transformation nachvollzogen (Modus 3)
- [ ] Die Transformation erfasst **jedes** Vorkommen des Wertes, nicht nur das erste (`packages[0]` ist kein `packages[*]`)
- [ ] Die Ableitung des Wertes ist gegen Nicht-Tag-Läufe abgesichert: Bei `workflow_dispatch` aus einem Branch ist `GITHUB_REF_NAME` der Branch-Name, und ein blindes `${VAR#v}` schreibt `main` als Version

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| «Wird beim Publish eh gesetzt» als Begründung fürs Nichtpflegen | Committete Datei führt Lesende in die Irre |
| Nur `version` geprüft, `packages[*].version` nicht | Halber Bump bleibt unentdeckt |
| Check erst im Test-Job mit voller Installation | Läuft nicht im schlanken Lint-Job, wird umgangen |
| Abbruch beim ersten Befund | Weitere, schwerere Abweichungen bleiben ungesehen (siehe IDENT-004) |
| Nur die committete Fassung geprüft | Die These des Checks, auf ihn selbst angewandt: der geschriebene Wert wird nie geprüft |
| Transformation greift auf `packages[0]` statt `packages[*]` | Im publizierten Manifest desynchron, sobald es mehr als einen Eintrag gibt — im Repo unsichtbar |
| Version aus `GITHUB_REF_NAME` ohne Tag-Prüfung abgeleitet | Ein `workflow_dispatch` aus `main` publiziert die Version `main` |
| Workflow gelesen statt ausgeführt | `jq`-Ausdrücke sind still bei Pfaden, die nicht existieren — der Fehler steht nicht im Text, sondern im Ergebnis |

## Remediation

`scripts/check_version_sync.py`, reine Standardbibliothek, im `lint`-Job:

```python
found = [("server.json → version", server.get("version", ""))]
for i, pkg in enumerate(server.get("packages", [])):
    found.append((f"server.json → packages[{i}].version", pkg.get("version", "")))

mismatches = [(w, v) for w, v in found if v != version]
if mismatches:
    ...
    sys.exit(1)
```

**Einbau als Schritt in einen bestehenden Job, nicht als eigener Job.** Ein neuer Job erzeugt einen neuen Check-Namen und kann mit Branch-Rulesets kollidieren, die bestimmte Namen als erforderlich führen — im Sweep bei einem Repo real aufgetreten.

Auf Python 3.10 gibt es `tomllib` noch nicht. Wo die Matrix dort beginnt, braucht der Check einen bedingten Import mit Minimal-Parser für die zwei benötigten Felder — sonst stürzt er ab, statt zu prüfen.

## Effort

S — 30 Minuten inklusive CI-Einbau. Das Inventar der überschriebenen Werte kann länger dauern.

## References

- Portfolio-Sweep 2026-07-29: 4 von 30 Servern betroffen
- `swiss-environment-mcp` v0.5.1 — Manifest stand von v0.2.3 bis v0.5.0 falsch
- IDENT-004 — dieselbe Klasse für dokumentierte Werte
- `IDENT-006` — die Index-Seite des Vergleichs aus Modus 3; `shipped_probe.py` liest die Version aus der installierten Distribution
- `OPS-005` — nicht erreichbare publizierte Seite heisst `todo`, nicht `pass`
- OPS-001 — CI-Gates
