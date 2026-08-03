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

## Abdeckungs-Matrix — was bleibt unerreichbar? (Schritt 1.3b)

Zeilen aus der **Bestandsachse der Quelle** (Rubriken / Typen / Register / Themen),
vollständig enumeriert — nicht aus der geplanten Tool-Liste abgeleitet. Die Tools
werden hineinmarkiert, nicht umgekehrt.

| Bestandsteil | in der Quelle | über geplante Tools | Beleg | Grund |
|---|---:|---|---|---|
| z. B. Handelsregister-Meldungen | 812'000 | ✅ | `/search?rubric=HR`, 200 | Kern der Anchor-Query |
| z. B. Konkurse | 96'000 | ❌ | Rubrik enumeriert, kein Tool | bewusst ausserhalb Scope (Phase 1) |
| z. B. Baugesuche | 41'000 | ❌ | Rubrik enumeriert, kein Tool | bewusst ausserhalb Scope |
| z. B. Betreibungen | ? | ❌ | Auth nötig (401) | technisch nicht erreichbar |
| | | | | |

Zulässige Gründe für ein ❌: **bewusst ausserhalb des Scopes** (mit Grund) /
**technisch nicht erreichbar** (kein Endpoint, Auth, Lizenz) / **noch offen**
(= offener Befund). Eine Zeile ohne Grund ist keine Zeile.

Diese Tabelle ist die Quelle für den Scope-Absatz im Architektur-Entscheid (2.3).
Wer den Scope später begründet, zitiert von hier — nicht aus dem Gedächtnis.

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

## Widening-Messung (Schritt 1.5)

Nur nötig, wenn ein Tool bei null Treffern den Suchbegriff verkürzen soll. Pro
Testbegriff jede Präfixlänge einmal abfragen (`widening_probe` im
`probe_template.sh`) und das kürzeste Präfix mit Treffern eintragen. Die unterste
Stufe der Staffel kommt aus dieser Spalte, nicht aus einem Prozentsatz.

| Testbegriff | Länge | kürzestes Präfix mit Treffern | Treffer | Morphemgrenze | Wildcard-Alternative | Präzision kippt ab |
|---|---:|---|---:|---|---|---|
| z. B. `Betonsanierungsarbeiten` | 23 | `Beton` (5) | 143 | ✅ | `Beton*` → 143 | `Bet` (3) → 4'100 |
| z. B. `Gebäudeversicherung` | 19 | `Gebäude` (7) | 88 | ✅ | `Gebäude*` → 88 | |
| | | | | | | |

Liefert die Wildcard-Spalte dasselbe Ergebnis in einem Aufruf, ist die Staffel ein
Workaround für eine vorhandene Funktion — dann Wildcard statt Widening.

Gemessene unterste Stufe als Kommentar am Code (mit Begriff und Datum)? ☐
Live-Test, der den gemessenen Begriff über die Staffel schickt? ☐

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
- [ ] README-Abschnitt «Architecture decision» schreiben, inkl. Scope-Absatz aus der Abdeckungs-Matrix
- [ ] Default-Matrix, Abdeckungs-Matrix und Recall-Ground-Truth ins README unter «Known Limitations»
- [ ] Recall-Canary als Live-Test festschreiben
- [ ] Widening-Staffel auf die gemessene unterste Stufe setzen (falls Widening gebaut wird)
- [ ] Notion-Portfolio-Karte anlegen
