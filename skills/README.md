# `skills/` — die Companion-Skills dieses Repositories

Ein Verzeichnis je Skill, jedes mit eigener `SKILL.md`, eigenem CHANGELOG und
eigenem `reference/`. Eingezogen in Phase 3 der Zusammenfuehrung, per
`git subtree` — die Historie der Herkunftsrepos ist erhalten und mit
`git log --follow skills/<name>/SKILL.md` lesbar.

| Verzeichnis | Skill-Name | Herkunft | Stand |
|---|---|---|---|
| `mcp-data-source-probe/` | `mcp-data-source-probe` | `malkreide/mcp-data-source-probe-skill` | eingezogen |
| `mcp-data-fidelity/` | `mcp-data-fidelity` | `malkreide/mcp-data-fidelity-skill` | eingezogen |
| `mcp-transport-hardening/` | `mcp-transport-hardening` | `malkreide/mcp-transport-hardening-skill` | eingezogen |

Die Frontmatter-`name` sind unveraendert geblieben — daran haengt, ob Claude
den Skill ueberhaupt zieht.

## Warum `mcp-audit` selbst NICHT hier liegt

Die vierte Skill dieser Kette ist dieses Repository, und ihre `SKILL.md` steht
in der Wurzel. Das ist eine Entscheidung aus Phase 3, keine offene Baustelle.

`mcp-audit.skill` — das hochladbare Paket — **spiegelt den Repository-Baum**:
`checks/SEC-001.md` liegt im Archiv unter `mcp-audit/checks/SEC-001.md`, an
genau demselben relativen Pfad. Daran haengen zwei Dinge, die `skill-manifest.txt`
ausdruecklich begruendet: `SKILL.md` nennt seine Dateien repo-relativ
(`python "$SKILL_BASE/tools/audit_init.py"`), damit im installierten Skill
woertlich derselbe Aufruf laeuft wie im Klon; und die Werkzeuge unter `tools/`
haengen ihre eigene Baumwurzel in `sys.path`.

Ein Umzug nach `skills/mcp-audit/SKILL.md` brauchte im Archiv trotzdem
`SKILL.md` an der Paketwurzel — also eine Umsortierung statt einer Spiegelung,
und damit den Bruch, gegen den das Manifest geschrieben ist. Das waere ein
Umbau von `skill-manifest.txt`, `tools/build_skill.py` und
`tools/skill_package.py` mitsamt ihren Tests, und er hat mit der
Zusammenfuehrung nichts zu tun.

Die Aufteilung ist damit: **die Wurzel ist der `mcp-audit`-Skill**
(`SKILL.md`, `checks/`, `templates/`, `docs/`), **`skills/` haelt die drei
Companions.** Wer das vereinheitlichen will, faengt beim Paketformat an, nicht
hier.

## Was noch nicht hier ist

Die Pruefungen der drei Skills (`tools/checks/` in den Herkunftsrepos) ziehen
in Phase 2b nach `tools/gates/` und `tools/suites/<name>/`. Bis dahin laufen
die Herkunftsrepos weiter und fahren ihre eigenen Gates — sie werden erst in
Phase 5 archiviert. Der Ablauf steht in
[`docs/consolidation/MERGE-PLAN.md`](../docs/consolidation/MERGE-PLAN.md).
