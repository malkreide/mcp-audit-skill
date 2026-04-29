# Roadmap — mcp-audit-skill

Stand: **v0.5.0 (2026-04-26) — vollständig.**

Der Skill enthält 68 Checks in 8 Kategorien und deckt alle Sektionen der ursprünglichen Best-Practice-PDF sowie der Anhang-PDF (`mcp-server-architecture-best-practice.pdf`) ab.

---

## Stand v0.5.0

| Kategorie | Quelle | Anzahl Checks | Status |
|---|---|---|---|
| `ARCH` | PDF Sec 2 + Anhang A1, A2, A5, A6, A8, A9 | 12 | ✅ |
| `SDK` | PDF Sec 3 | 5 | ✅ |
| `SEC` | PDF Sec 4 + Anhang B1–B12 | 23 | ✅ |
| `SCALE` | PDF Sec 5 | 6 | ✅ |
| `OBS` | PDF Sec 6 + Anhang B10 | 6 | ✅ |
| `HITL` | PDF Sec 7 | 5 | ✅ |
| `CH` | Custom — DSG/EDÖB, Schweiz-Compliance | 8 | ✅ |
| `OPS` | Anhang C1–C4 (neu in v0.5.0) | 3 | ✅ |
| **Total** | | **68** | **✅** |

**Severity-Verteilung:**
- critical: 15 (22%)
- high: 31 (46%)
- medium: 22 (32%)

---

## Versionshistorie

| Version | Datum | Inhalt |
|---|---|---|
| v0.1.0 | 2026-04-26 | 7 Sample-Checks, einer pro Kategorie |
| v0.2.1 | 2026-04-26 | +6 Critical-Security-Checks |
| v0.2.2 | 2026-04-26 | +5 ARCH + 4 SDK |
| v0.2.3 | 2026-04-26 | +5 SCALE + 4 OBS |
| v0.2.4 | 2026-04-26 | +4 HITL + 7 CH |
| v0.3.0 | 2026-04-26 | +11 SEC Edge-Cases |
| v0.4.0 | 2026-04-26 | Slash-Command-Integration für Claude Code |
| **v0.5.0** | **2026-04-26** | **+14 Checks aus Anhang-PDF (5 ARCH + 5 SEC + 1 OBS + 3 OPS)** |

---

## Künftige Erweiterungen (organisch)

Der Skill wird nicht durch Vollständigkeit weitergetrieben — er ist vollständig gegen die zugrundeliegenden PDFs. Erweiterungen kommen aus drei Quellen:

### 1. Real-World-Findings beim Portfolio-Audit

Beim Audit der Server im Schweizer-Public-Data-MCP-Portfolio entstehen Pattern, die neue Checks rechtfertigen:

- **Wiederkehrende Findings über mehrere Server:** zeigen einen System-Issue, der als eigener Check kodifiziert werden sollte
- **Server-spezifische Patterns:** z.B. SPARQL-Endpoint-Eigenheiten, OData-Quirks, CKAN-spezifische Patterns — können als kontextabhängige Checks aufgenommen werden (`applies_when: data_source.type == "CKAN"`)
- **False-Positives bei automatisierten Checks:** Verfeinerung der `applies_when`-Conditions

### 2. MCP-Spec-Updates

Die MCP-Spec hat in 13 Monaten vier Major-Updates erlebt (siehe ARCH-012). Neue Spec-Versionen können neue Checks erforderlich machen:

- **Neue Primitives** (z.B. ein viertes Primitiv neben Tools/Resources/Prompts)
- **Neue Annotations** (z.B. `costHint`, `latencyHint`)
- **Neue Auth-Modelle** (Spec-Updates zu OAuth, mTLS, andere)
- **Neue Transport-Optionen** (nach Streamable HTTP wahrscheinlich noch nicht das letzte Wort)

Quartalsweise Spec-Review als Notion-Workflow festhalten.

### 3. Neue Compliance-Anforderungen

Compliance-Landschaft im Schweizer öffentlichen Sektor entwickelt sich:

- **EU AI Act** — Schweizer Übernahme oder Bilaterale-Anpassungen
- **Schweizer KI-Gesetz** — frühe Entwürfe sichtbar, Stand 2026 unklar wann verbindlich
- **revDSG-Verordnungen** — Konkretisierungen zu Art. 22 Automatisierte Einzelentscheidung
- **ISDS-Update Stadt Zürich** — periodische Überarbeitungen
- **Sektorspezifische Bildungs-Vorgaben** — z.B. neue VSG-Bestimmungen Kanton Zürich zur Datenverarbeitung in der Volksschule

Pro neuem Compliance-Layer: Audit, ob existierende `CH`-Checks ausreichen oder neue ergänzt werden.

---

## Reife-Indikator: nächster Aktivitätsmarker ist nicht v0.6, sondern Pilot-Audit

Der Skill ist nun in einem Reife-Zustand, wo der nächste sinnvolle Schritt **nicht** weitere Checks sind, sondern ein echter Pilot-Audit gegen einen Portfolio-Server. Der Pilot zeigt:

- Welche Checks tatsächlich greifen (vs. theoretisch greifen könnten)
- Wo `applies_when`-Conditions zu eng oder zu breit sind
- Wo das Frontmatter-Schema Anpassungen braucht
- Welche Patterns bei mehrfacher Anwendung als wiederverwendbare Anti-Pattern in `reference/anti-patterns.md` gehören

**Empfohlene Pilot-Kandidaten** (geordnet nach Lerngewinn):

1. `parlament-mcp` oder ein OData-basierter Server — testet ARCH-, SEC-, SDK-Pfade
2. `zh-education-mcp` — Schulamt-Kontext → testet alle CH-Checks
3. `zurich-opendata-mcp` — CKAN-Backend, dual transport → testet SCALE-Pfade
4. Ein hypothetischer Phase-3-Write-Server (falls einer geplant ist) → testet ARCH-010, SEC-019, OPS-003

---

## Strukturelle Erweiterungen (mittelfristig)

Unabhängig vom Check-Katalog können diese strukturellen Erweiterungen den Audit-Workflow stärken:

| Erweiterung | Nutzen | Aufwand |
|---|---|---|
| `reference/anti-patterns.md` mit wiederverwendbaren Code-Snippets | Beschleunigt Findings-Schreiben bei Wiederholungen | Niedrig (organisch nach Pilot) |
| Notion-Audit-Findings-Sub-DB unter Audit-Tracker | Findings strukturiert tracken statt freier Markdown | Mittel |
| Reference-Template-Repo `mcp-server-template` mit Pass-Pattern aller Checks | Neue Server starten audit-ready | Hoch |
| CI-Lint im Skill-Repo: validates Frontmatter | Schützt gegen Schema-Drift bei künftigen Erweiterungen | Niedrig |
| Audit-Report-Aggregator: portfolio-weiter Status-Dashboard | Sichtbarkeit für GL und KI-Fachgruppe | Mittel |

Keine dieser Erweiterungen blockiert die heutige Nutzbarkeit des Skills.
