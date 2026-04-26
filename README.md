# mcp-audit-skill

> Reproduzierbares Audit-Skill für MCP-Server gegen einen versionierten Best-Practice-Katalog. Teil des Swiss Public Data MCP Portfolio von [@malkreide](https://github.com/malkreide).

## Was ist das?

Wenn du ein Portfolio von MCP-Servern betreibst, brauchst du irgendwann eine systematische Antwort auf «ist mein Server gut gebaut?». Dieses Skill kodiert ein 6-Schritte-Audit-Verfahren gegen einen kategorisierten Check-Katalog. Bei 30+ Servern lohnt sich diese Investition.

**Drei Eigenschaften:**

- **Profil-getrieben:** Ein Server-Profil (Transport, Auth, Datenklasse, Schreibzugriff, Deployment) filtert ~50 Checks auf die ~15-45 tatsächlich anwendbaren. Keine Audit-Müdigkeit.
- **Evidenz-pflichtig:** Jedes Finding braucht Datei-Pfad und Zeilen-Referenz. Vermutungen sind keine Befunde.
- **Severity-diszipliniert:** `critical` blockiert Production. `low` ist Backlog. Keine Inflation.

## Schnellstart

### Als Claude Code Slash-Command (`/audit-mcp`)

Der Skill bringt einen Slash-Command mit, der den 6-Schritte-Workflow als Claude-Code-Workflow ausführt — Profil-Load, Applicability-Filter, automatisierte Check-Ausführung, Findings-Generierung und Report-Erstellung in einem Lauf.

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git
cd mcp-audit-skill
./setup-slash-command.sh
```

Das Setup-Script symlinkt `.claude/commands/audit-mcp.md` nach `~/.claude/commands/`, damit `/audit-mcp` global in jeder Claude-Code-Session verfügbar ist. Optional kannst du `MCP_AUDIT_SKILL_PATH` in deiner Shell-RC setzen, damit der Command den Skill-Pfad nicht jedes Mal erfragen muss.

Verwendung:

```bash
# In einem MCP-Server-Repo oder beliebigen Verzeichnis
claude
```

```
> /audit-mcp .
> /audit-mcp /pfad/zum/server-repo
> /audit-mcp https://github.com/malkreide/zh-education-mcp
```

Der Command startet den 6-Schritte-Audit. Bei Profil-Unsicherheit fragt er nach. Output landet in `<repo>/audits/YYYY-MM-DD-<server-name>/` mit:

- `audit-report.md` — Gesamtreport nach Template
- `findings/<check-id>-*.md` — pro Fail/Partial-Check ein Finding
- `raw/<check-id>.txt` — Roh-Output der Bash-Befehle für Audit-Trail

Automatisierungstiefe ist **Standard**: alle `automated`/`config_check`/`documentation_check`-Modi laufen automatisch, `code_review`/`runtime_test`-Modi werden als TODO mit Such-Pattern in den Report geschrieben (kein Pattern-Match-Halluzinieren).

### Als Claude.ai Skill (manuell)

```bash
git clone https://github.com/malkreide/mcp-audit-skill.git ~/skills/mcp-audit
```

Dann in Claude.ai: `Verwende mcp-audit-Skill für <server-name>`. Der Workflow läuft dann interaktiv ohne Slash-Command-Automatisierung.

## Struktur

```
mcp-audit-skill/
├── SKILL.md                          # Methodik: 6-Schritte-Audit-Verfahren
├── checks/                           # ein Markdown pro Best-Practice-Check
│   ├── ARCH-001.md                   # Tool-Design & Architektur
│   ├── SDK-005.md                    # SDK-spezifische Patterns
│   ├── SEC-001.md                    # Security
│   ├── SCALE-002.md                  # Skalierung & Transport
│   ├── OBS-001.md                    # Observability & Errors
│   ├── HITL-005.md                   # Human-in-the-Loop
│   └── CH-001.md                     # Schweiz-Compliance (DSG/EDÖB)
├── reference/
│   └── best-practices-summary.md     # PDF-Quelle komprimiert
├── templates/
│   ├── finding.md                    # Template für einzelnes Finding
│   └── audit-report.md               # Template für Server-Gesamtreport
├── CHANGELOG.md
└── README.md
```

## Check-Kategorien

| Code | Bereich | Quelle |
|---|---|---|
| `ARCH` | Tool-Design, Naming, Granularität | PDF Sec 2 |
| `SDK` | FastMCP, TypeScript, Zod, Lifecycle | PDF Sec 3 |
| `SEC` | Security (grösste Kategorie) | PDF Sec 4 |
| `SCALE` | Transport, Load Balancing, Container | PDF Sec 5 |
| `OBS` | Logging, Errors, SIEM | PDF Sec 6 |
| `HITL` | Sampling, Human-in-the-Loop | PDF Sec 7 |
| `CH` | DSG/EDÖB, Schweiz-Compliance | Custom |

## Severity-Stufen

| Stufe | Bedeutung | Konsequenz |
|---|---|---|
| `critical` | Sicherheitslücke / Compliance-Bruch | Blockiert Produktion |
| `high` | Architektureller Mangel mit signifikantem Risiko | Im laufenden Sprint fixen |
| `medium` | Best-Practice-Verletzung | Im nächsten Sprint planen |
| `low` | Polish, Optimierung | Backlog |

## Audit-Workflow (Kurzform)

1. **Profil laden** — Server-Eigenschaften aus Notion Audit Tracker
2. **Katalog laden** — alle Checks parsen
3. **Applicability-Filter** — nur passende Checks selektieren (z.B. stdio-only-Server überspringt OAuth-Checks)
4. **Check-Ausführung** — automatisch (grep, AST) oder Code-Review pro Check
5. **Findings dokumentieren** — `templates/finding.md`
6. **Audit-Report** — `templates/audit-report.md`

Details siehe [`SKILL.md`](./SKILL.md).

## Verwandte Repos

- [`malkreide` MCP-Server-Portfolio](https://github.com/malkreide?tab=repositories) — die ~30 MCP-Server, gegen die dieses Skill auditiert
- Notion **MCP Audit Tracker** — laufender Status aller Server-Audits (intern)
- Notion **MCP Server Portfolio** — Master-Inventar aller Server (intern)

## Status

**Version:** v0.1.0 (initial release)

**Vollständigkeit:**
- ✅ Methodik (`SKILL.md`)
- ✅ Templates (Finding, Audit-Report)
- ✅ Reference-Summary
- ✅ Check-Katalog: **53 Checks, alle 7 Kategorien vollständig**

Künftige Erweiterungen kommen aus Real-World-Findings beim Portfolio-Audit oder PDF-Updates der MCP-Steering-Group.

## Lizenz

MIT — siehe `LICENSE`

## Kontext

Entwickelt im Rahmen des Swiss Public Data MCP Portfolio für die KI-Fachgruppe der Stadtverwaltung Zürich und das Schulamt der Stadt Zürich. Frei verwendbar von anderen Verwaltungen, Forschungsinstituten oder Privatpersonen, die MCP-Server systematisch auditieren wollen.
