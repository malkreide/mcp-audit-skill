# Re-Audit-Warteschlange

**Stand:** 2026-08-07 · **Letztes geprüftes Release:** `v2.2.0` (feuert nichts) · **Jüngste offene Auslöser:** `v2.1.0` · **Regel:** [`SKILL.md` §5](../SKILL.md#versionierung-des-check-katalogs)

---

## Unreleased — `FID-006` übernimmt die Feldnamen, `DRIFT-007` zurückgezogen

### Was gefeuert hat

| Auslöser | §5-Prüfung | Ergebnis |
|---|---|---|
| **`DRIFT-007` zurückgezogen** | Der Check war nie in einem Release — er stand vier Tage unter `[Unreleased]`. Es existiert kein Audit, das gegen ihn gemessen hat, also auch keins, das ungültig werden könnte. Unabhängig davon nennt §5b die Gegenrichtung (Reichweite verengt) ausdrücklich als CHANGELOG-Sache und nicht als Warteschlangen-Sache. | **feuert nicht** |
| **§5c** — `FID-006` bekommt Kriterien zu Feldnamen | Der Check wies bisher einen Server als bestanden aus, der die Antwortstruktur bestätigt **und** die Schreibweise fest verdrahtet. Genau diese Kombination hat im Belegfall vier von sechs Datensätzen still ausfallen lassen. Das ist «ein Kriterium, das am Ziel vorbeiging» — §5c im Wortlaut. | **feuert — kippt kein Verdikt** |

### Warum der zweite Eintrag kein Verdikt kippt

`FID-006` ist `advisory`. Er meldet und urteilt nicht; kein `production_ready: true` stützt sich darauf, dass sein Finding folgenlos blieb — dieselbe Begründung wie bei den vierzehn Migrations-Checks in `v2.0.0` weiter unten. Was sich ändert, ist der Inhalt künftiger Findings, nicht die Gültigkeit vergangener Verdikte.

Der Eintrag steht trotzdem hier, weil §5c gefeuert hat. Ein Auslöser, der geprüft und für folgenlos befunden wurde, ist von einem nicht geprüften Auslöser nur unterscheidbar, wenn er aufgeschrieben ist — derselbe Grund, aus dem `v2.2.0` weiter unten einen Abschnitt hat, in dem nichts feuert.

**Wen es beträfe, wenn der Check enforced wäre:** jeden Server, dessen Audit `FID-006` seit `v2.1.0` (2026-08-07) als `pass` geführt hat, ohne dass die Schreibweise gegen die echte Antwort gehalten wurde. Das Fenster ist kürzer als 24 Stunden. Wie viele Audits darin liegen, ist von hier aus **nicht gemessen** — die Audit-Ergebnisse liegen in den Server-Repos und im Notion-Tracker, nicht in diesem Repo. Bei der Promotion auf `enforced` (§5d) ist genau das die Zahl, die erhoben werden muss.

### Der scharfe Durchlauf, 2026-08-07

Gemessen über alle 43 Repos, **42 anwendbar** — `swiss-public-data-mcp` hat keine `pyproject.toml` und keinen Server, das ist das Portfolio-Meta-Repo.

| Hälfte A — Struktur bestätigen | von 42 |
|---|---:|
| lesen den Wurzelpfad mindestens einmal mit stillem Default (`.get("result", {})`) | **28** |
| bestätigen den Wurzelpfad irgendwo mit einem Raise | 3 |
| tragen einen eigenen **Struktur**-Fehlertyp | **0** |
| bestätigen die gelesenen Felder auf dem ersten Eintrag | **0** |
| halten die Struktur in einem Test gegen die echte Antwort | 1 |
| **erfüllen die Hälfte vollständig** | **0** |

| Hälfte B — Feldnamen | von 42 |
|---|---:|
| verdrahten mindestens einen gemischt geschriebenen Feldnamen fest | **28** |
| lesen nur kleingeschriebene Namen — die Frage beisst heute nicht | 13 |
| normalisieren an der Parse-Grenze | **1** (`zh-education-mcp`) |
| halten Feldnamen gegen die echte Antwort | **0** |

**Das ist 0 von 42, nicht ein Rückstand.** `ARCH-014` blieb `enforced`, weil sechs benannte Server mit je derselben dreizeiligen Behebung ein bewusst akzeptierter Rückstand sind (§2.3 Schritt 3). Hier ist es das ganze Portfolio, und ein Gate, das jeden Server rot färbt, wird abgeschaltet statt befolgt — genau die Form, gegen die §2.3 existiert. `FID-006` bleibt `advisory`.

**Was der Durchlauf über das Kriterium selbst sagt.** Es ist schneidbar, und das war die offene Frage. Acht Server sprechen mit CKAN, alle prüfen das `success`-Envelope — und dann trennen sie sich in einer Zeile: `zurich-opendata-mcp` schreibt `data["result"]` und scheitert laut, die anderen sieben schreiben `data.get("result", {})` und machen aus einer Formänderung eine Leermenge. Ein Kriterium, das diese beiden nicht auseinanderhält, wäre nicht durchsetzbar. Dieses tut es.

**Zwei Funde, die nur das Lesen von Hand ergeben hat:**

- `swisstopo-mcp` liest dasselbe Feld als `identDN` **und** `IdentDN`. **Beim Nachlesen korrigiert:** Der Server fängt beide Schreibweisen bereits ab — das ist kein stiller Ausfall und nicht die BISTA-Form, sondern eine handgeschriebene Alternation je Lesestelle über vier Felder. Der Befund bleibt einer, aber ein anderer: Die Quelle hält ihre Schreibweise nicht stabil, und die Antwort darauf gehört an die Parse-Grenze statt an jede Lesestelle. Behoben am 2026-08-07.
- `swiss-courts-mcp` hat die Fehlerklasse unabhängig erkannt und benannt. `UpstreamBlockedError` fängt den Bot-Schutz von entscheidsuche.ch, der mit **HTTP 200** und einem anderen JSON antwortet; der Docstring sagt: «Ohne Erkennung läse sich das wie `total == 0` (stille Leere).» Das ist `FID-006` in eigenen Worten, geschrieben ohne den Check.

### Nachgemessen nach dem CKAN-Sweep (2026-08-07, später am Tag)

Sieben Server wurden repariert — `wsl-envidat-mcp`, `swiss-energy-mcp`, `swiss-electricity-mcp`, `swiss-democracy-mcp`, `swiss-transport-mcp`, `swiss-cultural-heritage-mcp`, `seco-labor-mcp`. Alle acht CKAN-Server bestätigen ihren Wurzelpfad jetzt.

| | Erhebung | jetzt |
|---|---:|---:|
| mit mindestens einem stillen Root-Default | 28 | **27** |
| mit eigenem **Struktur**-Fehlertyp | 0 | **7** |
| Wurzelpfad irgendwo mit einem Raise bestätigt | 3 | **10** |
| **erfüllen den Check** | 0 | **0** |

**Sieben Reparaturen, eine Zahl Bewegung — und das ist die Aussage, nicht die Enttäuschung.** Nur `swiss-democracy-mcp` hat seinen **letzten** stillen Default verloren. Die übrigen sechs bedienen weitere Quellen mit demselben Idiom: GeoAdmin `find`/`identify` in `swiss-energy-mcp`, AMSTAT-Zeilen in `seco-labor-mcp`, die Ebene unter dem bestätigten `result` in `wsl-envidat-mcp`. Eine Kohorte zu reparieren repariert **einen Pfad**, nicht **einen Server** — und die Gesamtzahl misst Server.

Der Check bleibt damit auf 0 von 42 und `advisory`. Die beiden Kriterien, die niemand erfüllt, hat der Sweep nicht angefasst: die gelesenen Felder auf dem ersten Eintrag bestätigen, und Struktur oder Feldnamen gegen eine **echte** Antwort halten.

**Das Messwerkzeug hat die Reparatur nicht gesehen.** `tools/sweeps/fid006_sweep.py` meldete nach dem Sweep unverändert 13 Repos mit einem Wurzelpfad-Guard. Ursache: Seine Taint-Analyse beginnt am Parse-Aufruf, die neuen Bestätigungen sitzen aber in Helfern, die die Antwort als *Parameter* bekommen — derselbe Helfer-Blindfleck, der in diesem Portfolio schon zweimal zugeschlagen hat. Die Zahl **10** ist von Hand ausgezählt (drei aus der Erhebung plus die sieben reparierten, jeweils Klasse **und** Aufrufstelle geprüft). Die Einschränkung steht jetzt im Kopf des Skripts.

**Und eine zweite Messfalle, dieselbe Klasse.** Die erste Nachmessung ergab unverändert 28 — weil die Reparatur ihre eigene Begründung mitbringt: Die neuen Docstrings zitieren `data.get("result", {})` wörtlich, und ein Textzähler liest das als unveränderten Befund. Erst mit entfernten Kommentaren und Docstrings kommt 27 heraus. Dieselbe Falle wie beim `OPS-009`-Zähler und beim Quelltext-Test in `swiss-transport-mcp`.

### Zweite Nachmessung, nach der Fremdquellen-Nachlese (2026-08-07)

Fünf weitere PRs: `swiss-energy-mcp` (GeoAdmin `identify`/`find`), `swiss-electricity-mcp` (LINDAS SPARQL), `swiss-cultural-heritage-mcp` (Dodis Solr) — plus die zwei Ebenen unter dem bereits bestätigten CKAN-`result` in `wsl-envidat-mcp` und `swiss-transport-mcp`. Dazu `swisstopo-mcp` mit der Schreibweisen-Normalisierung.

| | Erhebung | nach dem CKAN-Sweep | jetzt |
|---|---:|---:|---:|
| mit mindestens einem stillen Root-Default | 28 | 27 | **25** |
| mit eigenem **Struktur**-Fehlertyp | 0 | 7 | 7 |
| Wurzelpfad irgendwo mit einem Raise bestätigt | 3 | 10 | 10 |
| normalisieren an der Parse-Grenze | 1 | 1 | **2** |
| **erfüllen den Check** | 0 | 0 | **0** |

**Drei Runden, drei Server Bewegung.** `wsl-envidat-mcp` und `swiss-transport-mcp` haben ihren letzten stillen Default verloren, `swiss-democracy-mcp` schon in der Runde davor. Die anderen bedienen weitere Quellen mit demselben Idiom.

**Der Fehler wandert nach unten.** Zwei der sieben Fundstellen dieser Runde waren Reste des CKAN-Sweeps selbst: Der Fix bestätigte `result` und hörte dort auf, während die Formatierer eine Ebene tiefer weiterlasen. Wer eine Ebene schliesst, sollte die nächste mitprüfen — das ist die Lehre, die in den nächsten Durchlauf gehört.

**Und die Trefferquote des Scans ist ausdrücklich schlecht.** 17 Fundstellen wurden nachgelesen, **7** waren echte Befunde, **10** keine: ein `error`-Zweig im eigenen Aggregat (`swiss-cultural-heritage`), ein echtes Optionalfeld einer CKAN-Zeile (`swiss-electricity`), das eigene Ergebnis-Dict (`seco-labor`), eine bereits bestätigte Struktur (`swiss-energy`). Ein Default ist nur dort ein Fehler, wo die Abwesenheit ein Irrtum des Lesers ist und keine Aussage der Quelle. Ein Scan, der 10 von 17 falsch anklagt, ist als Leseliste brauchbar und als Urteil unbrauchbar.

### Herkunft der Zahlen

| Zahl | Herkunft |
|---|---|
| 43 Repos gescannt, 42 anwendbar | **gemessen** — alle nicht-archivierten `*-mcp`-Repos unter `malkreide`, frisch gezogen am 2026-08-07 |
| 28 / 3 / 0 / 0 / 1 (Hälfte A) und 28 / 13 / 1 / 0 (Hälfte B) | **gemessen** — AST-Lauf ab der Parse-Grenze über Funktionsgrenzen hinweg, jede Einstufung von Hand nachgelesen |
| 0 eigene Struktur-Fehlertypen | **gemessen** — die 13 `Upstream*Error`-Klassen von Hand gelesen; alle betreffen Erreichbarkeit («unreachable after all retries», «budget was gone»), keine die Form |
| 8 CSV-Server, 7 fest verdrahtet, 1 normalisiert | **bestätigt** — die aus `DRIFT-007` übernommene Zahl hält dem Durchlauf stand |
| 27 / 7 / 10 nach dem Sweep | **gemessen** — Kommentare und Docstrings entfernt, sonst zählt die Begründung der Reparatur als Befund; die 10 von Hand ausgezählt, weil das Werkzeug Bestätigungen in Helfern nicht sieht |
| 25 / 7 / 10 / 2 nach der Nachlese | **gemessen** — dasselbe Verfahren; 7 von 17 Fundstellen als echte Befunde von Hand bestätigt, 10 verworfen und je Repo im PR benannt |
| 4 von 6 Endpunkten schreiben klein, 2 gross, 2 mischen innerhalb der Kopfzeile | **übernommen** aus dem `DRIFT-007`-Text vom 2026-08-03, dort am Belegfall erhoben |
| Audits mit `FID-006: pass` im Fenster seit `v2.1.0` | **nicht gemessen** — von diesem Repo aus nicht erhebbar |

**Drei Korrekturen am Messwerkzeug, jede hat die Zahlen bewegt** — sie stehen im Kopf von `fid006_ast.py` und gehören hierher, weil eine Zahl ohne ihre Fehlversuche nicht nachvollziehbar ist:

1. Ein Zeilen-Grep setzte ein Dutzend Repos wegen `scripts/check_version_sync.py` auf die Leseliste — ein Skript, das eine Lockfile liest, ist kein Server, der seine Quelle liest.
2. Argument-Validierung zählte als bestätigter Wurzelpfad. `if not search_term.strip(): raise` sagt nichts über die Form, die ankam.
3. Taint nur innerhalb einer Funktion sah in neunzehn Repos «kein einziger Feldzugriff». Die vorherrschende Form hier ist ein `_get_json()`-Helfer, der `resp.json()` zurückgibt, während die Aufrufer die Felder lesen — gemessen wurde der Helfer, der nichts liest.

---

## Unreleased — `ARCH-014`, Klarstellung zur Abwesenheit

### Was gefeuert hat

| Auslöser | §5-Prüfung | Ergebnis |
|---|---|---|
| **Die Abwesenheitsregel** — ein Server ohne Wiederholungspfad besteht `ARCH-014` | §5 kennt keinen Auslöser für eine **Lockerung**. Die Regel verwandelt mögliche `fail` in `pass`; sie kann kein `production_ready: true` ungültig machen, und genau das ist es, wogegen §5 schützt. | **feuert nicht** |
| **§5b/c** — Reichweite des Transport-Kriteriums präzisiert | «Transport-Retries stehen nachweislich auf null» galt bisher erkennbar für Server **mit** eigener Schleife. Es gilt jetzt ausdrücklich auch für Server **ohne** — dort kippt ein gesetzter Wert das Verdikt von `pass` auf `fail`. Das ist eine echte Verschärfung. | **feuert — trifft heute niemanden** |

### Warum der zweite Eintrag trotzdem hier steht

Gemessen am 2026-08-07 über alle 43 Portfolio-Server: **15** haben keinen Wiederholungspfad, und **keiner von ihnen** setzt Transport-Retries. Der Auslöser feuert also gegen eine leere Menge.

Das gehört hierher und nicht in die Erledigt-Ablage — derselbe Fall wie `FID-003` in `v2.1.0`. Der Unterschied zwischen «geprüft und niemand betroffen» und «nicht geprüft» ist der, den [`SKILL.md` §2.6](../SKILL.md) eine Ebene höher meint. Wer einen Server baut oder erbt, der `httpx.AsyncHTTPTransport(retries=3)` setzt und sonst nichts wiederholt, prüft `ARCH-014` in demselben Zug mit.

### Was der Durchlauf sonst geändert hat, ohne §5 zu sein

Die Zahlen im Check selbst. Die Promotion vom 2026-08-03 stützte sich auf «alle elf Server erfüllen den Check heute» — elf war eine **Stichprobe**, das Portfolio hat 43. Der Durchlauf sagt: 22 erfüllen ihn mit einer Politik, 15 haben keinen Pfad (nach der neuen Regel `pass`), und **sechs** verletzen ihn.

`amtsblatt-mcp` · `bag-health-mcp` · `openlex-mcp` · `swiss-environment-mcp` · `swiss-statistics-mcp` · `zurich-opendata-mcp`

Das ist **kein** §5-Auslöser: Kein Kriterium hat sich für diese sechs bewegt, sie waren schon vorher verletzt, und ihre Audits sind dadurch nicht ungültig geworden — sie waren nie gültig. Es ist ein offener Rückstand, kein Re-Audit. Die Adoptionsstufe bleibt `enforced` und stützt sich damit nach [§2.3](../SKILL.md#23-adoptionsstufen) Schritt 3 auf «Rückstand bewusst akzeptiert» statt auf «die betroffenen Server haben nachgezogen». Der Unterschied steht jetzt im Check; ihn nicht zu schreiben wäre der Fehler aus `OPS-004` gewesen.

### Herkunft der Zahlen

| Zahl | Herkunft |
|---|---|
| 43 Server gescannt | **gemessen** — alle nicht-archivierten `*-mcp`-Repos unter `malkreide`, flach geklont, 2026-08-07 |
| 22 / 6 / 15 | **gemessen** — mechanischer Scan über `src/`, jeder Treffer **und** jeder Nicht-Treffer von Hand am Quelltext nachgelesen |
| 0 der 15 mit Transport-Retries | **gemessen** — `grep` auf `HTTPTransport(`, `urllib3`, `Retry(`, `max_retries`; alle Treffer waren der MCP-Transport, nicht der HTTP-Transport |
| 11 Server der Promotion | **übernommen** aus dem Check-Text vom 2026-08-03, dort erhoben |

Diese Datei beantwortet eine Frage: **Welche bestandenen Audits gelten nicht mehr, und warum?**

Sie ist bewusst eine Momentaufnahme mit Datum und keine gepflegte Liste. Ein Dokument, das vorgibt, immer aktuell zu sein, ist nach dem zweiten Release falsch, ohne dass es jemand merkt. Der maschinelle Stand steht im Notion-Tracker (`Audit-Status`); hier steht die **Begründung**, die dort nicht hinpasst.

**Mehrere Releases, eine Datei.** Die Auslöser aus `v2.1.0` und `v2.0.0` stehen unverändert weiter unten — sie sind nicht dadurch erledigt, dass ein neues Release erschienen ist. Ein Server, der wegen `OBS-001` in der Warteschlange stand und seither nicht reauditiert wurde, steht jetzt wegen `OBS-001` **und** `DEP-001` darin.

---

## `v2.2.0` — 2026-08-07

### Was gefeuert hat

**Nichts.** Dieser Abschnitt steht trotzdem hier, und das ist sein ganzer Zweck: Ein Release, das in dieser Datei gar nicht auftaucht, ist von einem Release ohne §5-Prüfung nicht zu unterscheiden. Der Unterschied zwischen «geprüft und niemand betroffen» und «nicht geprüft» ist derselbe, den [`SKILL.md` §2.6](../SKILL.md) eine Ebene höher meint — und den `OPS-005` an Pipelines misst.

| Eintrag | §5-Prüfung | Ergebnis |
|---|---|---|
| `SEC-028` (`high`, `enforced`, **neu**) | Punkt **4** der Katalog-Versionierung, nicht Punkt 5: «Ein neuer Check ist ein neuer Vertrag. Bestehende Audits sind nicht rückwirkend ungültig.» Die vier Fälle a–d setzen sämtlich eine Änderung an einem **bestehenden** Check voraus — Severity (a), Reichweite (b), Prüfkriterium (c), Adoptionsstufe (d). Keiner trifft zu, weil es vorher nichts gab, das sich hätte ändern können. | feuert nicht |
| Ziel-Anker (`target_revision()`) | §5 regelt Änderungen am **Katalog**, nicht am Werkzeug. Keine Severity, keine Reichweite, kein Prüfkriterium hat sich bewegt. | feuert nicht |

### Was der Anker-Fix stattdessen bedeutet

Er trifft keine Audit-*Ergebnisse*, sondern Audit-*Anker* — und die Unterscheidung ist der Grund, warum er nicht in die Warteschlange gehört.

Ein Lauf, dessen `--target-repo` auf ein Verzeichnis **unterhalb** einer Repository-Wurzel zeigte, nennt in `audit-meta.json` eine SHA aus dem umgebenden Baum: vierzig Hexziffern, plausibel, und über ein anderes Repo. Die Befunde jenes Laufs bleiben, was sie waren; unbrauchbar ist die Angabe, *woran* sie hängen.

Nachprüfbar, ohne etwas neu zu auditieren:

```bash
git -C <target_repo> rev-parse --show-toplevel
```

Kommt ein anderer Pfad zurück als der, der als `--target-repo` übergeben wurde, ist der Anker jenes Laufs wertlos — der Report belegt dann nicht, woran er sich misst. Behebung ist ein neuer Lauf mit korrektem `--target-repo`, kein Re-Audit im Sinn von §5.

---

## `v2.1.0` — 2026-08-07

### Was gefeuert hat

| Auslöser | Was passiert ist | Reichweite |
|---|---|---|
| **§5c** — Prüfkriterium korrigiert | `DEP-001` verlangte eine Obergrenze und liess offen, **welche**. Neu wird sie gemessen: Modus 4a installiert und importiert die höchste vom Cap erlaubte Version, Modus 4b nimmt den Cap testweise weg und verlangt, dass der nächste Major hereinkommt. Ein `pass` von vorher belegt nur, dass ein Deckel dasteht. | `applies_when: always` → **alle 39 abgeschlossenen Audits** |
| **§5c** — Prüfkriterium korrigiert | `FID-003` kannte zwei Ausgänge; die Rückfrage (`resultType: "input_required"`) ist der dritte und sieht erfolgreich aus. Ein Server, der sie mit der Leermenge vermischt, hat bestanden, weil niemand danach gefragt hat. | `tools_make_external_requests == true` **und** Baseline `2026-07-28` → **noch niemand**, siehe unten |

### `FID-003` wartet, es ist nicht erledigt

Gemessen am 2026-08-07 steht **keiner** der 42 Server im Tracker auf `MCP-Spec-Version: 2026-07-28` — alle 42 auf `2025-11-25`. Der dritte Ausgang kann auf dieser Baseline nicht entstehen, also trifft der Auslöser heute niemanden.

Das ist derselbe Fall wie §5e in `v2.0.0`: ein Auslöser mit benanntem, aber noch nicht eingetretenem Ereignis. Er gehört hierher und **nicht** in die Erledigt-Ablage — der Unterschied zwischen «geprüft und niemand betroffen» und «nicht geprüft» ist genau der, den `SKILL.md` §2.6 eine Ebene höher meint. Wer einen Server auf `2026-07-28` migriert, prüft `FID-003` in demselben Zug mit; die Migration ist ohnehin schon ein §5e-Anlass.

### Der Sweep vom 2026-08-02 hat es nicht vorweggenommen

Naheliegender Einwand: Am 2026-08-02 lief ein Portfolio-Sweep gegen `DEP-001` — 28 Befunde über 24 Server, gedeckelte Abhängigkeiten 61 → 89, alle behoben. Ist damit nicht ohnehin alles frisch?

Nein, und der Grund ist der Kern dieses Auslösers: Der Sweep lief gegen das **alte** Kriterium — *ein Deckel ist da*. Genau die beiden Fragen, die dieses Release ergänzt, hat er nicht gestellt. Ein Repo, das im Sweep sauber wurde, hat einen Deckel, dessen Grenze ungemessen und dessen Wirkung ungeprüft ist. Der Sweep verkleinert die Warteschlange nicht; er hat die Vorbedingung geschaffen, gegen die jetzt gemessen werden kann.

### Reihenfolge

Anders als bei `v2.0.0` gibt es hier keine Stufen: `DEP-001` gilt `always` und trifft alle 39 gleich. Massgeblich ist deshalb der ohnehin nächste Anlass je Server — Refactoring, Migrationswelle, geplantes Re-Audit. §5 verlangt ausdrücklich **kein** automatisches Reaudit aller Server.

Wer nur einen Punkt herausgreifen will: **Modus 4b zuerst.** Ein Deckel ohne Wirkung ist im Diff von einem wirksamen nicht zu unterscheiden, und der Gegenversuch kostet einen Auflösungslauf ohne Cap.

### Nicht in der Warteschlange

| Server | Status | Grund |
|---|---|---|
| `amtsblatt-mcp`, `swiss-procurement-mcp` | Findings dokumentiert | Audit läuft; die verschärften Kriterien greifen im laufenden Verfahren, nicht rückwirkend. |
| `i14y-mcp` | Triagiert | Noch nie auditiert — es gibt kein Ergebnis, das ungültig werden könnte. |

### Herkunft der Zahlen

| Zahl | Herkunft |
|---|---|
| 42 Server im Tracker | **gemessen** — `GROUP BY "Audit-Status", "MCP-Spec-Version"` gegen den Notion-Tracker, 2026-08-07 |
| 39 abgeschlossene Audits | **gemessen** — dieselbe Abfrage: 39 × `Abgeschlossen`, 2 × `Findings dokumentiert`, 1 × `Triagiert` |
| 0 Server auf `2026-07-28` | **gemessen** — dieselbe Abfrage; alle 42 auf `2025-11-25` |
| `DEP-001` trifft alle | **abgeleitet** — `applies_when: always` im Katalog |
| `FID-003` trifft heute niemanden | **abgeleitet** aus der gemessenen Baseline-Verteilung plus der Bedingung im Kriterium |
| 28 Befunde / 24 Server / 61 → 89 | **übernommen** aus dem CHANGELOG-Eintrag zum Sweep vom 2026-08-02, dort gemessen |

---

## `v2.0.0` — 2026-08-04

*Weiterhin gültig, soweit die genannten Server seither nicht reauditiert wurden.*

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
