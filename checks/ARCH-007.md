---
id: ARCH-007
title: "Capability-Aggregation: Composability intern, Atomarität extern"
category: ARCH
severity: medium
applies_when: 'always'
pdf_ref: "Sec 2.3"
evidence_required: 2
---

# ARCH-007 — Capability-Aggregation

## Description

Eng verwandt zu ARCH-006, aber mit anderem Fokus: **Wo ARCH-006 sagt «weniger Tools, höhere Use-Cases», sagt ARCH-007 «aus LLM-Sicht atomar, intern composable».**

Ein gut designtes Tool bietet dem LLM eine atomare, gedanklich abgeschlossene Operation. Wie der Server das intern realisiert (mehrere API-Calls, Caching, Parallelisierung, Retry-Logik) ist verkapselt. Das Tool exponiert Zweck und Resultat, nicht den Implementierungs-Pfad.

**Kontrast:**

| LLM-Sicht (Tool) | Server-interne Realisierung |
|---|---|
| `fetchUserOrderHistory(user_id)` | Atomar | 4 API-Calls, parallel, mit Retry |
| `analyseMotion(motion_id, depth="full")` | Atomar | 2 DB-Queries + 1 LLM-Sub-Call + Caching |
| `getCurrentEpidemiologyZH()` | Atomar | RSS-Feed + JSON-API + Statistik-Aggregation |

Der Wert: Das LLM muss kein Workflow-Engineering machen. Es ruft *ein* Tool, kriegt *ein* sinnvolles Resultat.

**Der Unterschied zu ARCH-006:**
- ARCH-006 fragt: «Hast du zu viele Tools?» (quantitativ)
- ARCH-007 fragt: «Sind die Tools, die du hast, in sich gut abgeschlossen?» (qualitativ)

Ein Server kann ARCH-006 erfüllen (nur 8 Tools) und trotzdem ARCH-007 verletzen (jedes der 8 Tools verlangt vom LLM weiteres Verkettungs-Wissen).

## Verification

### Modus 1: code_review (Aggregations-Pattern in Tool-Implementierung)

```bash
# Suche nach asyncio.gather in Tool-Handlern (Indikator für interne Aggregation)
grep -rB5 "asyncio\.gather\|Promise\.all" src/
# Suche nach Multi-Step-Logik
grep -rA20 "@mcp\.tool" src/ | grep -cE "await.*await|fetch.*fetch"
```

**Pass-Pattern:**

```python
@mcp.tool(name="getCurrentEpidemiologyZH")
async def get_current_epidemiology_zh(ctx: Context) -> dict:
    """LLM ruft *ein* Tool, kriegt vollständige aktuelle Lage."""
    # Intern: 3 verschiedene Quellen
    bag, kanton, stat = await asyncio.gather(
        api_bag.get_current_grippe(),
        api_kanton_zh.get_aktuelle_lage(),
        api_statistik.get_woche_aggregat(),
    )
    return {
        "summary": _summarise(bag, kanton, stat),
        "details": {
            "bag_meldungen": bag,
            "kanton_lage": kanton,
            "wochen_stats": stat,
        },
        "as_of": datetime.utcnow().isoformat(),
        "source": "BAG + Kanton ZH + StatistikAmt",
    }
```

**Fail-Pattern (zwingt LLM zu Verkettung):**

```python
@mcp.tool()
async def get_bag_grippe(): ...

@mcp.tool()
async def get_kanton_zh_lage(): ...

@mcp.tool()
async def get_woche_statistik(): ...
# LLM muss jetzt selbst orchestrieren, alle 3 zu kombinieren
```

### Modus 2: code_review (Resultat ist gedanklich abgeschlossen)

Pro Tool die Frage stellen: «Wenn das LLM nur dieses eine Tool aufrufen würde, hätte der User dann eine sinnvolle Antwort?»

**Pass:** Ja, das Tool-Result enthält alle nötigen Informationen für eine erste vollständige Antwort.

**Fail:** Das Tool-Result ist ein Zwischenergebnis, das ohne weitere Calls keine User-Frage beantwortet (z.B. `getMotionId(title)` retourniert nur eine ID, mit der das LLM dann `getMotionDetails(id)` aufrufen muss).

## Pass Criteria

- [ ] Tools liefern gedanklich abgeschlossene Resultate (nicht nur IDs/Pointer für Folge-Calls)
- [ ] Wo Aggregation Sinn ergibt: Tools nutzen `asyncio.gather` / `Promise.all` für Parallelisierung
- [ ] Tool-Beschreibungen erwähnen explizit den aggregierten Charakter (siehe ARCH-002)
- [ ] Der Anchor-Demo-Query des Servers ist mit ≤ 2 Tool-Calls beantwortbar (Synergie zu ARCH-006)

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| Tools liefern nur IDs, LLM muss in Folge-Call Details holen | Verkettungs-Halluzinationen, mehr Latenz |
| Aggregations-Tools intern sequentiell statt parallel | Tool wird langsam, schlechte UX |
| Aggregation ohne Provenance-Info (siehe Resilienz-Defaults) | LLM kann Quellen-Mix nicht erklären |
| «Hilfs-Tools» wie `searchInternal()` exponiert | LLM hat Tools, die nur intern Sinn ergeben |

## Remediation

```diff
- @mcp.tool()
- async def get_motion_id(title: str) -> str: ...
-
- @mcp.tool()
- async def get_motion_details(motion_id: str) -> dict: ...
-
- @mcp.tool()
- async def get_motion_tags(motion_id: str) -> list: ...

+ @mcp.tool(
+     name="findMotionWithDetails",
+     description=(
+         "Sucht eine parlamentarische Motion anhand des Titels und liefert "
+         "vollständige Details inkl. Tags, Status, Eingebenden. "
+         "Aggregiert intern Suchindex + Detail-API + Tag-API."
+     ),
+ )
+ async def find_motion_with_details(title: str, ctx: Context) -> dict:
+     motion_ids = await api.search_motion_ids(title, limit=5)
+     if not motion_ids:
+         return {"results": [], "match_type": "none", "note": "..."}  # ARCH-003
+     # Parallel Details + Tags für alle Treffer
+     detail_tasks = [api.get_motion_details(mid) for mid in motion_ids]
+     tag_tasks = [api.get_motion_tags(mid) for mid in motion_ids]
+     details, tags = await asyncio.gather(
+         asyncio.gather(*detail_tasks),
+         asyncio.gather(*tag_tasks),
+     )
+     return {
+         "results": [
+             {**d, "tags": t} for d, t in zip(details, tags)
+         ],
+         "match_type": "exact",
+         "count": len(details),
+     }
```

## Effort

M — 1–3 Tage. Identifikation der Aggregations-Möglichkeiten + Refactoring + Performance-Tests.

## References

- PDF Sec 2.3 — Capability-Aggregation
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
