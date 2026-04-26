---
id: ARCH-006
title: "Tool-Budget: High-Level-Use-Cases statt API-Mapping 1:1"
category: ARCH
severity: high
applies_when: 'always'
pdf_ref: "Sec 2.3"
evidence_required: 2
---

# ARCH-006 — Tool-Budget-Management

## Description

Jedes Tool, das ein MCP-Server exponiert, kostet Context-Window-Tokens beim Client. Ein Server mit 50 fein granulierten Tools (`getUserById`, `getUserByEmail`, `listUserOrders`, `getOrderItems`, `getOrderShipping`, `getShippingTracking`, …) lädt das LLM mit ~8'000–15'000 Token Tool-Manifest, bevor überhaupt eine User-Frage bearbeitet wird. Bei Modellen mit 200K-Context wirkt das harmlos, ist aber:

1. **Teuer:** Tool-Manifest fliesst in jeden Inference-Call ein. Bei vielen Konversationsturns kumuliert das.
2. **Fehleranfällig:** Je mehr ähnliche Tools, desto öfter wählt das LLM das falsche.
3. **Verkettungs-Overhead:** Der LLM muss 4 Tools sequentiell aufrufen, um eine User-Frage zu beantworten — pro Tool entstehen Latenz, Token, Halluzinationsrisiko.

Der Best-Practice-Ansatz: **Use-Case-getriebene Aggregation.** Statt 4 Tools für «User-Order-Information» exposen → ein Tool `fetchUserOrderHistory(user_id)` baut die 4 Calls intern in der Server-Logik zusammen.

## Verification

### Modus 1: automated (Tool-Anzahl)

```bash
# Anzahl exponierter Tools im Server
grep -rE "@mcp\.tool|registerTool\(" src/ | wc -l
```

**Schwellenwerte (heuristisch):**
- ≤ 8 Tools: in der Regel ok
- 9–15 Tools: Use-Case-Cluster prüfen
- 16–25 Tools: ernste Zweifel, ob alle nötig sind
- > 25 Tools: fast sicher API-Mapping-Anti-Pattern

### Modus 2: code_review (1:1 API-Mapping erkennen)

Indikatoren für problematisches API-Mapping:

```bash
# Tool-Namen-Pattern: getX, listX, fetchX, getXByY mit ähnlichem Domain
grep -rE "@mcp\.tool" src/ -A2 | grep -E "name=" | sort
```

**Anti-Pattern (Tool-Inflation durch CRUD-Mapping):**

```python
@mcp.tool()
async def get_user(user_id: str): ...

@mcp.tool()
async def list_user_orders(user_id: str): ...

@mcp.tool()
async def get_order(order_id: str): ...

@mcp.tool()
async def list_order_items(order_id: str): ...

@mcp.tool()
async def get_item_details(item_id: str): ...
# Total: 5 Tools für eine plausible User-Frage
```

**Pass-Pattern (Use-Case-Aggregation):**

```python
@mcp.tool(
    name="fetchUserOrderHistory",
    description=(
        "Liefert die komplette Bestell-Historie eines Users inkl. Items, "
        "Versand-Status und Tracking. Aggregiert intern mehrere API-Calls."
    ),
)
async def fetch_user_order_history(
    user_id: str,
    include_archived: bool = False,
    ctx: Context = None,
) -> dict:
    user = await api.get_user(user_id)
    orders = await api.list_orders(user_id, include_archived=include_archived)
    # Parallel item details laden
    item_tasks = [api.list_order_items(o["id"]) for o in orders]
    items = await asyncio.gather(*item_tasks)
    for order, order_items in zip(orders, items):
        order["items"] = order_items
        if order["status"] == "shipped":
            order["tracking"] = await api.get_shipping(order["id"])
    return {
        "user": user,
        "orders": orders,
        "total_orders": len(orders),
    }
```

### Modus 3: code_review (Realistic User-Story Decomposition)

Pro Server eine konkrete User-Story formulieren und prüfen, wie viele Tool-Calls nötig sind:

| User-Story | Tool-Calls (gut) | Tool-Calls (Anti-Pattern) |
|---|---|---|
| «Zeige mir, was User X bestellt hat» | 1 (`fetchUserOrderHistory`) | 4–6 |
| «Welche Vorstösse zu KI hat Politiker Y eingereicht?» | 1 (`getMotionsByPolitician`) | 3–5 |
| «Wie ist die aktuelle Grippelage in Zürich?» | 1 (`getCurrentEpidemiologyZH`) | 4–8 |

**Pass:** Anchor Demo Query (siehe `mcp-data-source-probe`-Skill) wird mit ≤ 2 Tool-Calls beantwortbar.

## Pass Criteria

- [ ] Tool-Anzahl ist begründet (idealerweise ≤ 12 Tools)
- [ ] Keine offensichtlichen 1:1-API-Mappings (z.B. ein Tool pro REST-Endpoint)
- [ ] Anchor Demo Query des Servers ist mit 1–2 Tool-Calls beantwortbar
- [ ] Wo Aggregation stattfindet: Performance ist akzeptabel (< 5s typischerweise)
- [ ] Bei vielen Tools: dokumentierte Begründung im README warum keine Aggregation möglich

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Ein Tool pro REST-Endpoint | Token-Explosion + Verkettungs-Halluzinationen |
| `getX`, `getXById`, `getXByName` als drei Tools | LLM rät welches richtig ist |
| CRUD-Mapping (Create/Read/Update/Delete je einzeln) | Bricht oft Atomarität von Workflows |
| Aggregation ohne Parallelisierung | Sequentielle Calls = langsam |

## Remediation

### Schritt 1: User-Stories sammeln

Top-5-User-Fragen pro Server identifizieren (aus Logs, Demos, Stakeholder-Interviews).

### Schritt 2: Pro Story die nötigen API-Calls auflisten

```
Story: "Zeige mir die KI-Vorstösse von Hans Müller in den letzten 12 Monaten"
Calls:
  1. searchPoliticians("Hans Müller") → IDs
  2. listMotionsByPolitician(id, from="2025-04") → Motion-IDs
  3. getMotionDetails(motion_id) für jede Motion
  4. getMotionTags(motion_id) für Filter "KI"
```

### Schritt 3: Aggregations-Tool entwerfen

```python
@mcp.tool(name="getMotionsByPoliticianAndTopic")
async def get_motions_by_politician_and_topic(
    politician_name: str,
    topic_keywords: list[str],
    from_date: str | None = None,
    ctx: Context = None,
) -> dict:
    politicians = await api.search_politicians(politician_name)
    if not politicians:
        return {"results": [], "match_type": "none", ...}  # siehe ARCH-003
    politician = politicians[0]
    motions = await api.list_motions_by_politician(
        politician["id"], from_date=from_date
    )
    detail_tasks = [api.get_motion_details(m["id"]) for m in motions]
    details = await asyncio.gather(*detail_tasks)
    matched = [
        d for d in details
        if any(kw.lower() in (d["title"] + d["text"]).lower() for kw in topic_keywords)
    ]
    return {
        "politician": politician,
        "motions": matched,
        "total": len(matched),
    }
```

### Schritt 4: Alte fein-granulare Tools deprecaten

Bei publiziertem Server: alte Tools 1 Release-Zyklus mit `deprecated=True`-Annotation behalten, dann entfernen.

## Effort

M — 1–3 Tage Refactoring + Tests + ggf. Doku-Update.

## References

- PDF Sec 2.3 — Tool-Budget
- [Anthropic: Effective tool use](https://www.anthropic.com/engineering/building-effective-agents)
