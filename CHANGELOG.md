# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Das Repo hat Tags.** Bisher hatte es keine — `git checkout v1.4.0` ging
  nicht, und die Versionsnummer stand nur im CHANGELOG und in zwei Badges.
  Nachgetragen sind `v1.0.0` bis `v1.7.0`. Getaggt ist jeweils der Commit auf
  der Erst-Eltern-Historie von `main`, an dem die Release-Überschrift dort
  ankam — bei 1.0.0–1.3.0 der Release-Commit selbst, ab 1.4.0 der Merge-Commit
  der zugehörigen PR. Für jeden ist nachgeprüft, dass CHANGELOG-Spitze und
  **beide** Badges an dieser Stelle die Version tragen; die Tags behaupten also
  nichts, was der Stand nicht schon sagt.

- **Ein CI-Wächter für den Tag.** Der Schritt «Version badge matches the latest
  CHANGELOG release» bindet Badge an CHANGELOG. Der Tag war die dritte Stelle,
  die dieselbe Zahl behauptet und von keiner geprüft wurde — und die einzige der
  drei, die man nach dem Veröffentlichen nicht mehr stillschweigend korrigieren
  kann. Der Workflow triggert dafür neu auch auf `tags: ["v*"]`.

  **Grenze, ausdrücklich:** Bei einem Tag-Lauf führt GitHub die `ci.yml` des
  *getaggten* Commits aus, nicht die von `main`. Die sieben nachgetragenen Tags
  zeigen auf Commits ohne diesen Schritt und werden von ihm daher nie geprüft —
  sie sind stattdessen einmalig von Hand verifiziert. Der Wächter greift ab dem
  ersten Tag auf einen Commit, der ihn selbst enthält.

## [1.7.0] - 2026-08-06

Zehn Regeln. Eine ist dazugekommen, und eine bestehende bekommt einen Zusatz —
beide aus demselben Doppelfehler beim Anwenden von `ARCH-003`. Dazu die
Korrekturen an Regel 8, die schon vorher hier standen.

Die Leitfrage des Skills hat eine zweite Stufe bekommen. Bisher hiess sie: «kann
ich unterscheiden, ob es nichts gibt oder ob ich falsch gefragt habe?» Neu steht
daneben: «und wenn ich falsch gefragt habe — komme ich von hier zur richtigen
Frage?» Die erste entscheidet, ob das Modell schweigen darf; die zweite, ob es
weiterkommt, ohne sich einen Treffer zu erfinden.

**Der Anlass** ist [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp),
und er ist ausgeliefert gewesen. Version 0.20.0 lehnte Kriterium 1 von
`ARCH-003` («‹Not Found›-Anti-Pattern») ausdrücklich ab — kein Fuzzy-Match, kein
Vorschlagsmechanismus — und begründete das mit «bankruptcy notices,
debt-collection summonses, estate calls, construction objections», mit dem
Schadensbild, die falsche Firma als konkurs zu benennen.

**Jede Rubrik dieser Liste ist rot und über kein Tool erreichbar.** `KK`, `SB`,
`SR`, `LS`, `NA`, `ES`, `TE-*`, `GB-*`, `GE-*`, `BP-*` liegen sämtlich ausserhalb
der `GREEN_RUBRICS` — einer Allow-Liste, die genau dafür existiert, systematische
Personendaten auszuschliessen. Weil der durchsuchbare Bestand damit der
**nicht-sensible** ist, wurde die Ausnahme aus Kriterium 4 für genau die Menge
beansprucht, auf die Kriterium 1 anzuwenden gewesen wäre. Die Begründung stand in
beiden `SECURITY`-Dateien, im CHANGELOG und im abschliessenden PR; gefangen hat
sie erst das
[Re-Audit vom 2026-07-30](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md),
behoben hat sie 0.22.0.

Der zweite Fehler desselben Falls liegt in der Gegenrichtung: Der
Vorschlagsmechanismus, den der Check verlangt, ist als Erlaubnis lesbar, die
Vorschläge gleich mitzusuchen — dann liefert der Server Meldungen unter einem
Begriff aus, den niemand gewählt hat. Beide Wege laufen in dieselbe Falle, und
deshalb ist die Auflösung keine Wahl zwischen ihnen, sondern die Aufteilung.

**Einstufung: minor.** Eine neue Regel plus ein Regel-Zusatz, beides additiv;
kein bestehendes Kriterium wird enger. Wer nach 1.6.0 gebaut hat, muss nichts
zurückbauen — er hat zwei Nachweise mehr zu erbringen.

**Zur Herkunft:** Regel 10 steht auf derselben Latte wie 1–6 — ein eingetretener
Schaden, kein hergeleiteter Mechanismus. Was sie trotzdem nah an den Rand bringt,
ist die Unsichtbarkeit: Ein Server, der seine eigenen Vorschläge absucht, ist von
aussen nicht von einem zu unterscheiden, der Treffer hat.

Was darunter unverändert stehen bleibt: Regel 8 sagt in zwei Punkten etwas
anderes als vor diesem Stand.

Angefangen hat es bei der Zuordnung Regel → Audit-Check: `mcp-audit` hat mit
PR #98 drei Dinge bewegt (dort unter `[Unreleased]`, eingestuft als v2.1.0),
und alle drei machen Sätze hier falsch — Regel 6 hat einen Check bekommen, und
zwei Reichweite-Sätze sind von «prüft er nicht» auf «prüft er» gekippt. Beim
Abgleich gegen `ARCH-020` sind dann zwei Stellen aufgefallen, an denen **dieser
Skill** einen Wert empfahl, den der Check und die Spec zurückweisen. Sie stehen
unter `Fixed`.

**Einstufung: minor, nicht patch.** Eine Tabellenkorrektur, die eine Zahl
richtigstellt, wäre patch. Hier kippt die operative Aussage: Wer Regel 6 gebaut
hat, konnte sich bisher darauf verlassen, dass ein Audit dazu schweigt — jetzt
gibt es dafür ein `FID-006`-Finding. Und Regel 9 zeigt auf einen Check mehr.
Der Leser handelt danach anders, und das ist die Grenze zwischen patch und
minor; die Releases 1.4.0 und 1.6.0 haben dieselbe Art Korrektur ebenso
eingestuft. Die beiden Korrekturen an Regel 8 wären für sich genommen patch —
falsch war falsch — und ändern an der Einstufung nichts; dazu kommen drei
CI-Wächter und ein scharfgestelltes Lint-Gate, sämtlich additiv und ohne
Wirkung auf den Skill-Inhalt.

Alle Angaben sind gegen die Check-Dateien in `mcp-audit-skill` geprüft, nicht
gegen deren Changelog: `FID-003.md`, `FID-006.md`, `ARCH-020.md`, `HITL-006.md`.
Die beiden Werte-Fragen zusätzlich gegen die Spec selbst — das
[Changelog zu 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog),
Minor #5 (SEP-2549).

### Added

- **Regel 10 — Vorschlagen ist nicht Erweitern.** Auf der Leermenge kürzere
  Varianten des Begriffs anbieten, den der Aufrufer selbst geschickt hat — und
  keine davon abfragen. Die Sicherheitseigenschaft steht als eigener Satz da:
  *Keine Meldung im Resultat darf einem Begriff zuzuschreiben sein, den der
  Aufrufer nicht gewählt hat.* Sie ist in beide Richtungen verletzbar, und beide
  Male sieht das Ergebnis brauchbar aus — der Server mischt die Treffer der
  gekürzten Variante unter `entries`, oder er schlägt gar nichts vor und lässt
  den Aufrufer im Ausfall aus Regel 3 stehen. Der Konflikt zwischen «hilf dem
  Modell weiter» und «erfinde keine Treffer» wird deshalb aufgeteilt statt
  entschieden.

  **Der Nachweis ist ein Paar, und beide Hälften sind Pflicht:** Vorschläge
  erscheinen und stammen aus der Eingabe; Vorschläge werden nie gesucht —
  gemessen am Zähler der Upstream-Route und am tatsächlich gesendeten Suchbegriff.
  Fällt eine weg, ist die andere wertlos: Ein Server, der nie etwas vorschlägt,
  besteht die zweite mühelos; einer, der jeden Vorschlag sofort selbst abfragt,
  besteht die erste. Dieselbe Testform wie bei Regel 9 — die Trennung wird in
  beide Richtungen assertiert.

  Der Belegfall zeigt genau diese Halbierung: `amtsblatt-mcp` hatte die zweite
  Hälfte (`test_no_search_tool_widens_the_callers_term` — genau ein Request mit
  unverändertem Begriff) lange vor der ersten und war damit nachweislich
  unschädlich und nachweislich nutzlos. Eine Hälfte allein liest sich wie
  Disziplin und ist keine.

  **Ausnahmsweise offline.** Prüfgegenstand ist, was rausgegangen ist, nicht was
  zurückkam. Live ist das nicht messbar: Eine Suche mit einem Treffer sieht aus
  wie eine Suche mit stillschweigend ersetztem Begriff. Der Mock ist hier
  zulässig, weil die geprüfte Annahme das eigene Verhalten des Servers ist und
  keine über die Quelle — die Umkehrung der Begründung aus Regel 5.

  **Abgrenzung gegen `ARCH-003`, das die Regel ausgelöst hat.** Der Check
  verlangt Fuzzy-Match **oder** Vorschlagsmechanismus plus `match_type`; der
  Vorschlags-Arm erfüllt Check und Regel zugleich. Wer den Fuzzy-Arm nimmt, hält
  die Sicherheitseigenschaft nur mit einem eigenen Feld für die heuristischen
  Treffer, samt dem Begriff, der sie erzeugt hat. Verboten ist die Vermischung,
  nicht die Hilfe.

  **Drei Details aus der Umsetzung in `amtsblatt-mcp` 0.22.0**, je mit eigenem
  Test drüben: Vorschläge unter etwa vier Zeichen verwerfen («AG» ist kein
  Suchbegriff, ein so kurzes Präfix matcht den halben Bestand); das Resultat
  sagt ausdrücklich, dass **nicht** verbreitert wurde, sonst schliesst das Modell
  aus dem Schweigen und schliesst falsch; und der breiteste Vorschlag kommt
  zuletzt, weil die Reihenfolge als Empfehlung gelesen wird.

- **Regel-Zusatz zu Regel 1: Wer den Recall verengt, zitiert den Scope.** Eine
  Exakt-only-Entscheidung wird fast immer mit einem Risiko begründet. Das
  Argument trägt nur, wenn die Datenklasse, die das Risiko trägt, über diesen
  Server erreichbar ist. Prüffrage in zwei Teilen: *Nenne die Rubriken oder
  Datenklassen, die das Risiko tragen — und weise nach, dass sie erreichbar
  sind.* Der Nachweis ist der, gegen den Regel 1 ohnehin misst: die Aufzählung
  des vollen Scopes. Steht die Klasse nicht darin, fällt die Begründung; die
  Verengung kann richtig bleiben, muss aber aus dem Erreichbaren neu begründet
  werden.

  Es ist die vorformulierte Ausrede aus Regel 4, eine Stufe früher: Regel 4 fängt
  sie dort, wo das Modell sie liest, dieser Zusatz dort, wo jemand sie schreibt.
  Erkennungsmerkmal beide Male dasselbe — eine Begründung, die für jede beliebige
  Quelle wortgleich dastünde. Umgekehrt gilt: Ist die riskante Klasse erreichbar,
  ist Exakt-only richtig (die Ausnahme für sensible Daten in `ARCH-003`) und die
  Klasse gehört namentlich in die Tool-Description.

  Der Belegfall liefert beide Seiten. Was von der ursprünglichen Begründung übrig
  bleibt, ist schmal und echt: `HR`/`BH` (Handelsregister) und `OB-*`
  (Beschaffungen) **sind** erreichbar und nennen juristische Personen, ein
  verbreiterter Firmenname liefert also Meldungen über andere Firmen. Das ist ein
  Argument darüber, *wie* verbreitert wird — keine Ausnahme dagegen, überhaupt
  etwas anzubieten. Der Unterschied zwischen den beiden Begründungen ist nicht
  ihre Sorgfalt, sondern ob eine erreichbare Rubrik darunter steht.

- **Zwei Blöcke in `reference/patterns.py`** — `shorter_variants()` samt
  `search_and_suggest()` und dem ✗-Zweig, der die Vorschläge absucht, dazu
  `match_type` und `suggestions` auf `SearchResult` und ein `term` an
  `build_result()`, damit die Leermenge ihre Vorschläge ohne zweite Codestelle
  trägt. Die CI verlangt für jede Regel ein Pattern.

- **Drei neue Punkte in der Release-Checkliste** — der Scope-Beleg für jede
  bewusste Verengung (Regel 1), die beiden Hälften des Regel-10-Nachweises, und
  dass kein Eintrag in `entries` einen anderen Begriff beantwortet als den
  geschickten.

- **Ein CI-Schritt hält die Zuordnungstabelle gegen die Regelliste** — jede
  Regel genau eine Zeile, jede Zeile mindestens eine Check-ID, plus die
  Anker-Prüfung auf die Überschrift. Beide Gegenproben sind gelaufen (Zeile
  entfernt, Überschrift umbenannt) und haben angeschlagen. **Seine Grenze
  gehört dazu:** Er hätte den Anlass dieses Eintrags *nicht* gefangen. «Ein
  `FID-006` existiert nicht» nennt eine Check-ID und wäre grün durchgelaufen.
  Was drüben im Katalog steht, ist von hier aus nicht prüfbar — der Wächter
  fängt die nächste Regel ohne Zeile, nicht die nächste veraltete Zeile.

- **Ein Zeitplan-Lauf hält die Tabelle gegen den echten Katalog**
  (`.github/workflows/catalogue-drift.yml`, montags, dazu `workflow_dispatch`).
  Er holt `checks/MANIFEST.txt` aus `mcp-audit-skill` und vergleicht: die
  Katalog-Grösse, die Kategorienzahl und die Zahl der `FID`-Checks aus der
  Kopfzeile, dass jeder **verlinkte** Check dort existiert, und dass kein
  `FID`-Check unverlinkt bleibt. Das ist genau die Hälfte, die dem Wächter oben
  strukturell fehlt — und der Punkt, an dem `FID-006` aufgefallen wäre,
  während hier «kein Check» stand.

  **Warum nicht im PR-Lauf.** Die veraltete Zeile ist keine Eigenschaft eines
  Commits, sondern der verstrichenen Zeit — die Tabelle stand an einem Tag
  zweimal falsch, ohne dass hier jemand etwas geändert hat. Ein Netz-Zugriff vor
  dem Merge-Button würde ausserdem einen unbeteiligten Doku-PR rot färben, wenn
  drüben ein Release läuft; was dann passiert, steht in Regel 5. Meldeweg ist
  die Fehlermeldung des Zeitplan-Laufs, bewusst kein Issue-Opener.

  «Nicht erreichbar» und «abgewichen» sind zwei verschiedene Ausgänge mit
  verschiedenem Text, nach drei Versuchen — sonst sucht man beim nächsten
  Netzaussetzer einen Fehler im Katalog, den es nicht gibt.

  **Vier Gegenproben, alle angeschlagen:** Katalog um einen Check kürzer,
  ein zusätzliches `FID-007`, `FID-006` umbenannt, Kopfzeile umformuliert. Die
  ersten drei liefen zuerst *grün*, weil die Ersetzung der Manifest-URL im
  Prüfstand nicht gegriffen hatte und sie gegen den echten Katalog gemessen
  haben — die Fehlerform aus Regel 5, im eigenen Prüfstand. Der Prüfstand
  verifiziert die Ersetzung jetzt, bevor er misst.

  Der erste Lauf hat ausserdem einen **Fehlalarm** produziert: Er prüfte jede
  genannte Check-ID und schlug auf `FID-007` an — eine ID, die ein Satz unter
  der Tabelle absichtlich als *nicht existent* nennt. Geprüft wird deshalb der
  Link, nicht die Erwähnung. Ein Wächter, der eine korrekte Gegenrede meldet,
  wird abgeschaltet.

### Changed

- **Die Zuordnungstabelle bekommt eine Zeile 10 — und mit ihr den ersten
  `enforced` Check.** Regel 10 liegt auf
  [`ARCH-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-003.md)
  (`severity: medium`, `applies_when: always`, **kein** `adoption`-Feld und damit
  `enforced` — alle anderen Checks dieser Tabelle sind `advisory`). Die
  Reichweite ist der interessante Teil: Drüben fehlt genau die Disjunktheit. Kein
  Kriterium verbietet, den Vorschlag gleich abzufragen und seine Treffer unter
  `results` zu mischen — das Pass-Pattern des Checks tut es sogar, mit
  `match_type: "fuzzy"` auf einer gemeinsamen Liste. Nebenan steht `DRIFT-002`
  («Fallback verengt, erweitert nie»), dieselbe Form eine Ebene weiter: dort wird
  ein anderer *Datensatz* substituiert, hier eine andere *Abfrage*.

  **Die `FID-007`-Frage ist beantwortet statt offengelassen**, und zwar mit dem
  Verfahren des Katalogs selbst (§2.5 «Reichweite vor neuer Regel»): `applies_when`
  schliesst nichts aus (Frage 1, nein), beide Modi von `ARCH-003` lesen die
  Antwort und keiner misst den Request (Frage 2, **ja**), und eine eigene
  Prüfdimension ist es nicht — der Zähler wird in demselben Handgriff gesetzt wie
  der Mechanismus, und §2.5 verlangt, dass ein Check in einem Schritt behebbar
  bleibt. Also **kein `FID-007`, sondern ein dritter Modus in `ARCH-003`**, wie
  schon bei den Regeln 7 und 8, die `ARCH-020` aufgenommen hat. Vorschlag samt
  Belegfall und Gegenprobe liegt drüben als
  [`mcp-audit-skill#102`](https://github.com/malkreide/mcp-audit-skill/issues/102).

  Die Zeile zu Regel 1 nennt jetzt ebenfalls ihre Reichweite: `FID-001` verlangt,
  dass eine bewusst gewählte Einschränkung im Tool-Result **sichtbar** ist —
  dass ihre **Begründung** den erreichbaren Scope zitiert, verlangt keiner der
  113 Checks.

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
  am weitesten bei Regel 7. Dazu die zehnte Zeile in der Regelliste, der
  Scope-Zusatz an Zeile 1, der Herkunftsabsatz zu Regel 10 und der Satz im
  Contributing-Abschnitt, der sie als Grenzfall der eigenen Latte ausweist.

- **Die CI-Konstanten für die README-Überschriften stehen auf «ten»/«zehn».**
  Wie beim Schritt von acht auf neun bleiben die Zahlwörter hartcodiert: Eine
  ergänzte Regel erzwingt damit beide READMEs und die CI im selben Commit,
  statt eine veraltete Zahl grün durchzulassen. Ebenso das Zahlwort im Docstring
  von `reference/patterns.py`.

- **`select = []` wird zu einem vollen Ruleset mit genau einer Ausnahme.**
  Das Linting stand komplett aus, weil die Vorlagen unter `reference/`
  absichtlich Namen aus der Zielumgebung nennen und ruff das korrekt als
  `F821` meldet. Nachgemessen ist das **ein** Befund auf 581 Zeilen. Für eine
  Regel den ganzen Linter abzuschalten heisst, jeden echten Defekt in
  Vorlagen-Code mitdurchzulassen — und Vorlagen-Code ist der Code, der
  anschliessend kopiert wird; ein Defekt darin vermehrt sich. Neu:
  `E, W, F, I, UP, B, C4, SIM`, `F821` gezielt über
  `per-file-ignores` auf `reference/*.py` unterdrückt. Ausserhalb dieses Pfads
  greift `F821` weiterhin — nachgewiesen in beide Richtungen. Die CI führt den
  Schritt als eigenen `ruff check .` aus, mit demselben Pin wie der Formatter.

- **Der Pre-Commit-Hook spiegelt jetzt beides**, `ruff-check` und
  `ruff-format`. Liefe lokal nur der Formatter, meldete der Commit grün und
  erst die CI rot — genau der Fall, den ein Pre-Commit-Hook verhindern soll.
  Der Schritt «Ruff-Pin-Sync» prüft deshalb nicht mehr nur, dass beide Seiten
  dieselbe Version nennen, sondern auch, dass beide Hooks noch da sind.

### Fixed

- **Drei CI-Schritte hätten einen verschwundenen `reference/`-Ordner
  stillschweigend bestanden.** `python -m compileall -q reference/` schreibt
  auf ein fehlendes Verzeichnis «Can't list» und liefert **Exit 0**; `ruff
  format --check` und `ruff check` warnen «No Python files found» und liefern
  ebenfalls **Exit 0**. Ein Umbenennen des Ordners hätte damit drei Prüfungen
  auf einmal entwertet, ohne die CI rot zu machen — die Bauart, gegen die
  dieses Repo an anderen Stellen bereits explizit anschreibt («would silently
  stop checking»). Neu steht vor den dreien ein Wächter, der auf einem
  fehlenden oder `.py`-freien `reference/` mit benannter Ursache abbricht.

  Die übrigen ankernden Schritte wurden einzeln gegengeprüft — Frontmatter,
  `## Regel N`, beide README-Überschriften, das Zahlwort im Docstring, die
  Zuordnungstabelle, die Kettentabelle, die Release-Überschrift und das
  Versions-Badge brechen bereits alle mit klarer Meldung ab, wenn ihr Anker
  verschwindet. Dort war nichts nachzurüsten.

- **Regel 8 empfahl `ttlMs: 0` und `ARCH-020` führt es als Anti-Pattern.** Der
  Satz «Ist die Kadenz unbekannt, … ein Argument für einen kleinen oder für
  `ttlMs: 0`» ist beim Abgleich als Divergenz aufgefallen. Aufgelöst auf dieser
  Seite, weil hier der Fehler liegt: Eine Null schaltet das Feld ab, statt kurz
  die Wahrheit zu sagen — jeder Aufruf trifft die Quelle, und der Zweck von
  SEP-2549 verpufft. Die Regel sagt jetzt «den Boden, nicht die Null» und
  benennt die eine Stelle, an der eine Null richtig ist: als **abgeleitetes**
  Ergebnis, wenn die Quelle ihre eigene Publikation überschritten hat. Genau
  das rechnet `ttl_from_freshness` in `reference/patterns.py` seit jeher — die
  Referenzimplementierung dieses Skills hat den eigenen Prosa-Satz nie befolgt,
  und die Checkliste sprach schon vorher vom «Boden». Der Prosa-Satz war der
  Ausreisser.

- **`cacheScope: "session"` gibt es nicht.** `reference/patterns.py` gab
  `Literal["public", "session"]` zurück, und das Testrezept in `SKILL.md`
  behauptete `result.cache_scope == "session"`. SEP-2549 definiert **genau
  zwei** Werte, `"public"` und `"private"` — nachgelesen im
  [Spec-Changelog 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog),
  Minor #5, und deckungsgleich mit `ARCH-020`. Wer den Baustein kopiert hat,
  hat einen Wert ausgeliefert, der an der Schema-Validierung fällt; ein
  erfundener Wert ist kein vorsichtiger Wert. Beide Stellen auf `"private"`,
  und die Regel nennt die zwei zulässigen Werte jetzt ausdrücklich — gefehlt
  hat genau das.

  Gefunden beim Nachgehen der `ttlMs`-Divergenz, nicht gesucht. Das ist die
  zweite Hälfte derselben Lehre: `ARCH-020` misst `cacheScope` gegen
  `data_class`, aber kein Check dieses Portfolios prüft, ob der Wert überhaupt
  aus dem erlaubten Vorrat stammt.

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
