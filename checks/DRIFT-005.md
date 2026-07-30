---
id: DRIFT-005
title: "Live-Tests laufen geplant — «aus CI ausgeschlossen» ist kein Ort"
category: DRIFT
severity: medium
applies_when: 'tools_make_external_requests == true'
pdf_ref: "Custom (Portfolio-Fundstück meteoswiss-mcp#35, 2026-07-30)"
evidence_required: 2
---

# DRIFT-005 — Ausgeschlossene Tests verrotten

## Description

`OPS-001` verlangt Live-Tests, markiert mit `@pytest.mark.live` und via `pytest -m "not live"` aus CI ausgeschlossen. Das ist richtig: Ein PR darf nicht rot werden, weil eine fremde API gerade 503 liefert.

Der Ausschluss erzeugt allerdings die Blindheit, vor der `OPS-001` warnt. Ein Test, der nirgends läuft, ist Dokumentation, kein Schutz — und er verrottet leise, weil sein Scheitern niemandem auffällt. Genau diese Tests sind aber die einzigen, die eine falsche Grundannahme widerlegen können (`FID-002`, `DRIFT-004`); dass ausgerechnet sie nicht ausgeführt werden, ist die unangenehmste Lücke der Test-Strategie.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Beim ersten Ausführen der Live-Suite seit Monaten fielen **drei von sechs Tests** um. Sie waren nicht kürzlich kaputtgegangen — der Upstream-Endpoint war zwei Tage zuvor abgeschafft worden, und davor hatte die Suite ebenfalls niemand gestartet. Die Marke war korrekt gesetzt, die Doktrin befolgt, das Ergebnis trotzdem: niemand wusste, dass zwei Tools tot waren.

## Verification

### Modus 1: config_check

```bash
# Läuft irgendwo ein Job mit -m live oder --live?
grep -rn 'pytest' .github/workflows/*.yml | grep -v 'not live'

# Gibt es überhaupt einen zeitgesteuerten Workflow?
grep -rn -A2 '^\s*schedule:' .github/workflows/*.yml
```

**Pass-Pattern** (`.github/workflows/live-tests.yml`):

```yaml
on:
  schedule:
    - cron: "17 6 * * 1"    # wöchentlich, ungerade Minute gegen den Stampede
  workflow_dispatch:         # und von Hand auslösbar

jobs:
  live:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -m live -v
      - name: Issue bei Fehlschlag
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner, repo: context.repo.repo,
              title: `Live-Tests rot (${new Date().toISOString().slice(0,10)})`,
              body: 'Upstream-Vertrag geändert oder Quelle ausgefallen. Lauf: ' +
                    `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}` +
                    `/actions/runs/${context.runId}`,
              labels: ['upstream'],
            })
```

Der `if: failure()`-Schritt ist der eigentliche Punkt. Ein geplanter Lauf, dessen Ergebnis niemand sieht, ist nur eine teurere Variante von «läuft nicht»: Rote Cron-Jobs im Actions-Tab werden nach der zweiten Woche nicht mehr angeschaut.

**Akzeptabel** statt eines eigenen Workflows: Der Server wird von einem externen Auditor abgedeckt, der die Live-Suite gegen ihn fährt (`mcp-continuous-auditor`). Dann gehört der Verweis darauf ins README, sonst ist die Abdeckung nicht nachweisbar.

**Fail-Pattern:**

```yaml
# Der einzige Job. Live-Tests existieren, laufen aber nirgends.
- run: pytest tests/ -m "not live"
```

### Modus 2: documentation_check

```bash
grep -inE 'live.?test|@pytest.mark.live' README.md CONTRIBUTING.md docs/*.md
```

Dokumentiert sein muss, **wann** die Live-Suite läuft und **wer** ein rotes Ergebnis sieht. «Kann lokal ausgeführt werden» beantwortet beides nicht.

## Pass Criteria

- [ ] Die Live-Suite läuft zeitgesteuert (mindestens wöchentlich) oder ist nachweislich von einem externen Auditor abgedeckt
- [ ] Ein Fehlschlag erzeugt ein sichtbares Signal — Issue, Benachrichtigung oder Report; nicht nur einen roten Lauf im Actions-Tab
- [ ] `workflow_dispatch` ist gesetzt, damit die Suite nach einem Upstream-Hinweis sofort ausführbar ist
- [ ] Der PR-Lauf bleibt bei `-m "not live"` — dieser Check verlangt einen *zusätzlichen* Lauf, keinen Umbau
- [ ] README oder CONTRIBUTING nennt Kadenz und Verantwortliche

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Live-Tests nur markiert, nirgends ausgeführt | Verrotten unbemerkt; der Ausfall fällt erst einem Nutzer auf |
| Geplanter Lauf ohne Benachrichtigung | Rot im Actions-Tab wird nach zwei Wochen ignoriert |
| Live-Tests in den PR-Lauf aufgenommen | Fremde 503 machen fremde PRs rot; die Suite wird abgeschaltet |
| Tägliche Ausführung gegen eine fremde API | Unnötige Last, und die Kadenz rechtfertigt den Aufwand nicht |

## Remediation

### Schritt 1: Zweiten Workflow anlegen

Wöchentlich, `workflow_dispatch` dazu, `-m live`. Der PR-Lauf bleibt unverändert — dieser Check baut nichts um, er ergänzt.

### Schritt 2: Fehlschlag sichtbar machen

Issue mit stabilem Titel-Präfix und Label, damit Wiederholungen erkennbar bleiben. Wer Telegram oder Slack anbindet, kann sich das Issue sparen — sichtbar muss es sein, nicht formal.

### Schritt 3: Erwartung setzen

Ein roter Live-Lauf heisst nicht zwingend «unser Fehler». Er heisst «der Vertrag mit der Quelle hat sich geändert oder sie ist aus». Beides gehört gesehen; nur das Erste gehört gefixt. Das ins CONTRIBUTING schreiben, sonst wird der Job beim ersten transienten Rot deaktiviert.

## Effort

S — eine Stunde. Ein Workflow-File plus ein Absatz Doku.

## References

- Portfolio-Fundstück `meteoswiss-mcp#35` — drei von sechs Live-Tests rot beim ersten Ausführen seit Monaten
- `OPS-001` — Test-Strategie (die Marke, die dieser Check zur Ausführung bringt)
- `DRIFT-004` — Endpoint-Konstanten live verifizieren
- `FID-002` — Recall-Ground-Truth als Live-Canary
