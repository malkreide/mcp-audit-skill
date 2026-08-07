---
name: mcp-transport-hardening
description: Transport-, Bind- und Stateless-Härtung für MCP-Server mit Netz-Transport, über beide Spec-Baselines (2025-11-25 und 2026-07-28). Ergänzend zu mcp-builder, wenn (1) ein Server auf eine neue SDK-Major oder auf Spec 2026-07-28 migriert wird, (2) von stdio auf streamable-http umgestellt oder ein Legacy-HTTP+SSE-Pfad abgelöst wird, (3) Host, Port oder Bind konfiguriert, durchgereicht oder in einer ASGI-Factory gelesen werden, (4) ein Server mit HTTP 421 oder JSON-RPC -32020 antwortet, nicht startet oder «nur lokal erreichbar» ist, (5) eine eingehende Host-/Origin-Allow-List entworfen oder gegen CORS und Auth-Token abgewogen wird, (6) `initialize`, `Mcp-Session-Id`, `server/discover`, `Mcp-Method`/`Mcp-Name`, MRTR-`input_required` oder OAuth-`iss`/CIMD/DCR berührt werden, (7) Transport-Tests per Mutationstest abgenommen werden oder eine Suite hängt statt zu scheitern, oder (8) ein neuer Guard oder CI-Check gemergt wird. Für reine stdio-Server entfallen die Bind- und Header-Regeln, nicht die Stateless-Regeln.
---

# MCP Transport Hardening — kommt der Server hoch, weist er ab wen er abweisen muss, und bleibt er zustandslos?

Companion zu `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **kommt er unter dem konfigurierten Transport überhaupt hoch, weist er ab wen er abweisen muss, und hält er das auch ohne Sitzung durch?**

Das ist eine eigene Fehlerklasse, weil sie ebenfalls still ist — nur anders still als bei `mcp-data-fidelity`. Dort liefert der Server eine plausible Antwort, die inhaltlich falsch ist. Hier liefert er gar keine: grüne Unit-Tests, sauberer Linter, und in Produktion startet der Prozess nicht oder beantwortet jede Anfrage unter einem echten Hostnamen mit HTTP 421. Der Transport-Pfad ist genau der Teil, den eine Testsuite über stdio nie berührt.

Eine Schicht höher fallen die beiden Klassen allerdings zusammen: Wer das 421 nur daran misst, dass keine Datensätze zurückkommen, reicht es als Leermenge weiter — und dann ist es doch wieder eine plausible, inhaltlich falsche Antwort ([`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill) Regel 3, `FID-003`). Verlass dich also nicht darauf, dass ein 421 auffällt; sichtbar wird es nur dort, wo der Transport-Pfad selbst geprüft wird.

**Die Leitfrage bei jedem Server mit Netz-Transport:** *Wenn ich den Bind ändere — folgt die eingehende Allow-List mit, auf jedem Pfad, der eine App baut, und wird ein Test rot, wenn sie es nicht tut?* Ist die Antwort nein, greift eine der Regeln 1–4.

**Die zweite Leitfrage, seit Spec `2026-07-28`:** *Wenn zwei Aufrufer nichts mehr teilen — keinen Handshake, keine Sitzung, keine Verbindung —, sieht der eine dann noch etwas vom anderen, und wird ein Test rot, wenn er es tut?* Ist die Antwort ja, greift eine der Regeln 8–12.

## Wie die dreizehn Regeln geordnet sind

| Block | Regeln | Frage |
|---|---|---|
| Bind und Verdrahtung | 1–4 | Kommt er hoch, und weist er richtig ab? |
| Der Beweis | 5–7, 13 | Woran erkennt man, dass es trägt, und wen deckt der Beweis ab? Gilt auch für 8–12 |
| Die Stateless-Welt `2026-07-28` | 8–12 | Hält er ohne Sitzung, und spricht er den neuen Umschlag? |

Der Beweisblock steht in der Mitte und nicht am Ende, weil er älter ist als der dritte Block und weil dieses Repo, sein eigenes CHANGELOG und vier Nachbar-Repos «Regel 6» und «Regeln 5–7» namentlich zitieren. Eine Umnummerierung würde die eigene Historie rückwirkend falsch machen — neue Regeln werden deshalb angehängt, nicht eingeschoben. Regel 13 ist der Grund, warum diese Zeile nicht zusammenhängend ist: Sie gehört zum Beweis, kam aber nach 8–12 dazu, und eine ordentliche Nummer war es nicht wert, dieselbe Historie zu brechen.

Der zweite Teil bleibt der teurere: Transportregeln kann man nachschlagen, die Beweisführung nicht. Genau deshalb bekommt jede der Regeln 8–12 ihren Nachweis in der Form der Regeln 5–7 — Mutation benennen, anwenden, protokollieren.

**Zwei Baselines gleichzeitig.** Die Regeln 1–7 gelten unverändert auf beiden Ständen: Bind, Verdrahtung, Host-Allow-List und Beweisführung hängen am Transport, nicht am Lebenszyklus. Die Regeln 8–12 gelten auf `2026-07-28`. Und die beiden Stände stehen nicht nacheinander, sondern nebeneinander — im selben Prozess. Am Portfolio nachgemessen und in `zurich-opendata-mcp`s `pyproject.toml` festgehalten: Der Legacy-`initialize`-Handshake cappt weiter bei `2025-11-25` (ein Client, der `2026-07-28` verlangt, bekommt `2025-11-25` zurück), während derselbe Server daneben einen per-request-Umschlag bedient, der `2026-07-28` erreicht. Ein Stateless-Fehler ist damit für jeden Client unsichtbar, der noch auf der alten Ära spricht.

---

## Regel 1 — Der SDK-Major-Sprung bricht drei Dinge, nur eines davon mechanisch

**(a) Modul und Klasse.** `mcp.server.fastmcp.FastMCP` → `mcp.server.mcpserver.MCPServer`. Das ist der mechanische Teil: ein Suchen-und-Ersetzen über Server-, Client- und Testmodule, den der Import-Fehler zuverlässig anzeigt.

**(b) `mcp.settings` ist schreibgeschützt.** Unter 1.x war das Setzen von Host und Port über die Settings der einzige Weg. Dieselbe Zeile wirft unter 2.x, *bevor* der Server hört.

```python
# ✗ 1.x — wirft unter 2.x: ValueError: "Settings" object has no field "host"
mcp.settings.host = settings.host
mcp.settings.port = settings.port
mcp.run(transport=settings.transport)

# ✓ 2.x — der Bind geht als Kwargs an run(), und von dort in die Allow-List
mcp.run(transport=settings.transport, host=settings.host, port=settings.port)
```

Nachgemessen statt angenommen: die **Zuweisung** wirft `ValueError`, ein **Lesezugriff** wirft `AttributeError`. Ein Server mit der alten Zeile startet unter HTTP **gar nicht**.

**(c) Tool-Annotations werden snake_case gelesen.**

```python
# ✗ unter 2.x immer None — der Attributname ist nicht mehr camelCase
if tool.annotations.readOnlyHint:

# ✓ snake_case im Python-Zugriff; camelCase bleibt der Alias auf dem Draht
if tool.annotations.read_only_hint:
```

Das Entscheidende daran: **das Drahtformat ist unverändert.** camelCase überlebt als pydantic-Alias, serialisiert kommt weiterhin `readOnlyHint` heraus. Nur der lesende Zugriff im Python-Code bricht. Deshalb findet das ein Test und kein Client — und deshalb ist **camelCase in TypeScript-Servern weiterhin korrekt**. Wer nach dieser Regel einen Node-Server «repariert», bricht funktionierenden Code.

**Abgrenzung, die genauso wichtig ist:** Das eigenständige PyPI-Paket `fastmcp` ist ein **anderes Projekt** als `mcp.server.fastmcp` im offiziellen SDK. `from fastmcp import FastMCP` bleibt dort gültig und wird von dieser Regel nicht berührt. Zwei Projekte, ein Name — wer sie verwechselt, macht funktionierenden Code kaputt.

**Die dritte Achse, seit `2026-07-28`: der Cap ist keine Formalie mehr, sondern eine Weiche.** `fastmcp` 3.x pinnt seinerseits `mcp<2.0`. Ein Server auf dem eigenständigen Paket kann deshalb nicht nebenbei auf die 2er-Linie des offiziellen SDK wandern — und `fastmcp` 4.0 ist ein eigener Bruch daneben. Wer beide Pakete im selben Environment auflösen lässt, bekommt keinen Fehler, sondern einen Resolver-Entscheid.

Der Versions-Cap wandert mit: `mcp[cli]>=1.0.0,<2` wird zu `>=2.0.0,<3`. Der Bound bleibt, nur am anderen Ende verankert. Ein `<2`-Cap kauft Zeit, indem er auf der letzten 1.x pinnt — ein Ziel ist er nie. Die untere Grenze ist dabei genauso tragend wie die obere: `2.0.0` hat `mcp.server.fastmcp` ersatzlos entfernt, eine `>=1.x`-Range lässt einen Resolver also eine Version wählen, die am Import stirbt. Im Katalog ist das [`DEP-001`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/DEP-001.md).

**Und der Bound wirkt erst im Lock.** Der Auslöser dieses ganzen Sprungs war ein **unbeschränkter Resolve** — kein Cap, also nahm die nächste Auflösung die neue Major mit. Die Lehre daraus wird falsch gezogen, wenn sie beim Bound in `pyproject.toml` stehen bleibt: Die Deklaration sagt, was gelten *soll*. Installiert wird, was der Lock sagt.

```toml
# ✗ Bound gesetzt, Lock unberührt — das Deployment installiert weiter die alte Auflösung
dependencies = ["mcp[cli]>=2.0.0,<3"]      # pyproject.toml, allein committet

# ✓ derselbe Bound, und der Lock im selben Commit neu aufgelöst
#   uv lock && git add uv.lock
```

`uv sync` löst zwar von sich aus neu auf, wenn `pyproject.toml` sich bewegt hat — aber genau die Pfade, die zählen, tun das nicht: `--frozen`, ein bereits gebautes Environment, ein Container-Image aus dem committeten Lock. Der Bound steht dann korrekt in der Datei, in der ihn ein Review liest, und ist im Prozess folgenlos. Das ist derselbe Riss wie in Regel 2, nur eine Ebene tiefer: Die Deklaration und der Ort, an dem sie wirken müsste, sind zwei verschiedene Dateien, und niemand prüft die Naht dazwischen.

Beide Richtungen sind nötig, und sie widersprechen sich nicht: Der Lock verdeckt die schlechte Auflösung von morgen (deshalb prüft man frisch), und er verdeckt den guten Bound von heute (deshalb muss man ihn mitführen).

**Nachweis:** Die 1.x-Settings-Zuweisung zurückbauen — ein Test muss mit `ValueError` scheitern, nicht das Deployment. Für (c): beide Schreibweisen serialisieren und die JSON vergleichen; sind sie identisch, ist es ein reines Lesethema und der Client bleibt aussen vor. Für den Cap: in einer leeren Umgebung installieren und den Import ausführen — eine Range, die im Lockfile funktioniert, sagt nichts über die Auflösung von morgen. Und für den Lock nicht die Deklaration lesen, sondern die Installation messen: den Installationspfad fahren, den die CI fährt, dann `importlib.metadata.version("mcp")` ausgeben. Steht dort die alte Version, wurde der Lock nicht mitgeführt — und der Bound ist Dekoration.

## Regel 2 — `host` ist die Saat der Allow-List, kein kosmetischer Parameter

`host` defaultet auf `127.0.0.1`, und das SDK leitet daraus die **eingehende** Host-Allow-List ab. Wird er dem App-Builder nicht durchgereicht, schaltet das SDK `127.0.0.1:*` scharf und beantwortet jede Anfrage unter einem echten Hostnamen mit **HTTP 421** — auf genau dem `MCP_HOST=0.0.0.0`-Deployment, für das der Server dokumentiert ist.

```python
# ✗ host bleibt auf 127.0.0.1 → 421 unter jedem echten Hostnamen
def create_http_app():
    return mcp.create_http_app()

# ✓ die Factory liest denselben Bind wie main()
def create_http_app():
    settings = get_settings()
    return mcp.create_http_app(host=settings.host, port=settings.port)
```

**Die uvicorn-Falle:** uvicorn ruft eine `--factory` **ohne Argumente** auf. `--host` konfiguriert nur den Listener und erreicht die App nie. Die Factory muss den Bind deshalb selbst aus derselben Konfiguration lesen wie `main()` — sonst hört der Prozess auf `0.0.0.0` und die App glaubt weiterhin, sie sei Loopback.

**Die PaaS-Variante derselben Falle.** Auf einer Plattform, die den Port beim Start injiziert (`$PORT`) und den Hostnamen generiert, ist der Bind erst zur Laufzeit bekannt. Ein im Code stehender Port ist dort nicht bloss unschön, er ist falsch: Regel 4 verlangt Portgenauigkeit, und eine portgenaue Liste mit dem falschen Port ist dasselbe 421 wie hier. Der Bind muss also aus derselben Quelle stammen, die die Plattform tatsächlich setzt — und die Allow-List aus dem gelesenen Wert zusammengesetzt werden, nicht aus einem Literal.

Daraus folgt eine Doku-Pflicht: Im README muss stehen, **warum `MCP_HOST`/`MCP_PORT` neben den uvicorn-Flags nicht redundant sind.** Das ist im Code unsichtbar, sieht wie eine Verdopplung aus, und hat genau deshalb ein reales Deployment getroffen.

**Nachweis:** Den `host`-Kwarg aus der Factory entfernen — Verdrahtungstest **und** End-to-End-Regressionstest müssen scheitern. Achtung bei der Konstruktion: Setzt der Regressionstest `MCP_ALLOWED_HOSTS`, besteht er **trotz** angewandter Mutation, weil der Kwarg bei expliziter Allow-List irrelevant ist. Tragend wird er erst, wenn das SDK raten muss.

## Regel 3 — Jeder Pfad, der eine ASGI-App baut, wird identisch verdrahtet

Ein Server hat selten einen Pfad in die App. In den drei Migrationen unten fanden sich: ein **eigener App-Builder**, der nur benutzt wurde, wenn Auth *oder* CORS konfiguriert war; ein vom SDK servierter **`run()`-Pfad**; und ein deprecateter **SSE-Pfad** daneben. Wird nur einer verdrahtet, hängt das Scharfschalten einer Sicherheitskontrolle still davon ab, ob zufällig Auth gesetzt ist.

```python
# ✗ nur ein Pfad bekommt die Kontrolle — welcher läuft, entscheidet die Konfiguration
if settings.auth_token or settings.cors_origins:
    uvicorn.run(build_http_app(transport_security=policy), ...)
else:
    mcp.run(transport="streamable-http")            # ohne Policy

# ✓ eine Quelle, jeder Pfad
policy = build_transport_security(host=settings.host, port=settings.port)
if settings.auth_token or settings.cors_origins:
    uvicorn.run(build_http_app(transport_security=policy), ...)
else:
    mcp.run(transport="streamable-http", transport_security=policy)
```

**Der Port reist mit.** Ein Repo reichte dem Builder nur den Host durch und liess ihn den Port defaulten — die Loopback-Einträge der Allow-List nannten damit einen Port, den niemand bedient. Host ohne Port ist eine halbe Verdrahtung.

**Seit `2026-07-28` reist noch etwas mit:** die Header-Prüfung aus Regel 9. Sie ist dieselbe Art Kontrolle wie `transport_security` und macht denselben Fehler mit — ein Pfad ohne sie ist ein Pfad ohne Sicherheitsgrenze. Und der SSE-Pfad ist nicht mehr bloss «deprecated, aber erreichbar», sondern trägt ein Abschaltdatum; siehe Regel 10.

**Nachweis:** `transport_security` **einzeln** aus jedem Pfad entfernen; jede Entfernung muss mindestens einen Test zum Scheitern bringen. Dasselbe für den Port an der Naht zwischen Serve-Funktion und App-Builder: in einem Repo scheiterte dabei **kein einziger** Test, weil der Port-Test nur den Builder abdeckte — und der wird mit explizitem Port gerufen.

## Regel 4 — Die eingehende Host-Allow-List ist eine eigene Kontrolle

Der Angriff ist DNS-Rebinding in der **eingehenden** Richtung: Eine Seite im Netz des Betreibers löst ihren eigenen Hostnamen auf die Adresse dieses Servers auf und spricht dann aus dem Browser mit ihm. Der Angreifer braucht keinen Netzzugang — nur jemanden im richtigen Netz, der seine Seite öffnet.

Drei naheliegende Kontrollen greifen hier nicht:

| Kontrolle | Warum sie nicht hilft |
|---|---|
| **CORS** | Aus Browsersicht ist die Anfrage **same-origin** — es gibt keinen Cross-Origin-Request, den eine Policy prüfen könnte |
| **Auth-Token** | Sagt, *wer* fragt. Die angreifende Seite läuft in einem Kontext, der bereits eines hält |
| **Egress-Allow-List** | Die Gegenrichtung: *wohin* der Server sprechen darf, nicht unter *welchem Namen* er angesprochen wird |

Nur die `Host`-Prüfung beantwortet die Frage.

```python
# ✗ geraten — weist genau das Deployment ab, das die Liste schützen soll
allowed_hosts = ["*"]                      # oder: der Hostname aus der Doku

# ✓ portgenau, Loopback immer drin, CORS-Origins mit aufgenommen, kein «*»
hosts = [f"127.0.0.1:{port}", f"localhost:{port}", *configured_hosts]
origins = [o for o in configured_origins if o != "*"]
if not configured_hosts and host not in LOOPBACK:
    log.warning("transport.host_allowlist_disabled", bind=host)   # fail-open, sichtbar
```

Vier Eigenschaften, jede mit einem Grund: **portgenau**, weil Einträge wörtlich verglichen werden; **Loopback immer drin**, wegen Container-Health-Checks; **konfigurierte CORS-Origins aufgenommen**, sonst weist der Transport genau die Browser-Clients ab, für die CORS geöffnet wurde; **kein `*`**, weil Origins literal verglichen werden und ein Stern damit niemanden trifft.

Ohne Konfiguration auf einem Nicht-Loopback-Bind bleibt der Schutz **aus — fail-open, aber sichtbar, mit Startwarnung.** Auf `0.0.0.0` ist der erreichbare Name im Prozess unbekannt, und eine geratene Liste ist schlechter als keine: sie weist das Deployment ab, das sie schützen soll. Das ist dasselbe 421 wie in Regel 2, nur selbst verschuldet.

**Diese Regel überlebt den Wegfall der Sitzung unbeschadet — und wird dadurch wichtiger.** Wo es keine Sitzung mehr gibt, an die sich irgendetwas binden liesse (Regel 8), ist die Host-Prüfung die einzige Kontrolle, die *vor* der Bearbeitung jeder einzelnen Anfrage steht. Sie ersetzt keine Authentifizierung; sie ist nur die einzige, die nicht mit dem Lebenszyklus verschwunden ist.

**Nachweis:** **Richtiger Hostname, falscher Port** muss abgewiesen werden — ein `evil.example.com` allein beweist nichts, weil eine zurückfallende Loopback-Policy ihn ebenfalls abweist. Dazu: ein gültiges `Bearer`-Token darf einen fremden Host nicht retten.

---

## Regel 5 — Ein Negativtest muss aus deinem Grund scheitern, nicht aus dem eines Defaults

Die Regeln 1–4 sagen, was verdrahtet sein muss. Die Regeln 5–7 sagen, woran man erkennt, dass es verdrahtet **ist** (und Regel 13, für wen dieser Nachweis dann gilt) — und sie sind der teurere Teil, weil man sie nicht nachschlagen kann. Sie gelten unverändert für die Regeln 8–12: jede der neuen Kontrollen hat einen zweiten Grund, aus dem ihr Negativtest grün werden könnte.

Ein Negativtest behauptet: «Diese Anfrage wird abgewiesen.» Grün heisst aber nur, dass sie abgewiesen *wurde* — nicht, dass **deine** Kontrolle sie abgewiesen hat. Überall dort, wo ein Default, ein Fallback oder eine vorgelagerte Schicht dieselbe Anfrage ebenfalls ablehnt, ist der Test mit der Kontrolle und ohne sie grün. Er misst dann die Umgebung, nicht den Code.

Die Prüffrage lautet deshalb nicht «wird abgewiesen?», sondern: **Gibt es einen zweiten Grund, aus dem genau diese Anfrage scheitern könnte?** Gibt es einen, ist der Test noch nicht scharf. Man braucht den Fall, den **nur** die eigene Kontrolle richtig entscheidet.

Kanonisches Beispiel, die eingehende Allow-List:

```python
# ✗ ein fremder Hostname — beweist nichts
def test_foreign_host_is_rejected(client):
    assert client.get("/mcp", headers={"Host": "evil.example.com:8000"}).status_code == 421

# ✓ richtiger Hostname, FALSCHER Port — das entscheidet nur eine portgenaue Liste
def test_right_host_wrong_port_is_rejected(client):
    assert client.get("/mcp", headers={"Host": "mcp.example.ch:9999"}).status_code == 421
```

`evil.example.com` wird in **jedem** Zustand abgewiesen: von der korrekten Liste, von einer auf Loopback zurückgefallenen Default-Policy, und auch von einer Liste, die nur auf den Hostnamen und nicht auf den Port schaut. Drei verschiedene Zustände, ein grüner Test — der Informationsgehalt ist null.

`mcp.example.ch:9999` trennt sie: Eine portgenaue Liste weist ab, eine hostnamen-only Liste **lässt durch**. Und weil dieser Test seinen positiven Zwilling braucht — richtiger Name, richtiger Port wird angenommen —, fällt der Loopback-Rückfall ebenfalls auf: unter ihm scheitert der positive Test. Erst das Paar pinnt den Zustand fest.

**Nachweis:** Zu jedem Negativtest die zweite Ursache benennen, die dieselbe Ablehnung erzeugen würde — und wenn es eine gibt, einen Fall wählen, den sie nicht abdeckt. Ein Negativtest ohne seinen positiven Zwilling unterscheidet «abgewiesen» nicht von «alles wird abgewiesen».

## Regel 6 — Der Mutationstest ist das Abnahmekriterium für jede Sicherheitskontrolle

Nicht «Tests schreiben». Sondern: **Mutation benennen, anwenden, prüfen dass sie angekommen ist, protokollieren, welche Tests fallen.** Eine Kontrolle, deren Entfernung nichts rot macht, ist unbewiesen — unabhängig davon, wie viele grüne Tests daneben stehen.

**Der dritte Schritt ist kein Formalismus: die Mutation muss mutieren.** Eine Ersetzung, die ihr Ziel verfehlt, hinterlässt eine unveränderte Datei und eine grüne Suite — dasselbe Bild wie eine echte Lücke im Guard. Null in der Spalte heisst dann nicht «Kontrolle unbewiesen», sondern «nichts passiert», und die beiden sind am Ergebnis nicht zu unterscheiden. Der Fall, in dem das zuschlug: Das Suchmuster stand in einem umbrochenen Absatz, `5 partial` lag im Text als `5\npartial` — die Ersetzung traf nichts, und der scheinbar überlebende Mutant war ein No-op. Dieselbe Ursache wie in [`mcp-audit`](https://github.com/malkreide/mcp-audit-skill) §4.1 («Whitespace normalisieren, bevor auf Text geprüft wird»): *Wer auf Zeilenumbrüche prüft, prüft den Zeilenumbruch — nicht den Satz.* Dort geht ein Check-Treffer verloren, hier eine Mutation, und beide Ergebnisse sehen aus wie eine Aussage über den Code.

Eine Zeile mehr, und der Fall ist ausgeschlossen:

```bash
# ✗ angewandt geglaubt — traf die Ersetzung nichts, sieht das aus wie ein überlebender Mutant
sed -i 's/transport_security=policy//' src/server.py
pytest                                    # 0 rot → Befund? Oder gar keine Mutation?

# ✓ erst beweisen, dass sich etwas geändert hat, dann erst testen
sed -i 's/transport_security=policy//' src/server.py
git diff --exit-code src/server.py && { echo "Mutation war ein No-op"; exit 1; }
pytest
```

`git diff --exit-code` endet mit 0, wenn **nichts** geändert wurde — der `&&`-Zweig ist also genau der Fehlerfall. Bei einer Mutation von Hand tut derselbe Blick in `git diff` es auch; ungeprüft bleiben darf es nicht. Und beim Zurücksetzen zwischen zwei Mutationen: aus einer Kopie des Arbeitsbaums, nicht mit `git checkout --` — das restauriert HEAD und wirft jede uncommittete Änderung derselben Datei weg.

In den drei PRs unten hat der Handgriff dreimal etwas gefunden, das sonst durchgegangen wäre. Der teuerste Fall zuerst:

```python
# ✗ stellt selbst die Bedingung her, unter der der Fehler nicht auftreten kann
def test_real_hostname_is_accepted(client, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.ch:8000")
    assert client.get("/mcp", headers={"Host": "mcp.example.ch:8000"}).status_code != 421

# ✓ ohne explizite Liste muss das SDK aus dem Bind ableiten — erst dann trägt der Kwarg
def test_real_hostname_is_accepted(client, monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert client.get("/mcp", headers={"Host": "mcp.example.ch:8000"}).status_code != 421
```

Die drei Funde, jeder mit seinem Merksatz:

1. **Der Test bestand mit angewandter Mutation.** Er setzte die Allow-List-Variable selbst, und bei expliziter Liste ist der `host`-Kwarg irrelevant — tragend wird er erst, wenn das SDK raten muss. *Ein Test, der die Bedingung herstellt, unter der der Fehler nicht auftreten kann, prüft nichts.*
2. **Den Port zwischen zwei Funktionen fallenzulassen liess gar keinen Test scheitern.** Die Naht war ungetestet, weil der vorhandene Test die Zielfunktion mit explizitem Port aufrief. *Getestet wird die Naht, an der der Wert reist — nicht die Funktion, die ihn schon hat.*
3. **Die Kontrolle zu entfernen liess die Suite hängen statt scheitern.** Das ist kein Betriebsunfall, sondern der Regelfall: Ohne Kontrolle wird die verbotene Anfrage *zugelassen*, und zugelassen heisst bei einem Stream *warten*. Siehe Regel 7.

Der erste Merksatz gilt über den Transport hinaus: In `mcp-data-fidelity` (Regel 5) bildet ein Mock die eigene Annahme ab — ist sie falsch, ist der Mock falsch, und der Test bestätigt den Fehler, statt ihn zu finden. Derselbe Fehler, ein Spezialfall davon: Dort ist die hergestellte Bedingung die ganze Antwort.

**Nachweis:** Die Tabelle selbst — sie entsteht nur, wenn jede Mutation tatsächlich angewandt und die Suite tatsächlich gelaufen ist. Eine Zeile mit null roten Tests ist ein Befund, kein Nebenergebnis: Entweder fehlt der Test, oder die Kontrolle tut nichts — oder die Mutation ist nie angekommen. Die dritte Möglichkeit wird zuerst ausgeschlossen, mit einem Diff, sonst untersucht man einen Befund, den es nicht gibt. Die Tabelle gehört in den PR.

| Mutation | scheiternde Tests |
|---|---|
| `transport_security` aus dem eigenen App-Builder | 4 |
| `transport_security` aus dem SDK-`run()`-Pfad | 2 |
| `transport_security` aus dem SSE-Pfad | 1 |
| Allow-List nicht portgenau | 3 |
| Port reist nicht bis zum Builder | 1 |

Für die Regeln 8–12 gilt dieselbe Form. Die Mutationen stehen dort jeweils unter «Nachweis» — Handle-Argument entfernen, Header-Vergleich entfernen, Idempotenzschlüssel entfernen, `iss`-Prüfung entfernen.

## Regel 7 — Die Test-Harness ist bei HTTP-Transporten selbst eine Fehlerquelle

Vier Fallen. Die ersten drei haben dasselbe Symptom: Der Befund sieht aus wie ein Infrastrukturproblem und wird als Rauschen abgetan. Die vierte hat gar keines — sie nimmt einem Test still seinen Gegenstand, und ein Test ohne Gegenstand ist grün.

**(a) Ein blanker `httpx.ASGITransport` liefert 500 auf jede Anfrage.** Streamable HTTP baut seinen Transport-Manager im **App-Lifespan** auf, und dieser Transport führt den Lifespan nie aus. Wer den 500er für einen Befund hält, debuggt den falschen Code. Das gilt unabhängig von der Baseline: Was `2026-07-28` entfernt, ist die *Protokoll*-Sitzung, nicht der Aufbau der App.

```python
# ✗ kein Lifespan → kein Transport-Manager → 500 auf alles
transport = httpx.ASGITransport(app=build_http_app(settings))
client = httpx.AsyncClient(transport=transport, base_url="http://test")

# ✓ TestClient führt den Lifespan aus
with TestClient(build_http_app(settings)) as client:
    ...
```

**(b) Die Patch-Ebene muss konsistent bleiben.** Ein Test patchte `mcp.run` auf der **Instanz**. `monkeypatch` schreibt einen von der Instanz gelesenen Klassen-Wert beim Zurückrollen *auf die Instanz* — `mcp.run` bleibt dauerhaft verdeckt, ein späterer Klassen-Patch wird wirkungslos, und echtes uvicorn startet mitten in der Suite. Symptom: **Der Test besteht allein und hängt die Suite.** Wer im Repo bereits auf der Instanz patcht, patcht überall auf der Instanz.

**(c) Jeder Zweig-Test behauptet ausdrücklich, welcher Zweig lief.** Sonst scheitert ein falscher Zweig nicht, er hängt.

```python
# ✗ prüft das Ergebnis, nicht den Weg — nimmt der Test den anderen Zweig, startet uvicorn
serve_http(settings)
assert policy_was_applied

# ✓ der Zweig ist Teil der Behauptung
calls: list[dict] = []
monkeypatch.setattr(mcp, "run", lambda **kw: calls.append(kw))
serve_http(settings)
assert len(calls) == 1, "der Builder-Zweig lief — dieser Test behauptet den run()-Zweig"
assert calls[0]["transport_security"] is not None
```

Warum der SSE-Fall hängt, verbindet (a) und (c): Ohne Allow-List wird ein SSE-GET unter fremdem Host **zugelassen** und öffnet einen endlosen Event-Stream, auf den der `TestClient` beim Verlassen wartet. Die fehlende Kontrolle äussert sich also nicht als roter Test, sondern als stehende Suite — und ein Hänger wird routinemässig als Flake abgetan. Regel 11 fügt dieser Klasse eine zweite Ursache hinzu, die nichts mit SSE zu tun hat.

**(d) Eine `autouse`-Fixture, die ein fremdes Modul patcht, entschärft die Mechanik im ganzen Prozess.** `monkeypatch.setattr(modul.asyncio, "sleep", ...)` liest sich, als bliebe der Griff in `modul` — aber `modul.asyncio` **ist** das Modul `asyncio`, dasselbe Objekt, das jeder andere Import im Prozess hält. Mit `autouse=True` gilt der Griff für jeden Test der Suite, auch für die, die davon nichts wissen. (b) betrifft die *Ebene* des Patches, hier geht es um sein *Ziel*: Wem gehört der Name, auf den er zeigt?

Was real passiert ist: Eine solche Fixture hat eine Parallelitätsprüfung stillgelegt. Der Test liess zwei Coroutinen ineinandergreifen und benutzte dafür `asyncio.sleep(0)` — den Standardweg, dem Event-Loop das Wort zu geben. Der Ersatz gab es nicht weiter: Eine `async`-Funktion, die zurückkehrt, ohne etwas abzuwarten, suspendiert nie. Die eine Coroutine lief also durch, bevor die andere begann, und der Test behauptete Nebenläufigkeit über einen Ablauf, in dem es keine gab.

Er wurde rot, und das war Glück — er prüfte die Verschränkung direkt. Hätte er die Nebenläufigkeit nur indirekt geprüft, an einem Zähler, einer Reihenfolge, einem Ergebnis, wäre er grün geblieben und hätte nichts mehr abgesichert. Das ist der Unterschied zu (a)–(c): Dort ist der Schaden sichtbar und wird bloss falsch zugeordnet. Hier bleibt nichts übrig, das man zuordnen könnte.

```python
# ✗ sieht lokal aus, greift aber ins Modul asyncio — jeder Import im Prozess, jeder Test der Suite
@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def _instant(_delay): return None            # kehrt zurück, ohne zu suspendieren
    monkeypatch.setattr(server.asyncio, "sleep", _instant)

# ✓ der Produktivcode hält einen Alias, die Fixture patcht den Alias
# src/server.py:  _sleep = asyncio.sleep   …   await _sleep(delay)
@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def _instant(_delay): await asyncio.sleep(0)  # Dauer weg, Übergabe an den Loop bleibt
    monkeypatch.setattr(server, "_sleep", _instant)
```

Zwei Eigenschaften tragen. **Der Patch zielt auf einen Namen, den dieses Repo besitzt** — dann ist seine Reichweite am Namen ablesbar, statt aus der Importkette erschlossen werden zu müssen. Und **der Ersatz nimmt die Dauer weg, nicht die Übergabe an den Event-Loop**: `await asyncio.sleep(0)` ist genauso schnell, lässt aber den Punkt stehen, an dem eine andere Coroutine drankommt. Der Alias muss dafür an *jeder* Aufrufstelle stehen; bleibt irgendwo ein direktes `await asyncio.sleep(...)`, patcht die Fixture daran vorbei — derselbe No-op wie eine Mutation, die ihr Ziel verfehlt (Regel 6).

Damit schliesst (d) eine Lücke in Regel 6: Der Mutationstest ist dort das Abnahmekriterium, und dies ist genau der Fall, in dem er grün bleibt, ohne etwas zu prüfen. Nicht weil die Mutation nicht ankam — sie kam an —, sondern weil der Test, der sie hätte fangen sollen, seinen Gegenstand vorher an die Fixture verloren hat.

**Nachweis:** Ein Timeout auf die Suite (`pytest --timeout=30`) macht aus jedem Hänger einen Fehlschlag mit Stacktrace, und die Stelle ist damit benannt statt gemutmasst. Dazu jeden Zweig-Test **einzeln und in der vollen Suite** laufen lassen: Die Instanz-Patch-Falle aus (b) zeigt sich ausschliesslich im zweiten Fall. Für (d) ist die Fixture selbst der Gegenstand von Regel 6 — den Ersatz gegen einen ohne `await` tauschen: Verliert kein Test seine Aussage, hat auch keiner die Nebenläufigkeit geprüft, die er behauptet. Und ein `setattr`, dessen Ziel ein importiertes Fremdmodul ist, ist ein Befund beim Hinsehen:

```bash
grep -rnE 'setattr\(\s*([A-Za-z_][A-Za-z0-9_.]*\.)?(asyncio|time|socket|os|random|subprocess)\s*,' tests/
```

---

## Regel 8 — Ohne Sitzung teilt sich Zustand still, statt zu fehlen

Mit `2026-07-28` fällt der Lebenszyklus weg, um den herum bisher gebaut wurde: `initialize` und `notifications/initialized` sind entfernt, der `Mcp-Session-Id`-Header ebenfalls. Jede Anfrage trägt Protokollversion, `clientInfo` und Capabilities selbst, in `_meta` unter `io.modelcontextprotocol/*`. Zustand über Aufrufe hinweg läuft nur noch über **explizite, server-geprägte Handles als gewöhnliche Tool-Argumente**.

Der gefährliche Fall ist nicht der Server, der abstürzt — der fällt beim ersten Aufruf auf. Der gefährliche Fall ist der Server, der **weiterläuft und still degradiert**: Er hält seinen Zustand in einer prozesslokalen Struktur, die per Konvention über die Sitzung adressiert war. Ohne Sitzung landet jeder Request im selben Eimer. Bei einem Nutzer merkt das niemand; bei zweien ist es ein Datenleck zwischen Aufrufern, das keinen Fehler wirft.

```python
# ✗ prozesslokaler Zustand, adressiert über etwas, das es nicht mehr gibt
_CURSORS: dict[str, int] = {}          # war: pro Sitzung — jetzt: pro Prozess

@mcp.tool()
async def next_page() -> str:
    offset = _CURSORS.get("current", 0)     # jeder Aufrufer liest denselben Eintrag
    _CURSORS["current"] = offset + 50
    return await fetch(offset)

# ✓ der Zustand steht im Argument, ist server-geprägt und läuft ab
@mcp.tool()
async def next_page(page_handle: str | None = None) -> str:
    offset = _decode_handle(page_handle)    # signiert, opak, mit Ablauf
    return await fetch(offset, next_handle=_mint_handle(offset + 50))
```

Drei Worte der Spec tragen die Last. **Explicit:** Der Handle steht im Schema des Tools, ein Modell sieht ihn. **Server-minted:** Der Server prägt ihn, der Client denkt ihn sich nicht aus — ein Handle namens `cursor=42` ist eine ratbare Referenz auf fremden Zustand und verschiebt die Angriffsfläche bloss in die Tool-Signatur, wo kein Auth-Layer mehr hinschaut. **As ordinary tool arguments:** Er reist im Argument, nicht in einem Header und nicht in einer Tabelle neben dem Request.

**Der zweite Fehler ist leiser: ein Handle ohne Ablauf ist Zustand ohne Ende.** Bei der Sitzung erledigte das Aufräumen der Verbindungsabbruch. Ohne Sitzung gibt es kein Ereignis mehr, an dem irgendetwas aufräumt — ein Dict voller Handles ist ein Leck, das keine Testsuite bemerkt, weil es sich in Tagen zeigt und nicht in Sekunden.

**`server/discover` ist serverseitig Pflicht, nicht Kür.** Die Spec ist hier asymmetrisch: Server **MÜSSEN** den RPC implementieren, um Protokollversionen, Capabilities und Identität bekanntzugeben; Clients **DÜRFEN** ihn vor jeder anderen Anfrage rufen. Genau diese Asymmetrie ist die Falle — weil kein Client ihn rufen muss, funktioniert ein Server ohne ihn im Alltag scheinbar tadellos, und auf stdio, wo er als Rückwärtskompatibilitäts-Sonde dient, kann ein Client danach nicht unterscheiden, ob er einen alten Server vor sich hat oder einen neuen mit einer Lücke. Ein fehlendes `server/discover` ist kein fehlendes Feature, sondern eine falsche Auskunft über die eigene Protokollversion.

**Nachweis:** **Zwei Aufrufer, kein gemeinsamer Kontext.** Zwei unabhängige Requests absetzen und behaupten, dass der zweite nichts vom ersten sieht. Der Mutationstest dazu: das Handle-Argument entfernen und auf den prozesslokalen Eimer zurückfallen — ein Test mit *einem* Aufrufer bleibt dabei grün, ein Test mit *zweien* muss rot werden. Das ist Regel 5 auf diese Regel angewandt: Der Einzelaufruf-Test hat einen zweiten Grund, grün zu sein, nämlich dass er die Bedingung gar nicht herstellt. Für `server/discover`: den RPC tatsächlich aufrufen — eine grüne Tool-Suite beweist nichts, weil sie ihn nie ruft. Für den Ablauf: einen Handle mit abgelaufenem Zeitstempel einreichen und die Ablehnung behaupten.

## Regel 9 — Die Adresse steht neu aussen auf dem Umschlag, und beide Seiten müssen dasselbe lesen

Streamable HTTP verlangt auf jedem POST zwei Header: `Mcp-Method` mit der JSON-RPC-Methode und `Mcp-Name` mit dem Namen des adressierten Tools, Prompts oder der Ressource. Weichen Header und Body voneinander ab, ist die Antwort `HeaderMismatchError` — JSON-RPC-Code **`-32020`**.

Der Gewinn ist offensichtlich: Bisher musste jede Instanz zwischen Client und Server den Body parsen, um zu wissen, was durchläuft — ein Gateway, das nur ein bestimmtes Werkzeug durchlassen soll, ein Rate-Limiter mit Grenzen je Tool, ein Logpfad, der Methoden zählt. Jetzt steht das im Klartext an der Anfrage.

**Und genau daraus entsteht der Angriff.** Wenn eine Zwischenschicht am Header entscheidet und der Server am Body, entscheiden zwei Instanzen über zwei verschiedene Anfragen. Ein Client schickt `Mcp-Name: search_datasets` im Header und `delete_record` im Body: Das Gateway erlaubt, der Server führt aus. Die Header sind deshalb keine Metadaten — **die Prüfung ihrer Übereinstimmung ist eine Sicherheitsgrenze**, und sie muss serverseitig stattfinden, weil nur dort beide Seiten vorliegen.

```python
# ✗ Header als Metadatum behandelt — geloggt, geroutet, nie gegen den Body gehalten
log.info("mcp.request", method=request.headers.get("Mcp-Method"))
return await dispatch(body["method"], body["params"])

# ✓ Übereinstimmung ist eine Vorbedingung, und ein fehlender Header ist keine Ausnahme
declared_method = request.headers.get("Mcp-Method")
declared_name = request.headers.get("Mcp-Name")
if declared_method is None or declared_name is None:
    raise HeaderMismatchError(-32020, "Mcp-Method/Mcp-Name required")
if (declared_method, declared_name) != (body["method"], _addressed_name(body)):
    raise HeaderMismatchError(-32020, "header does not match body")
return await dispatch(body["method"], body["params"])
```

Der fehlende Header ist der Teil, den man am ehesten weglässt, und der die Kontrolle aushebelt: Wer nur vergleicht, *wenn* beide Header da sind, hat eine Prüfung gebaut, die man durch Auslassen umgeht. Dieselbe Form wie die «present»-Klausel in Regel 12.

**Daraus folgt die zweite Doku-Pflicht dieses Skills** — Schwester der `MCP_HOST`-Pflicht aus Regel 2. Im README gehört, **auf welche Header-Werte das Deployment routet und limitiert**: Ein Gateway, das auf `Mcp-Name` allow-listet, ist Teil der Sicherheitsarchitektur des Servers, steht aber nirgends in seinem Code. Wer das nicht aufschreibt, hat eine Kontrolle, die niemand pflegt, weil niemand von ihr weiss.

**Nachweis:** Drei Fälle, und der dritte ist der, den man vergisst. (1) Header und Body stimmen überein → durchgelassen, der positive Zwilling. (2) `Mcp-Name` nennt ein anderes Tool als der Body → `-32020`. (3) Header fehlen ganz → ebenfalls `-32020`, nicht durchgelassen. Der Mutationstest: den Vergleich durch ein reines Logging ersetzen — Fall 2 und 3 müssen rot werden. Wird nur Fall 2 rot, prüft niemand die Auslassung.

## Regel 10 — Legacy HTTP+SSE hat jetzt ein Datum: 2027-07-28

Der HTTP+SSE-Transport ist seit `2025-03-26` deprecated. Was `2026-07-28` ändert, ist nicht die Empfehlung, sondern ihre Verbindlichkeit: Der Pfad steht unter der Feature-Lifecycle-Politik und trägt damit den formalen Zustand **Deprecated** mit einem Fenster von mindestens zwölf Monaten — frühester Entfernungstermin **`2027-07-28`**. Dieselbe Frist gilt für Roots, Sampling und Logging.

**Warum es das braucht, obwohl «deprecated seit 2025-03» seit anderthalb Jahren im Raum steht.** Genau deswegen. Eine Empfehlung ohne Termin erzeugt keinen Vorgang, sondern einen Kompatibilitätspfad, den niemand abschaltet, weil er niemanden stört.

Der Legacy-Pfad ist dabei nicht neutral. Er ist ein zweiter Netzweg mit eigener Verdrahtung — und die Erfahrung aus Regel 3 ist, dass der zweite Pfad die Härtung des ersten nicht mitbekommt. Ein Server, dessen Streamable-HTTP-Endpunkt Host-Allow-Listing (Regel 4) und Header-Prüfung (Regel 9) durchsetzt, während der SSE-Endpunkt daneben weiterläuft, hat beides nicht. Auf `2026-07-28` verschärft sich das zusätzlich: Dort ist auch der GET-Endpunkt weg, ein verbliebener SSE-Pfad spricht also ein Protokoll, das der Server nach eigener Aussage nicht mehr führt.

**Erkennungsrezept — drei Orte, weil jeder für sich sauber sein kann, während ein anderer es nicht ist:**

1. **Code.** `create_sse_app`, `transport="sse"`, ein Mount auf `/sse`, ein `sse_app()`-Aufruf. Grep über das ganze Paket, nicht nur über das Servermodul.
2. **Start.** Was die Plattform tatsächlich startet: `[project.scripts]`, Procfile, `CMD`, die Argv im Deployment. Ein im Code vorhandener Zweig, den nie jemand aufruft, ist etwas anderes als ein Zweig, den das Deployment wählt — und umgekehrt kann eine Konfiguration einen Transport wählen, den man im Code übersehen hat.
3. **Draht.** Ein GET auf den Endpunkt. Öffnet sich ein Event-Stream oder kommt ein `Mcp-Session-Id` zurück, ist der Pfad live — unabhängig davon, was der Code nahelegt. Nur das hier ist ein Beweis; die ersten beiden sind Indizien.

```python
# ✗ «bleibt für Kompatibilität» — ohne Datum, ohne Signal, unbefristet
if settings.transport == "sse":
    uvicorn.run(mcp.create_sse_app(...), host=..., port=...)

# ✓ befristet, sichtbar, und bis zur Entfernung gleich hart verdrahtet wie der Rest
if settings.transport == "sse":
    log.warning(
        "transport.legacy_sse_selected removal_earliest=2027-07-28 — "
        "migrate to streamable-http; this path speaks a protocol 2026-07-28 dropped",
    )
    uvicorn.run(
        mcp.create_sse_app(host=..., port=..., transport_security=policy), ...
    )
```

**Angewandtes Rezept, gemessen: `zurich-opendata-mcp` v0.7.0.** Alle drei Orte negativ — kein `create_sse_app` und kein `transport="sse"` im Paket; ein einziger Netzpfad, `mcp.run(transport="streamable-http", host=…, port=…, transport_security=…)` in `src/zurich_opendata_mcp/server.py`; kein Deploy-Manifest im Repo, das einen zweiten Pfad starten könnte. So sieht ein sauberer Befund aus. Das ist der nützlichere Teil des Rezepts: Wer nur den positiven Fall kennt, weiss nicht, wann er fertig ist. Den positiven Fall liefert der Dreier-Zyklus unten — dort stand der SSE-Pfad neben den beiden anderen und bekam die Härtung nicht mit.

**Nachweis:** Die Abwesenheit ist beweisbar zu machen, nicht bloss zu behaupten — ein Test, der scheitert, sobald wieder eine SSE-App gebaut wird. Solange der Pfad existiert, gilt die Mutation aus Regel 3 auch für ihn: `transport_security` einzeln daraus entfernen, mindestens ein Test muss rot werden. Und der Beweis der Abschaltung ist der Draht, nicht der Code: ein GET, das keinen Stream öffnet. Achtung auf den zweiten Grund im Sinne von Regel 5 — ein GET, das scheitert, weil der Server gar nicht läuft, beweist nichts; der positive Zwilling auf dem Streamable-HTTP-Endpunkt muss danebenstehen.

## Regel 11 — MRTR: der Server antwortet und hält nichts offen — dafür läuft die Bearbeitung mehrfach

Bis `2025-11-25` konnte ein Server mitten in der Bearbeitung selbst einen Request an den Client stellen: `roots/list`, `sampling/createMessage`, `elicitation/create`. `2026-07-28` streicht das ersatzlos und setzt **MRTR** an seine Stelle:

1. Der Server merkt, dass ihm etwas fehlt, und **antwortet** — `resultType: "input_required"` plus ein Feld `inputRequests`, das benennt, was er braucht.
2. Der Client beschafft es und **wiederholt den ursprünglichen Request**, diesmal mit `inputResponses`.
3. Der Server bearbeitet ihn erneut, jetzt vollständig.

**Die Umkehrung, die alles daran schwierig macht:** Aus einem Dialog *innerhalb* einer Bearbeitung wird eine Bearbeitung, die **von vorn läuft**. Alles vor dem Rückfragepunkt passiert bei jedem Retry noch einmal. Damit wandert das Thema aus «Bedienoberfläche» in «Korrektheit»: Ein Tool, das erst etwas anlegt, dann nachfragt und im Retry wieder von vorn beginnt, legt es zweimal an.

```python
# ✗ Nebenwirkung vor dem Rückfragepunkt — jeder Retry wiederholt sie
async def submit(params):
    record = await api.create(params)              # läuft beim Retry erneut
    if params.confirm is None:
        return {"resultType": "input_required", "inputRequests": [CONFIRM]}
    return await api.finalise(record.id)

# ✓ erst vollständig werden, dann wirken — und die Wirkung trägt einen Schlüssel
async def submit(params):
    if params.confirm is None:
        return {
            "resultType": "input_required",
            "inputRequests": [CONFIRM],
            "requestState": _mint_state(params),   # Korrelation ohne Sitzung
        }
    return await api.create(params, idempotency_key=_key_from(params.request_state))
```

**Korrelation ohne Sitzung.** `elicitationId` und `notifications/elicitation/complete` sind entfernt. Wer einen ausserhalb laufenden Vorgang über Retries hinweg wiedererkennen muss, kodiert seine eigene Kennung in `requestState` — einen anderen Kanal gibt es nicht mehr. Es gelten dieselben Eigenschaften wie für Handles in Regel 8: server-geprägt, opak, mit Ablauf.

**Keine hängenden Streams.** Der Server *antwortet* und schliesst ab. Wer stattdessen die Verbindung offenhält und auf die Antwort des Clients wartet, hat das alte Modell nachgebaut, und zwar in der Form, die Regel 7 beschreibt: Der Fehler äussert sich nicht als roter Test, sondern als stehende Suite. Der Retry kann ausserdem **nie kommen** — ein Client ist zu nichts verpflichtet. Was vor dem Rückfragepunkt reserviert wurde, muss deshalb ohne ein Abschlussereignis wieder freigegeben werden, genau wie ein Handle ohne Ablauf in Regel 8 eines ist.

**Nachweis:** Den Retry **tatsächlich ausführen** — Aufruf ohne Eingabe, dann derselbe Aufruf mit `inputResponses` — und behaupten, dass die Nebenwirkung **einmal** eingetreten ist. Der zweite Grund im Sinne von Regel 5: Ein Test, der nur den Rückgabewert des zweiten Aufrufs prüft, ist auch bei doppelter Nebenwirkung grün; behauptet wird die Wirkung, nicht die Antwort. Der Mutationstest: den Idempotenzschlüssel entfernen — der Zwei-Aufruf-Test muss rot werden, der Ein-Aufruf-Test bleibt grün. Und die Suite läuft unter Timeout (Regel 7), sonst zeigt sich ein offengehaltener Stream als Flake statt als Befund.

## Regel 12 — Auth-Härten, und warum dieses Portfolio hier einen Negativbefund einträgt

Drei Änderungen an derselben Stelle, die nur zusammen einen behebbaren Zustand ergeben:

- **RFC-9207-`iss`-Validierung.** Autorisierungsserver **SOLLEN** einen `iss`-Parameter in die Authorization-Response legen; die einlösende Partei **MUSS** ihn gegen den erfassten Issuer prüfen, bevor sie den Code einlöst. Der Angriff dahinter ist Mix-up: Ein Code, der bei Server A ausgestellt wurde, wird auf den Callback von Server B umgeleitet und dort mit *dessen* Zugangsdaten eingelöst.
- **CIMD statt DCR.** Dynamic Client Registration ist abgekündigt zugunsten von Client ID Metadata Documents: Der Client veröffentlicht seine Metadaten unter einer URL, und diese URL **ist** die `client_id`. DCR bleibt für Autorisierungsserver, die CIMD nicht können — und wer dort bleibt, muss `application_type` setzen, sonst defaultet OpenID Connect auf `web` und ein nativer Client mit `http://127.0.0.1:…` wird abgelehnt.
- **Issuer-gebundene Credentials.** Persistierte Zugangsdaten werden nach Issuer-Identifier geschlüsselt, nie bei einem anderen Autorisierungsserver wiederverwendet, und beim Wechsel wird neu registriert. Das ist die Speicherseite desselben Angriffs, dessen Netzseite die `iss`-Prüfung abwehrt.

```python
# ✗ state geprüft, iss ignoriert — und die Credentials liegen flach in der Konfiguration
if callback.state != recorded.state:
    raise AuthError("state mismatch")
token = await httpx.post(recorded.token_endpoint, data={
    "code": callback.code, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
})

# ✓ iss gehört zur Vorbedingung, auch wenn er fehlt — und die Credentials hängen am Issuer
if callback.state != recorded.state:
    raise AuthError("state mismatch")
if callback.iss is None and recorded.metadata.iss_parameter_supported:
    raise AuthError("iss absent although this issuer advertises it")
if callback.iss is not None and callback.iss != recorded.issuer:
    raise AuthError("iss mismatch — this code was not issued by the recorded issuer")
creds = CREDENTIALS_BY_ISSUER[recorded.issuer]      # nie über Issuer hinweg wiederverwendet
```

**Die «present»-Klausel ist die Falle.** Die Pflicht gilt für einen *vorhandenen* `iss`. Wer nur prüft, wenn der Parameter da ist, erfüllt den Buchstaben und lässt sich angreifen, indem der Parameter weggelassen wird. Was der Autorisierungsserver kann, steht in seinen Metadaten (`authorization_response_iss_parameter_supported`) — es ist also bekannt und muss nicht geraten werden. Dieselbe Auslassungsfalle wie beim fehlenden Header in Regel 9.

**Der Negativbefund, ausgeschrieben statt weggelassen.** Für das Swiss-Public-Data-Portfolio ist diese Regel **derzeit nicht anwendbar**, und zwar aus einem benennbaren Grund: Die Server sind read-only, führen `auth_model: none` und lösen keinen Authorization Code ein — es gibt keine einlösende Partei, die `iss` prüfen könnte, und keine persistierten Client-Credentials, die man nach Issuer schlüsseln müsste. Die einzige eingehende Kontrolle bleibt die Host-Allow-List aus Regel 4.

Das steht hier ausgeschrieben, weil ein weggelassener Abschnitt von einem übersehenen nicht zu unterscheiden ist — dieselbe Logik, aus der Regel 5 besteht: Grün, weil nichts geprüft wurde, sieht aus wie Grün, weil alles stimmt. Und weil die Bedingung, die den Befund aufhebt, präzise ist: Die CIMD- und Issuer-Bindungspflicht greift, **sobald ein Server irgendein Auth-Modell trägt**; die `iss`-Pflicht, **sobald er als OAuth-Proxy auftritt**. Ab dem ersten Server mit einer Zugangsberechtigung ist der Satz aus Regel 4 — «ein Auth-Token sagt nur, *wer* fragt» — nicht mehr die ganze Auth-Geschichte.

**Nachweis:** Zwei Negativtests, und beide brauchen einen korrekten `state`, sonst prüfen sie die falsche Kontrolle (Regel 5): (1) ein Code mit fremdem `iss` wird abgelehnt; (2) ein Code **ohne** `iss` von einem Autorisierungsserver, dessen Metadaten ihn ankündigen, wird ebenfalls abgelehnt. Dazu der positive Zwilling mit passendem `iss`. Der Mutationstest: die `iss`-Prüfung entfernen — beide müssen rot werden; wird nur der erste rot, ist die Auslassung ungeprüft. Für den Negativbefund selbst gilt ein anderer Nachweis: Er ist an `auth_model` gebunden und muss neu bewertet werden, sobald das Feld eines Servers nicht mehr `none` ist.

## Regel 13 — Ein Guard prüft nicht, was vor ihm abgezweigt wurde

Diese Regel gehört inhaltlich zum Beweisblock 5–7 und steht trotzdem hier hinten, aus demselben Grund wie 8–12: angehängt, nicht eingeschoben. Die Regeln 5–7 sorgen dafür, dass ein Guard trägt. Diese sagt, **wen er trägt**: Ab dem Merge-Commit gilt er, und nur dort vorwärts. Zwei Mengen liegen ausserhalb, beide unsichtbar, weil sie ein grünes CI-Signal zeigen:

- **der Stand, der schon auf `main` liegt.** Der Guard entstand, weil etwas falsch war — geprüft hat er bisher nur den PR, der ihn eingeführt hat.
- **jeder Zweig, der vor dem Merge geschnitten wurde.** Dessen CI kennt den Guard nicht. Er wird gemergt, ohne ihn je gelaufen zu sein.

Der Schaden, der zu dieser Regel führte: Ein Versions-Sync-Check — Badge gegen oberste CHANGELOG-Überschrift — landete auf `main`, nachdem der Release-Branch für `0.20.0` bereits geschnitten war. Dessen Pipeline lief ihn nie, der Release ging durch, und danach prüfte niemand `main` nach. Die README-Badges waren **zwei Releases lang falsch** — gedeckt von einem Guard, der genau dafür geschrieben worden war und in der Zwischenzeit auf jedem grünen Lauf mit draufstand.

Das mechanische Stück ist ein Trigger:

```yaml
# ✗ der Guard sieht ausschliesslich, was nach ihm kommt
on:
  pull_request:

# ✓ er läuft auch auf dem Stand, den er nie geprüft hat
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:        # damit man ihn nach dem Merge einmal von Hand anwirft
```

Der Rest ist Handarbeit und steht in keinem YAML: **nach dem Merge einmal gegen `main` laufen lassen und hinsehen** — nicht annehmen, dass es gutgeht, weil der einführende PR grün war. Und die offenen Zweige, die vorher geschnitten wurden, auf `main` nachziehen; sonst mergen sie an dem Guard vorbei, der sie prüfen sollte.

Für die Kontrollen dieses Skills ist das der Normalfall, nicht der Sonderfall: Der portgenaue Allow-List-Test entsteht in dem Repo, das gerade den 421 hatte; der Zwei-Aufrufer-Test aus Regel 8 in dem, das gerade migriert wird. Die übrige Flotte läuft sie später — oder nie. Es ist dieselbe Form wie beim verschachtelten Server unten in «Woher diese Regeln stammen»: Die Abdeckung hat eine Grenze, die niemand absichtlich gezogen hat, und sie fällt niemandem auf, weil ausserhalb davon nichts rot wird.

**Die Grenze ist nicht nur zeitlich, sondern auch räumlich.** Ein Guard liest Dateien; alles, was **nicht** im Repo liegt, ist damit ausserhalb — GitHub-Description und -Topics, die Beschreibung im Registry-Eintrag, das Deployment-Manifest nebenan, der Text im Marketplace. Diese Stellen tragen oft genau die Behauptung, die im Repo geprüft wird, und keine Prüfung erreicht sie. Nachgemessen: Als dieses Repo von sieben auf zwölf Regeln ging, blieb seine GitHub-Description auf «twelve», während `SKILL.md`, beide READMEs und `reference/patterns.py` von drei Guards auf dreizehn gehalten wurden — der Zählguard war korrekt und deckte den Ort nicht ab, an dem die Zahl zuerst gelesen wird.

Solche Stellen lassen sich prüfen, sie brauchen nur einen Aufruf statt eines Dateilesers. Zwei Eigenschaften sind dabei tragend: Der Vergleich zieht seinen Sollwert aus derselben Quelle wie die übrigen Guards, statt ihn ein zweites Mal zu deklarieren — sonst hat man zwei Wahrheiten, die auseinanderlaufen. Und ein fehlgeschlagener Abruf ist ein **Fehler**, kein Skip: Ein Check, der bei einem Netzproblem grün durchläuft, meldet «bestanden», wo «nicht gelaufen» richtig wäre.

**Nachweis:** Regel 6 auf den Guard selbst angewandt, aber auf `main` statt im PR: die Verletzung, gegen die er geschrieben wurde, dort herstellen und den Lauf ansehen. Wird er nicht rot, war jeder bisherige grüne Lauf ein «nicht gelaufen» und kein «bestanden» — den Unterschied misst [`OPS-005`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/OPS-005.md). Dazu die Zweige benennen, die den Guard nicht kennen: `git branch -r --no-contains <merge-sha>` zählt sie auf. Diese Liste ist der Umfang der Nacharbeit; solange sie nicht leer ist, ist der Guard eingeführt, aber nicht durchgesetzt. Für die räumliche Hälfte: die Behauptung, die der Guard prüft, einmal ausserhalb des Repos suchen — Description, Topics, Registry-Eintrag — und nachsehen, ob sie dort dasselbe sagt. Was dort steht und nicht geprüft wird, ist eine Kopie, die niemand pflegt.

---

## Checkliste vor dem Release eines netzgebundenen Servers

**Der Server (Regeln 1–4)**

- [ ] Kein `mcp.settings.<feld> = ...` mehr im Code; der Bind geht als Kwargs an `run()`
- [ ] Annotations werden snake_case gelesen; Drahtformat gegen beide Schreibweisen verglichen
- [ ] TypeScript-Server nicht «mitmigriert» — dort bleibt camelCase korrekt
- [ ] `fastmcp` (PyPI) und `mcp.server.fastmcp` (SDK) nicht verwechselt; `fastmcp` 3.x pinnt `mcp<2.0`
- [ ] Versions-Cap an beiden Enden verankert (`>=2.0.0,<3`), auch in verschachtelten Subprojekten
- [ ] Cap und Lock im selben Commit — die installierte Version gemessen, nicht die Deklaration gelesen
- [ ] Jede ASGI-Factory erhält Host **und** Port aus derselben Konfiguration wie `main()`
- [ ] uvicorn-`--factory`-Pfad liest den Bind selbst; README begründet, warum `MCP_HOST`/`MCP_PORT` neben den Flags nicht redundant sind
- [ ] Auf einer PaaS wird die Allow-List aus dem injizierten `$PORT` zusammengesetzt, nicht aus einem Literal
- [ ] Jeder App-bauende Pfad (eigener Builder, SDK-`run()`, SSE) bekommt dieselbe Transport-Security
- [ ] Allow-List portgenau, Loopback drin, CORS-Origins aufgenommen, kein `*`
- [ ] Fail-open auf Nicht-Loopback ist sichtbar — Startwarnung im Log

**Die Stateless-Welt (Regeln 8–12)**

- [ ] Kein `initialize`-Handshake, kein `Mcp-Session-Id`, keine serverseitige Sitzungstabelle (Regel 8)
- [ ] Kein prozesslokaler Zustand, der über etwas adressiert wird, das es nicht mehr gibt (Regel 8)
- [ ] Handles sind server-geprägt, opak, im Tool-Schema sichtbar und laufen ab (Regel 8)
- [ ] `server/discover` implementiert und **aufgerufen** getestet — MUSS für Server, MAY für Clients (Regel 8)
- [ ] `Mcp-Method`/`Mcp-Name` serverseitig gegen den Body geprüft; fehlender Header wird abgewiesen, nicht übersprungen (Regel 9)
- [ ] README nennt, auf welche Header-Werte das Deployment routet und limitiert (Regel 9)
- [ ] Legacy-SSE-Pfad: Erkennungsrezept über Code, Start und Draht gelaufen; Befund festgehalten (Regel 10)
- [ ] Existiert der Pfad noch, trägt er das Datum `2027-07-28` in einer Startwarnung und dieselbe Härtung wie der Rest (Regel 10)
- [ ] MRTR: `input_required` beendet die Bearbeitung, der Server hält keinen Stream offen (Regel 11)
- [ ] Nebenwirkungen liegen hinter dem Rückfragepunkt oder tragen einen Idempotenzschlüssel; der Retry ist getestet (Regel 11)
- [ ] Reserviertes wird ohne Abschlussereignis wieder frei — kein Retry ist garantiert (Regel 11)
- [ ] Auth: `iss` geprüft inklusive Auslassung, CIMD statt DCR, Credentials nach Issuer geschlüsselt — **oder** der Negativbefund ist mit `auth_model` begründet festgehalten (Regel 12)

**Der Beweis (Regeln 5–7 und 13, gilt für alle Regeln)**

- [ ] Zu jedem Negativtest die zweite mögliche Ursache benannt und ausgeschlossen (Regel 5)
- [ ] Tragender Fall: richtiger Hostname, **falscher Port** — ein fremder Hostname allein beweist nichts (Regel 5)
- [ ] Jeder Negativtest hat seinen positiven Zwilling (Regel 5)
- [ ] Kein Test stellt selbst die Bedingung her, unter der der Fehler nicht auftreten kann (Regel 6)
- [ ] Getestet wird die Naht, an der der Wert reist, nicht die Funktion, die ihn schon hat (Regel 6)
- [ ] Jede Mutation vor dem Testlauf per Diff belegt — eine Ersetzung, die nichts trifft, sieht aus wie ein überlebender Mutant (Regel 6)
- [ ] Mutationstabelle im PR: jede Kontrolle einzeln entfernt, jede Zeile mit mindestens einem roten Test (Regel 6)
- [ ] Die Stateless-Kontrollen sind mit **zwei** Aufrufern getestet — ein Aufrufer ist in beiden Zuständen grün (Regeln 5, 8)
- [ ] Gegen den echten ASGI-Stack geprüft (`TestClient`), nicht gegen blankes `ASGITransport` (Regel 7)
- [ ] Patch-Ebene im ganzen Repo einheitlich — Instanz oder Klasse, nicht gemischt (Regel 7)
- [ ] Kein `setattr` auf ein importiertes Fremdmodul; gepatcht wird ein Name, den dieses Repo besitzt (Regel 7)
- [ ] Jede `autouse`-Fixture gegen die Tests gehalten, die sie nicht bestellt haben — nimmt der Ersatz die Dauer weg oder auch die Übergabe an den Event-Loop? (Regel 7)
- [ ] Jeder Zweig-Test behauptet, welcher Zweig lief (Regel 7)
- [ ] Suite läuft unter Timeout; jeder Zweig-Test zusätzlich einzeln **und** in der vollen Suite (Regel 7)
- [ ] Jeder neue Guard läuft auch auf `main`, nicht nur auf Pull Requests — und ist dort nach dem Merge einmal angesehen worden (Regel 13)
- [ ] Zweige, die vor dem Merge des Guards geschnitten wurden, auf `main` nachgezogen (`git branch -r --no-contains <merge-sha>`) (Regel 13)
- [ ] Behauptungen ausserhalb des Repos — GitHub-Description, Topics, Registry-Eintrag — gegen dieselbe Quelle geprüft wie im Repo; fehlgeschlagener Abruf ist ein Fehler, kein Skip (Regel 13)

## Woher diese Regeln stammen

**Die Regeln 1–7 stammen aus drei Pull Requests desselben Zyklus (2026-07):**

| PR | Ausgangslage |
|---|---|
| [`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29) | Migration 1.x → 2.x, als **letzter Server im Portfolio** auf der alten Major. Echter Startfehler plus 421 im HTTP-Pfad, vor dem Fix gegen den echten ASGI-Stack reproduziert |
| [`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51) | Kein 421-Bug — der Bind kam korrekt an. Es fehlte die Möglichkeit, überhaupt zu sagen, unter welchen Namen der Server erreichbar sein darf |
| [`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25) | Kein 421-Bug. Egress-Allow-List vorhanden, eingehend nichts — und der Port fiel auf dem Weg zum App-Builder heraus |

Sechs Dinge daran sind übertragbar:

1. **Nur einer der drei war ein Bug.** Die anderen zwei waren eine fehlende Kontrolle — für das gedachte Deployment vertretbar begründet, aber wer den Server anders betreibt, hatte keinen Weg, sich einzuklinken. Fehlende Konfigurierbarkeit fällt in keinem Test auf, weil nichts falsch ist.
2. **Grüne Tests und sauberer Linter, und der Prozess startet nicht.** Tool-Tests laufen über stdio und berühren den Transport-Pfad nie. Der Fehler wartet auf das erste HTTP-Deployment.
3. **Der letzte Server auf der alten Major war der, den keine Liste kannte.** `openparldata-mcp` liegt **verschachtelt** in einem anderen Repo und hat eine eigene `pyproject.toml`. Damit ist er durch jede Aufzählung gefallen, die Top-Level-Repos listet — und die Abhängigkeits-Constraint des Elternprojekts hat ihn nie erfasst. Ein Inventar, das Repos zählt statt Deployment-Einheiten, übersieht genau die Fälle, die am längsten unmigriert bleiben.
4. **Der Mutationstest hat in zwei von drei Repos die Tests korrigiert, nicht den Code** — daraus Regel 6. Eine Kontrolle, deren Entfernung nichts rot macht, ist unbewiesen.
5. **Ein Test, der hängt statt zu scheitern, ist schlimmer als keiner** — daraus Regel 7. Dass er *hängt* und nicht *scheitert*, ist der Regelfall: Ohne Kontrolle wird die verbotene Anfrage zugelassen, und zugelassen heisst bei einem Stream warten.
6. **Der Testaufbau selbst ist eine Fehlerquelle.** Ein blanker `httpx.ASGITransport` liefert auf jede Anfrage 500, weil er den App-Lifespan nie ausführt. Wer den 500er für einen Befund hält, debuggt den falschen Code.

**Die Regeln 8–12 haben keine Narbe, sondern ein Datum.** Das ist ein Unterschied, der hier ausgeschrieben gehört, weil der Contributing-Abschnitt dieses Repos von jeder neuen Regel einen konkreten Schaden verlangt. Ihr Anlass ist die Spec-Revision `2026-07-28`: ein externes, datiertes Ereignis, dessen Änderungen nicht plausibel klingen, sondern nachlesbar sind. Was sie mit den ersten sieben teilt, ist die Form — jede trägt ein ✗/✓-Paar und einen Nachweis, und jeder Nachweis benennt die Mutation, unter der er rot wird.

Was am Portfolio dazu **gemessen** ist und nicht angenommen: Der Legacy-`initialize`-Handshake cappt unter mcp 2.x weiter bei `2025-11-25`, während derselbe Prozess daneben einen per-request-Umschlag bedient, der `2026-07-28` erreicht (festgehalten in `zurich-opendata-mcp`s `pyproject.toml`). Und das Erkennungsrezept aus Regel 10, an demselben Server angewandt, kommt an allen drei Orten negativ zurück. Beides sind Messungen an einem Repo, keine Verallgemeinerungen — mehr behaupten die Regeln an dieser Stelle auch nicht.

**Regel 13 und drei Nachträge stammen aus dem Betrieb der Kette selbst (2026-08).** Die ersten drei haben untereinander dieselbe Form wie Punkt 3 oben, der verschachtelte Server: Etwas ist eingeführt, aber nicht dort angekommen, wo es hätte wirken müssen — und weil ausserhalb der Reichweite nichts rot wird, sieht der Zustand von innen aus wie Erfolg.

- **Regel 13.** Ein Versions-Sync-Check landete auf `main`, nachdem der `0.20.0`-Release-Branch geschnitten war. Dessen CI kannte ihn nicht, danach prüfte niemand `main` nach, und die README-Badges waren zwei Releases lang falsch.
- **Regel 6, der Diff-Schritt.** Eine Ersetzung lief ins Leere, weil das gesuchte Literal im umbrochenen Text über eine Zeilengrenze fiel. Die Datei blieb unverändert, die Suite grün — und das las sich als überlebender Mutant.
- **Regel 1, die Lock-Hälfte.** Der Auslöser des SDK-Major-Sprungs war ein unbeschränkter Resolve. Die Bounds danach in `pyproject.toml` zu setzen genügt nicht: Ohne neu aufgelösten Lock installiert das Deployment weiter, was vorher galt — was zu diesem Zeitpunkt auf einer `main` des Portfolios genau so lag.
- **Regel 7, der Fall (d).** Eine `autouse`-Fixture ersetzte `asyncio.sleep` im Modul `asyncio` selbst und nahm damit jedem Test im Prozess die Übergabe an den Event-Loop. Das ist die Spiegelung der drei Punkte darüber: Nicht die Reichweite war zu klein, sondern zu gross. Rot wird trotzdem nichts — der entschärfte Test hat keinen Gegenstand mehr, an dem er scheitern könnte. Hier ging er rot, weil er die Verschränkung direkt behauptete; das ist Glück und keine Eigenschaft der Fixture.

Regel 13 hat sich beim Schreiben dieses Abschnitts selbst bestätigt: Der Zweig, auf dem sie entstand, war vor dem Merge von `2.0.0` geschnitten. Sieben Regeln wurden zwölf, während er offen lag — und die neue Regel trug bis zum Rebase die Nummer 8, die inzwischen vergeben war.

**Zur Benennung:** Zwei der drei PRs führen im Titel `SEC-005`, implementieren aber die **eingehende** Kontrolle — im Audit-Katalog `SEC-024`. `SEC-005` ist die ausgehende Richtung (DNS-Pinning gegen TOCTOU). Zwei Angriffe, ein Name: Wer «DNS-Rebinding» ohne Richtungsangabe zitiert, meint mit einiger Wahrscheinlichkeit den anderen.

## Verwandte Skills

Fünf Repos, ein Lebenszyklus — gemeinsames GitHub-Topic [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain).

| Phase | Repo | Frage, die es beantwortet |
|---|---|---|
| vor dem Bau | [`mcp-data-source-probe`](https://github.com/malkreide/mcp-data-source-probe-skill) | Taugt die Quelle, und was hat sie? |
| im Bau | [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill) | Liefert er, was die Quelle hat? Dieselbe stille Fehlerklasse eine Schicht höher — nicht ob eine Antwort kommt, sondern was sie enthält |
| im Bau | **`mcp-transport-hardening`** | **Dieser Skill:** kommt er hoch, weist er richtig ab, bleibt er zustandslos? |
| nach dem Bau | [`mcp-audit`](https://github.com/malkreide/mcp-audit-skill) | Hält er gegen den Katalog? Die Zuordnung Regel → Check steht unten |
| im Betrieb | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Hält er morgen noch? |

Daneben, nicht Teil der Kette: `mcp-builder` — generische Bauanleitung von Anthropic, wird ergänzt und nicht ersetzt. Fremdes Repo, kann das Topic nicht tragen.

### Was hier steht, was der Katalog prüft, was der Auditor live exerziert

Die drei Repos berühren dieselben Gegenstände und stellen verschiedene Fragen. Ohne diese Trennung entsteht Duplikation, und Duplikation altert auseinander:

| Gegenstand | **Hier** (im Bau) | **`mcp-audit`** (nach dem Bau) | **`mcp-continuous-auditor`** (im Betrieb) |
|---|---|---|---|
| Bind, Verdrahtung, Host-Allow-List | Wie der Bind bis in jede App-Factory reist und woran ein Test rot wird | `ARCH-013`, `SEC-024`: existiert die Kontrolle | `transport_boot_probe.py` startet den Server über **seinen eigenen** Entrypoint und spricht MCP mit ihm |
| Stateless (Regel 8) | Die Naht, an der prozesslokaler Zustand still geteilt wird, und der Zwei-Aufrufer-Test | `ARCH-015`, `ARCH-016`, `ARCH-017` | `spec_probe.py`: `code`, `artifact`, `portfolio`, `wire` gegeneinander — Status `SPEC_DRIFT` |
| Header-Pflicht (Regel 9) | Der serverseitige Vergleich als Sicherheitsgrenze, inklusive Auslassungsfall | `SCALE-008`; `SEC-027` für `x-mcp-header` | — |
| Legacy-SSE (Regel 10) | Erkennungsrezept über drei Orte, Migrationspfad, Frist | `SCALE-009`, `SCALE-010` | `spec_probe.py`: Status `LEGACY_TRANSPORT` am Draht |
| MRTR (Regel 11) | Idempotenz über Retries und der Hänger, den es neu erzeugt | `HITL-006` | — |
| Auth (Regel 12) | Die Auslassungsfalle und der begründete Negativbefund | `SEC-025`, `SEC-026` | — |

Faustregel: **Hier steht, wie man es verdrahtet und woran man sieht, dass es trägt. Der Katalog fragt, ob es da ist. Der Auditor fragt, ob es heute noch da ist.** Wer eine Zeile in zwei Repos schreibt, hat zwei Stellen, die auseinanderlaufen können.

**Was dieser Skill bewusst nicht abdeckt**, obwohl `2026-07-28` es ändert: `resultType` auf allen Results ([`ARCH-018`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-018.md)), das Fristdatum für Roots, Sampling und Logging ([`ARCH-019`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-019.md)), `ttlMs`/`cacheScope` und deterministische Reihenfolge auf List- und Read-Ergebnissen ([`ARCH-020`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-020.md)), und die Deklaration versionierter Extensions ([`ARCH-021`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-021.md)). Das sind Fragen an die *Form der Antwort*, nicht an den Transport — sie gehören in den Katalog und, was `ttlMs` betrifft, in die Nachbarschaft von `mcp-data-fidelity`. Sie hier zu wiederholen würde den Skill verlängern, ohne dass er etwas entscheidet.

### Welche Regel welcher Check ist

Stand des Katalogs: [`mcp-audit`](https://github.com/malkreide/mcp-audit-skill) v2.0.0, 112 Checks in zwölf Kategorien auf **zwei Spec-Baselines**. Die Zuordnung ist durch Lesen der Check-Dateien belegt, nicht aus den Titeln geschlossen; die Lücken sind benannt, statt sie durch eine ungefähre Zuordnung zu verdecken:

| Regel | Check |
|---|---|
| 1 — SDK-Major-Sprung | [`SDK-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SDK-006.md) — «SDK-Major-Migration vollständig abgeschlossen»; für den Cap zusätzlich [`DEP-001`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/DEP-001.md) |
| 2 — `host` als Saat der Allow-List | **kein Check.** [`SEC-016`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SEC-016.md) liegt daneben, adressiert aber den umgekehrten Fall: `0.0.0.0` als *unbeabsichtigten* Bind (NeighborJack). Regel 2 setzt ein gewolltes `0.0.0.0`-Deployment voraus und fragt, ob der Bind die App erreicht |
| 3 — jeder Pfad identisch verdrahtet | [`ARCH-013`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-013.md) — «Alle Netz-Transportpfade identisch verdrahtet» |
| 4 — eingehende Host-Allow-List | [`SEC-024`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SEC-024.md); [`SEC-005`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SEC-005.md) ist die ausgehende Gegenrichtung |
| 5 — der Negativtest muss aus dem eigenen Grund rot werden | **teilweise.** [`DRIFT-003`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/DRIFT-003.md) — «Kein Test-Assert wird vom Degradationspfad erfüllt» — ist dieselbe Klasse: ein Test, der aus dem falschen Grund besteht. Die dort geführten Ausprägungen sind andere; der Transportfall — `evil.example.com` wird auch von einer Loopback-Fallback-Policy abgewiesen — steht nicht darin |
| 6 — der Mutationstest ist das Abnahmekriterium | **kein Check.** Der Katalog kennt keinen Check, der einen Mutationstest verlangt; er prüft, ob eine Kontrolle vorhanden ist, nicht ob ihr Nachweis trägt |
| 7 — die Testharness als eigene Fehlerquelle | **kein Check**, aber ein benachbarter: [`OPS-005`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/OPS-005.md) — «Pipeline unterscheidet ‹bestanden› von ‹nicht gelaufen›» — teilt die Frage, wie viel ein grüner Lauf belegt. Die Harness-Fälle dieser Regel stehen nicht darin |
| 8 — ohne Sitzung teilt sich Zustand still | **drei Checks, eine Regel:** [`ARCH-015`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-015.md) (kein Handshake, keine Sitzung), [`ARCH-016`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-016.md) (`server/discover`), [`ARCH-017`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-017.md) (handle-basierter Zustand). Der Katalog trennt sie, weil ein Server den ersten bestehen und am dritten scheitern kann — zustandslos verdrahtet und trotzdem zustandsbehaftet gebaut |
| 9 — Header-Pflicht | [`SCALE-008`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SCALE-008.md) — «`Mcp-Method` und `Mcp-Name` sind Pflichtheader»; daneben [`SEC-027`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SEC-027.md) für `x-mcp-header` aus Tool-Parametern, den diese Regel nicht führt |
| 10 — Legacy-SSE mit Datum | [`SCALE-009`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SCALE-009.md) — «Legacy HTTP+SSE abgeschaltet, mit Datum»; [`SCALE-010`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SCALE-010.md) für den entfallenen GET-Endpunkt |
| 11 — MRTR | [`HITL-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/HITL-006.md) — «MRTR statt serverinitiierter Requests: `input_required`, Retry, Idempotenz» |
| 12 — Auth-Härten | [`SEC-025`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SEC-025.md) (RFC-9207-`iss`, greift ab `auth_model == "OAuth-Proxy"`), [`SEC-026`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SEC-026.md) (CIMD statt DCR, greift ab `auth_model != "none"`) |
| 13 — der Guard und die Zweige vor ihm | **teilweise.** Wieder [`OPS-005`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/OPS-005.md), und diesmal näher: Er führt ausdrücklich den Guard, der nie gegen `main` gelaufen ist — «167 Workflow-Runs in der Repo-Historie, kein einziger ein Test». Das ist die eine Hälfte dieser Regel. Die andere steht nicht darin: der Zweig, der vor dem Merge geschnitten wurde und den Guard deshalb nie ausführt, obwohl er auf `main` seit Wochen grün läuft |

Wer nach den Regeln 1, 3, 4 und 8–12 baut, besteht die dort genannten Checks. Für die Regeln 2 und 6 gilt das nicht: Sie beschreiben Fehler, die dieser Katalog derzeit nicht sieht. Bei den Regeln 5, 7 und 13 liegt je ein Check daneben oder deckt eine Hälfte — `DRIFT-003` fängt bei Regel 5 die Klasse, aber nicht den Transportfall, und `OPS-005` bei Regel 13 den Guard, der nie gegen `main` lief, aber nicht den Zweig, der vor ihm abzweigte. Ein bestandenes Audit ist dort kein Beleg, dass der Nachweis trägt.

**Fünf Checks messen einen Gegenstand, den `2026-07-28` entfernt hat**, und sind für einen Server auf der neuen Baseline nicht mehr anwendbar: `SCALE-002` (Stateful Load Balancing), `SCALE-003` (`Mcp-Session-Id`-Routing im Edge-LB), `SCALE-007` (Stream-Wiederaufnahme via `Last-Event-ID`), `SDK-004` (CORS-Exposure von `Mcp-Session-Id`), `SEC-009` (kryptografische Bindung der Session-ID). Der letzte hat in `ARCH-017` eine Ersatzdimension: Die Sitzungs-ID gibt es nicht mehr, die Frage nach der Ratbarkeit der Referenz schon — sie ist in die Tool-Signatur gewandert, und dort schaut kein Auth-Layer mehr hin. Das ist der Grund, warum ein Server nach der Migration nicht automatisch *weniger* zu prüfen hat.
