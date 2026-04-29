---
id: ARCH-009
title: "Tool Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint"
category: ARCH
severity: high
applies_when: 'always'
pdf_ref: "Anhang A5"
evidence_required: 2
---

# ARCH-009 — Tool Annotations explizit setzen

## Description

Die MCP-Spec von 2025-03-26 hat **Tool Annotations** eingeführt — strukturierte Hints, die Hosts (z.B. Claude Desktop) für UI-Entscheidungen verwenden:

| Annotation | Wert | UI-Konsequenz |
|---|---|---|
| `readOnlyHint: true` | Tool macht keine Side-Effects | Auto-Approve im Host möglich, kein Confirmation-Dialog |
| `destructiveHint: true` | Tool kann Daten löschen/überschreiben | Zwei-Schritt-Bestätigung im Host, prominentes UI-Warning |
| `idempotentHint: true` | Wiederholter Call mit gleichen Args = gleiche Wirkung | Retry-Logik im Host aktiviert, kein User-Reauth |
| `openWorldHint: true` | Tool kann externe Welt erreichen (Web, andere Systeme) | Network-Egress-Warning im Host |

Ohne explizite Annotations geht der Host pessimistisch vor: jedes Tool wird als potenziell destruktiv behandelt, jeder Call braucht Confirmation. Das führt zu **Confirmation Fatigue** — User klicken «OK» blind, der Schutzmechanismus verliert seine Wirkung.

Mit korrekten Annotations balanciert der Host Sicherheit und UX: Read-only-Tools laufen ohne Friction, destruktive Tools bekommen prominente Warnings. Falsche Annotations sind aber gefährlich: ein `destructive_drop_table` als `readOnlyHint: true` markiert würde ohne Confirmation laufen.

Dieser Check ist `high`, weil falsche Annotations die UI-basierten Sicherheits-Mechanismen aushebeln.

## Verification

### Modus 1: code_review (Annotations gesetzt)

```bash
grep -rE 'annotations\s*=|readOnlyHint|destructiveHint|idempotentHint|openWorldHint' src/
```

**Pass-Pattern (Python / FastMCP):**

```python
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def search_education_stats(args: SearchArgs, ctx: Context) -> dict:
    return await db.search(args.query)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def delete_user_record(args: DeleteArgs, ctx: Context) -> dict:
    return await db.delete_user(args.user_id)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,  # Wegen idempotency_key
        "openWorldHint": True,    # Sendet E-Mail an extern
    },
)
async def send_notification(args: NotifyArgs, ctx: Context) -> dict:
    return await mailer.send(args.recipient, args.body, idempotency_key=args.idempotency_key)
```

### Modus 2: code_review (Konsistenz Annotation vs. Tool-Verhalten)

Die Annotations müssen mit dem tatsächlichen Verhalten übereinstimmen. Klassische Inkonsistenzen:

```bash
# Tools mit "delete"/"create"/"update" im Namen, aber readOnlyHint=True
grep -rB 5 'readOnlyHint.*True\|readOnlyHint:\s*true' src/ \
  | grep -E 'def (delete|create|update|remove|drop)_'
```

**Fail-Pattern:**

```python
# FAIL: Name suggeriert destruktiv, Annotation sagt read-only
@mcp.tool(annotations={"readOnlyHint": True})
async def delete_old_records(...):
    await db.delete(...)
```

### Modus 3: documentation_check (Annotations-Policy)

```bash
grep -iE 'annotations|readonly|destructive' README.md README.de.md docs/
```

**Pass:** README oder `docs/tool-annotations.md` dokumentiert die Annotations-Policy:

```markdown
## Tool Annotations

Alle Tools dieses Servers haben explizite Annotations gemäss MCP-Spec 2025-03-26.

| Tool | readOnly | destructive | idempotent | openWorld |
|---|:-:|:-:|:-:|:-:|
| search_motions | ✅ | — | ✅ | — |
| send_notification | — | — | ✅ | ✅ |
| delete_user_record | — | ⚠️ | — | — |

Phase-1-Standard: alle Tools sind `readOnlyHint: true`. Schreibende Tools
kommen erst nach Sicherheits-Review in Phase 2/3.
```

## Pass Criteria

- [ ] **Alle** Tools haben explizite Annotations (keine Defaults durch Weglassen)
- [ ] `readOnlyHint` ist konsistent mit Tool-Verhalten (nichts Schreibendes als read-only)
- [ ] `destructiveHint: true` für alle Tools, die Daten löschen oder überschreiben
- [ ] `idempotentHint` korrekt: bei Idempotency-Key-Pattern (siehe ARCH-010) auf true
- [ ] `openWorldHint: true` bei Tools, die externe Systeme erreichen (HTTP, Mail, Slack)
- [ ] Annotations-Übersicht im README oder docs/

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Annotations weggelassen (Default) | Host muss pessimistisch alle Tools als destruktiv behandeln |
| `readOnlyHint: true` bei Schreib-Operation | Aushebeln der UI-Confirmation, kritisches Sicherheitsrisiko |
| `destructiveHint: false` weggelassen bei `delete_*` | Host weiss nicht, dass besondere Vorsicht nötig ist |
| Annotations nicht aktualisiert beim Tool-Refactoring | Drift zwischen Code und Annotations |

## Remediation

### Schritt 1: Annotations-Inventar

Pro Tool eine Tabelle mit den vier Hints. Wenn unsicher: per Default konservativ (alles `false`/weggelassen impliziert «kann gefährlich sein»).

### Schritt 2: Decorator-Helper

```python
from typing import Literal

def read_only_tool(*args, **kwargs):
    """Shortcut für read-only Tools mit konsistenten Annotations."""
    annotations = kwargs.pop("annotations", {})
    annotations.update({
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    })
    kwargs["annotations"] = annotations
    return mcp.tool(*args, **kwargs)


@read_only_tool()
async def search_motions(args, ctx):
    ...
```

### Schritt 3: CI-Test gegen Drift

```python
def test_destructive_tools_have_destructive_hint():
    """Tools mit delete/create/update im Namen müssen destructiveHint setzen."""
    suspicious_prefixes = ("delete_", "create_", "update_", "remove_")
    for tool_name, tool in mcp.tools.items():
        if any(tool_name.startswith(p) for p in suspicious_prefixes):
            annotations = tool.annotations or {}
            assert annotations.get("readOnlyHint") is not True, (
                f"{tool_name} suggests write but is marked readOnlyHint"
            )
```

## Effort

S — < 1 Tag. Annotations-Inventar + Decorator + Tests.

## References

- Anhang A5 — Tool Annotations
- HITL-005 — Destructive Confirmation (Synergie via UI-Verhalten)
- ARCH-010 — Idempotency-Keys (Synergie via idempotentHint)
- [MCP Spec: Tool Annotations](https://modelcontextprotocol.io/specification/draft/server/tools#annotations)
