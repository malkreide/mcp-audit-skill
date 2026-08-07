# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Behoben — die Zuordnung von `seco-labor-mcp` konnte den Server nicht beschreiben

`seco-labor-mcp` hält `compute_delay` und `parse_retry_after` in
`retry_policy.py` und ruft sie aus **zwei** Retry-Schleifen auf, in `server.py`
und `uvg.py`. Keine der Dateien hält allein alle acht Eigenschaften: Die
Schleifen tragen Fehlerbehandlung, Netzfehler und Wanduhr-Budget, das
Policy-Modul trägt Jitter, Deckel und `Retry-After`.

Das Manifest konnte nur wählen, **welche Hälfte es unterberichtet** — und es
unterberichtete die mit drei Eigenschaften darin. Sechs Befunde gegen einen
Server, der jede einzelne hält.

Beide Adoptionen deklarieren jetzt `also = ["src/seco_labor_mcp/retry_policy.py"]`.
Das Feld ist neu in `reference_drift_probe.py` (mcp-continuous-auditor#83) und
nennt weitere Dateien desselben Repos, deren Funktionen das Einstiegssymbol
**aufrufen** darf. Es erweitert den Scope nicht auf diese Dateien; gefolgt wird
nur, was der Einstieg wirklich erreicht. Check 17 liest Adoptionen gar nicht —
es prüft Vorlagen, und eine Vorlage ist eine Datei —, das Feld ist dort also
bedeutungslos und wird ignoriert.

Gemessen: `seco-labor-mcp` verschwindet vollständig aus dem Bericht.

### Geändert — der Vorbehalt zu Finding 4 ist zurückgezogen, nicht abgemildert

Finding 4 trug den Satz, ein `REFERENCE_STALE` auf `reads_retry_after`,
`jitters` oder `caps_after_jitter` sei ein Sonden-Artefakt und dürfe nicht gegen
einen Server gebucht werden. Mit mcp-continuous-auditor#81 scopen beide Leser
gleich; solche Befunde sind wieder echt.

Der Vorbehalt ist **gelöscht** statt umformuliert. Ein Vorbehalt, der seine
Ursache überlebt, ist derselbe Defekt wie ein Verzeichnis, das seine Lesung
überlebt — und dieses Manifest hat heute schon einen davon korrigiert.

### Geändert — das Adoptionsregister nennt elf Server als defekt, die es nicht mehr sind

`reference/adoption.toml` führte elf Repositories unter «Still carrying the
2026-08-03 defect». Eine erneute Lesung am 2026-08-07 (abends) sagt: **alle elf
sind repariert.** Jedes liest heute `Retry-After`, streut seinen Backoff,
deckelt nach dem Jitter und hängt sein Budget an eine Wanduhr-Deadline.

Sie stehen jetzt in einer eigenen Gruppe — «repariert *nach* der Vorlage» —
und nicht bei den sechs, die die Eigenschaften *vor* ihr erreicht hatten. Die
beiden sagen Verschiedenes: Jene sind der Grund, warum die Reparatur eine Form
zum Abschreiben hatte; diese haben sie danach übernommen. Eine gemeinsame Liste
verlöre die Richtung, in die ein Fix gewandert ist, und das ist der einzige
Beleg, den dieses Manifest darüber führt.

Der Satz, der sie als ausstehend führte, ist **entfernt** und nicht abgemildert.
Ein Register, das ein veraltetes Verzeichnis behält, hat denselben Defekt wie
eine Vorlage, die einen veralteten Fix behält — eine Ebene weiter aussen.

### Hinzugefügt — fünf neue Adoptionen aus dem `ARCH-014`-Portfolio-Durchlauf

Ein Durchlauf des Audit-Katalogs über alle 43 Portfolio-Server fand sechs
Verstösse gegen `ARCH-014`. Fünf davon hatten ihren Retry selbst gebaut und
übernehmen jetzt die Eigenschaften dieser Vorlage: `zurich-opendata-mcp`,
`bag-health-mcp`, `openlex-mcp`, `swiss-statistics-mcp`, `amtsblatt-mcp`.

Der sechste, `swiss-environment-mcp`, steht **nicht** in der Liste, und die
Begründung steht daneben: Sein Retry liegt in einer vendored copy, die
byte-identisch mit `fedlex-mcp` gehalten wird. Ihn hier zu führen stellte eine
Datei unter zwei Zuordnungsregime — hier nach Eigenschaft gemessen, dort nach
Bytes — und eine Änderung hier erschiene dort als Drift.

Damit: 24 Adoptionen statt 19.

### Behoben — zwei Befunde über die Eigenschaften selbst (4 und 5)

**Finding 4: Die beiden Leser dieses Manifests scopen es verschieden.** Die
Datei sagt in ihrem Kopf, sie werde von zwei Seiten gelesen. Sie sagte nicht,
dass die beiden Seiten Verschiedenes unter `symbol` verstehen:

| Leser | Scope |
|---|---|
| `tools/checks/adoption.py::_scope` (Check 17) | das Symbol **plus die Modulfunktionen, die es aufruft** |
| `reference_drift_probe.py::load_symbol` | das Symbol, sonst nichts |

Das fällt erst auf, seit die Reparatur vom 2026-08-07 Helfer ausgelagert hat:
`retry-after` liegt in `parse_retry_after`, `random.random()` in
`compute_delay`, und `fetch_with_retry` ruft beide nur auf. Check 17 sieht sie,
die Portfolio-Sonde nicht — und meldet `reads_retry_after`, `jitters` und
`caps_after_jitter` als «implemented nowhere», über eine Vorlage, die alle drei
implementiert, und 23 Stellen, die es auch tun.

Ein Befund, der alles anklagt, klagt nichts an; diese Form ist das Erkennungs-
zeichen. Von Hand gegen alle elf reparierten Server geprüft: Check 17 hat recht.
Die Behebung gehört auf die Sonde und nicht in diese Datei — eine Eigenschaft
abzuschwächen, um einen Lauf grün zu bekommen, wäre genau der Zug, den die Notiz
im Kopf verbietet.

**Finding 5: `no_bare_runtime_error` feuert auf `lobbywatch-mcp` aus dem
falschen Grund.** Der `RuntimeError` nach erschöpften Versuchen, um den es
ging, ist weg. Übrig sind in `_download_dump` zwei Zusicherungen über die
**Form** einer angekommenen Antwort. Die Eigenschaft kann beides nicht
unterscheiden.

### Changed

- **`wall_clock_budget` konnte keine Schranke von einer Stoppuhr unterscheiden —
  die Zusage ist jetzt in zwei geteilt.** Die Eigenschaft war als `kind =
  "calls"` über `time.monotonic` / `time.perf_counter` deklariert und versprach
  im `says`, sie belege «bounds the total time spent». Ein Uhrenzugriff sieht
  aber gleich aus, ob er etwas begrenzt oder bloss misst.

  Gemessen: `i14y-mcp` rief `time.perf_counter()` zweimal auf, um `elapsed_ms`
  für eine **Log-Zeile** zu berechnen. Begrenzt wurde nichts. Damit zählte es
  als der eine Server von elf mit Wanduhr-Budget — die ehrliche Zahl jener
  Erhebung war 6 von 18, nicht 7.

  `wall_clock_budget` sagt jetzt nur noch, dass eine monotone Uhr gelesen wird.
  Die neue Eigenschaft **`wall_clock_deadline`** trägt die Hälfte, die
  tatsächlich bindet: ein Aufruf von `asyncio.timeout` oder `asyncio.wait_for`.
  Die beiden zusammen sind ein Budget, keine von beiden allein — Uhr lesen ist
  Arithmetik, Deadline durchsetzen ist Kontrollfluss.

  **Nicht der httpx-Timeout**, und das ist der Grund für die eigene Eigenschaft:
  httpx begrenzt pro *Operation*, und sein Read-Timeout beginnt mit jedem Chunk
  von vorn. Eine langsam tröpfelnde Antwort überdauert jede Einzelschranke, ohne
  dass ein einzelner Read abläuft — genau der Fall, für den ein Gesamtbudget
  existiert.

  **Beide Schreibweisen zählen**, weil beide richtig sind: `asyncio.timeout`
  braucht Python 3.11, und drei der übernehmenden Repositories halten
  `requires-python = ">=3.10"`, wo `asyncio.wait_for` dieselbe Wanduhr-Schranke
  unter dem älteren Namen ist. `wait_for` abzulehnen hiesse, diese drei dafür zu
  bestrafen, dass sie einen Interpreter unterstützen, den sie bewusst
  unterstützen.

  Gegengeprüft: **18 von 18** Übernahmen halten die neue Eigenschaft, und Check
  17 hält die Vorlage gegen jetzt acht statt sieben Eigenschaften.

### Added

- **Die Checkliste endete am Quellbaum — ausgeliefert wird das Artefakt.** Eine
  Kampagne über das Portfolio fand **fünf tote Installationen und zwei
  Versions-Drifts**, alle an Servern mit sauberem Probe-Lauf. Der Skill führte
  bis zum Scaffold und zur «Qualitätschecklist vor Release» und danach nicht
  weiter; zwischen geprüftem Quellbaum und installiertem Paket liegen aber ein
  Build, eine Auflösung von Abhängigkeiten und eine Veröffentlichung, und alle
  drei fallen aus, ohne dass im Repo etwas rot wird. Vier Ergänzungen, jede
  gegen einen gemessenen Ausfall:

  - **4.2 `_version.py`** — der Scaffold liest die Version des installierten
    Pakets über `importlib.metadata.version()`, mit Fallback `0.0.0+source`.
    Nie ein handgeschriebenes `VERSION = "0.4.0"`: Welche Version ausgeliefert
    wird, entscheidet der Build, und eine Zuweisung im Quelltext ist eine
    zweite Kopie derselben Zahl. `swiss-procurement-mcp` verschickte `0.4.0`
    im User-Agent aus einem Paket, das `0.18.3` war — vierzehn Minor-Versionen,
    und beide Zahlen sahen für sich plausibel aus. Der Fallback ist ein
    PEP-440-Local-Segment und damit eine Zeichenkette, die nie auf PyPI stehen
    kann: Wer sie in einem Log sieht, weiss ohne Nachfrage, dass dort ein
    Quellbaum läuft. **Eigenes Modul, nicht `__init__.py`** — sonst entsteht
    der Zirkelimport, den `bag-health-mcp` trägt.
  - **4.3 Obergrenzen im generierten `pyproject.toml`**, und `PUBLISHING.md`
    sagt, wie sie gemessen wurden: gegen das, was am genannten Tag
    nachweislich installiert **und importiert** wurde. `swiss-energy-mcp`
    0.3.3 wurde durch das Erscheinen von `mcp` 2.0.0 uninstallierbar, ohne
    dass sich am Artefakt eine Datei änderte. Der Einwand gegen Obergrenzen
    (Auflösungs-Sackgassen) ist der Grund für die Messung, nicht gegen die
    Grenze: Anheben ist damit eine Messung und keine Debatte.
  - **Schritt 5 «Startzeile und `start_event`»**, neu zwischen dem Repo-Bau
    (Schritt 4) und dem Portfolio-Register (jetzt Schritt 6). Der Scaffold gibt
    vor dem Transport-Aufruf genau eine stabile Zeile auf stderr aus — stderr,
    weil bei stdio stdout dem JSON-RPC-Rahmen gehört, und mit `flush=True`,
    weil stderr ohne TTY blockgepuffert ist, also genau unter dem Supervisor,
    dessen Log die Zeile belegen soll. Der Marker steht als `start_event` in
    `portfolio.json`. **Marker-Regeln:** bei strukturierten Logs wird das
    `event`/`msg`-Feld EXAKT verglichen (ein Präfix greift nicht — `server.start`
    träfe sonst `server.start_failed` mit), bei Klartext genügt eine
    Teilzeichenkette, und nie ein Zeitstempel oder ein anderer Pro-Lauf-Wert.
  - **Abschnitt «Nach dem Release»** mit drei Prüfungen: Paket in ein leeres
    Venv installieren und das Konsolen-Skript sechs Sekunden mit geschlossenem
    stdin beobachten (sechs, weil das die ersten zwei Sprossen der Retry-Leiter
    aus 3.1 sind, 2 s + 4 s); die Version des installierten Artefakts gegen
    `main` halten; und: **ein Tag veröffentlicht nichts.** `publish.yml` löst
    auf `release: types: [published]` aus, weder ein Tag noch ein Draft feuert
    das. Der Tag allein lässt das Repo aussehen, als sei ausgeliefert worden —
    genau so entstanden die fünf toten Installationen.

- **Die Gegenprobe, und was sie über den eigenen Text hinaus gezeigt hat.** Der
  Scaffold wurde einmal erzeugt, in ein leeres Venv installiert und gestartet;
  die vier Punkte stehen hier, weil dieser Durchlauf sie belegt. Drei Befunde
  sind erst dabei entstanden und stehen deshalb im Text:

  1. **Die Obergrenze auf `mcp` arbeitet heute, nicht irgendwann.** Am 7.8.2026
     löst dieselbe Zeile ohne `<2.0.0` auf `mcp` 2.0.0 auf, und dort existiert
     `mcp.server.fastmcp` nicht mehr: Die Installation gelingt, der Start
     scheitert am Import. Der Ausfall aus `swiss-energy-mcp`, an einem frischen
     Scaffold reproduziert — und der Grund, warum die Tabelle in `PUBLISHING.md`
     eine Spalte «Import geprüft» hat und nicht bloss eine aufgelöste Version.
  2. **Die Startzeile steht nicht allein auf der Leitung.** Der Lauf bekam eine
     `IncompleteFieldDefinitionWarning` aus `pydantic-settings` direkt über die
     Startzeile geschrieben, ohne dass der Scaffold etwas dazu beigetragen
     hätte. Das ist die Begründung für die Teilzeichenketten-Regel bei
     Klartext: Ein Vergleich auf die ganze Zeile bräche an fremdem Rauschen.
  3. **`pip install {dist}` ohne Pin macht die erste Prüfung wertlos.** Lief
     das Release nicht durch, installiert sie die **vorige** Version, die
     startet, ihre Startzeile schreibt und mit 0 endet — eine grüne Prüfung
     über ein Artefakt, das gar nicht Gegenstand der Prüfung war. Deshalb
     `pip install "{dist}=={version}"`: Dann scheitert die Installation, laut
     und an der richtigen Stelle.

- **Vier Anti-Patterns (16–19)** und das **Fundstück «fünf tote Installationen
  (2026-08)»**. Der Kern des Fundstücks ist die Fehlerform, nicht die Zahl: Ein
  Tag ohne veröffentlichtes Release erzeugt keinen roten Lauf, sondern gar
  keinen — die Actions-Seite zeigt danach die vorige Zeile. Fehlschläge, die als
  leere Menge auftreten, sind dieselbe Klasse wie die leere API-Antwort aus
  1.2c: Beide melden nichts und werden als «nichts los» gelesen.

### Changed

- **Der Portfolio-Register-Schritt ist jetzt Schritt 6**, weil die Startzeile
  als Schritt 5 dazwischen liegt. `start_event` ist ein Feld von
  `portfolio.json`, aber entschieden wird es am Code: Wer es erst beim
  Eintragen erfindet, schreibt hin, was dort stehen könnte, statt was der
  Prozess ausgibt. Alle Querverweise (5.1/5.2 → 6.1/6.2) und die beiden READMEs
  sind mitgezogen; die Zusage «drei Kernschritte» ändert sich nicht — der neue
  Schritt ist [Übergabe], und Check 11 hält das fest.

- **Die «elf» in `adoption.toml` stand auf der falschen Seite — gemessen, nicht
  geschätzt.** Die Notiz behauptete, die elf erhobenen Server hätten die
  Eigenschaften «einer nach dem anderen repariert, während diese Datei den
  Defekt weiter auslieferte». Am 7.8.2026 gegen die Server gelesen, ist das
  genau verkehrt herum: **Sechs** Repositories hatten die Eigenschaften vor der
  Vorlage, die anderen **elf** tragen den Defekt bis heute. Ein Grep über die
  ganzen Repositories — nicht nur über das deklarierte Symbol — findet in allen
  elf **null** Vorkommen von `retry-after` und **null** von `random`/`secrets`.
  Damit stimmt die Erhebung vom 3.8.2026 wörtlich: über elf Server las keiner
  `Retry-After` und keiner streute — weil sie alle diese Vorlage hatten.

  **Elf Repositories, zwölf Übernahmen:** `seco-labor-mcp` steht zweimal
  (`server.py` und `uvg.py`). Übernahmen gezählt sind es zwölf, Server gezählt
  elf; die Erhebung zählte Server. Das war die ganze Diskrepanz zwischen «elf»
  und «18 Übernahmen in 17 Repositories» — beide Zahlen stimmten, sie zählten
  Verschiedenes.

  `swiss-housing-mcp/src/swiss_housing_mcp/gwr.py:86` trägt die Zeile
  **wörtlich**: `raise RuntimeError(f"Upstream unreachable after retries:
  {last_error}")`. Genau die, deren leeres `str()` die Meldung erzeugt, die nach
  dem Doppelpunkt aufhört.

  Die 18 Einträge sind jetzt nach der Messung gruppiert — «hatte die
  Eigenschaften vor der Vorlage» und «trägt den Defekt noch». **Kein `since`
  wurde verschoben:** Ein `since` sagt, wann ein Repository das Verhalten
  übernommen hat, und daran ändert eine Lesung nichts. Was die Lesung hinzufügt,
  ist die Seite, auf der jeder Eintrag steht — gemessen statt angenommen.

- **Drei Befunde über die Eigenschaften selbst**, aus derselben Lesung. Eine
  Eigenschaft, die nicht messen kann, ist schlimmer als eine fehlende: Sie
  meldet mit Zuversicht.

  - **`caps_after_jitter` ist ein Falsch-Negativ auf jeder korrekten Übernahme,
    und die beiden Lesarten schliessen einander aus.** Alle sechs reparierten
    Server binden erst (`jittered = …`) und decken dann (`min(jittered, MAX)`) —
    ein `wraps`, das fragt, ob ein `random.*`-Aufruf *lexikalisch* in den
    Argumenten von `min` steht, findet in keinem von ihnen etwas. Lexikalisch
    gelesen fällt die Eigenschaft bei 6 von 6 Servern durch, die genau das
    Verhalten haben, das sie beschreibt. Die Vorlage schreibt `min` direkt um
    den Jitter-Ausdruck und besteht damit die lexikalische Lesart und fällt bei
    einer namensbindenden durch; die Server umgekehrt. **Kein einziger Ausdruck
    erfüllt beide**, denn die Wahl *ist*, ob ein Name gebunden wird. `wraps` muss
    also beide Formen akzeptieren, sonst misst es eine Schreibgewohnheit statt
    der Reihenfolge, für die es existiert.
  - **`wall_clock_budget` ist ein Falsch-Positiv auf `i14y-mcp`.** Dort ruft
    `client.py:147` und `:150` `time.perf_counter()` auf — um `elapsed_ms` für
    eine Log-Zeile zu berechnen. Begrenzt wird nichts. `kind = "calls"` kann
    «etwas messen» nicht von «etwas beschränken» unterscheiden. Ohne die zwei
    Zeilen zu lesen, zählt i14y als Server mit Budget; die ehrliche Zahl ist
    6 von 18, nicht 7.
  - **`no_bare_runtime_error` fällt bei `swiss-efv-mcp` durch** — dem
    Repository, gegen das die Reparatur dieser Vorlage geschrieben wurde.
    `client.py:315` und `:334` werfen beide `RuntimeError`. Die Referenz hat in
    den fünf Punkten recht, für die sie herangezogen wurde, und in diesem
    unrecht; die Vorlage kopiert sie hier **nicht**.

- **`reference/retry_backoff.py` hatte sechs Defekte, und alle sind mitkopiert
  worden.** Die Vorlage ist die Quelle, aus der die `*-mcp`-Server ihren Retry
  übernehmen; `reference/adoption.toml` nennt 18 Übernahmen in 17 Repositories.
  Die Erhebung vom 3.8.2026 las elf dieser Server: **keiner** las `Retry-After`
  und **keiner** streute seinen Backoff. Nicht elf unabhängige Auslassungen —
  eine Vorlage, elfmal kopiert. Was falsch war, im Einzelnen:

  1. **Kein Jitter.** `base_delay * 2 ** (attempt - 1)` ist rein
     deterministisch. Elf Server hinter derselben Quelle warten nach demselben
     Ausfall exakt 2s / 4s / 8s und kommen als Welle zurück, genau wenn die
     Quelle sich erholt — der Retry-Sturm verlängert den Ausfall, den er
     überbrücken sollte. Jetzt exponentiell in `[0.5x, 1.5x]`.
  2. **`Retry-After` wurde nie gelesen.** Ein 429 oder 503 ist die Quelle, die
     genau die Frage beantwortet, die die Backoff-Kurve rät. Jetzt werden beide
     Formen nach RFC 9110 §10.2.3 gelesen (Sekundenzahl und HTTP-Datum);
     unlesbar ergibt `None` und fällt auf die Kurve zurück, weil ein
     kaputter Header kein Absturz auf dem Fehlerpfad werden darf. Der Jitter
     darauf ist einseitig `[1.0x, 1.25x]`: Die Quelle hat gesagt wann — später
     ist höflich, früher missachtet die Angabe, die man gerade liest.
  3. **Kein Deckel auf die einzelne Wartezeit.** Die Leiter wuchs unbegrenzt.
     Jetzt `MAX_DELAY_SECONDS`, und zwar **nach** dem Jittern:
     `min(jittered, MAX)`. `min(MAX, base) * jitter` und `min(MAX, base *
     jitter)` enthalten beide einen Deckel und einen Jitter, nur der zweite
     ist beschränkt — ein auf 20 s gedeckelter Wert mal 1.5 sind 30 s. Diese
     Reihenfolge steckte in sechs Servern.
  4. **Ein Budget in Versuchen statt in Sekunden.** `max_attempts = 4`
     beschränkt die Zahl und sonst nichts: vier Versuche gegen eine Quelle mit
     30 s Timeout sind zwei Minuten in einem Tool-Call. Jetzt
     `TOTAL_BUDGET_SECONDS = 25.0` als Deckel über den ganzen Aufruf — der
     Anker ist gemessen, nicht geraten: das Python-MCP-SDK liefert
     `MCP_DEFAULT_TIMEOUT = 30.0`.
  5. **Das Budget hing an nichts.** Es hängt jetzt an einer
     Wanduhr-Deadline über `asyncio.timeout`, nicht am httpx-Timeout: httpx
     begrenzt pro Operation, und sein Read-Timeout beginnt mit jedem Chunk von
     vorn — eine langsam tröpfelnde Antwort überdauert das Budget, ohne dass
     ein einzelner Read abläuft.
  6. **Der teuerste Punkt: der Fehler wurde verpackt.**
     `raise RuntimeError(f"… after {max_attempts} attempts: {last_error}")`.
     `httpx.ConnectTimeout`, `ReadTimeout` und `ConnectError` tragen ein
     **leeres** `str()` — und das sind die einzigen Fehler, die ein echter
     Ausfall produziert. Die Meldung hörte nach dem Doppelpunkt auf; der
     CI-Fehler `RuntimeError: Upstream unreachable after retries:` aus dem
     Ursprungs-Commit von `swiss-efv-mcp` war der Auslöser der
     portfolioweiten Korrekturrunde. Jetzt `raise last_error`: Der Aufrufende
     bekommt den Typ und `.response` zurück, statt beides an eine leere
     Zeichenkette zu verlieren. Typ, Host und die Frage, welches der beiden
     Limits ausging, stehen im Log. Für den einen Fall ohne Ursprungsfehler —
     Budget weg, bevor ein Request rausging — gibt es `UpstreamUnavailableError`
     statt eines nackten `RuntimeError`, den niemand von einem Bug im Server
     selbst unterscheiden kann.

  Die Datei trägt jetzt eine **Kopfnotiz**: Sie wird kopiert, nicht importiert;
  eine Änderung an ihr ist eine Portfolio-Änderung und schuldet die Aussage,
  wer sie schon übernommen hat. `reference/adoption.toml` ist die Liste, und
  ihre Notiz zum Ist-Zustand ist mitgezogen — die fünf dort als «nicht erfüllt»
  deklarierten Eigenschaften sind erfüllt, ein `REFERENCE_STALE` darauf ist ab
  jetzt ein echter Befund und nicht mehr die bekannte Lücke.

  **`reference/response_envelope.py` mit denselben sechs Fragen gegengelesen:
  nichts Vergleichbares.** Die Datei enthält keinen Netzwerkpfad, keine
  Wartezeit und keinen `raise` — sie deklariert Pydantic-Modelle und
  Attributions-Konstanten. Die sechs Fragen greifen dort nicht. Der eine
  verwandte Punkt ist bereits gelöst: `fallback_stale` in `PROVENANCE_VALUES`
  ist genau die Zusage, die ein aufgebrauchtes Retry-Budget nach aussen sichtbar
  macht.

- **Die Zusage sind drei Kernschritte, nicht fünf Schritte.** Schritt 4
  (Übergabe an `github-repo`) und Schritt 5 (Portfolio-Register) sind
  Übergabe und zählen nicht mit. Das stand längst im Text — «durchläuft die
  drei Schritte unten», «nach Abschluss der Probe (Schritt 1-3)» —, nur
  nirgends so, dass eine Prüfung es hätte lesen können. Der vorangegangene
  Eintrag hatte deshalb die falsche Seite korrigiert und das Frontmatter auf
  `5-Schritte-Vorgehen` gezogen; es steht wieder auf `3`.

  Damit die Einordnung nicht wieder nur Prosa ist, trägt **jede**
  Schritt-Überschrift jetzt `[Kern]` oder `[Übergabe]`. Bewusst jede: Kern
  aus dem *Fehlen* einer Markierung abzuleiten hiesse, dass ein neu
  eingefügter Schritt ohne Marker still als Kern zählt und die Zusage
  aufbläst, ohne dass etwas rot wird.

  `ci.yml` prüft die GitHub-Description entsprechend gegen
  `<Zahlwort>-step core procedure`. **Die Description muss dafür neu gesetzt
  werden** — kein Commit erreicht sie.

- **Check 11 prüft jetzt die Klassifikation, nicht nur die Zahl.** Neu
  abgesichert: jeder Schritt trägt eine Markierung; die Kernschritte bilden
  einen zusammenhängenden Anfang (ein `[Kern]` hinter einem `[Übergabe]`
  wäre entweder falsche Reihenfolge oder falsche Einordnung); mindestens ein
  Kernschritt existiert; und das Zahlwort der Einleitung stimmt mit der
  Markierung überein — die eine Stelle, an der die Zusage als Prosa steht
  und genau deshalb unbemerkt veraltet.

### Added

- **Check 17: die Vorlagen müssen halten, was `adoption.toml` über sie
  behauptet.** Das Manifest deklariert je Vorlage eine Handvoll Eigenschaften.
  Gelesen wurden sie bisher ausschliesslich von
  `reference_drift_probe.py` in `mcp-continuous-auditor` — also in einem anderen
  Repository, und dort **gegen die Server**. Für die Vorlage selbst nahm die
  Liste niemand in die Hand.

  Das ist die Lücke, durch die der Defekt kam. `reference/retry_backoff.py`
  verletzte fünf der sieben Eigenschaften, die einen halben Meter weiter über
  sie deklariert waren, und wurde in dem Zustand in elf Server kopiert. Kein
  Schritt wurde rot, weil kein Schritt hinsah: Die Datei kompilierte (Check 2),
  importierte (Check 3) und bestand beide Ruff-Gates (13, 14). Alle vier haben
  recht — sie prüfen die **Form**, und die war in Ordnung. Die **Zusage**
  beanstandete niemand.

  **Gegenprobe, nicht Behauptung:** Gegen die Fassung von vor der Reparatur
  gefahren, meldet Check 17 genau die fünf Eigenschaften, die in elf Server
  kopiert wurden — `reads_retry_after`, `jitters`, `caps_after_jitter`,
  `wall_clock_budget`, `no_bare_runtime_error`.

  **Die Werte stehen nur im Manifest.** `any_of`, `outer`, `inner` und `expect`
  werden gelesen, nicht nachgebaut. Eine zweite Kopie der Liste in
  `tools/checks/` driftete von der ersten weg, und eine gedriftete Prüfung, die
  grün meldet, ist schlimmer als keine — dieselbe Begründung, aus der
  `scripts/validate.sh` die Gates nicht ein zweites Mal hinschreibt.

  **`wraps` akzeptiert beide Formen**, und das ist gemessen: Eine rein
  lexikalische Lesart fällt bei 6 von 6 Servern durch, die genau das Verhalten
  haben, das die Eigenschaft beschreibt (siehe den Befund oben). Die Prüfung
  nimmt `min(x * random.random(), MAX)` und `jittered = …` / `min(jittered,
  MAX)` gleichermassen an.

  Sieben der zehn Mutationen greifen nicht die Vorlage an, sondern **die
  Prüfung**: Manifest weg, kein `[[template]]`, Zuordnung ins Leere, Symbol
  unauffindbar, unbekannte `kind`, ungültiges `expect`, Vorlage ohne
  Eigenschaft, neue Vorlage ohne Zuordnung. Der Ursprungsdefekt kam nicht durch
  ein rotes Gate, das jemand ignoriert hat, sondern dadurch, dass keines hinsah
  — also ist «hört still auf zu prüfen» der Fall, der abgedeckt gehört.

  Dabei fiel ein Defekt in der Prüfung selbst auf: Eine Vorlage mit Syntaxfehler
  liess sie **abstürzen** statt einen Befund zu melden. «Die Prüfung ist
  abgestürzt» schickt den Lesenden nach `tools/checks/`, «die Vorlage parst
  nicht» nach `reference/` — das ist der Unterschied, für den es `CheckFailed`
  gibt. Behoben, mit eigener Mutation.

- **SKILL.md 1.2d «Feldnamen-Inventar».** Die Live-Probe protokolliert ab jetzt
  die tatsächlichen Feld- und Spaltennamen samt **Schreibweise** und legt die
  Rohantwort als **aufgezeichnete** Fixture ab. Anlass: Eine Quelle wechselte am
  3.8.2026 die Schreibweise ihrer CSV-Kopfzeile (`Schulgemeinde` →
  `schulgemeinde`) und legte vier von sechs Datensätzen eines Servers lahm —
  während **alle** Unit-Tests grün blieben, weil ihre von Hand geschriebenen
  Fixtures die alte Schreibweise pinnten. Ein getipptes Fixture ist eine
  Behauptung über die Quelle, kein Beleg: Es kann per Konstruktion nicht
  auffallen, wenn die Quelle sich bewegt. Neu auch in der Qualitätschecklist und
  als Irrtum 14.

- **Die Checks sind testbar geworden: `tools/checks/` statt Heredocs.** Jedes
  Gate ist jetzt eine gewöhnliche Funktion `(root: Path) -> str`, die bei
  einem Befund `CheckFailed` wirft, statt `sys.exit` aufzurufen. Beides ist
  Zweck, nicht Kosmetik: *root* statt `cwd` erlaubt, eine Prüfung gegen einen
  Baum zu fahren, in dem gezielt ein Anker fehlt; die Exception macht ihren
  Befundtext abfangbar. `sys.exit` hätte einen Test nur «nicht 0» prüfen
  lassen, nicht *warum* — und eine Prüfung, die aus dem falschen Grund rot
  wird, schickt den Lesenden zur falschen Datei.

  Vorher standen dieselben Prüfungen als Shell-Funktionen und Python-Heredocs
  in `scripts/validate.sh` und in `ci.yml`. Ein Heredoc lässt sich nur
  ausführen, indem man das ganze Repository in genau den Zustand bringt, den
  es beanstanden soll; entsprechend war von keiner einzigen Prüfung belegt,
  dass sie überhaupt beisst. Das ist derselbe Fehler, gegen den die
  Prüfungen gerichtet sind, eine Ebene höher — und Check 12 ist der Beleg,
  dass er hier vorkommt und nicht bloss denkbar ist.

  `scripts/validate.sh` bleibt der dokumentierte Einstieg und ruft
  `python -m tools.checks` auf. Die Ausgabe hat absichtlich dieselbe Form wie
  vorher.

- **`tests/` — pro Check mindestens ein Baum, auf dem er rot werden MUSS.**
  Rund fünfzig Mutationen, jede mit der Zusicherung, *welchen* Teil des
  Befundes die Prüfung dann nennt. Drei Wächter halten die Suite ehrlich:

  * `test_every_check_has_at_least_one_mutation` — eine Prüfung ohne Mutation
    lässt die Suite fehlschlagen. Ohne diesen Zwang wäre jede neue Prüfung
    genau das, wogegen dieses Repo angeschrieben ist: eine Behauptung, die
    nie widerlegt wurde.
  * `test_check_passes_on_the_real_repository` — jede Prüfung läuft
    zusätzlich gegen den echten Baum. Ohne diesen Meta-Test prüfte die Suite
    am Ende nur sich selbst: Ein handgeschriebenes Fixture enthält die Anker
    per Konstruktion.
  * Eine Mutation, deren Suchtext nicht mehr im Baum steht, schlägt **laut**
    fehl, statt still zu passieren. Eine veraltete Mutation wäre sonst ein
    Test, der nichts mehr testet.

  Der Fixture-Baum ist aus demselben Grund eine Kopie des echten
  Arbeitsbaums (`git ls-files`) und keine Attrappe; ein eigener Test belegt,
  dass die Kopie nichts verloren hat.

  Der schärfste Test der Sammlung ist
  `test_check_12_catches_what_13_and_14_cannot`: Auf einem Baum, in dem
  `reference/` aus `ruff.toml` genommen wurde, laufen beide Gates grün durch
  — sie haben nichts zu beanstanden, weil sie nichts mehr lesen. Genau das
  ist die Daseinsberechtigung von Check 12, und sie steht jetzt als Test da
  statt als Kommentar.

- **Check 13 und 14: `ruff check` und `ruff format --check` laufen im
  Runner.** Sie standen bisher als eigene Schritte in `ci.yml` und liefen
  damit *nicht* in `scripts/validate.sh` — der Datei, deren Kopfkommentar
  seit jeher argumentiert, zwei Kopien der Gates würden driften und ein
  gedrifteter Pre-Flight-Check melde grün auf einem Baum, den die CI
  ablehnt. Genau diese Eigenschaft hatte er selbst, für Lint und
  Formatierung. `ci.yml` installiert ruff und ruft den Runner auf; die
  doppelten Schritte sind weg.

  Die Reihenfolge ist Absicht: erst die Sonde (12), dann die Gates (13, 14).
  Ein grünes 13 heisst nur dann «der Baum ist sauber», wenn 12 vorher gezeigt
  hat, dass 13 überhaupt etwas liest.

- **Check 15 und 16 — die letzten zwei Heredocs aus `ci.yml`.** Check 15 ist
  die GitHub-Description gegen SKILL.md; sie ist als einzige Prüfung
  `offline=False` markiert, weil sie Netz und Token braucht, und bleibt
  deshalb aus `scripts/validate.sh` heraus — der Runner muss in einem Clone
  ohne Zugangsdaten vollständig durchlaufen. Ein Test hält zusätzlich den
  Description-Vorschlag, den ihr eigener Befund ausgibt, gegen das echte
  SKILL.md: Ein Hinweis, der eine Description empfiehlt, die derselbe Check
  anschliessend beanstandet, schickt den Lesenden im Kreis.

  Check 16 ist der Ruff-Pin-Abgleich zwischen `ci.yml` und
  `.pre-commit-config.yaml`. Er prüft neu auch, dass **beide** Hooks
  (`ruff-check`, `ruff-format`) noch geführt werden — fällt einer weg, läuft
  er lokal nicht mehr, der Commit geht grün durch und erst die CI wird rot.
  Das Schwester-Repo `mcp-data-fidelity-skill` hatte diesen Teil, dieses
  nicht.

- **Check 12: das Ruff-Gate greift nachweislich auf `reference/`.** `ruff
  check` und `ruff format --check` waren die einzigen Prüfungen dieses Repos
  ohne Anker-Wächter. Wird `reference/` in `ruff.toml` ausgeschlossen — per
  `exclude`, `[lint] exclude`, `[format] exclude`, `select = []` oder
  `per-file-ignores` —, melden beide Schritte eine Warnung auf stderr und
  **Exit 0**: «All checks passed!», ohne eine Zeile gelesen zu haben. Grün
  würde damit ausgerechnet der Code, den Leute kopieren.

  Der Fall ist nicht hypothetisch: für genau diese Dateien stand hier schon
  einmal `select = []` (siehe die Begründung und ihre Widerlegung in
  `ruff.toml`). Gemerkt hat es niemand, weil nichts rot wurde.

  Geprüft wird deshalb nicht die Konfiguration, sondern die Wirkung: eine
  absichtlich fehlerhafte Datei liegt kurz unter `reference/`, und beide Gates
  müssen sie beim Namen nennen. Ein Konfigurationsleser müsste jeden Schalter
  einzeln kennen und würde den verpassen, den ruff erst später bekommt. Die
  Sonde fährt dieselbe Invokation wie die CI (`.`, nicht `reference/` — ein
  explizit genannter Pfad umgeht `exclude` und würde die Lücke zudecken) und
  vergleicht gegen den Dateinamen statt gegen den Exit-Status, damit ein
  echter Fund anderswo im Baum nicht als bestandene Sonde durchgeht.

  Gegenprobe gefahren: `exclude = ["reference"]`, `select = []` und `[format]
  exclude` einzeln gesetzt. Alle drei lassen die CI-Schritte grün und werden
  von Check 12 rot gemeldet, jeweils mit Angabe, welches der beiden Gates
  ausgefallen ist.

- **Die GitHub-Description trägt eine prüfbare Zusage.** Sie nennt jetzt die
  Schrittzahl («a five-step procedure»), und die CI prüft sie bei jedem Lauf
  gegen `SKILL.md`. Die Description liegt ausserhalb des Repos und fiel damit
  durch jede Prüfung, die Dateien liest — dieselbe Lücke, die im Schwester-Repo
  `mcp-transport-hardening-skill` dazu geführt hat, dass dort zwei Wochen lang
  «twelve» stand, als es schon dreizehn Regeln waren. Der Schritt steht in
  `ci.yml` statt in `scripts/validate.sh`, weil er Netz und Token braucht und
  die Suite offline lauffähig bleiben soll. Ein fehlgeschlagener API-Aufruf ist
  ein Fehler, kein Skip (`curl -f`, kein `|| true`).

- **Check 11: die Schrittzahl stimmt in Überschriften und Frontmatter
  überein.** Das ist der repo-lokale Anker, gegen den die Description geprüft
  wird — die Zahl, auf die sich der CI-Schritt stützt, ist damit selbst
  abgesichert und nicht bloss geglaubt. Zusätzlich geprüft: die Schritte sind
  lückenlos von 1 durchnummeriert.

- **`ruff check` auf `reference/`, mit gepinnter Version.** Der Referenzcode
  wurde bisher nur kompiliert. `compileall` prüft Syntax — ein ungenutzter
  Import, ein mutables Default-Argument oder eine falsche Importreihenfolge
  kompilieren anstandslos und wandern dann in jeden `*-mcp`-Server, der die
  Vorlage kopiert. `ruff.toml` schaltet dafür das Linting ein (E, W, F, I, UP,
  B, SIM, C4, RUF); der Pre-Commit-Hook bekommt `ruff-check` dazu, damit lokal
  und CI dieselbe Antwort geben.

- **Import-Smoke-Test für `reference/*.py` (Check 3).** Die Vorlagen werden
  wirklich geladen, nicht nur kompiliert: Import vorhanden, Klassenkörper baut
  durch, Pydantic-Modell validiert sein eigenes Schema. Die Abhängigkeiten
  dafür stehen gepinnt in `requirements-reference.txt`. Fehlen sie, meldet der
  Check `FAIL` mit dem Installationsbefehl — kein stiller Skip, sonst meldete
  ein Lauf ohne Abhängigkeiten «bestanden», wo «nicht gelaufen» richtig wäre.
  Der Check läuft über `reference/*.py` statt über eine gepflegte Liste, damit
  eine dritte Vorlage automatisch abgedeckt ist.

- **Wächter gegen eingecheckte `.pyc`-Dateien (Check 4).** Der Vorfall steht
  seit 1.1.0 unter «Removed» im Changelog, der Wächter dagegen fehlte. Das
  Schwester-Repo `mcp-transport-hardening-skill` hat ihn seit jeher.

### Changed

- **Jeder Check, der über eine Überschrift, ein Regex oder einen Dateinamen
  ankert, bricht jetzt ab, wenn sein Anker verschwindet** — statt weiter grün
  zu melden, ohne noch etwas zu prüfen. Betroffen: Check 1 (fehlende
  `probe_template.sh`), Check 2 (`compileall` meldet auf einem `reference/`
  ohne `.py`-Dateien Erfolg), Check 6 (leerer Überschriften- **oder**
  Referenz-Satz macht die Differenz zwangsläufig leer, also „alle aufgelöst"),
  Check 8 (fehlendes Companion-README las sich wie ein falscher Inhalt). Die
  Checks 9 und 10 hatten diese Absicherung bereits; das Muster stammt aus
  `mcp-transport-hardening-skill`.

- **`ruff.toml`: `select = []` entfernt.** Die Begründung — Vorlagen führen
  offene Namen, ruff meldete sie korrekt als F821 — war aus einem
  Schwester-Repo übernommen, in dem sie zutrifft. Für die beiden Dateien hier
  gilt sie nicht: beide sind geschlossen und bestehen das Linting unverändert.

### Fixed

- **`reference/response_envelope.py`: Zeile über 88 Zeichen** (E501), gefunden
  vom neu eingeschalteten `ruff check`.

- **Das Frontmatter versprach ein «3-Schritte-Vorgehen», `SKILL.md` führt
  fünf.** Gefunden vom neuen Check 11, beim ersten Lauf. Schritt 4 (Übergabe an
  `github-repo`) und Schritt 5 (Portfolio-Register) sind nummerierte Schritte
  der Prozedur; die Zusage war schlicht nicht mitgewachsen. Korrigiert auf
  `5-Schritte-Vorgehen` — die Zeichenzahl bleibt gleich, das 1024er-Limit der
  Description ist weiterhin eingehalten (1017 Zeichen).

## [1.7.0] - 2026-08-05

1.6.0 hat zwei Lücken bewusst offen gelassen — die zulässigen `cacheScope`-Werte
und die Platzierung von `ttlMs` — statt sie zu raten. Sie sind jetzt an der
autoritativen Stelle geprobt (`schema/2026-07-28/schema.ts`) und stehen konkret
im Text. Dazu bekommen die Referenzdateien die Messungen, die 1.7 verlangt, und
Schritt 5 hört auf, ein bestimmtes Werkzeug vorauszusetzen.

### Added

- **`freshness_probe()` und `order_probe()` in `reference/probe_template.sh`.**
  Die erste ist eine `HEAD`-Abfrage mit Fallback-Hinweis, wenn weder
  `Last-Modified` noch `ETag` vorhanden sind, gedacht für den täglichen Lauf über
  mindestens zwei Zyklen; der Block gibt die Ableitungsregeln und die
  `cacheScope`-Frage direkt aus. Die zweite schickt denselben Listen-Call zweimal
  und vergleicht die Zeilen-Identitäten — mit dem Vorbehalt, dass Gleichheit
  notwendig und nicht hinreichend ist.

  Beim Testlauf hat `order_probe` zweimal die eigene Regel verletzt, bevor sie
  stand, und beide Male auf dieselbe Art: Die Identität kam zuerst aus der
  Position der Zeile, womit `0,1,2` gegen `0,1,2` verglichen wurde und jede
  Quelle als stabil galt — auch eine, die bei jedem Aufruf mischt. Und zwei
  identische *Fehlerantworten* ergaben zwei leere Listen, also ebenfalls
  «identisch». Jetzt kommt die Identität aus der Zeile (`id`, `uri`, `name`, …,
  sonst ein Kurz-Hash), und bei null gelesenen Zeilen verweigert die Funktion die
  Aussage und zeigt auf 1.2c. Dieselbe Regel, die der Skill für Proben aufstellt,
  gilt für seine eigenen Werkzeuge.

- **`reference/befund_tabelle_template.md`: Abschnitt «Aktualisierungsrhythmus
  und Haltbarkeit» und Abschnitt «Spec-Ziel».** Ersterer trägt die
  Rhythmus-Tabelle, die vier Ableitungsklassen, die Trennung der beiden
  `ttlMs`-Familien und zwei Häkchen (zugesagtes `ttlMs` ≥ interne Cache-TTL,
  Reihenfolge stabil). Letzterer die Zielversion mit den zwei zulässigen
  Abweichungsgründen und dem Häkchen gegen deprecated Bausteine. Bisher verlangte
  1.7 eine Messung, für die das mitgelieferte Protokoll keine Zeile hatte.

### Changed

- **1.7 nennt `cacheScope`-Werte und Platzierung konkret.** Beide Felder stehen
  auf oberster Ebene des Result-Objekts, nicht in `_meta`, gebündelt in
  `CacheableResult`; `cacheScope` ist `"public"` oder `"private"` mit der Semantik
  von HTTP `Cache-Control` — geteilt über Autorisierungskontexte hinweg oder auf
  einen beschränkt. Sechs Result-Typen erben davon, darunter
  `ListResourceTemplatesResult` und `DiscoverResult`, die in 1.6.0 noch fehlten;
  `CallToolResult` gehört nicht dazu. Die Familien-Tabelle ist entsprechend
  korrigiert.

  Zwei Punkte aus 1.6.0 waren damit ungenau und sind es nicht mehr: `ttlMs` ist in
  `CacheableResult` **nicht optional** — die Wahl steht nur zwischen gemessen und
  geraten, nicht zwischen Zahl und keiner Zahl —, und ein Handle als
  Tool-Argument ändert am `cacheScope` nichts, weil Tool-Ergebnisse die Felder
  gar nicht tragen. Der Entscheid fällt pro Response-Typ, nicht pro Server.

- **Schritt 5 heisst «Portfolio-Register nachführen» und trennt zwei Hälften.**
  Normativ ist die `portfolio.json` im Index-Repo: versioniert, im Diff, im
  Review, in der CI — und ohne Konto bei irgendwem, was für ein öffentlich
  installierbares Skill der Punkt ist. Die menschenlesbare Hälfte ist eine
  Darstellung nach Wahl; die Notion-Datenbank dieses Portfolios steht als eine
  Variante neben generierter Markdown-Tabelle, GitHub Issues und «gar keine», mit
  Nutzen und Kosten je Variante. Dazu die Regel, die alle teilen: genau eine
  normative Quelle, jede Darstellung daraus abgeleitet statt parallel gepflegt.
  Ein gedriftetes Register ist schlechter als keines — es beantwortet «welche
  Server stehen noch auf der alten Spec?» falsch, statt die Frage offen zu lassen.

- **Anti-Pattern 14** nennt jetzt auch die dritte Möglichkeit, die keine ist:
  `ttlMs` weglassen.

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
