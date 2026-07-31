---
name: mcp-transport-hardening
description: Transport- und Bind-Härtung für MCP-Server mit Netz-Transport — damit ein Server unter dem konfigurierten Transport überhaupt hochkommt und abweist, wen er abweisen muss. Verwende diesen Skill ergänzend zu mcp-builder immer wenn (1) ein Server auf eine neue SDK-Major-Version migriert wird (mcp 1.x → 2.x, FastMCP → MCPServer), (2) ein Server von stdio auf streamable-http, SSE oder einen anderen Netz-Transport umgestellt wird, (3) Host, Port oder Bind-Adresse konfiguriert, durchgereicht oder in einer ASGI-Factory gelesen werden, (4) jemand meldet, ein Server antworte mit HTTP 421, starte im Deployment nicht oder sei «nur lokal erreichbar», (5) eine eingehende Host- oder Origin-Allow-List entworfen wird oder DNS-Rebinding, CORS und Auth-Token gegeneinander abgewogen werden, (6) ein Server hinter uvicorn mit `--factory` betrieben wird, oder (7) Tests für den Transport-Pfad geschrieben werden. Nicht nötig für Server, die ausschliesslich über stdio laufen.
---

# MCP Transport Hardening — kommt der Server hoch, und weist er ab, wen er abweisen muss?

Companion zu `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **kommt er unter dem konfigurierten Transport überhaupt hoch, und weist er ab, wen er abweisen muss?**

Das ist eine eigene Fehlerklasse, weil sie ebenfalls still ist — nur anders still als bei `mcp-data-fidelity`. Dort liefert der Server eine plausible Antwort, die inhaltlich falsch ist. Hier liefert er gar keine: grüne Unit-Tests, sauberer Linter, und in Produktion startet der Prozess nicht oder beantwortet jede Anfrage unter einem echten Hostnamen mit HTTP 421. Der Transport-Pfad ist genau der Teil, den eine Testsuite über stdio nie berührt.

**Die Leitfrage bei jedem Server mit Netz-Transport:** *Wenn ich den Bind ändere — folgt die eingehende Allow-List mit, auf jedem Pfad, der eine App baut, und wird ein Test rot, wenn sie es nicht tut?* Ist die Antwort nein, greift eine der fünf Regeln unten.

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

## Regel 5 — Eine Kontrolle ist unbewiesen, bis ihre Entfernung rot wird

Die Regeln 1–4 sagen, was verdrahtet sein muss. Diese sagt, woran man erkennt, dass es verdrahtet **ist**. Ein grüner Test beweist, dass der Code läuft — nicht, dass er die Kontrolle prüft, die er zu prüfen vorgibt. Der Unterschied fällt nur auf, wenn man die Kontrolle **entfernt** und schaut, was rot wird.

In den drei Migrationen unten hat dieser Handgriff zweimal die **Tests** korrigiert und nicht den Code. Der teuerste Fall:

```python
# ✗ besteht auch mit entferntem host-Kwarg — die explizite Liste deckt die Lücke zu
def test_real_hostname_is_accepted(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.ch:8000")
    assert client.get("/mcp", headers={"Host": "mcp.example.ch:8000"}).status_code != 421

# ✓ ohne Allow-List muss das SDK aus dem Bind raten — erst dann trägt der Kwarg
def test_real_hostname_is_accepted(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert client.get("/mcp", headers={"Host": "mcp.example.ch:8000"}).status_code != 421
```

Die erste Fassung bestand **mit angewandter Mutation**: Bei expliziter Allow-List ist der `host`-Kwarg irrelevant. Der Test prüfte die Umgebungsvariable, nicht die Verdrahtung. Derselbe Mechanismus in der zweiten Variante: Ein Port-Test, der nur den App-Builder abdeckt, sagt nichts über die Naht davor — der Builder wird mit explizitem Port gerufen, also überlebt er jede Mutation an der Stelle, an der der Port tatsächlich verloren geht. **Ein Test deckt die Naht ab, an der der Wert reist, nicht die Funktion, die ihn schon hat.**

**Scheitern, nicht hängen.** Fehlt die Kontrolle, ist der wahrscheinlichste Ausgang kein rotes Kreuz, sondern eine Suite, die steht. Zwei belegte Wege:

- Ohne Allow-List wird ein SSE-GET unter fremdem Host **zugelassen** und öffnet einen endlosen Event-Stream, auf den der `TestClient` beim Verlassen wartet.
- `monkeypatch` schreibt ein Klassen-Attribut, das es von einer *Instanz* gelesen hat, beim Zurückrollen auf diese Instanz zurück. `mcp.run` bleibt dauerhaft verdeckt, ein späterer Klassen-Patch wirkt nicht — und der echte uvicorn startet mitten in der Suite.

Beide Zweig-Tests behaupten seither **ausdrücklich, welcher Zweig lief**. Ein Test, der die falsche Verzweigung nimmt, scheitert dadurch, statt zu warten.

**Der Testaufbau selbst ist eine Fehlerquelle.** Ein blanker `httpx.ASGITransport` liefert auf jede Anfrage 500: Streamable HTTP startet seinen Session-Manager im App-Lifespan, den dieser Transport nie ausführt. Wer den 500er für ein Finding hält, debuggt den falschen Code — es braucht `TestClient`.

**Nachweis:** Jede Kontrolle **einzeln** entfernen und die Zahl der scheiternden Tests notieren. Eine Mutation mit null roten Tests ist eine unbewiesene Kontrolle, keine bestandene Prüfung. Die Tabelle gehört in den PR:

| Mutation | scheiternde Tests |
|---|---|
| `transport_security` aus dem eigenen App-Builder | 4 |
| `transport_security` aus dem SDK-`run()`-Pfad | 2 |
| Allow-List nicht portgenau | 3 |
| Port reist nicht bis zum Builder | 1 |

---

## Checkliste vor dem Deployment eines Servers mit Netz-Transport

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
- [ ] Tragender Test: richtiger Hostname, **falscher Port** — ein fremder Hostname allein beweist nichts
- [ ] Mutationstest: jede Kontrolle einzeln entfernt, jede Entfernung bringt einen Test zum Scheitern (Regel 5)
- [ ] Mutationstabelle im PR, jede Zeile mit mindestens einem roten Test (Regel 5)
- [ ] Regressionstest läuft **ohne** gesetzte `MCP_ALLOWED_HOSTS` — sonst besteht er trotz Mutation (Regel 5)
- [ ] Getestet wird die Naht, an der der Wert reist, nicht die Funktion, die ihn schon hat (Regel 5)
- [ ] Kein Test **hängt**, wenn die Kontrolle fehlt — er scheitert, und behauptet, welcher Zweig lief (Regel 5)
- [ ] Gegen den echten ASGI-Stack geprüft (`TestClient`), nicht gegen blankes `ASGITransport` (Regel 5)

## Woher diese Regeln stammen

Aus drei Pull Requests desselben Zyklus (2026-07):

| PR | Ausgangslage |
|---|---|
| [`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29) | Migration 1.x → 2.x. Echter Startfehler plus 421 im HTTP-Pfad, vor dem Fix gegen den echten ASGI-Stack reproduziert |
| [`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51) | Kein 421-Bug — der Bind kam korrekt an. Es fehlte die Möglichkeit, überhaupt zu sagen, unter welchen Namen der Server erreichbar sein darf |
| [`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25) | Kein 421-Bug. Egress-Allow-List vorhanden, eingehend nichts — und der Port fiel auf dem Weg zum App-Builder heraus |

Fünf Dinge daran sind übertragbar:

1. **Nur einer der drei war ein Bug.** Die anderen zwei waren eine fehlende Kontrolle — für das gedachte Deployment vertretbar begründet, aber wer den Server anders betreibt, hatte keinen Weg, sich einzuklinken. Fehlende Konfigurierbarkeit fällt in keinem Test auf, weil nichts falsch ist.
2. **Grüne Tests und sauberer Linter, und der Prozess startet nicht.** Tool-Tests laufen über stdio und berühren den Transport-Pfad nie. Der Fehler wartet auf das erste HTTP-Deployment.
3. **Der Mutationstest hat in zwei von drei Repos die Tests korrigiert, nicht den Code** — daraus Regel 5. Einmal bestand der Regressionstest trotz Mutation, weil er `MCP_ALLOWED_HOSTS` setzte; einmal liess das Fallenlassen des Ports gar keinen Test scheitern. Eine Kontrolle, deren Entfernung nichts rot macht, ist unbewiesen.
4. **Ein Test, der hängt statt zu scheitern, ist schlimmer als keiner** — dass er *hängt* und nicht *scheitert*, ist der Regelfall, nicht die Ausnahme. Ohne Kontrolle wird die verbotene Anfrage zugelassen, und zugelassen heisst bei einem Stream: warten.
5. **Der Testaufbau selbst ist eine Fehlerquelle.** Ein blanker `httpx.ASGITransport` liefert auf jede Anfrage 500: Streamable HTTP startet seinen Session-Manager im App-Lifespan, den dieser Transport nie ausführt. Wer den 500er für einen Befund hält, debuggt den falschen Code.

**Zur Benennung:** Zwei der drei PRs führen im Titel `SEC-005`, implementieren aber die **eingehende** Kontrolle — im Audit-Katalog `SEC-024`. `SEC-005` ist die ausgehende Richtung (DNS-Pinning gegen TOCTOU). Zwei Angriffe, ein Name: Wer «DNS-Rebinding» ohne Richtungsangabe zitiert, meint mit einiger Wahrscheinlichkeit den anderen.

## Verwandte Skills

| Skill | Rolle |
|---|---|
| `mcp-builder` | Generische Bauanleitung — dieser Skill ergänzt sie, ersetzt sie nicht |
| `mcp-data-fidelity` | Dieselbe stille Fehlerklasse eine Schicht höher: liefert der Server, was die Quelle hat? |
| `mcp-data-source-probe` | Vorgehen *vor* dem Bau — dort wird die Datenquelle geprüft, hier der eigene Transport |
| `mcp-audit` | Prüfung *nach* dem Bau: Regel 4 ist Check `SEC-024`, `SEC-005` ist die Gegenrichtung |

Wer nach diesem Skill baut, besteht `SEC-024`. Wer ihn beim Audit reisst, findet hier die Behebung.
