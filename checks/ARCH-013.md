---
id: ARCH-013
title: "Alle Netz-Transportpfade identisch verdrahtet"
category: ARCH
severity: high
applies_when: 'transport != "stdio-only"'
pdf_ref: "Sec 2.1"
evidence_required: 2
---

# ARCH-013 — Alle Netz-Transportpfade identisch verdrahtet

> **Baseline-Hinweis (seit v2.0.0) — welche Pfade es überhaupt gibt.** Die Menge
> der zu prüfenden Netzwege ist auf `mcp_spec_version: 2026-07-28` eine andere:
>
> | Pfad | `2025-11-25` | `2026-07-28` |
> |---|---|---|
> | Streamable HTTP POST | ja | ja, mit Pflichtheadern (`SCALE-008`) |
> | HTTP GET für serverinitiierte Nachrichten | ja | **entfällt** — `subscriptions/listen` (`SCALE-010`) |
> | Legacy HTTP+SSE | deprecated seit 2025-03-26 | formal **Deprecated** (`SCALE-009`) |
> | stdio | ja | ja |
>
> Die Regel dieses Checks bleibt wörtlich dieselbe — **jeder** bediente Netzweg
> trägt dieselbe Härtung — und genau deshalb ändert sich das Prüfergebnis: Ein
> Legacy-SSE-Pfad, der neben dem Streamable-HTTP-Pfad weiterläuft, ist auf der
> neuen Baseline ein Pfad, der ein Protokoll spricht, das der Server nach
> eigener Aussage nicht mehr führt. Ein GET-Endpunkt, der noch antwortet,
> ebenso.

## Description

Ein Server, der über Netz erreichbar ist, konstruiert seine ASGI-App fast nie an genau einer Stelle. Typisch sind drei bis vier Wege, und sie entstehen nacheinander, ohne dass jemand sie als Menge betrachtet:

| Pfad | Wann er greift |
|---|---|
| Eigener App-Builder (`build_http_app()`, `create_http_app()`) | Oft nur unter einer Bedingung — etwa wenn Auth oder CORS konfiguriert ist |
| SDK-servierter `run()`-Pfad | Wenn diese Bedingung *nicht* zutrifft |
| Deprecateter SSE-Pfad | Parallel zu Streamable HTTP, für ältere Clients |
| Factory für uvicorn (`--factory`) | Im Container-Deployment, statt `main()` |

**Die Kontrolle sitzt dann auf einem dieser Pfade und nicht auf den anderen.** Das ist kein Bug, den man beim Lesen sieht: Jeder Pfad für sich ist korrekt, der Server startet, die Tests laufen. Nur die Antwort auf «ist die Kontrolle aktiv» lautet plötzlich *es kommt darauf an* — und zwar auf eine Bedingung, die mit der Kontrolle nichts zu tun hat.

**Zwei Ausprägungen, in zwei Repos unabhängig voneinander aufgetreten:**

**1. Die Kontrolle hängt an einer fremden Bedingung.** Ein Server nahm seinen eigenen App-Builder nur, wenn Auth **oder** CORS konfiguriert war; sonst servierte das SDK über `run()`. Wäre die Sicherheitskonfiguration nur dem Builder mitgegeben worden, hinge das Scharfschalten einer Sicherheitskontrolle still davon ab, ob zufällig ein Auth-Token gesetzt ist. Zwei Deployments desselben Images, eines geschützt, eines nicht — und der Unterschied steht in einer Variablen, die von etwas anderem handelt.

**2. Der Parametersatz reist unvollständig mit.** Im selben Portfolio bekam ein App-Builder nur den `host`, nicht den `port`, und defaultete den Port intern. Die Loopback-Einträge der Host-Allow-List nannten dadurch einen Port, den niemand bedient. Die Kontrolle war verdrahtet, aktiv, und trotzdem falsch — sie schützte eine Adresse, die es nicht gab. Bemerkt hat das kein Test, weil der vorhandene Port-Test den Builder mit explizitem Port rief; die Naht davor war ungeprüft.

**Warum das ein eigener Check ist und keine Fussnote in `SEC-024`:** Die Fehlerklasse ist nicht an eine bestimmte Kontrolle gebunden. Dieselbe Lücke entsteht mit Auth-Middleware, Rate-Limiting, Request-Logging oder Tracing-Instrumentierung. Was geprüft wird, ist die **Vollständigkeit der Aufzählung** — und die ist eine Struktureigenschaft des Servers, nicht eine Eigenschaft der Sicherheitskontrolle, die zufällig gerade betrachtet wird.

## Verification

### Modus 1: code_review (die Pfade aufzählen)

Zuerst die Menge bilden. Ein Pfad, der nicht auf der Liste steht, wird auch nicht geprüft.

```bash
# Alle Stellen, die eine ASGI-App konstruieren oder servieren
grep -rnE "streamable_http_app\(|sse_app\(|http_app\(" src/
grep -rnE "def .*_app\(|def create_app|def build_.*app|def .*factory" src/
grep -rnE "mcp\.run\(|uvicorn\.run\(|uvicorn\.Server" src/

# Deployment-Einstiegspunkte — hier tauchen Pfade auf, die im Code nicht sichtbar sind
grep -rnE "uvicorn|--factory|gunicorn|CMD|entrypoint" Dockerfile* railway.toml render.yaml \
  Procfile docker-compose*.yml pyproject.toml 2>/dev/null
```

**Pass-Pattern — eine Quelle, alle Pfade:**

```python
def _security(host: str, port: int) -> TransportSecuritySettings | None:
    """Einzige Stelle, an der die Verdrahtung entsteht."""
    ...


def build_http_app(host: str, port: int) -> Starlette:
    return mcp.streamable_http_app(transport_security=_security(host, port), host=host)


def app_factory() -> Starlette:
    """Für `uvicorn --factory`. Liest den Bind SELBST aus der Konfiguration."""
    settings = load_settings()          # dieselbe Quelle wie main()
    return build_http_app(settings.host, settings.port)


def main() -> None:
    settings = load_settings()
    mcp.run(
        transport=settings.transport,
        host=settings.host,
        port=settings.port,
        transport_security=_security(settings.host, settings.port),
    )
```

**Fail-Pattern 1 — die Kontrolle hängt an einer fremden Bedingung:**

```python
# FAIL: Nur der bedingte Zweig bekommt die Sicherheitskonfiguration.
if settings.auth_token or settings.cors_origins:
    app = build_http_app(host, port)     # mit transport_security
    uvicorn.run(app, host=host, port=port)
else:
    mcp.run(transport="streamable-http", host=host, port=port)   # ohne
```

**Fail-Pattern 2 — der Parametersatz reist unvollständig:**

```python
# FAIL: `port` bleibt zurück und wird im Builder gedefaultet.
def build_http_app(host: str) -> Starlette:
    port = 8000                          # geraten
    ...

_serve_http(host=settings.host, port=settings.port)   # kennt den echten Port
```

### Modus 2: code_review (uvicorn `--factory`)

Ein eigener Fall, weil der Fehler hier von aussen kommt und im Code unsichtbar ist.

```bash
grep -rnE "\-\-factory|factory=True" Dockerfile* railway.toml render.yaml Procfile \
  docker-compose*.yml 2>/dev/null
```

**uvicorn ruft eine Factory ohne Argumente auf.** `uvicorn "pkg.app:app_factory" --factory --host 0.0.0.0 --port 8000` konfiguriert mit `--host` **nur den Listener**. Der Wert erreicht die App nie — die Factory bekommt keine Parameter. Wer annimmt, `--host` würde durchgereicht, baut eine App, die ihren eigenen Bind nicht kennt.

**Pass:** Die Factory liest Host und Port selbst aus derselben Konfigurationsquelle wie `main()`, und die README erklärt, warum die Environment-Variablen neben den uvicorn-Flags **nicht** redundant sind.

**Fail:** Die Factory nimmt Parameter entgegen (uvicorn übergibt sie nicht) oder verlässt sich auf Defaults, während `--host` etwas anderes sagt.

### Modus 3: runtime_test (jeder Pfad einzeln belegt)

```bash
# Pro Pfad denselben Nachweis führen — hier am Beispiel der Host-Allow-List
MCP_TRANSPORT=streamable-http python -m my_mcp_server &   # run()-Pfad
curl -s -o /dev/null -w "run():     %{http_code}\n" -X POST \
  -H "Host: evil.example.com" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  http://127.0.0.1:8000/mcp

# Danach dasselbe über die Factory
uvicorn my_mcp_server.app:app_factory --factory --host 127.0.0.1 --port 8001 &
curl -s -o /dev/null -w "factory:   %{http_code}\n" -X POST ... http://127.0.0.1:8001/mcp
```

**Pass:** Alle Pfade antworten gleich. **Fail:** Ein Pfad weicht ab — dann ist die Kontrolle nicht am Server verdrahtet, sondern an einem Zweig.

**Die Gegenprobe gehört dazu und ist hier besonders lohnend.** Die Verdrahtung aus **einem** Pfad entfernen und die Suite laufen lassen: Scheitert kein Test, deckt die Suite diesen Pfad nicht ab. Genau so ist der Port-Fehler oben gefunden worden — der vorhandene Test rief den Builder mit explizitem Port und konnte die Naht davor nicht sehen.

## Pass Criteria

- [ ] Alle Codepfade, die eine ASGI-App konstruieren oder servieren, sind aufgezählt — eigener Builder, `run()`-Pfad, SSE, Factory
- [ ] Die Deployment-Manifeste sind mitgelesen; ein dort verdrahteter Pfad (`--factory`, eigener `CMD`) zählt mit
- [ ] Die Sicherheitsverdrahtung ist auf **allen** identisch, nicht nur auf dem bedingten Zweig
- [ ] Kein Scharfschalten hängt an einer sachfremden Bedingung (Auth gesetzt, CORS gesetzt, Debug aus)
- [ ] Der **vollständige** Bind-Parametersatz reist mit — Host **und** Port, nicht nur der Host
- [ ] Eine `uvicorn --factory` liest den Bind selbst aus derselben Quelle wie `main()`
- [ ] Pro Pfad existiert ein Test, der die Verdrahtung an der Naht prüft, nicht nur im Builder
- [ ] Gegenprobe geführt: Verdrahtung aus je einem Pfad entfernt, jedes Mal scheitert mindestens ein Test

## Common Failures

| Anti-Pattern | Konsequenz |
|---|---|
| App-Builder nur bei gesetztem Auth/CORS, sonst `run()` | Sicherheitskontrolle hängt an einer Variablen, die von etwas anderem handelt |
| SSE-Pfad vergessen, weil deprecated | Der alte Pfad ist noch erreichbar und ungeschützt |
| Factory nimmt Parameter entgegen | uvicorn ruft sie ohne Argumente — die Parameter sind immer die Defaults |
| `--host` im Manifest, Factory liest Environment nicht | Listener und App widersprechen sich |
| Nur `host` an den Builder, `port` intern gedefaultet | Loopback-Einträge nennen einen Port, den niemand bedient |
| Test ruft den Builder direkt mit allen Parametern | Die Naht davor bleibt ungeprüft — genau dort fällt der Parameter weg |
| «Der andere Pfad wird eh nicht benutzt» | Dann gehört er entfernt, nicht ungeprüft gelassen |

## Remediation

1. Die Pfade **aufschreiben**, bevor irgendetwas geändert wird — Code und Deployment-Manifeste. Die Liste ist das eigentliche Ergebnis dieses Checks; alles Weitere folgt daraus.
2. Die Verdrahtung in **eine** Funktion ziehen, die alle Pfade aufrufen. Nicht in jedem Pfad wiederholen: Duplikate driften.
3. Den vollständigen Parametersatz durchreichen. Wo ein Builder einen Wert defaultet, den der Aufrufer kennt, ist der Default die Fehlerquelle.
4. Für `uvicorn --factory` den Bind in der Factory aus derselben Konfiguration lesen wie `main()`, und in der README festhalten, warum die Environment-Variablen neben den Flags nötig sind.
5. Pro Pfad einen Test an der **Naht** — nicht im Builder, der ohnehin alles bekommt.
6. Mutationsgegenprobe: Verdrahtung aus je einem Pfad entfernen. Scheitert kein Test, ist dieser Pfad ungeprüft, und die Suite hat nur bestätigt, was sie ohnehin annahm.

## Effort

M — 1–3 Tage. Die Aufzählung ist schnell; die Zeit geht in die Tests an den Nähten und die Mutationsgegenprobe pro Pfad.

## References

- PDF Sec 2.1 — Inversion of Control; `ARCH-004` verlangt transport-agnostische Logik, dieser Check die gleichförmige Verdrahtung der Transporte
- `SEC-024` — der Anlassfall: eine Host-Allow-List, die einen von mehreren App-Pfaden erreichte
- `OPS-005` — dieselbe Denkfigur eine Ebene höher: Was nicht gelaufen ist, sieht aus wie bestanden
- Portfolio-PRs: [bag-health-mcp#51](https://github.com/malkreide/bag-health-mcp/pull/51) (Builder nur bei Auth/CORS), [swiss-transport-mcp#25](https://github.com/malkreide/swiss-transport-mcp/pull/25) (SSE-Pfad, verlorener Port), [parlament-mcp#29](https://github.com/malkreide/parlament-mcp/pull/29) (uvicorn-Factory ohne Argumente)
