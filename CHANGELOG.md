# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.6.0] - 2026-08-05

Die MCP-Spec 2026-07-28 macht zwei Dinge zu Entscheiden, die bisher Nebenprodukte
waren: gegen welche Spec-Version ein Server gebaut wird, und wie lange ein Client
seine Antworten behalten darf. Beide werden hier dort verankert, wo das Vorgehen
Entscheide ohnehin trifft — der eine neben A/B/C, der andere als eigener
Probe-Schritt. Bestehende Probe-Regeln bleiben unverändert.

### Added

- **1.7 Aktualisierungsrhythmus messen — die Grundlage für `ttlMs` und
  `cacheScope`.** Die Spec verlangt beide Felder auf `tools/list`,
  `prompts/list`, `resources/list` und `resources/read`. Woher die Zahl kommt,
  sagt sie nicht — und geschätzt ist sie entweder ein Cache, der einen ganzen
  Zyklus verschweigt, oder einer, der nie greift, während der Verkehr bleibt.
  Der Rhythmus der Quelle ist messbar, solange man ohnehin an der API hängt:
  eine `HEAD`-Serie auf `Last-Modified`/`ETag` über mindestens zwei erwartete
  Zyklen, mit vier Fallback-Quellen, wenn die Header fehlen.

  Der Abschnitt trennt zwei `ttlMs`-Familien, die regelmässig dieselbe Zahl
  bekommen und zwei verschiedene Uhren haben: `resources/*` veraltet mit den
  **Daten** — das misst 1.7 —, `tools/list` und `prompts/list` veralten mit der
  **Oberfläche** des Servers, also mit dem Deployment. Wer beiden dasselbe gibt,
  hält entweder eine Tool-Liste über ein Release hinweg fest oder wirft stündlich
  einen Katalog weg, der sich zweimal im Jahr ändert.

  Die Ableitungstabelle deckt vier Rhythmus-Klassen ab. Für den Normalfall —
  periodisch mit bekanntem Zeitpunkt, Beispiel MADD mit täglich gegen 05:30 CET —
  wird `ttlMs` pro Response als Rest bis zum nächsten Lauf plus Karenz berechnet,
  und die Karenz kommt aus der grössten beobachteten Verspätung der Messreihe,
  nicht aus einem runden Wert: Ein Lauf, der an manchen Tagen 37 Minuten später
  fertig ist, kostet bei einem TTL, das exakt um 05:30 abläuft, nicht 37 Minuten,
  sondern einen ganzen Tag. Dieselbe Logik wie bei der untersten Staffelstufe in
  1.5 — die brauchbare Zahl steht in der Quelle, nicht in der Formel.

  `cacheScope` wird auf eine einzige Frage zurückgeführt: Hängt diese Antwort
  davon ab, wer fragt? Für Phase-1-No-Auth-Quellen lautet die Antwort nein, und
  ein geteilter Cache ist genau das Erwünschte; sobald Auth oder ein Handle als
  Tool-Argument den Ausschnitt bestimmt, kippt sie — pro Response, nicht pro
  Server.

  Dazu der Merksatz fürs Portfolio: *«Frische innen (`source_freshness`),
  Haltbarkeit aussen (`ttlMs`).»* Die eine Zahl blickt zurück und gilt den Daten,
  die andere blickt nach vorn und gilt der Antwort; sie sind nie dieselbe.
  Ebenfalls in 1.7: die deterministische Reihenfolge der List-Responses, ohne die
  ein `ttlMs` eine Momentaufnahme cacht statt eines Zustands.

- **2.4 Spec-Ziel-Entscheid — welche `mcp_spec_version` der Server spricht.** Ein
  zweiter Pflicht-Entscheid neben A/B/C, gleich behandelt: hier getroffen, im
  README begründet, in `portfolio.json` und auf der Notion-Karte eingetragen.
  Standard ist neu `2026-07-28`; die Tier-1-SDKs sprechen die Version, für
  Variante A des Portfolios gibt es damit keinen technischen Abweichungsgrund.
  Zulässig sind zwei Gründe — ein blockierender SDK-Pin (standalone `fastmcp` 3.x
  hält `mcp` unterhalb 2.0, `fastmcp` 4.0 bringt Breaking Changes) und eine
  belegte Upstream-Abhängigkeit. «Wir migrieren später ohnehin» ist keiner: Der
  Grund stimmt und ist trotzdem falsch, weil ein neuer Server auf altem Stand
  genau die Welle vergrössert, deren Ende er abwarten will.

  Dazu das Bausteinverbot für neue Server — Roots, Sampling, Logging und Legacy
  HTTP+SSE stehen im 12-Monats-Fenster, das eine Frist für Bestehendes ist und
  kein Budget für Neues. Die Tabelle nennt zu jedem den Ersatz: explizite Handles
  statt Roots, MRTR mit `resultType: "input_required"` und Retry über
  `inputResponses` statt serverinitiiertem Sampling und Elicitation,
  maschinenlesbarer Status im Envelope statt Logging — was 3.5 ohnehin verlangt —,
  und Streamable HTTP mit den Pflicht-Headern `Mcp-Method` und `Mcp-Name`.
  Stateless Core, Extensions (`io.modelcontextprotocol/*`, für Phase 1: nicht
  bauen) und die Auth-Härtung für Phase 2 je in einem Absatz.

- **Zwei Anti-Patterns (13, 14)** — «Die Spec-Version ergibt sich aus dem SDK»
  und «`ttlMs` schätze ich» —, die zugehörigen Checklistenpunkte in Schritt 1 und
  2, eine Zeile in «Soll ich diesen Schritt überspringen?», und in Schritt 4 zwei
  Übergabepunkte an den `github-repo`-Skill.

### Changed

- **2.3 nennt Spec-Ziel und zugesagte Haltbarkeit in den Konsequenzen.** Das
  Beispiel-README im Abschnitt trug bereits die **interne** Cache-TTL und den
  Absatz darüber, dass dieselbe TTL unter `stdio` und `streamable-http` zwei
  verschiedene Dinge bedeutet. Daneben steht jetzt das `ttlMs`, das nach aussen
  zugesagt wird — mit der Regel, die beide verbindet: Eine interne TTL, die
  länger ist als das zugesagte `ttlMs`, bedient die neue Anfrage aus demselben
  alten Cache und bricht die Zusage, ohne dass es irgendwo auffällt.

- **Schritt 5 nennt die `portfolio.json`.** Bisher war die Notion-Karte der
  einzige Portfolio-Ablageort im ganzen Skill; die maschinenlesbare Hälfte im
  Index-Repo kam nicht vor. Ein neuer Server wird auf dem Ziel geboren und trägt
  trotzdem alle Migrationsfelder — sonst fehlt er in jeder Auswertung, die über
  sie läuft, und «fehlt» liest sich dort wie «noch nicht migriert».

- **«Welchen Transport-Modus unterstützen?» nennt `sse` nicht mehr.** Die
  Schnellreferenz führte `streamable-http` / `sse` als Paar. Legacy HTTP+SSE
  steht im 12-Monats-Fenster und ist für einen neuen Server kein Ziel mehr — die
  Zeile hätte sonst dem widersprochen, was 2.4 zwei Abschnitte weiter oben
  verbietet.

## [1.5.0] - 2026-08-03

Zwei Messungen kommen in Schritt 1 dazu. Beide sind billig, solange man ohnehin
an der API hängt, und beide werden sonst später aus dem Gedächtnis nachgeliefert
— einmal als Scope-Begründung, einmal als Zahl in einer Fallback-Staffel.

### Added

- **1.3b Abdeckungs-Matrix — welcher Teil des Bestands unerreichbar bleibt.** Die
  Befund-Tabelle hielt fest, was die geprobten Endpoints liefern. Sie hielt nicht
  fest, welche Bestandsteile **kein geplantes Tool** anfasst: Die erzeugen kein
  Delta, keinen Fehler und keine Zeile, sind aus der Probe also per Konstruktion
  unsichtbar. Das ist der Unterschied zu 1.2b, wo ein befragter Endpoint zu wenig
  liefert und ein Delta es beweist.

  Der Anlass ist ein Audit-Befund (`ARCH-003`): Die nachgelieferte Begründung des
  Architektur-Entscheids erklärte Konkurse und Baugesuche für ausserhalb der
  Quelle, während sie in der Quelle liegen und nur ausserhalb der geplanten
  Tools. Der Scope war richtig, die Begründung falsch — und falsch auf die teure
  Art, weil sie die Quelle kleiner macht, als sie ist. Wer Monate später
  begründet, rekonstruiert, und Rekonstruktion liefert plausible Gründe statt
  gemessener.

  Der Abschnitt verlangt, die Bestandsachse **aus der Quelle** zu enumerieren
  (Rubriken, Typen, Register, Themen — meist selbst ein Endpoint oder eine
  Facette) und die geplanten Tools hineinzumarkieren. Der umgekehrte Weg, die
  Liste aus dem Tool-Entwurf zu bilden, kann nichts finden, was der Entwurf
  übersieht. Jede nicht erreichbare Zeile trägt einen von drei zulässigen
  Gründen — bewusst ausserhalb des Scopes, technisch nicht erreichbar, noch
  offen. Die vierte Möglichkeit, in der Praxis die häufigste, ist damit
  ausgeschlossen: gar nicht erwähnt.

- **1.5 Widening-Schedule gegen die Live-API messen.** Kürzt ein Tool bei null
  Treffern den Suchbegriff, ist die Staffel eine Annahme über die Quelle. Die
  Quelle beantwortet sie in einer Handvoll Calls: ab welcher Präfixlänge liefert
  sie Treffer?

  Belegfall: Eine Staffel in Schritten von 30 % mit unterster Stufe bei acht
  Zeichen endete für `Betonsanierungsarbeiten` bei `Betonsan`; Treffer beginnen
  bei `Beton`. Drei Zeichen, und die Antwort lautete «nichts gefunden» für einen
  Bestand, der die Einträge hatte. Der Prozentsatz war nicht ungenau, sondern die
  falsche Grösse: Deutsche Komposita brechen an Morphemgrenzen, die eine relative
  Staffel nur zufällig trifft.

  Die Messung liefert drei Werte, die vorher geschätzt wurden — die unterste
  Stufe, die Stelle, ab der die Präzision in Rauschen kippt, und die Antwort auf
  die Frage, ob eine Präfix-Wildcard dasselbe in einem Aufruf tut. Tut sie es,
  ist die Staffel ein Workaround für eine vorhandene Funktion.

- **Zwei Anti-Patterns (11, 12)** und die zugehörigen Checklistenpunkte in
  Schritt 1, 2 und 3, plus das Fundstück «die geratene Staffel».

- **`reference/probe_template.sh`: `widening_probe()` und ein Coverage-Block.**
  Beide Messungen sind ausführbar statt nur beschrieben — der Coverage-Block
  enumeriert die Kategorienachse und markiert die geplanten Tools hinein, mit
  Fallback-Hinweis, wenn die Quelle keinen Kategorien-Endpoint hat.
  `reference/befund_tabelle_template.md` bekommt für beide je einen Abschnitt.

### Changed

- **2.3 verlangt einen Scope-Absatz im Architektur-Entscheid.** Der Entscheid
  sagte, *wie* die Daten geholt werden, nicht *welche*. Die Zeilen dafür stehen
  nach 1.3b bereits im Probe-Protokoll und müssen nur übernommen werden — genau
  darum wird die Matrix beim Proben angelegt und nicht hier. Das Beispiel-README
  im Abschnitt zeigt den Absatz mit Zahlen.

- **Das bisherige 1.5 (Dump-Verfügbarkeit) ist jetzt 1.6.** Die Widening-Messung
  gehört neben die Recall-Ground-Truth aus 1.4: Beide messen Suchverhalten, und
  beide sind nach der Befund-Tabelle fällig, bevor der Bulk-Weg geprüft wird.

### Fixed

- **Beide READMEs nannten «sieben Checks», seit 1.4.0 sind es acht.** Die Zahl
  steht jetzt nicht mehr da: Sie war der einzige Ort im Repo, an dem die Anzahl
  der Prüfungen von Hand gepflegt wurde, und sie ist beim Hinzufügen von Check 8
  prompt liegengeblieben. Die Aussage — jeder Check läuft auch nach einem
  Fehlschlag weiter — hängt nicht an ihr, und `validate.sh` gibt die aktuelle
  Zahl bei jedem Durchlauf selbst aus.

## [1.4.0] - 2026-08-02

Nothing about the procedure itself changes — five steps, four disciplines, and
step 3 still has six points. What changes is that the neighbouring repositories
are now named as a chain rather than as a list: five repositories along the
lifecycle, this one first, with a shared GitHub topic so they can be found as a
group from outside.

The same table now stands in `SKILL.md` as its closing section. It was only in
the READMEs, and the README is not the file the model receives — the same
argument that made the companion directory a pointer in 1.1.0. `validate.sh`
gains an eighth check so the table cannot quietly lose a member.

### Added

- **`SKILL.md` gains the quality chain as its closing section.** The change below
  renewed the table in both READMEs; `SKILL.md` named the neighbouring skills
  only in passing — in the transport hint and in the finding at the end — and
  that is the file the model actually receives. It now carries the same five
  repositories in the same order, with a stage column, and with the entries that
  matter from this end: `mcp-data-fidelity` shipped here under `companion/`
  until it got its own repository, and `mcp-continuous-auditor` is the recall
  ground truth from 1.4 measured continuously rather than once.

  The CI guard added with the chain reads the READMEs only. `SKILL.md` is
  structured differently in every repository of the chain and deliberately
  carries a repo-specific third column, so it is checked by reading, not by
  pattern.

### Changed

- **The related-repositories table is now the MCP quality chain, and it names all
  five members.** The table listed four skills plus `mcp-builder` and left
  `mcp-continuous-auditor` out of the table — it was named in a trailing sentence after it,
  which reads as an afterthought rather than as a link in the chain. It is not a skill, but it is the fifth link:
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

- **`scripts/validate.sh` check 8, asserting the chain table names all five members** — the chain table is the only place the five are named together,
  so a check makes sure it has not quietly lost a member, in both language
  versions, and that it links the topic page.

## [1.3.0] - 2026-08-02

Three changes: one to the tooling, two to the procedure. The repository's checks
now live in a single file that can be run before opening a pull request. The
transport decision sits where its consequence becomes visible — among the
consequences of the architecture decision. And 3.5 separates an outage from a
rejection, because the two carry different next steps and "try again in ten
minutes" does not terminate on a wrong host header.

The five steps and the four disciplines are unchanged, and step 3 still has six
points: 3.5 grew, no section was added.

### Added

- **`scripts/validate.sh` — alle Checks des Repos in einem Kommando.** Vier der
  sieben Prüfungen lagen bisher als Python-Heredocs inline in `ci.yml` und waren
  lokal nur per Copy-paste aus der YAML zu bekommen. Wer SKILL.md editierte,
  erfuhr das Ergebnis frühestens im Pull Request.

  Die CI ruft das Skript jetzt auf, statt die Checks zu wiederholen: Eine zweite
  Kopie würde auseinanderlaufen, und ein lokaler Runner, der von der CI
  abgewichen ist, meldet grün auf einem Baum, den die CI ablehnt — das ist genau
  der Fehlermodus, den eine Vorabprüfung nicht haben darf. Dasselbe Argument, das
  in 1.1.0 den Companion-Ordner zu einem Pointer gemacht hat.

  Drei Unterschiede zum bisherigen Verhalten, alle absichtlich:

  Das Skript läuft **nach einem Fehlschlag weiter**. Als Kette von
  Workflow-Steps brach die Prüfung beim ersten roten Schritt ab, was bei zwei
  Problemen zwei Pushes kostete; jetzt benennt ein Durchlauf alle. Der
  Exit-Code ist 0 nur, wenn keiner fehlgeschlagen ist.

  Der Frontmatter-Check gibt den **verbleibenden Spielraum** aus statt nur der
  Länge: `1017/1024 chars (7 left)`. Die Zahl ist die schärfste Nebenbedingung
  im Repo — ein zusätzlicher Trigger-Begriff in der `description` reisst das
  Limit in einer einzigen Bearbeitung, und die blosse Länge lässt das nicht
  sehen.

  `compileall` schreibt seine Bytecode-Caches über `PYTHONPYCACHEPREFIX` in ein
  temporäres Verzeichnis. In der CI war das egal, lokal legt derselbe Befehl ein
  untracked `reference/__pycache__/` an — auf diesem Weg ist in 1.1.0 schon
  einmal eine `.pyc` in den Commit geraten.

  Zehnfach mutationsgetestet: je eine Mutation pro Check, plus die beiden Fälle,
  in denen Check 3 und Check 7 aus zwei verschiedenen Gründen rot werden können
  (falscher Name / zu lange Description, veralteter Badge / fehlende
  Release-Überschrift). Alle zehn wurden vom jeweils zuständigen Check gefangen,
  bei allen zehn liefen die übrigen sechs zu Ende.

- `__pycache__/` und `*.pyc` in `.gitignore` — die zweite Hälfte desselben
  Problems. Der Cache-Prefix hält das Skript sauber, der Eintrag hält jeden
  anderen `python`-Aufruf im Repo sauber.

### Changed

- **3.5 trennt Ausfall und Abweisung.** Der Abschnitt schlug für die ganze
  Fehlerklasse denselben Satz vor — «Bitte in 10 Minuten erneut versuchen».
  Für den Ausfall ist das richtig; für eine Abweisung ist es ein nächster
  Schritt, der per Konstruktion nicht terminiert. `401`, `403` und
  `421 Invalid Host header` heissen, dass die Quelle antwortet und den Aufruf
  nicht annimmt: Warten behebt davon nichts, und 3.1 retried 4xx aus genau
  diesem Grund nicht — `429` ist die Ausnahme, dort ist Warten tatsächlich der
  richtige Schritt.

  Die Unterscheidung selbst stand schon im Skill, an drei Stellen: 3.1 wirft
  bei 4xx statt zu schlucken, 3.5 verlangt «nie einfach leere Records», und 3.6
  grenzt sich im ersten Satz gegen 3.5 ab. Was fehlte, war die Folge daraus für
  den Text, den der Aufrufer zu lesen bekommt. Es ist derselbe Fehler wie ein
  Leermengen-Hinweis, der zur Wildcard rät, während die Abfrage nie angekommen
  ist — nur eine Klasse weiter oben. Dazu die Forderung, die Klasse
  maschinenlesbar in den Status zu legen: Wer bloss einen Satz bekommt, kann
  «später nochmal» nicht von «so nie» unterscheiden.

  Anlass ist die Gegenprüfung nach der Regel-3-Ergänzung in
  [`mcp-data-fidelity` v1.2.0](https://github.com/malkreide/mcp-data-fidelity-skill/releases/tag/v1.2.0)
  und `FID-003` in `mcp-audit` v1.5.0. Dort ging es darum, dass ein Fehlschlag
  nicht als Leermenge formatiert werden darf; hier bleibt er ein Fehler und
  trägt nur den falschen nächsten Schritt.

- **Der Transport steht jetzt in 2.3, bei den Konsequenzen des
  Architektur-Entscheids** — nicht mehr nur als Zeile in der Schnellreferenz.
  Der Grund ist die Cache-Semantik: Bei ARCH B und C trifft die Transport-Wahl
  eine zweite Entscheidung mit, ohne dass sie jemand ausspricht. Unter `stdio`
  läuft ein Prozess pro Client, der Cache lebt eine Sitzung und der Dump wird
  pro Sitzung neu geladen; unter `streamable-http` bedient ein Prozess viele
  Clients, derselbe Cache lebt so lange wie die Instanz und wird geteilt.
  Dieselbe TTL bedeutet damit zwei verschiedene Dinge. Das README-Template
  nennt die Transporte und diese Folge jetzt in den `Consequences`.

  Daran hängt eine Reichweiten-Korrektur statt einer neuen Regel: Den
  Zeitstempel des letzten erfolgreichen Abrufs verlangt 3.5 schon, aber nur für
  den Ausfall. Bei geteiltem Cache sagt `provenance: cached` aus 3.2 unter
  `streamable-http` etwas anderes als unter `stdio` — «womöglich Stunden alt und
  für jemand anderen geholt» statt «in dieser Sitzung schon geholt» —, also
  braucht auch die erfolgreiche Antwort den Zeitstempel. Sonst hängt das Alter
  der Daten an der Deployment-Konfiguration statt an der Antwort.

  Erwogen und verworfen wurde ein eigener Abschnitt 3.7. Er wäre zur Hälfte
  eine Wiederholung der bestehenden «immer beide»-Regel gewesen und hätte
  Schritt 3 auf sieben Punkte gebracht, dessen Wert darin liegt, kurz genug zu
  sein, dass ihn niemand überspringt. Das ist Lehre 1 aus dem VARIA-Fundstück,
  angewandt auf den Skill selbst: erst fragen, ob eine bestehende Regel zu eng
  gefasst war, statt sofort eine neue zu schreiben. Eine Zeile in der
  Qualitätschecklist unter «Schritt 2 – Architektur» hält den Punkt prüfbar.

  Offen und bewusst so vermerkt: Für diese Regel gibt es **kein Fundstück**. Die
  Mechanik ist aus dem bestehenden Text ableitbar, aber kein Server im Portfolio
  ist bisher nachweislich darüber gestolpert. Nach dem Massstab des
  Contributing-Abschnitts ist das ein Mangel — wer den Fall trifft, trägt ihn
  bitte nach.

- **`ENV_VAR_TRANSPORT` und `__main__.py` sind aus der Schnellreferenz raus.**
  Beides ist Implementierungsdetail des Einstiegspunkts und gehört damit in
  `mcp-transport-hardening`, das genau diese Rolle hat. Die Schnellreferenz
  behält die Entscheidung («immer beide») und verweist für die Folgen auf 2.3,
  für die Umsetzung auf den Schwester-Skill.

## [1.2.0] - 2026-08-01

Documentation and guards, no change to the procedure itself — the four
disciplines and their steps are as in 1.1.0. What changes is that the skill names
its place in the family correctly, and that two things which nothing checked
before now fail loudly.
### Added

- **Die Verwandte-Repos-Tabelle nennt jetzt alle fünf Skills in einer
  Reihenfolge** — builder, probe, fidelity, transport-hardening, audit —, damit
  die Familie sich aus jedem Repo gleich liest. Zwei der fünf fehlten hier ganz:
  `mcp-data-fidelity` stand nur in der Companion-Sektion weiter oben,
  `mcp-builder` überhaupt nicht — obwohl die Rahmung dieses Skills «vor dem Bau»
  ist und die anderen damit voraussetzt.

  `mcp-continuous-auditor` und `termdat-mcp` sind aus der Tabelle in einen Satz
  darunter gewandert: Keiner von beiden ist ein Skill der Familie, und in einer
  Tabelle mit Rollenverteilung lasen sie sich, als wären sie welche.

  Dabei fiel ein Sachfehler auf: Der Schlusssatz lautete «Wer nach diesem Skill
  baut, besteht die `FID`-Checks». Die bestehen aber, wer nach `mcp-data-fidelity`
  baut — dieser Skill liefert die Ground Truth, an der jene Regeln gemessen
  werden, er ersetzt sie nicht. Korrigiert.

- Contributing section in both READMEs. The same standard the procedure applies
  to data sources applies to the procedure itself: a proposed step should come
  from a source that actually behaved that way, and name it, so the next person
  can re-probe. The smallest useful contribution is one line in the default
  matrix, with the parameter description that proves it.
- `.gitattributes` pinning `*.sh`, `*.py`, `*.yml`, `*.yaml`, `*.md` and `*.txt`
  to LF, matching the other repositories in the portfolio. This one had been the
  exception, and it is the repository where it matters most: it ships a shell
  script, and CRLF chokes bash. The CI's frontmatter check is the second reason —
  its regex expects `\n`-only fences. The index was already LF-clean, so this
  changes no content; it prevents a Windows checkout from introducing CRLF later.

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

- **`reference/response_envelope.py` zeigt das Usage-Beispiel ohne Decorator.**
  Der Repo-Validator meldete `my_tool` als «nicht im README dokumentiertes Tool»
  — dieses Repo hat gar keine Tools. Seine E1-Prüfung sucht per Regex ein
  `@x.tool(...)` unmittelbar über einem `def` im **Rohtext** einer `.py`-Datei
  und kann Code nicht von einem Docstring-Beispiel unterscheiden. Das Beispiel
  stand genau in dieser Form im Modul-Docstring.

  Behoben nicht durch Umbenennen, sondern durch Weglassen: Der Decorator war nie
  der Gegenstand des Beispiels — es geht um die Rückgabe-Hülle. Er ist raus, mit
  einem Absatz darunter, der festhält warum, damit ihn niemand «zur
  Vollständigkeit» wieder einfügt. Eine Referenzdatei, die ein Tool
  dokumentiert, sollte nicht wie eines aussehen.

  Damit ist das einzige Vorkommen dieser Form im Portfolio erledigt; die
  `patterns.py` der beiden anderen Skills tragen keinen Decorator. Repo-Validator:
  0 ERROR, 0 WARN.

## [1.1.0] - 2026-08-01

Adds a structural-assertion discipline to the probe, splits the companion skill
out into its own repository, and documents what running the probe template
actually does.

### Changed

- **`companion/mcp-data-fidelity/` is now a pointer, not a copy.** The skill has
  its own repository —
  [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill),
  released as `v1.0.0` — and that is its canonical home. What sat here was
  byte-identical to that release, so the move loses nothing; keeping it would
  have meant maintaining two copies that drift. The directory now holds a single
  `README.md` naming the new location, so anyone browsing the old path lands on
  a signpost rather than a 404.
- Both READMEs point at the standalone repository for installation, and the
  companion section now lists **six** rules rather than five — rule 6 was added
  after the copy was made, so this repository has been describing the companion
  by one rule short of what it shipped.
- CI drops the companion from the syntax check, the frontmatter check and the
  file list, and gains a guard that fails if a `SKILL.md` ever reappears under
  `companion/` — that reappearance is exactly the drift the split ended.

- Both READMEs gain a **Security** section. The one thing in this repository that
  actually does something is `reference/probe_template.sh`, and it deserved
  saying out loud: it makes live HTTP requests against whatever `BASE` it is
  given — several per endpoint, with the scope probe deliberately asking for the
  maximum a source will return — and it writes raw API responses to `$OUTDIR`.
  Point it only at sources you may query, mind their rate limits, and keep the
  output out of commits.

### Removed

- `companion/mcp-data-fidelity/reference/__pycache__/patterns.cpython-311.pyc`,
  a compiled artefact that had been committed by accident.

### Added

- **Section 1.2c — structural assertion before an empty probe counts as a
  finding.** A misread nesting returns the same empty list as a genuine
  zero-hit answer: no error, no status code, no warning. Evidence: an MCP
  Registry query kept returning nothing because the fields live under
  `servers[].server.*` and the probe looked one level up. Every probe that
  reports zero must also print the response's top-level keys and a truncated
  raw excerpt, and the finding table gains a "structure confirmed" column.
  Same rule as 3.6, one layer up: there it protects the model from the tool,
  here it protects the probe from itself.
- **1.2c, second part — aggregated endpoints lag behind authoritative ones.**
  PyPI's aggregate JSON endpoint reported the previous version after three
  consecutive releases while the simple index and a real install were current.
  Any freshness claim must record *which* endpoint was queried.
- **Anti-patterns 9 and 10** plus two release-checklist items for the above.
- **`mcp-data-fidelity` rule 6 — confirm the response shape before counting
  it.** Rules 1–5 cover what the server *sends* and what it *tells* the model;
  rule 6 covers what it *reads*. `payload.get("servers", [])` turns an upstream
  shape change into a valid-looking empty result — the same confabulation
  surface as rule 3, one layer down. A schema mismatch belongs in the error
  channel, not in an empty list.
- **`rows_of()` guard in `companion/mcp-data-fidelity/reference/patterns.py`**,
  deliberately not full schema validation: it checks only the envelope and the
  fields the caller actually reads. Verified against all four cases — valid,
  missing envelope, wrong type, fields one level deeper — plus a genuine empty,
  which still returns `[]`.

- **Companion skill `mcp-data-fidelity`** under `companion/`, separately
  installable. Five rules for MCP tools that query an external data source:
  scope parameters sent explicitly, parameter groups sent in full, empty results
  that carry a next step, the tool description as a hallucination surface, and
  query syntax in the description with recall in the tests. Ships with
  copy-paste FastMCP / httpx / pydantic patterns in `reference/patterns.py`.

  It is a companion rather than a patch to Anthropic's `mcp-builder` because
  that skill is vendored: an in-place edit would be overwritten on the next
  sync, and a fork would cut off upstream improvements.

- CI validates the companion skill alongside the main one — Python syntax,
  frontmatter, and file presence.

## [1.0.0] - 2026-07-29

Initial public release. The skill had been in internal use across the Swiss
Public Data MCP portfolio; this release publishes it together with the
data-fidelity additions described below.

### Added

- **Step 1.2b — default matrix.** For every optional parameter of every endpoint
  used: what does omitting it actually mean? The answer lives only in the spec's
  parameter description — never in the response schema, never in a working
  example. Includes an extraction snippet for OpenAPI parameter descriptions, a
  table of the usual suspects (CKAN `rows`, WFS `maxFeatures`, SPARQL named
  graphs, Elasticsearch `size`, GraphQL `first`), and the rule that a non-zero
  recall delta is a finding.
- **Step 1.4 extended to query endpoints.** Formerly "reality check against
  homepage figures", now recall ground truth against the source's official web
  UI — explicitly for search endpoints, not only list endpoints. With a selection
  rule for 3–5 reference terms and a recall canary as a live test using floors
  rather than exact counts.
- **Fifth probe call per endpoint** — the scope probe (parameter omitted vs.
  explicitly maximal).
- **Step 3.6 — an empty result is not absence.** The tool description as a
  hallucination surface: a phrasing that explains an empty result causes
  confabulation more reliably than no phrasing at all. Two non-negotiable rules
  (a `hint` field on empty results; no description that explains or excuses one)
  plus query-syntax and whole-word matching guidance.
- **`scope_probe()` and `count_of()`** in `reference/probe_template.sh` —
  runnable, verified against a live API.
- **Two mandatory sections** in `reference/befund_tabelle_template.md`: default
  matrix and recall ground truth.
- **Anti-patterns 7 and 8** ("optional means unrestricted", "zero hits means
  there is nothing"), a fourth line in the mantra, and a findings entry
  documenting the incident these additions came from.

### Changed

- Note on the limits of mocking under step 3.4: a mock reproduces the assumption
  it was written with, so scope and recall bugs are structurally invisible to it.
- Skill description now also triggers on the symptom rather than only the task —
  "finds nothing", "too few results", "web UI shows more".

### Context

Sections 1.2b, 1.4 and 3.6 come from a single real incident:
[`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). The
server sent `ClassificationIds` only when the caller supplied them; the upstream
API restricts an ID-less search to one of 23 classifications. Searching for
"Quellensteuer" returned nothing despite several matching entries.

The uncomfortable part is that this skill already contained the check that would
have caught it. Step 1.4 was applied to the list endpoints — 140 collections, 23
classifications, both correct — and never to the search endpoint. The rule was
not missing; its reach was. That is recorded in the findings section rather than
quietly fixed.
