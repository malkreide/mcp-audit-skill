---
id: ARCH-011
title: "Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)"
category: ARCH
severity: medium
applies_when: 'always'
pdf_ref: "Anhang A8"
evidence_required: 3
---

# ARCH-011 — Standardisierte Repo-Struktur

## Description

Aus dem Schweizer Public-Data-Portfolio bewährt sich ein konsistentes Repo-Layout. Das ist nicht nur Code-Schönheit — es ist Operational Discipline:

- **Auditierbarkeit:** Jeder Auditor (intern, extern) findet Tests, Doku, Lizenz an erwarteter Stelle ohne Anleitung
- **Onboarding:** Neue Maintainer arbeiten in Tagen statt Wochen produktiv
- **Reproducibility:** Identische Strukturen erlauben portfolio-weite Tooling (CI-Templates, Dependency-Scans, Audit-Skill)
- **Compliance:** Klare Trennung von User-facing Doku (README, README.de.md) und interner Doku (`docs/`) erleichtert DSG-Verarbeitungsverzeichnis-Findability

Standard-Struktur:

```
server-name/
├── src/
│   └── server_name/                # snake_case, identisch zu pyproject [project] name
│       ├── __init__.py
│       ├── server.py                # FastMCP-Instance, Tool-Registry
│       ├── tools/                   # Eine Datei pro Tool-Gruppe
│       ├── clients/                 # HTTP-Clients zur Datenquelle
│       ├── schemas/                 # Pydantic-Modelle
│       └── transport.py             # stdio + SSE-Setup (siehe ARCH-004)
├── tests/
│   ├── test_unit.py                 # respx-mocked, läuft in CI
│   └── test_live.py                 # @pytest.mark.live, manuell oder nightly
├── docs/                            # Interne Doku, Audit-Reports, ISDS-Klassifikation
├── audits/                          # Pro Audit-Run ein Verzeichnis (siehe Slash-Command)
├── README.md                        # Englisch (primär)
├── README.de.md                     # Deutsch (secondary)
├── CHANGELOG.md                     # Keep-a-Changelog Format
├── CONTRIBUTING.md                  # Bilingual
├── LICENSE
├── pyproject.toml                   # hatchling, src-Layout
└── .github/workflows/
    ├── test.yml                     # CI: pytest -m "not live"
    └── publish.yml                  # PyPI Trusted Publisher (siehe SEC-008)
```

Abweichungen sind okay, müssen aber begründet sein.

## Verification

### Modus 1: documentation_check (Pflicht-Files vorhanden)

```bash
# Pflicht-Top-Level-Files
for f in README.md README.de.md CHANGELOG.md LICENSE pyproject.toml; do
  test -f "$f" && echo "✓ $f" || echo "✗ $f MISSING"
done

# Pflicht-Verzeichnisse
for d in src tests .github/workflows; do
  test -d "$d" && echo "✓ $d/" || echo "✗ $d/ MISSING"
done

# CI-Workflows
ls .github/workflows/*.yml 2>/dev/null
```

**Pass:** Alle 5 Top-Level-Files vorhanden, alle 3 Verzeichnisse vorhanden, mindestens 1 Workflow-File.

### Modus 2: code_review (src-Layout korrekt)

```bash
# src/-Verzeichnis ist nicht direkt Module, sondern enthält Module
ls src/
# Erwartet: ein Verzeichnis (z.B. server_name/), nicht direkt .py-Files

# pyproject.toml deklariert src-Layout
grep -E 'packages|tool\.hatch\.build' pyproject.toml
```

**Pass-Pattern (`pyproject.toml`):**

```toml
[project]
name = "zh-education-mcp"
version = "0.3.0"
requires-python = ">=3.11"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/zh_education_mcp"]
```

### Modus 3: documentation_check (README.de.md Inhalt-Parität)

```bash
# Beide README müssen die gleichen Top-Level-Sektionen haben
grep -E '^## ' README.md | sort > /tmp/en-sections.txt
grep -E '^## ' README.de.md | sort > /tmp/de-sections.txt
diff /tmp/en-sections.txt /tmp/de-sections.txt
```

**Pass:** Section-Überschriften decken sich semantisch (Übersetzung erlaubt). Nicht jeder Absatz muss synchron sein, aber Sektion-Inventar ja.

### Modus 4: code_review (Konsistente Tool-Verzeichnis-Aufteilung)

Bei Servern mit > 5 Tools sollten sie in Gruppen aufgeteilt sein, nicht alle in `server.py`:

```bash
ls src/*/tools/*.py 2>/dev/null
wc -l src/*/server.py 2>/dev/null
```

**Pass:** Bei > 5 Tools ist `tools/`-Verzeichnis vorhanden. `server.py` ist < 200 Zeilen (Registry + Lifecycle, keine Tool-Bodies).

## Pass Criteria

- [ ] Top-Level-Pflicht-Files vorhanden: `README.md`, `README.de.md`, `CHANGELOG.md`, `LICENSE`, `pyproject.toml`
- [ ] Verzeichnisse vorhanden: `src/`, `tests/`, `.github/workflows/`
- [ ] `src/`-Layout korrekt (kein flat package)
- [ ] CI-Workflows: mindestens `test.yml` (CI ohne live-Tests) und `publish.yml`
- [ ] `README.de.md` ist parallel zu `README.md` (gleiche Top-Level-Sektionen)
- [ ] Bei > 5 Tools: `tools/`-Verzeichnis mit File-pro-Gruppe-Aufteilung
- [ ] Abweichungen vom Standard sind im README begründet

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Flat package (Code direkt in `<repo>/<module>/`) | `pyproject.toml`-Editable-Installs brechen, Test-Imports inkonsistent |
| Kein `README.de.md` | Verstösst gegen Schweizer Mehrsprachigkeit-Norm im öffentlichen Sektor |
| `CHANGELOG.md` fehlt | Releases nicht nachvollziehbar |
| Alle Tools in einer Datei (`server.py` mit 800 Zeilen) | Code-Review schwer, Test-Isolierung erschwert |
| Tests im `src/`-Verzeichnis | Nicht-Standard, Linter-Konflikte |

## Remediation

### Schritt 1: Migration zu src-Layout (falls flat)

```bash
mkdir -p src
git mv my_module src/my_module
# pyproject.toml anpassen:
# [tool.hatch.build.targets.wheel]
# packages = ["src/my_module"]
```

### Schritt 2: README.de.md initial befüllen

Wenn nur `README.md` existiert, mit Übersetzung beginnen — mindestens Top-Level-Sektionen synchron halten.

### Schritt 3: CI-Workflows aufsetzen

`.github/workflows/test.yml`:

```yaml
name: Tests
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest -m "not live"
```

### Schritt 4: Tools aufteilen

Bei > 5 Tools:

```diff
  src/server_name/
+ ├── tools/
+ │   ├── __init__.py
+ │   ├── search.py        # search_motions, search_authors
+ │   ├── statistics.py    # aggregate_*, count_*
+ │   └── notifications.py # send_*
- └── server.py            # vorher 800 Zeilen
+ └── server.py            # nur Registry, ~100 Zeilen
```

## Effort

S — < 1 Tag bei einzelnem Server. M — 1 Woche bei portfolio-weitem Roll-out (29 Server).

## References

- Anhang A8 — Sormena-Pattern
- ARCH-004 — Inversion of Control (Synergie zu `transport.py`)
- SEC-008 — Pre-Configuration Consent (PyPI Trusted Publisher)
- OPS-001 — Test-Strategie (Synergie zu `tests/`-Layout) (siehe v0.5)
- [Python Packaging User Guide: src-Layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
