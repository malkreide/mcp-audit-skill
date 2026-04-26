---
id: HITL-001
title: "Sampling Request Review: User-UI vor LLM-Send"
category: HITL
severity: high
applies_when: 'uses_sampling == true'
pdf_ref: "Sec 7.2"
evidence_required: 2
---

# HITL-001 — Sampling Request Review

## Description

Das MCP-Sampling-Protokoll erlaubt einem Server, LLM-Inferenz über den Client anzufordern (umgekehrte Richtung des normalen Tool-Calls). Beispiel: ein Curia-Vista-Server findet 50 Motionen und bittet den LLM via Sampling, daraus eine Zusammenfassung zu erstellen — der Client (Claude Desktop) führt die LLM-Anfrage aus und leitet die Antwort zurück.

Das Risiko: der Server könnte Sampling missbrauchen, um manipulierte Prompts an das LLM zu schicken — Prompt-Injection, sensitive Datenextraktion, oder einfach Token-Missbrauch zu Lasten des Users.

Der Best-Practice-Standard verlangt: **Bevor** ein Sampling-Request an das LLM geht, sieht der User eine UI mit dem vollen Prompt-Inhalt und kann ihn modifizieren oder ablehnen. Diese Pflicht-Checkpoint-Mechanik wird im MCP-Protokoll vom Client durchgesetzt — der Server muss aber Prompts so strukturieren, dass diese Review menschlich nachvollziehbar ist (klar, kurz, ohne maschinengenerierten Lärm).

## Verification

### Modus 1: code_review (Sampling-Aufrufe)

```bash
# Suche nach ctx.sample()-Aufrufen
grep -rE 'ctx\.sample|sampleMessage|createMessage' src/
```

**Pass-Pattern:**

```python
@mcp.tool()
async def summarize_motions(motion_ids: list[str], ctx: Context) -> dict:
    motions = await api.fetch_motions(motion_ids)

    # Klar lesbarer Prompt — User in Sampling-UI kann ihn nachvollziehen
    prompt = (
        "Fasse die folgenden parlamentarischen Motionen in maximal 5 "
        "Bullet-Points zusammen. Fokus: Bildungs- und Datenschutz-Themen.\n\n"
        f"Motionen:\n"
        + "\n\n".join(f"- {m['title']}: {m['summary']}" for m in motions[:10])
    )

    result = await ctx.sample(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        system_prompt="Du bist ein Schulamts-Analyst. Antworte auf Deutsch.",
    )
    return {"summary": result.content, "source_count": len(motions)}
```

**Fail-Pattern:**

```python
# FAIL: Prompt enthält maschinengenerierten Lärm — User kann nicht prüfen
prompt = json.dumps(motions, indent=2) + "\n\nSummarize this."
# 50 KB JSON in Sampling-Review-Dialog ist nicht human-reviewable
```

### Modus 2: code_review (User-Friendly Prompt-Format)

Pro Sampling-Aufruf prüfen:

- Prompt ist auf Deutsch oder Englisch (Sprache der User-Audience)
- Prompt ist < 2000 Zeichen (sonst Review-UI-Bruch)
- System-Prompt ist explizit gesetzt (nicht implizit)
- Keine Embeds von Roh-API-Responses (z.B. JSON-Blobs)

## Pass Criteria

- [ ] Sampling-Aufrufe verwenden `ctx.sample()` (nicht direkte LLM-API-Calls am Client vorbei)
- [ ] Prompts sind in für User lesbarer Form (kurz, deutsch/englisch, formatiert)
- [ ] System-Prompts sind explizit gesetzt
- [ ] Kein Auto-Sampling ohne User-Trigger (z.B. nicht auf jeder Tool-Invocation)
- [ ] Bei Fehler im Sampling: Tool gibt klare Fehlermeldung zurück (User hat abgelehnt → Tool hat keinen Output)

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| JSON-Dump als Prompt-Body | User-Review unmöglich |
| Prompt > 5000 Zeichen | Review-UI bricht oder wird übersprungen |
| Sampling im Hintergrund ohne User-Bewusstsein | Token-Missbrauch, Sampling-Müdigkeit |
| Direkter LLM-API-Call statt MCP-Sampling | Server umgeht User-Review komplett |

## Remediation

```diff
  @mcp.tool()
  async def analyze(data_ids: list[str], ctx: Context):
      records = await api.fetch(data_ids)
-     prompt = json.dumps(records)  # 50 KB JSON
+     prompt = (
+         "Analysiere die folgenden Datensätze auf Mustern in Bildungsthemen.\n\n"
+         + "\n".join(f"- {r['title']} ({r['date']})" for r in records[:20])
+     )
      result = await ctx.sample(
          messages=[{"role": "user", "content": prompt}],
          max_tokens=500,
+         system_prompt="Du bist ein Schulamts-Analyst. Antworte strukturiert.",
      )
      return {"analysis": result.content}
```

## Effort

S — Pro Sampling-Aufruf 15–30 Minuten.

## References

- PDF Sec 7.2 — Sampling-Protokoll
- [MCP Spec: Sampling](https://modelcontextprotocol.io/specification/draft/client/sampling)
