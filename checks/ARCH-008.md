---
id: ARCH-008
title: "Drei Primitive nutzen: Tools, Resources und Prompts"
category: ARCH
severity: medium
applies_when: 'always'
pdf_ref: "Anhang A2"
evidence_required: 2
---

# ARCH-008 — Drei MCP-Primitive nutzen

## Description

MCP definiert drei orthogonale Primitive, von denen die meisten Server nur eines nutzen:

| Primitiv | Zweck | Beispiel | Mentales Modell |
|---|---|---|---|
| **Tools** | Ausführbare Funktionen mit Side-Effects | `search_motions`, `create_invoice` | **Verben** |
| **Resources** | Passive Daten mit URI für Kontext-Lesen | `db://customers/12345`, `report://q3-2024` | **Substantive** |
| **Prompts** | Templates für wiederkehrende Workflows | `summarize_with_swiss_legal_context` | **Kochrezepte** |

Die häufige Anti-Pattern: alles als Tool modellieren. Ein Tool wie `get_document(id)` ist semantisch ein Resource — es hat keine Side-Effects, ist idempotent, dient nur dem Kontext-Lesen. Als Tool kostet es Tokens im Tool-Manifest und konkurriert mit echten aktiven Operationen um die Tool-Budget-Grenze (siehe ARCH-006).

Resources haben drei klare Vorteile gegenüber Read-only-Tools:

1. **Niedrigerer Token-Verbrauch im Tool-Manifest** — Resources werden nicht in jedem LLM-Call gelistet, sie werden vom Client on-demand abgerufen.
2. **Strukturierte URI-Hierarchie** — `school://schulhaus-leutschenbach/2024/luftqualitaet` ist auch ohne LLM-Inferenz navigierbar.
3. **Cache-Freundlichkeit** — Clients können Resources cachen, Tools nicht.

Prompts sind unterausgenutzt. Sie sind besonders wertvoll für wiederkehrende Schulamt-Workflows: «Bildungsbericht für Quartal Q», «Schulhaus-Vergleich nach Standortindex». Statt dass jeder User den Prompt selbst formuliert, bietet der Server geprüfte, kuratierte Templates an.

Für die meisten Server im Schulamt-Portfolio ist die ehrliche Antwort: Tools-only ist okay für Phase-1-Wrapper, aber Resources sollten geprüft werden, sobald der Server reift.

## Verification

### Modus 1: code_review (Resources-Inventar)

```bash
# Resources-Registrierungen finden
grep -rE '@mcp\.resource|server\.resource\(|registerResource' src/

# Tools, die de facto Read-Only sind und Resources sein könnten
grep -rE 'readOnlyHint.*True|readOnlyHint:\s*true' src/ -B 1
```

**Pass-Pattern (mindestens ein Resource oder dokumentierte Begründung):**

```python
@mcp.resource("schulhaus://{school_id}/profile")
async def get_school_profile(school_id: str) -> str:
    """Statisches Profil eines Schulhauses — Adresse, Klassen, Capacity."""
    profile = await db.get_school_profile(school_id)
    return profile.as_markdown()


@mcp.resource("luftqualitaet://{school_id}/{date}")
async def get_air_quality(school_id: str, date: str) -> str:
    """Luftqualitäts-Messwerte eines Schulhauses an einem Datum."""
    measurements = await api.get_air_quality(school_id, date)
    return measurements.as_csv()
```

**Pass-Pattern (Prompts):**

```python
@mcp.prompt()
async def schulhaus_quartalsbericht(
    school_id: str,
    quarter: Literal["Q1", "Q2", "Q3", "Q4"],
) -> list[Message]:
    """Generiert einen strukturierten Quartalsbericht für ein Schulhaus."""
    return [
        UserMessage(
            f"Erstelle einen Quartalsbericht für Schulhaus {school_id} im "
            f"Quartal {quarter}. Strukturiere nach: Schülerzahl-Entwicklung, "
            f"Personalfluktuation, Infrastruktur-Updates, Pädagogische Highlights. "
            f"Max 2 Seiten."
        ),
    ]
```

### Modus 2: documentation_check (Begründung bei Tools-only)

Wenn der Server bewusst nur Tools nutzt, muss das im README dokumentiert sein:

```bash
grep -iE 'resources|prompts|primitive' README.md README.de.md
```

**Pass:**

```markdown
## MCP-Primitive

Dieser Server nutzt nur **Tools** und keine Resources/Prompts. Begründung:
- Phase-1-Wrapper-Server, alle Daten sind read-only-Tool-Returns
- Resources werden in Phase 2 ergänzt, sobald URI-Schema stabilisiert ist
- Prompts sind nicht relevant, da Use-Cases ad-hoc und nicht wiederkehrend sind
```

## Pass Criteria

- [ ] Server nutzt mindestens zwei der drei Primitive (Tools + Resources oder Tools + Prompts), oder
- [ ] README dokumentiert begründet, warum nur Tools verwendet werden
- [ ] Bei Resources: URI-Schema ist konsistent und dokumentiert
- [ ] Bei Prompts: Template-Liste ist kuratiert, nicht beliebig
- [ ] Tools, die rein read-only sind (idempotent, side-effect-frei, deterministisch), werden auf Resources-Migrations-Potential geprüft

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Alles als Tools, keine Resources | Tool-Manifest-Bloat, höherer Token-Verbrauch pro Call |
| Resources als Tools getarnt (`get_*`-Pattern überall) | Verschenkte Cache- und URI-Vorteile |
| Resource-URIs ohne Schema-Hierarchie | Nicht navigierbar, kein Discoverability-Vorteil |
| Prompts ohne Template-Disziplin (jeder Maintainer fügt eigene hinzu) | Inkonsistente UX, keine Compliance-Kontrolle |

## Remediation

### Schritt 1: Tools-zu-Resources-Audit

Pro Tool prüfen:

```
- Hat Side-Effects? → Tool bleibt
- Ist deterministisch und idempotent? → Resource-Kandidat
- Liefert primär Kontextdaten zum Lesen? → Resource-Kandidat
```

### Schritt 2: URI-Schema definieren

Pro Resource-Klasse ein konsistentes Schema:

```
school://<school_id>/profile
school://<school_id>/classes/<year>
luftqualitaet://<school_id>/<date>
budget://<school_id>/<year>
```

### Schritt 3: Migration

```diff
- @mcp.tool()
- async def get_school_profile(school_id: str) -> dict:
-     return await db.get_school_profile(school_id).dict()

+ @mcp.resource("school://{school_id}/profile")
+ async def school_profile(school_id: str) -> str:
+     profile = await db.get_school_profile(school_id)
+     return profile.as_markdown()
```

### Schritt 4: Prompts-Inventar

Falls wiederkehrende Workflows existieren: pro Workflow ein Prompt-Template, ins README dokumentieren.

## Effort

M — 1–3 Tage. Audit + Migration einer Handvoll Tools + Doku.

## References

- Anhang A2 — Drei Primitive
- ARCH-006 — Tool-Budget (Synergie: weniger Tools durch Resources-Migration)
- ARCH-007 — Capability-Aggregation (komplementär)
- [MCP Spec: Resources](https://modelcontextprotocol.io/specification/draft/server/resources)
- [MCP Spec: Prompts](https://modelcontextprotocol.io/specification/draft/server/prompts)
