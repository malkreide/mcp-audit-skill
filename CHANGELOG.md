# Changelog

Alle wesentlichen Änderungen am Skill und am Check-Katalog werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Versionierung: [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt — `SKILL.md` §4.1: negative Kontrolle für Ad-hoc-Messungen

§2.6 behandelt den Fall, dass ein Werkzeug **nichts** meldet: Hat es gesucht? Der neue Abschnitt behandelt den gefährlicheren Fall — das Werkzeug meldet **etwas**, das Ergebnis ist plausibel, und es misst trotzdem etwas anderes. Ein leeres Ergebnis macht misstrauisch, ein gefülltes nicht.

Die Regel gilt bewusst nicht den Checks im Katalog, sondern den **Wegwerf-Kommandos**, mit denen während Schritt 4 ein Sachverhalt festgestellt wird. Genau die speisen die Evidenz in die Findings, und genau die werden nie gegengeprüft. Der Katalog kennt die Gegenprobe längst; für die Kommandos des Auditors gab es sie nicht.

Zwei reale Fälle, beide in einer Sitzung, beide von der auditierenden Instanz selbst: ein `grep`-Muster, das nur `- uses:`-Zeilen traf und deshalb nahelegte, drei CI-Dateien täten nichts — sie haben 9 bis 11 Schritte; und ein `pip install` mit unterdrückter Ausgabe, dessen Fehlschlag dazu führte, dass ein Versionsvergleich zweimal unter derselben Version lief. Der erste hätte einen falschen Befund über drei fremde Repositories erzeugt und fiel nur auf, weil vor dem Berichten eine der Dateien gelesen wurde.

Drei Faustregeln statt einer Haltung: Ausgabe nie unterdrücken, deren Fehlschlag das Ergebnis verfälscht; nach dem Installieren oder Auschecken zurückfragen (`--version`, `git rev-parse HEAD`); und eine Null als Behauptung lesen — «0 Treffer» heisst entweder «nichts da» oder «Muster greift nicht», und ohne Gegenprobe sind die beiden ununterscheidbar.

**Bewusst kein Gate.** Über den Katalog gemessen führen 11 von 97 Checks eine Gegenprobe. Ein Guard, der bei 86 anschlägt, wird abgeschaltet — und die Zahl misst die Erwähnung, nicht die Praxis. Sie steht als Ausgangswert im Text, damit die Richtung sichtbar bleibt, und ist selbst mit negativer Kontrolle erhoben.

Verankert in der Qualitätschecklist (Schritt 4, zwei Zeilen) und als Anti-Pattern 12. `tests/test_negative_control.py` hält Abschnitt, Belege, Checklist-Zeilen und Anti-Pattern fest — 11 Tests, fünf Mutationen gegengeprüft, alle fünf schlagen an. Jede Prüfung scheitert auch, wenn ihr Muster ins Leere greift; die Testdatei wendet damit an, was sie einfordert.

### Geändert — `ARCH-014` blockiert jetzt: von `advisory` auf `enforced`

Der Check startete auf der Brücke, und die Zahlen gaben dem recht. Bei der Erhebung las **keiner von elf** Servern `Retry-After`, **keiner** streute seinen Backoff, und drei hatten überhaupt keine Retry-Schleife. Enforced am ersten Tag wäre ein rotes Portfolio gewesen — so werden Checks zurückgenommen statt übernommen.

Die Bedingung, unter der die Stufe zurückgestellt wurde, ist eingelöst: **Alle elf Server erfüllen den Check.** Damit hat er nichts mehr zu beweisen, indem er nicht blockiert. Der teure Fall ist ab jetzt nicht mehr der Rückstand, sondern der zwölfte Server, der ohne Politik dazukommt.

**Der Durchlauf hat den Check geschärft, nicht nur bestätigt.** Drei Befunde sind erst beim Übernehmen aufgefallen, und alle drei stehen jetzt in den Pass-Pattern:

- **Der Deckel muss *nach* dem Jittern greifen.** Das Pass-Pattern dieses Checks deckelte selbst davor — der Katalog hätte den Fehler gelehrt, den er prüfen soll. `min(hint, MAX)` und danach `* (0.5 + random())` lässt eine 20-s-Decke auf 30 s wachsen. Sechs Server hatten die Reihenfolge falsch, weil sie sich beim Lesen richtig anfühlt: erst begrenzen, dann streuen. Neu mit Ziehungstest, denn bei Zufall beweist ein einzelner Blick nichts.

- **Ein Gesamtbudget aus einem httpx-Timeout ist keines.** `httpx` begrenzt pro Operation, und sein Read-Timeout beginnt mit jedem Chunk von vorn — eine langsam tröpfelnde Antwort überdauert das Budget, ohne dass ein einzelner Read abläuft. Neu verlangt der Check eine Wanduhr-Deadline (`asyncio.timeout` / `asyncio.wait_for`) **und** einen Test ohne Fake-Uhr: Eine Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über echte Zeit nicht widerlegen. Genau dieser blinde Fleck liess den Fehler durch sechs Server reisen.

- **Netzwerkfehler sind der Fall, für den man den Retry baut.** Ein Server wiederholte nur Status-Codes: 503 bekam drei Versuche, eine abgelehnte Verbindung aus demselben Ausfall keinen. Der Retry sah vorhanden aus und liess den häufigsten Fall ungedeckt — die Asymmetrie hinter dem Vorfall, der diesen Check ausgelöst hat. Modus 1 hat dafür jetzt einen eigenen Griff.

Damit sind drei Checks `advisory` (`OPS-005`, `OPS-006`, `OPS-007`) und `ARCH-014` reiht sich bei `DEP-001`, `DRIFT-006` und `OBS-007` ein, die dieselbe Brücke überquert haben.
### Behoben — ein zu breites Pass-Kriterium in `DRIFT-003`, und die Gegenrichtung des Advisory-Wächters

**Das mit v1.7.0 hinzugekommene Pass-Kriterium in `DRIFT-003` war unbedingt formuliert.** Es verlangte, dass Regex-Prüfmuster ihre Metazeichen maskieren — ohne Ausnahme. Ein Test mit `match=r"timeout|unavailable"` meint das Metazeichen aber absichtlich; nach dem Wortlaut wäre er ein Verstoss, und weil `DRIFT-003` `enforced`, `high` und `always` ist, ein blockierender.

Das Kriterium gilt jetzt für Muster, die **wörtlich gemeint** sind. Ein beabsichtigtes Metazeichen ist ausdrücklich kein Befund — es muss aber als Absicht erkennbar sein und nicht bloss übrig geblieben. Der Prosa-Teil von Modus 3 sagte das bereits («Jeder Treffer ist zu prüfen, nicht automatisch ein Befund»); die Pass-Kriterien, die das Verdikt tragen, sagten es nicht, und sie tragen es. Neu dazu ein Anti-Pattern für die Gegenrichtung: `re.escape` pauschal über ein absichtlich gemeintes Muster gelegt, womit aus `timeout|unavailable` eine Zeichenkette wird.

**`TestReadmesNameTheAdvisorySet` prüfte nur eine Richtung.** Der mit v1.7.0 eingezogene Wächter stellt sicher, dass jeder Check, den der Katalog als `advisory` führt, im README-Satz genannt wird — und dass das Zahlwort stimmt. Was er nicht prüfte: ob der Satz einen Check nennt, den der Katalog **nicht mehr** auf der Brücke führt. Eine Promotion auf `enforced` ist genau der Vorgang, bei dem dieser Satz zu lang wird, und das Zahlwort fängt es nur, solange auch die Länge auffällt.

Neu `test_no_promoted_check_is_still_listed`. Der Satz nennt hinter dem Punkt bewusst auch die bereits promovierten Checks — geprüft wird deshalb nur der Teil davor.

Beide Punkte stammen aus dem automatisierten Review zu `#80`; der dritte Befund von dort (der Advisory-Satz nannte drei Checks statt vier) war bei v1.7.0 bereits behoben.

## [v1.7.0] — 2026-08-03 — Woran ein Lauf hängt, und was ein Report nicht behaupten darf

**Ein neuer Check** (`OPS-007`) — der Katalog wächst von 96 auf **97 in zwölf Kategorien**, 700 Tests. Dazu je eine neue Ausprägung in `OPS-006` und `DRIFT-003`, und eine Präzisierung an `ARCH-011`.

Der Rest dieses Release stammt nicht aus dem Katalog, sondern aus dem Werkzeug darunter — und alle Punkte teilen eine Form. Die Prüflogik war jedes Mal in Ordnung. Falsch war, **was zwischen zwei Läufen transportiert wurde und was ein Report zu behaupten bereit war, ohne es gemessen zu haben.**

**Woran ein Lauf hängt.** `catalog_hash` hielt bisher fest, *womit* gemessen wurde; *woran*, hielt nichts fest. `audit_init.py init --target-repo` schreibt jetzt die HEAD-Revision des auditierten Repos, und das Pflicht-Gate prüft sie am Ende erneut. Ein Commit, der mitten im Lauf landet, teilt den Report sonst unbemerkt: Die Checks davor beschreiben einen Baum, die danach einen anderen, und die Mischung wird als ein Urteil präsentiert.

**Was ein Report nicht behaupten darf.** Drei Verweigerungen, dieselbe Regel:

- Weicht der Katalog-Stand vom Vorlauf ab, wird der Verlaufsvergleich **verweigert** statt korrigiert. «30 pass / 4 fail / 2 partial → x/y/z» wäre über 36 gegen 54 Checks geschrieben worden, und jede Zahl wäre als Bewegung im Server gelesen worden.
- Ein Vergleich, dessen beide Seiten leer parsen, meldet nicht mehr «identisch». Er hat recht in der Arithmetik und unrecht in allem übrigen.
- Ein Check, der sich nicht feststellen liess, hat mit `not_verified` endlich einen Status. `OPS-004` verlangte ihn, seit der Check geschrieben wurde, während das Schema den Wert zurückwies — wer die Regel befolgen wollte, bekam einen Fehler und trug `pass` ein. Eine Regel, deren Einhaltung das Werkzeug unmöglich macht, ist keine strenge Regel; sie ist eine Regel, die sich in ihr Gegenteil auflöst.

**Kein Re-Audit-Auslöser nach §5.** `OPS-007` startet `advisory`; damit sind vier Checks advisory: `ARCH-014`, `OPS-005`, `OPS-006`, `OPS-007`. Die Erweiterungen an `OPS-006` und `DRIFT-003` heben keine Severity an und dehnen kein `applies_when`. Die Präzisierung an `ARCH-011` ist enger als der bisherige Wortlaut — ein Audit, das eine Abweichung allein wegen einer Begründung in `SECURITY.md` bestanden hat, würde heute anders ausfallen; wer `ARCH-011` in einem laufenden Audit auf `pass` stehen hat, sieht dort noch einmal nach.

**Nicht dabei:** `not_verified` blockiert keine Freigabe. Ein unbeantwortbarer Check ist kein fehlgeschlagener — er steht neben dem Urteil, nicht darin.

### Ergänzt — `OPS-007`, und zwei Ausprägungen, die kein neuer Check sein durften

**Ein neuer Check** (`OPS-007`) — der Katalog wächst von 96 auf **97 in zwölf Kategorien**. Dazu je eine neue Ausprägung in `OPS-006` und `DRIFT-003`.

Der Anlass war eine Liste von vier Kandidaten, abgeleitet aus einem Arbeitstag an sechs Repos. Nach der Prüfung nach §2.5 («Reichweite vor neuer Regel») blieb genau **einer** davon ein neuer Check:

| Kandidat | Ausgang |
| --- | --- |
| Dokumentierte Befehle vs. behauptete Plattformen | **neuer Check** `OPS-007` — kein bestehender Check stellt die Frage |
| Toolchain-Version an zwei Orten | **Ausprägung von `OPS-006`** — der Check deckte das Pinnen ab, nicht den zweiten Pin |
| Prüfmuster schwächer als sein Wortlaut | **Ausprägung von `DRIFT-003`** — dieselbe Klasse, anderer Mechanismus |
| Unterbrochene Fehlerkette (`raise … from`) | **verworfen** — `OBS-007` verlangt es bereits, in Verification und Pass-Kriterien |

Der vierte Fall ist der lehrreichste: Der Befund war real (eine `TrackerError` in `tools/tracker_sync.py`, die ihre Ursache verdeckte), aber er war die **Verletzung eines bestehenden Checks**, nicht seine Lücke. Ein Katalog, der per Reflex wächst, hätte hier einen zweiten Check bekommen, der dasselbe misst — genau der Fall, vor dem §2.5 warnt.

#### `OPS-007` — eine Anleitung, die niemand ausführt, ist ungetesteter Code

`OPS-005` fragt, ob ein Check gelaufen ist. `OPS-006` fragt, ob sein Urteil hält. `OPS-007` fragt nach dem Teil des Repos, den **überhaupt nichts ausführt**: die Befehle in README und `CONTRIBUTING`.

Der Fundort ist dieses Repo. `#70` führte in beide READMEs ein:

```bash
pip install pre-commit && pre-commit install
```

Die Testmatrix in `test.yml` fährt `windows-latest`, der Quickstart trägt einen eigenen `powershell`-Block — die Windows-Zusage ist also ausgesprochen. In PowerShell 5.1 ist `&&` ein Syntaxfehler. Die CI blieb grün, weil sie den Befehl nie ausführt, auch nicht im Windows-Feld. Aufgefallen ist es erst, als jemand beiläufig sagte, er arbeite in PowerShell; behoben in `#71`.

`swiss-snb-mcp` bekam denselben Hook am selben Tag und war unauffällig — seine Anleitung stand von Anfang an auf zwei Zeilen. Nicht aus Absicht: Es hat keine Windows-Matrix, niemand hatte die Frage gestellt. Plattformtauglichkeit war dort Zufall, und ein Zufall besteht den Check nur, solange er anhält.

`medium`, `adoption: advisory`, `applies_when: always`. Advisory, weil absehbar viele Repos eine Plattform beiläufig behaupten; der Check meldet, bis ein Portfolio-Durchlauf zeigt, ob er richtig geschnitten ist. Damit stehen vier Checks auf der Brücke (`ARCH-014`, `OPS-005`, `OPS-006`, `OPS-007`).

Gegengeprüft mit der eigenen Verification: Die Suche aus Modus 2, gegen den realen Vorzustand von `#70` gehalten, findet die Zeile; gegen den heutigen Stand gehalten, findet sie nichts.

#### `OPS-006`, vierte Ausprägung — der zweite Pin

`OPS-006` verlangt, die Werkzeugversion dort zu pinnen, wo die CI sie installiert. Das löst die erste Ausprägung und erzeugt beim nächsten Schritt eine neue: Wer den Formatcheck lokal vorzieht, legt einen Pre-Commit-Hook an, und der pinnt dasselbe Werkzeug ein zweites Mal.

Laufen die beiden auseinander, formatiert der Hook nach der einen und die CI prüft nach der anderen Version — der Hook meldet grün, die CI wird rot. Abgesichert war das in beiden betroffenen Repos durch einen Kommentar, der darum bittet, sie zusammen zu bumpen. Bitten ist keine Prüfung; dieselbe Bauart wie `OPS-005`.

Neu: `Modus 3` (beide Pins gegeneinander halten, mit Gegenprobe), drei Pass-Kriterien, zwei Anti-Patterns. Die Verallgemeinerung gilt über Ruff hinaus — CI und Devcontainer, CI und `Makefile`.

#### `DRIFT-003`, dritte Ausprägung — das Prüfmuster ist schwächer als sein Wortlaut

Die bisherigen zwei Ausprägungen sitzen im Inhalt der Assertion. Die dritte sitzt in ihrer Sprache:

```python
with pytest.raises(ReleaseError, match="summary.json not found"):
```

Der Punkt ist ein Metazeichen. Das Muster passt auch auf `summaryXjson not found`. Wer die Zeile liest, liest einen Dateinamen; ausgeführt wird eine Zeichenklasse. Gefunden wurde der Fall in diesem Repo beim Anheben des Lint-Regelsatzes (`RUF043`) — nicht bei einer Testdurchsicht, weil er sich nicht schwach liest.

Neu: `Modus 3` (Regex-Argumente mit unmaskierten Metazeichen, mit Gegenprobe gegen die Zeichenkette, die abgelehnt werden soll), zwei Pass-Kriterien, ein Anti-Pattern, ein Remediation-Schritt.

**Kein Re-Audit-Auslöser nach §5** für die beiden Erweiterungen: keine Severity angehoben, keine `applies_when` erweitert. `OPS-007` ist als neuer Check der übliche Fall — bestehende Audits bleiben gültig, beim nächsten Audit gilt der neue Katalog.

### Hinzugefügt — die Anker, an denen ein Lauf hängt: Ziel-Revision und Katalog-Epoche

Zwei Zahlen machen ein Audit reproduzierbar, und bisher stand nur eine davon fest. `catalog_hash` hielt fest, **womit** gemessen wurde; **woran** gemessen wurde, hielt nichts fest.

**Die Ziel-Revision.** `audit_init.py init --target-repo <repo>` schreibt `target_sha`, `target_dirty`, `target_branch` und `target_repo` in die `audit-meta.json`. Am Ende des Laufs prüft `audit_init.py verify-target <audit_dir>` erneut, und dieselbe Prüfung läuft im Pflicht-Gate `aggregate_results.py validate`. Ohne sie teilt ein Commit, der mitten im Audit landet, den Report unbemerkt: Die Checks vor ihm beschreiben einen Baum, die danach einen anderen, und der Report präsentiert die Mischung als ein Urteil. Ein Audit, dessen Ziel sich während des Laufs bewegt, ist kein Audit — es ist eine Aussage über keine bestimmte Revision.

`target_dirty` steht daneben, weil ein sauberer SHA über einem verschmutzten Working-Tree einen Baum beschreibt, den es nur auf einer Maschine gibt. Ein Tree, der beim Start sauber war und am Ende nicht mehr, zählt als bewegt.

Das Gate ist bewusst abgestuft: **bewegt** ist ein hard fail, **nicht aufgezeichnet** eine Warnung. Ein hard fail auf Läufe, die vor `--target-repo` initialisiert wurden, hätte nur beigebracht, `--skip-target-check` reflexhaft zu setzen — und damit auch den Fall abgeschaltet, auf den es ankommt. Jede Lage landet als `target.status` im Gate-Report; eine Warnung, die nur nach stderr geht, ist beim Lesen des Run-Verzeichnisses verschwunden.

**Die Katalog-Epoche.** `aggregate_results.py aggregate --previous audits/<vorlauf>/` schreibt einen `catalog_epoch`-Block, und bei abweichendem `catalog_hash` verweigert `build_report.py` den Verlaufsvergleich: keine gegenübergestellten Status-Zahlen, nur beide Hashes, beide Check-Anzahlen und der Grund.

Der Anlass war konkret. «30 pass / 4 fail / 2 partial → x/y/z» wäre über **36 gegen 54 Checks** geschrieben worden, und jede Zahl wäre als Bewegung im Server gelesen worden. Zwei Audits desselben Servers sind nur dann ein Trend, wenn sie mit demselben Massstab gemessen wurden. Der Vergleich wird deshalb nicht normalisiert, sondern verweigert: Es gibt keine richtige Art, eine über einen Katalog gezählte Zahl von einer über einen anderen gezählten abzuziehen, und eine Fussnote überlebt das erste Zitieren nicht. Die Verweigerung muss das sichtbare Artefakt sein.

Ein **unbekannter** Hash auf einer der beiden Seiten gilt ebenfalls als nicht vergleichbar. Nicht zu wissen, ob sich der Massstab geändert hat, ist nicht dasselbe wie zu wissen, dass er gleich geblieben ist.

Nebenbei: `--checks-dir` schreibt jetzt den Hash des Katalogs, der **tatsächlich auf der Platte liegt**, und warnt bei Abweichung vom aufgezeichneten. Dieselbe Fehlerklasse wie eine wandernde Ziel-Revision, eine Ebene höher — diesmal hat sich nicht das Gemessene bewegt, sondern das Messgerät.

### Hinzugefügt — Status `not_verified`, weil «nicht geprüft» sonst als `pass` landet

`OPS-004` verlangt diesen Status, seit der Check geschrieben wurde: «ein `pass` beruht auf einem positiven Beleg, nicht auf der Abwesenheit eines Negativbelegs; sonst `not_verified`». Das Schema in `tools/aggregate_results.py` kannte den Wert nicht. Wer die Regel befolgen wollte, bekam einen Schema-Fehler und trug am Ende `pass` ein — genau das Ergebnis, das `OPS-004` verbietet. **Eine Regel, deren Einhaltung das Werkzeug unmöglich macht, ist keine strenge Regel; sie ist eine Regel, die sich in ihr Gegenteil auflöst.**

`not_verified` ist jetzt ein Status mit eigenem Zähler: eigene Spalte in der Applicability-Tabelle, eigene Liste `not_verified_findings` in `summary.json`, eigene Nennung in der Executive Summary und in der Release-Notiz. Er blockiert kein Release — ein unbeantwortbarer Check ist kein fehlgeschlagener — steht aber neben dem Urteil statt darin, samt Zusatz am Flag («YES (über 3 nicht verifizierte Checks)»). Ein grünes Urteil über eine grosse unverifizierte Menge ist eine andere Behauptung als ein grünes Urteil über keine.

Abgrenzung zu `todo`: `todo` heisst *noch nicht angeschaut*, `not_verified` heisst *angeschaut und ohne Ergebnis geblieben*. Unter der Policy `needs-attention` erzeugt er ein Finding-Dokument, unter den beiden anderen nicht.

**Zwei weitere Checks litten unbemerkt an derselben Lücke.** Ein neuer Test hält den ganzen Katalog gegen `VALID_STATUSES` und fand `IDENT-001` und `DRIFT-006`, die den Status als `unverified` schrieben — dieselbe Sache in zweiter Schreibweise. `IDENT-001` bildete beide betroffenen Exit-Codes auf `todo` ab, weil ihm nichts Besseres zur Verfügung stand: Eine Distribution, die sich nicht installieren liess, ist nicht «noch nicht angeschaut». Beide Checks sind auf die eine Schreibweise vereinheitlicht und die Zuordnung korrigiert. Zwei Schreibweisen desselben Status sind genau der Weg, auf dem «nicht verifiziert» dreimal verschieden abgelegt wird.

### Hinzugefügt — `tools/compare_guard.py`: ein Vergleich über eine Leermenge ist kein Vergleich

Ein Applicability-Diff zwischen zwei Läufen meldete **«0 == 0, identisch»** und wurde geglaubt. Beide Seiten hatten wegen eines falschen Pfads nichts geparst; der Helfer zog eine leere Menge von der anderen ab und fand keinen Unterschied. Er hatte in der Arithmetik recht und in allem übrigen unrecht: Die beiden Läufe *waren* verschieden, es hatte nur niemand hingesehen.

Das ist schlimmer als gar kein Vergleich. Ohne Helfer bleibt die Frage offen und wird irgendwann beantwortet; mit ihm schliesst eine grüne Zeile die Frage mit Belegen, die nie erhoben wurden — dieselbe Fehlerklasse, die `OPS-005` für nie gelaufene Checks und `FID-003` für eine vom Server gedeutete Leermenge benennt. Ein leerer Input ist kein Befund von Gleichheit, sondern das Fehlen einer Beobachtung.

Alle Vergleichs-Helfer laufen jetzt über `require_non_empty` / `diff_sets`. Der Guard ist absichtlich stumpf: Er unterscheidet nicht zwischen «legitim leer» und «versehentlich leer», weil der Helfer das nicht kann — und der Auditor, der der ersten Fassung glaubte, konnte es auch nicht. Wo eine leere Seite die erwartete Antwort ist, gibt es `--allow-empty`; als Flag und nicht als stille Toleranz, damit die Entscheidung eine Spur hinterlässt.

Angewandt an drei Stellen:

- **Neu: `eval_applicability.py diff <alt> <neu>`** — der Vergleich, der von Hand schiefging, jetzt einmal geschrieben. Er trennt dabei zwei Dinge, die eine reine Anwendbarkeits-Differenz gleich aussehen lässt: welche Checks überhaupt **ausgewertet** wurden (der Katalog hat sich geändert) und welche **anwendbar** waren (das Profil hat sich geändert). Nimmt gespeicherte Auswertungen entgegen, weil der Katalog-Stand des Vorlaufs vielleicht nicht mehr auf der Platte liegt. Exit 1 bei Unterschied, damit er als Gate taugt.
- **`carry_forward.py`** verweigert einen Lauf, in dem *keine* Quelle ein brauchbares Dokument enthält. Das ist die zweite der beiden realen Übertrags-Pannen: Der Quell-Lauf war falsch gewählt, es gab nichts zu übernehmen, und der Schritt meldete ein sauberes «0 carried», während jede Findung undokumentiert blieb. Ein Verzeichnis, das ein gültiger Pfad, aber der falsche Lauf ist, sieht exakt aus wie ein Lauf, aus dem nichts mehr zu holen ist.
- **Die Katalog-Epoche** vergleicht nicht gegen einen Vorlauf mit null ausgewerteten Checks.

### Präzisiert — `ARCH-011`: `SECURITY.md` ist kein README

Das Kriterium verlangte, Abweichungen vom Standard-Layout seien «im README begründet», ohne zu sagen, welche Dateien das *nicht* erfüllen. In einem realen Audit stand die Begründung in `SECURITY.md` und wurde zuerst als bestanden abgelegt.

Jetzt steht dort, dass `README.md` oder `README.de.md` zählen und `SECURITY.md`, `CONTRIBUTING.md`, `docs/`, ein Issue oder eine Commit-Message nicht — auch dann nicht, wenn die Begründung dort inhaltlich vollständig ist. Der Grund ist der Zweck des Kriteriums: Wer die Struktur nicht wiedererkennt, schaut ins README, dorthin, wo die Abweichung ihm begegnet. Eine Begründung in `SECURITY.md` erreicht nur, wer ohnehin nach Sicherheitsthemen sucht.

### Hinzugefügt — der Description-Guard bekommt einen Adressaten

`repo-description` war über **sechs aufeinanderfolgende Merges rot** (seit PR #68) und wurde nie beantwortet. Der Check war dabei die ganze Zeit korrekt: Der Katalog hat 96 Checks, die Repo-Description nennt 93. Gefehlt hat nicht die Prüfung, sondern der Empfänger — ein Guard, der auf `push: main` läuft, meldet an niemanden, weil ein roter Push-Lauf in keinem Pull Request auftaucht und die Job-Summary nur sieht, wer den Lauf öffnet.

Der Workflow legt bei Drift jetzt ein Issue an oder aktualisiert es und **schliesst es selbst**, sobald die Description wieder stimmt. Ohne das Schliessen wäre es Dauergemecker und nach zwei Wochen abgeschaltet.

`tools/render_description_issue.py` trennt drei Zustände statt zwei. Die naheliegende Form — «Body geschrieben → Issue auf, kein Body → Issue zu» — ist falsch, und das hat erst die Messung gezeigt: `result.json` kann fehlen, leer, kaputt oder `description: null` sein, wenn der Abruf scheiterte. Alle vier erzeugen keinen Body und hätten ein offenes Issue geschlossen, gestützt auf einen Vergleich, der nie stattgefunden hat. Ein Check, der nicht gelaufen ist, ist kein Bestehen (§2.6) — `unchecked` fasst deshalb nichts an. 18 Tests, drei Mutationen gegengeprüft, alle drei schlagen an.

### Hinzugefügt — `SKILL.md` §0.5: Platzhalter in spitzen Klammern

Ein PR-Body mit «suchte `findings/<ID>.md`, während der Lauf `<ID>-<slug>.md` benannt hatte» kommt als «suchte `findings/.md`, während der Lauf `-.md` benannt hatte» an. Backticks schützen nicht. In PR #79 zweimal reproduziert — beim Anlegen und beim Korrekturversuch mit denselben Klammern.

Bösartig ist der Fall, weil das Ergebnis plausibel bleibt: `findings/.md` sieht nach einem Dateinamen aus, nicht nach einem Fehler. Ein Text über den Unterschied zweier Schreibweisen wurde zu einem Text, der beide gleich nennt — ohne Meldung, ohne rotes Gate. Dieselbe Mechanik trifft die Template-Überschrift `## Finding: <CHECK-ID> — <CHECK-TITLE>`.

Wo die Umwandlung passiert, ist **nicht** belegt und steht deshalb als Vermutung im Text, nicht als Regel: Der gespeicherte Body escaped auch Apostrophe zu `&#39;`, was GitHub in Bodies nicht tut — der Verlust entsteht also vermutlich in der Werkzeugschicht des Agenten, nicht bei GitHub. Die Regel gilt darum für den Agentenpfad, für den sie gemessen ist.

### Hinzugefügt — `tools/carry_forward.py`

Übernimmt unveränderte Finding-Dokumente aus früheren Audit-Läufen. Bisher war das ein Handgriff, und er ist zweimal schiefgegangen.

Beim ersten Mal suchte der handgeschriebene Übertrag `findings/<ID>.md`, während der Quell-Lauf `<ID>-<slug>.md` benannt hatte. Er fand nichts, schrieb einen leeren Platzhalter, füllte ihn nie — 16 Findings über zwei Läufe als Null-Byte-Dateien, vom Validation-Gate durchgewinkt. Beim zweiten Mal war der Quell-Lauf falsch gewählt, mit demselben Ergebnis.

Der Helfer garantiert fünf Dinge:

- **Beide Namensformen lösen auf.** `<ID>.md` und `<ID>-<slug>.md` sind dieselbe Findung.
- **Eine leere Quelle ist keine Quelle.** Der Rückstand genau dieses Bugs wird übersprungen, nicht weitergereicht.
- **Es wird nie etwas Leeres geschrieben.** Der Fehlermodus lässt sich vom Werkzeug, das ihn behebt, nicht wieder einführen.
- **Handgeschriebenes im Ziel gewinnt.** Nur leere Stubs werden ersetzt — und zwar an Ort und Stelle, nicht durch eine zweite Datei daneben.
- **Eine fehlende Quelle ist laut.** Exit 1 mit den betroffenen IDs.

Beim Gegenprüfen an dem real kaputten Lauf fiel eine zweite Ebene auf: die erste Fassung reparierte die Abdeckung und liess zwölf Null-Byte-Dateien neben den befüllten liegen. Das Gate war zufrieden, weil es je ID die substantiellste Datei nimmt — der Müll war für es unsichtbar. Ein Werkzeug, das ein Artefakt repariert, darf es nicht schmutzig hinterlassen; der Stub wird jetzt überschrieben statt ergänzt.

21 Tests, davon zwei nach den realen Fehlern benannt.

**Die allgemeine Regel dahinter**, jetzt auch in `SKILL.md` §5.0: Was zweimal von Hand gemacht wurde, wird ein Skript. Alle vier realen Fehler dieser Methodik lagen nicht in der Prüflogik, sondern im Transport von Zustand zwischen Läufen.

### Ergänzt — `OPS-006`, und was ein Rollout über 32 Repos über Gates lehrt

**Ein neuer Check** (`OPS-006`) — der Katalog wächst von 95 auf **96 in zwölf Kategorien**. Dazu zwei Erweiterungen an `OPS-005` und ein neuer Abschnitt in `SKILL.md`. Alles stammt aus einem einzigen Vorgang: dem Ausrollen eines Formatgates über 32 Portfolio-Repos, das nebenbei 112 angesammelte Lint-Verstösse und 205 unformatierte Dateien sichtbar machte.

**`OPS-006` — das Urteil eines Gates ist reproduzierbar.** `OPS-005` fragt, ob ein Check gelaufen ist; `OPS-006` fragt, ob sein Urteil morgen dasselbe wäre. Drei Ausprägungen, zwei davon eigene Fehler beim Ausrollen:

- 29 der 32 Repos deklarierten `ruff>=0.4.0` ohne obere Grenze. Solange nur `check` lief, war das erträglich — ein `format --check` ohne Pin hätte beim nächsten Upstream-Release **portfolioweit gleichzeitig** den Merge-Pfad blockiert, an unberührtem Code.
- Zwei ruff-Binaries im `PATH`: Das ältere verdeckte das, welches die CI installiert. Derselbe Befehl im selben Klon zählte je nach Binary 17 oder 56 Dateien; eine lokal grüne Prüfung belegte nichts.
- Eine Zählung per `grep -c "^Would reformat"` traf unter der neueren Version nie mehr zu und meldete überall sauber `0`. Die daraus abgeleitete Aussage «alle 32 Repos sind bereits formatgerecht» war falsch — es waren 205 Dateien. Ein Zählfehler, der Null meldet, sieht nicht nach einem Fehler aus.

Startet `advisory`. Damit sind drei Checks `advisory`: `ARCH-014`, `OPS-005` und `OPS-006`.

**`OPS-005` bekommt eine sechste Ausprägung** — der Geltungsbereich der geprüften *Pfade*, als Gegenstück zur fünften, die den Geltungsbereich der *Konfiguration* betrifft. Fast alle Repos linteten nur `src/`. Bei der Ausweitung kamen in fünf Repos 112 Verstösse hoch, die nie jemand gemeldet hatte. Unangenehm daran ist vor allem `scripts/`: Dort liegen die Prüfskripte, die in der CI der übrigen Gates laufen — die Durchsetzer waren selbst ungeprüft. Zwei Sonderformen kamen dazu: ein Repo mit vollständigem Regelsatz in `pyproject.toml`, den kein Workflow aufrief, und eines, das seinen Formatcheck als Kommentar stillgelegt hatte («vorerst deaktiviert, Refactoring ausstehend») — eine bekannte Lücke ohne Termin und ohne Eintrag.

**`SKILL.md`, Portfolio-Hygiene: ein mechanischer Eingriff braucht einen mechanischen Nachweis.** Wer 205 Dateien umformatiert, kann das Ergebnis nicht lesen. Der Abschnitt beschreibt zwei billige, harte Prüfungen — AST-Vergleich für Formatierung, Vergleich der String-Literale für Umbenennungen — und wann sie anschlagen. Beide haben es in diesem Rollout getan: Der AST-Vergleich fand zwei Docstrings, bei denen `ruff format` den Stringinhalt ändert (vier Anführungszeichen am Anfang), und die Literal-Prüfung verhinderte, dass eine Umbenennung von `S` ein Literal `'[S'` verfälscht. Dazu drei Eigenschaften, die erst beim Ausrollen sichtbar werden, darunter: Sobald ein Formatgate steht, prüft die CI den Merge-Commit — ein offener Pull Request kann rot werden, ohne dass sich an ihm etwas ändert. Das traf zwei von 27 offenen Pull Requests.

**Korrektur an v1.6.0.** Der Eintrag zur fünften Ausprägung von `OPS-005` behauptete, die auslösende Fehlermeldung habe eine Datei genannt, in der das Symbol nicht vorkam. Das war falsch und ist mit [#77](https://github.com/malkreide/mcp-audit-skill/pull/77) entfernt: Der Lauf stammte aus `lobbywatch-mcp` selbst und benannte Datei, Zeile und Symbol korrekt. Beide Belege für die gegenteilige Annahme trugen nicht — eine Dateizählung, die eine ältere ruff-Version widerspiegelte, und eine `git log --all -S`-Suche, die überschriebene Historie eines gelöschten Branches nicht sehen kann. Ursache, Mechanismus und die abgeleitete Regel sind vom Irrtum nicht berührt.

## [v1.6.0] — 2026-08-02 — Zwei Befunde aus dem Durchlauf, und eine Kette die man findet

**Zwei neue Checks** (`ARCH-014`, `OBS-007`) — der Katalog wächst von 93 auf **95 in zwölf Kategorien**, 469 Tests. Beide stammen nicht aus einem einzelnen Vorfall, sondern aus dem Blick über zehn Server gleichzeitig: Acht von ihnen retryen, keiner liest `Retry-After` oder streut seinen Backoff (`ARCH-014`); und zwei von acht packen die ursprüngliche Exception so ein, dass nach aussen sauber maskiert und nach innen nichts mehr übrig ist (`OBS-007`). Was ein Review pro Repo nicht sieht, weil in jedem einzelnen nichts falsch aussieht.

Daneben wird die Familie als Gruppe auffindbar. Die fünf Repos verwiesen in ihren READMEs seit je aufeinander, auf GitHub war die Schnittmenge ihrer Topics **leer** — sichtbar also nur für den, der ohnehin schon eines offen hatte. Jetzt tragen sie ein gemeinsames Topic, die Mitgliedschaft steht an einer Stelle (`docs/quality-chain.json`), ein wöchentlicher Guard prüft sie, und die Kette steht neben den READMEs auch in `SKILL.md` — der Datei, die das Modell beim Audit tatsächlich bekommt.

**Re-Audit:** Die Promotion von `OBS-007` auf `enforced` fällt unter den neuen Auslöser d) aus §5 der Katalog-Versionierung — sie kippt ein Verdikt, ohne dass sich ein Feld ändert, das die Regel las. `ARCH-014` startet `advisory` und blockiert nicht. Damit sind weiterhin genau zwei Checks `advisory`: `ARCH-014` und `OPS-005`.

### Behoben — `tools/check_ruff_pin.py` war selbst nicht breitenunabhängig

Nachgereichter Eintrag zu [#73](https://github.com/malkreide/mcp-audit-skill/pull/73). Der Guard, der Pin-Drift zwischen `lint.yml` und `.pre-commit-config.yaml` verhindert, verstiess selbst gegen die Regel, die `OPS-005` mit [#72](https://github.com/malkreide/mcp-audit-skill/pull/72) als fünfte Ausprägung aufgenommen hat.

Er entstand in [#70](https://github.com/malkreide/mcp-audit-skill/pull/70) und ist ausdrücklich zum Kopieren gedacht. Die Gegenprobe über die vier Portfolio-Breiten fiel jedoch nie:

| `line-length` | `ruff format --check` |
| --- | --- |
| 88 (dieses Repo, ruff-Default) | unverändert |
| 100 | unverändert |
| **110** | würde umformatieren |
| **120** | würde umformatieren |

Ab Breite 110 zieht `ruff format` zwei Ausdrücke in `compare()` zusammen, die bei 88 mehrzeilig bleiben. Hier war die Datei grün — in einem der zwei 110er- oder fünf 120er-Repos wäre die Kopie beim ersten `ruff format --check` rot gewesen. Genau der Fall, den `OPS-005` beschreibt, im Werkzeug, das gegen dieselbe Klasse von Drift antritt.

Behoben nach den zwei Regeln der kanonischen `check_version_sync.py`, die jetzt auch im Docstring dieser Datei stehen: keine Zeile über 88 Zeichen, keine impliziten String-Verkettungen über mehrere Zeilen ausser in Aufrufen mit Magic Trailing Comma. `LINT_WORKFLOW.as_posix()` und `PRECOMMIT_CONFIG.as_posix()` stehen dafür einmal als lokale Variablen am Anfang von `compare()`.

Der Eintrag fehlte in #73, weil #72 zeitgleich in dieselbe `[Unreleased]`-Sektion schrieb und ein zweiter Eintrag dort einen Konflikt erzeugt hätte — ausgerechnet in dem PR, der die Regel formuliert.

### Ergänzt — Qualitätsketten-Guard: die fünf Repos als Gruppe erkennbar

Die fünf Repos verweisen in ihren READMEs seit je aufeinander. Auf GitHub taten sie es nicht: Die Schnittmenge der Topics über alle fünf war **leer**. `mcp-continuous-auditor` trug überhaupt keine Topics, die vier Skills benutzten zwei Vokabulare (`claude-skill` gegen `claude-skills`), und eine Homepage hatte eines von fünf. Damit war die Zusammengehörigkeit genau dort unsichtbar, wo sie jemand findet, der nicht schon eines der Repos offen hat — in der Suche.

Dasselbe Muster wie bei `check_repo_description.py`, und aus demselben Grund: Metadaten ausserhalb der Arbeitskopie erreicht kein Test, also driften sie.

- **`docs/quality-chain.json`** — die Mitgliedschaft steht an einer Stelle: gemeinsames Topic, gemeinsame Homepage, fünf Mitglieder mit Phase und Leitfrage in beiden Sprachen.
- **`tools/check_quality_chain.py`** — prüft Topic, Homepage und Description aller fünf gegen das Manifest und druckt die fertigen `gh`-Kommandos. Er **schreibt nicht**: Topics zu setzen braucht ein Token mit Administrationsrechten, und Repo-Metadaten zu ändern gehört einem Menschen. Zwei Eigenschaften wiegen schwerer als die Einzelfälle — ein fehlendes Feld in der API-Antwort ist `UNVERIFIED` und nicht «keine Topics» (die Trennung, die `FID-006` verlangt), und eine nicht erreichbare API endet mit 1 statt mit «stimmt» (`DRIFT-003`).
- **`.github/workflows/quality-chain.yml`** — montags 06:41 UTC, versetzt zu `repo-description.yml` (06:23), damit sich die beiden nicht dasselbe Rate-Limit teilen. Bewusst nicht bei `pull_request`: Die Korrektur ist erst nach dem Merge möglich, ein PR-Gate bestrafte das falsche Ereignis.
- **`docs/hub-readme.md`** — Entwurf für ein optionales Hub-Repo `mcp-quality-chain`. Nötig ist es nicht: `github.com/topics/mcp-quality-chain` listet die fünf von selbst, sobald das Topic gesetzt ist.
- **28 Tests** in `tests/test_quality_chain.py`, davon acht allein auf der Eigenschaft, dass ein fehlendes Feld weder als Befund erfunden noch als Bestehen gelesen wird.

Der Guard läuft nur hier, prüft aber alle fünf Mitglieder — die vier Schwester-Repos brauchen dafür nichts.

### Ergänzt — die Kette steht jetzt auch in `SKILL.md`, nicht nur in den READMEs

Die Umbenennung darunter hat die Tabelle in beiden READMEs erneuert. `SKILL.md` nannte die Nachbar-Repos gar nicht — und das ist die Datei, die das Modell beim Audit tatsächlich bekommt. Wer ein Finding gegen `FID-003` schreibt, sollte ohne Umweg über das README wissen, welcher Skill die Behebung beschreibt.

Die Tabelle steht in «Übergabe & Folge-Skills», wo der Rückweg ohnehin hingehört, und trägt dieselbe dritte Spalte wie im README: nicht die Rolle des Repos, sondern **seine Regeln in diesem Katalog**. Für `mcp-transport-hardening` ist dort auch die Lücke benannt — seine Regeln 2 und 5–7 hat der Katalog nicht, und das ist von dieser Seite aus die nützlichere Information als eine ungefähre Zuordnung.

Derselbe Nachzug ist in den drei anderen Skill-Repos gelaufen: Die Kette stand überall im README und in keiner der Dateien, die der Skill selbst ausliefert. Der Guard aus dem Eintrag oben prüft weiterhin nur die READMEs — `SKILL.md` ist pro Repo verschieden aufgebaut und trägt bewusst eine repo-eigene dritte Spalte.

### Geändert — «Die Skill-Familie» heisst jetzt «Die MCP-Qualitätskette»

Die Tabelle nannte vier Skills plus `mcp-builder` und liess `mcp-continuous-auditor` weg. Der ist kein Skill, gehört aber in die Kette: Er ist das einzige Glied, das nach dem Audit weiterprüft, und `OPS-005` stammt aus ihm. Die Tabelle führt jetzt fünf Repos entlang des Lebenszyklus — vor dem Bau, im Bau, nach dem Bau, im Betrieb. `mcp-builder` steht daneben statt darin, weil es ein fremdes Repo ist und das gemeinsame Topic nicht tragen kann.

### Geändert — `OPS-005` bekommt eine fünfte Ausprägung: der Geltungsbereich des grünen Hakens

Die vier bisherigen Ausprägungen sind Abdeckungslücken — etwas lief nicht. Der Fall, der die fünfte auslöst, ist anders gelagert: Der Check lief, bestand, und war korrekt. Zu weit war nur, was aus ihm gelesen wurde. `ruff format --check .` belegt «formatgerecht unter der `line-length` dieses Repos»; gelesen wurde es als «formatgerecht». Für `scripts/check_version_sync.py`, das in 33 Repos liegt, war das zu wenig: eine 99 Zeichen lange Zeile, bei 100 einzeilig und grün, bei 88 mehrzeilig und rot. Der Bruch entstand beim Kopieren und fiel erst im Zielrepo auf, wo er wie ein Fehler am Skript aussah.

Die Mechanik dahinter stand seit `v1.5.0` in `SKILL.md` unter «Portfolio-Hygiene: ein Commit, 33 Repos» — und hat den Rückfall nicht verhindert. Das ist der eigentliche Befund: Die Sektion ist Anleitung für den, der ausrollt, und es gibt keinen Zeitpunkt, an dem etwas rot wird, wenn niemand sie liest. Der Check fragt deshalb nicht «kennt jemand die Regel», sondern «erzwingt die Pipeline sie». Dazu ein `Modus 3` in der Verifikation (Breiten auszählen, Kopien hashen, gegen jede Breite prüfen), ein Pass-Kriterium, zwei Anti-Patterns, ein Remediation-Schritt und die Gegenprobe — der neue Schritt muss anschlagen, **und** der gewöhnliche `ruff format --check .` muss dieselbe Zeile durchlassen; erst das belegt, dass er eine Lücke schliesst statt den lokalen Lint zu duplizieren.

Kein neuer Check: Ein eigener Eintrag bräuchte ein `applies_when` für «gehört zum Portfolio», das es im Profil nicht gibt — mit `always` liefe er bei jedem Einzelserver-Audit sinnlos durch. Als Ausprägung eines bestehenden Checks kostet er keine Applicability-Prüfung. Katalog-Zahlen unverändert, `evidence_required` und `severity` unverändert, `adoption` bleibt `advisory`. Kein Re-Audit-Auslöser nach §5: keine Severity angehoben, keine `applies_when` erweitert. Das ergänzte Pass-Kriterium ist neu, blockiert aber als `advisory` nicht.

### Geändert — `SKILL.md` Portfolio-Hygiene: 110 fehlte in der Breitenliste

Die Sektion nannte «88, 100 und 120», und die Prüfschleife lief über genau diese drei. Ein Durchlauf über alle 43 Portfolio-Repos zeigt vier Breiten: 24-mal 100, 5-mal 120, **2-mal 110** (`sbb-opendata-mcp`, `termdat-mcp`), 1-mal 88 (`swiss-snb-mcp`, ohne Eintrag und damit auf dem ruff-Default). Die Zahlen stehen jetzt mit Beleg in der Sektion, die Schleife prüft vier Werte.

Praktisch ändert das wenig — wessen zusammengezogene Form in 88 Spalten passt, hält bei jeder Breite darüber —, aber die Sektion behauptete eine vollständige Aufzählung und war es nicht. Die Formulierung sagt jetzt «jede Breite ab 88» statt «alle drei Breiten», damit die Regel nicht wieder an einer Liste hängt. Dazu ein Absatz am Ende, der auf `OPS-005` verweist: Die Sektion beschreibt die Regel, der Check erzwingt sie.

### Geändert — Ruff-Regelsatz auf den Portfolio-Standard angehoben

Der Regelsatz startete bewusst schmal (`E4`, `E7`, `E9`, `F`), damit die Einführung von Ruff nicht an über hundert Befunden hängenblieb. Er steht jetzt auf demselben Satz wie das übrige Portfolio: zusätzlich `I` (Import-Sortierung), `UP` (pyupgrade), `B` (bugbear), `C4` (comprehensions), `SIM` (simplify) und `RUF`. `RUF001`–`RUF003` bleiben aus — die deutsche Prosa nutzt bewusste Typografie (—, –, →), die diese Regeln als Verwechslungszeichen melden würden.

113 Befunde, davon 98 automatisch behoben. Die beiden grössten Gruppen sind rein mechanisch: 37 × `UP009` (`# -*- coding: utf-8 -*-`, in Python 3 ein No-op, da UTF-8 ohnehin die Standard-Quellcodierung ist) und 29 × `I001` (Import-Sortierung). **Diese Zeilen haben nichts mit dem Laufzeit-Encoding zu tun** — dafür sorgen weiterhin `PYTHONUTF8=1` und `force_utf8_stdio()`, beide unangetastet.

19 × `UP017` ersetzt `timezone.utc` durch `datetime.UTC`. Das ist ab Python 3.11 verfügbar; `target-version` steht auf `py311` und die Matrix fährt 3.11 und 3.13.

15 Befunde brauchten Handarbeit, drei davon mit inhaltlicher Wirkung:

* **`B904` (2 ×, `tools/tracker_sync.py`)** — die `TrackerError` der Notion-Anbindung verdeckte bisher ihre Ursache. Jetzt `raise … from e`, womit im Traceback sichtbar bleibt, ob ein `HTTPError` oder ein `URLError` dahintersteht. Für einen Katalog, der mit `OBS-007` Fehler-Diagnostizierbarkeit verlangt, war das die eigene Baustelle.
* **`RUF012` (3 ×)** — veränderliche Klassenattribute (`FIELD_MAP`, `FAIL_HIGH`, `PREVIOUSLY_BUGGY_CHECKS`) tragen jetzt `ClassVar`.
* **`RUF043`** — `pytest.raises(match="summary.json not found")`: der Punkt ist ein Regex-Metazeichen und hätte auf jedes Zeichen gepasst. Jetzt maskiert.

Der Rest ist Kosmetik: sechs ungenutzte Entpackungen mit `_`-Präfix gekennzeichnet, zwei Listen-Konkatenationen entpackt, ein `if`/`else` zum Ternär.

Testsuite unverändert 441 bestanden, Smoke-Test exit 0.

### Behoben — Setup-Anleitung war in PowerShell nicht lauffähig

`pip install pre-commit && pre-commit install` in beiden READMEs: `&&` ist in PowerShell 5.1 ein Syntaxfehler. Jetzt zwei Zeilen, gültig in Bash wie in PowerShell — passend dazu, dass das Repo Windows ausdrücklich unterstützt und die Test-Matrix dort läuft.

### Ergänzt — `ARCH-014`: Retry-Politik gegenüber der Quelle

Beim Formulieren von `OBS-007` fiel auf, dass der Katalog zwar regelt, was in der Meldung steht, wenn alle Versuche verbraucht sind, aber nirgends, **was, wie schnell und wie lange** überhaupt wiederholt wird. `Retry-After` kam in keinem der 94 Checks vor, `429` nur als Beispiel für einen Execution-Error in `OBS-001`.

Der neue Check verlangt: keine Wiederholung bei 4xx ausser 429; gestreuten Backoff; `Retry-After` gelesen und der eigenen Kurve vorgezogen; ein Gesamtbudget in Sekunden, das **unter** dem Timeout des aufrufenden MCP-Clients liegt; Wiederholung auf genau einer Ebene (Transport-Retries stapeln sich multiplikativ); und eine gekennzeichnete Degradation statt stiller alter Zahlen.

Der Portfolio-Durchlauf über zehn Server begründet die Adoptionsstufe: Acht haben einen Retry-Pfad, **keiner** liest `Retry-After`, **keiner** streut seinen Backoff. Drei Server sahen zunächst nach Jitter aus — zweimal war es das Wort «uniform» in einem Prosa-Kommentar, einmal ein eigener Rate-Limiter, der 429 *aussendet*, statt ihn zu lesen. `enforced` am Tag des Merges wäre ein rotes Portfolio, und das ist der Weg, auf dem Checks zurückgenommen statt übernommen werden.

`high`, `adoption: advisory`, `applies_when: tools_make_external_requests == true`. Einordnung unter `ARCH` neben `ARCH-010` (ist eine Wiederholung *sicher*) und `ARCH-013` (derselbe ausgehende Pfad); dieser Check fragt, ob sie *angemessen* ist.

Katalog: 94 → 95 Checks, `ARCH` 13 → 14.

### Geändert — `OBS-007` auf `enforced` promoviert

Derselbe Durchlauf hat die Annahme widerlegt, mit der `OBS-007` advisory startete. Acht der zehn Server haben einen Retry-Pfad; **zwei** davon verletzen den Check:

| Server | Befund |
|---|---|
| `lindas-mcp` | `f"Last error: {last_error}."` — bei `ConnectError` leer, und darunter folgt «this often means the query was too broad», eine Ursachenbehauptung, die dann nachweislich nicht zutrifft |
| `termdat-mcp` | `log.error("termdat.unreachable", attempts=…, error=str(last_error))` ohne `error_type`; die Retry-Zeile eine Ebene darüber verwendet `error=type(exc).__name__` korrekt |

Die übrigen sechs bestehen, und zwar aus einem Grund, der den Check schärft: `raise last_exc` reicht die ursprüngliche Exception samt Typ und Traceback weiter und erfüllt ihn automatisch. Verletzt wird er nur beim **Einpacken** in eine neue Meldung. Der Check ist damit eng geschnitten und hatte im Sample keine falschen Positive — ein Check, der weder breit streut noch daneben trifft, gewinnt durch Nichtblockieren nichts mehr.

Beide Fail-Muster sind jetzt in `OBS-007` aufgenommen. Der `log.error(..., error=str(exc))`-Fall fehlte, weil ein strukturiertes Event mit gefülltem `attempts`-Feld vollständig aussieht: ein leeres `error`-Feld fällt in JSON weniger auf als in einem Satz.

Advisory-Brücke danach: `ARCH-014` und `OPS-005`.

### Ergänzt — Ruff, ein `lint`-Workflow und ein Guard auf die eigenen Pins

Das Repo war ungelintet und unformatiert: 37 Python-Dateien, kein Ruff, kein Lint-Job. Neu gibt es `ruff.toml`, `.github/workflows/lint.yml` und Pre-Commit-Hooks, die diesen Job lokal vorziehen.

Der Regelsatz ist bewusst schmal — exakt der, den Ruff heute per Default aktiviert (`E4`, `E7`, `E9`, `F`). Er steht trotzdem explizit in der Konfiguration, weil ein `select` die eingebauten Defaults vollständig ersetzt und der erzwungene Satz damit stabil bleibt, auch wenn eine spätere Ruff-Version ihre Defaults ändert. Der strengere Satz aus dem übrigen Portfolio (`I`, `UP`, `B`, `C4`, `SIM`, `RUF`) hätte 101 Befunde gekostet statt 12; ihn nachzuziehen bleibt ein eigener Commit.

Die Formatierung liegt getrennt in einem reinen `style:`-Commit — 36 von 37 Dateien, ohne jede inhaltliche Änderung. Belegt ist das nicht durch Zusicherung, sondern durch einen AST-Vergleich vor und nach dem Lauf: 35 Dateien exakt identisch, bei `tools/agent_run_log.py` normalisiert Ruff die Einrückung eines Docstrings, und ein zweiter Vergleich mit whitespace-normalisierten String-Konstanten zeigt, dass das der einzige Unterschied ist.

`tools/check_ruff_pin.py` schliesst die Lücke, die der Hook selbst aufmacht. Ruff ist jetzt an zwei Orten gepinnt — `rev:` im Hook und `ruff==` im Workflow. Laufen sie auseinander, formatiert der Hook nach der einen und die CI prüft nach der anderen Version: der Hook meldet grün, die CI wird rot. Abgesichert wäre das sonst nur durch einen Kommentar, der darum bittet, beide zusammen zu bumpen — dieselbe Bauart von Lücke, gegen die `DRIFT-003` steht.

Der Guard folgt der Hausform von `check_repo_description.py`: `compare()` ist eine reine Funktion über zwei Strings, ohne Dateisystem testbar, und ein fehlender Pin ist ein Befund statt eines stillen Bestehens. Zehn Tests decken das ab, darunter der Fall, dass die `rev` eines *anderen* pre-commit-Repos nicht mit Ruffs verwechselt wird, und ein Test gegen die echten Repo-Dateien — sonst wäre der Guard grün, ohne auf das Format zu passen, das er prüfen soll.

Die Testsuite bleibt unverändert bei 431 bestandenen Tests, dazu die 10 neuen.
### Ergänzt — `OBS-007`: maskiert nach aussen, aussagekräftig nach innen

`OBS-002` verlangt, dass Fehler-Details das LLM nicht erreichen, und verweist sie ins Server-Log. Was dort ankommt, prüfte der Katalog nicht. Der neue Check schliesst die Gegenrichtung: Der Text, den der Server für sich behält, muss etwas sagen.

Der Fundort ist `swiss-efv-mcp` ([#16](https://github.com/malkreide/swiss-efv-mcp/pull/16)). Die nächtliche Live-Suite scheiterte an einer Netzstörung, viermal mit derselben Meldung:

```
RuntimeError: Upstream unreachable after retries:
```

Satzende. Ursache: `httpx.ConnectTimeout`, `ReadTimeout` und `ConnectError` tragen ein leeres `str()`, und `f"...: {last_error}"` expandiert entsprechend zu nichts. Weder Fehlermodus noch Ziel noch Anzahl Versuche — also keine der drei Angaben, wegen derer man die Meldung liest. Der Server erfüllte `OBS-002` mustergültig; die Maske sass, dahinter stand nichts.

Bemerkenswert ist weniger der Einzelfall als die Klasse: Ein Text, der nach aussen maskiert wird, hat im Normalbetrieb keinen Leser. Er wird genau einmal gebraucht, im Störungsfall, und bis dahin bemerkt niemand, dass er leer ist. Das ist die Nebenwirkung des eigenen Rats, und `f"...: {exc}"` ist dabei die naheliegende Schreibweise, kein Ausrutscher.

Der Check verlangt Exception-Typ, benanntes Ziel (ohne Query-String und Credentials, `SEC-013`), Anzahl Versuche, `raise ... from` — und einen Test auf den Fall `str(exc) == ""`, ohne den der Text beim nächsten Refactoring wieder verfällt.

`medium`, `adoption: advisory`, `applies_when: tools_make_external_requests == true`. Advisory, weil das beanstandete Muster mutmasslich breite Teile des Portfolios trifft: Der Check meldet, blockiert aber nicht, bis ein Portfolio-Durchlauf zeigt, ob er richtig geschnitten ist. Damit stehen zwei Checks auf der Brücke (`OBS-007`, `OPS-005`).

Katalog: 93 → 94 Checks, `OBS` 6 → 7.

### Ergänzt — `OPS-001`: was die Live-Suite kostet, wenn die Quelle schweigt

Derselbe Vorfall, zweiter Befund. `OPS-001` begründet die Trennung von Unit- und Live-Tests unter anderem damit, dass Live-Tests bei Outages scheitern. Was sie dabei **kosten**, stand nirgends — `timeout-minutes` kam in keinem der 93 Checks vor, und das Nightly-Beispiel des Checks hatte selbst keins.

Bei `swiss-efv-mcp` legte jeder Live-Test einen eigenen Client an. Damit war der Cache wirkungslos, und die Retry-Leiter (4 Versuche × 60 s plus Backoff, rund 254 s) lief pro Test erneut: vier Tests, 17 Minuten, für die Information «Host nicht erreichbar». Nach der Umstellung auf einen geteilten Client 10 Sekunden.

Neu in `OPS-001`: Modus 5 mit zwei greps, drei Pass-Kriterien (`timeout-minutes` im Live-Workflow, geteilter Client samt Teardown, Test-Timeouts enger als die Prod-Defaults), drei Zeilen in *Common Failures* und ein Remediation-Schritt. Der Nebeneffekt ist nicht nur Laufzeit: Ohne geteilten Client lädt jeder Test denselben Dump erneut — vermeidbare Last auf fremder, meist unfinanzierter Open-Data-Infrastruktur.

Keine Änderung an Severity oder Reichweite von `OPS-001`; die neuen Kriterien erweitern das Prüfkriterium und lösen damit Re-Audit-Fall (c) aus.

### Ergänzt — §5 kennt jetzt den Promotionsfall (`d`)

Punkt 5 der Katalog-Versionierung nannte drei Re-Audit-Auslöser: Severity angehoben (a), `applies_when` erweitert (b), Prüfkriterium korrigiert (c). Bei der Promotion von `DEP-001` auf `enforced` in v1.5.0 traf **keiner** davon zu — Severity blieb `high`, Reichweite blieb `always`, das Kriterium blieb Wort für Wort. Nach dem Buchstaben der Regel wäre die Re-Audit-Liste leer gewesen, während in Wahrheit jeder Server mit einer ungedeckelten Range in diesem Moment seine Production-Readiness verlor.

Der Grund ist strukturell: **Die Adoptionsstufe ist der einzige Hebel im Katalog, der ein Verdikt kippt, ohne dass sich ein Feld ändert, das die Regel las.** Genau dieselbe Lehre wie bei b) und c) in v1.3.0, eine Achse weiter — dort war der Auslöser, dass ein Release ohne jede Severity-Änderung trotzdem zwei Re-Audit-Gründe hatte.

Neu als **d)**, mit den drei Abgrenzungen, die sonst nachgefragt würden:

- Nur bei `critical`/`high`. Bei `medium`/`low` blockierte auch vorher nichts, die Promotion ändert an keinem Verdikt etwas — deshalb war `DRIFT-006` kein Auslöser und `DEP-001` einer.
- Die Gegenrichtung (Demotion auf `advisory`) löst kein Re-Audit aus, kann aber ein Verdikt nachträglich grün machen. Das gehört in den CHANGELOG, nicht in die Warteschlange — dieselbe Konstruktion wie bei b).
- Betroffen sind Audits, deren `production_ready: true` sich darauf stützte, dass dieses Finding nicht zählte.

Dazu zwei Stellen, die auf den Fall zeigen mussten: §2.3 Schritt 3 verweist jetzt auf §5d, und die zweite Eselsbrücke zu Punkt 5 nennt die vierte Achse («…oder ob der Befund noch folgenlos bleibt»).

**Miterledigt, weil derselbe Diff die Stelle berührt:** §2.3 Schritt 3 hält jetzt auch fest, was gilt, wenn Schritt 2 übersprungen wird — eine Promotion ohne dazwischenliegenden Portfolio-Durchlauf stützt sich auf «Rückstand bewusst akzeptiert» und nicht auf ausgewertete Advisory-Findings. Welches von beidem gilt, gehört in den CHANGELOG-Eintrag; eine Promotion, die Evidenz behauptet, die nicht erhoben wurde, ist der Fehler aus `OPS-004`. Genau dieser Fall lag bei `DEP-001` vor und steht dort auch so.

Reine Prozess-Regel, kein Check angefasst: 93 Checks in zwölf Kategorien, alle `applies_when`, `severity` und `adoption` unverändert, 431 Tests.

## [v1.5.0] — 2026-08-02 — Schweigen ist kein Freispruch

**Drei neue Checks** (`IDENT-007`, `DEP-001`, `DRIFT-006`) mit der neuen Kategorie `DEP` — der Katalog wächst von 90 auf **93** —, **zwei erweiterte** (`FID-003`, `IDENT-001`), ein abgegebener Prüfgegenstand (`IDENT-006`) und mit §2.6 eine Regel, die für den Katalog selbst gilt.

Der Titel ist die Eselsbrücke aus §2.6, und er beschreibt die Herkunft fast aller Einträge unten. Jeder von ihnen kommt aus einem Fall, in dem nichts gemeldet wurde und das als Freispruch gelesen wurde: `IDENT-001` erklärte 24 Pakete für unauffällig, von denen 16 drifteten; bei `IDENT-007` stimmten die Versionsnummern und die Installation war tot; `DEP-001` änderte das Artefakt ohne einen einzigen Commit; und `FID-003` liess einen abgewiesenen Request als Leermenge durchgehen — mit dem Hinweis, die Suche zu verbreitern. Vier verschiedene Ebenen, eine Fehlerform.

Kein Re-Audit-Auslöser nach §5 der Katalog-Versionierung; die Begründung steht unter «Katalog-Zahlen».

> **Zur Lesart der Zahlen in diesem Abschnitt:** Jeder Eintrag nennt den Katalogstand *zum Zeitpunkt seiner Änderung*. Die Einträge weiter unten sagen deshalb «90 Checks in 11 Kategorien», und das war dort richtig. Der Stand, den dieses Release ausliefert, steht hier oben: **93 Checks in zwölf Kategorien, 431 Tests.**

### Geändert — `DEP-001` und `DRIFT-006` sind `enforced`

Beide gingen den Weg aus §2.3: als `advisory` gemergt, jetzt promoviert. Die Advisory-Liste steht damit wieder bei einem Eintrag (`OPS-005`) — so sieht eine leere Brücke aus, nicht eine abgeschaltete.

**Was sich dadurch tatsächlich ändert, ist nur bei einem der beiden etwas.** `DRIFT-006` trägt `medium`; blockierend sind nur `critical` und `high`, das Finding wurde also schon vorher gezählt und geführt und ändert an keinem Verdikt etwas. `DEP-001` trägt `high` und `applies_when: always`: **Ab jetzt verliert jeder Server mit einer ungedeckelten Range auf einer Abhängigkeit, aus der er importiert, seine Production-Readiness.** Nach dem Befund, der den Check ausgelöst hat, ist das kein Randfall, sondern der Normalzustand im Portfolio.

**Offen gesagt, welcher Schritt übersprungen wurde.** §2.3 sieht zwischen Merge und Promotion einen Portfolio-Durchlauf vor, dessen Advisory-Findings zeigen, ob der Check richtig geschnitten ist. Dieser Durchlauf hat nicht stattgefunden — zwischen dem Merge beider Checks und dieser Promotion liegt keiner. Die Promotion stützt sich deshalb nicht auf ausgewertete Advisory-Findings, sondern auf den zweiten in §2.3 genannten Grund: **der Rückstand ist bewusst akzeptiert.** Das ist zulässig und die Entscheidung der Maintainerin; unausgesprochen zu lassen, worauf sie sich stützt, wäre der Fehler, den `OPS-004` beschreibt.

**Re-Audit-Folge.** §5 nennt drei Auslöser — Severity angehoben, `applies_when` erweitert, Prüfkriterium korrigiert. Eine Promotion ist keiner davon *wörtlich*, für die betroffenen Server aber von 5a nicht zu unterscheiden: Ein blockierender Check greift, wo vorher keiner griff. Für `DEP-001` (`high`) gilt deshalb ausdrücklich, was 5a anordnet — bestehende Audit-Ergebnisse sind insoweit nicht mehr gültig. Für `DRIFT-006` (`medium`) nicht, weil dort nie etwas blockierte. Dass §5 den Fall nicht selbst benennt, ist eine Lücke in der Regel und kein Grund, die Folge hier auszulassen.

Nachgezogen: der Pin in `tests/test_adoption_stage.py` und der Advisory-Satz in beiden READMEs. Keine Katalog-Änderung im Übrigen: 93 Checks in zwölf Kategorien, alle `applies_when` und `severity` unverändert, 431 Tests.

### Ergänzt — `FID-003` gilt in beide Richtungen: ein Fehlschlag ist keine Leermenge

`FID-003` führte «Leermenge als `isError` maskiert» seit dem ersten Tag als Anti-Pattern. Die Gegenrichtung stand nirgends, und sie ist die häufigere: **Ein Transport- oder Autorisierungsfehler kommt bei der aufrufenden Schicht als Fehlschlag ohne Daten an — also wie eine Leermenge**, und wer nur prüft, ob Datensätze da sind, reicht ihn als solche durch.

Gemessener Fall aus dem Transport-Vorfall: Eine Anfrage mit fremdem Host-Header bekommt `HTTP 421` mit dem Body `Invalid Host header` (Ursache in `SEC-016` und `SEC-024`). Daraus wird ein Result mit `returned: 0` — und, wenn der Server diesen Check sonst sauber erfüllt, mit dem Hinweis aus genau dieser Prüfung: Wildcard versuchen, Felder erweitern. Der Hinweis zeigt dann auf die Query, während die Abfrage nie angekommen ist. **Ein Konfigurationsfehler unterläuft damit den Check, der das Raten verhindern soll** — die Umsetzung macht den Fall schlimmer als die Nicht-Umsetzung.

Kein neuer Check, nach §2.5 Frage 2: Es fehlte keine Dimension, die Verification griff nur auf einen Pfad. Die Gegenprobe zum Sammelbehälter fällt hier eindeutig aus — das Kriterium ist dasselbe (was das Modell sieht, wenn keine Datensätze kommen) und in einem Schritt behebbar (Fehlerkanal statt Result).

Dazu ein dritter Verifikationsmodus, weil dieser Pfad ohne Bestand prüfbar ist: den Abruf gezielt scheitern lassen und schauen, was am Tool ankommt. `isError` mit Konfigurations-Meldung ist `pass`, jedes wohlgeformte `returned: 0` ist `fail` — und lief das Harness nicht, ist es `todo`, nicht `pass` (§2.6). Katalogstand unverändert: 93 Checks in zwölf Kategorien.

### Hinzugefügt — `IDENT-007`: das veröffentlichte Artefakt startet in einer leeren Umgebung

Die Gesundheits-Achse, die `IDENT-006` im Eintrag weiter unten dazubekommen hat, ist jetzt ein eigener Check. Der Auslöser ist ein zweiter Fall derselben Klasse, diesmal bei `swiss-energy-mcp`: **Die Versionsnummern stimmten überein, der Gap-Check war zufrieden — und die Installation war trotzdem tot.** Nicht weil die Prüfung falsch gerechnet hätte, sondern weil sie eine andere Frage beantwortet.

Zwei Checks statt einem, weil §2.5 des Skills genau dieses Signal nennt: Sobald eine Erweiterung ein «oder» in die Pass-Criteria zwingt, das mit dem ursprünglichen Kriterium nichts zu tun hat, ist es ein neuer Check. `IDENT-006` hatte seit dem Umbau zwei Achsen, zwei Kriterienblöcke, zwei Befundcode-Tabellen und zwei Remediation-Stränge — und ein Verstoss auf der einen Achse war in einem Schritt behebbar, auf der anderen nicht. Ab jetzt:

| Check | Frage | Ist die Antwort messbar aus Metadaten? |
|---|---|---|
| `IDENT-006` | Hat jemand vergessen zu publizieren? | ja — Versionsnummern in Repo, Tag und Index |
| `IDENT-007` | Läuft das, was auf dem Index liegt? | nein — nur durch Installieren und Starten |

Neu gegenüber der Fassung in `IDENT-006` ist vor allem **die Umgebung als Teil des Kriteriums**. «Frisch» genügt nicht; die Umgebung muss *leer* sein. Ein venv mit dem Lockfile des Repos pinnt genau die Verschiebung weg, die den Vorfall ausmacht, und ein `pip install -e .` prüft den Branch — also das, was CI ohnehin prüft. Dazu ein dritter Modus, der fragt, ob die Prüfung **wiederkehrend** läuft: Der Zustand kann sich ohne Commit ändern, deshalb ist eine einmalige Messung hier ein Datum und kein Ergebnis.

`IDENT-007` ist **`enforced`**, nicht `advisory`. Der Weg über die Advisory-Stufe (§2.3) existiert, damit eine *neue Forderung* das Portfolio nicht am Merge-Tag rot färbt. Diese Forderung ist nicht neu — sie stand seit dem letzten Eintrag als Achse 1 in `IDENT-006` und war dort blockierend. Sie als `advisory` einzutragen wäre eine stille Demotion, also genau das, wovor die Adoptionsstufe schützen soll.

### Hinzugefügt — Kategorie `DEP` mit `DEP-001`: Obergrenzen für Abhängigkeiten, die den Import tragen

`mcp[cli]>=1.28.1` sieht aus wie eine Mindestanforderung und ist eine Vollmacht. Am 2026-07-28 erschien `mcp` 2.0.0 und entfernte `mcp.server.fastmcp` ersatzlos; von da an löste jede frische Installation zweier Portfolio-Server eine Major-Version auf, gegen die ihr Code nicht lief. **Kein Commit, kein roter Test, kein Release — und trotzdem ein anderes Artefakt.**

Bisher stand das als Anti-Pattern-Zeile und als Remediation-Schritt in `IDENT-006`. Das war zu wenig: Es ist keine Nachbemerkung zu einem Release-Problem, sondern die Ursache einer eigenen Fehlerklasse, und sie ist an einer anderen Stelle zu beheben (`pyproject.toml`, nicht der Release-Prozess). Nach §2.5 ist das die dritte Frage mit «ja» — eine eigene Prüfdimension, kein zu enger Zuschnitt eines bestehenden Checks. Die Kategorie `DEP` heisst deshalb nicht «Dependencies», sondern steht für den **Auflösungsraum des publizierten Artefakts**: den Bereich, den das Paket der Zukunft offenlässt.

Der Check verlangt ausdrücklich **nicht**, alles zu deckeln — das hält Sicherheitspatches zurück und macht den Server mit anderen Paketen unvereinbar. Gedeckelt gehört, was beim Major-Wechsel den Import bricht: Abhängigkeiten, aus deren Modulpfaden importiert wird, deren Typen abgeleitet werden, und das SDK ausnahmslos. Und weil ein `<3` nach zwei Jahren kein Schutz mehr ist, sondern der Grund für eine tote Major-Version, sind Deckel und automatisierter Anhebungs-PR ein Paar — das steht als Kriterium drin, nicht als Empfehlung.

Drei Mechanismen, die den Vorfall nicht verhindert hätten und regelmässig dafür gehalten werden, stehen als Tabelle im Check: das Lockfile (gilt für die Entwicklungsumgebung), grüne CI (löst nicht auf, was heute aufgelöst würde) und ein frisch geschnittenes Release (die Range wirkt beim Installieren, nicht beim Publizieren).

`DEP-001` ist **`advisory`**: eine neue Forderung, die am Merge-Tag einen grossen Teil des Portfolios träfe. Das ist der Fall, für den §2.3 die Stufe vorsieht.

### Hinzugefügt — `DRIFT-006`: der CHANGELOG darf dem Code nicht widersprechen

Bei `swiss-energy-mcp` stand im `[Unreleased]`, die Migration auf 2.x bleibe «a separate, deliberate piece of work». Sie war längst gemergt. Der Satz hatte den PR überlebt, der ihn widerlegte.

**Prosa, die dem Repo widerspricht, ist schlimmer als fehlende Prosa.** Eine Lücke führt dazu, dass jemand nachsieht; ein falscher Satz führt dazu, dass niemand nachsieht — er beantwortet die Frage plausibel, bevor sie gestellt wird. Im Fall oben lieferte er zusätzlich eine fertige Erklärung für einen dringenden Zustand: Ein Artefakt, das auf dem Index nicht mehr startete, sah aus wie die bekannte, bewusst zurückgestellte Migration statt wie ein Ausfall. Die falsche Prosa war die Deckung, unter der ein Befund liegen blieb.

Derselbe Mechanismus wie in `DRIFT-003`, eine Ebene höher: Dort erfüllt der Degradationspfad die Assertion, hier erfüllt die veraltete Absicht die Frage. Beide Male sieht der Ausfall aus wie der erwartete Fall — deshalb steht der Check in `DRIFT` und nicht in `IDENT`.

Abgegrenzt gegen die beiden Nachbarn: `IDENT-004` prüft eine **Zahl** in der Doku (mechanisch vergleichbar, per Skript erzwingbar), `IDENT-006` prüft, ob `[Unreleased]` zu **alt** ist. `DRIFT-006` prüft, ob der Inhalt **wahr** ist. Für diesen dritten gibt es kein Skript — Zahlen lassen sich vergleichen, Sätze nicht —, und genau deshalb überlebt die Sorte Fehler am längsten. Der Check sagt das über sich selbst: Sein `grep`-Modus sammelt Kandidaten und **eine leere Trefferliste ist kein Pass**, weil ein Absichtssatz ohne jedes Schlüsselwort auskommt.

Ebenfalls `advisory`, aus demselben Grund wie `DEP-001`.

### Geändert — `IDENT-006` gibt die Gesundheits-Achse ab und misst nur noch den Abstand

Die Lücken-Kriterien bleiben Wort für Wort. Entfernt sind Achse 1 (installiert/importiert/startet/antwortet), ihre Befundcodes und die zugehörige Remediation — sie stehen jetzt in `IDENT-007`. Was bleibt, sagt der Check jetzt explizit über sich: Er vergleicht **Etiketten**, und drei gleiche Etiketten heissen genau eines — niemand hat vergessen zu publizieren.

Der Abschnitt «Was dieser Check nicht sagt» führt den Fall vor, der die Trennung erzwungen hat: `zurich-opendata-mcp` `0.5.1` bestand **jedes Kriterium dieses Checks** und war tot. Ein grünes `IDENT-006` war dort die Wahrheit und trotzdem wertlos. Als Kriterium ergänzt: `IDENT-007` wurde separat beantwortet und ein Pass hier nicht als Beleg dafür verbucht.

Modus 1 ist damit wieder `--metadata-only` — die billige Hälfte, zwei Requests und etwas Git. Der Aufruf ohne das Flag ist ab jetzt `IDENT-007`.

### Geändert — `IDENT-001` vergleicht den Produkt-Token normalisiert

Zwei von 33 Paketen im Sweep senden einen Produkt-Token, der nicht der Dist-Name ist:

| Dist-Name | gesendeter Token |
|---|---|
| `swisstopo-mcp` | `SwisstopoMCP/…` |
| `zurich-opendata-mcp` | `ZurichOpenDataMCP/…` |

Beide sind korrekt — der Token identifiziert den Server eindeutig. Falsch war der **Vergleich**: Das vorgeschriebene Muster `<dist>/<Ziffer>.<Ziffer>` trifft `SwisstopoMCP/0.3.1` nicht. Bei genau diesen beiden Servern fiel der Check also entweder in «kein User-Agent gefunden» oder — schlimmer — in die Befundklasse für *fremde* User-Agents, die für gefälschte Browser-Kennungen reserviert ist.

Das ist die unangenehme Stelle: Ausgerechnet ein Server, der seinen User-Agent als Literal führt, wurde von der Literal-Suche nicht gesehen. Der Check war dort blind für genau das, wogegen er existiert. Zwei von 33 ist keine Randerscheinung, sondern eine Schreibweise, die jeder zweite Autor plausibel findet.

**Neu: vor dem Vergleich normalisieren** — `casefold`, Trennzeichen entfernt, auf beiden Seiten, und nur für die Identität des Tokens; die Versionsnummer daneben wird weiter exakt verglichen. Der `grep` in Modus 1 macht dasselbe (`-i`, jeder Trenner optional), mit dem bisherigen wörtlichen Aufruf als Gegenbeispiel daneben. Dazu zwei Grenzen, die mit drinstehen: Weiter zu normalisieren, bis irgendetwas passt, macht die Prüfung wertlos (`Mozilla` muss fremd bleiben) — und ein Token, der auch normalisiert nicht passt, ist `unverified` und von Hand zuzuordnen, weder Pass noch automatisch «fremd».

### Hinzugefügt — `SKILL.md` §2.6: «Ein Check, der nichts findet, muss sagen können, ob er gesucht hat»

Die Regel hinter `unverified` in der Identitäts-Probe, jetzt als Regel für den **Katalog selbst**. Ein Check hat drei Ausgänge, nicht zwei, und der dritte — «nicht gesucht, oder gesucht und die Form nicht erkannt» — verschwindet in der Praxis ohne Zutun: «nichts gefunden» und «nicht hingeschaut» erzeugen dieselbe Beobachtung, nämlich eine leere Ergebnisliste. Zusammenfallen tun sie immer nach `pass`, weil ein Werkzeug meldet, was es findet, und nicht, was es nicht gesucht hat.

Der Beleg steht in `IDENT-001`: Die erste Fassung der Probe erklärte **24 Pakete für unauffällig, von denen 16 drifteten**. Kein Fehler in der Vergleichslogik — sie erkannte die Form des User-Agents nicht und meldete nichts. Nichts las sich als «in Ordnung». Zwei Drittel der Befunde gingen an dieser Stelle verloren, und die Zusammenfassung war grün.

Vier Konsequenzen für jeden Check im Katalog stehen im Abschnitt: ein Ausgang für «Harness lief nicht» in jedem `automated`-Modus (auf `todo`, nie auf `pass`); eine Pass-Criterion der Form «kein X gefunden» muss sagen, wie gesucht wurde; wo die Erkennung selbst scheitern kann, gehört das als eigener Befundwert in den Check; und die Gegenprobe gegen ein Repo, in dem der Verstoss sicher vorliegt. Verhältnis zu `OPS-005`: dieselbe Asymmetrie, andere Adressaten — `OPS-005` prüfen wir an fremden Repos, §2.6 schulden wir dem eigenen Katalog.

Dazu ein Anti-Pattern («Das Werkzeug hat nichts gemeldet, also ist der Check bestanden»), ein Punkt in der Qualitätschecklist und die Eselsbrücke *«Schweigen ist kein Freispruch.»*

### Hinzugefügt — `SKILL.md`: Portfolio-Hygiene für gemeinsam ausgerollten Code

Findings aus diesem Katalog treffen selten einen Server allein; die Remediation ist dann einmal geschrieben und 33-mal angewandt. Im Portfolio stehen `line-length` 88, 100 und 120 nebeneinander, und `ruff format` zieht einen Ausdruck zusammen, sobald er passt — beides für sich harmlos, zusammen der Grund für **einen roten CI-Lauf und 33 Force-Pushes**: Der Patch war in einem 120er-Repo geschrieben und getestet, sah überall gleich aus und war in jedem 88er-Repo nicht formatkonform.

Die Regel steht als eigener Abschnitt, und sie ist etwas schärfer formuliert als «für 88 schreiben»: Weil der Formatter in beide Richtungen arbeitet — umbrechen bei zu schmal, zusammenziehen bei zu breit —, hält ein identischer Text nur dann überall, wenn seine **zusammengezogene Form in 88 Spalten passt**. Dann hat kein Formatter etwas zu tun und alle drei Breiten erzeugen dasselbe. Praktisch: eine Zwischenvariable, ein kürzerer Bezeichner, eine Anweisung mehr. Dazu die Prüfschleife über alle drei Breiten vor dem Ausrollen, der zulässige Ausweg (pro Repo formatieren lassen — kostet aber die Vergleichbarkeit der 33 Diffs) und die Eselsbrücke *«Der schmalste Wert im Portfolio schreibt den Code.»*

### Katalog-Zahlen

**90 → 93 Checks, 11 → 12 Kategorien.** `IDENT` 6 → 7, `DRIFT` 5 → 6, neue Kategorie `DEP` mit 1. Severity-Verteilung 16 critical · 45 high · 31 medium · 1 low. Advisory sind jetzt drei statt einem: `OPS-005`, `DEP-001`, `DRIFT-006` — der Pin in `tests/test_adoption_stage.py` ist entsprechend erweitert, mit der Begründung, warum `IDENT-007` nicht dazugehört.

Kein Re-Audit-Auslöser nach §5 der Katalog-Versionierung: keine Severity angehoben, keine `applies_when` erweitert, kein Prüfkriterium korrigiert. `IDENT-007` trägt eine Forderung weiter, die als Achse 1 von `IDENT-006` bereits blockierend war; `DEP-001` und `DRIFT-006` blockieren als `advisory` nicht. Mitgezogen: die Kategorienliste im Slash-Command (sie ist Instruktion, nicht Doku), beide READMEs samt Provenance-Zeilen, `docs/roadmap.md` und die vier Guard-Tests. Das Muster für die Provenance-Zeilen in `test_readme_counts.py` kennt jetzt auch die Einzahl — «1 Check (`DEP-*`)» wäre sonst ungeprüft durchgelaufen, was §2.6 in eigener Sache wäre.

431 Tests, unverändert grün.

### Geändert — der Blindfleck aus `IDENT-006` in den übrigen `IDENT`-Checks

Nach dem Umbau von `IDENT-006` wurden `IDENT-001` bis `IDENT-005` auf dieselbe Frage geprüft: Messen sie die Quelle und schliessen daraus auf das Artefakt? Drei Befunde, in absteigender Schwere. Ausserdem referenzierte **kein einziger** `IDENT`-Check die beiden Identitäts-Proben des `mcp-continuous-auditor` — dieselbe Lücke, die bei `IDENT-006` für `shipped_probe.py` bestand.

**`IDENT-003` — der schärfste Fall, weil der Check ihn selbst beschreibt.** Sein Titel lautet «Werte, die die **Pipeline überschreibt**», seine These:

> Ein Wert, den die Pipeline zur Laufzeit überschreibt, wird nie geprüft.

Beide Modi lasen das Repo, und ein Kriterium verlangte wörtlich einen Check «auf die **committete** Fassung». Der committete Wert war geprüft, der geschriebene nicht — die These, auf den Check selbst angewandt. Neuer **Modus 3** liest zurück: Registry gegen Index (die Index-Seite liefert `shipped_probe.py`), oder die Transformation lokal gegen einen Tag ausführen statt den Workflow zu lesen.

Dabei ist ein realer Fund aufgefallen. Die Publish-Workflows des Portfolios schreiben:

```
jq --arg v "$VERSION" '.version = $v | .packages[0].version = $v' server.json
```

**Nur `packages[0]`.** Kriterium 2 dieses Checks verlangt für die committete Fassung ausdrücklich «*jeder* `packages[*]`» — die Pipeline, die diese Fassung ersetzt, erfüllt genau das nicht. Bei einem Server mit zwei Einträgen wäre der zweite im publizierten Manifest desynchron, und kein Kriterium hätte es gesehen. Aktuell führt jeder geprüfte Server genau einen Eintrag; das ist ein Zustand, keine Eigenschaft, und steht jetzt als Kriterium und als Anti-Pattern drin. Dazu die Nicht-Tag-Falle, die dieselben Workflows bereits kommentieren: Bei `workflow_dispatch` aus einem Branch ist `GITHUB_REF_NAME` der Branch-Name, und ein blindes `${VAR#v}` publiziert die Version `main`.

**`IDENT-001` — Achse vorhanden, Methoden belegt blind.** Der Check mass bereits am installierten Paket, schrieb dafür aber zwei Techniken vor, die an realen Servern versagt haben. Neuer **Modus 3** ist `published_probe.py`, das drei Strategien gleichzeitig fährt und zu jedem Befund festhält, welche ihn erzeugte:

| Strategie | Woran sie scheiterte |
|---|---|
| Regex auf `f"…{__version__}…"` | `lobbywatch-mcp` — die Variable heisst dort `PACKAGE_VERSION` |
| Modul-Namespace lesen (bisheriger Modus 2) | `seco-labor-mcp` — Wert in `_HTTP_KWARGS["headers"]["User-Agent"]`; `swiss-transport-mcp` — Literal inline im `httpx`-Konstruktor *innerhalb einer Funktion* |
| Quelltext-Literale (bisheriger Modus 1) | jeden f-String-User-Agent — nach dem Schrägstrich steht keine Ziffer zum Verankern |

Zwei Dinge, die dem Check ganz fehlten. Erstens die Zahl: Der Sweep im `pdf_ref` (2026-07-29, 30 Server) ist der **repo-seitige**. Ein zweiter am Folgetag installierte **33 publizierte Pakete aus dem Index — 16 sendeten eine andere Version, als die sie installiert wurden.** Alle 16 hatten den Fix gemergt, keines released. Zweitens `unverified`: Eine Probe, die keinen User-Agent findet, darf nicht melden, dass es keinen gibt. Genau so wurden 24 Pakete für unauffällig erklärt, 16 davon drifteten. Und ein **fremder** User-Agent — im Sweep eine gefälschte Browser-Kennung — ist eine eigene Befundklasse mit anderer Behebung, nicht Versionsdrift.

Ergänzt ist auch, dass die Exit-Vokabulare der beiden Proben **nicht** übereinstimmen: Bei `published_probe.py` heisst `2` «nicht installierbar», bei `shipped_probe.py` «Befund».

**`IDENT-002` und `IDENT-005` — Reichweite bestätigt, Abgrenzung ergänzt.** Beide prüfen zu Recht die Quelle. `IDENT-002` vergleicht installierte Metadaten gegen `pyproject.toml` — beide aus demselben Baum, sie können gar nicht widersprechen; wer daraus auf das publizierte Paket schliesst, macht den Fehler aus `IDENT-006`. `IDENT-005` prüft die *Form* des Fallback-Markers; dass der Marker im installierten Paket feuert (beschädigte Wheel-Metadaten), ist ein Befund gegen `IDENT-002`, sichtbar in `IDENT-001` Modus 3. Beides steht jetzt als Absatz und als Verweis drin, `IDENT-002` zusätzlich als Kriterium.

Keine Katalog-Änderung: 90 Checks in 11 Kategorien, alle `applies_when` und `severity` unverändert, 431 Tests unverändert.

### Geändert — `IDENT-006` bekommt eine zweite Achse: läuft das Artefakt überhaupt?

Der Check war lückenbasiert und hätte einen realen Vorfall durchgewunken. `zurich-opendata-mcp` `0.5.1`, reproduziert am 2026-07-31: Repo-Version, letzter Git-Tag und PyPI standen **alle drei auf `0.5.1`** — jeder Versionsvergleich meldete «in sync» — und das Artefakt starb beim Import.

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

Gebrochen hatte nichts im Repository. `0.5.1` trug `mcp[cli]>=1.28.1` **ohne Obergrenze**; `mcp` 2.0.0 erschien am 2026-07-28 und entfernte das Modul ersatzlos. Das publizierte Artefakt änderte sich, ohne dass jemand es publizierte.

**Die Lehre, die dem Check fehlte, steht jetzt als eigener Abschnitt darin:** Versionsgleichheit über Repo, Tag und Index ist ein Vergleich von *Etiketten*. Sie sagt, dass niemand vergessen hat zu publizieren — nicht ob das Artefakt installiert, importiert oder antwortet. Die einzige Aussage darüber kommt daher, dass man es installiert und startet.

**Zwei Achsen statt einer.** Die bisherigen Lücken-Kriterien bleiben unverändert und richtig; sie waren im Vorfall sogar *erfüllt* — zwischen dem `mcp`-2.0.0-Release und dem Fund lagen ein bis drei Tage. Daneben steht jetzt die Gesundheits-Achse: installiert, importiert, startet, beantwortet einen echten `tools/call`, nicht zurückgezogen. **Ein Verstoss dort ist ein sofortiger Befund, unabhängig vom Alter der Lücke** — auch bei null unveröffentlichten Commits. Ist die Achse nicht gemessen worden, ist der Check `todo`, nicht bestanden.

### Geändert — `shipped_probe.py` ist der primäre Modus, `pip show` fliegt raus

**Modus 1** ist jetzt `scripts/shipped_probe.py` aus dem `mcp-continuous-auditor`: Installation der Distribution **aus dem Index in ein frisches venv**, Start des installierten Entry Points, echtes `initialize` plus echter `tools/call`. Die zwanzig Befundcodes der Probe sind auf die zwei Achsen aufgeteilt, mit den beiden, die erfahrungsgemäss falsch gelesen werden: `NOT_ON_INDEX` («nie publiziert», Prozess einrichten) gegen `STALE_ON_INDEX` («publiziert, aber hinterher», Workflow-Run ansehen) — und `TOOL_ERROR`, das für sich genommen auch eine Egress-Allow-List sein kann und nicht ungeprüft als Artefakt-Defekt gehört. Exit `127` ist kein Pass (`OPS-005`).

Der bisherige Metadaten-Vergleich wird **Modus 2** und behält seinen Wert — er ist billig und findet die Lücke. Sein Fail-Pattern-Block trägt jetzt aber auch den Fall, den er *nicht* sehen kann: drei gleiche Nummern, null Commits, totes Artefakt.

**Nebenbefund beim Verifizieren:** Der Check zeigte auf `release_gap.py`. Das ist seit dem Zusammenlegen **nur noch ein Kompatibilitäts-Shim** über `shipped_probe.py --metadata-only` — Argument-Weiterleitung und Exit-Code-Übersetzung, keine eigene Logik, im Quell-Repo ausdrücklich zur Löschung vorgesehen. Der Shim übersetzt ausserdem auf das alte Vokabular zurück und ebnet damit den Unterschied zwischen «Befund» und «Vergleich nicht möglich» wieder ein. Beide Verweise zeigen jetzt auf `shipped_probe.py`.

**In der Remediation ersetzt ein echter Start den `pip show`-Zweizeiler.** `pip show` beweist, dass ein Verzeichnis mit Metadaten angelegt wurde — nicht, dass ein `import` durchläuft. Genau diese Unterscheidung *war* der Vorfall: `0.5.1` installierte sauber. An seiner Stelle stehen Import-Test und ein `initialize`/`tools/list`-Handshake gegen den installierten Entry Point, mit den zwei Fallen, die ihn wertlos machen — stdin zu früh schliessen, und die eigene Umgebung mitbenutzen.

Zwei neue Schritte: die Ursache schliessen (Obergrenze in der Range; ein Lockfile schützt hier nicht, es gilt nicht für die Auflösung beim Nutzer) und die Gesundheit **wiederkehrend** prüfen — der Vorfall entstand nach einem korrekten Release, eine Prüfung nur beim Publish kann diese Klasse prinzipiell nicht sehen.

Acht neue Zeilen in «Common Failures». Keine Katalog-Änderung: 90 Checks in 11 Kategorien, `applies_when` und `severity` unverändert, 431 Tests unverändert.

### Geändert — `SEC-016` misst die Eigenschaft statt des Mechanismus

Zwei Pass-Kriterien waren so formuliert, dass sie an einer korrekten Implementierung vorbeigehen.

**Kriterium 2 verlangte «via Environment-Variable».** `zurich-opendata-mcp` löst dieselbe Aufgabe seit `0.7.0` mit `--host` und Default `127.0.0.1` — Absicht vollständig erfüllt, Kriterium wörtlich verfehlt. Der Check hätte ein Finding gegen eine korrekte Implementierung erzeugt und zur Gegenrichtung eingeladen: eine `MCP_HOST`-Variable nachzurüsten, die niemand liest, damit die Zeile grün wird. Der Mechanismus ist jetzt offen — Env-Var **oder** CLI-Flag.

**Wichtiger ist, was an die Stelle tritt.** Nicht «es gibt eine Option», sondern **der gesetzte Wert erreicht den Listener**. Das ist der Fehler, der hier real gebrochen war: Vor `0.7.0` hatte derselbe Server gar keine Konfigurationsfläche — `mcp.run(transport="streamable-http", port=…)` ohne `host=`, uvicorn band immer Loopback, kein Flag änderte daran etwas. Ein Kriterium der Form «es existiert eine Env-Var» hätte den Zustand angezeigt, aber den Folgefehler nicht gefangen, dass eine vorhandene Option den Listener nie erreicht. Aus einem Kriterium werden damit vier: konfigurierbar, Default Loopback, Wert kommt an, `0.0.0.0` steht in der Deployment-Konfiguration statt im Code.

**Neuer Modus 3 (`runtime_test`) misst genau das.** Das Startlog nennt die tatsächlich gebundene Adresse (`Uvicorn running on http://…`) — zwei Läufe, einer ohne Konfiguration, einer mit gesetztem Wert. Der Default-Lauf allein beweist nichts: Ein Server, der die Option ignoriert, besteht ihn und wirkt dabei besonders sicher. Nicht als Beleg zählt eine Logzeile, die der Server aus seiner **eigenen** Konfigurationsvariablen schreibt — die sagt, was er binden wollte, und wäre in genau dem Fehlerfall grün. Der bisherige `nmap`-Modus rückt auf 4.

### Geändert — die Startwarnung in `SEC-016` ist nicht mehr «Optional»

Sie war als optional geführt und ist es nicht. Nachgeprüft an allen drei Servern, aus denen die Belege stammen — `bag-health-mcp@f108657`, `swiss-transport-mcp@da6c629`, `zurich-opendata-mcp@2ea82d9`: Alle drei warnen beim Nicht-Loopback-Bind, `bag-health-mcp` nennt `SEC-016` dabei namentlich im Code.

**Der Auslöser stimmte allerdings nicht.** Das Kriterium hing die Warnung an eine **Container-Detection** — und die ist in keinem der drei implementiert. Ausgelöst wird überall durch die **fehlende Allow-List**. Wäre der alte Wortlaut einfach verbindlich gemacht worden, wäre ein Kriterium entstanden, das das gesamte Portfolio reisst, ohne dass ein einziger Server unsicherer geworden wäre. Das Kriterium nennt jetzt den Zustand, den die drei tatsächlich prüfen: Ein Bind ausserhalb Loopback ist nicht still, wenn keine Allow-List ihn kompensiert. Die Container-Heuristik steht in der Remediation als möglicher Zusatz — sie rät, wo die Allow-List-Prüfung weiss.

**Damit bedient dieselbe Logzeile zwei Checks**, und die Frage nach einer Doppelung wie bei `SEC-004`/`SEC-005` gehört beantwortet: `SEC-024` fragt, ob die *Abwesenheit der Allow-List* angesagt wird — Subjekt ist die Allow-List. Hier ist das Subjekt die **Exposition**. Ein Server kann hier bestehen und dort durchfallen und umgekehrt; wer die Zeile entfernt, verletzt beide. Eine Ursache mit zwei Wirkungen, kein Doppelbefund. Der Absatz steht in `SEC-016`, damit die Frage nicht bei jedem Audit neu gestellt wird.

Sechs neue Zeilen in «Common Failures», darunter der Auditor-Fehler selbst: ein CLI-Flag als Verstoss zu werten, weil keine Env-Var da ist.

Keine Katalog-Änderung: 90 Checks in 11 Kategorien, `applies_when` und `severity` unverändert, 431 Tests unverändert. Die Lockerung von Kriterium 2 kann nur Findings auflösen; die Verschärfung («Wert erreicht den Listener», Warnung verbindlich) bestehen alle drei geprüften Server bereits, deshalb ohne `adoption: advisory` nach `SKILL.md` 2.3.

### Ergänzt — die vierte Übernahme der eingehenden Allow-List, und was sie nicht ist

Der Abschnitt «Zitate, die nach diesem Release falsch sind» unter `v1.3.0` nennt drei gemergte Portfolio-PRs, die `SEC-005` für die eingehende Host-Allow-List zitieren. Die Vermutung, `zurich-opendata-mcp` habe dieselbe Fehlzuweisung in `0.7.0` übernommen, **ist nachgeprüft und trifft nicht zu.**

Nachgeprüft an `malkreide/zurich-opendata-mcp@2ea82d9`:

- Die Kontrolle **ist** dort implementiert — `MCP_ALLOWED_HOSTS`, portgenau verglichen, Loopback bleibt drin, `421` für alles andere, drei explizit entschiedene Fälle statt der stillen SDK-Ableitung. Damit ist es die vierte Übernahme neben den drei PRs.
- Der `0.7.0`-Eintrag zitiert dafür aber **keine Katalog-ID**. Er verweist auf `bag-health-mcp#51` und `swiss-transport-mcp#25` als Vorlage und nennt sonst nichts; der gesamte CHANGELOG des Repos enthält keine einzige `SEC-`/`ARCH-`/`SDK-`-ID.

Die Empfehlung an die Repos hat damit **zwei verschiedene Formen**, nicht eine: Bei den drei PRs ist eine vorhandene ID falsch und wäre zu korrigieren. Bei `zurich-opendata-mcp` fehlt sie — dort wäre `SEC-024` zu **ergänzen**, und es gibt nichts zu korrigieren. Der v1.3.0-Abschnitt bleibt unverändert; seine Aussage über die drei PRs war und ist richtig, sie war nur nie eine Aussage über alle Übernahmen.

**Ein `SEC-005`-Zitat gibt es in dem Repo trotzdem**, an anderer Stelle und für etwas Drittes: `SECURITY.md` und `SECURITY.de.md` führen in der Hardening-Tabelle die Zeile «TLS — Zertifikatsprüfung standardmässig aktiv; nie deaktiviert (`SEC-005`)». `verify=False` steht in `SEC-005` tatsächlich unter «Common Failures», die Zeile ist also nicht aus der Luft gegriffen — aber sie steht dort nur als Folgeproblem des DNS-Pinnings, nicht als eigenes Kriterium. Ein Server, der nie pinnt, kann diese Zeile nicht erfüllen und auch nicht verletzen.

Damit trägt der Name `SEC-005` im Portfolio drei Bedeutungen: ausgehendes DNS-Pinning (der Katalog), die eingehende Allow-List (die drei PRs) und TLS-Zertifikatsprüfung (dieses `SECURITY.md`). Das ist kein weiterer Befund gegen die Repos, sondern die nachträgliche Rechtfertigung dafür, dass `SEC-005` umbenannt und `SEC-024` aufgemacht wurde.

Reine CHANGELOG-Ergänzung: kein Check angefasst, 90 Checks in 11 Kategorien, 431 Tests unverändert.

### Ergänzt — `SEC-024` bekommt seinen `automated`-Modus

Der Check beschrieb die tragende Probe («richtiger Name, falscher Port») bisher nur als `curl`-Block zum Nachbauen. Es gibt sie fertig: `scripts/rebind_probe.py` im [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) bootet das Ziel mit einer selbst gesetzten Allow-List und läuft vier Proben in zwei Durchläufen — ohne Auth und mit gültigem Token. Der Katalog verankert vergleichbare Werkzeuge bereits (`DRIFT-004` → `live_probe.py`, `IDENT-006` → `release_gap.py`); hier fehlte das Muster.

Der neue **Modus 2 (`automated`)** steht vor der Handprobe, die zu **Modus 3** wird; `config_check` rutscht auf **Modus 4**. Inhaltlich neu ist vor allem, was die Ausgänge des Gates für diesen Check bedeuten:

- **`allowed` ist keine Kontrollprobe zum Weglassen.** Was trägt, ist das *Paar* (`wrong-port` abgewiesen, `allowed` angenommen) — zwei Requests, die sich nur im Port unterscheiden. Eine zurückgefallene Loopback-Policy weist beide ab, eine namensweise verglichene Liste nimmt beide an. Das Pass-Kriterium für Evidence 2 ist entsprechend geschärft.
- **Exit `3` ist kein Pass.** Der Gate meldet «nicht konfiguriert» absichtlich als eigene Kategorie, weil er Deployments beobachtet und der Fail-open-Zustand auf `0.0.0.0` dokumentiert ist. Gegen die Pass Criteria dieses Checks ist derselbe Befund ein `fail` — Kriterium 1 verlangt die Verdrahtung. Wer den Exit-Code direkt auf einen Status abbildet, verbucht die Abwesenheit der Kontrolle als bestanden.
- **Exit `2` ist nicht durchgängig `fail`.** Beim `case` `not-attributable` wurde nichts gemessen; das ist `todo`. Ein Fail-Befund daraus wäre erfunden.
- **`not-applicable` ist ein Abgleich, kein Freispruch.** Der Gate leitet die Transporte aus dem Ziel-Checkout ab, `applies_when` aus dem Profil. Widersprechen sie sich, ist das ein eigener Befund.

Dazu zwei Ausführungs-Stolperfallen, die beim Lesen des Skripts sichtbar wurden: Der Gate setzt die Allow-List unter allen Schreibweisen, die ein Ziel lesen könnte — darunter `ALLOWED_HOSTS`, das bei manchen Servern die **Egress**-Liste aus `SEC-021` ist und im Lauf überschrieben wird (Artefakt, kein Befund). Und ein Ziel, das seine Liste im Code pinnt, lässt die Kontrollprobe scheitern; dafür gibt es `REBIND_ALLOWED_HOST`.

Drei Zeilen in «Common Failures», drei Verweise (`OPS-005`, das Skript, die Boot-Harness darunter). Keine Katalog-Änderung: 90 Checks in 11 Kategorien unverändert, `applies_when` unverändert, 431 Tests unverändert.

## [v1.4.1] — 2026-08-01 — Die Familie steht jetzt auch im README

### Ergänzt — die Skill-Familie im Abschnitt «Verwandte Repos»

Der Abschnitt listete nur das Server-Portfolio und die beiden Notion-Tracker. Die Skills, neben denen dieser Katalog existiert, waren nirgends genannt — für das Repo am Ende der Kette die falsche Auslassung.

Aus dieser Richtung ist die nützliche Information, welche Checks welchen Skill-Regeln entsprechen. Die Tabelle trägt das jetzt: `FID-001`–`FID-005` für `mcp-data-fidelity`, und `SDK-006`, `ARCH-013`, `SEC-024` für das neue `mcp-transport-hardening`. Die Zuordnung ist durch Lesen der Check-Dateien belegt, nicht aus den Titeln geschlossen.

Festgehalten ist auch, was der Katalog **nicht** abdeckt, weil das aus Audit-Sicht die interessantere Hälfte ist. Zwei Transport-Hardening-Regeln haben hier kein Gegenstück, und die beiden Fälle sind verschieden:

- Die Regel, dass der Bind die App erreichen muss, ist eine **echte Lücke**. `SEC-016` liegt daneben, adressiert aber den umgekehrten Fall — dort ist `0.0.0.0` der unbeabsichtigte Bind (NeighborJack), dort ein gewollter.
- Die drei Regeln zur Beweisführung (Negativtest-Schärfe, Mutationstest, Harness-Fallen) sind eine **Bereichsgrenze**: Der Katalog prüft, ob eine Kontrolle vorhanden ist, nicht ob ihr Nachweis trägt.

Keine Katalog-Änderung: 90 Checks in 11 Kategorien unverändert, 429 Tests.

`mcp-builder` steht ohne Lizenzangabe in der Tabelle. `anthropics/skills` trägt keine LICENSE-Datei, die GitHub-API meldet `license: null`, und `THIRD_PARTY_NOTICES.md` betrifft Abhängigkeiten. Eine unbelegte Lizenzangabe gehört nicht in ein öffentliches README.

## [v1.4.0] — 2026-08-01 — Zwei Sprachfassungen, und keine Zahl mehr ohne Wächter

Reine Doku- und Test-Änderungen: keine neuen Checks, kein Katalog-Eingriff, 90 Checks in 11 Kategorien unverändert. Das englische `README.md` kommt dazu, die deutsche Fassung zieht nach `README.de.md`, und jede Zahl, die im README steht, hat jetzt etwas, das sie prüft.


### Ergänzt — `## Mitwirken` als eigene Sektion

Die Aussage stand bisher als ein Satz unter `## Kontext` («Pull Requests willkommen — insbesondere für ergänzende Compliance-Layer»). Sie hat jetzt eine eigene Überschrift und benennt die Anatomie, die ein neuer Check mitbringen muss: benannte Quelle, ein Pass-Kriterium, das zwei Auditoren gleich beantworten, ein Remediation-Pfad, ein Aufwands-Indikator. Ein Check ohne Quelle ist eine Meinung, und ein auslegbares Pass-Kriterium macht den Katalog unreproduzierbar — also genau das, was er verhindern soll.

Der Satz in `## Kontext` entfällt, damit die Aussage nur an einer Stelle steht.

### Nachgezogen — `## Status` und der fehlende `v1.3.0`-Tag

Der Status-Abschnitt stand in beiden Fassungen auf **v1.0.0 vom 2. Mai**, drei Releases zurück, mit «10 Helper-Scripts, 255 pytest cases» — tatsächlich waren es 17 und 426. Jetzt v1.3.0, und **ohne die beiden Zählungen**.

Dabei kam heraus, dass `v1.3.0` **nie getaggt war**: Der CHANGELOG führt den Block seit dem 31. Juli, die `--skill-version`-Literale in `SKILL.md`, `audit_init.py` und dem Slash-Command stehen auf `1.3.0`, und `test_skill_version_literals.py` hält sie genau daran fest — nur Tag und Release fehlten, letzter war `v1.2.0`. Vier Angaben, drei davon einig, und die vierte war die einzige, die man von aussen sieht.

Der Tag sitzt auf `5ef54e7`, dem letzten Commit vor den Doku-Änderungen dieses Blocks — also genau auf dem Stand, den der `v1.3.0`-Abschnitt beschreibt, und nicht auf einem späteren, der Dinge enthielte, die dort nicht stehen.

**Warum die Zahlen weg sind.** «10 Helper-Scripts» und «255 pytest cases» erzwang nichts, und beide waren entsprechend gedriftet — dieselbe Mechanik, gegen die `test_readme_counts.py` die Katalog-Zahlen hält. Sie nur zu korrigieren hätte den Zustand um ein paar Monate verlängert, nicht behoben.

Ein Test wäre hier der schlechtere Weg: Eine Testsuite, die ihre eigene Fallzahl festnagelt, wird bei jedem neuen Test rot, ohne dass etwas kaputt ist — und ein Test, der ständig grundlos anschlägt, wird abgeschaltet. Also die Regel, die dieses Repo ohnehin anwendet: Eine Zahl steht dort, wo etwas sie prüft. Die Katalog-Zahlen bleiben (Badge, Kategorien-Tabelle, Total, Provenance — alle gegen `checks/` gesichert), die Skript- und Testzählungen verschwinden. Was sich pro Release ändert, steht im CHANGELOG, wo es hingehört.

Die CI-Matrix bleibt: Sie ist keine Zählung, sondern eine Zusage, und sie steht eine Datei entfernt in `test.yml`.

**Die Versionszeile selbst hängt jetzt am CHANGELOG.** Sie war die letzte unbewachte Angabe im Status — und die, die drei Releases lang falsch stand. `test_skill_version_literals.py` zog die aktuelle Version schon vorher aus der obersten Release-Überschrift, um die `--skill-version`-Literale daran festzuhalten; dieselbe Quelle deckt jetzt auch `**Version:**` in jeder README-Fassung ab. Zwei Anker, ein Wert.

Die Fassungen kommen per `glob("README*.md")` statt aus einer gepflegten Liste — eine dritte Sprachfassung ist damit automatisch abgedeckt, statt still durchzurutschen. Dazu zwei Tests, die den Anker selbst schützen: dass überhaupt eine README gefunden wird (eine leere Parametrisierung ist grün) und dass die Zeile `**Version:** vX.Y.Z` existiert (ein Muster, das nichts findet, ist ebenfalls grün).

Gegengeprobt, beide Richtungen: Status auf `v1.2.0` zurückgedreht → «Status nennt ['1.2.0'], oberster Release im CHANGELOG ist 1.3.0»; Anker in `**Release:**` umbenannt → «keine Zeile `**Version:** vX.Y.Z` gefunden». Beides zurückgenommen, wieder still. 424 → 429 Tests.

### Umgestellt — englisches `README.md`, deutsches `README.de.md`

Dieses Repo war das letzte im Portfolio mit einem einzigen, deutschsprachigen `README.md`. Der Repo-Validator prüft `README.md` aber grundsätzlich als englische Datei — er erkannte deshalb weder `## Mitwirken` noch `## Lizenz` noch den Autor und meldete sie als fehlend. Fünf ERROR und eine WARN, sämtlich Artefakte dieser einen Annahme. Jetzt: **0 ERROR, 0 WARN**, und dieselbe Struktur wie in den drei Schwester-Repos.

Der deutsche Text zieht unverändert nach `README.de.md` (per `git mv`, damit die History dranbleibt), `README.md` ist die Übersetzung. Beide tragen den Sprachumschalter.

Bei der Gelegenheit zwei Dinge nachgezogen, die derselbe Check meldete: Der Autor steht jetzt als Überschrift `## Autor` statt als Fettdruck — Fettdruck sieht gleich aus, erzeugt aber keine Gliederungsebene. Und beide Fassungen haben eine `## Sicherheit`-Sektion, die drei Betriebsfragen benennt: dass `audits/` und `portfolio-logs/` Roh-Output *fremder* Repos enthalten und vor dem Veröffentlichen durchzusehen sind; dass `portfolio.yaml` (ein Inventar) und `NOTION_TOKEN` nie in einen Commit gehören; und dass ein grünes Audit keine Sicherheitszusage ist, weil der Katalog gegen veröffentlichte Best Practices prüft und nicht gegen ein Bedrohungsmodell.

**`test_readme_counts.py` läuft jetzt über beide Dateien — das war der eigentliche Aufwand.** Die Prosa-Muster waren deutsch (`(\d+)\s+Kategorien`, `Checks\s+aus\s+(\d+)`). Auf englischem Text hätten sie nichts mehr gefunden, und ein Muster, das nichts findet, ist grün: Die Tests wären durchgelaufen, während die Drift-Sicherung, für die es diese Datei überhaupt gibt, still ausgefallen wäre. Genau die Fehlerklasse, gegen die `FID` und `DRIFT` im Katalog stehen — hier in den eigenen Tests.

Deshalb: Prosa-Muster je Sprache in einem `PROSE`-Dict, Fixture parametrisiert über beide Fassungen, `LAYER_ROW` case-insensitive. Dazu zwei neue Tests gegen genau diesen Ausfall — `test_prose_patterns_actually_match_something` verlangt, dass jedes Muster in seiner Fassung mindestens einmal greift, und `test_every_readme_is_covered` vergleicht die `README*.md` auf der Platte gegen die Einträge in `PROSE`, damit eine dritte Sprachfassung nicht lautlos ungeprüft bleibt. 6 → 15 Tests in dieser Datei, 417 → 424 in der Suite.

Beim Übersetzen war die Prosa an den Mustern auszurichten: «alle 23 Security-Checks» wird zu «all 23 security checks» — die Zahl steht dort nicht direkt vor «checks», das Muster greift also korrekt nicht. Andernfalls hätte der Test 23 gegen 90 geprüft und wäre zu Recht rot geworden.

**Nicht angefasst:** Die GitHub-Repo-Description bleibt deutsch, und `tools/check_repo_description.py` prüft sie weiterhin mit deutschen Mustern — beides passt zusammen. Wer die Description später auf Englisch umstellt, muss dort nachziehen; der Check schlägt dann laut fehl («Description nennt keine Check-Zahl») und nicht still.

## [v1.3.0] — 2026-07-31 — Zwei Richtungen, alle Pfade, und ein Inventar das nachfragt

**Fünf neue Checks** (`OPS-005`, `SCALE-007`, `SEC-024`, `ARCH-013`, `SDK-006`) — der Katalog wächst von 85 auf **90** —, **vier inhaltlich korrigierte** (`SEC-004`, `SEC-005`, `SEC-016`, `SEC-021`), ein vereinheitlichtes `transport`-Vokabular mit Validator-Gate und ein Inventar-Gate für das Portfolio. Die Einzelheiten stehen in den Abschnitten unten; hier nur, was beim Upgrade zu tun ist.

### ⚠️ Zuerst lesen: `SEC-016` lehrte Code, der auf dem aktuellen SDK nicht startet

Das Pass-Pattern von `SEC-016` (0.0.0.0-Binding-Prevention) zeigte bis zu diesem Release die **mcp-1.x-API**:

```python
mcp.settings.host = host      # unter 2.x: ValueError: "Settings" object has no field "host"
mcp.settings.port = port
mcp.run(transport="sse")
```

Unter `mcp` 2.x trägt `Settings` weder `host` noch `port`. Ein Server, der nach dem dokumentierten Muster gebaut wurde, **startet auf HTTP-Transport gar nicht** — auf stdio fällt es nicht auf, weil dort kein Bind vorkommt.

**Wer `SEC-016` in einem Audit als bestanden geführt hat und das Pass-Pattern übernommen hat, hat ein Problem.** Der Check ist auf `run(transport=…, host=…, port=…)` korrigiert, die alte Form steht jetzt als Fail-Pattern daneben, und die Remediation — die denselben kaputten Code als Fix empfahl — ist mitgezogen. Prüfen lässt es sich in einer Zeile:

```bash
grep -rnE "mcp\.settings\.[a-z_]+\s*=" src/
```

Der neue `SDK-006` deckt diese Klasse vollständig ab; siehe dort.

### Was neu ist

| Check | Severity | Kurz |
|---|---|---|
| `OPS-005` | high (`advisory`) | Pipeline unterscheidet «bestanden» von «nicht gelaufen» |
| `SCALE-007` | medium | Wiederaufnahme abgerissener Streams via `Last-Event-ID` |
| `SEC-024` | high | Inbound Host/Origin-Allow-List — DNS-Rebinding auf den eigenen Endpoint |
| `ARCH-013` | high | Alle Netz-Transportpfade identisch verdrahtet |
| `SDK-006` | high | SDK-Major-Migration vollständig abgeschlossen |

### Was korrigiert wurde

| Check | Art der Änderung | Severity |
|---|---|---|
| `SEC-004` | `applies_when` — Transport-Disjunkt entfernt (Überanwendung zurückgenommen) | unverändert `critical` |
| `SEC-005` | Titel auf «DNS-Rebinding **egress**», `applies_when` erweitert (stdio-only nicht mehr ausgenommen) | unverändert `high` |
| `SEC-016` | Pass-Pattern und Remediation auf die 2.x-API, Notiz zur Host-Allow-List | unverändert `critical` |
| `SEC-021` | FAIL-Pattern-Klarstellung: die Regel gilt für Egress, nicht für Ingress | unverändert `high` |

**Keine Severity eines bestehenden Checks wurde geändert** — `SEC-004` und `SEC-016` stehen unverändert auf `critical`, `SEC-005` und `SEC-021` auf `high`.

**Trotzdem ist ein Re-Audit fällig, und die Regel dafür wurde in diesem Release nachgezogen.** [§Versionierung](SKILL.md#versionierung-des-check-katalogs) Punkt 5 kannte bisher nur die Severity als Auslöser. Dieses Release hatte keine einzige — und trotzdem zwei Fälle, die bestehende Audit-Ergebnisse entwerten:

- **`SEC-005` gilt jetzt für Server, die nie dagegen gemessen wurden.** Die Klausel wurde auf stdio-only-Server mit ausgehenden Requests ausgeweitet. Für die betroffenen Server ist das von einer Severity-Anhebung nicht zu unterscheiden: Ein blockierender Check greift, wo vorher keiner war.
- **`SEC-016` hat die falsche Sache als bestanden ausgewiesen.** Ein «bestanden» aus der Zeit vor der Pass-Pattern-Korrektur belegt nichts — im Gegenteil, wer dem Muster gefolgt ist, hat einen Server, der auf HTTP-Transport nicht startet.

Punkt 5 nennt deshalb ab sofort **drei** Auslöser: Severity angehoben (a), `applies_when` nach oben erweitert (b), Prüfkriterium korrigiert (c). Eselsbrücke: *«Re-Audit, wenn sich geändert hat, wie hart geprüft wird, wer geprüft wird oder worauf geprüft wird.»*

Betroffen sind damit: jeder stdio-only-Server mit `tools_make_external_requests: true` (wegen b), und jeder Python-Server mit Netz-Transport, dessen Audit `SEC-016` als bestanden führt (wegen c). Punkt 4 bleibt unberührt — neue Checks gelten weiterhin nicht rückwirkend.

`SEC-004` ist der Gegenfall: Die Reichweite wurde **verengt**. Das löst kein Re-Audit aus, kann aber Findings aus alten Audits gegenstandslos machen — betroffen wären Server mit Netz-Transport ohne ausgehende Requests.

### Zitate, die nach diesem Release falsch sind

Drei bereits gemergte Portfolio-PRs zitieren im Titel `SEC-005` für eine Kontrolle, die seit diesem Release `SEC-024` heisst — die eingehende Host-Allow-List:

- [`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29)
- [`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51)
- [`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25)

Zum Zeitpunkt dieser PRs gab es keine passende ID — genau diese Verwechslung war der Anlass für `SEC-024` und die Umbenennung von `SEC-005`. Die Zitate sind gemergte Historie und niemand muss sie umschreiben; wer die Repos ohnehin anfasst, kann sie bei Gelegenheit nachziehen.


### Hinzugefügt — Inventar-Gate: die Portfolio-Liste behauptet nicht mehr, was es gibt

`portfolio.yaml` ist handgepflegt, und `audit-portfolio.sh` arbeitet genau diese Liste ab. Was nicht darin steht, wird nie auditiert — **und es gibt keine Rückmeldung darüber.** Ein nicht auditierter Server erzeugt keine Zeile, keinen Fehler, keine Lücke im Report. Er ist schlicht nicht da.

Der reale Fall: `openparldata-mcp` liegt verschachtelt im Repo `parlament-mcp`, mit eigener `pyproject.toml`. Jede Aufzählung, die Top-Level-Repos listet, hat ihn übersprungen. Dadurch war er der letzte Server im Portfolio auf dem alten SDK-Major, und unter dem neuen wäre er auf HTTP-Transport gar nicht mehr gestartet. Gefunden wurde er zufällig und spät.

Neu `tools/verify_inventory.py` und `./audit-portfolio.sh --verify-inventory`. **Die Beweislast dreht sich um:** Nicht die Liste sagt, was es gibt — der Checkout wird befragt, und jedes gefundene Server-Manifest (`pyproject.toml`, `package.json`) muss sich einem Listeneintrag zuordnen lassen oder ausdrücklich als Nicht-Server deklariert sein. Alles andere ist ein harter Fehler mit Exit 1.

**Zwei optionale Felder in `portfolio.yaml`:**

- `path:` — wo das Manifest im Checkout liegt, Default `.`. Ein verschachtelter Server bekommt einen eigenen Eintrag mit derselben `repo`-URL und seinem Pfad. Die deklarierten Pfade werden **pro Repo-URL** gruppiert; ohne das meldete das Gate den Eltern-Checkout als Drift, obwohl der verschachtelte Server ordentlich gelistet ist.
- `ignore:` — Glob-Muster für Verzeichnisse, die kein Server sind. Pro Server oder global.

**Keine Heuristik darüber, was ein Server ist.** Ohne Deklaration übersprungen werden nur Vendor- und Cache-Verzeichnisse (`node_modules`, `.venv`, `__pycache__`, `.tox`, `*.egg-info`, …) — das ist keine Aussage über Server, sondern darüber, was Werkzeuge dort ablegen. Test-Fixtures, Beispiele und Tooling-Unterprojekte werden **nicht** geraten: Eine Regel, die `examples/` pauschal für harmlos hält, hätte `openparldata-mcp` genauso übersehen wie die Handliste. Wer weiss, dass es kein Server ist, schreibt es hin.

**Übersprungenes steht im Report.** Ein still übergangenes Verzeichnis wäre dieselbe Fehlerklasse in neuer Verpackung — `OPS-005` beschreibt sie: Was nicht geprüft wurde, sieht aus wie bestanden. Aus demselben Grund ist ein **fehlender Checkout** kein Bestehen, sondern `unverified` mit Exit 1; `--skip-missing` stuft das für Teilläufe herunter, deckt aber echte Drift weiterhin auf.

**Die Begründung steht im Fehlertext, nicht nur im Quelltext.** Wer das Gate rot sieht, liest den `openparldata`-Fall und die zwei Auswege mit. Ein Gate ohne sichtbaren Grund fliegt beim nächsten Aufräumen raus — deshalb steht der Hinweis auch als Abschnitt «BITTE NICHT WEGRÄUMEN» im Modul-Docstring, und ein Test hält fest, dass die Begründung im CLI-Output erscheint.

**24 neue Tests** (`tests/test_verify_inventory.py`), darunter das Fixture, das genau den Anlassfall nachbaut, sowie die Form, die ein echter `audit-portfolio.sh`-Lauf erzeugt: zwei Checkouts desselben Repos, beide mit beiden Manifesten. 385 → 409 Tests.

Hinweis zur Testumgebung: Diese Tests brauchen PyYAML — dieselbe Abhängigkeit, die CI seit je installiert (`pip install pytest pyyaml`). Sie sind bewusst **nicht** mit `importorskip` versehen: Ein Skip, den CI durch eine Installation verhindern könnte, ist nach `OPS-005` kein Skip, sondern eine Lücke.

### Hinzugefügt — `ARCH-013` und `SDK-006`: zwei Fehlerklassen, die beim Import nicht brechen

Der Katalog wächst auf **90 Checks**. `ARCH` auf 13, `SDK` auf 6.

#### `ARCH-013` — Alle Netz-Transportpfade identisch verdrahtet

Die Verallgemeinerung des Hinweises, den `SEC-024` im Remediation-Teil offen gelassen hat. Ein netzerreichbarer Server konstruiert seine ASGI-App fast nie an genau einer Stelle: eigener App-Builder, SDK-servierter `run()`-Pfad, deprecateter SSE-Pfad, `uvicorn --factory`. Die Kontrolle sitzt dann auf einem davon.

Zwei Ausprägungen, in zwei Repos unabhängig aufgetreten:

- **Die Kontrolle hängt an einer fremden Bedingung.** Ein App-Builder wurde nur genommen, wenn Auth **oder** CORS konfiguriert war; sonst servierte das SDK über `run()`. Damit hinge das Scharfschalten einer Sicherheitskontrolle davon ab, ob zufällig ein Auth-Token gesetzt ist — zwei Deployments desselben Images, eines geschützt, eines nicht, und der Unterschied steht in einer Variablen, die von etwas anderem handelt.
- **Der Parametersatz reist unvollständig.** Ein Builder bekam nur `host`, nicht `port`, und defaultete ihn intern. Die Loopback-Einträge der Host-Allow-List nannten dadurch einen Port, den niemand bedient: verdrahtet, aktiv, und trotzdem falsch. Kein Test hat das gesehen, weil der vorhandene Port-Test den Builder mit explizitem Port rief — die Naht davor war ungeprüft.

Eigener Check statt Fussnote in `SEC-024`, weil die Klasse nicht an eine Kontrolle gebunden ist: Dieselbe Lücke entsteht mit Auth-Middleware, Rate-Limiting, Request-Logging oder Tracing. Geprüft wird die **Vollständigkeit der Aufzählung** — eine Struktureigenschaft des Servers.

Eigener Verification-Modus für `uvicorn --factory`, weil der Fehler dort von aussen kommt und im Code unsichtbar ist: uvicorn ruft eine Factory **ohne Argumente** auf. `--host` konfiguriert nur den Listener und erreicht die App nie; die Factory muss den Bind selbst aus derselben Quelle lesen wie `main()`.

#### `SDK-006` — SDK-Major-Migration vollständig abgeschlossen

Der mechanische Teil eines Major-Sprungs ist in einer Stunde erledigt und sieht danach fertig aus. Liegen bleiben die Stellen, die nicht am Import hängen — und die brechen nicht dort, wo getestet wird: Ein Server mit halber Migration importiert sauber, startet auf stdio, besteht die Suite und stirbt beim ersten HTTP-Deployment.

Fünf greppbare Kriterien: Bound am **neuen** Major verankert (`>=2.0.0,<3`) statt als Deckel auf dem alten (`<2` kauft Zeit und ist kein Zielzustand) · keine Importe aus `mcp.server.fastmcp` · keine Zuweisungen an `mcp.settings.<x>` · Annotations in snake_case **gelesen** · jede verschachtelte `pyproject.toml` erfasst, nicht nur die im Root.

**Das vierte Kriterium ist mit einer ausdrücklichen Gegenwarnung versehen.** `readOnlyHint` überlebt unter 2.x als pydantic-**Alias**, das Drahtformat ist unverändert, und nur der *lesende* Zugriff im Python-Code bricht — deshalb findet das ein Test und kein Client. Umgekehrt heisst das: **In TypeScript-Servern ist camelCase der Spec-Feldname und bleibt richtig.** Der Check gilt für `sdk_language == "Python"` und sagt über Node-Server nichts aus; wer danach einen TypeScript-Server auf snake_case «korrigiert», macht ihn kaputt. Das steht so im Check, in den Common Failures und in der Remediation.

`applies_when: 'sdk_language == "Python"'` — dieselbe Form wie `SDK-001` bis `SDK-004`; `SDK-005` drückt seine TypeScript-Bindung spiegelbildlich aus. Kein neues Profilfeld nötig.

#### Nachgezogen

`checks/MANIFEST.txt`, `SKILL.md` §2.1, `README.md`, `docs/roadmap.md` und die Lock-Tests.

Zwei Werte brauchten mehr als das Hochzählen:

- **Die SKILL-Bereichsspalte für `ARCH` von `10–12` auf `10–13`.** 13 lag ausserhalb, `test_category_ranges_contain_actual` wäre rot geworden. Die Spalte dokumentiert eine Erwartung, nicht den Bestand — bei Überschreitung ist die Erwartung veraltet, genau wie der Test sagt.
- **Die Applicable-Schranke in `test_applicability.py` von 51 auf 55.** `SDK-006` hat die alte Grenze exakt ausgereizt (51 von 51). Eine Schranke ohne Luft kippt beim nächsten gewöhnlichen Katalogwachstum und meldet «drift», wo keine ist — damit prüfte sie die Katalog-Grösse statt der Grammatik, also das Gegenteil ihres im Kommentar festgehaltenen Zwecks. Die absolute Grösse ist eine Zeile höher ohnehin festgenagelt.

Severity-Verteilung neu **16 critical · 43 high · 30 medium · 1 low**. 385 Tests.

#### Behoben — ein Zählwert, den der Guard vier Releases lang nicht sah

Beim Nachziehen der Zahlen fiel `README.md:71` auf: «Auswahl der ~30 anwendbaren Checks **aus 86**». Der Wert stand auf 86, während der Katalog über 87, 88 und 90 gewachsen ist.

`test_readme_counts.py` hat ihn nicht gemeldet, weil `PROSE_CHECKS` die Zahl **vor** dem Wort erwartet (`(\d+)\s+Checks`). Hier steht sie dahinter. Nach `SKILL.md` §2.5 ist das kein fehlender Test, sondern ein zu kurz greifender: Reichweite korrigieren, nicht Regel ergänzen. Neu `PROSE_CHECKS_TRAILING` (`Checks\s+aus\s+(\d+)`), geprüft in derselben Schleife.

Gegengeprobt: Zahl auf 86 zurückgesetzt — der Test meldet `README.md:71 nennt 86 Checks, Katalog hat 90`; zurückgenommen — still.

### Geändert — `SEC-024` auf die Portfolio-Belege umgeschrieben, `SEC-005` disambiguiert

Der Katalog bleibt bei **88 Checks**. `SEC-024` wurde im letzten Release aus der SDK-Mechanik heraus geschrieben; jetzt liegt der Befund aus drei realen Nachrüstungen vor, und der Check ist danach neu gefasst.

**Die drei PRs zitieren im Titel alle `SEC-005`** — [parlament-mcp#29](https://github.com/malkreide/parlament-mcp/pull/29), [bag-health-mcp#51](https://github.com/malkreide/bag-health-mcp/pull/51), [swiss-transport-mcp#25](https://github.com/malkreide/swiss-transport-mcp/pull/25) — also eine ID, die etwas anderes prüft. Das ist kein Flüchtigkeitsfehler dreimal, sondern die Folge davon, dass der Katalog zwei verschiedene Angriffe unter einem Namen führte.

**`SEC-005` heisst jetzt «DNS-Rebinding *egress*».** Dazu ein Absatz am Anfang, der die Richtung benennt und auf `SEC-024` als eingehendes Gegenstück verweist. Der Titel kam ausserhalb der Check-Datei nirgends wörtlich vor (geprüft in `README.md`, `docs/roadmap.md`, `reference/best-practices-summary.md`) — nachzuziehen war nichts. In `reference/best-practices-summary.md` stand unter der Überschrift «SSRF / DNS Rebinding» aber nur die ausgehende Hälfte; dort steht jetzt ein Absatz zur eingehenden.

**Was `SEC-024` inhaltlich dazugewonnen hat:**

- **Warum die drei naheliegenden Kontrollen nicht greifen**, als Tabelle. *CORS* nicht, weil die Anfrage aus Browsersicht same-origin ist. Ein *Auth-Token* nicht, weil die angreifende Seite in einem Kontext läuft, der eines hält — belegt in `bag-health-mcp#51` durch einen Test, der festhält, dass ein gültiges `Bearer` einen fremden Host nicht rettet. Die *Egress-Allow-List* (`SEC-021`) nicht, weil sie die Gegenrichtung ist.
- **Vier Eigenschaften des Pass-Patterns**, alle aus den PRs: portgenau (ein Eintrag trägt seinen Port), Loopback bleibt immer drin für Container-Health-Checks, konfigurierte CORS-Origins wandern in die Origin-Liste des Transports — sonst weist der Transport genau die Browser-Clients ab, für die CORS geöffnet wurde —, und `*` wird nicht übernommen, weil Origins literal verglichen werden.
- **Der Fail-open-Zustand ist jetzt als akzeptiert beschrieben, nicht als Fehler.** Die vorige Fassung verlangte einen harten Startabbruch. Das war falsch: Ohne gesetzte Variable bleibt der Schutz auf einem Nicht-Loopback-Bind aus — sichtbar, mit Startwarnung. Eine geratene Liste wäre schlechter als keine, weil auf `0.0.0.0` der erreichbare Name im Prozess unbekannt ist und der Tipp genau das Deployment abweist, das er schützen soll.
- **Evidence 2 ist präzisiert**: nicht «fremder Host wird abgewiesen», sondern **richtiger Hostname, falscher Port**. Der Grund steht im Check: Ein Test gegen `evil.example.com` beweist nichts, weil eine zurückgefallene Loopback-Policy ihn ebenfalls abweist — der Test bestünde, ohne dass die Kontrolle da ist. Nur eine tatsächlich übergebene, portgenaue Liste weist `mcp.example.com:9999` ab. Der Test muss aus seinem eigenen Grund scheitern, nicht aus dem eines Defaults.
- Dazu die Gegenrichtung aus `parlament-mcp#29`: Ein Positiv-Test, der `MCP_ALLOWED_HOSTS` selbst setzt, kann die `host`-Verdrahtung nicht prüfen — bei expliziter Allow-List ist der Kwarg irrelevant. Dort bestand die erste Testfassung deshalb auch mit angewandter Mutation.
- **Warnung zu den Netzpfaden** im Remediation-Teil. In den drei PRs sah das jedes Mal anders aus: ein App-Builder, der nur bei konfiguriertem Auth oder CORS überhaupt genommen wurde (sonst servierte das SDK über `run()`); eine uvicorn-`--factory`, die ohne Argumente aufgerufen wird, sodass `--host` nur den Listener konfiguriert; und ein deprecateter SSE-Pfad neben Streamable HTTP. Wer nur den Pfad verdrahtet, den er vor Augen hat, macht den Schutz davon abhängig, welcher Zweig zufällig greift.

`severity: high` bestätigt, nicht still geändert: `SEC-016` trägt `critical` für die Netzwerk-Exposition und macht für Container eine Ausnahme; `SEC-024` ist die kompensierende Kontrolle für genau diese Ausnahme — eine Verteidigungsschicht, keine Exposition. Dass sie per Default fail-open ist, spricht für ihre Wichtigkeit, macht sie aber nicht zur Exposition selbst.

Keine Zählwert-Änderung: `SEC-024` war bereits im Katalog, `SEC-005` behält seine ID. 385 Tests unverändert.

### Hinzugefügt — `SEC-024`: Die gefährliche Konfiguration ist die unauffällige

Der Katalog wächst auf **88 Checks**, `SEC` auf 24. `SEC-024` prüft die eingehende Host-Allow-List — die Frage, die `SEC-016` offen lässt, sobald es `0.0.0.0` für Container erlaubt.

`SEC-016` endete bei «in Container-Kontexten ist `0.0.0.0` korrekt». Damit ist die Frage «wer darf mich erreichen» aber nicht beantwortet, sondern verschoben: Wer an alle Interfaces bindet, kann sie nicht mehr über das Interface stellen. Sie muss an der eingehenden Anfrage gestellt werden — unter welchem Hostnamen der Server angesprochen werden darf. Ohne das ist er offen für **eingehendes** DNS-Rebinding: Eine beliebige Webseite lässt `attacker.com` auf `127.0.0.1` auflösen und spricht den Server aus dem Browser des Opfers an. Die Same-Origin-Policy hilft nicht — für den Browser ist es dieselbe Herkunft.

**Der eigentliche Befund steckt in der Asymmetrie der beiden Fehlermodi.** Am Quelltext von `mcp` 2.0.0 nachgesehen:

| `host` an den App-Builder | `transport_security` | Ergebnis |
|---|---|---|
| nicht durchgereicht → Default `127.0.0.1` | `None` | Schutz **an** mit Localhost-Allow-List → `HTTP 421` für jeden echten Namen |
| `0.0.0.0` durchgereicht | `None` | Schutz **aus** — jeder `Host`-Header wird angenommen |

Der Auto-Zweig greift ausschliesslich, wenn `host` in `("127.0.0.1", "localhost", "::1")` liegt. Für jeden anderen Wert bleibt `transport_security` bei `None`, und `TransportSecurityMiddleware.__init__` belegt dann ausdrücklich «for backwards compatibility» mit `enable_dns_rebinding_protection=False` vor.

Wer `0.0.0.0` also **korrekt** durchreicht, bekommt einen Server, der startet, antwortet, Health-Checks besteht — und jeden Host-Header akzeptiert. Wer es **vergisst**, bekommt `HTTP 421` und merkt es in der ersten Minute. Der laute Fall ist der sichere, der stille ist der Befund. Dieselbe Asymmetrie, die `OPS-005` für Pipelines beschreibt.

Das prägt die Verification: Modus 2 verlangt beide Richtungen — erlaubter Host `200`, fremder Host `421`. Ein Test, der nur den erlaubten Namen prüft, bestätigt, dass der Server läuft, und kann einen abgeschalteten Schutz nicht von einem funktionierenden unterscheiden.

`high`, nicht `critical`: `SEC-016` trägt bereits `critical` für die Netzwerk-Exposition selbst; dieser Check ist die Verteidigung für den Fall, dass `0.0.0.0` zu Recht gesetzt ist. Zweimal `critical` auf derselben Deployment-Form würde die Stufe entwerten.

`applies_when: 'transport != "stdio-only"'` — dieselbe Klausel wie `SEC-016`, und hier ist die Transport-Bedingung **richtig**: Der Angriff braucht einen HTTP-Listener. Das ist der Gegenfall zu `SEC-004`/`SEC-005`, wo dieselbe Bedingung falsch war, weil dort die ausgehende Seite geprüft wird.

`pdf_ref: "Sec 4.4"` — die eingehende Hälfte von DNS Rebinding; `SEC-004`/`SEC-005` decken unter derselben Referenz die ausgehende ab. Bewusst kein `Custom`: Das hätte `SEC` in die Provenance-Prüfung der eigenen Layer gezogen und eine README-Zeile erzwungen, die 23 von 24 Checks der Kategorie falsch einordnet.

**Platzhalter aufgelöst.** Der Satz «*(Verweis folgt — siehe Aufgabe 2.)*» aus dem letzten Release steht nicht mehr im Katalog; `SEC-016` verweist jetzt namentlich auf `SEC-024`.

**Abgrenzung zu `SEC-021` im Check verankert.** Dort ist «Allow-List aus Env-Var» ein Fail-Pattern — das gilt für Egress. Hier ist die Umgebungs-Konfiguration die geforderte Form, weil der von aussen erreichbare Name im Prozess prinzipiell unbekannt ist. Beide Variablen heissen in der Praxis `ALLOWED_HOSTS`; der Check sagt, wie man sie auseinanderhält.

Nachgezogen: `checks/MANIFEST.txt`, `SKILL.md` §2.1 (Intro 87 → 88, `SEC` 23/23 → 24/24, Total), `README.md` (Badge, vier Prosa-Stellen, `SEC`-Zeile inkl. Severity-Profil `8 critical · 13 high · 3 medium`, Total-Severity `41 high`), `docs/roadmap.md`, plus die Lock-Tests `test_parse_catalog.py` (`SEC: 23 → 24`) und `test_applicability.py` (`len(results) 87 → 88`). Die SKILL-Bereichsspalte `20–25` trägt 24 ohne Anpassung. Das srgssr-Baseline-Profil ist `stdio-only` — die Applicable-Schranke bleibt unberührt. 385 Tests.

### Geändert — `SEC-005`: Geltungsbereich erweitert, stdio-only nicht mehr ausgenommen

Nachzug zu `SEC-004`. Die Klausel lautete `transport != "stdio-only" and tools_make_external_requests == true`; neu gilt `tools_make_external_requests == true`.

**Das ist eine Ausweitung, keine Korrektur** — im Unterschied zu `SEC-004`, wo derselbe Handgriff eine Überanwendung zurücknahm. Hier bekommen Server einen `high`-Check, den sie bisher nicht bekamen:

| `transport` | ausgehende Requests | bisher | neu |
|---|---|---|---|
| `stdio-only` | **ja** | **gilt nicht** | **gilt** |
| `stdio-only` | nein | gilt nicht | gilt nicht |
| `dual` / `HTTP/SSE` | ja | gilt | gilt |
| `dual` / `HTTP/SSE` | nein | gilt nicht | gilt nicht |

Sachlich war die Konjunktion nie haltbar. Der in `SEC-005` beschriebene Angriff läuft vollständig auf der **ausgehenden** Seite: zwei DNS-Antworten für einen Hostnamen, den der Server selbst abruft. Der eigene Transport kommt darin nicht vor. Alle fünf Pass-Kriterien betreffen den ausgehenden Request — DNS-Auflösung einmalig, gepinnte IP in der TCP-Verbindung, `Host`-Header und SNI für TLS, Cert-Validation, ein DNS-Call pro Request. Kein einziges fragt, wie der Server angesprochen wird.

**Nicht zu verwechseln mit eingehendem DNS-Rebinding** — dem Angriff, bei dem eine Webseite den Browser des Opfers auf einen lokal lauschenden Server zeigen lässt. Der *ist* transportabhängig, und er hat eigene Checks: `SEC-016` (0.0.0.0-Binding) und `SDK-004` (CORS). Beide tragen ihre Transport-Bedingung zu Recht. `SEC-005` hatte sie nur geerbt, ohne dass sie zu seinem Angriffsmodell passte.

**Was das für das Portfolio heisst.** Jeder stdio-only-Server mit ausgehenden Requests bekommt am Merge-Tag einen `high`-Check, gegen den er nie gemessen wurde — im Beispielportfolio `zh-education-mcp`, im Test-Baseline-Profil `srgssr` (49 → 50 anwendbare Checks). Bei einem Portfolio aus überwiegend lokal laufenden Servern trifft das die Mehrheit.

`SKILL.md` 2.3 beschreibt für genau diese Lage den Weg über `adoption: advisory`. Er wird hier **bewusst nicht** gegangen: Die Stufe wirkt pro Check, nicht pro Profilsegment. `SEC-005` auf `advisory` zu setzen, würde die Blockierung auch dort aufheben, wo sie heute schon greift — eine Demotion für die Server mit Netzwerk-Transport, die niemand verlangt hat, als Preis für die Schonung der neu erfassten. Die ehrlichere Variante ist, die Ausweitung als solche zu benennen und einen Portfolio-Durchlauf vor dem Release einzuplanen.

Die Umstellung auf `advisory` bleibt eine Zeile, falls ein Durchlauf zeigt, dass der Rückstand zu gross ist.

**Tests:** `TestSsrfScope` läuft jetzt über beide Checks der Familie (`SEC-004`, `SEC-005`) statt nur über `SEC-004` — Verhalten über drei Transportwerte × beide Request-Zustände, plus die strukturelle Prüfung, dass die Klausel `transport` nicht mehr nennt. Der Subset-Test `SEC-005` ⊆ `SEC-004` bleibt; beide Klauseln sind jetzt identisch, und er hält fest, dass sie nicht wieder auseinanderlaufen. Gegengeprobt: alte Klausel eingesetzt → zwei Tests rot, beide auf `SEC-005` benannt. 381 → 385 Tests.

**Beobachtung, nicht geändert:** `SEC-004` und `SEC-005` haben jetzt identische Reichweite, und ihre Pass-Kriterien überlappen an einer Stelle — `SEC-004` verlangt bereits «DNS-Resolution erfolgt einmal, resolved IP wird für den eigentlichen Request verwendet». `SEC-005` sagt dazu selbst, es prüfe das «spezifisch, weil viele SSRF-Implementations DNS-Pinning vergessen». Das ist eine bewusste Doppelung, aber sie erzeugt bei einem Server, der Pinning vergisst, zwei Findings für eine Ursache — die Sorte Überlappung, vor der `SKILL.md` 2.5 warnt. Ob die beiden zusammengelegt gehören, ist eine eigene Frage.

### Behoben — `SEC-004`: SSRF hängt am ausgehenden Request, nicht am eigenen Transport

Die Klausel lautete `transport != "stdio-only" or tools_make_external_requests == true`. Der Transport-Disjunkt zog jeden Server mit Netzwerk-Transport hinein — auch einen ohne einen einzigen ausgehenden Request.

| `transport` | ausgehende Requests | bisher | korrigiert |
|---|---|---|---|
| `stdio-only` | ja | gilt | gilt |
| `stdio-only` | nein | gilt nicht | gilt nicht |
| `dual` / `HTTP/SSE` | ja | gilt | gilt |
| `dual` / `HTTP/SSE` | **nein** | **gilt** | **gilt nicht** |

Nur die letzte Zeile ändert sich, und dort war die alte Antwort falsch. SSRF setzt voraus, dass der Server eine URL abruft, die aus Tool-Argumenten stammt. Wie er selbst angesprochen wird, ist dafür ohne Belang: Ein stdio-only-Server, der URLs fetcht, ist voll exponiert — und war schon vorher erfasst. Ein HTTP-Server ohne ausgehende Requests hat keine SSRF-Oberfläche; jedes der sechs Pass-Kriterien beschreibt dort einen Request, den es nicht gibt.

Neu: `applies_when: 'tools_make_external_requests == true'` — dieselbe Form, die bereits zehn andere Checks tragen (`FID-*`, `DRIFT-*`, `IDENT-001`).

**Ein Fehlalarm auf `critical` ist teuer.** Er kostet Prüfzeit an einem Befund, der keiner ist, und wenn er sich über ein Portfolio wiederholt, gewöhnt er die Leser daran, `critical` zu überblättern. Das ist die Währung, die ein Katalog nicht ausgeben darf. `SKILL.md` nennt den Applicability-Filter genau dafür: «Ohne diesen Filter überfluten irrelevante Findings den Report.»

**Die Netzwerk-Ebene bleibt geprüft.** `SEC-021` (Egress-Allow-List) greift bei `tools_make_external_requests == true or is_cloud_deployed == true`. Die Zuständigkeit für ein Cloud-Deployment lag also nie beim Transport, sondern bei `is_cloud_deployed` — SEC-004 hat sie doppelt und mit dem falschen Feld mitgeführt.

Drei Regressionstests in `tests/test_applicability.py`:

- **Verhalten** — über alle drei Transportwerte × beide Request-Zustände. Der Transport darf das Ergebnis in keiner Richtung beeinflussen.
- **Struktur** — die Klausel darf `transport` nicht mehr nennen. Ohne diesen Test käme eine Formulierung durch, die den Transport führt, ohne das Ergebnis zu ändern (`… and transport != "carrier-pigeon"`); gegengeprobt, dass genau sie nur hier auffällt.
- **Verfeinerung ⊆ Grundfall** — `SEC-005` beschreibt sich im Text als Verfeinerung von `SEC-004`. Solange das dasteht, darf es kein Profil geben, für das die Verfeinerung greift und der Grundfall nicht. Sonst verlangt der Katalog die Härtung gegen DNS-Rebinding von einem Server, dem er die SSRF-Basisprüfung erlässt.

Gegengeprobt: alte Klausel wieder eingesetzt — drei Tests rot; Tarnvariante eingesetzt — der strukturelle Test rot. 376 → 381 Tests.

**Offen, bewusst nicht mitgeändert:** `SEC-005` trägt `transport != "stdio-only" and tools_make_external_requests == true`. Nach derselben Logik ist auch dort der Transport-Teil fragwürdig — ein stdio-only-Server, der URLs fetcht, ist gegen DNS-Rebinding genauso angreifbar. Das wäre aber eine *Ausweitung* auf `critical`-Nachbarschaft und damit eine eigene Entscheidung, keine Korrektur im selben Zug.

### Behoben — `transport`: eine Schreibweise, zwei Vokabulare, vier still verlorene Checks

Der Katalog beschrieb dieselbe geschlossene Werteliste an fünf Orten und kam auf zwei Antworten. `SKILL.md`, `templates/audit-report.md` und jede `applies_when`-Klausel sagten `stdio-only / dual / HTTP/SSE`. `portfolio.example.yaml` und der Slash-Command empfahlen `stdio-only, dual, HTTP, SSE`.

**`HTTP` und `SSE` waren nie eigene Transporte** — sie sind eine zweite Schreibweise für `HTTP/SSE`. Wer der Empfehlung folgte, schrieb einen Wert ins Profil, gegen den keine Klausel je vergleicht.

Der Schaden war messbar, nicht hypothetisch. Ein Profil mit `transport: HTTP`, sonst identisch:

| | anwendbare Checks |
|---|---|
| `transport: HTTP/SSE` | 61 |
| `transport: HTTP` | 57 |

Verloren: `SCALE-002`, `SCALE-003` (beide `high`), `SCALE-007`, `SDK-004`. Gleichzeitig griff jede `transport != "stdio-only"`-Klausel weiter — die `SEC`-Checks liefen also, die `SCALE`-Checks nicht. Halb erkanntes Profil, sauberer Report, kleinerer Katalog als behauptet. Genau der Fall aus `OPS-005`: Was nicht gelaufen ist, sieht aus wie bestanden.

**Warum nichts es gemeldet hat.** `tools/validate_profile.py` trug die Begründung im Docstring: *«It does NOT validate semantics like "is `transport` a valid enum value". That's intentionally out of scope; the canonical evaluator surfaces those mismatches loudly via UnknownFieldError / TypeMismatchError once applies_when runs.»*

Das stimmte nicht, und der Irrtum verdeckte sich selbst. `UnknownFieldError` feuert bei einem unbekannten **Feld**, `TypeMismatchError` bei einem unpassenden **Typ**. Ein unbekannter **Wert** ist ein gewöhnlicher String: `transport == "HTTP/SSE"` gegen `transport: "HTTP"` ergibt schlicht `False`. Keine Exception, keine Warnung, keine Zeile im Report. Die Ausrede, warum nicht geprüft wird, war zugleich der Grund, warum niemand nachsah.

**Behoben:**

- **Kanonisch sind drei Werte** — `stdio-only`, `dual`, `HTTP/SSE`. Der Katalog unterscheidet HTTP und SSE nirgends; eine Aufspaltung hätte jede Netzwerk-Klausel zu einer Vierfach-Disjunktion gemacht, ohne ein einziges Audit-Ergebnis zu ändern. `portfolio.example.yaml` und `.claude/commands/audit-mcp.md` nachgezogen.
- **`ALLOWED_VALUES` in `tools/validate_profile.py`** als einzige Quelle, plus neue Report-Kategorie `enum_mismatch`. Ein unbekannter Wert ist jetzt Exit 1 vor Step 2, mit den erlaubten Werten im `allowed`-Feld — statt eines stillen Filters.
- **Bewusst nicht gepinnt:** `auth_model` und `data_class`. Sie tragen dokumentierte Werte, die kein Check einzeln abfragt (`OIDC`, `Verwaltungsdaten`), abgedeckt von den `!=`-Klauseln. Ein Wert, den niemand vergleicht, ist dort eine Lücke im Katalog, kein Fehler im Profil. `transport` war anders: gleicher Begriff, zwei Schreibweisen.
- **Keine stille Normalisierung.** `HTTP` wird nicht auf `HTTP/SSE` umgeschrieben. Ein Wert, der klammheimlich etwas anderes bedeutet, ist dieselbe Fehlerklasse in neuer Verpackung — die Korrektur ist eine Zeile im Profil bzw. im Notion-Select.

**Neu `tests/test_transport_vocabulary.py`** (7 Tests): Katalog-Literale ⊆ `ALLOWED_VALUES`, jeder erlaubte Wert wird von mindestens einer Klausel tatsächlich abgefragt (ein totes Vokabular-Mitglied lädt genau zu dem Fehler ein, aus dem `HTTP` kam), und alle vier Doku-Orte nennen dieselbe Liste. Jede Prüfung scheitert auch, wenn ihr Muster **gar nichts** findet.

Zwei Details, die beim Schreiben auffielen und im Test stehen:

- Die Klausel-Literale werden **nur aus dem Frontmatter** gelesen, nie aus dem Body. `ARCH-004`, `SEC-006` und `SEC-016` enthalten Python-Beispiele wie `settings.transport == "stdio"` — das ist die Config des *geprüften Servers*, nicht das Audit-Profil. Ein Scan über die ganze Datei hält sie fälschlich für Vokabular-Drift.
- Der Trenner in den Aufzählungen ist ein **umschlossener** Slash: `a / b` trennt, `HTTP/SSE` ist ein Wert. Wer den engen Slash als Trenner liest, schreibt `HTTP` ins Profil — die Verwechslung, die den Fehler überhaupt erzeugt hat.

Gegengeprobt: Drift in Doku, Katalog und Beispielprofil einzeln eingebaut, jedes Mal schlägt der zuständige Test an und schweigt nach der Rücknahme. 357 → 376 Tests.

### Hinzugefügt — `SCALE-007`: Der Reconnect findet die Session und verliert die Antwort

Der Katalog wächst auf **87 Checks**. `SCALE-007` prüft, ob ein Server einen abgerissenen Streamable-HTTP-Stream wiederaufnimmt: `id:` an den SSE-Events, `Last-Event-ID` beim Reconnect, Replay der verpassten Events aus einem Event-Store.

**Erst gegen §2.5 geprüft, dann geschrieben.** `SCALE-001` fragt nach der Transport*wahl*, `SCALE-002` und `SCALE-003` nach der *Affinität* beim Reconnect. Beide Klauseln zu weiten hätte nichts geholfen — die Frage ist eine andere, nicht ein ausgeschlossener Fall. Und die Verification von `SCALE-002` zu erweitern hätte genau das erzwungen, was §2.5 als Signal für einen eigenen Check nennt: ein `oder` in den Pass-Criteria («Sticky Sessions *oder* Event-Store»), das die beiden Hälften als Alternativen ausgibt, obwohl sie unabhängig voneinander nötig sind. Affinität bringt den Reconnect auf die richtige Instanz; Resumability bringt die verpassten Bytes zurück. Sticky Sessions korrekt, `Mcp-Session-Id` gültig, richtiger Pod — und die Antwort auf den laufenden Tool-Call ist trotzdem weg.

Der Abriss ist der Normalfall: Proxy-Idle-Timeouts liegen im Minutenbereich, ein Rolling Deploy beendet den Pod, ein Mobilfunkwechsel wechselt die IP. Genau dann läuft der lange Tool-Call, für den sich Streaming überhaupt lohnt. Für den Client sieht das nicht wie ein Fehler aus, sondern wie ein geschlossener Stream — kein JSON-RPC-Error, kein Statuscode, nichts, woran eine Fehlerbehandlung greift. Der Reflex ist, den Tool-Call zu wiederholen; ohne `ARCH-010` ist das eine zweite Ausführung.

Zwei Punkte, die der Check über das blosse Vorhandensein eines Stores hinaus prüft:

- **Wo der Store liegt.** Ein `InMemoryEventStore` überlebt weder Pod-Neustart noch einen Reconnect auf eine andere Replica — also genau die beiden Fälle, für die Resumability existiert. Geteilter Session-State (`SCALE-002`) neben lokalem Event-Store ist ein inkonsistentes Deployment.
- **Wie weit der Replay reicht.** Event-IDs sind pro Session eindeutig, die Folgen aber pro Stream. Ein Store, der nach ID sucht und alles Jüngere nachspielt, mischt die Antwort eines fremden Requests in die wiederaufgenommene Verbindung.

`medium`, nicht `high`: Die Spec stellt Resumability als **MAY**, und bei lesenden Tools kommt ein wiederholender Client ans Ziel. Degradiert, nicht kaputt — die Kategorie behält damit ihr Profil `3 high · 4 medium`. Keine Adoptionsstufe: `advisory` hebt das Veto auf `critical`/`high` auf, das ein `medium`-Check ohnehin nie hat, und wäre hier Zeremonie ohne Wirkung.

Gegenprobe im Check verankert — einmal mit erfundener `Last-Event-ID` aufrufen. Ein Server, der darauf stillschweigend alles nachspielt, was er hat, hat den Resume-Pfad nicht implementiert, sondern nur einen zweiten Weg zum Vollreplay.

Nachgezogen: `checks/MANIFEST.txt`, `SKILL.md` §2.1 (Intro, `SCALE`-Zeile, Total), `README.md` (Badge, Prosa, Kategorien-Zeile inkl. Severity-Profil, Total-Severity), `docs/roadmap.md` `Stand:`. Dazu die beiden Lock-Tests, die den Bestand hart pinnen: `test_parse_catalog.py::test_category_distribution` (`SCALE: 6 → 7`) und `test_applicability.py` (`len(results) 86 → 87`). Das srgssr-Baseline-Profil ist `stdio-only` und nicht cloud-deployed — die Applicable-Schranke bleibt unberührt. 357 Tests.

### Hinzugefügt — Zwei Regeln zur Audit-Methode (kein neuer Check)

Der Katalog bleibt bei **86 Checks**. Beide Ergänzungen betreffen, *wie* geprüft wird, nicht *was* — sie gehören deshalb in `SKILL.md`, nicht in `checks/`. Die erste ist zugleich ihr eigenes erstes Anwendungsbeispiel.

**§2.5 «Reichweite vor neuer Regel».** Ein Fund, den kein Check gemeldet hat, löst den Reflex aus, einen neuen Check zu schreiben. Häufiger als eine fehlende Regel ist eine vorhandene, die zu eng angewandt wurde. Drei Fragen in fester Reihenfolge: Schliesst `applies_when` den Fall aus? Nennt die Verification nur *einen* Endpoint, *ein* Artefakt? Erst danach: Ist es wirklich eine eigene Prüfdimension?

Beide Ausgänge sind belegt. *Reichweite:* Die Guard-Tests pinnten Katalogzahlen und liessen trotzdem «Zehn Kategorien» über einer Tabelle mit elf Zeilen durch — es fehlte kein Test, der vorhandene reichte nur bis zur Intro-Zeile. *Wirklich neu:* Die Kategorie `FID` entstand an einem Server, der 68 Checks bestanden hatte und den keine der acht damaligen Kategorien nach Datentreue fragte.

Zwei Checks mit teilweiser Überlappung sind schlimmer als einer mit korrekter Reichweite: Sie doppeln das Finding, und wenn der Server die Ursache behebt, bleibt der zweite rot — der Fix sieht aus, als hätte er nicht gewirkt. Gegen den Gegenfehler, den Sammelbehälter-Check, steht ein konkretes Signal: Wenn die Erweiterung ein `oder` in die Pass-Criteria zwingt, das mit dem ursprünglichen Kriterium nichts zu tun hat, ist es ein neuer Check.

**§4.1 Whitespace normalisieren, bevor auf Text geprüft wird.** `assert "not in TERMDAT" in tool.__doc__` schlug fehl, weil das Quellformat zwischen `in` und `TERMDAT` umbricht. Der Docstring enthielt den Satz. Die Prüfung meldete «fehlt».

Falsch-negativ ist hier der teure Fehler: Er führt zu einem Finding, einer Remediation-Empfehlung und einer Änderung an etwas, das bereits stimmte — im schlimmsten Fall zu einem Duplikat des vorhandenen Satzes. Ein Prüfergebnis, das an einem Umbruch hängt, prüft die Formatierung, nicht den Inhalt. Neu mit `re.sub(r"\s+", " ", …)` für Python, `tr` bzw. `rg -U` für die Kommandozeile, einer Liste, was normalisiert werden muss (Docstrings, Fliesstext, YAML-`>`-Blöcke) und was nicht (Code, Einrückung als Syntax, Diffs), und der Gegenprobe: Eine Prüfung, die nach der Normalisierung *immer* zutrifft, hat nur gelernt, alles zu bestehen.

`FID-005` bekommt einen Verweis darauf — dessen `grep`-Begriffe sind bewusst einzelne Wörter, und der Grund dafür stand bisher nirgends.

**Die Guard-Tests waren selbst betroffen.** `INTRO_SIZE` verlangte je ein hartes Leerzeichen zwischen «86», «Checks», «in», «elf», «Kategorien» — die Prosa hätte nur umbrechen müssen, und der Zeilen-Scan hätte die Angabe nicht mehr gefunden. Eine veraltete Zahl stünde dann ungeprüft im Dokument, ohne dass ein Test rot wird. Trenner jetzt `\s+`, dazu `test_no_count_claim_hides_in_a_line_break`: dieselbe Suche ein zweites Mal auf dem geglätteten Text, und weniger Treffer im Zeilen-Scan sind ein Fehlschlag. Gegengeprobt — bei eingebautem Umbruch schlägt der Test an, ohne Umbruch schweigt er. Das ist §2.5 an sich selbst angewandt: kein neuer Check, ein zu kurz greifender bestehender.

Dazu Anti-Patterns 7 und 8, zwei Eselsbrücken und ein Checklisten-Punkt. 357 Tests.

### Hinzugefügt — `OPS-005`: Übersprungen ist nicht bestanden

Der Katalog wächst auf **86 Checks**. `OPS-005` zieht die Linie aus `OPS-004` eine Ebene tiefer: Dort geht es um einen Report, der Gemessenes von Geschlossenem trennt; hier um eine Pipeline, die «bestanden» von «nicht gelaufen» unterscheidet.

Ein Check, der nicht gelaufen ist, sieht in jeder Zusammenfassung exakt aus wie einer, der bestanden hat. Das ist keine Nachlässigkeit im Einzelfall, sondern eine Eigenschaft der Werkzeuge: CI-Oberflächen zeigen Fehlschläge, nicht Abwesenheiten.

Vier Ausprägungen, alle real im Portfolio beobachtet:

1. **Die ganze Suite lief nie.** `mcp-continuous-auditor` hatte über 150 Tests und keinen Workflow, der sie ausführte — `ci.yml` lag als `.yml.template` für Zielrepos. 167 Läufe in der Repo-Historie, kein einziger ein Test.
2. **Tests skippen wegen fehlender Abhängigkeit.** Drei Klassen desselben Repos meldeten `skipped 'fastmcp not installed'`. Die Suite war grün.
3. **`continue-on-error` ohne sichtbare Folge.** Die Abdeckung schrumpft still von Woche zu Woche.
4. **Der Exit-Code kommt vom falschen Befehl.** GitHub Actions führt `run:` unter Linux mit `bash -e` aus, **ohne** `pipefail`. In `python check.py | tail -4` bestimmt `tail` den Exit-Code. Genau das ist hier passiert — beim Verifizieren eines Gates, das korrekt angeschlagen hatte.

- **Erster Check mit `adoption: advisory`.** `OPS-005` geht den in `SKILL.md` 2.3 dokumentierten Weg: Er meldet und blockiert nicht, bis ein Portfolio-Durchlauf zeigt, ob er richtig geschnitten ist. Damit hat der letzte Release eingeführte Mechanismus seinen ersten Kunden — und der Katalog wächst um einen Check, ohne 30+ Server am Tag des Merges rot zu färben.
- **`test_nothing_is_advisory_yet` wird zu `test_advisory_set_is_pinned`.** Statt Leere wird die bekannte Menge festgenagelt: Jede Promotion oder Demotion fällt im Review auf. Dazu ein zweiter Test, der die Stufe davor schützt, zur Ausrede zu werden — höchstens ein Zehntel des Katalogs darf advisory sein.
- **Gegenprobe im Check verankert:** Ein Gate, das nicht scheitern kann, ist Dekoration. `OPS-005` verlangt, es einmal ohne die Abhängigkeit laufen zu lassen.

### Behoben — Guard-Test für Abschnitts-Überschriften

`test_skill_counts.py` prüfte die Intro-Zeile («86 Checks in elf Kategorien»), nicht aber die Abschnitts-Überschrift («### 2.1 Elf Kategorien»). Nach der Ergänzung der Kategorie `DRIFT` stand dort «Zehn», während die Tabelle darunter elf Zeilen hatte — korrigiert wurde das im letzten Release, gesichert ist es erst jetzt.

Neu `test_section_heading_states_category_count`. Der Test scheitert auch, wenn er **gar keine** passende Überschrift findet: Ein Muster, das nach einer Umbenennung ins Leere greift, prüft stillschweigend nichts mehr — dieselbe Fehlerklasse, die `OPS-005` beschreibt.

### Hinzugefügt — Adoptionsstufe `advisory` | `enforced`

Der Katalog hatte bisher nur eine Achse: Severity. Die sagt, **wie schlimm** ein Verstoss ist — aber nicht, **ob der Katalog das Portfolio schon darauf festnageln darf**. Ohne die zweite Achse trifft jeder neue Check am Tag des Merges 30+ Server als rote Pipeline, und so werden Checks zurückgenommen statt übernommen.

Der Anlass war konkret: Bei `FID-003` musste die positive Hälfte — eine Leermenge *soll* einen nächsten Schritt tragen — im promptfoo-Profil graded statt assertiert werden, weil `zurich-opendata-mcp` sie nicht erfüllt hätte. Das war eine Ad-hoc-Lösung für ein strukturelles Problem, dem das Vokabular fehlte.

| Stufe | Konsequenz |
|---|---|
| `enforced` | Ein `fail` auf `critical`/`high` blockiert Production-Readiness |
| `advisory` | Finding wird erzeugt, gezählt, mit voller Severity geführt — blockiert aber nicht |

- **Rückwärtskompatibel per Konstruktion.** Das Feld ist optional und defaultet auf `enforced`. Alle 85 Checks bleiben `enforced`; die Einführung des Mechanismus hat kein einziges Verdikt geändert. Ein Test hält fest, dass derzeit nichts advisory ist — wird er rot, war das eine bewusste Entscheidung und gehört in diesen CHANGELOG.
- **Advisory versteckt nichts.** Das Finding entsteht, trägt seine Severity, erscheint im Report. Nur das Veto entfällt. Eine Stufe, die den Befund unterdrückte statt nur sein Veto, wäre schlimmer als gar keine Stufe.
- **Ein grünes Verdikt verschweigt keine Advisory-Reisser.** `summary.advisory_findings` listet die Checks, die bei `enforced` blockiert hätten; `build_report.py` nennt sie in der Executive Summary auch dann, wenn Production-Readiness erreicht ist. Wer später promoviert, weiss vorher, was rot würde.
- **Der Katalog ist autoritativ, nicht die Ergebnisdatei.** Neu `aggregate --checks-dir`: die Stufe wird aus `checks/` nachgezogen. Ohne das Flag gilt, was in `verification-results.json` steht — und ein fehlendes Feld bekommt dort still den `enforced`-Default. Sichere Richtung, aber es heisst: Eine Advisory-Stufe wirkt nur, wenn der Katalog gelesen wird. Ergebnis-IDs, die der Katalog nicht kennt, werden laut gemeldet und behalten den blockierenden Default.
- **Ein Tippfehler ist ein harter Fehler.** `adoption: advisroy` bricht das Katalog-Parsen ab. Eine stille Demotion wäre die leiseste Art, einen Check zu verlieren.
- **Der Promotionsweg** steht in `SKILL.md` 2.3: als `advisory` mergen, einen Portfolio-Durchlauf auswerten, dann promovieren — die Promotion in den CHANGELOG, nicht in einen Diff, den niemand liest.
- **21 neue Tests** (`tests/test_adoption_stage.py`), in beide Richtungen: dass `enforced` weiter blockiert, dass `advisory` nicht blockiert, dass das Finding trotzdem entsteht, dass der Katalog die Ergebnisdatei überstimmt. 338 Tests grün.

### Behoben

- `SKILL.md` 2.1 trug noch die Überschrift «Zehn Kategorien», während die Tabelle elf Zeilen hatte und das Intro «elf Kategorien» sagte — ein Rest der `DRIFT`-Ergänzung. Die Guard-Tests prüfen die Intro-Zeile, nicht die Abschnitts-Überschrift; diese Lücke besteht weiterhin.

### Hinzugefügt — der sechste Ort: die GitHub-Repo-Description

v1.1.1 schloss mit dem Satz, keine Katalog-Angabe im Repo sei mehr ungesichert. Das stimmte — und liess offen, dass eine davon **ausserhalb** des Repos liegt: die Repository-Description auf GitHub.

Sie war prompt gedriftet. Während der Katalog von 68 über 78 auf 85 Checks in elf Kategorien wuchs, stand dort unverändert «68 Checks · 8 Kategorien». Kein Fehler mit Folgen für ein Audit, aber die erste Zeile, die jemand liest, der das Repo findet. Ein Wert, den nichts erzwingt, driftet — dieselbe Regel, aus der `IDENT-004` entstand, nur eine Ebene ausserhalb der Arbeitskopie.

- **`tools/check_repo_description.py`** holt die Description über die GitHub-API und hält ihre Zahlen gegen den geparsten Katalog. Geprüft werden ausschliesslich die Zahlen, nicht die Formulierung — die gehört der Autorin. Bei Abweichung gibt der Guard den **fertigen korrigierten Text** aus.
- **`.github/workflows/repo-description.yml`** führt ihn aus: nach dem Merge auf `main` (wenn `checks/**` betroffen ist), wöchentlich, und von Hand. Der Befund samt Ersatztext landet in der Job-Summary, nicht nur im Log.
- **`tests/test_repo_description.py`** — 16 Tests.

Der Guard **schreibt nicht**. Repo-Metadaten zu ändern ist ein Eingriff, der einer Person gehört; das Skript benennt die Abweichung und legt den Text daneben.

Drei Entscheidungen:

1. **Kein `pull_request`-Trigger.** Ein PR, der den Katalog wachsen lässt, macht die Description im selben Moment veraltet — und korrigieren kann sie nur ein Mensch in den Settings, nach dem Merge. Ein PR-Gate würde das falsche Ereignis bestrafen und wäre nach zwei Wochen abgeschaltet.
2. **Eine nicht erreichbare API ist kein Bestehen.** Ohne Antwort hat der Vergleich nicht stattgefunden; der Guard meldet `UNKNOWN` und endet mit 1, statt aus dem lokalen Katalog allein «stimmt» zu drucken. Das ist `DRIFT-003` auf den Guard selbst angewandt — und beim Bauen sofort eingetreten: In der Sandbox blockiert der TLS-Proxy `api.github.com`, und der Guard hat korrekt `UNKNOWN` gemeldet statt grün.
3. **Der Vergleich ist eine reine Funktion.** `compare()` nimmt den Description-String entgegen und ist ohne Netz testbar; `fetch()` ist absichtlich die dünnste Funktion der Datei und wird **nicht** gemockt. Ein Mock bildete nur die eigene Annahme über die GitHub-Antwort ab und könnte sie nie widerlegen — die Grenze, an der `DRIFT-004` ansetzt.

Damit hängen sechs Orte am Katalog:

| Ort | Gesichert durch |
|---|---|
| `checks/MANIFEST.txt`, Katalog-Grösse, Kategorien, Severities | `test_parse_catalog.py`, `test_applicability.py` |
| `README.md` | `test_readme_counts.py` |
| `SKILL.md` | `test_skill_counts.py` |
| `docs/roadmap.md` (`Stand:`-Zeile) | `test_roadmap_counts.py` |
| `.claude/commands/audit-mcp.md` (Kategorienliste) | `test_command_counts.py` |
| **GitHub-Repo-Description** | **`repo-description.yml` (ausserhalb des Repos, deshalb Workflow statt Test)** |

### Nachgetragen aus `[Unreleased]`

Die drei folgenden Abschnitte standen zum Zeitpunkt des Tags unter `[Unreleased]` und fehlten deshalb in den ursprünglich veröffentlichten Release-Notes — die beschriebene Arbeit ist aber in `v1.3.0` enthalten (Commits `b011432` und `da17222`, beide Vorfahren des Tags). Hierher verschoben, damit Tag-Inhalt und Notes übereinstimmen; die Release-Notes auf GitHub sind entsprechend nachgezogen.

### Dokumentiert — warum `SEC-005` `enforced` bleibt

Die Reichweiten-Erweiterung aus v1.3.0 hat die Frage aufgeworfen, ob der Check den in `SKILL.md` 2.3 dokumentierten Weg über `adoption: advisory` gehen sollte. Er tut es nicht — und der Grund steht jetzt im Check, nicht nur in einem PR-Kommentar.

Portfolio-Stand zum Zeitpunkt der Erweiterung: **3 Server bisher erfasst, 5 neu erfasst**, Reichweite also 3 → 8. Relativ fast eine Verdreifachung, absolut fünf Server. 2.3 begründet die Stufe mit «30+ Server als rote Pipeline am Tag des Merges» — bei fünf greift diese Begründung nicht.

Ausschlaggebend war die Asymmetrie: Die Stufe wirkt **pro Check, nicht pro Profilsegment**. `advisory` hätte die Blockierung auch bei den drei Servern aufgehoben, wo sie heute schon greift — ein Preis, der gewiss und unsichtbar ist, gegen einen, der ungewiss und laut ist.

Festgehalten sind auch die Umkehrbedingung (ein Durchlauf zeigt, dass alle fünf durchfallen und der Rückstand nicht in einem Sprint abbaubar ist) und die drei Orte, die eine Umstellung berührt. Ohne die Zahlen käme die Frage in drei Monaten wieder — und dann ohne die Zahlen.

Keine Katalog-Änderung: Reichweite, Severity und Adoptionsstufe von `SEC-005` bleiben, wie sie sind. 417 Tests unverändert.

### Behoben — `sdk_language` war Pflichtfeld für sieben Checks und stand nirgends

Sieben Checks fragen `sdk_language` ab (`SDK-001`…`SDK-006`, `IDENT-005`). Das Feld stand weder in `validate_profile.REQUIRED_FIELDS` noch in `portfolio.example.yaml`, noch im Slash-Command, im DSL-Doc oder in der Profil-Tabelle von `SKILL.md` — und `audit-notion-sync.py` hat es nie gesetzt.

**Die Reihenfolge war genau verkehrt.** Nachgemessen mit einem Profil, wie `build_profile()` es erzeugt:

```
validate_profile: consistent=True          ← das Gate lässt es durch
evaluate_catalog: 7 Checks unknown-field   ← erst hier fällt es auf
```

Das Validierungs-Gate existiert, um solche Löcher **vor** Schritt 2 zu fangen. Es war blind, weil das Feld nicht in seiner Liste stand. Der laute Fehlschlag im Evaluator war korrekt — er kam nur zu spät und traf jedes aus Notion gezogene Profil.

Nachgezogen an sechs Orten: `REQUIRED_FIELDS` (15 → 16 Felder), `portfolio.example.yaml`, `.claude/commands/audit-mcp.md`, `SKILL.md` (Profil-Tabelle, Beispielblock, Feldzahl), `docs/applies-when-dsl.md` und `audit-notion-sync.py`. Letzteres liest jetzt eine Notion-Property `SDK-Sprache` mit Default `Python` — dieselbe Konvention, die dort schon für `transport` und `auth_model` gilt.

**Bewusst nicht als geschlossenes Vokabular gepinnt.** Anders als `transport` ist `sdk_language` offen: Ein Server in Go oder Rust trägt eine Sprache, die kein Check abfragt — das ist eine Lücke im Katalog, kein Fehler im Profil, und ein harter Reject würde ein korrekt beschriebenes Profil abweisen. Der Preis ist derselbe Rest-Risiko wie bei jedem offenen Feld: `python` statt `Python` lässt sechs Checks still wegfallen. Ein Test hält die Entscheidung samt Begründung fest, damit eine spätere Umkehr eine bewusste ist.

Fünf Guard-Tests: Feld ist Pflichtfeld · der Katalog nutzt es überhaupt · jeder Wert, gegen den eine Klausel vergleicht, steht in allen vier Doku-Orten · es ist *nicht* in `ALLOWED_VALUES` · `audit-notion-sync.py` setzt es. 409 → 417 Tests.

### Behoben — `SEC-004` und `SEC-005` prüften dasselbe Kriterium doppelt

Seit `SEC-005` auf dieselbe Reichweite wie `SEC-004` erweitert wurde, trugen beide wortgleich dasselbe Pass-Kriterium:

| | Kriterium |
|---|---|
| `SEC-004` | «DNS-Resolution erfolgt **einmal**, resolved IP wird für eigentlichen Request verwendet (kein TOCTOU)» |
| `SEC-005` | «DNS-Resolution erfolgt **einmalig** vor dem HTTP-Request» + «Resolved IP wird für die TCP-Connection verwendet» |

Ein Server, der DNS-Pinning vergisst, erzeugte damit **zwei Findings für eine Ursache** — eines auf `critical`, eines auf `high`. Und nach dem Fix wäre eines davon rot geblieben, weil niemand daran denkt, zwei Checks nachzuführen. Genau der Schaden, den `SKILL.md` §2.5 beschreibt: «Sie doppeln das Finding, und wenn der Server die Ursache behebt, bleibt der zweite rot — der Fix sieht aus, als hätte er nicht gewirkt.»

**Aufgelöst durch Entflechtung, nicht durch Zusammenlegen.** `SEC-004` prüft, ob die aufgelöste IP *erlaubt* ist (HTTPS-Enforcement, Blocklisting); `SEC-005`, ob sie auch die *benutzte* ist (Pinning). Das doppelte Kriterium und die zugehörige Common-Failures-Zeile sind aus `SEC-004` entfernt, beide Checks benennen die Grenze ausdrücklich.

Zusammengelegt wurden sie nicht, weil §2.5 auch die Gegenrichtung kennt: Ein Check muss **in einem Schritt behebbar** bleiben. Blocklisting und Pinning sind getrennt behebbar — ein Server kann die Blockliste korrekt führen und trotzdem zweimal auflösen. Das sind zwei Befunde mit zwei Remediationen.

Das Pass-Pattern von `SEC-004` löst weiterhin einmal auf und verwendet die IP — echter Code macht beides in derselben Funktion. Nur das *Kriterium* liegt jetzt an einer Stelle. Der Unterschied steht im Check, damit ihn niemand für eine Lücke hält.

## [v1.2.0] — 2026-07-30 — Vertrag mit der Quelle, und was davon gemessen ist

Der Katalog wächst von **78 auf 85 Checks** in **elf statt zehn Kategorien**. Severity-Verteilung neu **16 critical · 39 high · 29 medium · 1 low** (v1.1.1: 16 · 34 · 27 · 1).

Beide Zuwächse stammen aus dem Betrieb, nicht aus einer Quelle — dasselbe Muster wie bei `FID` und `IDENT`:

| Zuwachs | Anlass |
|---|---|
| `DRIFT` (5 Checks) + `IDENT-006` | `meteoswiss-mcp`: drei von sechs Tools lieferten nichts, Unit-Tests grün, ein 68-Punkte-Audit bestanden. Gemeldet hat es ein aussenstehender Nutzer. |
| `OPS-004` | Nachlauf zu `termdat-mcp#11`: Eine als Vermutung gekennzeichnete Erklärung stand zwei Tage als Quasi-Ergebnis im Raum — und war falsch. |

Zusammen schliessen sie zwei benachbarte Lücken. `DRIFT` fragt, ob der Vertrag mit der Datenquelle noch gilt und ob überhaupt etwas es bemerken würde. `OPS-004` fragt dasselbe für den Audit-Report selbst: Was davon ist gemessen, was geschlossen, was offen.

Bemerkenswert an beiden Fällen ist nicht der Fehler, sondern wer ihn gefunden hat: in beiden ein Aussenstehender, an einer grünen Testsuite und einem bestandenen Audit vorbei.

### Zur Versionsnummer

Minor, und diesmal ohne Vorbehalt: eine neue Kategorie, sieben neue Checks, keine entfernte oder geänderte Schnittstelle. Wer gegen v1.1.1 auditiert hat, bekommt zusätzliche Befunde, aber keine anderen.

### Hinzugefügt — Neue Kategorie `DRIFT` (Upstream-Vertrag und Testgüte), 5 Checks, plus `IDENT-006`

Der Katalog wächst von 79 auf **85 Checks** in **elf Kategorien**. `DRIFT` entsteht auf demselben Weg wie seinerzeit `FID` und `IDENT`: aus einem einzelnen Vorfall im Betrieb, nicht aus einer Quelle.

**Der Vorfall** (`meteoswiss-mcp`, 30.07.2026): Drei von sechs Tools lieferten nichts — `meteo_current` einen 404 für jede Station, `meteo_forecast` und `meteo_school_check` gar keine Daten. Die Unit-Tests waren grün, ein 68-Punkte-Audit war bestanden, und gemeldet hat es ein aussenstehender Nutzer. Drei unabhängige Ursachen, zwei davon Änderungen bei den Datenquellen:

| Issue | Ursache |
|---|---|
| [#33](https://github.com/malkreide/meteoswiss-mcp/issues/33) | STAC-Item-ID falsch konstruiert — dieselbe URL an drei Stellen dupliziert, Fehlermeldung inklusive |
| [#35](https://github.com/malkreide/meteoswiss-mcp/issues/35) | Open-Meteo hat `/v1/meteoswiss` abgeschafft; die Mocks pinnten die eigene tote Konstante |
| [#37](https://github.com/malkreide/meteoswiss-mcp/issues/37) | Ortsnamen mit Zusatz gar nicht auflösbar |

Die bestehenden Kategorien prüfen, ob ein Server korrekt gebaut ist (`ARCH`, `SDK`, `SEC`), ob er liefert was die Quelle hat (`FID`) und als was er sich ausgibt (`IDENT`). Keine prüfte, **ob der Vertrag mit der Quelle noch gilt und ob überhaupt etwas es bemerken würde.**

- **`DRIFT-001`** (medium) — Endpoint- und Ressourcen-URLs an genau einer Stelle konstruiert. Im Vorfall stand dieselbe falsche URL dreimal im Code; die Fehlermeldung zitierte sie als Beleg und führte die Fehlersuche in die Irre.
- **`DRIFT-002`** (high) — Ein Fallback verengt, erweitert nie. Der Asset-Selektor fiel auf «erstes CSV» zurück und gab Tageswerte ab 1980 als «aktuelle Beobachtung» aus. Wo die Semantik nicht mehr stimmt, ist ein Fehler das bessere Ergebnis: ein Fehler wird gemeldet, ein semantisch falscher Datensatz wird zitiert.
- **`DRIFT-003`** (high) — Kein Test-Assert wird vom Degradationspfad erfüllt. Drei Tests prüften Stichworte, die auch in der Fehlermeldung stehen (`"KLO" in result or "Zürich" in result`); einer prüfte eine Koordinaten-Box, in der auch die *falsche* Gemeinde liegt. Sie liefen grün durch einen Totalausfall.
- **`DRIFT-004`** (high) — Endpoint-Konstanten live verifiziert. Ein `respx`-Mock wird gegen die eigene Konstante registriert; verschwindet der Endpoint upstream, antwortet der Mock unverändert. Die Frage «existiert dieser Endpoint noch» ist prinzipiell nicht gemockt beantwortbar.
- **`DRIFT-005`** (medium) — Live-Tests laufen geplant. `OPS-001` verlangt sie und schliesst sie aus CI aus; damit führt sie niemand aus. Beim ersten Ausführen seit Monaten fielen drei von sechs um.

Dazu in `IDENT`:

- **`IDENT-006`** (high) — Kein Release-Gap zwischen `main` und dem Artefakt. `IDENT-001`–`005` prüfen, ob die gemeldete Version *korrekt* ist; dieser prüft, ob sie *aktuell* ist. Im Vorfall lag der Fix seit drei Tagen auf `main`, während PyPI unverändert das kaputte `0.4.0` auslieferte — CI testet den Branch, nie das Artefakt. Deterministisch prüfbar mit `release_gap.py` aus dem [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor).

Severity-Verteilung neu **16 critical · 39 high · 29 medium · 1 low** (Stand vor diesem Eintrag: 16 · 35 · 27 · 1).

Hinweis zur Nummerierung: `DRIFT-003` hiess im ersten Entwurf `OPS-004`. Zwischenzeitlich ist auf `main` ein anderer `OPS-004` gelandet («Gemessenes von Geschlossenem trennen»); durch die Verschiebung nach `DRIFT` gibt es keine Kollision.

**Zur Platzierung.** Die fünf `DRIFT`-Checks lagen im ersten Entwurf in `ARCH` und `OPS`, weil sie thematisch dorthin passen. `tests/test_readme_counts.py` hat das zurückgewiesen: Eine Kategorie mit `Custom`-Provenance braucht eine eigene Zeile in der Provenance-Tabelle, und eine gemischte Kategorie kann keine haben, ohne die PDF-Herkunft der übrigen Checks falsch darzustellen. Der Test hat damit eine Design-Entscheidung erzwungen, die richtig ist und die der Entwurf umgangen hätte — genau das, wofür er da ist.

`tests/test_applicability.py`: Obergrenze der Anwendbarkeits-Schranke 45 → 51 (anwendbar gegen das srgssr-Profil: 48 von 85). Alle sechs neuen Checks greifen bei einem Server mit externer Datenquelle; das ist Katalogwachstum, nicht die Grammatik-Drift, gegen die die Schranke schützt.

### Hinzugefügt — `OPS-004`: Gemessenes von Geschlossenem trennen

Der Katalog wächst auf **79 Checks**. `OPS-004` überträgt die Regel aus `FID-003` vom Server auf den Auditor: Ein Audit-Report darf einen unerklärten Rest so wenig für den Leser deuten, wie ein Tool eine Leermenge für das Modell deuten darf.

Anlass ist der Nachlauf zu [`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11), und es ist ein Eigenbefund. Nach der Behebung des eigentlichen Bugs blieb eine Differenz — Weboberfläche 12 Einträge, API 7 bei maximalem Recall. Dazu wurde eine plausible Erklärung veröffentlicht: das Web-UI zähle Benennungen statt Einträge, also eine Zähldifferenz. Die Formulierung war als Vermutung gekennzeichnet und trotzdem falsch. Der Melder schickte die zwölf Entry-IDs, alle verschieden; tatsächlich liefert die API zehn davon überhaupt nicht aus, auch nicht beim gezielten Abruf per ID. Die Vermutung stand zwei Tage als Quasi-Ergebnis im Raum. Hätte niemand nachgefragt, wäre sie zur Dokumentation geworden.

- **`checks/OPS-004.md`** — drei Ausprägungen des Musters (Vermutung als Ergebnis, Rest weggerundet, Abwesenheit von Belegen als Beleg), Verifikation über Report-Struktur und Status-Vergabe.
- **`templates/finding.md` und `templates/audit-report.md`** — neuer Pflichtabschnitt **Gemessen / Geschlossen / Offen**. Ohne ihn wäre der Check nicht erfüllbar; die Templates sind der Ort, an dem er praktisch wirkt.
- **Zwei Regeln mit Zähnen.** Bleibt «Offen» leer, steht dort ausdrücklich *keine offenen Punkte* — ein weggelassener Abschnitt ist von einem unbearbeiteten nicht unterscheidbar. Und ein `pass` braucht einen positiven Beleg: Ein leerer `grep` ist nur dann ein `pass`, wenn das Suchmuster nachweislich greifen *würde*, sonst `not_verified`.
- **Eine Technik, die im Ausgangsfall funktioniert hat**, ist als Anforderung kodiert: Jeder offene Punkt trägt **eine** Frage, deren Antwort zwischen den Hypothesen entscheidet. «Entsprechen die 12 Treffer 12 verschiedenen Entry-IDs?» hat den Fall in einer Runde erledigt.
- **Severity `high`, nicht `medium`.** Ein einzelner falscher Befund ist ärgerlich; ein Report, der Vermutungen und Messungen vermischt, macht alle seine Befunde unzuverlässig, weil dem Leser das Unterscheidungsmerkmal fehlt.
- Katalog-Metadaten: `MANIFEST.txt`, Kategorien-Tabellen in `SKILL.md` und `README.md`, Severity-Verteilung neu **16 critical · 35 high · 27 medium · 1 low**.

## [v1.1.1] — 2026-07-30 — Jede Zusage im Repo hat jetzt einen Test

Der Katalog bleibt unverändert bei **78 Checks in zehn Kategorien**. Dieses Release ändert nichts an dem, was der Skill prüft — es schliesst die letzten beiden Stellen, an denen das Repo eigene Angaben nur auf Disziplin stützte.

Damit ist keine Zahl und keine Versionsangabe im Repo mehr ungesichert:

| Ort | Quelle der Wahrheit | Test |
|---|---|---|
| `checks/MANIFEST.txt`, Katalog-Grösse, Kategorien, Severities | Katalog | `test_parse_catalog.py`, `test_applicability.py` |
| `README.md` | Katalog | `test_readme_counts.py` |
| `SKILL.md` | Katalog | `test_skill_counts.py` |
| `docs/roadmap.md` (`Stand:`-Zeile) | Katalog | `test_roadmap_counts.py` |
| `.claude/commands/audit-mcp.md` (Kategorienliste) | Katalog | `test_command_counts.py` |
| `--skill-version` (drei Fundorte) | CHANGELOG | `test_skill_version_literals.py` |

Bewusst ausgenommen bleiben `CHANGELOG.md` und die historischen Stände in `docs/roadmap.md`: Dort ist eine veraltete Zahl die richtige Zahl.

### Zur Versionsnummer

Ein Patch, kein Minor: keine Katalogänderung, keine Verhaltensänderung, nur Absicherung bestehender Zusagen plus ein korrigiertes Doku-Literal. Für Anwender des Skills ändert sich nichts — die Tests wirken im Repo, nicht im Audit.

Die neuen Test-Module sind sichtbare Arbeit, aber keine neue Fähigkeit des Skills. Wer `1.1.0` gegen `1.1.1` vergleicht, soll genau das erwarten dürfen.

### Hinzugefügt — `--skill-version`-Literale an die Release-Version gebunden

Die letzte ungesicherte Versionsangabe, und die einzige, die nicht am Katalog hängt: Quelle ist die oberste Release-Überschrift im CHANGELOG.

Unbewacht ist dieser Wert besonders anfällig, weil er nirgends im Code vorkommt — `audit_init.py` kennt keinen Default ausser `"unspecified"`, die Doku-Beispiele sind die einzige Quelle. Wer den Befehl kopiert, schreibt den dort stehenden String in seine `audit-meta.json`, und daran hängt später, mit welcher Skill-Version ein Befund entstanden ist. Ein falscher Wert fällt nie auf und lässt sich im Nachhinein nicht rekonstruieren.

**`tests/test_skill_version_literals.py`** durchsucht alle `.md`- und `.py`-Dateien nach `--skill-version <version>` und verlangt für jeden Fundort die aktuelle Release-Version. Ausgenommen sind `CHANGELOG.md` (dort ist jede Zahl historisch) und `tests/` (Fixtures brauchen freie Versionen). Zusätzlich geprüft werden die Existenz mindestens eines Fundorts und das Format der Release-Überschrift — ohne beides hinge der Test an einer leeren Quelle und liefe still grün.

### Behoben — dritter `--skill-version`-Fundort war beim v1.1.0-Release übersehen worden

Der Release-Eintrag zu v1.1.0 nennt `SKILL.md` und `.claude/commands/audit-mcp.md` als «die einzige Quelle». Das war unvollständig: Die Usage-Zeile in **`tools/audit_init.py`** trug dieselbe Angabe und stand weiter auf `1.0.0` — ausgerechnet in der Datei, die den Wert entgegennimmt.

Gefunden hat ihn der Test oben beim ersten Lauf. Aufzählungen von Hand sind genau die Fehlerquelle, die er ersetzt; er zählt deshalb alle Fundorte, statt eine gepflegte Dateiliste abzuarbeiten.

### Hinzugefügt — Kategorienliste im Slash-Command gesichert

Die vierte und letzte ungesicherte Katalog-Angabe, und die einzige, deren Fehler das **Verhalten** ändert statt nur eine Anzeige: `.claude/commands/audit-mcp.md` nennt die Kategorien in der Einleitung namentlich. Diese Zeile ist Instruktion, keine Dokumentation — sie sagt Claude, woraus der Katalog besteht, bevor ein einziger Check gelesen wird.

Bis v1.1.0 stand dort «7 Kategorien: ARCH, SDK, SEC, SCALE, OBS, HITL, CH». `OPS` fehlte schon zu v1.0.0-Zeiten, `FID` und `IDENT` kamen danach dazu: drei von zehn unterschlagen, und nichts hat es gemeldet. Korrigiert wurde die Zeile im v1.1.0-Release, gesichert ist sie erst jetzt.

**`tests/test_command_counts.py`** vergleicht die Liste **elementweise** gegen den Katalog, nicht bloss ihre Länge — eine falsche Länge ist der harmlosere Fehler, ein falscher Name der stille. Geprüft werden ausserdem die vorangestellte Zahl gegen die Anzahl gelisteter Einträge, Duplikate in der Liste und die Existenz des Ankers selbst.

Gegen fünf Mutationen geprüft, darunter die historische Regression (`7 Kategorien` mit verkürzter Liste), ein erfundener Kategoriename, eine Zahl die nicht zur Liste passt, ein Duplikat und das ersatzlose Entfernen der Zeile. Jede schlägt an.

Damit ist keine Katalog-Angabe im Repo mehr ungesichert: `checks/MANIFEST.txt`, `README.md`, `SKILL.md`, die `Stand:`-Zeile in `docs/roadmap.md` und der Slash-Command hängen alle am geparsten Katalog.

## [v1.1.0] — 2026-07-30 — Datentreue, Identität und gesicherte Doku-Zahlen

Der Katalog wächst von **68 auf 78 Checks** in **zehn statt acht Kategorien**. Beide neuen Kategorien kamen nicht aus einer Quelle, sondern aus dem Betrieb: `FID` aus einem einzelnen Vorfall an `termdat-mcp`, `IDENT` aus einem Sweep über alle 30 Server des Portfolios. Severity-Verteilung neu **16 critical · 34 high · 27 medium · 1 low** (v1.0.0: 15 · 31 · 22).

Dazu die operative Seite: Release-Vorschläge für auditierte Server, austauschbare Tracker-Backends — und eine Reihe von Stellen, an denen der Skill bisher auf Disziplin statt auf Tests baute.

### Hinweis zum Upgrade

Das Validation-Gate weist jetzt **leere Finding-Dokumente** ab. Ein Audit-Verzeichnis, das unter v1.0.0 `consistent: true` meldete, kann unter v1.1.0 `false` und Exit 1 liefern — nachweislich bei `amtsblatt-mcp` und `swiss-procurement-mcp` mit zusammen 16 leeren Platzhaltern. Das ist die Korrektur eines Gates, das die falsche Frage stellte (existiert die Datei? statt: steht etwas drin?), kann aber bestehende Pipelines rot machen. Wer eine solche Pipeline betreibt, prüft die betroffenen Verzeichnisse vor dem Upgrade mit `python tools/aggregate_results.py validate <audit_dir>`.

### Behoben — veraltete Versions- und Katalogangaben in der Doku

Beim Zusammenstellen des Releases aufgefallen, alle vom selben Typ, den `IDENT-004` beschreibt: eine dokumentierte Version, die nichts erzwingt.

- **`--skill-version "1.0.0"`** stand als Literal in `SKILL.md` und `.claude/commands/audit-mcp.md`. `audit_init.py` kennt keinen Default ausser `"unspecified"` — diese zwei Doku-Stellen sind die einzige Quelle. Wer den Befehl kopierte, schrieb nach diesem Release eine falsche `skill_version` in seine `audit-meta.json`. Auf `1.1.0` gezogen.
- **Der Slash-Command nannte «`mcp-audit-skill v0.5.0`-Katalog (7 Kategorien: ARCH, SDK, SEC, SCALE, OBS, HITL, CH)»** — zwei Majors alt und inhaltlich falsch: `OPS` fehlte bereits in v1.0.0, `FID` und `IDENT` kamen dazu. Der Command instruierte Claude also mit einer Kategorienliste, die drei Kategorien unterschlug. Korrigiert auf zehn; die Versionsangabe entfällt, weil `checks/MANIFEST.txt` die Quelle ist.
- **Die Spaltenüberschrift «Status v0.5.0»** in `SKILL.md` (2.1) trug eine Version, deren Inhalt längst aktuell war. Auf «Status» gekürzt.

Diese drei Stellen sind noch nicht durch Tests gesichert — die Kategorienliste im Slash-Command wäre der nächste Kandidat.

### Hinzugefügt — Stand-Zeile in `docs/roadmap.md` gesichert

Die dritte und letzte Stelle mit einer Katalog-Zahl. Anders als `README.md` und `SKILL.md` darf diese Datei **nicht** als Ganzes geprüft werden: Sie zitiert an mehreren Stellen historische Stände («Der v0.5.0-Katalog mit 68 Checks in 8 Kategorien», «+14 Checks aus Anhang-PDF»), die richtig sind und richtig bleiben sollen. Ein Test über alle Zahlen würde die Historie anmahnen — und wer ihn danach «grün macht», beschädigt sie.

Aktuell zu halten ist genau eine Zeile: die mit `Stand:` beginnende Kopfzeile. **`tests/test_roadmap_counts.py`** prüft nur sie, gegen Anzahl Checks und Anzahl Kategorien. Zusätzlich verlangt der Test, dass es diese Zeile überhaupt gibt — sonst liesse sich der Anker still entfernen und die Prüfung ins Leere laufen.

### Hinzugefügt — SKILL.md-Zahlen gegen den Katalog gesichert

Nach `README.md` jetzt auch `SKILL.md`, die zweite Stelle mit einer Kategorien-Übersicht. Das Format dort ist ein anderes: eine Spalte mit dem erwarteten Bereich («Typische Anzahl Checks», etwa `4–6`), eine mit dem Ist-Stand (`5 / 5 ✅`).

**`tests/test_skill_counts.py`** prüft die Einleitung («78 Checks in zehn Kategorien» — inklusive des ausgeschriebenen Zahlworts), die Kategorien-Tabelle auf Vollständigkeit gegenüber dem Katalog, den Ist-Stand je Kategorie sowie die Total-Zeile.

Dazu eine Prüfung, die über blosses Nachzählen hinausgeht: Der **dokumentierte Bereich muss den Ist-Stand einschliessen**. Wächst eine Kategorie darüber hinaus, ist nicht der Katalog falsch, sondern die Erwartung veraltet — und genau das soll auffallen, statt still zu bleiben.

Ausgenommen sind die Schätzwerte in der Prosa («~50 Checks», «~15–20 Checks» in Schritt 3): Sie beziffern, was nach dem Applicability-Filter typischerweise übrig bleibt, hängen also am Profil und nicht am Katalog. Eine Bindung an `len(catalog)` wäre dort schlicht falsch. Ebenso die Gesamt-Schätzung `~75` in der Total-Zeile, die die Bereichs-Spalte summiert und nicht den Bestand — von ihr wird nur verlangt, dass sie innerhalb der Summe aller Bereiche liegt.

`SKILL.md` war beim ersten Lauf korrekt; der Test wurde gegen vier künstliche Abweichungen geprüft (Einleitung, Ist-Stand einer Kategorie, Bereich, Total-Zeile) und schlägt bei jeder an.

`docs/roadmap.md` wird nur punktuell gesichert — siehe den Abschnitt darüber.

### Behoben — README-Zahlen gegen den Katalog gesichert

Die Katalog-Zählungen leben an drei Orten: `checks/MANIFEST.txt`, den Lock-Tests und der Prosa in `README.md`. Die ersten beiden prüft CI seit je, die dritte war ungesichert — und genau dort blieb beim Hinzufügen von `IDENT` die Aktualisierung aus. Ein Wert, den nichts erzwingt, driftet (derselbe Mechanismus, den `IDENT-003` für Server beschreibt).

**`tests/test_readme_counts.py`** liest die Zahlen aus `README.md` und vergleicht sie gegen den geparsten Katalog: Badge und Alt-Text, Prosa-Erwähnungen (`NN Checks`, `NN Kategorien`) ausserhalb von Tabellen, die Kategorien-Tabelle mit Anzahl **und** Severity-Profil je Kategorie, die Total-Zeile sowie die Layer-Zeilen der Provenance-Tabelle. Ausgenommen sind die beiden PDF-Zeilen der Provenance-Tabelle: Sie beschreiben historische Herkunft, überlappen mit den Layer-Zeilen und summieren sich bewusst nicht zum Total.

Der Test hat beim ersten Lauf zwei Bestandsfehler aufgedeckt, beide älter als `IDENT`:

- **Severity-Profile in der Kategorien-Tabelle** stimmten bei fünf von zehn Kategorien nicht mit dem Katalog überein — `ARCH` (war `1 critical · 7 high · 4 medium`, ist `2 critical · 3 high · 7 medium`), `SEC` (war `14 critical · 8 high · 1 medium`, ist `8 critical · 12 high · 3 medium`), `OBS`, `HITL` und `CH`. Die Spaltensummen ergaben entsprechend nie die ausgewiesene Total-Zeile. Nur die Anzahl-Spalte war durchgehend korrekt.
- **Provenance-Tabelle** hatte keine Zeile für den Identitäts-Layer, obwohl der Fliesstext darüber bereits von «drei eigenen Layern» spricht. Ergänzt; der Test verlangt jetzt für jede Custom-Kategorie eine Zeile.

Dieselbe Auslassung betraf die reinen Zählungen: Badge, Header, Provenance-Fliesstext, Workflow-Schritt und Feature-Liste in `README.md` sowie die Stand-Zeile in `docs/roadmap.md` standen weiter auf 73 Checks in 9 Kategorien. Nachgezogen; die README-Zahlen hält ab jetzt `test_readme_counts.py`.

### Hinzugefügt — Neue Kategorie `IDENT` (Identität und Versionstreue), 5 Checks

Der Katalog wächst von 73 auf **78 Checks** in **zehn Kategorien**. `IDENT` schliesst eine Lücke, die dieselbe Form hat wie seinerzeit `FID`: Alle bisherigen Kategorien prüfen, ob ein Server korrekt gebaut ist und liefert, was die Quelle hat. Keine prüfte, **als welche Version er sich nach aussen ausgibt**. `ARCH-012` erwähnt `importlib.metadata`, betrifft aber die MCP-Protokollversion des SDK, nicht die Version des Servers selbst.

Anlass war ein Sweep über alle 30 Server des Portfolios am 2026-07-29. Ausgangspunkt: `swiss-environment-mcp` hatte von v0.2.0 bis v0.5.0 gegenüber jedem Upstream `swiss-environment-mcp/0.2.0` gemeldet — über drei Releases hinweg, ohne dass etwas brach.

| ID | Titel | Severity | Befund im Sweep |
|---|---|---|---|
| `IDENT-001` | User-Agent aus den Paket-Metadaten, nie als Literal | high | 12 / 30 Server, davon 4 mit falscher Major-Version |
| `IDENT-002` | `__version__` aus der installierten Distribution | medium | 20 / 30 Server |
| `IDENT-003` | Werte, die die Pipeline überschreibt, brauchen einen eigenen Check | medium | 4 / 30 Server |
| `IDENT-004` | Dokumentierte Versionen erzwingen | low | 17 / 30 Server, grösster Abstand 16 Minor-Versionen |
| `IDENT-005` | Fallback-Version darf nicht wie ein Release aussehen | medium | 1 / 30 Server |

Die Checks tragen zusätzlich die **Methodik-Lehren** aus dem Sweep, weil dort die eigentlichen Fehler passierten: eine zeilenweise Suche nach dem Schlüsselwort verfehlt mehrzeilige Konstanten (`swiss-electricity-mcp` sendete nach einem bereits gemergten Fix weiter `0.2.0`); ein Check, der beim ersten Befund abbricht, verdeckt den schwereren; die Fallback-Erkennung gehört an das lokale `+`-Segment statt an einen festen Marker-String.

### Geändert — Katalog-Grösse in Tests abgeleitet statt festgenagelt

Fünf Tests scheiterten am Katalogwachstum, weil sie die Anzahl Checks als Literal führten. Wo die Zahl reine Wartungslast war, wird sie jetzt abgeleitet:

- `test_count_matches_manifest` vergleicht gegen `manifest_count` — der Test prüft damit, was sein Name sagt.
- `test_manifest_consistent_with_catalog` vergleicht `manifest_count` gegen `catalog_count`.
- `test_severity_distribution_known_set` summiert gegen `len(catalog)`.

Bewusst fixiert bleiben `test_category_distribution` (spiegelt die Tabelle in `SKILL.md`, eine Änderung soll auffallen) und `test_srgssr_profile_count` (dokumentiert die Pinning-Absicht ausdrücklich). Deren Zahlen sind nachgezogen: 73 → 78.

Die Obergrenze der anwendbaren Checks im srgssr-Profil steigt von 40 auf 45. Alle fünf `IDENT`-Checks sind für dieses Profil anwendbar (36 → 41); das ist Katalogwachstum, nicht die Grammatik-Drift, gegen die die Schranke schützt.
### Behoben — Validation-Gate akzeptierte leere Finding-Dokumente

`aggregate_results.py validate` prüfte, ob pro erwarteter Check-ID eine Datei in `findings/` **existiert** — nicht, ob sie etwas enthält. Ein Verzeichnis voller Null-Byte-Dateien meldete `consistent: true`.

Aufgefallen ist das an einem realen Doppelfall: ein Carry-forward-Schritt schrieb über zwei Audit-Läufe hinweg **16 Findings als leere Platzhalter** (11 in `amtsblatt-mcp`, 5 in `swiss-procurement-mcp`). Die älteren Läufe benennen Findings `<ID>-<slug>.md`, das Skript suchte ein blankes `<ID>.md`, fand nichts und legte einen Stub an, den es nie füllte. Beide Läufe passierten das Gate, und beide `SECURITY.md` verwiesen auf diese Verzeichnisse als Beleg für die offene Findings-Menge.

Ein leeres Finding-Dokument ist schlimmer als ein fehlendes: ein fehlendes fällt durchs Gate, ein leeres kommt durch und sagt einem Leser nichts über eine Findung, die offen ist.

- `validate_findings_persistence()` zählt jetzt Nicht-Whitespace-Zeichen pro Check-ID und meldet zu dünne Dokumente in einem neuen Report-Feld `empty`; `consistent` wird dadurch `false` und der CLI-Exit 1.
- Neuer Parameter `--min-substance` (Default 1) — fängt per Default nur den eindeutigen Fall. Bewusst nicht höher vorbelegt: ein knappes Finding ist legitim, und ein Guard, der Fehlalarm schlägt, wird umgangen.
- Existieren mehrere Dateien zu einer ID (`<ID>.md` neben `<ID>-<slug>.md`), zählt die grösste. Sonst würde ausgerechnet das Layout durchfallen, das der Carry-forward-Bug erzeugt hat, während er behoben wird.
- Vier Tests, drei davon mutationsgeprüft: die Substanz-Prüfung zu entfernen lässt sie fallen, der Negativkontroll-Test (echtes Dokument neben verirrtem Stub) bleibt korrekt grün.

Rückwärtskompatibel: die Signatur bekommt nur einen Parameter mit Default, alle 18 bestehenden Audit-Läufe in den beiden Portfolio-Repos validieren unverändert.

### Hinzugefügt — Neue Kategorie `FID` (Datentreue), 5 Checks

Der Katalog wächst von 68 auf **73 Checks** in **neun Kategorien**. Die neue Kategorie `FID` (Data Fidelity) schliesst eine Lücke, die ein realer Portfolio-Vorfall sichtbar gemacht hat: Alle bisherigen acht Kategorien prüfen, ob ein Server **korrekt gebaut** ist. Keine prüfte, ob er **liefert, was die Quelle hat**.

Anlass war [`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). Der Server sendete `ClassificationIds` nur bei explizitem Aufruf; die TERMDAT-API schränkt eine ID-lose Suche auf `VARIA` ein — eine von 23 Klassifikationen. Jede Default-Suche lief damit gegen ein Dreiundzwanzigstel des Bestands und meldete das Ergebnis als gewöhnliche Leermenge. Der Server hatte das Audit mit 68 Checks bestanden. Gefunden hat den Fehler ein User mit dem offiziellen Web-UI daneben.

| ID | Titel | Severity |
|---|---|---|
| `FID-001` | Scope-Defaults: Filter-Parameter explizit senden, nie erben | critical |
| `FID-002` | Recall-Ground-Truth: Referenzqueries gegen die offizielle Oberfläche | high |
| `FID-003` | Leermenge von Abwesenheit unterscheidbar — keine Konfabulations-Einladung | high |
| `FID-004` | Parameter-Gruppen vollständig senden — Teilmengen erben Server-Defaults | medium |
| `FID-005` | Query-Syntax in der Tool-Description, nicht im README | medium |

Zwei Eigenheiten der Kategorie, die bei der Katalogpflege relevant sind:

- **`FID-001` und `FID-002` sind nicht per `code_review` verifizierbar.** Man sieht dem Code nicht an, dass ein *fehlender* Parameter Schaden anrichtet — der Beleg liegt in der Parameterbeschreibung der Spec und im Live-Vergleich gegen Ground Truth. Beide Checks führen `runtime_test` als Pflichtmodus. Das ist der erste Katalog-Teil, bei dem statische Analyse strukturell nicht ausreicht.
- **`FID-003` behandelt die Tool-Description als Halluzinations-Oberfläche.** Im gemeldeten Transkript hat das Modell die Leermenge mit dem hauseigenen Caveat «an empty result usually means the term is out of scope» kombiniert und eine erfundene Antwort produziert. Eine Formulierung, die eine Leermenge erklärt, erzeugt Konfabulation zuverlässiger als gar keine Formulierung.

Alle fünf Checks gelten bei `tools_make_external_requests == true`, also für jeden Server, der eine Upstream-Datenquelle abfragt — im Portfolio praktisch alle.

- **Katalog-Metadaten:** `checks/MANIFEST.txt` auf 73 IDs, Kategorien-Tabellen in `SKILL.md` (2.1) und `README.md` um `FID` ergänzt, Severity-Verteilung neu **16 critical · 33 high · 24 medium**
- **Tests:** hartcodierte Katalog-Zählungen in `tests/test_parse_catalog.py` und `tests/test_applicability.py` auf 73 gehoben, `FID: 5` in die Kategorien-Verteilung aufgenommen (297 Tests grün)

### Hinzugefügt — Release-Automatisierung für auditierte Server (Schritt 7)

Nach den Audit-/Remediation-Schleifen schlägt der Skill jetzt automatisch einen versionierten Release des **auditierten MCP-Servers** vor (nicht des Skill-Repos), inklusive CHANGELOG-Eintrag und GitHub-Release-Draft.

- **`tools/propose_release.py`** — `propose`-Modus generiert Vorschlag (semver-Bump, CHANGELOG-Entry, Tag- und Release-Befehle) und modifiziert nichts; `apply`-Modus schreibt CHANGELOG, committet, erzeugt annotated git tag und optional einen `gh release --draft`. Pusht **nie** automatisch — Maintainer-Verantwortung.
- **Production-Ready-Gate** — `propose`/`apply` weigern sich, wenn `summary.production_ready == false`. `--force` existiert für dokumentierte Hotfix-Eskalationen.
- **Versions-Detection** — liest `pyproject.toml`/`package.json`/letztes git-Tag (in dieser Reihenfolge); ändert Version-Strings in den Manifesten **nicht** (Bump-Konvention liegt beim Projekt).
- **CHANGELOG-Integration** — `## [Unreleased]`-Block bleibt erhalten; neue Einträge werden direkt darunter eingefügt. Audit-Metadaten (run-id, skill_version, catalog_hash, by_status) werden im Eintrag persistiert für Audit-Trail.
- **SKILL.md Schritt 7** + **Slash-Command Schritt 7** dokumentieren den verbindlichen Vorschlag-Bestätigung-Apply-Workflow. Slash-Command darf Apply **nur nach explizitem OK** des Users ausführen.
- **23 neue pytest cases** (`tests/test_propose_release.py`).

### Hinzugefügt — Pluggable Tracker-Backends (Notion + CSV)

Der bisherige `audit-notion-sync.py` band den Skill an Notion. Neue Abstraktion erlaubt anderen Datenbanken-Backends, damit alle Auditoren den Skill nutzen können — nicht nur die mit Notion-Workspace.

- **`tools/tracker_sync.py`** — pluggable Backend-Layer mit gemeinsamer `TrackerBackend.get/update/list_all`-Schnittstelle. Aktuelle Adapter: `csv` (zero-deps, Default) und `notion` (wraps die existierende API). Backend-Wahl via `--backend` oder `MCP_AUDIT_TRACKER_BACKEND`-Env.
- **CSV-Backend** — schreibt `tracker.csv` mit kanonischen Spalten (`server_name`, `audit_status`, `findings`, `last_audit_run`, `last_audit_at`, `production_ready`, `released_version`, `notes`). Datei wird beim ersten Schreibzugriff samt Header erzeugt; Updates merge-tolerant.
- **Notion-Backend** — selbe Field-Semantik, mappt auf existierende Tracker-Properties plus optional `Released Version`/`Production Ready`/`Last Audit Run/At`. Felder, die in Notion fehlen, werden ignoriert ohne Drama.
- **`--from-summary`** — zieht `findings`, `production_ready`, `last_audit_run`, `last_audit_at` direkt aus `summary.json` (Single-Source-of-Truth, kein Re-Counting). Ersetzt die manuelle `jq`-Pipeline aus dem alten Workflow.
- **SKILL.md Schritt 5.2 + 7.3** dokumentieren beide Backends; Anleitung zum Hinzufügen weiterer Adapter (Airtable, Google Sheets) enthalten.
- **19 neue pytest cases** (`tests/test_tracker_sync.py`).

Test-Total: 255 → 297.

---

## [v1.0.0] — 2026-05-02 — Production-Ready Reproducibility

Erstes stabiles Release nach dem Reproduzierbarkeits-Hardening, das aus dem ersten realen Audit-Lauf (`srgssr-mcp`, 2026-04-30, PowerShell auf Windows) hervorging. Alle 11 Issues aus dem Retrospektiv (#6–#16) sind geschlossen, inklusive vollständiger Behebung des damals entdeckten Catalog-Bugs (Listen-vs-String-Vergleich in 9 Checks).

### Highlights

- **10 dedizierte Helper-Scripts unter `tools/`** ersetzen Inline-Heredocs, die auf Windows Git Bash unzuverlässig waren.
- **Kanonischer DSL-Evaluator** für `applies_when` mit handgeschriebenem recursive-descent Parser — kein `eval()`, deterministisch reproduzierbar, strict-typed.
- **Single-Source-of-Truth-Aggregator** für Status-Counts und Findings-Persistenz, mit Validation-Gate vor Audit-Abschluss.
- **Cross-Platform-Härtung** — UTF-8-Stdio-Force, POSIX↔Windows-Pfad-Konvertierung, CRLF-tolerante Frontmatter, `.gitattributes` mit `eol=lf`.
- **CI-Pipeline** auf GitHub Actions: pytest auf Ubuntu + Windows × Python 3.11 + 3.13.
- **255 pytest cases** über 11 Test-Files, inkl. Regression-Tests die den exakten srgssr-Bug reproduzieren.
- **Deterministische Run-IDs** im Format `YYYY-MM-DDTHHMMSS-<offset>-<server>` mit Catalog-Hash als Reproduzierbarkeits-Anker in `audit-meta.json`.

### Hinzugefügt — Profile-Validation-Gate + ISO-Run-ID (Issues #14 und #15)

Zwei P2-Quality-of-Life-Verbesserungen aus dem ersten realen Audit-Lauf, kombiniert in einem PR.

**Issue #14 — Profile-Placeholder-Detection:** Im ersten Audit hat der User versehentlich das Template mit `...`-Werten reingepastet. Claude hat das durch Defensive-Behavior abgefangen, aber das war Eigeninitiative, nicht Skill-Spec. Jetzt verbindlich:

- **`tools/validate_profile.py`** prüft Profile gegen `...`, `<placeholder>`, `<TODO>`, `TODO`/`FIXME`/`XXX`, leere Strings, `null`, leere Listen — plus Pflicht-Felder + Type-Mismatches (bool wo String, list wo String, etc.). 17 Placeholder-Patterns erfasst.
- **SKILL.md Step 1.3** dokumentiert das Gate als verbindlich vor Step 2.
- **Slash-Command** ruft den Validator vor dem Catalog-Load auf.

**Issue #15 — ISO-Run-ID mit Timezone:** Im ersten Audit hat `date +%Y-%m-%d` `2026-04-30` zurückgegeben, obwohl der lokale Kalendertag `2026-05-01` war (UTC-Container-Drift). Output-Verzeichnis hatte falsches Datum, Re-Audits am gleichen Tag würden kollidieren.

- **`tools/audit_init.py`** generiert deterministische Run-IDs im Format `YYYY-MM-DDTHHMMSS-<offset>-<server>` (z.B. `2026-05-02T091245-Z-srgssr-mcp` oder `...+0200-...` für CEST). Bei Sekunden-genauer Kollision: automatisches `-2`/`-3`-Suffix auf das Verzeichnis (Run-ID bleibt logisch identisch).
- **`audit-meta.json`** wird beim Audit-Start initialisiert mit `started_at` (ISO mit TZ), `timezone_offset`, `skill_version`, `catalog_hash` (SHA-256 aller `*.md` + `MANIFEST.txt` — Reproduzierbarkeits-Anker). `agent_runs[]` (Issue #12) hängt sich daran an.
- **SKILL.md Step 0.4** dokumentiert das verbindliche Init-Helper.
- **Slash-Command Step 0** ruft `audit_init.py` auf, ersetzt `date +%Y-%m-%d`-Pattern.

60 neue pytest cases (`tests/test_audit_init.py`: 24, `tests/test_validate_profile.py`: 36). Test-Total: 195 → 255.

### Geändert — `is_cloud_deployed`-Flag ersetzt 9 broken `deployment`-Checks (Issue #16)

Der canonical evaluator (Issue #6) hatte 9 Checks identifiziert, die das Listen-Feld `deployment` mit einem String-Literal verglichen — `deployment != "local-stdio"`. Im alten ad-hoc-Evaluator (Python `eval`) lieferte das immer `True` (`["x"] != "x"` ist in Python immer wahr), wodurch die Checks fälschlich für jeden Server als anwendbar galten. Jetzt strukturell behoben.

**Entscheidung (Option C aus Issue #16):** Neues Profil-Feld `is_cloud_deployed: bool`, abgeleitet aus dem `deployment`-Listen-Feld (`true` iff mindestens ein Eintrag ungleich `local-stdio`). Vorteile: explizite Intention, kein DSL-Change, gleichlautend zu `write_capable`/`uses_sampling`.

- **9 Check-Files migriert:** `OBS-005`, `OBS-006`, `SCALE-003`, `SCALE-004`, `SCALE-006`, `SEC-014`, `SEC-015`, `SEC-021`, `SEC-022` — `applies_when` von `deployment != "local-stdio"` auf `is_cloud_deployed == true` umgestellt
- **`audit-notion-sync.py build_profile`** leitet `is_cloud_deployed` automatisch aus `deployment` ab — Notion-Tracker bleibt unverändert (single source of truth: `Deployment`-Multi-Select)
- **`portfolio.example.yaml` + `SKILL.md`** dokumentieren das neue Feld
- **`docs/applies-when-dsl.md`** Anti-Pattern-Sektion aktualisiert: list-vs-string-Anti-Pattern explizit auf `is_cloud_deployed`-Lösung verwiesen
- **Tests:** `KNOWN_BUGGY_DEPLOYMENT_COMPARISON`-Set entfernt (nun leer); neue `TestIsCloudDeployedFlag`-Klasse mit 5 Cases für die Flag-Semantik; `test_no_check_compares_deployment_list_to_string_literal` als Regression-Sweep über alle 68 Checks; neuer `tests/test_notion_sync.py` (7 Cases) verifiziert die Notion-Sync-Derivation
- Test-Total: 181 → 195

### Geändert — Schema-Migration `write_access` → `write_capable` (Issue #13)

Der Skill hatte zwei parallele Profil-Felder für dieselbe Frage "schreibt der Server?": `write_access: "write-capable"` (Enum-String) und `write_capable: bool`. Damit hing die Applicability eines Checks davon ab, welche Variante das Profil zufällig setzte. Issue #6 (canonical evaluator) hat das offengelegt; jetzt aufgeräumt.

**Entscheidung:** `write_capable: bool` ist das kanonische Feld (kürzer, eindeutig boolesch, konsistent mit `uses_sampling: bool`, `tools_make_external_requests: bool`). `write_access` ist deprecated und wird vom Evaluator als `UnknownFieldError` geflaggt — keine stille Backwards-Compatibility, weil das exakt die "loud failure"-Philosophie aus Issue #6 verletzt hätte.

- **`checks/HITL-005.md`** migriert: `write_access == "write-capable"` → `write_capable == true`
- **`SKILL.md`** Profil-Beispiel und Schema-Hinweis aktualisiert; klargestellt, dass das Notion-Tracker-Select `Schreibzugriff` durch `audit-notion-sync.py` automatisch zu `write_capable: bool` gemappt wird (Notion-UX bleibt unverändert)
- **`tests/test_applicability.py`** — neue Klasse `TestWriteCapableSchemaMigration` mit 5 Cases: kein Check nutzt `write_access` mehr, HITL-005 nutzt das neue Feld, korrekte Applicability bei `write_capable=true/false`, Legacy-Profile werden laut abgelehnt
- Test-Total: 176 → 181

### Hinzugefügt — Task-Agent-Validation-Gate (Issue #12)

Im ersten realen Audit hat ein Task-Agent mit `Done (68 tool uses · 0 tokens · 2m 20s)` zurückgegeben — vollständiger stiller Fehlschlag. Der Skill hat das nicht erkannt, Claude hat manuell weitergemacht und das Problem ad hoc kompensiert. Bei einem unbeaufsichtigten Audit wäre das stiller Datenverlust gewesen.

- **`tools/verify_raw_outputs.py`** — verifiziert, dass alle erwarteten Check-IDs eine nicht-leere Output-Datei in `raw/` haben. Catches die Empty-Placeholder-Files via `--min-bytes`-Threshold. Exit 0/1/2.
- **`tools/agent_run_log.py`** — appendet pro Task-Agent-Aufruf einen Eintrag in `audit-meta.json` mit Tool-Uses, Tokens, Duration, Expected/Satisfied/Incomplete-IDs und einer 3-State-Klassifikation (`ok`/`empty`/`incomplete`). `summary`-Subcommand gibt Coverage-Aggregate.
- **Drei-State-Klassifikation** — `empty` (Tokens=0, hard fail), `incomplete` (Tokens > 0 aber IDs fehlen), `ok`. Empty hat Vorrang, weil 0 Tokens immer auf einen Agent-Fehlschlag hindeutet.
- **Retry-Policy in SKILL.md Step 4.5** — bei `incomplete`/`empty` max. 2 Retries nur für die fehlenden IDs (`--retry-of <run_index>`-Kette in audit-meta.json). Danach harter Abbruch.
- **37 neue pytest cases** — `tests/test_verify_raw_outputs.py` (14) + `tests/test_agent_run_log.py` (23). Test-Total: 139 → 176.
- **SKILL.md Step 0.3 erweitert** — Tabelle der Helper-Scripts um Verifier + Logger ergänzt.
- **Slash-Command Step 4 erweitert** — Pflicht-Gate dokumentiert.

### Hinzugefügt — Catalog-Parser und Report-Builder (Issue #11)

Inline-Heredocs sind jetzt vollständig durch dedizierte Helper-Scripts ersetzt. Im ersten realen Audit wurden Inline-Python-Blöcke ad hoc generiert, was auf Windows Git Bash mehrfach an Quoting gecrasht ist.

- **`tools/parse_catalog.py`** — parst alle Check-Frontmatter, validiert MANIFEST.txt-Konsistenz, listet Kategorien/Severities. CLI: `--format {json,table,manifest-check}`. Pflicht-Felder werden hart enforced (jede Inkonsistenz crasht laut, statt stille Defaults).
- **`tools/build_report.py`** — generiert `audit-report.md` aus `summary.json` + `findings/` + Profile. Sieben Pflicht-Sektionen, deterministisch reproduzierbar. Findings werden nach Severity sortiert; fehlende Finding-Docs werden im Report explizit als Validation-Lücke markiert.
- **Standalone-Bootstrap fix** — `aggregate_results.py` und `parse_catalog.py` setzen jetzt `sys.path` für Direktaufruf via `python tools/<x>.py`. Vorher funktionierten sie nur via pytest.
- **SKILL.md Step 0.3** — Inline-Heredocs sind jetzt explizit verboten; Tabelle aller Helper-Scripts mit Aufgabe/Aufruf.
- **Slash-Command `audit-mcp.md`** — Step 2 und Step 6 rufen Helper-Scripts statt Inline-Loops auf. `python`/`python3` zu allowed-tools hinzugefügt.
- **36 neue pytest cases** — `tests/test_parse_catalog.py` (16) + `tests/test_build_report.py` (20). Test-Total: 103 → 139.

### Hinzugefügt — Findings-Persistenz-Aggregator (Issues #8 und #9)

Im ersten Audit (`srgssr-mcp`, 2026-04-30) berichteten drei Stages drei verschiedene Zahlen für dieselben Daten — Step 5 sagte 15 Findings, Step 6 sagte 6, auf Disk waren 6. Strukturelle Lösung:

- **`tools/aggregate_results.py`** — Single-Source-of-Truth-Aggregator. Liest `verification-results.json`, produziert `summary.json` mit canonical Counts, validiert `findings/` gegen `expected_ids`. CLI: `aggregate`, `expected-findings`, `validate`.
- **Findings-Persistenz-Policies** — explizite Wahl zwischen `fail-or-partial` (Default), `fail-only`, `needs-attention`. Policy wird in `summary.json` persistiert.
- **Schema-Validierung** — `CheckResult` rejectet ungültige Status- und Severity-Werte beim Laden.
- **Validation-Gate** — `validate <audit_dir>` exitet mit Code 1 wenn `findings/*.md` nicht zu `expected_ids` passt. Pflicht-Schritt vor Audit-Abschluss.
- **`docs/verification-results-schema.md`** — formale Spec der Datenkontrakte zwischen Step 4/5/6.
- **`tests/test_aggregate_results.py`** (32 Cases) — inkl. Regression-Test, der den exakten srgssr-Bug reproduziert (nur 6 von 15 Findings persistiert) und vom Validator gefangen wird.
- **SKILL.md Step 5/6-Update** — verbindliche Spec, dass alle Counts aus `summary.json` zu lesen sind, nie neu zu berechnen.

### Hinzugefügt — Reproduzierbarkeits-Hardening (Issues #6, #7, #10)

Initiale Hardening-Welle nach dem srgssr-Audit-Lauf auf Windows/Git Bash:

- **Kanonischer `applies_when`-Evaluator** (`tools/eval_applicability.py`): hand-rolled recursive-descent parser, kein `eval()`. Strict-typed Vergleiche (string-vs-string, bool-vs-bool, list-vs-list-membership). Unbekannte Felder, Type-Mismatches und Parse-Errors werden laut, nicht stille `False`. Unterstützt CLI: `expr`, `catalog`. Funktioniert mit Bare-Profile, Wrapped-Profile, oder Portfolio-File.
- **DSL-Spezifikation** (`docs/applies-when-dsl.md`): formale Grammar, Operator-Präzedenz, Type-Rules, bekannte Anti-Patterns.
- **Pytest-Suite** (`tests/test_applicability.py`, 45 Cases): deckt alle DSL-Konstrukte, Error-Paths, und Real-World-Catalog-Regressionen ab.
- **Cross-Platform-Pfad-Helpers** (`tools/path_utils.py`, `tools/paths.sh`): konvertieren zwischen POSIX-Drive-Form (`/c/Users/foo`) und Windows-Form (`C:\Users\foo`). Lösen das Read-Tool-Path-Problem auf Windows.
- **UTF-8-Stdio-Force** (`force_utf8_stdio()` + `ensure_python_utf8`): vermeidet `cp1252`-Crashes bei Emojis/Umlauten.
- **CI-Workflow** (`.github/workflows/test.yml`): pytest auf Ubuntu + Windows, Python 3.11 + 3.13.
- **`.gitattributes`** mit `eol=lf` für `*.sh`/`*.py`/`*.yml`/`*.yaml`/`*.md`/`*.txt` — verhindert CRLF-Probleme auf Windows-Checkouts mit `autocrlf=true`.
- **CRLF-tolerante Frontmatter-Regex** als Defence-in-Depth, falls `.gitattributes` mal nicht greift.
- **SKILL.md-Update**: neuer Schritt 0 mit Cross-Platform-Voraussetzungen; Schritt 3 verweist auf canonical evaluator.

### Roadmap nach v1.0.0

Nicht-blockierende Features für künftige Releases:

- `reference/anti-patterns.md` mit wiederverwendbaren Code-Snippets aus wiederkehrenden Findings
- CI-Lint im Skill-Repo, der das Frontmatter aller Check-Files validiert (über `parse_catalog.py manifest-check` hinaus)
- Audit-Findings-Sub-DB unter dem Notion-Audit-Tracker
- Parallelism in `audit-portfolio.sh` via `xargs -P`
- Profile-Override-Layer (lokale Datei merged mit Tracker-Werten beim `pull`)
- `write_access` vs. `write_capable`-Schema-Migration (Issue #13)

---

## [v0.7.0] — 2026-04-30

### Hinzugefügt — Notion-Audit-Tracker-Integration (Muster 3, bidirektional)

Neuer Stdlib-Python-Client `audit-notion-sync.py` als Brücke zwischen Notion-Tracker (`a2736a65-677d-4cf3-9f94-e874f74a1975`) und dem v0.6.0-Portfolio-Workflow. Drei Subcommands:

- **`health`** — verifiziert `NOTION_TOKEN` + DB-Zugriff, listet Bot-Name, DB-Titel, Property-Count, warnt wenn die `Org-Kontext`-Spalte fehlt.
- **`pull`** — liest Tracker-Entries (default-Filter: `Audit-Status` ∈ {`Triagiert`, `In Audit`}; `--all` für alle) und schreibt eine vollständige `portfolio.yaml`. Refused-by-default Overwrite ohne `--force`. Behandelt Notion-Pagination automatisch.
- **`push`** — aktualisiert eine Tracker-Karte: setzt `Findings` (number), `Audit-Status` (select), appendet `Notizen` mit Report-Pfad/URL. `--dry-run` zeigt das Payload ohne PATCH-Call.

`audit-portfolio.sh` bekommt zwei neue Flags:
- `--from-notion` — `pull` läuft vorab und ersetzt `portfolio.yaml`.
- `--sync-back` — nach jedem erfolgreichen Audit-Run wird automatisch `push <server> --findings N --status "Findings dokumentiert" --report <path>` aufgerufen.

**Architektur-Entscheidungen:**
- **Stdlib-only** (`urllib.request`, `json`, `argparse`) — keine `pip install`-Dependencies. Funktioniert auf jedem Python-3.9+-System.
- **Token via `NOTION_TOKEN` env var, niemals committed** — `.env*` und `portfolio.yaml` sind gitignored.
- **DB-ID konfigurierbar via `NOTION_AUDIT_DB_ID`** mit Default auf den Schulamt-Tracker; die alte falsche ID `308e0a91…` aus `SKILL.md` wurde gefixt auf die korrekte `a2736a65…`.
- **Org-Kontext als `multi_select`-Spalte im Tracker:** Optionen `Stadt Zürich`, `Schulamt`, `Volksschule`, `Enterprise`. Der Pull-Script mappt diese 1:1 auf die context-Flags der `applies_when`-Expressions. Falls die Spalte fehlt, warnt `health` und context-Flags defaulten auf `false` (CH-Compliance-Checks greifen dann nicht).
- **Konservative Defaults für nicht-modellierte Tech-Flags** (`uses_sampling=false`, `uses_sequential_thinking=false`, `tools_include_filesystem=false`, `tools_make_external_requests=true`) — pro Server manuell in `portfolio.yaml` overridebar.
- **Custom YAML-Emitter** statt PyYAML-Dependency: dumpt den begrenzten Strukturraum (servers/profile/list/dict-of-scalars) deterministisch und yq-kompatibel.
- **Pull verhindert versehentliches Überschreiben** — `--force` notwendig, sobald `portfolio.yaml` existiert. Verhindert Daten-Verlust bei manuellen Profil-Edits.
- **Push referenziert Pages via Server-Name** statt Page-ID; Page-ID-Override via `--page-id` möglich. Bei mehrdeutigem Server-Name wird abgebrochen.
- **Formula-Felder** (`Risiko-Score`, `Reife-Score`, `Prio`) werden gelesen aber niemals geschrieben — sind in Notion read-only.

**Neue Files:**
- `audit-notion-sync.py` — Notion-Bridge (executable)

**Geänderte Files:**
- `audit-portfolio.sh` — `--from-notion`, `--sync-back` Flags + Helper-Funktion `require_notion_sync`
- `SKILL.md` — DB-ID-Fix `308e0a91…` → `a2736a65…`
- `README.md` — Notion-Sync-Abschnitt
- `CHANGELOG.md` — v0.7.0-Eintrag

**Setup:**
```bash
# 1. Notion: Audit-Tracker → ••• → Connections → Add → "Claude Code"
# 2. Multi-select-Property "Org-Kontext" anlegen mit Optionen:
#    Stadt Zürich, Schulamt, Volksschule, Enterprise
# 3. Lokal:
export NOTION_TOKEN="ntn_..."     # in shell-rc, nicht committen
python3 audit-notion-sync.py health
python3 audit-notion-sync.py pull
./audit-portfolio.sh              # liest portfolio.yaml; oder
./audit-portfolio.sh --from-notion --sync-back   # bidirektionaler Lauf
```

**Bekannte Einschränkungen:**
- Pull überschreibt manuelle `portfolio.yaml`-Edits (bis Override-Layer in v0.7.1 oder später kommt).
- `Audit-Status` ist `select` (nicht `status`-Type) — das match unsere Konvention, aber falls du den Tracker auf `status` umstellst, muss der Push-Code auf das `status`-API-Format angepasst werden.
- Sequenziell auch im Notion-Sync — paralleles Push würde Notion-Rate-Limits riskieren.

---

## [v0.6.0] — 2026-04-30

### Hinzugefügt — Portfolio-Batch-Audit (Muster 1: headless via `claude -p`)

Neues Top-Level-Script `audit-portfolio.sh` für sequenziellen Headless-Audit über mehrere MCP-Server hinweg. Pro Server: clone/pull → `claude -p` mit autoritativem Profil → Audit-Report einsammeln → in `portfolio-summary.md` aggregieren.

**Architektur-Entscheidungen:**
- **Sequenziell statt parallel** (vermeidet API-Rate-Limits beim ersten Run; Parallelism via `xargs -P` lässt sich später trivial nachrüsten)
- **Profil autoritativ aus `portfolio.yaml`** — der Headless-Marker im Prompt («Profil ist autoritativ») weist `/audit-mcp` an, Schritt 1 (Profil-Bestätigung) zu überspringen. Kleine Ergänzung in `.claude/commands/audit-mcp.md` dokumentiert diesen Modus.
- **`portfolio.yaml` ist `.gitignore`d**, nur `portfolio.example.yaml` als Template wird committet — verhindert versehentliches Pushen von Server-Listen / Deployment-Details.
- **yq-Variant-Detection:** Script erkennt zur Laufzeit ob Mike Farahs Go-yq oder kislyuks Python-yq installiert ist; passt YAML-Output-Flag entsprechend an. Bei Python-yq wird zusätzlich `jq` geprüft (Python-yq ist ein jq-Wrapper).
- **Skip-Logik standardmässig an:** wenn `<repo>/audits/<heute>-*` existiert, wird übersprungen. `--force` überschreibt.
- **Subset-Filtering** via positionalen Args: `./audit-portfolio.sh zh-education-mcp foo-mcp`.
- **Remote-URL-Validierung:** wenn ein lokaler Klon existiert, wird die `origin`-URL gegen `portfolio.yaml` geprüft — bei Abweichung Re-Clone, damit das Script keinen falschen Server unter altem Namen auditiert.
- **Aggregation in `portfolio-summary.md`:** Tabelle mit Server | Status | Findings-Counts (critical/high/medium/low) | Production-Ready | Report-Pfad. Severity-Extraktion liest das Tabellen-Format aus `templates/finding.md` (`| **Severity** | critical |`).

**Neue Files:**
- `audit-portfolio.sh` — Orchestrator (executable)
- `portfolio.example.yaml` — Template mit zwei Beispiel-Servern und allen Profil-Feldern

**Geänderte Files:**
- `.claude/commands/audit-mcp.md` — Headless-Modus-Hinweis in Schritt 1
- `.gitignore` — `portfolio.yaml` und `portfolio-logs/`
- `README.md` — Portfolio-Audit-Abschnitt
- `checks/MANIFEST.txt` — mitgewachsen auf 68 IDs (inkl. v0.5.0-Anhang-Coverage)

**Setup:**
```bash
cp portfolio.example.yaml portfolio.yaml
$EDITOR portfolio.yaml         # Server-Liste anpassen
./audit-portfolio.sh --dry-run # Plan verifizieren
./audit-portfolio.sh           # echter Run
```

**Bekannte Einschränkungen:**
- `claude -p` mit Slash-Commands inline ist abhängig von Claude-Code-Version; falls die Slash-Command-Erkennung im Headless-Mode nicht greift, kann der Prompt alternativ den `audit-mcp.md`-Inhalt direkt einbetten (Folge-Iteration).
- Sequenziell: bei 30 Servern × ~10 min/Audit = ~5 h Wallclock. Parallelism ist v0.6.1-Material.
- Profil-Inferenz (Schritt 1, Weg C) wird im Headless-Modus nicht genutzt — alle Profile müssen in `portfolio.yaml` explizit gesetzt sein.

---

## [v0.5.0] — 2026-04-26

### Hinzugefügt — Anhang-Coverage (Architektur-Disziplin + Security-Verstärkung + Operative Disziplin)

Lücken-Analyse gegen `mcp-server-architecture-best-practice.pdf` zeigte, dass v0.4.0 etwa 65–70% des Anhang-Inhalts vollständig deckte. v0.5.0 schliesst die identifizierten Lücken mit 14 neuen Checks in drei Clustern.

**Cluster 1 — Architektur-Disziplin (5 Checks):**
- `ARCH-008` — Drei MCP-Primitive nutzen (Tools, Resources, Prompts)
- `ARCH-009` — Tool Annotations explizit (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`)
- `ARCH-010` — **Idempotency-Keys + Compensating Actions** (CRITICAL bei Write-Servern, schliesst die SOLID-Idempotency-Lücke)
- `ARCH-011` — Standardisierte Repo-Struktur (Sormena-Pattern)
- `ARCH-012` — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

**Cluster 2 — Security-Verstärkung (5 Checks):**
- `SEC-019` — **Lethal Trifecta vermeiden** (CRITICAL, Server-Separation Read vs Write/Send)
- `SEC-020` — **Command Injection Prevention** (CRITICAL, 43%-Lücke gemäss Equixly 2025)
- `SEC-021` — Egress-Allow-List auf Code- und Network-Layer
- `SEC-022` — Tool-Hash-Pinning + Namespace-Präfix gegen Rug Pull
- `SEC-023` — DLP-Scanning auf Tool-Outputs (ergänzt HITL-003 für Non-Sampling-Pfad)

**Cluster 3 — Operative Disziplin (4 Checks, neue Kategorie OPS):**
- `OBS-006` — OpenTelemetry Distributed Tracing pro Tool-Call
- `OPS-001` — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert
- `OPS-002` — Doku-Standard: bilingualer README, ASCII-Diagramm, Limits-Sektion
- `OPS-003` — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

### Status

Check-Katalog: **68 Checks**, alle 8 Kategorien.

- `ARCH`: 12 / 12 ✅
- `SDK`: 5 / 5 ✅
- `SEC`: 23 / 23 ✅
- `SCALE`: 6 / 6 ✅
- `OBS`: 6 / 6 ✅
- `HITL`: 5 / 5 ✅
- `CH`: 8 / 8 ✅
- `OPS`: 3 / 3 ✅ (neue Kategorie)

**Severity-Verteilung:**
- critical: 15 (22%)
- high: 31 (46%)
- medium: 22 (32%)

### Gap-Coverage gegen Anhang

Vollständige Abdeckung der drei Anhang-Sektionen:
- A (Architektur): A1, A2, A3, A4, A5, A6, A7, A8, A9 — alle abgedeckt
- B (Sicherheit): B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12 — alle abgedeckt
- C (Operative Praxis): C1, C2, C3, C4 — alle abgedeckt

Plus die SOLID-Eselsbrücke ist nun komplett: **S**andbox (SEC-007), **O**Auth (SEC-001/2/3), **L**east Privilege (SEC-003), **I**dempotency (ARCH-010), **D**efense-in-Depth (über alle Layer).

---

## [v0.4.0] — 2026-04-26

### Hinzugefügt — Claude-Code-Slash-Command-Integration

Der Audit-Workflow ist nun als Claude-Code-Slash-Command `/audit-mcp <repo>` ausführbar. Standard-Automatisierungstiefe: alle `automated`/`config_check`/`documentation_check`-Modi laufen automatisch, `code_review`/`runtime_test`-Modi werden als TODOs mit Such-Pattern in den Report geschrieben.

> **Erratum (nachträglich, 2026-04-29):** Im ursprünglichen v0.4.0-Eintrag wurde die Anzahl Checks fälschlich mit 53 angegeben — tatsächlicher Stand zum Release-Zeitpunkt war 54. Die Diskrepanz entstand durch einen Off-by-one-Zählfehler beim Übergang von v0.3.0 zu v0.4.0. v0.5.0 baut korrekt auf 54 + 14 = 68 Checks auf.

**Neue Files:**
- `.claude/commands/audit-mcp.md` — Slash-Command-Definition (orchestriert die 6 Schritte aus `SKILL.md`)
- `setup-slash-command.sh` — installiert den Symlink nach `~/.claude/commands/audit-mcp.md` für globale Verfügbarkeit

**Architektur-Entscheidungen:**
- File wohnt im Skill-Repo (versioniert mit Skill-Updates), wird via Symlink user-global verfügbar gemacht
- `allowed-tools` strikt limitiert auf `Bash(grep|find|curl|git|ls|cat|...)`, `Read`, `Write`, `Glob` — keine Tool-Surface jenseits der Audit-Operationen
- Profil-Load mit drei Fallback-Wegen: User-Conversation → Notion-Card-Copy-Paste → Repo-Inferenz (mit konservativen Defaults)
- Bei mehr als zwei geratenen Profil-Werten bricht der Command ab und fragt — falsches Profil = falscher Audit
- Nutzt ausschliesslich Bash-Snippets aus den Check-Files, kein erfundenes Pattern-Match
- Output-Verzeichnis pro Audit: `<repo>/audits/YYYY-MM-DD-<server-name>/` mit `audit-report.md`, `findings/`, `raw/`
- Bei wiederholtem Audit am gleichen Tag: `-vN`-Suffix statt Überschreiben

**Setup:**
```bash
git clone https://github.com/malkreide/mcp-audit-skill.git
cd mcp-audit-skill
./setup-slash-command.sh
```

Danach in jeder Claude-Code-Session: `/audit-mcp <repo-url-or-path>`.

---

## [v0.3.0] — 2026-04-26

### Hinzugefügt — SEC Edge-Cases (Final)

Elf SEC-Checks komplettieren die Security-Kategorie. Geordnet nach Portfolio-Relevanz für das Schulamt-Portfolio (Universal → Lokal → File → DNS → OAuth → Multi-Server).

**Cluster 1 — Universal (alle Server):**
- `SEC-018` — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)
- `SEC-013` — API-Key-Storage: Secret Manager statt Plain-Text Env-Vars

**Cluster 2 — Lokale stdio-Server:**
- `SEC-006` — stdio-Transport zwingend für lokale Server (Netzwerk-Isolation)
- `SEC-007` — Container-Sandboxing mit minimalen Privilegien
- `SEC-008` — Pre-Configuration Consent für Local-Server-Installation

**Cluster 3 — File-Tools:**
- `SEC-017` — Path-Traversal-Prevention (Allow-List + safe_resolve)

**Cluster 4 — DNS:**
- `SEC-005` — DNS-Rebinding-Prevention via DNS-Pinning (TOCTOU-Schutz)

**Cluster 5 — OAuth-Proxy:**
- `SEC-003` — Progressive Scope-Minimierung mit WWW-Authenticate-Challenges
- `SEC-011` — Cookie-Security: __Host-Prefix, Secure, HttpOnly, SameSite
- `SEC-012` — Clickjacking-Protection: X-Frame-Options + CSP frame-ancestors

**Cluster 6 — Multi-Server-Cluster:**
- `SEC-014` — Tool-Allow-Listing via MCP-Gateway-Pattern
- `SEC-015` — Pre-Flight Tool-Poisoning Detection

### Status

Check-Katalog: **53 von ~50 Checks** vollständig (Plan war ~50, finale Zählung +3 durch granularere Aufteilung mancher PDF-Themen). Alle sieben Kategorien komplett.

- `ARCH`: 7 / 7 ✅
- `SDK`: 5 / 5 ✅
- `SEC`: **18 / 18 ✅**
- `SCALE`: 6 / 6 ✅
- `OBS`: 5 / 5 ✅
- `HITL`: 5 / 5 ✅
- `CH`: 8 / 8 ✅

### v0.3 markiert das vollständige Skill

Der Check-Katalog ist nun produktiv einsatzbereit für alle Server-Profile im Schulamt-Portfolio. Künftige Erweiterungen kommen aus zwei Quellen:
1. Real-World-Findings beim Audit der 29 Server, die neue Pattern aufzeigen
2. PDF-Updates mit neuen Best Practices (z.B. neue Specs der MCP-Steering-Group)

---

## [v0.2.4] — 2026-04-26

### Hinzugefügt — HITL & Schweiz-Compliance Wave (Final)

Vier HITL-Checks und sieben CH-Checks. Komplettiert die Kategorien `HITL` und `CH`. Damit ist der Check-Katalog operativ einsatzbereit für das Schulamt-Portfolio.

**Human-in-the-Loop (4):**
- `HITL-001` — Sampling Request Review: User-UI vor LLM-Send
- `HITL-002` — Sampling Response Review: Output-Validation vor Server-Übergabe
- `HITL-003` — **Data Redaction**: PII-Filter vor LLM-Send (CRITICAL bei nicht-public + Sampling)
- `HITL-004` — Sequential Thinking Object-Sanitization gegen Key-Leaks

**Schweiz-Compliance (7):**
- `CH-002` — **DSG-konforme Personendaten-Verarbeitung** mit Rechtsgrundlage (CRITICAL bei PII)
- `CH-003` — Lehrpersonen-Einwilligung bei Volksschule-Daten (Auskunfts-/Berichtigungsrecht)
- `CH-004` — OGD-CH Lizenz-Compliance: CC BY 4.0 Attribution
- `CH-005` — ISDS Stadt Zürich Schutzbedarfsklasse-Mapping (3 Schutzziele)
- `CH-006` — Schulamt Klassifikationsschema (BUI/VERT/SVERT, Aggregations-Risiko)
- `CH-007` — Datenresidenz Backup-Region (Backups als gleichwertige Verarbeitung)
- `CH-008` — **EDÖB-Meldepflicht** bei Datenschutz-Verletzungen (CRITICAL, 72h-Frist)

### Status

Check-Katalog: **42 von ~50 Checks** vollständig. Alle sieben Kategorien mit operativ einsetzbarem Check-Set abgedeckt.

- `ARCH`: 7 / ~7 ✅ vollständig
- `SDK`: 5 / ~5 ✅ vollständig
- `SEC`: 6 / ~18 (kritische Subset komplett, Rest in Roadmap für v0.3)
- `SCALE`: 6 / ~6 ✅ vollständig
- `OBS`: 5 / ~5 ✅ vollständig
- `HITL`: 5 / ~5 ✅ vollständig
- `CH`: 8 / ~8 ✅ vollständig

### Verbleibend für v0.3

Nicht-kritische SEC-Checks (~11): SEC-003 (Scope-Minimierung), SEC-005 (DNS-Pinning), SEC-006/007/008 (Local-Server / Container-Sandbox / Pre-Config-Consent), SEC-011/012 (Cookie-Security / Clickjacking), SEC-013 (API-Key-Storage), SEC-014/015 (Tool-Allow-Listing / Tool-Poisoning), SEC-017 (Path-Traversal), SEC-018 (Input-Validation).

Diese Checks decken Edge-Cases ab, die im Schulamt-Portfolio aktuell noch nicht produktionsrelevant sind. Werden ergänzt, sobald Server in Production gehen, die OAuth-Proxy nutzen oder File-Tools exponieren.

---

## [v0.2.3] — 2026-04-26

### Hinzugefügt — Skalierung & Observability Wave

Fünf SCALE-Checks und vier OBS-Checks. Komplettiert die Kategorien `SCALE` und `OBS` aus dem PDF.

**Skalierung (5):**
- `SCALE-001` — Streamable HTTP statt stdio für Cloud-Deployments
- `SCALE-003` — Mcp-Session-Id Routing via Edge-LB (HAProxy Stick-Tables / NGINX Hash)
- `SCALE-004` — Containerization mit Multi-Stage-Builds (Image-Grösse + Non-Root-User)
- `SCALE-005` — MCP-Gateway für Enterprise (Anti-Shadow-MCP)
- `SCALE-006` — Resource-Limits per Container (Memory, CPU, FDs)

**Observability (4):**
- `OBS-002` — Mask Error Details (keine Stacktraces / SQL ans LLM)
- `OBS-003` — Structured Logging mit RFC 5424 Severity-Stufen
- `OBS-004` — **stderr für stdio-Server** (CRITICAL — stdout reserviert für Protocol)
- `OBS-005` — SIEM-Integration für Audit-Logs (Datadog EU / Splunk)

### Status

Check-Katalog: 31 von ~50 Checks vollständig. Verbleibend: ~10 Checks in v0.2.4 (HITL + CH).
- `ARCH`: 7 / ~7 ✅ vollständig
- `SDK`: 5 / ~5 ✅ vollständig
- `SEC`: 7 / ~18 (kritische Subset komplett)
- `SCALE`: 6 / ~6 ✅ vollständig
- `OBS`: 5 / ~5 ✅ vollständig
- `HITL`: 1 / ~4
- `CH`: 1 / ~7

---

## [v0.2.2] — 2026-04-26

### Hinzugefügt — Architektur & SDK Wave

Fünf Architektur-Checks und vier SDK-Checks. Komplettiert die Kategorien `ARCH` und `SDK` aus dem PDF.

**Architektur (5):**
- `ARCH-002` — Tool-Beschreibung mit Use-Case-Tags (`<use_case>`, `<important_notes>`)
- `ARCH-003` — «Not Found» Anti-Pattern: Fuzzy-Match + Suggestions statt leerer Antworten
- `ARCH-004` — Inversion of Control: Transport-agnostische Server-Logik (stdio + SSE identisch)
- `ARCH-006` — Tool-Budget: High-Level-Use-Cases statt API-Mapping 1:1
- `ARCH-007` — Capability-Aggregation: Composability intern, Atomarität extern

**SDK (4):**
- `SDK-001` — FastMCP Lifespan via `@asynccontextmanager` + AsyncExitStack
- `SDK-002` — Pydantic v2 / TypedDict / Dataclass als Tool-Returns
- `SDK-003` — Context Injection für Progress-Reports und Logging
- `SDK-004` — CORS `Mcp-Session-Id` Exposure bei HTTP/SSE-Deployments

### Status

Check-Katalog: 22 von ~50 Checks vollständig. Verbleibend: ~28 Checks in v0.2.3 + v0.2.4.
- `ARCH`: 7 / ~7 ✅ vollständig
- `SDK`: 5 / ~5 ✅ vollständig
- `SEC`: 7 / ~18 (kritische Subset komplett)
- `SCALE`: 1 / ~6
- `OBS`: 1 / ~5
- `HITL`: 1 / ~4
- `CH`: 1 / ~7

---

## [v0.2.1] — 2026-04-26

### Hinzugefügt — Critical Security Wave

Sechs kritische Security-Checks aus dem PDF-Anhang. Alle haben Severity `critical` und müssen vor Production-Release bestanden sein.

- `SEC-002` — Token Passthrough Prohibition (RFC 8707 Audience Validation)
- `SEC-004` — SSRF-Prevention: HTTPS-Enforcement + IP-Blocklisting (mit DNS-Rebinding-Schutz)
- `SEC-009` — Session-ID Cryptographic Binding an validierte user_id
- `SEC-010` — OAuth State Parameter: Single-Use, max 10min TTL (Redis GETDEL)
- `SEC-016` — 0.0.0.0-Binding-Prevention (NeighborJack-Schutz)
- `ARCH-005` — Keine Hardcoded Secrets (Pydantic SecretStr + Gitleaks/Trufflehog CI)

### Status

Check-Katalog: 13 von ~50 Checks vollständig (v0.1.0: 7 Sample + v0.2.1: 6 Critical). Verbleibend: ~37 Checks in v0.2.2 bis v0.2.4.

---

## [v0.1.0] — 2026-04-26

### Hinzugefügt — Initial Release

**Skill-Methodik:**
- `SKILL.md` mit 6-Schritte-Audit-Verfahren
- Profil-getriebene Applicability-Logik
- Severity-Disziplin: critical / high / medium / low
- Sieben Check-Kategorien: ARCH, SDK, SEC, SCALE, OBS, HITL, CH

**Templates:**
- `templates/finding.md` — Finding-Dokumentation
- `templates/audit-report.md` — Server-Gesamtreport

**Reference:**
- `reference/best-practices-summary.md` — komprimiertes PDF

**Sample-Checks (7 von ~50 geplant):**
- `ARCH-001` — Tool Naming Convention (medium, universal)
- `SDK-005` — TypeScript Strict Mode + Zod (high, TypeScript-only)
- `SEC-001` — Confused Deputy: Per-Client Consent Flow (critical, OAuth-Proxy)
- `SCALE-002` — Stateful Load Balancing für Streamable HTTP/SSE (high, HTTP/SSE)
- `OBS-001` — Protocol vs. Execution Errors (high, universal)
- `HITL-005` — Destructive Operation Confirmation (critical, write-capable)
- `CH-001` — DSG/EDÖB Datenresidenz Schweiz/EU (high, non-public-data)

### Bekannt unvollständig

Der Check-Katalog enthält in v0.1 nur 7 Sample-Checks zur Format-Validierung. Die verbleibenden ~43 Checks sind in `docs/roadmap.md` dokumentiert und werden in v0.2 ergänzt:

- ARCH: 6 weitere Checks (Inversion of Control, Tool-Beschreibungen, Tool-Budget, etc.)
- SDK: 4 weitere Checks (Lifespan-Management, Pydantic-Returns, Context-Injection, CORS)
- SEC: 17 weitere Checks (Token Passthrough, SSRF, Session-Hijacking, etc.)
- SCALE: 5 weitere Checks (Streamable HTTP, Container, MCP-Gateway, etc.)
- OBS: 4 weitere Checks (Mask-Error-Details, Structured Logging, SIEM, etc.)
- HITL: 4 weitere Checks (Sampling-Review, Data-Redaction, Sequential Thinking, etc.)
- CH: 7 weitere Checks (Personendaten-Verarbeitung, OGD-Lizenz, ISDS, etc.)

---

## Versions-Historie

Das Repository wurde mit **v0.5.0** publiziert. Frühere Versionen (v0.1.0 bis
v0.4.0) sind in diesem CHANGELOG dokumentiert, existieren aber nicht als
separate Git-Tags — sie repräsentieren Iterationsstände während der
initialen Skill-Entwicklung vor dem GitHub-Push.

[Unreleased]: https://github.com/malkreide/mcp-audit-skill/compare/v0.5.0...HEAD
[v0.5.0]: https://github.com/malkreide/mcp-audit-skill/releases/tag/v0.5.0
