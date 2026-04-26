---
id: HITL-004
title: "Sequential Thinking Object-Sanitization gegen Key-Leaks"
category: HITL
severity: medium
applies_when: 'uses_sequential_thinking == true'
pdf_ref: "Sec 7.3"
evidence_required: 2
---

# HITL-004 — Sequential Thinking Object-Sanitization

## Description

Das Sequential-Thinking-Pattern erlaubt Servern, komplexe Aufgaben in adressierbare Denkschritte («Thoughtboxes») zu zerlegen. Jeder Thought ist ein eigenständiges Objekt mit ID, Inhalt, Verweisen auf vorherige/nächste Thoughts. Diese Thoughts werden im Server-Memory gehalten, an den Client zur Anzeige propagiert und bei Sampling als Chain-of-Thought weitergereicht.

**Risiko:** Wenn Tool-Code Thoughts mit dem Inhalt von Server-Variablen befüllt — z.B. zum Debug-Tracing — können dort Secrets, Env-Vars, API-Keys oder PII landen. Diese fliessen dann in:

1. Den User-sichtbaren Trace (UI-Leak)
2. Das Sampling als Chain-of-Thought (LLM-Provider-Leak)
3. Die Audit-Logs des Servers (SIEM-Leak)

Der Best-Practice-Standard: **Server-seitiger Sanitization-Filter**, der Thought-Objekte vor Serialisierung scannt und verdächtige Pattern (API-Keys, Tokens, Env-Var-Werte) entfernt.

Severity ist `medium`, weil Sequential Thinking optional ist und nicht alle Server es verwenden.

## Verification

### Modus 1: code_review (Sanitization vor Thought-Speicherung)

```bash
# Suche nach Sequential-Thinking-Implementation
grep -rE 'sequential_thinking|SequentialThinking|nextThoughtNeeded|Thought\(' src/

# Suche nach Sanitization-Logik
grep -rE 'sanitize.*thought|redact.*thought|filter.*thought' src/
```

**Pass-Pattern:**

```python
import os
import re

# Pattern für bekannte Secret-Formate
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{32,}"),  # OpenAI API Key
    re.compile(r"sk-ant-[A-Za-z0-9_-]{32,}"),  # Anthropic API Key
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
    re.compile(r"ghp_[A-Za-z0-9]{36}"),  # GitHub PAT
    re.compile(r"glpat-[A-Za-z0-9_-]{20}"),  # GitLab PAT
]


def sanitize_thought_content(content: str) -> str:
    """Entfernt bekannte Secret-Pattern aus Thought-Content."""
    # Bekannte Secret-Formate
    for pattern in SECRET_PATTERNS:
        content = pattern.sub("[REDACTED-SECRET]", content)

    # Aktuelle Env-Var-Werte (paranoia: falls jemand Env-Var direkt in Thought packt)
    for key in ("API_KEY", "SECRET", "TOKEN", "PASSWORD", "DATABASE_URL"):
        for env_name, env_value in os.environ.items():
            if any(s in env_name.upper() for s in ("KEY", "SECRET", "TOKEN", "PASSWORD")):
                if env_value and len(env_value) > 8 and env_value in content:
                    content = content.replace(env_value, f"[REDACTED-ENV-{env_name}]")

    return content


@dataclass
class Thought:
    id: str
    content: str
    next_needed: bool

    def __post_init__(self):
        # Sanitization beim Erstellen — kein "vergessenes" Sanitizen später
        self.content = sanitize_thought_content(self.content)


@mcp.tool()
async def reason_step_by_step(query: str, ctx: Context) -> dict:
    thoughts: list[Thought] = []
    thought_id = 0

    # Erster Schritt
    t = Thought(
        id=f"t{thought_id}",
        content=f"Analyzing query: {query}",
        next_needed=True,
    )
    thoughts.append(t)
    # ... iterativer Thought-Aufbau
    return {"thoughts": [t.__dict__ for t in thoughts]}
```

### Modus 2: runtime_test (Sanitization wirkt)

```python
def test_secret_redaction_in_thought():
    leaked = "Debug: api_key=sk-ant-abc123def456ghi789jkl012mno345pqr678"
    sanitized = sanitize_thought_content(leaked)
    assert "sk-ant-" not in sanitized
    assert "[REDACTED-SECRET]" in sanitized

def test_env_var_redaction_in_thought():
    os.environ["TEST_API_KEY"] = "supersecretvalue123"
    leaked = "Loading config: supersecretvalue123 from env"
    sanitized = sanitize_thought_content(leaked)
    assert "supersecretvalue123" not in sanitized
```

## Pass Criteria

- [ ] Server, der Sequential Thinking nutzt, hat eine Sanitization-Funktion
- [ ] Sanitization deckt mindestens ab: API-Key-Pattern (OpenAI, Anthropic, AWS, GitHub), Env-Var-Werte
- [ ] Sanitization wird **automatisch** bei Thought-Erstellung angewandt (nicht optional vom Tool-Code aufzurufen)
- [ ] Tests mit Secret-Pattern decken Edge-Cases ab
- [ ] Audit-Log notiert, wenn Sanitization eine Redaction durchgeführt hat

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Thoughts werden ohne Sanitization gespeichert | Secret-Leak in UI/Sampling/Logs |
| Sanitization optional via Flag | Vergessen → Leak |
| Pattern-Liste zu eng | Neue Secret-Formate entweichen |
| Sanitization erst beim Output, Thoughts in Memory unsanitiert | Server-Crash-Dump leaked alles |

## Remediation

Implementierung wie oben. Zusätzlich:

### CI-Test gegen Regression

```yaml
- name: Sanitization tests must pass
  run: pytest tests/test_thought_sanitization.py -v
```

### Pattern-Update-Verfahren

Im Repo `docs/sanitization-patterns.md` mit:
- Liste aller aktiven Pattern
- Letzter Update-Datum
- Verfahren bei neuem Secret-Format-Bekanntwerden (z.B. neuer Cloud-Provider)

## Effort

S — < 1 Tag pro Server.

## References

- PDF Sec 7.3 — Sequential Thinking
- ARCH-005 — Hardcoded Secrets (verwandt)
- [Anthropic Cookbook: Secret Detection](https://github.com/anthropics/anthropic-cookbook)
