---
id: HITL-002
title: "Sampling Response Review: Verifikation vor Server-Übergabe"
category: HITL
severity: high
applies_when: 'uses_sampling == true'
pdf_ref: "Sec 7.2"
evidence_required: 2
---

# HITL-002 — Sampling Response Review

## Description

HITL-001 deckt den Hin-Weg ab (Server → LLM): User sieht den Prompt vor dem Send. HITL-002 deckt den Rück-Weg ab (LLM → Server): User sieht die generierte Antwort, bevor sie an den Server zurückgeht und dort weiterverarbeitet wird.

Warum nötig: Wenn der Server die LLM-Antwort als Input für weitere Tool-Aufrufe verwendet, kann eine halluzinierte oder bösartig manipulierte Response eine Kette von Folgehandlungen auslösen. Beispiel: Server sampelt eine «Klassifikation» eines Dokuments; LLM klassifiziert irrtümlich als «Public»; Server publiziert basierend darauf das Dokument auf einer offenen Website.

Im MCP-Protokoll wird diese Review-Mechanik vom Client durchgesetzt. Server-Pflicht: Sampling-Calls so strukturieren, dass die Response nachvollziehbar ist, und vor allem: **Sampling-Output validieren**, bevor er weiterverwendet wird (Schema-Check, Sanity-Range, semantische Plausibilität).

## Verification

### Modus 1: code_review (Output-Validation nach Sampling)

```bash
# Suche nach Sampling-Calls und prüfe ob Output validiert wird
grep -rA10 'ctx\.sample\(' src/
```

**Pass-Pattern:**

```python
from pydantic import BaseModel, ValidationError

class ClassificationResult(BaseModel):
    classification: Literal["Public", "Internal", "Confidential", "Restricted"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

@mcp.tool()
async def classify_document(doc_id: str, ctx: Context) -> dict:
    doc = await api.get_document(doc_id)
    sample_result = await ctx.sample(
        messages=[{"role": "user", "content": f"Klassifiziere folgendes Dokument..."}],
        max_tokens=200,
    )

    # Validation: parsen und sicherstellen, dass nichts Unerwartetes drin ist
    try:
        parsed = ClassificationResult.model_validate_json(sample_result.content)
    except ValidationError as e:
        return {
            "isError": True,
            "content": [TextContent(
                type="text",
                text=f"Sampling-Output entsprach nicht dem erwarteten Schema."
            )],
        }

    if parsed.confidence < 0.7:
        # Niedrige Konfidenz: nicht weiterverarbeiten, User soll manuell prüfen
        return {
            "classification_draft": parsed.model_dump(),
            "requires_human_review": True,
        }

    # Hohe Konfidenz: weiterverarbeiten
    await api.tag_document(doc_id, parsed.classification)
    return {"classification": parsed.classification, "tagged": True}
```

**Fail-Pattern:**

```python
# FAIL: LLM-Output direkt als Input für destruktive Action
sample_result = await ctx.sample(...)
classification = sample_result.content.strip()  # roher String
await api.tag_document(doc_id, classification)  # ungeprüft!
# Wenn LLM "Public; DROP TABLE documents" antwortet, ist das ein Problem
```

### Modus 2: code_review (Confidence-Schwellen)

Bei Sampling-basierter Klassifikation oder Entscheidung sollte ein Confidence-Threshold definiert sein. Unter dem Threshold: Output an User zur manuellen Bestätigung weitergeben, nicht direkt weiterverarbeiten.

## Pass Criteria

- [ ] Sampling-Outputs werden mit Pydantic / Zod / JSON-Schema validiert (kein roher String-Use)
- [ ] Bei strukturierten Outputs: Schema mit `Literal` / Enum für erlaubte Werte
- [ ] Confidence-Threshold definiert für Entscheidungs-Sampling
- [ ] Bei niedriger Confidence: Output wird User-Review zugeleitet, nicht autonom verarbeitet
- [ ] Sampling-Outputs werden **nicht** ungeprüft als Input für destruktive Tools verwendet

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| LLM-Output direkt als SQL-Param | SQL-Injection durch Prompt-Injection im Sample |
| LLM-Output direkt in Shell-Command | RCE-Risiko |
| Kein Schema-Check | Halluzinierte Werte werden als gültig akzeptiert |
| Kein Confidence-Threshold | Unsichere Klassifikationen werden autonom umgesetzt |

## Remediation

Setup für robustes Sampling mit Output-Validation:

```python
from typing import Literal
from pydantic import BaseModel, Field, ValidationError

class SamplingOutput(BaseModel):
    """Pflicht-Schema für alle Sampling-Outputs in diesem Server."""
    decision: Literal["approve", "reject", "review_needed"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(max_length=500)

async def safe_sample(ctx: Context, prompt: str, schema: type[BaseModel]) -> BaseModel | None:
    """Wrapper: führt Sampling aus, validiert Output, gibt None bei Schema-Mismatch."""
    result = await ctx.sample(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )
    try:
        return schema.model_validate_json(result.content)
    except ValidationError:
        await ctx.warning("sampling_output_invalid", raw=result.content[:200])
        return None
```

## Effort

S — Pro Sampling-basiertem Tool 30–60 Minuten.

## References

- PDF Sec 7.2 — HITL Response Review
- [MCP Spec: Sampling](https://modelcontextprotocol.io/specification/draft/client/sampling)
