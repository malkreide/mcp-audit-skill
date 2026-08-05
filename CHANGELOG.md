# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Neun Regeln, unverändert — auch dieses Mal ändert sich nichts an dem, was der
Skill lehrt. Es ändert sich, was die Zuordnung Regel → Audit-Check behaupten
darf. `mcp-audit` hat mit PR #98 drei Dinge bewegt (dort unter `[Unreleased]`,
eingestuft als v2.1.0), und alle drei machen Sätze hier falsch: Regel 6 hat
einen Check bekommen, und zwei Reichweite-Sätze sind von «prüft er nicht» auf
«prüft er» gekippt.

**Einstufung: minor, nicht patch.** Eine Tabellenkorrektur, die eine Zahl
richtigstellt, wäre patch. Hier kippt die operative Aussage: Wer Regel 6 gebaut
hat, konnte sich bisher darauf verlassen, dass ein Audit dazu schweigt — jetzt
gibt es dafür ein `FID-006`-Finding. Und Regel 9 zeigt auf einen Check mehr.
Der Leser handelt danach anders, und das ist die Grenze zwischen patch und
minor; die Releases 1.4.0 und 1.6.0 haben dieselbe Art Korrektur ebenso
eingestuft. Dazu kommt ein neuer CI-Wächter, also additiv.

Alle Angaben sind gegen die Check-Dateien in `mcp-audit-skill` geprüft, nicht
gegen deren Changelog: `FID-003.md`, `FID-006.md`, `ARCH-020.md`, `HITL-006.md`.

### Added

- **Ein CI-Schritt hält die Zuordnungstabelle gegen die Regelliste** — jede
  Regel genau eine Zeile, jede Zeile mindestens eine Check-ID, plus die
  Anker-Prüfung auf die Überschrift. Beide Gegenproben sind gelaufen (Zeile
  entfernt, Überschrift umbenannt) und haben angeschlagen. **Seine Grenze
  gehört dazu:** Er hätte den Anlass dieses Eintrags *nicht* gefangen. «Ein
  `FID-006` existiert nicht» nennt eine Check-ID und wäre grün durchgelaufen.
  Was drüben im Katalog steht, ist von hier aus nicht prüfbar — der Wächter
  fängt die nächste Regel ohne Zeile, nicht die nächste veraltete Zeile.

### Changed

- **Regel 6 zeigt auf [`FID-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-006.md)**
  («Antwortstruktur bestätigen, bevor gezählt wird», `high`,
  `spec_baseline: beide`, `adoption: advisory`, `evidence_required: 2`) — vorher
  stand dort «kein Check. Ein `FID-006` existiert nicht». Der Belegfall ist
  derselbe wie in der Regel: MCP Registry, Felder unter `servers[].server.*`,
  gelesen eine Ebene höher. Die Zeile nennt Fail- und Pass-Pattern und die
  Reichweite: ausdrücklich **keine** vollständige Schema-Validierung, nur was
  der Code anfasst. `DRIFT-002` bleibt als Nachbar stehen, weil die Verwechslung
  ohne den Hinweis wiederkommt; neu dazu der Querverweis auf `DRIFT-004` — Mocks
  fangen diese Klasse prinzipiell nicht.

- **Regel 7: Der Pagination-Schnitt wird jetzt geprüft — die Baseline nicht.**
  `ARCH-020` hat einen Modus 4 bekommen: zwei aufeinanderfolgende Seiten, leere
  Schnittmenge **und** vollständige Vereinigung, gegen einen Bestand grösser als
  eine Seite. Der Satz «Den Pagination-Schnitt prüft er nicht» ist damit weg.
  An seine Stelle tritt die Teil-Lücke, statt die Spalte leer zu lassen:
  `ARCH-020` trägt `spec_baseline: 2026-07-28`, der Pagination-Verlust existiert
  aber auch auf `2025-11-25` — er hängt an der Quelle und am Sortierschlüssel,
  nicht am Protokollstand. Regel 7 gilt in diesem Skill ausdrücklich unabhängig
  von der Spec-Version, ein Server der alten Baseline wird drüben aber nicht
  dagegen gemessen. Genau deshalb steht dieser Satz bei Regel 7 und nicht bei
  8 oder 9: Die setzen `2026-07-28` ohnehin voraus, für sie ist die Baseline
  des Checks keine Lücke.

- **Regel 8: Die Ableitung aus `source_freshness` wird abgefragt, bedingt.**
  `ARCH-020` verlangt sie jetzt für Datenresultate — gedeckelt auf die nächste
  Publikation, unbekannte Kadenz kurz statt komfortabel. Das Kriterium greift
  aber nur, «sofern der Server Datenresultate mit `ttlMs` versieht». Ein
  Datenresultat ganz **ohne** `ttlMs` fällt drüben nicht auf; dass eines
  hingehört, verlangt weiterhin nur diese Regel. Das steht als Rest in der
  Spalte.

- **Regel 9 zeigt zusätzlich auf [`FID-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-003.md)** —
  nachträglich geprüft, nicht aus dem Anlass übernommen. Der bisherige Satz
  «Die Abgrenzung gegen den Null-Treffer steht in keinem der beiden» ist über
  `HITL-006` und `ARCH-018` wörtlich noch wahr und liest sich trotzdem falsch,
  seit `FID-003` sie trägt. Die Aufteilung steht drüben in beiden Checks
  ausgeschrieben: `HITL-006` prüft Retry-Idempotenz und die Abgrenzung gegen
  gewöhnliche **Fehler**, `FID-003` die Disjunktheit gegen die **Leermenge**.
  Reichweite neu: Die drei `FID-003`-Kriterien sind doppelt bedingt (auf
  `2026-07-28` und darauf, dass das Tool `input_required` zurückgeben kann), und
  dass der beantwortete Retry tatsächlich Treffer liefert, verlangt drüben nur
  der Idempotenz-Test bei `write_capable: true` — für lesende Server steht
  dieser Nachweis allein hier.

- **Der Katalogstand in der Kopfzeile steht auf 113 Checks in zwölf Kategorien,
  davon sechs in `FID`** — vorher 112 und fünf. Die Kategorienzahl bleibt bei
  zwölf, `FID-006` ist in eine bestehende Kategorie gegangen. Ausgewiesen ist
  auch, dass geschnitten weiterhin v2.0.0 ist und die drei Änderungen drüben
  unter `[Unreleased]` stehen; ein Katalogstand «v2.1.0» wäre eine Version, die
  es noch nicht gibt.

- **Die Sätze unter der Tabelle folgen nach.** «Ohne Check ist einzig Regel 6»
  ist weg; offen ist jetzt Reichweite, nicht Abdeckung. Der Absatz «Warum die
  Zeilen 7–9 nicht in `FID` liegen» sagt nicht mehr, die Datentreue-Hälfte
  fehle im Katalog — sie ist dort, nur nicht als neuer `FID`-Check: `ARCH-020`
  hat sie aufgenommen, weil sie an denselben zwei Grössen hängt, und die
  Disjunktheit ist nach `FID-003` gegangen, weil sie an der Leermenge hängt und
  nicht am Rückfrageprotokoll. Der Haltbarkeitssatz bekommt den neuen Datenpunkt:
  zwischen v2.0.0 und diesem Stand liegt **ein** Tag.

- **Beide READMEs ziehen die Kurzfassung nach** — Regeln 1–6 auf sechs
  `FID`-Checks, Regel 9 zusätzlich auf `FID-003`, Katalogstand 113, und statt
  «Regel 6 hat keinen Check» der Hinweis, dass offen nur noch Reichweite ist,
  am weitesten bei Regel 7.

## [1.6.0] - 2026-08-05

Neun Regeln, unverändert — dieses Release ändert nichts an dem, was der Skill
lehrt. Es korrigiert, wohin er zeigt, und zwar an derselben Stelle wie 1.4.0:
der Zuordnung Regel → Audit-Check. Sie stand seit heute Vormittag auf
Katalogstand v1.7.0 und behauptete für die Regeln 7, 8 und 9 «kein Check». Der
Katalog steht aber seit dem 4. August auf **v2.0.0**, 112 Checks auf zwei
Spec-Baselines, und drei dieser vier Lücken sind dort längst geschlossen.

Zwischen v1.7.0 und v2.0.0 lagen vier Tage. Genau deshalb steht unter der
Tabelle jetzt ein Satz zu ihrer Haltbarkeit: Der Katalog bewegt sich schneller
als dieser Skill, und der teuerste Zeitpunkt für eine falsche Zuordnung ist
der, an dem jemand ein Finding beheben will.

### Changed

- **Die Regeln 7 und 8 liegen auf [`ARCH-020`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-020.md), Regel 9 auf [`HITL-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/HITL-006.md)** —
  beide `spec_baseline: 2026-07-28`, beide `adoption: advisory`, dazu
  `ARCH-018` für `resultType`. `ARCH-020` trägt Reihenfolge und Caching
  bewusst als *einen* Check, weil beide Anforderungen einzeln wertlos sind und
  derselbe Handgriff sie behebt. Sein Reihenfolge-Test ist schärfer als das
  Rezept in diesem Skill: zwei **Prozesse** statt zweier Aufrufe, mit
  `PYTHONHASHSEED=random` — die häufigste Ursache instabiler Ordnung ist
  Iteration über ein `set`, und dessen Ordnung ist innerhalb eines Prozesses
  konstant. Ein Test im selben Interpreter bestätigt eine Stabilität, die es
  über Neustarts nicht gibt.

- **Jede der drei Zeilen nennt jetzt ihre Reichweite — was der Check *nicht*
  abdeckt.** Eine Zuordnung, die nur den Treffer nennt, liest sich als
  vollständige Abdeckung, und dann ersetzt ein bestandenes Audit die Regel.
  `ARCH-020` misst die fünf `CacheableResult`-Methoden, nicht den
  Pagination-Schnitt auf Query-Resultaten und nicht die Ableitung eines
  `ttlMs` aus `source_freshness`; `HITL-006` prüft die Retry-Idempotenz, nicht
  die Disjunktheit von Rückfrage und Leermenge. Diese Reste sind die
  Datentreue-Hälfte der drei Regeln — sie gehören nach `FID` und stehen dort
  noch nicht.

- **Regel 6 ist die einzige ohne Check, und die Zeile sagt jetzt auch, was
  danebenliegt.** `DRIFT-002` («Fallback verengt, erweitert nie») behandelt die
  stille Substitution — ein *anderer* Datensatz. Regel 6 behandelt den Fall, in
  dem *keiner* geliefert wird, weil die Struktur nicht so aussieht wie
  angenommen. Verwandt, aber nicht dasselbe, und ohne den Hinweis sucht man
  beim falschen Check.

- **Der Katalogstand in der Kopfzeile der Tabelle steht auf v2.0.0, 112 Checks,
  zwei Spec-Baselines** — vorher v1.7.0 und 97. Beide READMEs ziehen die
  Kurzfassung nach.

## [1.5.0] - 2026-08-05

Drei neue Regeln, und zum ersten Mal keine davon aus einem Schaden. Die
MCP-Spec 2026-07-28 hat drei Stellen geschaffen, an denen dieselbe stille
Unvollständigkeit entsteht wie aus einem vergessenen Filter-Parameter: eine
instabile Sortierung verliert Treffer über Seitengrenzen, ein zu grosszügiges
`ttlMs` verliert sie in der Zeit, und eine als Leermenge formatierte
MRTR-Rückfrage lädt zu genau der Konfabulation ein, gegen die Regel 4 geschrieben
wurde.

Der Herkunftsunterschied ist ausgewiesen statt geglättet. Die Regeln 1–6 stammen
aus Vorfällen, die Regeln 7–9 aus einer Herleitung — das steht in einem eigenen
Abschnitt vor Regel 7, im Herkunftskapitel und im Contributing-Abschnitt beider
READMEs. Die Latte für Vorschläge von aussen bleibt der eingetretene Schaden;
über die tiefere Latte gekommen ist eine Protokolländerung, die alle 42 Server
des Portfolios gleichzeitig trifft.

### Added

- **Regel 7 — Deterministische Reihenfolge, dokumentiert.** `tools/list` und
  jedes Query-Resultat mit totaler Sortierung: eindeutiger Schlüssel als letztes
  Glied, benannt in Tool-Description und Envelope. Ein Relevanz-Score allein ist
  keine Ordnung, weil er Ties hat und deren Auflösung upstream nicht selten von
  der Shard-Verteilung abhängt.

  Der teure Teil ist nicht der Prompt-Cache, den ein Reconnect verliert — die
  Spec hat `initialize` und `Mcp-Session-Id` abgeschafft, Reconnect ist der
  Normalfall geworden —, sondern die Ebene darunter: Bei instabiler Ordnung
  erscheint ein Datensatz, der zwischen Seite 1 und Seite 2 die Position
  wechselt, doppelt oder gar nicht. Das ist die Fehlerklasse aus Regel 1, nur
  beim Blättern statt beim Filtern entstanden, und sie tritt bei korrekt
  gesendeten Parametern auf.

  Testrezept in beiden Varianten: offline mit `respx`, dessen Mock zwischen zwei
  identischen Calls **permutieren** muss — zweimal dieselbe Reihenfolge zu mocken
  und Gleichheit zu behaupten, ist die Fehlerform aus Regel 5 —, live der
  Pagination-Schnitt (`ids1 & ids2 == set()` und Summe gleich Gesamtmenge), den
  kein Mock kennt, weil er von der Seitenaufteilung der Quelle abhängt.

  Gilt unabhängig von der Spec-Version.

- **Regel 8 — Ehrliches `ttlMs`.** Nie länger als die tatsächliche
  Quellen-Frische. `ttlMs` ist eine Zusage, und eine, die die nächste
  Publikation überdauert, lässt den Client eine Antwort ausliefern, von der der
  Server im Moment des Sendens schon weiss, dass sie überholt sein wird —
  dieselbe Klasse wie ein verlorener Filter-Parameter: Regel 1 verliert Treffer
  im Raum, Regel 8 in der Zeit. Ein zu grosszügiges `ttlMs` ist dabei schlimmer
  als gar keines: Ohne Angabe fragt der Client neu, mit falscher Angabe fragt er
  begründet nicht.

  Abgeleitet aus `source_freshness`, nicht geschätzt: publizierte Kadenz,
  `Last-Modified`, `Cache-Control`. Unbekannte Kadenz heisst Boden oder
  `ttlMs: 0`, nicht Komfortwert. Dazu `cacheScope` gegen `requires_credentials`:
  Auf einem credential-abhängigen Resultat ist ein zu weiter Scope kein
  Frischeproblem mehr, sondern ein Datenleck — Antwort A an Aufrufer B. Das ist
  die einzige Stelle in diesem Skill, die eine klassische Schwachstelle
  beschreibt, und sie steht deshalb auch im Sicherheitsabschnitt beider READMEs.

  Testrezept: offline mit fixierter Uhr und gemocktem `Last-Modified` gegen die
  Restdistanz zur nächsten Publikation, plus der Fall ohne Frische-Angabe, der
  auf `TTL_FLOOR_MS` und `session` fallen muss; live als Obergrenzen-Canary gegen
  den echten Header — gespiegelt zur Untergrenze aus Regel 5 und aus demselben
  Grund grosszügig.

- **Regel 9 — `input_required` ist keine leere Antwort.** MRTR hat die
  serverinitiierten `elicitation`/`sampling`/`roots` ersetzt und damit neben
  Leermenge und Fehler einen dritten Ausgang geschaffen. Er ist der
  gefährlichste, weil er erfolgreich aussieht: HTTP 200, wohlgeformtes Result,
  keine Treffer darin. Als Leermenge formatiert, liefert er exakt die
  Konfabulation aus Regel 4 — diesmal über eine Frage, die der Server gestellt
  und niemand beantwortet hat. Die Umkehrung kostet ebenso viel: ein echter
  Null-Treffer als `input_required` verpackt, und der Client retryt ins Leere.

  Drei disjunkte Zustände als Tabelle, unterscheidbar an genau einem Feld;
  `entries` fehlt auf der Rückfrage wörtlich, statt leer dabeizustehen — das ist
  der Unterschied zwischen «ich habe nicht gesucht» und «ich habe gesucht und
  nichts gefunden». Im ✗/✓-Paar liegt der Fehler in der Reihenfolge: Wer zuerst
  sucht und danach die Argumente prüft, hat die Rückfrage bereits durch die
  Leermengen-Behandlung geschickt.

  Testrezept: offline drei Fälle gegen dasselbe Tool, in beide Richtungen
  assertiert (kein `hint` auf der Rückfrage, kein `inputRequests` auf der
  Leermenge), plus die Retry-Runde — eine Rückfrage, deren Beantwortung nichts
  ändert, war keine; live derselbe Übergang gegen den laufenden Server.

  Setzt Spec 2026-07-28 voraus, wie Regel 8.

- **Ein eigener Abschnitt zur Herkunft der Regeln 7–9**, vor Regel 7 in
  `SKILL.md`. Er sagt, was ihr Beleg ist (der Mechanismus) und was nicht (ein
  gemessener Schaden), und hält den Geltungsbereich fest: Regel 7 gilt immer, die
  Regeln 8 und 9 setzen die neue Spec voraus. Auf einem Wave-D- oder eingefrorenen
  Server werden sie als **nicht anwendbar** abgehakt, nicht als unerfüllt — sonst
  liest dort jemand eine Checkliste mit drei Punkten, die er nicht erfüllen kann.

- **Sechs neue Punkte in der Release-Checkliste** — totaler Sortierschlüssel,
  überschneidungsfreie Seiten, abgeleitetes `ttlMs`, `cacheScope` gegen
  `requires_credentials`, Disjunktheit von Rückfrage und Leermenge, erfolgreicher
  Retry.

- **Drei neue Blöcke in `reference/patterns.py`** — `in_stable_order()`,
  `ttl_from_freshness()` samt `cache_scope()`, und `InputRequired` mit
  `search_or_ask()`. Die CI verlangt für jede Regel ein Pattern: Eine Regel ohne
  Vorlage ist eine, die niemand kopieren kann.

### Changed

- **Die Regel-zu-Check-Tabelle nennt jetzt vier Regeln ohne Check statt einer.**
  Der Katalogstand `mcp-audit` v1.7.0 ist vor 2026-07-28 geschnitten und kennt
  weder die Sortierpflicht noch `ttlMs`/`cacheScope` noch den dritten Ausgang aus
  MRTR; `FID-003` kennt zwei. Die Zeilen 7–9 sagen das einzeln, wie Regel 6 es
  seit 1.4.0 tut. Die vier Lücken zu schliessen ist Folgearbeit in
  `mcp-audit-skill` — hier wäre ein behaupteter Check schlimmer als keiner, weil
  ein Audit ohne Befund dann als Beleg gelesen würde.

- **Der Contributing-Abschnitt beider READMEs sagt, was er noch verlangt.** Er
  las «Jede Regel hier stammt aus einem konkreten Schaden» — mit den Regeln 7–9
  ist das nicht mehr wahr, und eine Latte, die im eigenen Text nicht mehr stimmt,
  ist keine mehr. Er beschreibt jetzt die Ausnahme und ihre Grenze: eine
  Protokolländerung, die alle Server gleichzeitig trifft, ist kein zweiter Weg
  hinein für Empfehlungen im Allgemeinen.

- **Die CI-Konstanten für die README-Überschriften stehen auf «nine»/«neun».**
  Der Zählschritt hat die Überschriften hartcodiert; die Zahlwörter bleiben
  bewusst Konstanten statt Regex, damit eine ergänzte Regel beide READMEs und die
  CI im selben Commit erzwingt, statt eine veraltete Zahl grün durchzulassen.
  Dieselbe Drift, die in 1.3.0 drei Releases lang unbemerkt blieb.

## [1.4.0] - 2026-08-03

Sechs Regeln, unverändert — dieses Release ändert nichts an dem, was der Skill
lehrt. Es ändert, wohin er zeigt: Die Zuordnung Regel → Audit-Check stand als
Bereichsangabe da und war für drei von sechs Regeln falsch. Wer nach einem
Finding hierher kam, um die Behebung zu finden, landete beim falschen Check —
der teuerste Ort für eine Ungenauigkeit, weil er genau dann gelesen wird, wenn
jemand etwas reparieren will.

### Changed

- **Die Regel-zu-Check-Zuordnung ist eine Tabelle statt einer Bereichsangabe,
  geprüft gegen `mcp-audit` v1.7.0.** Es hiess: «Die Regeln 1–5 erscheinen dort
  als Checks `FID-001`–`FID-005`». Zwei aufsteigende Bereiche nebeneinander
  lesen sich als eins zu eins, und so ist die Zuordnung nicht: Regel 2 ist
  `FID-004`, nicht `FID-002`; die Regeln 3 und 4 teilen sich `FID-003`, weil der
  Check beide Hälften trägt — den fehlenden nächsten Schritt und die
  vorformulierte Ausrede; und Regel 5 braucht zwei Checks, `FID-005` für die
  Syntax und `FID-002` für den Recall.

  Wer die alte Zeile beim Beheben eines Findings gelesen hat, landete für drei
  von sechs Regeln beim falschen Check. Die neue Tabelle steht in `SKILL.md`
  neben der Kettentabelle, an derselben Stelle wie im Schwester-Skill
  `mcp-transport-hardening`, und nennt den Katalogstand, gegen den sie geprüft
  wurde.

  Am Ergebnis für Regel 6 ändert das nichts: Ein `FID-006` existiert nicht, und
  kein anderer Check des Katalogs fragt, ob eine Strukturabweichung upstream im
  Fehlerkanal endet statt in einer leeren Liste. Das steht jetzt als eigene
  Zeile da statt als Nachsatz.

## [1.3.0] - 2026-08-02

Six rules, unchanged — nothing in this release touches what the skill teaches.
What changes is where the family is named and how reliably the figures about it
hold. The related-repositories table becomes the MCP quality chain, five
repositories along the lifecycle with a shared GitHub topic, and the same table
now stands in `SKILL.md` rather than only in the READMEs — that is the file the
model actually receives.

Three figures were wrong and are corrected. Two of them had been wrong since the
sixth rule was added: the guiding question and rule 4 still spoke of five. The
CI counts headings against the README list items and does not read prose, which
is exactly how a number survives three releases.

### Changed

- **The related-repositories table is now the MCP quality chain, and it names all
  five members.** The table listed four skills plus `mcp-builder` and left
  `mcp-continuous-auditor` out. It is not a skill, but it is the fifth link:
  the only one that keeps checking after the audit has passed. The table now runs
  along the lifecycle — before the build, in the build, after the build, in
  operation — and `mcp-builder` sits beside it rather than in it, because it is
  someone else's repository and cannot carry the shared topic.

- **The five now share a GitHub topic,
  [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain).** They
  referenced each other in prose already; on GitHub the intersection of their
  topics was empty, so nothing tied them together for anyone who had not already
  found one of them. The topic is verified weekly by
  `tools/check_quality_chain.py` in `mcp-audit-skill`, which carries the manifest
  — that metadata lives outside every working copy and is unreachable from here.

### Added

- **A CI step asserting the chain table names all five members** — the chain table is the only place the five are named together,
  so a check makes sure it has not quietly lost a member, in both language
  versions, and that it links the topic page.

### Fixed

- **`SKILL.md` still said «fünf Regeln» in two places.** The guiding question in
  the introduction and the opening line of rule 4 both carried the count from
  before rule 6 existed. Headings, both READMEs, the CHANGELOG and the CI counter
  all say six — the CI counts `## Regel N` headings against the list items in the
  READMEs and does not read prose, which is why this survived three releases.
  Exactly the drift this repository documents as a hazard: the probe skill
  described this one as "five rules" for two weeks after the sixth was added.

- **The table in `SKILL.md` was still the old five-skill list.** The READMEs
  became the quality chain — five repositories along the lifecycle, with
  `mcp-continuous-auditor` in and `mcp-builder` beside it — and the table the
  model actually reads kept naming the previous set. The CI guard added with the
  chain only reads the READMEs, so nothing caught it. `SKILL.md` now carries the
  same five in the same order, with the stage column, and keeps the two
  detail lines that belong to this skill (the probe's section numbers, the
  rule-to-`FID` mapping).

- **The related-skills row for `mcp-audit` claimed more than it delivers.** It
  read «dieselben Regeln als Checks `FID-001` bis `FID-005`», which reads as if
  all rules had a check. Rules 1–5 do; rule 6 has none. Both READMEs already
  stated it precisely — the table in `SKILL.md` now does too.

## [1.2.0] - 2026-08-02

Two boundaries, both drawn from an incident in a neighbouring skill rather than
from this one. Still six rules — what changes is that two of them now say where
they stop. Rule 3 no longer lets a rejected request pass as an empty set, and
rule 5 names the variant of its own failure that needs no mock at all.

### Changed

- **Rule 3 now draws the line against transport and authorization failures.** The
  rule listed four causes for zero hits, all of them query-level — absent term,
  too narrow a query, restricted scope, wrong syntax. A rejected request is none
  of them: measured case, a request carrying a foreign Host header comes back as
  HTTP 421 with the body `Invalid Host header`, and a layer that only asks "any
  records?" passes that through as an empty set. The hint it then attaches — try
  a wildcard, widen the fields — points away from the actual fix, so a
  configuration error undercuts the very rule that exists to prevent guessing.
  Rule 6 already made this distinction for schema drift, but a request turned away
  at the transport never reaches the parsing layer. One paragraph and one
  checklist item in `SKILL.md`, one sentence on the rule-3 line in both READMEs,
  and a `search_or_raise` block in `reference/patterns.py` that names the
  `except httpx.HTTPError: entries = []` clause as the bug it is. No new rule.

- **Rule 5 now names the mock-free variant of the same failure.** A regression
  test in `mcp-transport-hardening` set the environment variable whose *absence*
  was the actual subject under test, so it passed with a deliberately introduced
  fault in place. Independent confirmation from a different domain — transport
  security rather than data fidelity — of what rule 5 already said about mocks:
  a test that establishes the condition under which the fault cannot occur
  checks nothing. Two sentences, no new rule.

## [1.1.0] - 2026-08-01

Documentation and guards. No rule added, changed or removed — six rules, as in
1.0.0. What changes is that the skill names its place in the family, and that two
figures nothing used to check now have something behind them: the reference file
can no longer drift from the rules it claims to cover, and the version badge can
no longer drift from this file.
### Added

- **The related-skills tables now name all five skills in one order** — builder,
  probe, fidelity, transport-hardening, audit — in `SKILL.md` and both READMEs, so
  the family reads the same way from every repository in it. The new
  [`mcp-transport-hardening`](https://github.com/malkreide/mcp-transport-hardening-skill)
  sits *next to* this skill rather than under it: this one asks whether the answer
  contains what the source holds, that one whether an answer arrives at all. Same
  silent class, one layer down.

  `mcp-builder` is described as Anthropic's without a licence claim:
  `anthropics/skills` carries no LICENSE file and the API reports none, so stating
  one would be a guess in a public README. `termdat-mcp` moved out of the table
  into a sentence below it — it is the server the rules came from, not a skill of
  the family, and in a table of roles it read as if it were.

- Contributing section in both READMEs. It states the bar a new rule has to
  clear: the incident it came from, a counter-example pair, and its Nachweis.
  The skill's own subject applies to the proposal — evidence that comes only from
  a mock is not yet evidence.

### Changed

- **CI checks the version badge against the CHANGELOG.** It was the last figure
  in the README with nothing behind it, and it is the one most likely to be
  forgotten: the release is cut, the badge stays. In `mcp-audit-skill` it sat
  three releases behind before anyone noticed.

  Source is the topmost `## [X.Y.Z]` heading — `[Unreleased]` carries no version
  and is skipped by the pattern. The READMEs come from `glob("README*.md")`
  rather than a maintained list, so a third language is covered automatically.
  Both anchors are asserted separately: a CHANGELOG without a release heading and
  a README without a badge each fail, because a check that finds nothing is green.

  Mutation-tested four ways. One of them changed the design: removing the topmost
  release heading does not report a missing anchor, it silently falls back to the
  next release and blames the badge. The check still goes red, but the diagnosis
  pointed at the wrong file — so the failure message now names the CHANGELOG line
  it derived the expected version from, and says that either side may have moved.

- **CI now checks `reference/patterns.py` for content, not just syntax.** Until
  now it was verified to exist and to compile; its two claims — the number word
  in the module docstring and that every rule actually appears — were guarded by
  nothing. Both happened to be correct, which is the least reliable reason for a
  value to be right: `mcp-data-source-probe-skill` described this skill as "five
  rules" for two weeks after the sixth was added, for exactly that reason.

  The rule-count step now covers the file as well: the docstring word against the
  count in `SKILL.md`, and the set of rules mentioned (`Rule 1`, `Rules 4 + 5` —
  ranges expanded) against the set that exists. A rule without a pattern is a rule
  nobody can copy, so a gap fails the build.

  Verified against mutations rather than a green run: a wrong docstring word, a
  reworded anchor phrase, and a rule with every mention removed each fail with a
  message naming the problem.

## [1.0.0] - 2026-08-01

First standalone release. The skill was previously distributed as
`companion/mcp-data-fidelity/` inside
[`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill);
this repository makes it the canonical home. The skill content is unchanged from
that copy — packaging only.

### Added

- **Rule 1 — send scope parameters explicitly, never inherit them.** An omitted
  optional filter frequently means an arbitrary slice rather than "unrestricted".
  The fact lives only in the spec's parameter description — not in the response
  schema, not in the documentation example, and not visible from a working call.
  With the table of the usual suspects (CKAN `rows`, WFS `maxFeatures`, SPARQL
  named graphs, Elasticsearch `size`, GraphQL `first`, TERMDAT
  `ClassificationIds`) and the two-call recall delta that proves it.
- **Rule 2 — send parameter groups in full.** Members of a group that are not
  sent keep their server-side default, so the argument can widen but never
  narrow — a no-op that looks like control.
- **Rule 3 — an empty result carries a next step.** Zero hits are ambiguous
  between absent term, too narrow a query, restricted scope, and wrong syntax.
  The `hint` belongs in the tool result, not in the README, because the README is
  not handed to the model.
- **Rule 4 — the tool description is a hallucination surface.** The
  counter-intuitive one: a phrasing that explains an empty result causes
  confabulation more reliably than no phrasing at all. A caveat must ask for a
  retry, never license a conclusion.
- **Rule 5 — query syntax in the description, recall in the tests.** Query
  language plus matching granularity, since whole-word indexes make German
  compounds unfindable from their parts. Recall guarded by live floors rather
  than exact counts, because a test that cries wolf gets switched off.
- **Rule 6 — confirm the response shape before counting it.** Rules 1–5 cover
  what the server *sends* and what it *tells* the model; rule 6 covers what it
  *reads*. `payload.get("servers", [])` turns an upstream shape change into a
  valid-looking empty result — the same confabulation surface as rule 3, one
  layer down. A schema mismatch belongs in the error channel.
- **`reference/patterns.py`** — copy-paste FastMCP / httpx / pydantic v2
  patterns for all six rules, including the `rows_of()` guard, which deliberately
  checks only the envelope and the fields the caller actually reads rather than
  validating a full schema.
- **Release checklist** for a data-querying tool, in `SKILL.md`.
- Bilingual README (EN/DE) with a Security section stating the two deliberate
  limits: the best-effort scope widening in rule 1, which narrows recall rather
  than failing the call when the vocabulary endpoint is unreachable, and the
  `rows_of()` guard in rule 6, which validates the envelope and the fields
  actually read rather than the full schema.

### Context

Rules 1–5 come from a single real incident:
[`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). The
server sent `ClassificationIds` only when the caller supplied them; the upstream
API restricts an ID-less search to one of 23 classifications. Searching for
"Quellensteuer" returned nothing despite several matching entries — past 33 green
offline tests and a passed 68-check audit.

Rule 6 comes from a second case: an MCP Registry query returned nothing for a
while because the fields sit under `servers[].server.*` and the client looked one
level up. Syntactically fine, semantically blind.
