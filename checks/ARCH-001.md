---
id: ARCH-001
title: "Tool Naming Convention"
category: ARCH
severity: medium
applies_when: 'always'
pdf_ref: "Sec 2.2"
evidence_required: 2
---

# ARCH-001 — Tool Naming Convention

## Description

LLMs wählen Tools über semantische Entsprechung. Inkonsistente oder maschinenfeindliche Namen führen dazu, dass Tools ignoriert oder fehlerhaft angewandt werden. Die GPT-Tokenizer-Familie parst `camelCase`-Fragmente am effizientesten, gefolgt von `kebab-case` und `snake_case`. Spaces, Punkte und Klammern in Tool-Namen brechen Discovery und Parsing.

## Verification

### Modus 1: automated (Static Code Analysis)

Verlangt das Repo zu untersuchen auf Tool-Definitionen.

```bash
# Python (FastMCP): Tool-Namen aus Decorators
grep -rE "@mcp\.tool\(.*name=" src/ | grep -oP 'name=["'\''][^"'\'']*["'\'']'

# Python (FastMCP, Funktions-basiert): Funktionsnamen unter @mcp.tool()
grep -B1 "@mcp\.tool" src/ | grep -E "^def " | awk '{print $2}'

# TypeScript: Tool-Registrierungen
grep -rE "registerTool\(\s*['\"]" src/ | grep -oP "['\"]\\w+['\"]"
```

**Erwartete Tool-Namen-Eigenschaften:**
- Genau eine konsistente Convention im ganzen Repo (nicht gemischt)
- Keine Spaces, Punkte, Klammern, Unicode-Sonderzeichen
- Erste Convention bevorzugt: `camelCase`

### Modus 2: code_review (Beschreibungs-Qualität)

Pro Tool prüfen, ob die `description=`-Klausel mehr als einen Satz enthält und Kontext liefert.

**Akzeptabel:**
> "Sucht in der Curia-Vista-API nach parlamentarischen Vorstössen. Use-Case: Politische Recherche zu Bildungs-, Datenschutz- oder Verwaltungsthemen. Returnt strukturierte Ergebnisse mit Titel, Datum, Status und URL."

**Nicht akzeptabel:**
> "Searches Curia Vista."

## Pass Criteria

- [ ] Eine einheitliche Naming-Convention im ganzen Repo
- [ ] Convention ist `camelCase` (bevorzugt) oder `kebab-case` / `snake_case` (akzeptabel)
- [ ] Keine Spaces, Punkte, Klammern, Sonderzeichen in Tool-Namen
- [ ] Tool-Beschreibungen enthalten Use-Case oder Kontext (nicht nur Funktion)

## Common Failures

| Pattern | Warum problematisch |
|---|---|
| `get user info` (mit Space) | Discovery bricht in vielen Clients |
| `client.get_user` (mit Punkt) | LLM interpretiert als Method-Chain |
| Mix `getUserInfo` + `get_user_data` | LLM wird verwirrt, welche Convention gilt |
| `tool1`, `tool2`, `helper` | Semantik-leer, LLM kann nicht sinnvoll wählen |

## Remediation

```diff
- @mcp.tool(name="get user info", description="Returns user data.")
+ @mcp.tool(
+     name="getUserInfo",
+     description=(
+         "Liefert Benutzer-Profildaten anhand der User-ID. "
+         "Use-Case: Bei Personalisierung von Antworten oder Audit-Logs. "
+         "Returnt JSON mit Feldern: id, email, role, lastLoginAt."
+     ),
+ )
```

## Effort

S — Lokale Umbenennung im Code, ggf. Anpassung von Tests und Tool-Dokumentation. Bei publiziertem PyPI-Paket: Breaking Change, Major-Version-Bump.

## References

- PDF Sec 2.2 — Semantische Nomenklatur
- [Anthropic Best Practices](https://github.com/lirantal/awesome-mcp-best-practices)
