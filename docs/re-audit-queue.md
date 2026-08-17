# Re-Audit-Warteschlange

**Stand:** 2026-08-17 · **Letztes geprüftes Release:** `v3.0.0` (feuert nicht — der Katalog steht still) · **Jüngste offene Auslöser:** `v2.1.0`, dazu **§5e für 2 Server** (Migration 2026-07-29, releaseunabhängig) · **Regel:** [`SKILL.md` §5](../SKILL.md#versionierung-des-check-katalogs)

---

## `v3.0.0` — 2026-08-11 — der Katalog steht still, sein Fingerabdruck nicht

### Was gefeuert hat

**Nichts.** Derselbe Zweck wie beim leeren Abschnitt zu `v2.2.0` weiter unten: Ein Release, das hier gar nicht auftaucht, ist von einem Release ohne §5-Prüfung nicht zu unterscheiden. Bei einem **Major** wiegt das schwerer statt leichter — die Versionsnummer ist genau das Signal, bei dem jemand annimmt, es müsse etwas fällig sein.

| Auslöser | §5-Prüfung | Ergebnis |
|---|---|---|
| **a)** Severity angehoben | `severity` über alle 120 Checks unverändert gegenüber `v2.3.0` | **feuert nicht** |
| **b)** `applies_when` nach oben erweitert | `applies_when` über alle 120 unverändert | **feuert nicht** |
| **c)** Prüfkriterium korrigiert | sieben Check-Dateien geändert, neun Stellen — **keine** davon unter `## Pass Criteria` | **feuert nicht** |
| **d)** Adoptionsstufe promoviert | `adoption` bei allen 25 Checks, die das Feld tragen, unverändert | **feuert nicht** |
| **e)** Spec-Baseline verengt | `spec_baseline` bei allen 20 Checks, die es tragen, unverändert; [§2.7](../SKILL.md#27-spec-baseline-welcher-protokollstand-gemessen-wird) nicht angefasst | **feuert nicht** |
| Der Major-Bump selbst | §5 regelt Änderungen am **Katalog**. Bewegt hat sich das Repository darum herum: vier Skills statt einem, `tools/checks/` heisst `tools/suites/`, drei Herkunftsrepos archiviert. SemVer misst die Schnittstelle, §5 misst den Massstab — zwei verschiedene Gegenstände. | **feuert nicht** |

Kein Check ist dazugekommen und keiner weggefallen: 120 vor und 120 nach dem Release. Punkt **4** der Katalog-Versionierung — «ein neuer Check ist ein neuer Vertrag» — kommt damit gar nicht erst zum Zug.

### Was sich trotzdem bewegt hat, und wovon der CHANGELOG nichts sagt

**Der Katalog-Hash.** Die sieben geänderten Dateien haben alle denselben Anlass: Die drei Companion-Skills sind in diesen Baum gezogen, also zeigen ihre Verweise nicht mehr nach `github.com/malkreide/mcp-…-skill`, sondern nach `../skills/…`. Inhaltlich ist das nichts. Für [§6.2](../SKILL.md#62-vergleich-mit-dem-vorlauf-nur-innerhalb-einer-katalog-epoche) ist es alles:

| Stand | Katalog-Hash |
|---|---|
| `v2.3.0` | `2bbded9079fd2a69…` |
| `v3.0.0` (= heutiger `main`) | `d09a60316c75040a…` |

`hash_catalog()` hasht die **Dateien**, nicht die Kriterien, und das ist Absicht: Nicht zu wissen, ob der Massstab sich bewegt hat, ist nicht dasselbe wie zu wissen, dass er gleich blieb — die sichere Richtung ist die, die keine Linie zieht. Die Folge: **Jedes Audit gegen `v3.0.0` bekommt `comparable: false` gegen jeden Vorlauf aus der `v2.3.0`-Epoche.** Der Report druckt dann keine Delta-Tabelle, sondern beide Hashes und den Grund.

Das ist **kein** Re-Audit-Auslöser. Kein Verdikt wird ungültig, kein `production_ready: true` fällt, und in die Warteschlange gehört es nicht. Es kostet aber jedem Server beim nächsten Lauf seine Trendlinie — für sieben Links. Wer den fehlenden Vergleich im nächsten Report sieht, findet die Erklärung hier, statt sie im Server zu suchen.

Und es ist **wirksam, nicht theoretisch**: `mcp-continuous-auditor` zeigt in beiden READMEs auf `mcp-audit-skill/tree/v3.0.0`, gepinnt und von `tests/test_quality_chain_table.py` festgehalten. Der neue Hash ist der, gegen den das Portfolio ab jetzt misst.

### §5e, die Serverseite — für dieses Fenster gemessen

§5e nennt neben der Katalogseite den **Server**: Wechselt einer seine `mcp_spec_version`, ist das für sich ein Auslöser, ohne dass am Katalog etwas geändert sein muss. Für das Fenster **seit dem 2026-08-08** ist die Antwort **nein**, und zwar gemessen statt angenommen — über alle 43 Repos, jedes bis vor den 2026-08-08 zurück vertieft und gegen `HEAD` gehalten.

| Frage | Ergebnis |
|---|---|
| Änderung an einer Protokoll- oder Spec-Version seit dem 2026-08-08 | **keine**, über alle 43 Repos |
| Server, die heute den neuen Stand sprechen | **2** — `amtsblatt-mcp` und `swiss-procurement-mcp`, beide `MCP_PROTOCOL_VERSION = "2026-07-28"` |
| seit wann | beide **2026-07-29**, derselbe Anlass («migrate to mcp 2.x») — also **vor** dem Fenster |

**Gesucht wurde nach dem Feld- und Konstantennamen, nicht nach dem Wert**, und das ist hier kein Detail: `2026-07-28` ist in diesem Portfolio auch ein gewöhnliches Datum. `swiss-environment-mcp` trägt `LSV_VERIFIED_ON = "2026-07-28"` — ein Probendatum, kein Protokollstand. Ein Scan über die Zeichenkette hätte den Server als migriert gemeldet, und die Zahl in der Zeile darüber wäre **3** statt 2 gewesen.

### Zwei Server stehen unter §5e, und es stand nirgends

Der `v2.0.0`-Abschnitt weiter unten führt §5e als stehenden Auslöser mit der Reichweite «**pro Server, bei seiner Migration**». Beide oben genannten sind migriert, beide am 2026-07-29 — und in dieser Datei erscheinen sie bis heute nur einmal, unter «Nicht in der Warteschlange · Audit läuft noch». Der Auslöser hat also gefeuert und wurde nie aufgeschrieben.

Die Umstände machen es nicht kleiner, sondern grösser. Beide wurden am 2026-07-29 beziehungsweise 2026-07-30 zuletzt auditiert, also **nach** ihrer Migration — aber mit `skill_version: 1.0.0`, gegen einen Katalog, der die Baseline-Achse noch gar nicht kannte. §2.7 kam erst mit `v2.0.0`. Heute teilt `v3.0.0` den Katalog so:

| `spec_baseline` | Checks | für einen `2026-07-28`-Server |
|---|---:|---|
| `2025-11-25` | 5 | messen einen Gegenstand, den sein Protokoll **nicht mehr hat** |
| `2026-07-28` | 11 | wurden bei ihm **nie gestellt** |
| `beide`, ausgeschrieben | 4 | protokollunabhängig |
| Feld fehlt → Default `beide` | 100 | protokollunabhängig |

Die fünf sind `SCALE-002`, `SCALE-003`, `SCALE-007`, `SDK-004` und `SEC-009` — dieselben fünf, die §2.7 namentlich als verengt führt.

**Und die Zahl, die das erklärt:** **Kein einziges Audit im Portfolio führt `mcp_spec_version`.** 85 Läufe in 31 von 43 Repos, keiner mit dem Feld — weder in `profile.yaml` noch in `audit-meta.json`, `summary.json` oder `verification-results.json`. Der Grund ist die Zeit und nicht die Sorgfalt: Der jüngste Lauf im **ganzen** Portfolio datiert auf den **2026-07-30**, und die höchste aufgezeichnete `skill_version` ist **1.0.0**. Pflichtfeld ist `MCP-Spec-Version` seit `v2.0.0`. Es gibt im Portfolio also kein Audit, gegen das §5e sich überhaupt prüfen liesse — die Frage «hat der Server seit seinem letzten Audit gewechselt?» hat auf keiner Seite eine aufgezeichnete Antwort.

### Was auch jetzt nicht gemessen ist

Der **Notion-Tracker**. `MCP-Spec-Version` ist dort das Pflichtfeld, und was für die beiden migrierten Server darin steht, ist von hier aus nicht zu sehen. Der Code-Pin ist ein Beleg dafür, welches Protokoll ein Server spricht, und nicht dafür, was das Profil behauptet — auseinanderlaufen können sie.

Ein Nebenbefund dazu, gemessen: `portfolio.json` im Portfolio-Repo führt `current_mcp_spec_baseline: "2025-11-25"` als **eine** Zahl fürs ganze Portfolio, `last_checked: "2026-07-28"` — einen Tag vor der Migration. Seine 44 Server-Einträge tragen **kein** eigenes `mcp_spec_version`, obwohl `required_report_metadata` im selben Dokument es als Pflichtangabe jedes Reports nennt.

### Herkunft der Zahlen

| Zahl | Herkunft |
|---|---|
| 120 Checks vor und nach dem Release | **gemessen** — `git ls-tree -r --name-only <ref> -- checks/` auf `v2.3.0` und `HEAD`, `*.md` gezählt |
| 0 Abweichungen in `id`, `title`, `category`, `severity`, `applies_when`, `adoption`, `spec_baseline` | **gemessen** — Frontmatter beider Stände geparst und Feld für Feld verglichen |
| Gegenprobe zum leeren Ergebnis | **gemessen** — derselbe Parser findet auf `HEAD` 120× `severity` und `applies_when`, 25× `adoption`, 20× `spec_baseline`. Ohne diese Zahl wäre «keine Abweichung» von «kein Feld gelesen» nicht zu unterscheiden — der Fehler, den `OPS-010` an Tests misst |
| sieben Dateien, neun Stellen, keine unter Pass Criteria | **gemessen** — `git diff --name-status -M v2.3.0..HEAD -- checks/`, dann je Hunk die nächste Überschrift darüber: siebenmal `## References`, einmal `## Description` (`OPS-010`), einmal `### Modus 3` (`SEC-028`) |
| beide Katalog-Hashes | **gemessen** — `tools/audit_init.py::hash_catalog()` gegen die aus beiden Ständen ausgecheckten `checks/`-Bäume. `MANIFEST.txt` geht in beide Hashes ein und ist in beiden identisch, trägt zur Differenz also nichts bei |
| Pin des Auditors auf `v3.0.0` | **gemessen** — `mcp-continuous-auditor` bei `9749234`, vier Verweise je README |
| «kein Auslöser greift» | **unabhängig bestätigt** — der CHANGELOG-Eintrag zu `v3.0.0` sagt dasselbe. Die Zahlen oben sind daneben erhoben und nicht daraus abgeschrieben |
| 43 Repos, keine Spec-Änderung seit dem 2026-08-08 | **gemessen** — alle nicht-archivierten `*-mcp`-Repos unter `malkreide` flach geklont und bis vor den 2026-08-08 vertieft, dann `git diff <letzte Revision vor dem Stichtag>..HEAD` über `src/`, `pyproject.toml`, `README.md`, gefiltert auf die Feld- und Konstantennamen. Ein Treffer, und der ist ein README-Absatz in `swiss-cultural-heritage-mcp`, der ausdrücklich festhält, dass der Server die Aushandlung **nicht** übersteuert |
| 2 Server auf `2026-07-28` | **gemessen** — Konstanten-Scan über alle `*/src/`, jeder Treffer einzeln am Quelltext nachgelesen. Der dritte Treffer auf die Zeichenkette (`swiss-environment-mcp`, `LSV_VERIFIED_ON`) ist ein Probendatum und wurde deshalb **nicht** gezählt |
| Migrationsdatum 2026-07-29 | **gemessen** — `git log -S'MCP_PROTOCOL_VERSION' --all` in beiden Repos, bis zum einführenden Commit zurück (`e123539`, `4ed85f6`, beide «migrate to mcp 2.x») |
| 85 Läufe in 31 von 43 Repos, jüngster 2026-07-30 | **gemessen** — alle Verzeichnisse unter `*/audits/`, die dem Run-ID-Muster entsprechen; `skill_version` aus `audit-meta.json` |
| kein Lauf führt `mcp_spec_version` | **gemessen** — Suche nach dem **Feldnamen** (nicht dem Wert) in `profile.yaml`, `audit-meta.json`, `summary.json`, `verification-results.json` aller 85 Läufe. Die zwei Treffer auf `MCP-Spec-Version` im Portfolio sind Fliesstext in `ARCH-012`-Findings von `bakom-mcp`, kein Profilfeld |
| 5 / 11 / 4 / 100 Checks je Baseline | **gemessen** — Frontmatter aller 120 Checks auf `HEAD`; dieselbe Aufteilung steht schon seit `v2.0.0` |
| `portfolio.json`-Angaben | **gemessen** — `swiss-public-data-mcp/portfolio.json`, Stand des heutigen `HEAD` |

---

## `v2.3.0` — 2026-08-08 — `DRIFT-008`, ein Live-Test muss die Quelle erreichen

### Was gefeuert hat

| Auslöser | §5-Prüfung | Ergebnis |
|---|---|---|
| **`DRIFT-008` neu** (`high`, `advisory`) | Punkt **4** der Katalog-Versionierung, nicht Punkt 5: «Ein neuer Check ist ein neuer Vertrag. Bestehende Audits sind nicht rückwirkend ungültig.» Die vier Fälle a–d setzen sämtlich eine Änderung an einem **bestehenden** Check voraus — Severity, Reichweite, Prüfkriterium, Adoptionsstufe. Keiner trifft zu, weil es vorher nichts gab, das sich hätte ändern können. | **feuert nicht** |

Dieselbe Prüfung wie bei `SEC-028` in `v2.2.0` weiter unten, mit demselben Ergebnis. Der Abschnitt steht trotzdem hier: Ein neuer Check, der in dieser Datei gar nicht auftaucht, ist von einem ungeprüften nicht zu unterscheiden.

### Woher der Check kommt

Aus dem Ausfall darüber, aber nicht aus dem Ausfall selbst — aus der **Fehldiagnose**. Fünf Läufe lang sah ein gestubbter Namensauflöser in der eigenen Suite wie ein Zertifikatsfehler von `bista.zh.ch` aus. `DRIFT-005` fragte «läuft die Live-Suite?» und war grün; sie lief fünfmal. `OPS-010 b)` beschreibt den Mechanismus des globalen Monkeypatch, fragt aber nach Mutationsabdeckung — auch grün. Niemand fragte, **ob dabei die Quelle angesprochen wurde**.

`DRIFT-008` stellt diese Frage. Er steht ausdrücklich als eigener Check und nicht als Absatz in `OPS-010`, weil dort der Mechanismus steht und hier das Kriterium; die Abgrenzung ist im Check ausgeschrieben.

**Warum `advisory`:** neuer Check, §2.3 Schritt 1. Wie viele Portfolio-Server ihn heute erfüllen, ist **nicht gemessen** — der Scan über `autouse`-Fixtures lief bisher nur gegen die eigenen Testverzeichnisse und fand ausserhalb von `zh-education-mcp` kein Vorkommen des Musters. Das ist eine Suche nach einer Signatur, kein Durchlauf gegen das Kriterium. Bei der Promotion (§5d) ist genau diese Zahl zu erheben.

**Die Nummer 007 bleibt frei.** `DRIFT-007` wurde am 2026-08-07 zurückgezogen und ging in `FID-006` auf. Eine wiederverwendete Nummer machte den Audit-Trail mehrdeutig.

---

## `v2.3.0` — 2026-08-08 — `FID-006` übernimmt die Feldnamen, `DRIFT-007` zurückgezogen

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

### Der erste Server, der den Check erfüllen könnte — und warum die Zahl trotzdem 0 bleibt (2026-08-08)

`zh-education-mcp` hat mit [PR #43](https://github.com/malkreide/zh-education-mcp/pull/43) alles implementiert, was `FID-006` verlangt: `_READ_FIELDS` erklärt für jeden der sechs BISTA-Endpunkte die gelesenen Spalten, `_confirm_shape` bestätigt sie auf dem ersten Eintrag und wirft `UpstreamSchemaError` mit den **tatsächlich vorhandenen** Spalten, verdrahtet an der Abrufstelle in `_fetch_csv`. Dazu 18 Unit-Tests und 12 Live-Tests, die dieselbe Erklärung gegen die echte Antwort halten.

**Er steht trotzdem auf `todo` und nicht auf `pass`, und die Portfolio-Zahl bleibt bei 0 von 42.** Das letzte Kriterium — Struktur oder Feldnamen gegen eine **echte** Antwort halten — ist implementiert, aber nie grün gelaufen. Nach [`SKILL.md` §2.6](../SKILL.md) ist ein Live-Test, der nicht durchgelaufen ist, kein bestandener Test.

**Der Grund ist die Quelle, nicht der Server.** `www.bista.zh.ch` liefert auf allen sechs OGD-Endpunkten **HTTP 502**, während die Startseite mit 200 antwortet. Erster gemessener 502 am 2026-08-07 um 21:24 UTC, letzter am 2026-08-08 um 07:34 UTC — **gut zehn Stunden**, und zwar aus **zwei unabhängigen Netzen**: aus der Audit-Sitzung heraus (acht Messungen) und aus [Lauf 31245489543](https://github.com/malkreide/zh-education-mcp/actions/runs/31245489543) auf einem GitHub-Runner (2026-08-08, 07:08–07:13 UTC, `workflow_dispatch` auf `main`).

Der Lauf ist die Messung, auf die es hier ankommt, weil er die naheliegende Gegenerklärung ausschliesst: Die 502er der Audit-Sitzung gehen alle über denselben Proxy-Ausgang, ein Runner geht über einen anderen. Beide sehen dasselbe.

| Live-Lauf 31245489543 | |
|---|---:|
| eingesammelt (`-m live`) | 15 |
| gefallen mit `502 Bad Gateway` | 10 |
| gefallen mit `TimeoutError` | 3 |
| gefallen beim Verbindungsaufbau | 1 |
| **grün** | **1** |

**Kein einziger Fehlschlag betrifft einen Feldnamen.** Der eine grüne Test ist `test_live_the_real_host_resolves_past_the_egress_guard` — der einzige, der den Host **auflöst**, aber nicht **abruft**. DNS steht also; die Anwendung dahinter antwortet nicht. *(Der erste Eintrag schrieb hier «DNS steht, TLS steht» — der zweite Satzteil ist gestrichen, siehe den TLS-Absatz weiter unten.)*

**Der zweite Lauf, und was er umwirft (2026-08-08, 07:25–07:31 UTC).** [Lauf 31246130572](https://github.com/malkreide/zh-education-mcp/actions/runs/31246130572) hat dieselbe Bilanz — 14 gefallen, 1 grün — und eine **andere Ursache**:

| | Lauf 1 (07:08) | Lauf 2 (07:25) |
|---|---:|---:|
| `502 Bad Gateway` | 10 | **0** |
| `TimeoutError` | 3 | **13** |
| TLS-Hostname-Mismatch | 1 | 1 |

**Der Hostname-Mismatch ist reproduziert.** Zweimal, im selben Test (`test_live_bista_api_letzi`), mit demselben Wortlaut — `certificate is not valid for 'www.bista.zh.ch'`, jeweils nach vier `ConnectError`-Retries. Der erste Eintrag führte ihn als «einmal beobachtet, nicht reproduziert»; das gilt nicht mehr.

**Und die Gegenevidenz war keine.** Der erste Eintrag hielt dagegen, die Nachmessung aus der Audit-Sitzung melde `ssl_verify_result=0`, die Quelle sei also in Ordnung. Nachgesehen:

```
tls=0  ip=127.0.0.1  http=502
```

`remote_ip=127.0.0.1` — der TLS-Handschlag der Sitzung endet **am Agent-Proxy**, der mit eigener CA neu signiert. Das Zertifikat von BISTA bekommt diese Umgebung überhaupt nie zu sehen. Die Zahl sagt aus, dass der Proxy sich korrekt ausgewiesen hat, und sonst nichts. Sie hat der Runner-Beobachtung nie widersprochen — hier wurde eine Messung als Beleg für etwas gelesen, das sie nicht messen kann. Dieselbe Fehlerklasse wie der Helfer-Blindfleck und die selbstzitierenden Docstrings weiter oben, nur eine Ebene tiefer: nicht das Werkzeug hat falsch gezählt, sondern der Messpunkt lag nicht dort, wo die Frage war.

**Was der Proxy-Vorbehalt nicht trifft.** Der Ausfall selbst bleibt doppelt belegt. Über den Proxy kommt eine Antwort mit `server: Microsoft-IIS/10.0` und einem 1477 Byte grossen HTML-Körper zurück — das ist der Ursprung, der 502 sagt, keine Fehlerseite des Proxys; und Lauf 1 hat dieselben 502 ohne jeden Proxy gesehen. Nur die **TLS**-Aussage der Sitzung ist wertlos, nicht die HTTP-Aussage.

### Der dritte Lauf, mit Diagnose — das Zertifikat ist geprüft (2026-08-08, 08:17–08:23 UTC)

Der Diagnoseschritt ist gebaut ([zh-education-mcp#45](https://github.com/malkreide/zh-education-mcp/pull/45)) und lief zum ersten Mal. Er erhebt Auflösung, Zertifikat **je Adresse** mit SNI und Hostnamen-Prüfung, und den HTTP-Status je Endpunkt. Ergebnis um 08:22:48 UTC:

```
### 193.246.68.83
Hostnamen-Prüfung: BESTANDEN
subject=C = CH, ST = Zürich, L = Zürich, O = Kanton Zürich, CN = www.bista.zh.ch
issuer=C = US, O = DigiCert Inc, CN = DigiCert Global G2 TLS RSA SHA256 2020 CA1
notBefore=Jun  4 2026   notAfter=Dec 19 2026
SAN: www.bista.zh.ch, biss.bista.zh.ch, api.bista.zh.ch, bista.zh.ch, pub.bista.zh.ch

Startseite                       http=200  tls=0  ip=193.246.68.83
<alle sechs Endpunkte>           http=502  tls=0  ip=193.246.68.83
```

**Damit ist «die Quelle liefert ein falsches Zertifikat» erledigt.** Öffentliche CA, richtiger Inhaber, passender SAN, gültig. Und `ip=193.246.68.83` statt `127.0.0.1`: Der Runner spricht direkt mit dem Ursprung, der Lesehinweis über aufgebrochene Verbindungen greift hier nicht. Diese Messung sagt wirklich etwas über die Quelle — im Unterschied zu der, die sie ersetzt.

**Der Ausfall ist damit sauber am Ursprung belegt**, ohne Proxy und ohne Umweg: Startseite 200, alle sechs Endpunkte 502. Rund elf Stunden.

**Und der Mismatch zeigt jetzt auf uns.** `test_live_bista_api_letzi` scheiterte um 08:22:35–08:22:47 mit `Hostname mismatch`; das `openssl` derselben Maschine, gegen dieselbe Adresse, mit derselben SNI, lief **eine Sekunde später** und bekam das gültige Zertifikat. Dazu: drei Läufe, drei Mismatches, **immer derselbe Test, immer der letzte im Lauf**. Zu deterministisch für eine flatternde Quelle.

Eine naheliegende Erklärung ist geprüft und **verworfen**: Der Egress-Guard des Servers könnte auf eine IP pinnen und dann ohne saubere SNI verbinden. Tut er nicht — `_resolve_and_validate` löst nur zur Prüfung gegen die Blocklist auf, verbunden wird danach über den Hostnamen.

Was auffiel, war die Reihenfolge: Unmittelbar davor läuft `test_live_a_dns_hiccup_costs_an_attempt_not_the_call`, der einzige Live-Test, der `getaddrinfo` monkeypatcht. **Diese Vermutung ist inzwischen widerlegt** — siehe den nächsten Abschnitt.

### Die Ursache, gefunden (2026-08-08, 08:37–08:56 UTC)

Drei Sonden, und jede hat eine Erklärung erledigt statt eine bestätigt.

| | Aufbau | Ergebnis |
|---|---|---|
| **1** ([31248804156](https://github.com/malkreide/zh-education-mcp/actions/runs/31248804156)) | `-k test_live_bista_api_letzi`, sonst nichts | `1 failed` — **derselbe Mismatch, ohne jeden Vorgänger** |
| **2** ([31248874966](https://github.com/malkreide/zh-education-mcp/actions/runs/31248874966)) | `-k "dns_hiccup or letzi"` | `2 failed` — Vorgänger 502, `letzi` Mismatch |
| **3** ([31249419687](https://github.com/malkreide/zh-education-mcp/actions/runs/31249419687)) | derselbe Tool-Aufruf, **ohne pytest** | alle vier Zustände `TLS ok`, kein Mismatch |

Sonde 1 tötet die Reihenfolge-Vermutung: kein Vorgänger, kein DNS-Patch, trotzdem der Fehler. Sonde 3 tötet die Import-Vermutung *und* den Aufrufpfad: derselbe Aufruf, dieselbe Maschine, dieselben Importe — sauberes TLS, `truststore` in keinem Zustand geladen, gescheitert allein am 502.

Übrig blieb die Differenz zwischen einem pytest-Lauf und einem nackten Skript. Sie steht in `tests/test_server.py`:

```python
@pytest.fixture(autouse=True)
def _stub_dns(monkeypatch):
    """… damit Unit-Tests hermetisch bleiben (kein echtes DNS) …"""
    monkeypatch.setattr("zh_education_mcp.http_client.socket.getaddrinfo", fake_getaddrinfo)
```

`fake_getaddrinfo` liefert **`8.8.8.8`**. Die Fixture ist `autouse` für die ganze Datei und nimmt Live-Tests **nicht** aus — die Fixtures in `conftest.py` tun das, diese eine nicht. Der einzige Live-Test jener Datei verband sich also nach `8.8.8.8:443` und sandte SNI `www.bista.zh.ch`. Google antwortet mit einem Zertifikat für `dns.google`, mithin mit `certificate is not valid for 'www.bista.zh.ch'`.

Verschärfend, und nachgemessen: `http_client` macht `import socket`, also **ist** `http_client.socket` das Modulobjekt. Wer dessen `getaddrinfo` ersetzt, ersetzt es prozessweit — auch für anyio, über das httpx verbindet. Der Stub sieht lokal aus und ist global.

Behoben in [zh-education-mcp#48](https://github.com/malkreide/zh-education-mcp/pull/48): die fehlende Ausnahme, dieselbe vorsorglich in einer zweiten Datei, und ein Wächter in `conftest.py`, der jeden Live-Test mit gestubbtem Auflöser abbricht — in jeder Datei, nicht nur den zwei bekannten. **Das Portfolio ist geprüft:** Nur dieses Repo trägt das Muster; `swisstopo-mcp` und `swiss-environment-mcp` schalten in `autouse`-Fixtures DNS-*Pinning* ab, ein Feature-Flag, und lenken den Auflöser nicht um.

**Was das für den Katalog heisst.** An der Zahl nichts — `FID-006` bleibt 0 von 42, und der Ausfall der Quelle bleibt, was er war: 502 auf allen sechs Endpunkten bei 200 auf der Startseite, inzwischen rund zwölf Stunden. Was sich ändert, ist der Status der Nebenbeobachtung: **Der «TLS-Mismatch» war nie ein Befund über BISTA.** Er war der eigene Teststub.

Zwei Lehren, und beide gehören in den nächsten Durchlauf:

1. **Ein Befund über eine fremde Quelle braucht einen Messpunkt, der die Quelle erreicht.** Zwischen «BISTA liefert ein falsches Zertifikat» und «unser Stub lenkt auf 8.8.8.8 um» liegen fünf Läufe, ein zurückgezogener Beleg, ein Diagnoseschritt und drei Sonden — und die Frage war von Anfang an dieselbe.

2. **Ein Live-Test, der gegen einen Stub läuft, ist ein Live-Test nur dem Namen nach.** Er prüft nichts und behauptet alles. Das ist dieselbe Form wie ein leeres Suchergebnis, das wie eine Antwort aussieht — die Form, gegen die `FID-003` und `FID-006` geschrieben sind —, nur eine Ebene tiefer: nicht im Server, sondern im Werkzeug, das ihn prüft. Ein Katalog, der Live-Tests als Beleg verlangt (§2.6), muss auch verlangen, dass sie live sind.

**§5 feuert nicht.** Ein Quellenausfall ist keiner der fünf Auslöser: keine Severity, keine Reichweite, kein Prüfkriterium, keine Adoptionsstufe, keine Baseline hat sich bewegt. Kein bestandenes Audit wird dadurch ungültig. Der Eintrag steht hier aus dem Grund, aus dem weiter unten `v2.2.0` einen Abschnitt hat, in dem nichts feuert: Ein Kriterium, das erfüllt **aussieht** und dessen Beleg nie erbracht wurde, ist von einem erfüllten nur unterscheidbar, wenn der fehlende Beleg aufgeschrieben ist.

**Was der Ausfall über den Check selbst sagt, und das gehört in die Promotionsentscheidung.** Das Kriterium «gegen eine echte Antwort halten» hat eine Eigenschaft, die kein anderes Kriterium in `FID-006` hat: Es ist **nicht auf Zuruf erfüllbar**. Alle übrigen kann ein Team an einem Nachmittag herstellen; dieses hängt an der Verfügbarkeit eines Dritten. Auf `enforced` gehoben hiesse das, ein Server verliert seine Produktionsreife, weil seine Quelle ein Wochenende lang aus ist — und ein Gate, das das tut, wird abgeschaltet statt befolgt. Wer promoviert, braucht dafür eine Antwort: entweder ein Alter für den letzten grünen Lauf («jünger als N Tage») oder eine ausdrückliche Ausnahme für nachweisbare Ausfälle der Quelle. Beides ist eine Entscheidung, keine Formalie — und sie steht noch aus.

**Was den Eintrag schliesst:** ein grüner Lauf von `pytest tests/ -m live` gegen `zh-education-mcp`. Der wöchentliche Live-Workflow (`live-tests.yml`, Montag 05:23 UTC) läuft von selbst und meldet sich über ein Issue mit dem Label `upstream`; er lässt sich über **Actions → Live-Tests → Run workflow** auch von Hand starten. Dann — und erst dann — bewegt sich die Zeile «erfüllen den Check» in `checks/FID-006.md` von 0 auf 1.

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
| 15 / 10 / 3 / 1 / 1 in Lauf 1 | **gemessen** — Job-Log von Lauf 31245489543, jede Zeile der `short test summary info` einzeln zugeordnet |
| 15 / 0 / 13 / 1 / 1 in Lauf 2 | **gemessen** — dasselbe Verfahren am Job-Log von Lauf 31246130572. Die Ausfallform hat gewechselt, die Bilanz nicht |
| BISTA 502 seit 2026-08-07 21:24 UTC | **gemessen** — acht `curl`-Messungen aus der Sitzung plus Lauf 1; die Startseite antwortete bei jeder Messung mit 200 |
| Ausfall aus zwei unabhängigen Netzen | **gemessen** — Sitzungs-Ausgang über den Agent-Proxy, Runner-Ausgang über GitHub; kein gemeinsamer Pfad ausser der Quelle selbst. Gilt für die **HTTP**-Aussage; die Antwort trägt `server: Microsoft-IIS/10.0`, ist also die des Ursprungs und keine Fehlerseite des Proxys |
| TLS-Hostname-Mismatch | **dreimal beobachtet** — Läufe 31245489543, 31246130572 und der Lauf vom 08:17 UTC; jedes Mal derselbe Test, jedes Mal der letzte im Lauf |
| Zertifikat der Quelle gültig | **gemessen** — Diagnoseschritt auf dem Runner, 08:22:48 UTC, `ip=193.246.68.83` (kein Zwischenstopp): DigiCert Global G2, `O = Kanton Zürich`, SAN enthält `www.bista.zh.ch`, Hostnamen-Prüfung bestanden — **eine Sekunde nach** dem Mismatch derselben Maschine |
| IP-Pinning als Ursache | **geprüft und verworfen** — `_resolve_and_validate` löst nur zur Blocklist-Prüfung auf; verbunden wird über den Hostnamen, die SNI stimmt |
| Ursache des Mismatch | **gefunden** — eine `autouse`-Fixture in `tests/test_server.py` stubbt `getaddrinfo` auf `8.8.8.8` und nimmt Live-Tests nicht aus. Nachgemessen: `http_client.socket is socket` → `True`, der Patch wirkt prozessweit, anyio sieht ihn. Behoben in `zh-education-mcp#48` |
| Reihenfolge als Ursache | **geprüft und verworfen** — Sonde 1 liess den Test allein laufen (`1 selected, 1 failed`), ohne Vorgänger und ohne DNS-Patch des Nachbartests |
| Import-Nebeneffekt als Ursache | **geprüft und verworfen** — Sonde 3 misst vier Zustände in einem Prozess: alle `TLS ok`, `truststore` in keinem geladen, derselbe Tool-Aufruf scheitert allein am 502 |
| `ssl_verify_result=0` aus der Sitzung | **untauglich, zurückgezogen** — `remote_ip=127.0.0.1`; der Handschlag endet am Agent-Proxy, der neu signiert. Diese Umgebung sieht das Zertifikat der Quelle nie. Der erste Eintrag hat die Zahl als Widerspruch zur Runner-Beobachtung gelesen; sie war nie einer |

**Drei Korrekturen am Messwerkzeug, jede hat die Zahlen bewegt** — sie stehen im Kopf von `fid006_ast.py` und gehören hierher, weil eine Zahl ohne ihre Fehlversuche nicht nachvollziehbar ist:

1. Ein Zeilen-Grep setzte ein Dutzend Repos wegen `scripts/check_version_sync.py` auf die Leseliste — ein Skript, das eine Lockfile liest, ist kein Server, der seine Quelle liest.
2. Argument-Validierung zählte als bestätigter Wurzelpfad. `if not search_term.strip(): raise` sagt nichts über die Form, die ankam.
3. Taint nur innerhalb einer Funktion sah in neunzehn Repos «kein einziger Feldzugriff». Die vorherrschende Form hier ist ein `_get_json()`-Helfer, der `resp.json()` zurückgibt, während die Aufrufer die Felder lesen — gemessen wurde der Helfer, der nichts liest.

---

## `v2.3.0` — 2026-08-08 — `ARCH-014`, Klarstellung zur Abwesenheit

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
