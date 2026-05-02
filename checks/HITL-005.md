---
id: HITL-005
title: "Destructive Operation Confirmation"
category: HITL
severity: critical
applies_when: 'write_capable == true'
pdf_ref: "Sec 7.2"
evidence_required: 3
---

# HITL-005 — Destructive Operation Confirmation

## Description

Wenn ein MCP-Server schreibende Tools (DELETE, UPDATE, DROP, Send-Email, Post-Message, Cancel-Subscription, etc.) anbietet, erweitert er die Macht des LLMs ins Unumkehrbare. Ohne Human-in-the-Loop-Checkpoint (HITL) kann eine Halluzination oder Prompt-Injection zu echten, irreversiblen Schäden führen — gelöschte Daten, verschickte E-Mails an falsche Empfänger, abgesagte Termine, gelöschte Code-Branches.

Die MCP-Spezifikation **verlangt** für destruktive Operationen einen Bestätigungs-Workflow. Der Server initiiert die Operation, der Host (Claude Desktop / Claude.ai) zeigt dem User eine Bestätigungs-UI, der User stimmt **explizit** zu, erst dann führt der Server tatsächlich aus.

## Verification

### Modus 1: code_review (Tool-Annotations)

MCP-Tools können in ihrer Definition angeben, ob sie destruktiv sind. Diese Annotation triggert beim Host die Confirmation-UI.

```bash
# Suche nach destructive-Annotation
grep -rE "destructive|destructiveHint|read_only_hint|requires_confirmation" src/
```

**Pass-Pattern (Python / FastMCP):**

```python
@mcp.tool(
    name="deleteUser",
    description="Permanently deletes a user account and all associated data.",
    annotations={
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
        "readOnlyHint": False,
    },
)
async def delete_user(user_id: str, ctx: Context) -> dict:
    # Implementation
    ...
```

**TypeScript:**

```typescript
server.registerTool({
  name: "deleteUser",
  description: "...",
  inputSchema: z.object({ userId: z.string().uuid() }),
  annotations: {
    destructiveHint: true,
    idempotentHint: false,
    readOnlyHint: false,
  },
  handler: async (args) => { /* ... */ },
});
```

### Modus 2: code_review (Mehrstufige Bestätigung in komplexen Cases)

Für besonders kritische Operationen (Massen-Delete, Bulk-Send, Daten-Migration) reicht die Standard-Annotation nicht. Hier ist ein Two-Phase-Commit-Pattern erforderlich:

```python
@mcp.tool(annotations={"destructiveHint": True})
async def bulk_delete_users(user_ids: list[str], ctx: Context) -> dict:
    if len(user_ids) > 10:
        # Bei grossen Operationen: separate confirmation-Phase
        confirmation_token = await ctx.elicit(
            schema={
                "type": "object",
                "properties": {
                    "confirmed_count": {"type": "integer"},
                    "confirmation_phrase": {"type": "string"},
                },
                "required": ["confirmed_count", "confirmation_phrase"],
            },
            message=(
                f"You are about to delete {len(user_ids)} users. "
                f"This action is irreversible. "
                f"Type the number {len(user_ids)} and the word DELETE to confirm."
            ),
        )
        if (
            confirmation_token.confirmed_count != len(user_ids)
            or confirmation_token.confirmation_phrase != "DELETE"
        ):
            return {"isError": True, "content": [TextContent(
                type="text", text="Confirmation failed. Operation cancelled."
            )]}
    # Eigentliche Löschung
    return await _do_bulk_delete(user_ids)
```

### Modus 3: code_review (Audit-Logging vor Ausführung)

Jede destruktive Operation muss **vor** Ausführung in einen Audit-Log geschrieben werden — nicht erst danach. So bleibt im Crash-Fall nachvollziehbar, dass die Operation initiiert wurde.

```bash
grep -rE "audit_log|AuditLog|logger\.audit|structlog" src/
```

**Pass-Pattern:**

```python
import structlog
audit_logger = structlog.get_logger("audit")

async def delete_user(user_id: str, ctx: Context) -> dict:
    audit_logger.warning(
        "destructive_operation_initiated",
        operation="delete_user",
        target_id=user_id,
        actor=ctx.client_info.name,
        session_id=ctx.session_id,
    )
    # ... eigentliche Löschung
    audit_logger.warning(
        "destructive_operation_completed",
        operation="delete_user",
        target_id=user_id,
    )
```

### Modus 4: runtime_test (Tatsächliches Verhalten beobachten)

In einer Test-Umgebung das Tool aufrufen und prüfen, ob der Host eine Bestätigungs-UI zeigt:

1. MCP-Inspector oder Claude Desktop mit Test-Server verbinden
2. Schreibendes Tool aufrufen
3. Visuell prüfen: erscheint eine Bestätigungsabfrage vor Ausführung?
4. Bei «Cancel» klicken: Operation darf nicht ausgeführt werden

## Pass Criteria

- [ ] **Alle** schreibenden/destruktiven Tools haben `destructiveHint: true` in ihren Annotations
- [ ] Idempotenz-Hints (`idempotentHint`) sind korrekt gesetzt (DELETE meist `false`, PUT mit gleichem Body meist `true`)
- [ ] Für High-Stakes-Operationen (Bulk-Delete, Mass-Send): zusätzliche Elicitation-basierte Confirmation
- [ ] Audit-Log-Eintrag **vor** der eigentlichen Operation
- [ ] Test in Live-Umgebung zeigt: Confirmation-UI erscheint vor Ausführung
- [ ] Cancel-Pfad lässt Operation nicht durchlaufen

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| `destructiveHint` fehlt → Host zeigt keine Confirmation-UI | LLM kann ohne User-Bestätigung löschen/senden |
| Audit-Log nur **nach** Operation | Bei Crash unklar ob Operation lief oder nicht |
| Bulk-Operationen ohne separaten Confirmation-Schritt | User klickt einmal «OK» und löscht 10’000 Records |
| `idempotentHint: true` falsch gesetzt für DELETE | Host darf Operation bei Fehler retry’en, was unerwünscht ist |
| Confirmation-Text generisch («Are you sure?») statt spezifisch | User klickt routinemässig «OK» (Consent Fatigue) |

## Remediation

### Schritt 1: Inventar aller schreibenden Tools

```bash
# Liste aller Tools, dann manuell als read/write markieren
grep -rE "@mcp\.tool|registerTool" src/ -A2 | grep -E "name|description"
```

Als Tabelle:

| Tool | Wirkung | destructiveHint | idempotentHint |
|---|---|---|---|
| `getUserInfo` | read | — | — |
| `updateUserEmail` | write | true | true |
| `deleteUser` | destructive | true | false |
| `sendEmail` | external side-effect | true | false |

### Schritt 2: Annotations setzen

Pro Tool:

```python
@mcp.tool(
    name="sendEmail",
    description="Sends an email via SMTP. This is irreversible once sent.",
    annotations={
        "destructiveHint": True,        # nicht zurücknehmbar
        "idempotentHint": False,         # gleicher Call → mehrfacher Send
        "openWorldHint": True,           # externer Effekt
        "readOnlyHint": False,
    },
)
async def send_email(to: str, subject: str, body: str, ctx: Context) -> dict:
    audit_logger.warning("email_send_initiated", to=to, subject=subject[:80])
    # ... actual send
```

### Schritt 3: High-Stakes-Operationen mit Elicitation

Siehe Beispiel oben unter Modus 2.

### Schritt 4: Test mit MCP Inspector

```bash
# MCP Inspector lokal starten und Server-Tools durchklicken
npx @modelcontextprotocol/inspector path/to/server.py
# Visuell prüfen: erscheint Confirmation bei destruktiven Tools?
```

## Effort

M — 1–3 Tage. Inventarisierung + Annotation-Updates + Audit-Logging + 1–2 Elicitation-Flows für kritische Operationen + Tests.

## References

- PDF Sec 7.2 — Human-in-the-Loop Kontrollen
- [MCP Spec: Tool Annotations](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [MCP Spec: Elicitation](https://modelcontextprotocol.io/specification/draft/client/elicitation)
- [Permit.io: HITL for AI Agents](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo)
