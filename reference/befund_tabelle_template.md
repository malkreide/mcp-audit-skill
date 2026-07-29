# Befund-Tabelle — Live-Probe `{datenquelle-name}`

**Datum:** {YYYY-MM-DD}
**Probender:** {Name}
**Datenquelle:** `{https://...}`
**Dokumentation:** `{URL zur OpenAPI / Datenmodell}`
**Lizenz:** {CC BY / CC BY-SA / OGD-CH / proprietary}

---

## Homepage-Claim vs. Live-Realität

| Behauptet auf Homepage | Live ermittelt | Abweichung? |
|---|---|---|
| z. B. "246 Parlamentarier:innen" | 245 via Dump, 0 via API | ⚠️ API defekt |
| | | |

## Endpoint-Matrix

| Endpoint | HTTP | Status | Records | Bemerkung |
|---|---|---|---|---|
| `/table/X/list` | 200 | ✅ | 139 | wie dokumentiert |
| `/table/Y/list` | 200 | ⚠️ leer | 0 | SQL-Filter zu restriktiv |
| `/table/Z/id/1` | 404 | ❌ | – | Doku veraltet |
| `/search/default/Foo` | 200 | ✅ | ~5 | |
| Bulk-Dump (JSON) | 200 | ✅ | 17 MB | wöchentlich Montag früh |

## Default-Matrix — was bedeutet Weglassen? (Schritt 1.2b)

Eine Zeile pro **optionalem** Parameter jedes genutzten Endpoints. Quelle ist die
Parameterbeschreibung der Spec, Beweis ist das gemessene Recall-Delta.

| Parameter | Spec sagt | Delta (weggelassen → maximal) | Bedeutung | Server sendet explizit? |
|---|---|---|---|---|
| `ClassificationIds` | «default set (=VARIA)» | 0 → 3 | ⚠️ 1 von 23 Sachgebieten | ✅ voller Satz |
| `MaxEntryCount` | «Default: 25» | 25 → 140 | ⚠️ stille Kürzung | ✅ immer explizit |
| `OutLanguageCode` | additive Zielsprache | 12 → 12 | ✅ kein Filter | n/a |
| | | | | |

**Boolesche Flag-Gruppen** (`Field.*`, `include_*`): Werden nur einzelne Mitglieder
gesendet, behalten die übrigen ihren Server-Default — das Argument kann dann nur
erweitern, nie einschränken. Gegenprobe mit explizitem `false` durchgeführt? ☐

## Recall-Ground-Truth gegen die offizielle Oberfläche (Schritt 1.4b)

Nur für Such-/Query-Endpoints. Beide Oberflächen am selben Tag abfragen.
Nicht den Anchor-Demo-Query verwenden — der funktioniert immer.

| Referenzbegriff | Typ | Web-UI | API | Delta | Erklärung |
|---|---|---:|---:|---:|---|
| z. B. `Pensionskasse` | viele Treffer | 25 (gekürzt) | 28 | +3 | UI-Anzeige gekürzt |
| z. B. `Quellensteuer` | Kompositum | 12 | 7 | −5 | UI zählt Benennungen, API Entries |
| z. B. `Bundeskanzlei` | wenige Treffer | 4 | 4 | 0 | — |

Jedes Delta braucht eine Erklärung. **«Weiss ich nicht» ist ein offener Befund** und
gehört unter «Blocker / Escalation», nicht in den Papierkorb.

Recall-Canary als `@pytest.mark.live`-Test mit Untergrenzen angelegt? ☐

## Datenstruktur-Findings

**Feld-Überraschungen** (z. B. Bool-Kodierung, Timestamp-Format, Nested-vs-Flat):

- ...
- ...

**Fehlende Relationen** (z. B. Branche im Essential-Dump nicht nested):

- ...

## Architektur-Empfehlung

**Gewählt: ARCH {A|B|C}**

Begründung:
- ...

## Blocker / Escalation

- ...

## Nächste Schritte

- [ ] Scaffold via `github-repo`-Skill bauen
- [ ] Anchor Demo Query definieren: *"..."*
- [ ] README-Abschnitt «Architecture decision» schreiben
- [ ] Default-Matrix und Recall-Ground-Truth ins README unter «Known Limitations»
- [ ] Recall-Canary als Live-Test festschreiben
- [ ] Notion-Portfolio-Karte anlegen
