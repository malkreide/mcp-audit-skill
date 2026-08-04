# Re-Audit-Warteschlange

**Stand:** 2026-08-04 · **Auslösendes Release:** `v2.0.0` · **Regel:** [`SKILL.md` §5](../SKILL.md#versionierung-des-check-katalogs)

Diese Datei beantwortet eine Frage: **Welche bestandenen Audits gelten nicht mehr, und warum?**

Sie ist bewusst eine Momentaufnahme mit Datum und keine gepflegte Liste. Ein Dokument, das vorgibt, immer aktuell zu sein, ist nach dem zweiten Release falsch, ohne dass es jemand merkt. Der maschinelle Stand steht im Notion-Tracker (`Audit-Status`); hier steht die **Begründung**, die dort nicht hinpasst.

---

## Warum überhaupt

§5 nennt fünf Auslöser, unter denen ein bestehendes Audit-Ergebnis nicht mehr gilt. Mit `v2.0.0` haben zwei davon gefeuert, und ein dritter wird beim Abschluss der Migrationswellen feuern.

| Auslöser | Was passiert ist | Reichweite |
|---|---|---|
| **§5c** — Prüfkriterium korrigiert | `OBS-001` führte «Schema-Mismatch» als Protocol Error. SEP-1303 verlangt seit `2025-11-25` das Gegenteil. | `applies_when: always` → **alle 42 Server** |
| **§5c** — Prüfkriterium korrigiert | `SEC-003` kannte den `.well-known`-Discovery-Weg nach RFC 9728 nicht (SEP-985). | `auth_model != "none"` → **4 Server** (`API-Key`), plus 1 mit ungesetztem Feld |
| **§5d** — Adoptionsstufe promoviert | Die vierzehn Migrations-Checks sind heute `advisory` und blockieren nicht. | **noch nicht gefeuert** — feuert beim Abschluss von Welle D |
| **§5e** — Baseline gewechselt | Ein Server, der auf `2026-07-28` migriert, wird gegen eine teilweise andere Katalogmenge gemessen. | **pro Server, bei seiner Migration** |

Dazu, ohne eigenen §5-Auslöser zu sein: **Der `catalog_hash` hat sich bewegt.** Jeder Trendvergleich gegen einen Vorlauf vor `v2.0.0` ist nach §6.2 nicht mehr vergleichbar. `aggregate_results.py` meldet das von selbst — der Report druckt dann die beiden Epochen und keinen Pfeil.

### Was **nicht** in dieser Liste steht, und warum

Die vierzehn neuen Checks für `2026-07-28` lösen **kein** §5b aus. §5b greift, wenn ein blockierender Check Server erreicht, die vorher nicht dagegen gemessen wurden — die vierzehn sind `advisory` und blockieren nichts. Sie erzeugen Findings, die gezählt und im Report genannt werden, aber kein Verdikt kippen. Erst ihre Promotion ist ein Auslöser, und die ist §5d.

Der Unterschied ist nicht formal: Würde man sie hier aufführen, stünden 42 Server unter einem Auslöser, den es nicht gibt, und die beiden echten Gründe gingen darin unter.

---

## Reihenfolge

Alle 42 stehen unter §5c, also entscheidet nicht das *Ob*, sondern das *Wann*. Drei Stufen, absteigend nach dem, was ein falsches `pass` gekostet haben kann:

### Stufe 1 — `OBS-001` **und** `SEC-003` betroffen (4 Server)

Server mit `auth_model: API-Key`. Beide Korrekturen greifen; `SEC-003` betrifft die Auffindbarkeit des Autorisierungsservers.

Aus dem Tracker zu ziehen:

```
Auth-Modell = API-Key
```

### Stufe 2 — Audit gegen einen überholten Katalogstand (2 Server)

| Server | Warum |
|---|---|
| `lindas-mcp` | Lauf vom 2026-07-26 mit Skill `1.0.0` gegen **68** Checks. Die Kategorien `FID`, `IDENT`, `DRIFT`, `DEP` gab es damals nicht — 30 Prüfdimensionen wurden nie gestellt. |
| `swiss-housing-mcp` | Derselbe Katalogstand, und der Report nennt **weder Audit-Datum noch Catalog-Version**. Ohne `catalog_hash` ist nicht feststellbar, wogegen gemessen wurde; nach §«Woran ein Lauf hängt» ist das kein verwertbarer Audit-Trail. Ausserdem 21 von 32 Checks `partial` bei `production_ready: YES`. |

Beide standen bis zum 2026-08-04 **gar nicht im Tracker**, obwohl sie im Index (`portfolio.json`, `scope: core`, `audit: published`) geführt sind. Das ist die Lücke, für die `--verify-inventory` gebaut wurde, eine Ebene höher: Das Gate prüft Server gegen `portfolio.yaml`, aber niemand prüfte `portfolio.yaml` gegen den Index.

### Stufe 3 — der Rest (36 Server)

`OBS-001` allein. Beim nächsten ohnehin anstehenden Anlass mitnehmen — Refactoring, Migrationswelle, geplantes Re-Audit. §5 verlangt ausdrücklich **kein** automatisches Reaudit aller Server.

### Nicht in der Warteschlange

| Server | Status | Grund |
|---|---|---|
| `i14y-mcp` | Triagiert | Noch nie auditiert — es gibt kein Ergebnis, das ungültig werden könnte. |
| `amtsblatt-mcp`, `swiss-procurement-mcp` | Findings dokumentiert | Audit läuft noch; die Korrekturen greifen im laufenden Verfahren. |
| `swiss-geodata-mcp` | archiviert | Unberührt. |
| `MCP-Server-for-patent-research-` | legacy, archiviert | Unberührt. |

---

## Was beim Re-Audit anders ist als beim letzten Mal

1. **`mcp_spec_version` ist Pflicht.** Ohne das Feld stoppt `validate_profile.py` vor Schritt 2. Für nicht migrierte Server ist der Wert `2025-11-25`.
2. **Der Applicability-Report nennt Baseline-Ausfälle namentlich.** Bei einem `2025-11-25`-Profil fallen 11 Checks als `baseline-mismatch` weg — das ist erwartet und kein Fehler.
3. **Der Vergleich mit dem Vorlauf ist abgeschnitten.** Andere Katalog-Epoche; `aggregate_results.py` sagt es im Report.
4. **Die vierzehn Migrations-Checks laufen mit und blockieren nicht.** Ihre Findings erscheinen unter `advisory_findings` — namentlich, auch bei grünem Verdikt. Wer später promoviert, weiss vorher, was rot würde.

---

## Herkunft der Zahlen

Nach `SKILL.md` §4.1 — eine abgeleitete Zahl speist kein Gate:

| Zahl | Herkunft |
|---|---|
| 42 Server im Tracker | **gemessen** — `SELECT COUNT(*)` gegen den Notion-Tracker, 2026-08-04 |
| 4 mit `auth_model: API-Key` | **gemessen** — `GROUP BY "Auth-Modell"`; dazu 37 × `none`, 1 × ungesetzt |
| `OBS-001` trifft alle | **abgeleitet** — `applies_when: always` im Katalog |
| `SEC-003` trifft 4 (+1) | **abgeleitet** — `applies_when: auth_model != "none"`; der ungesetzte Eintrag ist unentschieden, nicht ausgeschlossen |
| Katalogstand der zwei Stufe-2-Audits | **gemessen** — `audit-meta.json` bzw. Report-Kopf im jeweiligen Repo |

Der eine Server mit ungesetztem `Auth-Modell` steht bewusst als «+1» und nicht in der 4: Ein leeres Feld ist keine Antwort, und ihn stillschweigend zu `none` zu zählen wäre genau der Fehler, den `SEC-003` gerade wegen einer unvollständigen Prüfung bekommen hat.
