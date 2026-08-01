---
id: IDENT-001
title: "User-Agent aus den Paket-Metadaten, nie als Literal"
category: IDENT
severity: high
applies_when: 'tools_make_external_requests == true'
pdf_ref: "Custom (Portfolio-Sweep 2026-07-29, 30 Server)"
evidence_required: 2
---

# IDENT-001 — User-Agent aus den Paket-Metadaten

## Description

Der User-Agent ist die einzige Selbstauskunft, die ein MCP-Server bei jedem Upstream-Request hinterlässt. Steht die Version dort als Literal im Code, muss sie bei jedem Release von Hand mitgezogen werden — und genau das wird vergessen.

Der Portfolio-Sweep vom 2026-07-29 über 30 Server hat **12 Server mit falschem User-Agent** gefunden, davon **4 mit falscher Major-Version**:

| Server | meldete | Paket stand auf |
|---|---|---|
| `register-mcp` | `register-mcp/1.0` | 0.5.0 |
| `swiss-transport-mcp` | `swiss-transport-mcp/1.0` (2 Stellen) | 0.3.3 |
| `swiss-democracy-mcp` | `swiss-democracy-mcp/1.0.0` | 0.2.3 |
| `swiss-culture-mcp` | `swiss-culture-mcp/1.0` | 1.1.3 |
| `swiss-environment-mcp` | `swiss-environment-mcp/0.2.0` | 0.5.0 (über drei Releases) |

**Am publizierten Artefakt gemessen ist es schlimmer.** Der Sweep oben las Repositories. Ein zweiter Sweep am Folgetag (2026-07-30) installierte **33 publizierte Pakete aus dem Index** und mass, was sie tatsächlich senden würden: **16 sendeten eine Version, die nicht der entsprach, als die sie installiert wurden.** Alle 16 hatten den Fix gemergt. Keines hatte ihn released.

Das ist derselbe Abstand wie in `IDENT-006`, aus der anderen Richtung gesehen: Ein Quellbaum kann wochenlang tadellos sein, während jeder `pip install` weiterhin die alte, falsche Identität ausliefert. **Ein sauberes Repository ist deshalb kein Nachweis für diesen Check** — der Nachweis kommt aus dem Artefakt (Modus 3).

Der Schaden ist nicht theoretisch. Bundesstellen ordnen Requests über den User-Agent zu — für Rate-Limits, für Störungsmeldungen, für die Frage, welche Client-Version ein Problem verursacht. Ein Server, der sich seit drei Releases als 0.2.0 ausgibt, macht diese Zuordnung falsch, und zwar still: nichts bricht, niemand merkt es.

**Abgrenzung zu SEC-021 (Egress-Allow-List):** Dort geht es darum, *wohin* der Server spricht. Hier darum, *als wer*. Beides ist Aussenwirkung gegenüber Dritten und gehört zusammen geprüft.

**Abgrenzung zu ARCH-012:** Dort geht es um die MCP-Protokollversion des SDK. Hier um die Version des Servers selbst.

## Verification

### Modus 1: code_review (Literal-Suche über das ganze Modul)

Entscheidend ist die Suchmethodik. Eine zeilenweise Suche nach dem Schlüsselwort verfehlt mehrzeilige Definitionen — im Sweep genau der Fall, der einen bereits als «behoben» gemeldeten Server durchrutschen liess:

```python
# swiss-electricity-mcp/api_client.py — Name auf Zeile 32, Literal auf Zeile 33
DEFAULT_USER_AGENT = (
    "swiss-electricity-mcp/0.2.0 (+https://github.com/malkreide/swiss-electricity-mcp)"
)
```

Ein `grep -i "user.agent"` mit Versionsfilter auf derselben Zeile findet das **nicht**. Die Konstante wurde an drei Stellen verwendet; der Server meldete weiter 0.2.0.

```bash
# RICHTIG: das ganze src/ nach dem Wertmuster absuchen, unabhängig vom Bezeichner
grep -rnE "$(python -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['name'])")/[0-9]+\.[0-9]" src/

# FALSCH: setzt voraus, dass Bezeichner und Wert dieselbe Zeile teilen
grep -rn -i "user.agent" src/ | grep -E "[0-9]+\.[0-9]"
```

Zusätzlich muss `USER_AGENT` auch die Schreibweise mit Unterstrich abdecken: `grep -i 'user-agent'` trifft die Konstante `USER_AGENT` **nicht**.

**Pass-Pattern:**

```python
# __init__.py
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

try:
    __version__ = _distribution_version("swiss-environment-mcp")
except PackageNotFoundError:
    __version__ = "0.0.0+source"          # siehe IDENT-005

# api_client.py
from . import __version__
USER_AGENT = f"swiss-environment-mcp/{__version__} (https://github.com/…)"
```

**Fail-Pattern:**

```python
headers={"User-Agent": "swiss-environment-mcp/0.5.1 (https://github.com/…)"}
```

### Modus 2: runtime_test (Auflösung am installierten Paket)

Der belastbare Nachweis erfolgt am **ausgelieferten Artefakt**, nicht an der Quelle:

```bash
python -m venv /tmp/v && /tmp/v/bin/pip install -q "<dist>==<version>"
/tmp/v/bin/python -c "
from <pkg> import api_client as a
print(a._new_client().headers['User-Agent'])"
# Muss die soeben installierte Version enthalten.
```

**Dieser Handgriff findet nur einen Teil.** Er liest den Wert über ein Modulattribut, und genau daran scheitert er an realen Servern — siehe Modus 3.

### Modus 3: automated — `published_probe.py` (der primäre Modus)

`scripts/published_probe.py` aus dem [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) installiert die Distribution aus dem Index in ein Wegwerf-venv und misst den User-Agent, den der installierte Code **auf die Leitung legen würde**:

```bash
python scripts/published_probe.py <dist> --format json
python scripts/published_probe.py --constraint 'mcp<2' <dist>    # bei kaputter Auflösung
```

**Warum ein einzelner Handgriff nicht genügt.** Gegen dieselben 33 Pakete wurden drei Erkennungsstrategien geprüft. Jede meldete Pakete als sauber, die drifteten — und jede war an einer *anderen* Stelle blind:

| Strategie | Woran sie scheiterte |
|---|---|
| Regex auf `f"…{__version__}…"` | `lobbywatch-mcp` — die Variable heisst dort `PACKAGE_VERSION`. Ein Muster kennt nur die Schreibweisen, die sein Autor bedacht hat |
| Modul-Namespace zur Laufzeit lesen (Modus 2 oben) | `seco-labor-mcp` — der Wert liegt in `_HTTP_KWARGS["headers"]["User-Agent"]`; `swiss-transport-mcp` — Literal inline im `httpx`-Konstruktor **innerhalb einer Funktion**, existiert also in gar keinem Modulattribut |
| Quelltext nach Literalen absuchen (Modus 1 oben) | Jeden f-String-User-Agent, weil nach dem Schrägstrich keine Ziffer zum Verankern steht |

Die Probe fährt deshalb **alle drei** und schreibt zu jedem Befund, welche ihn erzeugt hat. Die beiden Modi oben bleiben nützlich — sie sind billig und für einen einzelnen Server oft ausreichend —, aber keiner von ihnen trägt allein ein Portfolio.

**Der Teil, auf den es am meisten ankommt:** Eine Probe, die keinen User-Agent findet, darf nicht melden, dass es keinen gibt. Das sind zwei verschiedene Aussagen — «dieser Server sendet keinen eigenen UA» ist ein Ergebnis, «ich habe die Form nicht erkannt» ist ein Versagen der Probe. Die Probe meldet das als `unverified` und **beendet sich mit einem Fehlercode**; sie tut es, weil ihre erste Fassung 24 Pakete für unauffällig erklärte, von denen 16 drifteten. Schweigen ist hier kein Freispruch.

| Exit | Bedeutung | Status für `IDENT-001` |
|---|---|---|
| `0` | Jeder aufgelöste UA passt zur installierten Version — oder das Paket setzt gar keinen | pass |
| `1` | Drift, ein **fremder** User-Agent, oder `unverified` | `fail` bei Drift/fremd; `todo` bei `unverified` |
| `2` | Die Distribution liess sich nicht installieren | `todo` — und ein Befund gegen `IDENT-006` |

> Die Exit-Codes sind **nicht** die von `shipped_probe.py` (dort ist `2` ein Befund und `127` ein Harness-Fehler). Wer beide in einem Skript aufruft, muss sie getrennt auswerten.

**Ein fremder User-Agent ist eine eigene Befundklasse.** Im Sweep sandte ein Paket eine gefälschte Browser-Kennung. Das ist keine Drift, sondern eine Falschangabe gegenüber dem Upstream — es gehört nicht mit «Version veraltet» in denselben Topf, und die Behebung ist eine andere.

## Pass Criteria

- [ ] Keine Datei unter `src/` enthält `<dist>/<Ziffer>.<Ziffer>` als Literal
- [ ] Der User-Agent wird aus `__version__` gebaut (f-String oder Äquivalent)
- [ ] `__version__` stammt aus den Paket-Metadaten (siehe IDENT-002)
- [ ] Die Prüfung wurde über das **ganze Modul** geführt, nicht zeilenweise nach Schlüsselwort
- [ ] Beide Schreibweisen geprüft: Header `User-Agent` und Konstante `USER_AGENT`
- [ ] Der User-Agent wurde am **aus dem Index installierten** Paket aufgelöst, nicht nur am Checkout — ein sauberes Repository ist kein Nachweis
- [ ] Die Auflösung lief über **mehr als eine** Strategie (Modul-Namespace, Quelltext-Literale, f-String-Muster); keine davon trägt allein
- [ ] Ein nicht aufgelöster User-Agent wurde als `unverified` geführt, **nicht als «sendet keinen»** — das sind zwei Aussagen, und nur eine davon ist ein Pass
- [ ] Ein **fremder** User-Agent (Browser-Kennung o. Ä.) ist als eigener Befund geführt, nicht als Versionsdrift
- [ ] Bei mehreren HTTP-Clients im Server: **alle** verwenden dieselbe Konstante

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Versionsliteral im Header-Dict | Drift bei jedem Release, still |
| Mehrzeilige Konstante (`= (\n  "name/1.0…"\n)`) | Entgeht zeilenweiser Suche — real vorgekommen |
| Zweiter, separater HTTP-Client mit eigenem UA | Ein Fix erwischt nur einen von mehreren Pfaden |
| UA nur in `server.py` geprüft, `api_client.py` übersehen | Teilbefund als «behoben» gemeldet |
| Prüfung nur an der Quelle, nicht am installierten Paket | Editable Install kann veraltete Metadaten tragen |
| Prüfung am Checkout statt am Index-Artefakt | 16 von 33 Paketen drifteten bei sauberem Repository — der Fix war gemergt, nie released |
| UA über ein Modulattribut gelesen | Findet ihn nicht, wenn er in einem verschachtelten Dict oder inline in einem Konstruktor-Aufruf steht |
| «Kein UA gefunden» als «sendet keinen» verbucht | Genau so wurden 24 Pakete für unauffällig erklärt, 16 davon drifteten |
| Fremder UA als Versionsdrift geführt | Andere Ursache, andere Behebung — eine Falschangabe gegenüber dem Upstream, keine vergessene Zahl |
| Exit-Codes von `published_probe.py` und `shipped_probe.py` gleich behandelt | Die Vokabulare unterscheiden sich; `2` heisst hier «nicht installierbar», dort «Befund» |

## Remediation

```diff
+ from . import __version__
  from .observability import get_logger

  DEFAULT_USER_AGENT = (
-     "swiss-electricity-mcp/0.2.0 (+https://github.com/malkreide/swiss-electricity-mcp)"
+     f"swiss-electricity-mcp/{__version__} (+https://github.com/malkreide/swiss-electricity-mcp)"
  )
```

Achtung auf Zirkelimporte: Importiert `__init__.py` ein Submodul (`from .server import mcp`), muss der Versionsblock **vor** diesem Import stehen — sonst ist `__version__` beim Import des Submoduls noch nicht definiert. Im Sweep bei `seco-labor-mcp` aufgetreten.

## Effort

S — Pro Server 10–20 Minuten, inklusive Laufzeitprobe.

## References

- Portfolio-Sweep 2026-07-29 (Repositories): 12 von 30 Servern betroffen
- Portfolio-Sweep 2026-07-30 (**publizierte Artefakte**): 16 von 33 Paketen sendeten eine andere Version, als die sie installiert wurden; alle 16 mit gemergtem, nie released Fix. Dazu ein Paket mit gefälschtem Browser-User-Agent
- `swiss-electricity-mcp#26` / `#27` — der Fall, den die zeilenweise Suche verfehlte
- `mcp-continuous-auditor` → `scripts/published_probe.py` (Modus 3, liest das Artefakt), `scripts/identity_probe.py` (liest das Repository)
- `IDENT-006` — derselbe Abstand zwischen Quelle und Artefakt, dort als eigener Check
- IDENT-002 — Herkunft von `__version__`
- IDENT-005 — Fallback-Marker
- SEC-021 — Egress-Allow-List (dieselbe Aussenwirkungs-Familie)
- ARCH-012 — MCP-Protokollversion (nicht zu verwechseln)
