# `skills/` — die vier Skills dieses Repositories

Ein Verzeichnis je Skill, jedes mit eigener `SKILL.md`. Das ist das Layout,
das Claude Code fuer eine Skill-Sammlung erwartet: Eine Installation bringt
alle vier, statt vier Klone einzeln zu pflegen.

| Verzeichnis | Skill-Name | Herkunftsrepo | Stand |
|---|---|---|---|
| `mcp-audit/` | `mcp-audit` | dieses Repo (`/SKILL.md`) | wartet auf Phase 3 |
| `mcp-data-source-probe/` | `mcp-data-source-probe` | `mcp-data-source-probe-skill` | wartet auf Phase 3 |
| `mcp-data-fidelity/` | `mcp-data-fidelity` | `mcp-data-fidelity-skill` | wartet auf Phase 3 |
| `mcp-transport-hardening/` | `mcp-transport-hardening` | `mcp-transport-hardening-skill` | wartet auf Phase 3 |

**Noch ist hier nichts eingezogen.** Diese Verzeichnisse stecken die Zielform
ab; der Umzug der Inhalte ist Phase 3 und passiert per `git subtree`, damit
die Historie der Herkunftsrepos erhalten bleibt. Der vollstaendige Ablauf mit
Datei-fuer-Datei-Entscheid steht in
[`docs/consolidation/MERGE-PLAN.md`](../docs/consolidation/MERGE-PLAN.md).

## Was NICHT hierher zieht

Der **Katalog** bleibt unter `/checks/`. Er ist kein Skill, sondern die
gemeinsame Quelle, gegen die alle vier arbeiten — und er wird von aussen unter
`raw.githubusercontent.com/.../checks/…` zitiert. Ihn zu verschieben braeche
diese Verweise ohne Gegenwert.

Das **Geruest der Pruefungen** bleibt unter `/tools/harness/`. Genau darum
geht die Zusammenfuehrung: EIN Geruest fuer alle Suiten statt vier Kopien. Was
je Skill verschieden ist, sind die Pruefmodule — die ziehen nach
`/tools/suites/<name>/`.
