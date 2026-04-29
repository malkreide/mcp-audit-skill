---
id: ARCH-010
title: "Idempotency-Keys und Compensating Actions statt Transaktionen"
category: ARCH
severity: critical
applies_when: 'write_capable == true'
pdf_ref: "Anhang A6"
evidence_required: 4
---

# ARCH-010 — Idempotency und Compensating Actions

## Description

MCP hat **kein 2-Phase-Commit**. Wenn ein schreibendes Tool nach erfolgreicher Datenmodifikation ein Network-Error wirft (Timeout, Verbindungsabbruch zwischen Server und LLM-Host), weiss der LLM nicht, ob die Operation durchging oder nicht. Der LLM probiert es erneut. Resultat: doppelte Rechnung, doppelter E-Mail-Versand, doppelter User-Account.

Die Lösung kommt aus dem Stripe/PayPal-Playbook und ist in MCP übertragen:

**1. Idempotency-Key als Pflichtparameter** bei jedem schreibenden Tool. Server speichert `(idempotency_key, result)` für 24h. Wiederholter Call mit gleichem Key → gleiches Resultat aus Cache, **keine** zweite Ausführung.

**2. Compensating Actions statt Transaktionen.** Pro Tool, das einen Side-Effect erzeugt, gibt es ein Gegenstück, das ihn rückgängig macht:

| Forward-Operation | Compensation |
|---|---|
| `create_invoice(...)` | `delete_invoice(invoice_id)` |
| `send_notification(...)` | `cancel_notification(notification_id)` falls noch nicht zugestellt |
| `update_record(id, new)` | Server speichert `old` und liefert `revert_record(id)` |
| `delete_record(id)` | `restore_record(id)` aus Soft-Delete-Storage |

Das ist `critical`, weil ohne Idempotency in Production garantiert Duplikat-Bugs auftreten — eine Frage von Wochen, nicht Jahren. Im Schulamt-Kontext: doppelte Eltern-Mailings, doppelte Klassenzuteilungen, falsche Statistik-Aggregate.

## Verification

### Modus 1: code_review (Idempotency-Key Pflichtparameter)

```bash
grep -rB 3 -A 10 '@mcp\.tool' src/ | grep -E "idempotency_key|idempotencyKey"
```

**Pass-Pattern:**

```python
from typing import Annotated
from pydantic import BaseModel, Field, StringConstraints

class CreateInvoiceArgs(BaseModel):
    model_config = {"strict": True, "extra": "forbid"}

    customer_id: Annotated[str, StringConstraints(pattern=r"^CUST-\d{6}$")]
    amount: Annotated[float, Field(gt=0)]
    description: str
    idempotency_key: Annotated[str, StringConstraints(min_length=8, max_length=64)]


@mcp.tool(annotations={"destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def create_invoice(args: CreateInvoiceArgs, ctx: Context) -> dict:
    # Cache-Lookup
    cached = await idempotency_store.get(args.idempotency_key)
    if cached:
        ctx.logger.info("idempotency_replay", key=args.idempotency_key)
        return cached  # Wiederholter Call gibt gleiches Resultat

    # Echte Operation
    invoice = await billing_api.create(
        customer_id=args.customer_id,
        amount=args.amount,
        description=args.description,
    )
    result = {"invoice_id": invoice.id, "status": invoice.status}

    # Cache für 24h
    await idempotency_store.set(args.idempotency_key, result, ttl=86400)
    return result
```

**Fail-Pattern:**

```python
# FAIL: Kein Idempotency-Key, jede Wiederholung erzeugt neue Rechnung
@mcp.tool()
async def create_invoice(customer_id: str, amount: float):
    return await billing_api.create(customer_id, amount)
```

### Modus 2: code_review (Compensating Actions vorhanden)

Pro schreibendem Tool muss ein Compensating-Tool existieren oder das Tool selbst muss Soft-Delete-Logik bieten.

```bash
# Suche schreibende Tools
grep -rB 3 'destructiveHint.*True\|destructiveHint:\s*true' src/

# Pro destruktiv markiertem Tool: gibt es ein Gegenstück?
grep -rE 'def (revert|restore|undo|cancel)_' src/
```

**Pass-Pattern:**

```python
@mcp.tool(annotations={"destructiveHint": True, "idempotentHint": True})
async def update_user_email(args: UpdateEmailArgs, ctx: Context) -> dict:
    # Alte Werte vor dem Update sichern
    user = await db.get_user(args.user_id)
    revert_token = await revert_store.save({
        "user_id": args.user_id,
        "previous_email": user.email,
        "previous_modified_at": user.modified_at,
    }, ttl=86400 * 7)  # 7 Tage Revert-Fenster

    await db.update_user(args.user_id, email=args.new_email)
    return {"status": "updated", "revert_token": revert_token}


@mcp.tool(annotations={"destructiveHint": False, "idempotentHint": True})
async def revert_user_email_change(revert_token: str, ctx: Context) -> dict:
    snapshot = await revert_store.get(revert_token)
    if not snapshot:
        return {"isError": True, "content": [TextContent(
            type="text", text="Revert-Token ist abgelaufen oder ungültig.",
        )]}
    await db.update_user(
        snapshot["user_id"],
        email=snapshot["previous_email"],
    )
    return {"status": "reverted"}
```

### Modus 3: code_review (Idempotency-Store TTL)

Der Store für Idempotency-Keys muss eine TTL haben (typisch 24h gemäss Stripe-Pattern). Zu kurz = Duplikate bei verzögerten Retries; zu lang = Memory-Exhaustion und potenzielles Replay alter Operationen mit verändertem Kontext.

```bash
grep -rE 'ttl|expire|TTL' src/ | grep -iE 'idempoten'
```

**Pass:** TTL ist explizit gesetzt, dokumentiert, zwischen 4h und 48h.

### Modus 4: runtime_test (Wiederholter Call mit gleichem Key)

```python
async def test_idempotent_invoice_creation():
    args = CreateInvoiceArgs(
        customer_id="CUST-123456",
        amount=100.0,
        description="Test",
        idempotency_key="test-key-001",
    )
    result_1 = await create_invoice(args, ctx=mock_ctx())
    result_2 = await create_invoice(args, ctx=mock_ctx())
    assert result_1 == result_2
    assert result_1["invoice_id"] == result_2["invoice_id"]
    # billing_api.create wurde nur einmal aufgerufen
    assert billing_api.create.call_count == 1
```

## Pass Criteria

- [ ] **Alle** schreibenden Tools haben `idempotency_key` als Pflichtparameter
- [ ] Idempotency-Store mit TTL zwischen 4h und 48h
- [ ] Replay-Schutz: wiederholter Call mit gleichem Key → gleiches Resultat aus Cache
- [ ] Pro destruktivem Tool: Compensating Action vorhanden (revert/restore/cancel)
- [ ] Bei Update-Operationen: alte Werte werden für Revert-Fenster gespeichert
- [ ] `idempotentHint: true` in Tool-Annotations gesetzt (Synergie zu ARCH-009)
- [ ] Tests verifizieren Idempotency mit doppeltem Call

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Kein Idempotency-Key | Duplikat-Bugs garantiert in Produktion |
| Idempotency-Key optional | LLM vergisst ihn → Duplikate |
| TTL zu kurz (< 1h) | Real-World-Retry nach kurzem Outage erzeugt Duplikate |
| TTL zu lang (> 7 Tage) | Replay einer alten Operation mit neuem Kontext, Memory-Bloat |
| Keine Compensating Actions | Bei Fehler keine Recovery, manuelle DB-Eingriffe nötig |
| Compensating-Action ist destruktiv ohne eigenen idempotency_key | Doppelter Revert möglich |

## Remediation

### Schritt 1: Idempotency-Store wählen

| Backend | Eignung | Aufwand |
|---|---|---|
| In-Memory dict | Demo / Single-Instance | Trivial, geht bei Restart verloren |
| Redis | Standard für Production | Niedrig, geteilt zwischen Instanzen |
| PostgreSQL Table | Bei vorhandener DB-Infra | Mittel |
| DynamoDB | Bei AWS-Stack | Niedrig |

```python
# Beispiel mit Redis
import aioredis
import json

class IdempotencyStore:
    def __init__(self, redis_url: str, default_ttl: int = 86400):
        self.redis = aioredis.from_url(redis_url)
        self.default_ttl = default_ttl

    async def get(self, key: str) -> dict | None:
        raw = await self.redis.get(f"idem:{key}")
        return json.loads(raw) if raw else None

    async def set(self, key: str, result: dict, ttl: int | None = None):
        await self.redis.setex(
            f"idem:{key}",
            ttl or self.default_ttl,
            json.dumps(result),
        )
```

### Schritt 2: Decorator für Idempotency

```python
def idempotent_tool(*args, **kwargs):
    """Decorator: extrahiert idempotency_key, prüft Cache, speichert Resultat."""
    def decorator(tool_func):
        @functools.wraps(tool_func)
        async def wrapper(args_obj, ctx):
            key = getattr(args_obj, "idempotency_key", None)
            if not key:
                return {"isError": True, "content": [TextContent(
                    type="text", text="idempotency_key is required",
                )]}
            cached = await idempotency_store.get(key)
            if cached:
                return cached
            result = await tool_func(args_obj, ctx)
            await idempotency_store.set(key, result)
            return result
        return wrapper
    return decorator
```

### Schritt 3: Compensating Actions implementieren

Pro Forward-Operation ein Reverse-Tool. Wichtig: das Reverse-Tool selbst muss idempotent sein.

### Schritt 4: Tests gegen Replay

Wie im Pass-Pattern Modus 4.

## Effort

L — 1–2 Wochen pro Server. Idempotency-Store + Decorator + Compensating Actions + Tests.

## References

- Anhang A6 — Idempotenz und Compensating Actions
- ARCH-009 — Tool Annotations (`idempotentHint` Synergie)
- HITL-005 — Destructive Confirmation (komplementär)
- [Stripe API: Idempotent Requests](https://stripe.com/docs/api/idempotent_requests)
- [Saga-Pattern für Compensating Transactions](https://microservices.io/patterns/data/saga.html)
