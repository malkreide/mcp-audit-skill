# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.2.0] - 2026-08-07

**Reichweite — dreimal zu klein, einmal zu gross.** Dreizehn Regeln statt zwölf,
und drei der bestehenden lernen dazu. Kein Anlass von aussen: Weder die drei PRs
von 2026-07 noch die Spec-Revision stecken darin, sondern der Betrieb der Kette
selbst. Was die vier Änderungen verbindet, ist eine Grenze, die niemand
absichtlich gezogen hat — und ausserhalb davon wird nichts rot, also sieht der
Zustand von innen aus wie Erfolg.

Neu ist **Regel 13** («Ein Guard prüft nicht, was vor ihm abgezweigt wurde»),
inklusive ihrer räumlichen Hälfte: Behauptungen, die ausserhalb des Repos stehen
— GitHub-Description, Topics, Registry-Eintrag — erreicht kein Check, der Dateien
liest. **Regel 6** verlangt jetzt drei Schritte statt zwei, weil eine Ersetzung,
die ihr Ziel verfehlt, wie ein überlebender Mutant aussieht. **Regel 1** führt den
Bound bis in den Lock. Und **Regel 7** bekommt mit (d) den Spiegelfall: eine
`autouse`-Fixture, deren Reichweite nicht zu klein war, sondern zu gross — dort
wird auch innerhalb davon nichts rot, weil der entschärfte Test seinen Gegenstand
verloren hat.

**Zur Nummer: `2.1.0` bleibt frei.** Dieses Release folgt auf `2.0.0` und
überspringt einen Minor, damit die Nummer mit dem Stand von
[`mcp-audit`](https://github.com/malkreide/mcp-audit-skill) gleichzieht — die
Kette wird häufiger als Ganzes zitiert als einzeln, und zwei auseinanderlaufende
Zählungen kosten bei jedem Verweis eine Rückfrage. Die Lücke ist beabsichtigt und
steht hier, weil eine übersprungene Version sonst wie ein verlorenes Release
aussieht. Ab hier zählen beide Repos wieder normal weiter; ein Gleichstand ist
kein Versprechen für kommende Releases.

### Added

- **Regel 7 bekommt einen vierten Fall: die `autouse`-Fixture, die ein fremdes
  Modul patcht.** `monkeypatch.setattr(modul.asyncio, "sleep", ...)` liest sich,
  als bliebe der Griff in `modul` — aber `modul.asyncio` ist das Modul `asyncio`,
  dasselbe Objekt, das jeder andere Import im Prozess hält. Mit `autouse=True`
  gilt der Griff für jeden Test der Suite, auch für die, die davon nichts wissen.
  Die bestehende Falle (b) betrifft die *Ebene* eines Patches (Instanz gegen
  Klasse); diese betrifft sein *Ziel* — wem der Name gehört, auf den er zeigt.

  Real passiert ist damit das Stilllegen einer Parallelitätsprüfung. Der Test
  liess zwei Coroutinen ineinandergreifen und benutzte dafür `asyncio.sleep(0)`,
  den Standardweg, dem Event-Loop das Wort zu geben. Der Ersatz gab es nicht
  weiter: Eine `async`-Funktion, die zurückkehrt, ohne etwas abzuwarten,
  suspendiert nie. Er wurde rot, und das war Glück — er behauptete die
  Verschränkung direkt. Hätte er die Nebenläufigkeit indirekt geprüft, an einem
  Zähler oder einer Reihenfolge, wäre er grün geblieben und hätte nichts mehr
  abgesichert.

  Damit schliesst der Fall eine Lücke in Regel 6: Der Mutationstest ist dort das
  Abnahmekriterium, und dies ist genau der Fall, in dem er grün bleibt, ohne
  etwas zu prüfen — nicht weil die Mutation nicht ankam, sondern weil der Test,
  der sie hätte fangen sollen, seinen Gegenstand vorher an die Fixture verloren
  hat.

  Zwei Eigenschaften tragen im ✓-Muster, und sie sind unabhängig voneinander:
  Der Produktivcode hält einen Modul-Alias (`_sleep = asyncio.sleep`), auf den
  die Fixture zielt, damit die Reichweite am Namen ablesbar ist statt aus der
  Importkette erschlossen — und der Ersatz nimmt die *Dauer* weg, nicht die
  *Übergabe an den Event-Loop* (`await asyncio.sleep(0)` statt `return None`).
  Der Nachweis ist Regel 6 auf die Fixture selbst angewandt, dazu ein Grep auf
  jedes `setattr`, dessen Ziel ein importiertes Fremdmodul ist.

  Die Regelzahl bleibt bei dreizehn: Das ist ein Fall innerhalb von Regel 7,
  keine neue Regel. `reference/patterns.py` trägt das Muster als lauffähigen
  Block, beide READMEs die Kurzfassung.

### Added

- **Ein Guard auf die GitHub-Description, und Regel 13 bekommt ihre räumliche
  Hälfte.** Der Zählguard deckt `SKILL.md`, beide READMEs und
  `reference/patterns.py` ab — und war korrekt, während die Description des
  Repos noch «twelve transport-hardening rules» sagte. Sie liegt ausserhalb des
  Repos, also erreicht sie kein Check, der Dateien liest. Das ist Regel 13
  räumlich statt zeitlich: dieselbe ungezogene Grenze, nur nicht zwischen
  vorher und nachher, sondern zwischen drinnen und draussen.

  Regel 13 nennt die Klasse jetzt ausdrücklich — Description, Topics,
  Registry-Eintrag, Deployment-Manifest, Marketplace-Text tragen oft genau die
  Behauptung, die im Repo geprüft wird — mit zwei tragenden Eigenschaften für
  den Guard: Der Sollwert kommt aus derselben Quelle wie bei den übrigen
  Prüfungen (hier das Zahlwort aus dem `patterns.py`-Docstring, das der Schritt
  davor bereits an die Regelzahl bindet, statt eines zweiten Wortschatzes), und
  ein fehlgeschlagener Abruf ist ein Fehler, kein Skip — sonst meldet der Check
  «bestanden», wo «nicht gelaufen» richtig wäre (`OPS-005`).

  Der neue CI-Schritt ist **rot, bis die Description gesetzt ist**: Sie lässt
  sich nicht per Commit korrigieren, sie hängt am Repo. Die Fehlermeldung nennt
  den Befehl.

Dreizehn Regeln statt zwölf, und drei der bestehenden lernen dazu. Diese vier
Änderungen stammen weder aus den drei PRs von 2026-07 noch aus der Spec-Revision,
sondern aus dem Betrieb der Kette selbst. Die ersten drei haben untereinander
dieselbe Form: Etwas ist eingeführt, aber nicht dort angekommen, wo es hätte
wirken müssen — und ausserhalb der Reichweite wird nichts rot, also sieht der
Zustand von innen aus wie Erfolg. Der vierte, Regel 7(d), ist deren Spiegelung:
Dort war die Reichweite nicht zu klein, sondern zu gross — und rot wird auch
innerhalb davon nichts, weil der entschärfte Test seinen Gegenstand verloren hat.

### Added

- **Regel 13 — «Ein Guard prüft nicht, was vor ihm abgezweigt wurde.»** Ein
  frisch gemergter Guard gilt ab dem Merge-Commit und nur vorwärts. Zwei Mengen
  liegen ausserhalb und zeigen beide grünes CI: der Stand, der schon auf `main`
  liegt, und jeder Zweig, der vor dem Merge geschnitten wurde.

  Der Schaden dahinter: Ein Versions-Sync-Check — Badge gegen oberste
  CHANGELOG-Überschrift — landete auf `main`, nachdem der Release-Branch für
  `0.20.0` bereits geschnitten war. Dessen Pipeline lief ihn nie, der Release
  ging durch, und danach prüfte niemand `main` nach. Die README-Badges waren
  zwei Releases lang falsch, gedeckt von einem Guard, der genau dafür
  geschrieben worden war.

  Das mechanische Stück ist der `push`-Trigger auf `main` plus
  `workflow_dispatch`; der Rest ist Handarbeit — den Lauf auf `main` nach dem
  Merge einmal ansehen und die vorher geschnittenen Zweige nachziehen
  (`git branch -r --no-contains <merge-sha>`). Der Nachweis ist Regel 6 auf den
  Guard selbst angewandt, auf `main` statt im PR.

  **Angehängt statt eingeschoben**, obwohl die Regel inhaltlich zum Beweisblock
  5–7 gehört — dieselbe Begründung wie bei 8–12: Eine Umnummerierung machte die
  eigene Historie und vier Nachbar-Repos rückwirkend falsch. Die Blocktabelle im
  Kopf führt den Beweisblock deshalb als «5–7, 13».

  Die Regel hat sich beim Entstehen selbst bestätigt: Ihr Zweig war vor dem
  Merge von `2.0.0` geschnitten, lief dessen CI nie, und die neue Regel trug
  bis zum Rebase die Nummer 8 — die inzwischen vergeben war.

### Changed

- **Regel 6 verlangt jetzt drei Schritte statt zwei: Mutation anwenden, per Diff
  belegen, dass sie angekommen ist, erst dann testen.** Eine Ersetzung lief ins
  Leere, weil das gesuchte Literal im umbrochenen Text über eine Zeilengrenze
  fiel — die Datei blieb unverändert, die Suite grün, und das las sich als
  überlebender Mutant. Ein No-op und eine echte Lücke im Guard sind am Ergebnis
  nicht zu unterscheiden: Beide Male steht null in der Spalte. Getrennt werden
  sie nur vorher, mit `git diff --exit-code` vor dem Testlauf. Dieselbe Ursache
  wie `mcp-audit` §4.1: Wer auf Zeilenumbrüche prüft, prüft den Zeilenumbruch
  und nicht den Satz.

  Dazu die zweite Falle desselben Handgriffs, aus demselben Lauf: Zwischen zwei
  Mutationen wird aus einer Kopie des Arbeitsbaums zurückgesetzt, nicht mit
  `git checkout --` — das restauriert HEAD und verwirft jede uncommittete
  Änderung derselben Datei.

- **Regel 1 führt den Bound bis in den Lock.** Auslöser des SDK-Major-Sprungs
  war ein unbeschränkter Resolve, und die Lehre daraus wird falsch gezogen, wenn
  sie beim Bound in `pyproject.toml` stehen bleibt. `uv sync` löst zwar von sich
  aus neu auf — aber die Pfade, die zählen, tun das nicht: `--frozen`, ein
  bereits gebautes Environment, ein Container-Image aus dem committeten Lock.
  Beide Richtungen stehen jetzt nebeneinander, weil sie sich nicht
  widersprechen: Der Lock verdeckt die schlechte Auflösung von morgen (deshalb
  frisch installieren und importieren) und den guten Bound von heute (deshalb
  `importlib.metadata.version("mcp")` messen statt die Deklaration lesen).

- **Die Zuordnung Regel → Audit-Check führt Regel 13 mit,** gegen `mcp-audit`
  v2.0.0: [`OPS-005`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/OPS-005.md)
  deckt die eine Hälfte — den Guard, der nie gegen `main` gelaufen ist — und
  nicht die andere: den Zweig, der vor dem Merge geschnitten wurde.

- **Die Abdeckungsprüfung für `reference/patterns.py` zählt nur noch einzelne
  Regel-Nennungen.** Ein Mutationstest dieses PRs hat gezeigt, warum: Das
  Löschen des ganzen Regel-13-Blocks blieb grün, weil die Sammelüberschrift
  darüber die Nummer mitzählte. Eine Sammelüberschrift benennt einen Abschnitt
  und belegt kein Muster, das jemand kopieren kann. Bereiche werden weiterhin
  expandiert, aber nur noch für die ausgegebene Abdeckungszeile.

## [2.0.0] - 2026-08-05

Sieben Regeln werden zwölf. Anlass ist die Spec-Revision `2026-07-28`, und sie
trifft diesen Skill härter als jeden anderen der Kette: Transport und Auth sind
genau die Ebenen, die sich am stärksten geändert haben. Der Handshake ist weg,
die Sitzung ist weg, zwei Header sind neu Pflicht, der Legacy-Transport hat ein
Abschaltdatum, und serverinitiierte Rückfragen sind durch ein Muster ersetzt, bei
dem dieselbe Bearbeitung mehrfach von vorn läuft.

Major, nicht Minor: Der Skill spannt neu über **zwei** Spec-Baselines, die
Regelzahl bestimmt Überschriften, auf die die CI zeigt, und die Aussage «Nicht
nötig für Server, die ausschliesslich über stdio laufen» im Trigger war
schlichtweg falsch geworden — die Stateless-Regeln gelten dort ebenso.
`mcp-audit` ist an derselben Grenze auf v2.0.0 gegangen.

**Die neuen Regeln sind angehängt, nicht eingeschoben.** Die Beweisregeln bleiben
5–7. Dieses CHANGELOG zitiert «Regel 6» und «Regeln 5–7» mehrfach, `mcp-audit`
und `mcp-data-fidelity` verweisen von aussen darauf; eine Umnummerierung hätte
die eigene Historie rückwirkend falsch gemacht. Die Blockordnung steht dafür
jetzt als Tabelle im Kopf: 1–4 Bind und Verdrahtung, 5–7 der Beweis, 8–12 die
Stateless-Welt.

### Added

- **Regel 8 — ohne Sitzung teilt sich Zustand still, statt zu fehlen.**
  `initialize`, `notifications/initialized` und `Mcp-Session-Id` sind entfernt;
  jede Anfrage trägt Protokollversion, `clientInfo` und Capabilities in `_meta`
  unter `io.modelcontextprotocol/*`. Der gefährliche Server ist nicht der, der
  abstürzt, sondern der, der weiterläuft: prozesslokaler Zustand, der per
  Konvention über die Sitzung adressiert war, landet ohne Sitzung im selben
  Eimer — bei einem Aufrufer unauffällig, bei zweien ein Datenleck ohne
  Fehlermeldung. Zustand reist als expliziter, server-geprägter, ablaufender
  Handle im Tool-Argument; ein Handle ohne Ablauf ist Zustand ohne Ende, weil
  ohne Verbindungsabbruch kein Ereignis mehr aufräumt. Und `server/discover` ist
  serverseitig ein **MUSS**, clientseitig ein MAY — genau diese Asymmetrie macht
  ein fehlendes `server/discover` zu einer falschen Auskunft über die eigene
  Protokollversion statt zu einem fehlenden Feature.

  Der Nachweis ist der Zwei-Aufrufer-Test, und er ist zugleich Regel 5 auf sich
  selbst angewandt: Unter der Mutation «Handle-Argument entfernen» bleibt ein
  Test mit *einem* Aufrufer grün, weil er die Bedingung gar nicht herstellt.

- **Regel 9 — die Adresse steht neu aussen auf dem Umschlag.** `Mcp-Method` und
  `Mcp-Name` sind Pflichtheader auf Streamable-HTTP-POSTs, eine Abweichung ist
  `HeaderMismatchError` mit Code `-32020`. Der Gewinn ist, dass eine Schicht
  ohne Body-Parsing weiss, was durchläuft; genau daraus entsteht der Angriff.
  Entscheidet ein Gateway am Header und der Server am Body, haben zwei Instanzen
  über zwei verschiedene Anfragen entschieden — `Mcp-Name: search_datasets` im
  Header, `delete_record` im Body. Der Vergleich ist deshalb eine
  Sicherheitsgrenze und muss serverseitig stattfinden, weil nur dort beide
  Seiten vorliegen. Inklusive des Auslassungsfalls: Wer nur vergleicht, *wenn*
  beide Header da sind, hat eine Prüfung gebaut, die man durch Weglassen umgeht.

  Dazu die zweite Doku-Pflicht dieses Skills, Schwester der `MCP_HOST`-Pflicht
  aus Regel 2: Im README gehört, auf welche Header-Werte das Deployment routet
  und limitiert. Ein Gateway, das auf `Mcp-Name` allow-listet, ist Teil der
  Sicherheitsarchitektur des Servers und steht nirgends in seinem Code.

- **Regel 10 — Legacy HTTP+SSE hat jetzt ein Datum: `2027-07-28`.** Deprecated
  ist der Pfad seit `2025-03-26`; was `2026-07-28` ändert, ist nicht die
  Empfehlung, sondern ihre Verbindlichkeit — Feature-Lifecycle-Politik, Fenster
  von mindestens zwölf Monaten, frühester Entfernungstermin damit `2027-07-28`.
  Dieselbe Frist gilt für Roots, Sampling und Logging. Eine Empfehlung ohne
  Termin erzeugt keinen Vorgang, sondern einen Kompatibilitätspfad, den niemand
  abschaltet, weil er niemanden stört — und dieser zweite Netzweg erbt die
  Härtung des ersten nicht, was Regel 3 mit Ablaufdatum ist.

  Mit Erkennungsrezept über drei Orte, weil jeder für sich sauber sein kann,
  während ein anderer es nicht ist: Code, was das Deployment tatsächlich
  startet, und der Draht. Nur der dritte ist ein Beweis.

- **Regel 11 — MRTR: der Server antwortet und hält nichts offen, dafür läuft die
  Arbeit mehrfach.** Serverinitiierte `roots/list`, `sampling/createMessage` und
  `elicitation/create` sind ersatzlos gestrichen. Stattdessen: `resultType:
  "input_required"` plus `inputRequests`, der Client wiederholt den
  ursprünglichen Request mit `inputResponses`. Die Umkehrung ist das Teure — aus
  einem Dialog *innerhalb* einer Bearbeitung wird eine Bearbeitung, die von vorn
  läuft, und alles vor dem Rückfragepunkt passiert bei jedem Retry erneut. Damit
  wandert das Thema aus «Bedienoberfläche» in «Korrektheit».

  Zwei Anschlüsse an Bestehendes: Korrelation läuft ohne Sitzung nur noch über
  `requestState`, mit denselben Eigenschaften wie ein Handle aus Regel 8; und ein
  offengehaltener Stream ist die Hänger-Klasse aus Regel 7 mit neuer Ursache,
  weshalb der Retry-Test unter Timeout laufen muss.

- **Regel 12 — Auth-Härten, mit ausgeschriebenem Negativbefund.**
  RFC-9207-`iss`-Validierung vor dem Einlösen des Authorization Code inklusive
  der «present»-Falle: Die Pflicht gilt für einen *vorhandenen* `iss`, wer nur
  dann prüft, erfüllt den Buchstaben und wird durch Weglassen angegriffen — was
  der Autorisierungsserver kann, steht in seinen Metadaten und muss nicht
  geraten werden. Dazu CIMD statt DCR und issuer-geschlüsselte Credentials als
  Speicherseite desselben Mix-up-Angriffs.

  Für dieses Portfolio ist die Regel **nicht anwendbar**, und genau das steht
  jetzt da statt einer Auslassung: Die Server sind read-only, führen
  `auth_model: none` und lösen keinen Authorization Code ein. Ausgeschrieben,
  weil ein weggelassener Abschnitt von einem übersehenen nicht zu unterscheiden
  ist — dieselbe Logik, aus der Regel 5 besteht. Die Bedingung, die den Befund
  aufhebt, ist benannt: CIMD und Issuer-Bindung greifen ab jedem Auth-Modell,
  die `iss`-Pflicht ab dem OAuth-Proxy.

- **Abgrenzungstabelle «was hier steht, was der Katalog prüft, was der Auditor
  live exerziert».** Die drei Repos berühren dieselben Gegenstände; ohne die
  Trennung entsteht Duplikation, und Duplikation altert auseinander. Die
  Faustregel steht jetzt ausgeschrieben: *Hier steht, wie man es verdrahtet und
  woran man sieht, dass es trägt. Der Katalog fragt, ob es da ist. Der Auditor
  fragt, ob es heute noch da ist.* Mit `transport_boot_probe.py` und
  `spec_probe.py` aus `mcp-continuous-auditor` namentlich in der Spalte «im
  Betrieb», inklusive der Status `SPEC_DRIFT` und `LEGACY_TRANSPORT`.

- **Ein Abschnitt, der benennt, was dieser Skill bewusst *nicht* abdeckt.**
  `resultType` auf allen Results (`ARCH-018`), die Frist für Roots, Sampling und
  Logging (`ARCH-019`), `ttlMs`/`cacheScope` und deterministische Reihenfolge
  (`ARCH-020`), versionierte Extensions (`ARCH-021`). Das sind Fragen an die
  Form der Antwort, nicht an den Transport. Sie hier zu wiederholen würde den
  Skill verlängern, ohne dass er etwas entscheidet.

- **Patterns für die Regeln 8–12 in `reference/patterns.py`** — `mint_handle` /
  `decode_handle` mit Signatur und Ablauf, `server_discover`, der
  Zwei-Aufrufer-Test, `require_matching_headers` mit dem Auslassungsfall,
  `LEGACY_SSE_REMOVAL_EARLIEST` samt dem dreiteiligen Erkennungsrezept als
  Kommentar, `submit_with_mrtr` mit Idempotenzschlüssel und `requestState`,
  `redeem_authorization_code` mit `iss`-Prüfung und issuer-geschlüsselten
  Credentials, und der Negativbefund als Kommentarblock daneben. Der
  ✗-Gegenpart zu Regel 8 — der prozesslokale Cursor-Dict — steht bewusst als
  auskommentiertes Muster da, wie schon der `evil.example.com`-Test bei Regel 5.

### Changed

- **Die Zuordnung Regel → Check ist gegen `mcp-audit` v2.0.0 nachgeführt.** Der
  Stand im Text lautete «v1.7.0, 97 Checks in zwölf Kategorien»; er lautet jetzt
  «v2.0.0, 112 Checks in zwölf Kategorien auf zwei Spec-Baselines». Neu
  zugeordnet: Regel 8 auf `ARCH-015`, `ARCH-016` und `ARCH-017` — drei Checks
  für eine Regel, weil ein Server den ersten bestehen und am dritten scheitern
  kann, also zustandslos verdrahtet und trotzdem zustandsbehaftet gebaut ist;
  Regel 9 auf `SCALE-008` mit `SEC-027` daneben; Regel 10 auf `SCALE-009` und
  `SCALE-010`; Regel 11 auf `HITL-006`; Regel 12 auf `SEC-025` und `SEC-026`.
  Regel 1 führt zusätzlich `DEP-001` für den Versions-Cap.

  Dazu die Gegenrichtung, die vorher nirgends stand: **Fünf Checks messen einen
  Gegenstand, den `2026-07-28` entfernt hat** — `SCALE-002`, `SCALE-003`,
  `SCALE-007`, `SDK-004`, `SEC-009`. Für einen migrierten Server sind sie nicht
  mehr anwendbar. `SEC-009` hat in `ARCH-017` eine Ersatzdimension: Die
  Sitzungs-ID gibt es nicht mehr, die Frage nach der Ratbarkeit der Referenz
  schon — sie ist in die Tool-Signatur gewandert, wo kein Auth-Layer mehr
  hinschaut.

- **Regel 1 bekommt die dritte Achse: der Cap ist eine Weiche, keine
  Formalie.** Das eigenständige `fastmcp` pinnt seinerseits `mcp<2.0`, ein
  Server auf diesem Paket kann also nicht nebenbei auf die 2er-Linie des
  offiziellen SDK wandern, und `fastmcp` 4.0 ist ein eigener Bruch daneben. Wer
  beide im selben Environment auflösen lässt, bekommt keinen Fehler, sondern
  einen Resolver-Entscheid. Dazu die untere Grenze als tragender Teil: `2.0.0`
  hat `mcp.server.fastmcp` ersatzlos entfernt, eine `>=1.x`-Range lässt einen
  Resolver eine Version wählen, die am Import stirbt (`DEP-001`).

- **Regel 2 bekommt die PaaS-Variante der uvicorn-Falle.** Wo die Plattform den
  Port beim Start injiziert und den Hostnamen generiert, ist ein im Code
  stehender Port nicht bloss unschön, sondern falsch: Regel 4 verlangt
  Portgenauigkeit, und eine portgenaue Liste mit dem falschen Port ist dasselbe
  421. Die Allow-List muss aus dem gelesenen Wert zusammengesetzt werden.

- **Regel 3 nennt den SSE-Pfad nicht mehr «deprecated, aber erreichbar».** Er
  trägt jetzt ein Abschaltdatum und verweist auf Regel 10. Und seit
  `2026-07-28` reist auf jedem Pfad noch etwas mit: die Header-Prüfung aus
  Regel 9, dieselbe Art Kontrolle wie `transport_security`, mit demselben
  Fehlerbild, wenn nur ein Pfad sie bekommt.

- **Regel 4 hält fest, dass sie den Wegfall der Sitzung unbeschadet überlebt —
  und dadurch wichtiger wird.** Wo es keine Sitzung mehr gibt, an die sich
  etwas binden liesse, ist die Host-Prüfung die einzige Kontrolle, die vor der
  Bearbeitung jeder einzelnen Anfrage steht. Sie ersetzt keine
  Authentifizierung; sie ist nur die einzige, die nicht mit dem Lebenszyklus
  verschwunden ist.

- **Regel 7(a) sagt «Transport-Manager» statt «Session-Manager».** Die
  Formulierung setzte eine Sitzung voraus, die es nicht mehr gibt. Der Befund
  selbst bleibt unverändert gültig, und das gehört dazugesagt: Was
  `2026-07-28` entfernt, ist die *Protokoll*-Sitzung, nicht der Aufbau der App
  im Lifespan. Ein blanker `httpx.ASGITransport` liefert weiterhin 500 auf
  alles.

- **Der Trigger im Frontmatter deckt die neue Welt ab** — Migration auf Spec
  `2026-07-28`, Ablösung eines Legacy-HTTP+SSE-Pfads, `-32020` neben dem 421,
  und die Begriffe `initialize`, `Mcp-Session-Id`, `server/discover`,
  `Mcp-Method`/`Mcp-Name`, `input_required`, `iss`/CIMD/DCR. Der Schlusssatz
  «Nicht nötig für Server, die ausschliesslich über stdio laufen» war falsch
  geworden und lautet jetzt: Für reine stdio-Server entfallen die Bind- und
  Header-Regeln, nicht die Stateless-Regeln.

- **Die Checkliste hat einen dritten Block.** «Die Stateless-Welt (Regeln
  8–12)» mit zwölf Punkten, und der Beweisblock trägt zwei neue Zeilen — dass
  die Stateless-Kontrollen mit **zwei** Aufrufern getestet sind, weil einer in
  beiden Zuständen grün ist.

- **Der Abschnitt «Woher diese Regeln stammen» sagt, was die neuen Regeln nicht
  haben.** Die Regeln 1–7 stammen aus drei Pull Requests mit einem
  eingetretenen Schaden. Die Regeln 8–12 haben **keine Narbe, sondern ein
  Datum** — ein externes, datiertes Ereignis, dessen Änderungen nachlesbar
  statt plausibel sind. Das steht ausgeschrieben, weil der Contributing-Abschnitt
  von jeder neuen Regel einen konkreten Schaden verlangt; die Latte wird dort
  entsprechend auf «Schaden **oder** datierte, zitierbare Änderung von aussen,
  und gesagt werden muss, welches von beidem» präzisiert.

  Zwei Dinge sind daran gemessen und nicht angenommen, beide an
  `zurich-opendata-mcp`: dass ein mcp-2.x-Prozess den Legacy-Handshake mit Cap
  `2025-11-25` und den per-request-Umschlag mit `2026-07-28` **nebeneinander**
  bedient — weshalb ein Stateless-Fehler für jeden Client auf der alten Ära
  unsichtbar ist —, und dass das Erkennungsrezept aus Regel 10 dort an allen
  drei Orten negativ zurückkommt. Der negative Befund steht bewusst als
  Beispiel: Wer nur den positiven Fall kennt, weiss nicht, wann er fertig ist.

- **CI: die Regelzahl-Prüfung kennt Zahlwörter bis `fifteen` und meldet ein
  unbekanntes Wort als eigenen Fehler.** Das `WORDS`-Dict endete bei `ten`. Beim
  Sprung auf zwölf hätte `WORDS.get("twelve")` `None` ergeben und dieselbe
  Meldung erzeugt wie ein echter Zahlendreher — der Befund hätte auf
  `reference/patterns.py` gezeigt, während die Lücke im Prüfskript lag. Das ist
  derselbe Fehler, den `1.1.1` beim Version-Badge behoben hat: Die Meldung muss
  sagen, welche Seite sich bewegt hat. Die Überschriften-Literale der READMEs
  sind mitgezogen (`The twelve rules` / `Die zwölf Regeln`).

## [1.4.0] - 2026-08-03

Sieben Regeln, unverändert — dieses Release ändert nichts an dem, was der Skill
lehrt. Es ändert eine Zeile in der Zuordnung Regel → Audit-Check: Die drei
Beweisregeln standen zusammengefasst als «kein Check», obwohl für Regel 5 einer
danebenliegt, der dieselbe Fehlerklasse fängt. Eine Sammelzeile ist bequem und
selten falsch genug, um aufzufallen — genau die Eigenschaft, gegen die diese
Tabelle geschrieben wurde.

### Changed

- **Die Regel-zu-Check-Zuordnung führt die Regeln 5, 6 und 7 einzeln,
  nachgeführt gegen `mcp-audit` v1.7.0.** Sie standen in einer Zeile als
  «5–7 — die Beweisführung: kein Check». Für Regel 6 stimmt das weiterhin, für
  Regel 5 nicht: [`DRIFT-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/DRIFT-003.md)
  — «Kein Test-Assert wird vom Degradationspfad erfüllt» — ist dieselbe Klasse,
  ein Test, der aus dem falschen Grund besteht. Seine Ausprägungen sind andere
  (Degradationsantwort, zu weite Koordinaten-Box, `match=` als Regex statt als
  Literal), und der Transportfall steht nicht darin — der Negativtest, den auch
  eine Loopback-Fallback-Policy grün macht. Bei Regel 7 liegt `OPS-005`
  benachbart, ohne die Harness-Fälle zu treffen.

  Der Fehler war keine Veralterung: `DRIFT-003` (Katalog v1.2.0) und `OPS-005`
  (v1.3.0) existierten bereits, als die Tabelle geschrieben wurde. Eine
  zusammengefasste Zeile verdeckt genau das, was die Tabelle sichtbar machen
  soll — deshalb stehen die drei Regeln jetzt einzeln da, auch wenn zwei davon
  leer bleiben.

  Dazu der Katalogstand im Text (v1.7.0, 97 Checks in zwölf Kategorien), damit
  beim nächsten Wachstum erkennbar ist, wogegen zuletzt geprüft wurde.

## [1.3.0] - 2026-08-02

Seven rules, unchanged — nothing here touches what the skill teaches. The
related-repositories table becomes the MCP quality chain, five repositories
along the lifecycle with a shared GitHub topic, and the same table now stands in
`SKILL.md` rather than only in the READMEs.

One figure was wrong: the rule-to-check mapping claimed four of seven rules
where it covers three. Four is the count of the rules the catalogue does *not*
see — the sentence directly below the table said so all along.

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

- **The table in `SKILL.md` was still the old five-skill list.** The READMEs
  became the quality chain — five repositories along the lifecycle, with
  `mcp-continuous-auditor` in and `mcp-builder` beside it — while the table the
  model actually reads still named the previous set. The CI guard added with the
  chain only reads the READMEs, so nothing caught it. `SKILL.md` now carries the
  same five in the same order, with the stage column, and keeps the pointer from
  the audit row to the rule-to-check mapping below it.

- **The rule-to-check mapping said four rules where it covers three.** The table
  maps rule 1 to `SDK-006`, rule 3 to `ARCH-013` and rule 4 to `SEC-024` — and
  the sentence directly below it already read «Wer nach den Regeln 1, 3 und 4
  baut» and «Für die Regeln 2 und 5–7 gilt das nicht». Four is the count of the
  rules the catalogue does *not* see; it had been stated as the number it covers.
  Corrected in `SKILL.md` and both READMEs. Cross-checked from the other side:
  the row for this skill in `mcp-audit-skill`'s README lists exactly three
  checks.

## [1.2.0] - 2026-08-02

Two documentation changes, no rule added, changed or removed — seven rules, as
in 1.1.0. Both are about the same thing seen from two sides: a fault that
produces no signal. Rule 6 names the variant that needs no network at all, a
test that establishes the very condition under which the fault cannot occur. The
introduction drops the assurance that a 421 gets noticed, because one layer up
it can arrive as an ordinary empty result.

### Changed

- **The introduction no longer promises that a 421 is noticed.** It distinguished
  this skill's silence from the one in `mcp-data-fidelity` — there a plausible
  but wrong answer, here no answer at all. One layer up the two classes
  converge: a caller that measures the 421 only by "no records came back" passes
  it on as an empty set, and then it *is* a plausible, substantively wrong
  answer after all. Measured case: a request with a foreign Host header returns
  HTTP 421 with the body `Invalid Host header`, and nobody upstream saw it as
  anything but zero hits.

  This sharpens the skill's own thesis rather than importing a neighbour's rule.
  The reason the transport path needs a test of its own was stated as "a stdio
  suite never touches it"; the stronger reason is that the failure can be
  swallowed above, so the transport test is the only place it reliably becomes
  visible. Counterpart to rule 3 in
  [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill)
  v1.2.0 and `FID-003` in `mcp-audit` v1.5.0, cited from this side. Two
  sentences, no new rule — seven rules, unchanged.

- **Rule 6 now names the mock as the same failure outside the transport.** The
  first of the three findings — a test that set the environment variable whose
  absence was the subject under test, and passed with the mutation applied —
  generalises beyond a network transport: a mock pins its own assumption, so a
  wrong assumption produces a test that confirms the fault instead of finding
  it. Counterpart to the same addition in
  [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill)
  rule 5, cited from the other side. Two sentences, no new rule.

## [1.1.1] - 2026-08-01

CI only. No rule, no pattern, no documentation changed — seven rules, as in
1.1.0. The version badge is simply no longer a figure that nothing checks.
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

## [1.1.0] - 2026-08-01

Documentation and guards. No rule added, changed or removed — seven rules, as in
1.0.0. What changes is that the skill now says where each rule is audited, and
that the reference file can no longer drift from the rules it claims to cover.

### Added

- **Rule-to-check mapping against the `mcp-audit` catalogue.** `SKILL.md` gains a
  table saying which rule corresponds to which check, verified by reading the
  check files rather than inferring from titles: rule 1 is `SDK-006`, rule 3 is
  `ARCH-013`, rule 4 is `SEC-024` with `SEC-005` as its outbound counterpart.

  It also names the two gaps rather than stretching a near-match over them. Rule 2
  has no check: `SEC-016` looks like one and is the opposite case — it treats
  `0.0.0.0` as an *unintended* bind (NeighborJack), while rule 2 assumes a
  deliberate one and asks whether it reaches the app. Rules 5–7 have no check
  either, which is a scope boundary: the catalogue verifies that a control exists,
  not that its proof holds.

- **The related-skills tables now name all five skills in one order** — builder,
  probe, fidelity, transport-hardening, audit — in `SKILL.md` and both READMEs, so
  the family reads the same way from every repository in it. `mcp-builder` is
  described as Anthropic's without a licence claim: `anthropics/skills` carries no
  LICENSE file and the API reports none, so stating one would be a guess in a
  public README.

- Contributing section in both READMEs. It states the bar a new rule has to
  clear: the incident it came from, a counter-example pair, and its Nachweis —
  the same form CI enforces. A plausible-sounding guideline without a scar behind
  it makes the skill longer and weaker.

### Changed

- **CI now checks `reference/patterns.py` for content, not just syntax.** Until
  now it was verified to exist and to compile; its two claims — the number word
  in the module docstring and that every rule actually appears — were guarded by
  nothing. Both happened to be correct, which is the least reliable reason for a
  value to be right.

  The rule-count step now covers the file as well: the docstring word against the
  count in `SKILL.md`, and the set of rules mentioned (`Rule 4`, `Rules 2 + 3`,
  `Rules 5-7` — ranges expanded) against the set that exists. A rule without a
  pattern is a rule nobody can copy, so a gap fails the build.

  Verified against three mutations rather than a green run: docstring reverted to
  "six" → *docstring says 'six' rules, SKILL.md defines 7*; the anchor phrase
  reworded → *anchor removed or reworded, so this check would silently stop
  checking*; every mention of rule 7 renamed → *nothing for rule(s) [7]*. All
  three reverted, green again.

## [1.0.0] - 2026-08-01

Initial release. Seven rules for MCP servers on a network transport, covering the
gap between "the server is built correctly" and "the server comes up and turns
away who it must turn away" — and, in rules 5–7, how to prove that it does.

### Added

- **Rule 1 — the SDK major bump breaks three things, only one of them
  mechanically.** The module and class rename (`mcp.server.fastmcp.FastMCP` →
  `mcp.server.mcpserver.MCPServer`) is search-and-replace. `mcp.settings` turning
  read-only is not: the assignment raises `ValueError`, a read raises
  `AttributeError`, and a server carrying the old line does not start under HTTP
  at all — the bind goes to `run()` as kwargs instead. Annotations move to
  snake_case for Python-side reads only; camelCase survives as a pydantic alias
  and the wire format is unchanged, which is why a test finds this and no client
  would, and why camelCase remains correct in TypeScript servers. Includes the
  distinction between the standalone PyPI package `fastmcp` and
  `mcp.server.fastmcp` in the official SDK — two projects, one name.
- **Rule 2 — `host` is the seed of the allow-list, not a cosmetic parameter.**
  It defaults to `127.0.0.1` and the SDK derives the inbound allow-list from it,
  so an app builder that never receives it answers HTTP 421 on exactly the
  `0.0.0.0` deployment it is documented for. With the uvicorn trap: a `--factory`
  is called with no arguments, so `--host` configures the listener and never
  reaches the app, and the README must say why the env vars are not redundant
  next to the flags.
- **Rule 3 — every path that builds an ASGI app is wired identically.** A custom
  builder used only when auth or CORS is configured, the SDK-served `run()` path,
  and a deprecated SSE path alongside it. Wire one and arming a security control
  silently depends on unrelated configuration. The port travels with the host —
  one repo passed only the host, so the loopback entries named a port nobody
  serves.
- **Rule 4 — the inbound host allow-list is its own control.** Why CORS, a
  token, and the egress allow-list all miss the question, and the four
  properties that make the list usable: port-exact, loopback always in, CORS
  origins included, no `*`. Fail-open on a non-loopback bind, made visible with a
  startup warning, because a guessed list rejects the deployment it should
  protect.
- **Rule 5 — a negative test must fail for *your* reason, not a default's.**
  Green only says the request was rejected, not that your control rejected it.
  `evil.example.com` is refused by the correct list, by a loopback fallback, and
  by a hostname-only list alike — three states, one green test, no information.
  Right hostname with the wrong port is the case only a port-exact list decides
  correctly, and it needs its positive twin to rule out the fallback state.
- **Rule 6 — the mutation test is the acceptance criterion for a security
  control.** Not "write tests": name the mutation, apply it, record which tests
  fall, and put the table in the PR. Carries all three finds from the source
  PRs — the test that set the allow-list variable itself and so passed *with* the
  mutation applied; the dropped port that failed no test at all because the seam
  was untested; and the removal that made the suite hang instead of fail.
- **Rule 7 — the test harness is itself a source of error on HTTP transports.**
  The bare `httpx.ASGITransport` and its 500s, the instance-versus-class
  `monkeypatch` trap that shadows `mcp.run` and starts real uvicorn mid-suite,
  and the branch test that must assert its branch or hang. With the SSE
  explanation for *why* a missing control hangs rather than fails.
- **Release checklist** with 20 items, split into "Der Server (Regeln 1–4)" and
  "Der Beweis (Regeln 5–7)", and a naming note: two of the source PRs are titled
  `SEC-005` but implement `SEC-024`, the inbound control. `SEC-005` is the
  outbound direction.
- **`reference/patterns.py`** — copy-paste patterns for all seven rules,
  targeting MCP SDK 2.x behind ASGI/uvicorn:
  - `build_transport_security()` with the four properties spelled out at the call
    site — port-exact, loopback always present, configured CORS origins folded in,
    `*` dropped — and the fail-open branch that warns instead of guessing.
  - `create_http_app()` as a uvicorn `--factory` that reads its own bind, with
    the reason in the docstring: a factory is called with no arguments, so
    `--host` never reaches the app.
  - `serve_http()` wiring one policy object into all three branches that can
    serve HTTP — SDK-served `run()`, the custom builder, and the deprecated SSE
    path — and `build_http_app()`, which receives the policy rather than building
    its own.
  - `is_read_only()` plus `test_wire_format_is_unchanged()`, which makes rule
    1(c)'s Nachweis runnable: if the pydantic alias still emits `readOnlyHint`,
    the change is read-side only and no client contract is at stake.
  - The test shapes for rules 5–7: the `client` fixture built through the app
    lifespan; the rule 5 pair plus the `evil.example.com` test written out as a
    comment showing why it is *not* used; `test_real_hostname_is_accepted`, which
    must run without `MCP_ALLOWED_HOSTS` or it passes with the mutation applied;
    `_patch_run()` carrying the patch-level trap and its symptom; both branch
    tests, each asserting which branch ran; and `test_the_sse_path_is_wired`,
    which checks the wiring precisely where an end-to-end test would hang.
  - Rule 6's mutation table as a comment block, and a closing note on running the
    suite under a timeout and each branch test alone *and* in the full suite.
- Bilingual README (EN/DE) and a CI workflow that enforces the skill's own form:
  every rule carries a counter-example pair and a Nachweis, the rule numbers are
  sequential, and the count matches both READMEs.

### Context

The rules come from three pull requests of the same cycle (2026-07):
[`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29),
[`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51) and
[`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25).

Only the first was a bug. The other two were a missing control — defensible for
the intended deployment, but leaving anyone who runs the server differently
without a way in, and failing no test because nothing was wrong.

Two things about the first one generalise beyond its own fix. It was the last
server in the portfolio still on the old SDK major, because it sits *nested*
inside another repository with its own `pyproject.toml`: it fell through every
enumeration that lists top-level repos, and the parent project's dependency
constraint never covered it. And in two of the three repositories the mutation
test corrected the *tests* rather than the code — which is where rules 5–7 come
from, and why they are in this skill at all.
