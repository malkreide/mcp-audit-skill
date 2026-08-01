---
name: mcp-transport-hardening
description: Transport- und Bind-Härtung für MCP-Server mit Netz-Transport — damit ein Server unter dem konfigurierten Transport überhaupt hochkommt und abweist, wen er abweisen muss. Verwende diesen Skill ergänzend zu mcp-builder immer wenn (1) ein Server auf eine neue SDK-Major-Version migriert wird (mcp 1.x → 2.x, FastMCP → MCPServer), (2) ein Server von stdio auf streamable-http oder SSE umgestellt wird, (3) Host, Port oder Bind-Adresse konfiguriert, durchgereicht oder in einer ASGI-Factory gelesen werden, (4) jemand meldet, ein Server antworte mit HTTP 421, starte im Deployment nicht oder sei «nur lokal erreichbar», (5) eine eingehende Host- oder Origin-Allow-List entworfen wird oder DNS-Rebinding, CORS und Auth-Token gegeneinander abgewogen werden, (6) ein Server hinter uvicorn mit `--factory` betrieben wird, oder (7) Tests für den Transport-Pfad geschrieben, per Mutationstest abgenommen werden oder eine Suite hängt statt zu scheitern. Nicht nötig für Server, die ausschliesslich über stdio laufen.
---

# MCP Transport Hardening — kommt der Server hoch, und weist er ab, wen er abweisen muss?

Companion zu `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **kommt er unter dem konfigurierten Transport überhaupt hoch, und weist er ab, wen er abweisen muss?**

Das ist eine eigene Fehlerklasse, weil sie ebenfalls still ist — nur anders still als bei `mcp-data-fidelity`. Dort liefert der Server eine plausible Antwort, die inhaltlich falsch ist. Hier liefert er gar keine: grüne Unit-Tests, sauberer Linter, und in Produktion startet der Prozess nicht oder beantwortet jede Anfrage unter einem echten Hostnamen mit HTTP 421. Der Transport-Pfad ist genau der Teil, den eine Testsuite über stdio nie berührt.

**Die Leitfrage bei jedem Server mit Netz-Transport:** *Wenn ich den Bind ändere — folgt die eingehende Allow-List mit, auf jedem Pfad, der eine App baut, und wird ein Test rot, wenn sie es nicht tut?* Ist die Antwort nein, greift eine der sieben Regeln unten.

Die Regeln 1–4 betreffen den Server, die Regeln 5–7 den Beweis. Der zweite Teil ist der teurere: Transportregeln kann man nachschlagen, die Beweisführung nicht.

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

Der Versions-Cap wandert mit: `mcp[cli]>=1.0.0,<2` wird zu `>=2.0.0,<3`. Der Bound bleibt, nur am anderen Ende verankert. Ein `<2`-Cap kauft Zeit, indem er auf der letzten 1.x pinnt — ein Ziel ist er nie.

**Nachweis:** Die 1.x-Settings-Zuweisung zurückbauen — ein Test muss mit `ValueError` scheitern, nicht das Deployment. Für (c): beide Schreibweisen serialisieren und die JSON vergleichen; sind sie identisch, ist es ein reines Lesethema und der Client bleibt aussen vor.

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

**Nachweis:** **Richtiger Hostname, falscher Port** muss abgewiesen werden — ein `evil.example.com` allein beweist nichts, weil eine zurückfallende Loopback-Policy ihn ebenfalls abweist. Dazu: ein gültiges `Bearer`-Token darf einen fremden Host nicht retten.

---

## Regel 5 — Ein Negativtest muss aus deinem Grund scheitern, nicht aus dem eines Defaults

Die Regeln 1–4 sagen, was verdrahtet sein muss. Die Regeln 5–7 sagen, woran man erkennt, dass es verdrahtet **ist** — und sie sind der teurere Teil, weil man sie nicht nachschlagen kann.

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

Nicht «Tests schreiben». Sondern: **Mutation benennen, anwenden, protokollieren, welche Tests fallen.** Eine Kontrolle, deren Entfernung nichts rot macht, ist unbewiesen — unabhängig davon, wie viele grüne Tests daneben stehen.

In den drei PRs unten hat dieser Handgriff dreimal etwas gefunden, das sonst durchgegangen wäre. Der teuerste Fall zuerst:

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

**Nachweis:** Die Tabelle selbst — sie entsteht nur, wenn jede Mutation tatsächlich angewandt und die Suite tatsächlich gelaufen ist. Eine Zeile mit null roten Tests ist ein Befund, kein Nebenergebnis: Entweder fehlt der Test, oder die Kontrolle tut nichts. Die Tabelle gehört in den PR.

| Mutation | scheiternde Tests |
|---|---|
| `transport_security` aus dem eigenen App-Builder | 4 |
| `transport_security` aus dem SDK-`run()`-Pfad | 2 |
| `transport_security` aus dem SSE-Pfad | 1 |
| Allow-List nicht portgenau | 3 |
| Port reist nicht bis zum Builder | 1 |

## Regel 7 — Die Test-Harness ist bei HTTP-Transporten selbst eine Fehlerquelle

Drei Fallen, die alle dasselbe Symptom haben: Der Befund sieht aus wie ein Infrastrukturproblem und wird als Rauschen abgetan.

**(a) Ein blanker `httpx.ASGITransport` liefert 500 auf jede Anfrage.** Streamable HTTP startet seinen Session-Manager im **App-Lifespan**, und dieser Transport führt den Lifespan nie aus. Wer den 500er für einen Befund hält, debuggt den falschen Code.

```python
# ✗ kein Lifespan → kein Session-Manager → 500 auf alles
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

Warum der SSE-Fall hängt, verbindet (a) und (c): Ohne Allow-List wird ein SSE-GET unter fremdem Host **zugelassen** und öffnet einen endlosen Event-Stream, auf den der `TestClient` beim Verlassen wartet. Die fehlende Kontrolle äussert sich also nicht als roter Test, sondern als stehende Suite — und ein Hänger wird routinemässig als Flake abgetan.

**Nachweis:** Ein Timeout auf die Suite (`pytest --timeout=30`) macht aus jedem Hänger einen Fehlschlag mit Stacktrace, und die Stelle ist damit benannt statt gemutmasst. Dazu jeden Zweig-Test **einzeln und in der vollen Suite** laufen lassen: Die Instanz-Patch-Falle aus (b) zeigt sich ausschliesslich im zweiten Fall.

---

## Checkliste vor dem Release eines netzgebundenen Servers

**Der Server (Regeln 1–4)**

- [ ] Kein `mcp.settings.<feld> = ...` mehr im Code; der Bind geht als Kwargs an `run()`
- [ ] Annotations werden snake_case gelesen; Drahtformat gegen beide Schreibweisen verglichen
- [ ] TypeScript-Server nicht «mitmigriert» — dort bleibt camelCase korrekt
- [ ] `fastmcp` (PyPI) und `mcp.server.fastmcp` (SDK) nicht verwechselt
- [ ] Versions-Cap am anderen Ende verankert (`>=2.0.0,<3`), auch in verschachtelten Subprojekten
- [ ] Jede ASGI-Factory erhält Host **und** Port aus derselben Konfiguration wie `main()`
- [ ] uvicorn-`--factory`-Pfad liest den Bind selbst; README begründet, warum `MCP_HOST`/`MCP_PORT` neben den Flags nicht redundant sind
- [ ] Jeder App-bauende Pfad (eigener Builder, SDK-`run()`, SSE) bekommt dieselbe Transport-Security
- [ ] Allow-List portgenau, Loopback drin, CORS-Origins aufgenommen, kein `*`
- [ ] Fail-open auf Nicht-Loopback ist sichtbar — Startwarnung im Log

**Der Beweis (Regeln 5–7)**

- [ ] Zu jedem Negativtest die zweite mögliche Ursache benannt und ausgeschlossen (Regel 5)
- [ ] Tragender Fall: richtiger Hostname, **falscher Port** — ein fremder Hostname allein beweist nichts (Regel 5)
- [ ] Jeder Negativtest hat seinen positiven Zwilling (Regel 5)
- [ ] Kein Test stellt selbst die Bedingung her, unter der der Fehler nicht auftreten kann (Regel 6)
- [ ] Getestet wird die Naht, an der der Wert reist, nicht die Funktion, die ihn schon hat (Regel 6)
- [ ] Mutationstabelle im PR: jede Kontrolle einzeln entfernt, jede Zeile mit mindestens einem roten Test (Regel 6)
- [ ] Gegen den echten ASGI-Stack geprüft (`TestClient`), nicht gegen blankes `ASGITransport` (Regel 7)
- [ ] Patch-Ebene im ganzen Repo einheitlich — Instanz oder Klasse, nicht gemischt (Regel 7)
- [ ] Jeder Zweig-Test behauptet, welcher Zweig lief (Regel 7)
- [ ] Suite läuft unter Timeout; jeder Zweig-Test zusätzlich einzeln **und** in der vollen Suite (Regel 7)

## Woher diese Regeln stammen

Aus drei Pull Requests desselben Zyklus (2026-07):

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

**Zur Benennung:** Zwei der drei PRs führen im Titel `SEC-005`, implementieren aber die **eingehende** Kontrolle — im Audit-Katalog `SEC-024`. `SEC-005` ist die ausgehende Richtung (DNS-Pinning gegen TOCTOU). Zwei Angriffe, ein Name: Wer «DNS-Rebinding» ohne Richtungsangabe zitiert, meint mit einiger Wahrscheinlichkeit den anderen.

## Verwandte Skills

| Skill | Rolle |
|---|---|
| `mcp-builder` | Generische Bauanleitung — fremder Skill von Anthropic, dieser hier ergänzt ihn |
| `mcp-data-source-probe` | Vorgehen *vor* dem Bau |
| `mcp-data-fidelity` | Liefert er, was die Quelle hat? |
| `mcp-transport-hardening` | **Dieser Skill:** kommt er hoch, weist er richtig ab? |
| `mcp-audit` | Prüfung *nach* dem Bau — die Zuordnung steht unten |

### Welche Regel welcher Check ist

Der Katalog von [`mcp-audit`](https://github.com/malkreide/mcp-audit-skill) deckt vier der sieben Regeln ab. Die Lücken sind hier benannt, statt sie durch eine ungefähre Zuordnung zu verdecken:

| Regel | Check |
|---|---|
| 1 — SDK-Major-Sprung | [`SDK-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SDK-006.md) — «SDK-Major-Migration vollständig abgeschlossen» |
| 2 — `host` als Saat der Allow-List | **kein Check.** [`SEC-016`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SEC-016.md) liegt daneben, adressiert aber den umgekehrten Fall: `0.0.0.0` als *unbeabsichtigten* Bind (NeighborJack). Regel 2 setzt ein gewolltes `0.0.0.0`-Deployment voraus und fragt, ob der Bind die App erreicht |
| 3 — jeder Pfad identisch verdrahtet | [`ARCH-013`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/ARCH-013.md) — «Alle Netz-Transportpfade identisch verdrahtet» |
| 4 — eingehende Host-Allow-List | [`SEC-024`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SEC-024.md); [`SEC-005`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/SEC-005.md) ist die ausgehende Gegenrichtung |
| 5–7 — die Beweisführung | **kein Check.** Der Katalog prüft, ob eine Kontrolle vorhanden ist — nicht, ob ihr Nachweis trägt |

Wer nach den Regeln 1, 3 und 4 baut, besteht `SDK-006`, `ARCH-013` und `SEC-024`. Wer sie beim Audit reisst, findet hier die Behebung. Für die Regeln 2 und 5–7 gilt das nicht: Sie beschreiben Fehler, die dieser Katalog derzeit nicht sieht.
