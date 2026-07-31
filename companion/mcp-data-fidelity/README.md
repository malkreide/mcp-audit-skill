# `mcp-data-fidelity` has moved · ist umgezogen

This skill used to be distributed here, as `companion/mcp-data-fidelity/` inside
`mcp-data-source-probe-skill`. It now has its own repository, which is its
canonical home:

**https://github.com/malkreide/mcp-data-fidelity-skill**

```bash
git clone https://github.com/malkreide/mcp-data-fidelity-skill.git
cp -r mcp-data-fidelity-skill ~/.claude/skills/mcp-data-fidelity
```

The directory name must be `mcp-data-fidelity` — skill discovery uses it.

The copy that sat here was byte-identical to `v1.0.0` of that repository, so
nothing was lost in the move. This directory is no longer updated; the rules are
maintained there, including the sixth one added after the split.

The two skills still divide the work by phase, and installing both is still the
point: `mcp-data-source-probe` covers what happens *before and around* the build,
`mcp-data-fidelity` covers the query code itself. See
[Companion skill](../../README.md#companion-skill-mcp-data-fidelity) in this
repository's README.

---

Dieser Skill wurde bisher hier ausgeliefert, als `companion/mcp-data-fidelity/`
innerhalb von `mcp-data-source-probe-skill`. Er hat jetzt ein eigenes Repo, das
sein kanonisches Zuhause ist — siehe Link oben.

Die Kopie an dieser Stelle war Byte für Byte identisch mit `v1.0.0` jenes Repos,
beim Umzug ist also nichts verlorengegangen. Dieses Verzeichnis wird nicht mehr
gepflegt; die Regeln werden dort weitergeführt, inklusive der sechsten, die nach
der Trennung dazugekommen ist.
