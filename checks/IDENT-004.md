---
id: IDENT-004
title: "Dokumentierte Versionen erzwingen — Badges sind sonst dauerhaft falsch"
category: IDENT
severity: low
applies_when: 'always'
pdf_ref: "Custom (Portfolio-Sweep 2026-07-29, 30 Server)"
evidence_required: 1
---

# IDENT-004 — Dokumentierte Version erzwungen

## Description

Das Versions-Badge im README ist die Zahl, die Menschen als Erstes sehen — und die einzige Stelle im ganzen Repo, hinter der **nichts** steht. `publish.yml` synchronisiert das Manifest aus dem Tag, Tests prüfen den Code, aber ein Shields.io-Badge korrigiert niemand automatisch.

Das Ergebnis ist die häufigste Abweichung im ganzen Portfolio-Sweep: **17 von 30 Servern** hatten ein veraltetes Badge.

| Server | Badge | Paket |
|---|---|---|
| `amtsblatt-mcp` | 0.3.0 | **0.19.0** — sechzehn Minor-Versionen |
| `bag-epl-mcp` | 0.1.0 | 1.0.1 |
| `srgssr-mcp` | 0.1.0 | 1.0.3 |
| `bakom-mcp` | 1.0.0 | 2.0.3 |
| `news-monitor-mcp` | 0.1.0 | 0.3.4 |

Die Severity ist bewusst `low`: Es bricht nichts, und kein Upstream sieht es. Aber es ist die Stelle mit dem **grössten** gemessenen Abstand — weil sie als einzige völlig ungesichert war. Das ist der eigentliche Befund: Nicht die Wichtigkeit einer Stelle bestimmt ihre Drift, sondern ob etwas sie erzwingt.

Wer einen Server evaluiert, liest das README zuerst. Ein Badge, das eine Version vortäuscht, die zwei Major-Versionen zurückliegt, beschädigt die Glaubwürdigkeit des gesamten Repos — auch wenn technisch alles stimmt.

## Verification

```bash
python - <<'EOF'
import re, tomllib, pathlib
ver = tomllib.load(open("pyproject.toml","rb"))["project"]["version"]
pat = re.compile(r"img\.shields\.io/badge/[Vv]ersion-([^-\s)]+)-")
for f in sorted(pathlib.Path(".").glob("README*.md")):
    for m in pat.finditer(f.read_text(encoding="utf-8")):
        print(("OK  " if m.group(1) == ver else "!!  ") + f"{f.name}: {m.group(1)} (pyproject {ver})")
EOF
```

**Alle** README-Varianten prüfen. Bilinguale Repos haben `README.md` und `README.de.md`; im Sweep war mehrfach nur eine der beiden gebumpt — der Bump erfolgte an der Stelle, auf die jemand zufällig geschaut hatte.

## Pass Criteria

- [ ] Jedes Versions-Badge stimmt mit `pyproject.toml` überein
- [ ] Alle README-Varianten geprüft (EN **und** DE), nicht nur die englische
- [ ] Ein CI-Check erzwingt das im selben Lauf wie IDENT-003
- [ ] Gegenprobe gefahren: zurückgedrehtes Badge bricht den Check mit `exit 1`

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Badge nur in `README.md` gebumpt, `README.de.md` vergessen | Halbe Korrektur, Drift bleibt |
| «Nur kosmetisch» als Begründung fürs Weglassen | Genau deshalb driftet es am weitesten |
| Badge ohne Quelle der Wahrheit (Repo ohne `pyproject`-Version) | Nichts, wogegen geprüft werden könnte |
| Check bricht bei erstem Befund ab | Badge-Drift verdeckt die schwerere `src/`-Prüfung |

Der letzte Punkt ist im Sweep real aufgetreten: Der Check meldete Badge-Drift und beendete sich, bevor er `src/` prüfte. Bei acht von neun Servern wäre die eigentliche Frage nie beantwortet worden. **Alle Kategorien melden, dann erst `exit`.**

## Remediation

```diff
- ![Version](https://img.shields.io/badge/version-0.3.0-blue)
+ ![Version](https://img.shields.io/badge/version-0.19.0-blue)
```

Und den Check im selben Lauf wie IDENT-003:

```python
for readme in sorted(ROOT.glob("README*.md")):
    for match in _BADGE.finditer(readme.read_text(encoding="utf-8")):
        found.append((f"{readme.name} → Versions-Badge", match.group(1)))
```

Repos ohne Paketversion (reine Tool-/Skill-Repos) sollten entweder ein Badge ohne Versionsangabe führen oder eine Quelle der Wahrheit definieren. Ein Badge, das gegen nichts prüfbar ist, ist eine Behauptung ohne Deckung.

## Effort

XS — Minuten, sobald der Check aus IDENT-003 steht.

## References

- Portfolio-Sweep 2026-07-29: 17 von 30 Servern betroffen, grösster Abstand 16 Minor-Versionen
- IDENT-003 — derselbe Check, gemeinsamer Lauf
