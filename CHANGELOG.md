# Changelog

Alle wesentlichen Änderungen am Skill und am Check-Katalog werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Versionierung: [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

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
