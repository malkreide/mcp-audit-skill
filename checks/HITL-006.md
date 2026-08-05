---
id: HITL-006
title: "MRTR statt serverinitiierter Requests — input_required, Retry, Idempotenz"
category: HITL
severity: high
applies_when: 'always'
spec_baseline: 2026-07-28
adoption: advisory
pdf_ref: "SEP-2322"
spec_ref: "SEP-2322 (PR 2322) — Spec-Changelog 2026-07-28, Major #7 und #8"
evidence_required: 4
---

# HITL-006 — Multi Round-Trip Requests

## Description

Bis `2025-11-25` konnte ein Server mitten in der Bearbeitung eines Requests selbst einen Request an den Client stellen: `roots/list`, `sampling/createMessage`, `elicitation/create`. `2026-07-28` streicht dieses Muster ersatzlos und setzt **MRTR** an seine Stelle:

1. Der Server merkt, dass ihm etwas fehlt, und **antwortet** — mit `resultType: "input_required"` und einem Feld `inputRequests`, das benennt, was er braucht.
2. Der Client beschafft es und **wiederholt den ursprünglichen Request**, diesmal mit `inputResponses`.
3. Der Server bearbeitet ihn erneut, jetzt vollständig.

**Die Umkehrung, die alles daran schwierig macht:** Aus einem Dialog innerhalb einer Bearbeitung wird eine Bearbeitung, die **mehrfach von vorn läuft**. Was vor dem Rückfragepunkt passiert ist, passiert bei jedem Retry noch einmal.

Damit wandert dieser Check aus dem Bereich «Bedienoberfläche» in den Bereich «Korrektheit». Ein Tool, das erst eine Zahlung anlegt, dann nach einer Bestätigung fragt und im Retry wieder von vorn beginnt, legt zwei Zahlungen an. Auf der alten Baseline gab es dieses Problem nicht, weil die Rückfrage die Bearbeitung nicht beendete. Deshalb `evidence_required: 4` und `high`: Der teure Fehler ist nicht der falsch aufgebaute Dialog, sondern die **doppelte Nebenwirkung** — und die zeigt sich nur, wenn der Retry tatsächlich getestet wird.

**Korrelation ohne Sitzung.** Die Spec hat `notifications/elicitation/complete` und `elicitationId` entfernt (Minor #11). Ein Server, der einen ausserhalb laufenden Vorgang über Retries hinweg wiedererkennen muss, kodiert seine eigene Kennung in `requestState`. Es gibt keinen anderen Kanal mehr.

## Verification

### Modus 1: automated (alte Muster)

```bash
grep -rnE "sampling/createMessage|create_message|elicitation/create|elicit|roots/list|list_roots" \
    src/ --include="*.py" --include="*.ts"
```

Jeder Treffer ist auf dieser Baseline ein Befund — der Fluss existiert nicht mehr. Zusätzlich `ARCH-019` für die Deprecation-Seite.

### Modus 2: automated (neues Muster)

```bash
grep -rnE "input_required|inputRequests|inputResponses|requestState" \
    src/ --include="*.py" --include="*.ts"
```

### Modus 3: code_review (was vor dem Rückfragepunkt geschieht)

Je Tool, das `input_required` zurückgeben kann: Welche Nebenwirkungen liegen **vor** dem Punkt, an dem zurückgefragt wird? Jede davon läuft beim Retry erneut.

Drei zulässige Auflösungen, in dieser Reihenfolge zu bevorzugen:

1. **Rückfrage nach vorn ziehen** — vor jede Nebenwirkung. Der Retry läuft dann durch reinen Lesecode.
2. **Nebenwirkung idempotent machen** — über einen Idempotency-Key aus dem Request, siehe `ARCH-010`.
3. **Zwischenstand über `requestState` wiedererkennen** und die bereits erledigten Schritte überspringen.

Was nicht zählt: die Annahme, der Client wiederhole schon nicht.

### Modus 4: runtime_test (der Retry-Pfad wirklich)

Den Rückfragepfad auslösen, den Request mit `inputResponses` wiederholen und prüfen: Ergebnis korrekt **und** die Nebenwirkung genau einmal eingetreten. Bei Servern mit `write_capable: true` ist dieser Modus Pflicht — statische Analyse zeigt die Doppelung nicht.

## Pass Criteria

- [ ] Keine serverinitiierten `sampling/createMessage`, `elicitation/create`, `roots/list` mehr
- [ ] Fehlende Eingaben werden über `resultType: "input_required"` und `inputRequests` gemeldet
- [ ] `inputResponses` aus dem Retry werden validiert wie jede andere Eingabe (`SEC-018`) — sie kommen vom Client und sind nicht vertrauenswürdiger als ein Tool-Argument
- [ ] **Jede Nebenwirkung vor dem Rückfragepunkt ist idempotent, oder es gibt keine** — je Tool einzeln belegt
- [ ] Bei `write_capable: true`: Ein Test führt den vollen Retry-Zyklus aus und prüft, dass die Nebenwirkung **einmal** eintrat
- [ ] Ausserhalb laufende Vorgänge werden über eine selbst kodierte Kennung in `requestState` wiedererkannt, nicht über `elicitationId`
- [ ] `input_required` wird nicht für gewöhnliche Fehler verwendet — eine fehlende Berechtigung ist ein Fehler, keine Eingabeanforderung
- [ ] Ein Retry ohne die erwarteten `inputResponses` erzeugt einen klaren Fehler, keine Endlosschleife aus `input_required`
- [ ] **Gegenprobe:** Der Idempotenz-Test ist gegen eine Fassung ohne Schlüssel gelaufen und hat dort zwei Nebenwirkungen gesehen

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Nebenwirkung vor der Rückfrage, kein Idempotency-Key | Zwei Zahlungen, zwei Tickets, zwei Mails — je Retry eine mehr |
| `inputResponses` ungeprüft übernommen | Eingabekanal ohne Validierung; `SEC-018` |
| `input_required` als allgemeiner «unvollständig»-Zustand | Client sucht eine Eingabeaufforderung, die es nicht gibt |
| Retry ohne Antworten → wieder `input_required` | Endlosschleife zwischen Client und Server |
| Nur der glückliche Pfad getestet | Genau der Pfad, der die Doppelung erzeugt, ist ungeprüft |
| Bestätigung vor destruktiver Aktion über den alten Elicitation-Weg | `HITL-005` wird auf dieser Baseline unwirksam |

## Remediation

```python
@mcp.tool()
async def archive_dossier(dossier_id: str,
                          confirmation: str | None = None,
                          requestState: str | None = None) -> dict:
    """Archiviert ein Dossier. Verlangt eine ausdrückliche Bestätigung."""
    if confirmation != "ARCHIVIEREN":
        return {
            "resultType": "input_required",
            "inputRequests": [{
                "name": "confirmation",
                "prompt": f"Dossier {dossier_id} archivieren? Tippe ARCHIVIEREN.",
            }],
            # Eigene Korrelation — elicitationId gibt es nicht mehr
            "requestState": mint_request_state(dossier_id),
        }
    # Erst NACH der Bestätigung, und mit Schlüssel gegen den doppelten Retry
    await _impl.archive(dossier_id, idempotency_key=requestState or dossier_id)
    return complete({"archived": dossier_id})
```

```python
async def test_retry_archives_exactly_once(client, upstream):
    first = await client.call("archiveDossier", {"dossier_id": "D-42"})
    assert first["resultType"] == "input_required"
    await client.call("archiveDossier", {
        "dossier_id": "D-42", "confirmation": "ARCHIVIEREN",
        "requestState": first["requestState"],
    })
    assert upstream.archive_calls == 1        # nicht 2
```

## Effort

M für Read-only-Server: der Rückfragepunkt liegt vor allem Wesentlichen, der Retry ist folgenlos. L für schreibende Server — dort ist es keine Protokollumstellung, sondern eine Idempotenz-Überarbeitung jedes betroffenen Tools.

## References

- [Spec 2026-07-28 — Changelog, Major #7, #8, Minor #11](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2322](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2322)
- [MRTR pattern](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- `HITL-005` (destruktive Bestätigung), `ARCH-010` (Idempotency-Keys), `ARCH-018`, `SEC-018`
- `FID-003` — die Gegenrichtung derselben Grenze. Hier steht, dass `input_required` nicht für gewöhnliche **Fehler** benutzt werden darf; dort, dass es nicht mit dem **Null-Treffer** verschwimmen darf: kein `hint` auf einer Rückfrage, kein `inputRequests` auf einer Leermenge, und `entries` fehlt bei der Rückfrage statt leer zu sein
