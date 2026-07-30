---
id: IDENT-003
title: "Werte, die die Pipeline überschreibt, brauchen einen eigenen Check"
category: IDENT
severity: medium
applies_when: 'always'
pdf_ref: "Custom (Portfolio-Sweep 2026-07-29, 30 Server)"
evidence_required: 2
---

# IDENT-003 — Pipeline-überschriebene Werte prüfen

## Description

`server.json` ist das Manifest für die MCP Registry. Beim Veröffentlichen synchronisiert `publish.yml` die Version daraus **aus dem Tag-Namen** — die committete Fassung erreicht das publizierte Artefakt also nie.

Genau deshalb kann sie beliebig lange falsch sein. Bei `swiss-environment-mcp` stand sie von v0.2.3 bis v0.5.0 auf einer veralteten Nummer: funktional folgenlos, denn in der Registry landete jedes Mal korrekt die Tag-Version. Aufgefallen ist es niemandem, weil nichts brach.

Der Sweep fand vier Server mit dieser Abweichung (`news-monitor`, `swiss-courts`, `swiss-cultural-heritage`, `swiss-statistics` — letzterer 0.3.0 bei Paketversion 0.6.0).

**Der verallgemeinerbare Kern — und der eigentliche Grund für diesen Check:**

> Ein Wert, den die Pipeline zur Laufzeit überschreibt, wird nie geprüft. Er kann beliebig lange falsch sein, ohne dass etwas bricht.

Das gilt über `server.json` hinaus: überall dort, wo CI/CD einen committeten Wert ersetzt (Image-Tags, Chart-Versionen, generierte Manifeste, `.env.example`-Defaults), fehlt der Rückkanal. Der committete Wert wirkt dann nur noch auf **Menschen**, die ihn lesen — und führt sie in die Irre, ohne dass eine Maschine widerspricht.

## Verification

### Modus 1: code_review

```bash
# Alle Versionsfelder im Manifest gegen pyproject.toml
python - <<'EOF'
import json, tomllib
py = tomllib.load(open("pyproject.toml","rb"))["project"]["version"]
d = json.load(open("server.json"))
vals = [("version", d.get("version"))] + [
    (f"packages[{i}].version", p.get("version")) for i, p in enumerate(d.get("packages", []))
]
for where, v in vals:
    print(("OK  " if v == py else "!!  ") + f"{where} = {v!r} (pyproject {py!r})")
EOF
```

Beide Ebenen prüfen: das Server-Objekt **und** jeden Package-Eintrag. Ein Bump nur an einer der beiden Stellen bleibt sonst unentdeckt — im Sweep der ursprüngliche Auslöser für den Check.

### Modus 2: Inventar der überschriebenen Werte

Über das Manifest hinaus: Welche Werte ersetzt die Pipeline?

```bash
grep -rn "sed -i\|jq '\.\|yq -i\|::set-output\|GITHUB_REF_NAME" .github/workflows/
```

Jeder Treffer bezeichnet einen Wert, der im Repo steht, aber im Artefakt anders lautet. Für jeden davon gilt die Frage: Prüft irgendetwas die committete Fassung?

## Pass Criteria

- [ ] `server.json → version` stimmt mit `pyproject.toml` überein
- [ ] **Jeder** `packages[*].version` stimmt überein, nicht nur der erste
- [ ] Ein CI-Check erzwingt das, nicht nur eine Konvention
- [ ] Der Check läuft ohne Projekt-Installation (schlanker Lint-Job genügt)
- [ ] Die Werte, die `publish.yml` zur Laufzeit überschreibt, sind dokumentiert
- [ ] Für jeden überschriebenen Wert existiert ein Check auf die committete Fassung

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| «Wird beim Publish eh gesetzt» als Begründung fürs Nichtpflegen | Committete Datei führt Lesende in die Irre |
| Nur `version` geprüft, `packages[*].version` nicht | Halber Bump bleibt unentdeckt |
| Check erst im Test-Job mit voller Installation | Läuft nicht im schlanken Lint-Job, wird umgangen |
| Abbruch beim ersten Befund | Weitere, schwerere Abweichungen bleiben ungesehen (siehe IDENT-004) |

## Remediation

`scripts/check_version_sync.py`, reine Standardbibliothek, im `lint`-Job:

```python
found = [("server.json → version", server.get("version", ""))]
for i, pkg in enumerate(server.get("packages", [])):
    found.append((f"server.json → packages[{i}].version", pkg.get("version", "")))

mismatches = [(w, v) for w, v in found if v != version]
if mismatches:
    ...
    sys.exit(1)
```

**Einbau als Schritt in einen bestehenden Job, nicht als eigener Job.** Ein neuer Job erzeugt einen neuen Check-Namen und kann mit Branch-Rulesets kollidieren, die bestimmte Namen als erforderlich führen — im Sweep bei einem Repo real aufgetreten.

Auf Python 3.10 gibt es `tomllib` noch nicht. Wo die Matrix dort beginnt, braucht der Check einen bedingten Import mit Minimal-Parser für die zwei benötigten Felder — sonst stürzt er ab, statt zu prüfen.

## Effort

S — 30 Minuten inklusive CI-Einbau. Das Inventar der überschriebenen Werte kann länger dauern.

## References

- Portfolio-Sweep 2026-07-29: 4 von 30 Servern betroffen
- `swiss-environment-mcp` v0.5.1 — Manifest stand von v0.2.3 bis v0.5.0 falsch
- IDENT-004 — dieselbe Klasse für dokumentierte Werte
- OPS-001 — CI-Gates
