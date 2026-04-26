# Audit-Report-Template

Endgültiges Dokument pro Server-Audit. Wird nach Abschluss aller Findings erstellt und in der Notion-Karte unter `Notizen` verlinkt sowie als Markdown-Datei im `audits/`-Ordner des Server-Repos abgelegt.

---

# MCP-Server Audit-Report — `<server-name>`

**Audit-Datum:** YYYY-MM-DD
**Auditor:** <n>
**Skill-Version:** mcp-audit v0.1.0
**Check-Katalog-Version:** 2026-04
**Audit-Tracker-Karte:** [Notion-Link](https://www.notion.so/...)

---

## 1. Executive Summary

*(Maximal 3 Sätze. Klar, ohne Konjunktive.)*

```
Beispiel:
Der Server zurich-opendata-mcp wurde gegen 23 anwendbare Best-Practice-
Checks geprüft. 19 Checks bestanden, 4 Findings (1 critical, 2 high,
1 medium) wurden dokumentiert. Production-readiness: nicht erreicht —
das critical-Finding zu OAuth-State-Management muss vor dem nächsten
Release behoben werden.
```

**Production-Readiness:** ✅ ja / ❌ nein
**Empfohlenes nächstes Release:** *blockiert / freigegeben mit Auflage / freigegeben*

---

## 2. Profil-Snapshot

Aus Audit Tracker zum Audit-Zeitpunkt:

| Feld | Wert |
|---|---|
| Server-Name | `<name>` |
| Repo-URL | `<url>` |
| Cluster | <cluster> |
| Transport | stdio-only / dual / HTTP/SSE |
| Auth-Modell | none / API-Key / OAuth-Proxy |
| Datenklasse | Public Open Data / Verwaltungsdaten / PII |
| Schreibzugriff | read-only / write-capable |
| Deployment | local-stdio, Railway, Render, ... |
| Produktiv genutzt | ja-extern / ja-intern / nur-Demo / ungenutzt |
| Letzter Commit | YYYY-MM-DD |

---

## 3. Applicability

### Verwendete Checks

| Kategorie | anwendbar | gesamt | Anteil |
|---|---|---|---|
| ARCH | 7 | 7 | 100% |
| SDK | 6 | 6 | 100% |
| SEC | 4 | 18 | 22% |
| SCALE | 3 | 6 | 50% |
| OBS | 3 | 5 | 60% |
| HITL | 0 | 4 | 0% |
| CH | 0 | 6 | 0% |
| **Total** | **23** | **52** | **44%** |

### Severity-Breakdown der anwendbaren Checks

| Severity | Anzahl |
|---|---|
| critical | 4 |
| high | 11 |
| medium | 6 |
| low | 2 |

---

## 4. Findings-Übersicht

| ID | Titel | Severity | Status | Effort |
|---|---|---|---|---|
| SEC-010 | OAuth State nicht single-use | critical | open | M |
| OBS-002 | Mask error details fehlt | high | open | S |
| ARCH-006 | Tool-Granularität zu fein | high | open | L |
| SDK-004 | CORS Mcp-Session-Id nicht exposed | medium | open | S |

**Gesamt:** 4 Findings (1 critical, 2 high, 1 medium, 0 low)

---

## 5. Detail-Findings

*(Eines pro fehlgeschlagenem Check, vollständig nach `templates/finding.md`-Format. Hier nur Platzhalter.)*

### 5.1 SEC-010 — OAuth State nicht single-use

[Vollständiges Finding nach finding.md-Template]

### 5.2 OBS-002 — Mask error details fehlt

[Vollständiges Finding nach finding.md-Template]

*(usw. für alle weiteren Findings)*

---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **SEC-010** (critical, M) — Blockiert Production. Sofort fixen.
2. **OBS-002** (high, S) — Schnell-Win, direkt nach SEC-010.
3. **SDK-004** (medium, S) — Schnell-Win, kann parallel zu ARCH-006 laufen.
4. **ARCH-006** (high, L) — Architekturelle Refaktorierung. Nächster Sprint.

### Effort-Aggregation

| Severity | Anzahl | Total Effort |
|---|---|---|
| critical | 1 | M (1–3d) |
| high | 2 | L+S = ~1.5 Wochen |
| medium | 1 | S |
| **Gesamt** | **4** | **~2 Wochen** |

### Empfohlene Sprint-Verteilung

| Sprint | Findings |
|---|---|
| Sprint N (aktuell) | SEC-010, OBS-002, SDK-004 |
| Sprint N+1 | ARCH-006 (Refactoring) |

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|
| Skill-Version | mcp-audit v0.1.0 |
| Check-Katalog-Version | 2026-04 |
| Audit-Methodik | siehe `SKILL.md` |
| Tools verwendet | grep, AST-Analyse, manueller Code-Review |
| Audit-Dauer | ca. X Stunden |
| Re-Audit empfohlen nach | Remediation oder 6 Monate, was zuerst eintritt |

---

## 8. Zusatz: nicht-anwendbare Kategorien

Folgende Kategorien wurden nicht geprüft, da nicht anwendbar:

- **HITL** — Server hat `read-only`-Schreibzugriff, kein Sampling, kein Human-in-the-Loop nötig.
- **CH (Schweiz-Compliance)** — Datenklasse `Public Open Data` ohne PII, DSG/EDÖB-Checks nicht relevant.

Sollten sich diese Profilfaktoren ändern (z.B. Erweiterung um schreibende Tools oder Verarbeitung von Personendaten), ist ein Re-Audit zwingend.

---

## 9. Sign-Off

- [ ] Auditor bestätigt: alle anwendbaren Checks ausgeführt
- [ ] Auditor bestätigt: Findings im Audit Tracker erfasst
- [ ] Server-Maintainer bestätigt: Findings akzeptiert / Remediation-Plan akzeptiert
- [ ] (optional) GL/KI-Fachgruppe Sign-Off bei Datenklasse `Verwaltungsdaten` oder höher

---

*Ende des Audit-Reports.*
