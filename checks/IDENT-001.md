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

## Pass Criteria

- [ ] Keine Datei unter `src/` enthält `<dist>/<Ziffer>.<Ziffer>` als Literal
- [ ] Der User-Agent wird aus `__version__` gebaut (f-String oder Äquivalent)
- [ ] `__version__` stammt aus den Paket-Metadaten (siehe IDENT-002)
- [ ] Die Prüfung wurde über das **ganze Modul** geführt, nicht zeilenweise nach Schlüsselwort
- [ ] Beide Schreibweisen geprüft: Header `User-Agent` und Konstante `USER_AGENT`
- [ ] Der User-Agent wurde am frisch installierten Paket zur Laufzeit aufgelöst
- [ ] Bei mehreren HTTP-Clients im Server: **alle** verwenden dieselbe Konstante

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Versionsliteral im Header-Dict | Drift bei jedem Release, still |
| Mehrzeilige Konstante (`= (\n  "name/1.0…"\n)`) | Entgeht zeilenweiser Suche — real vorgekommen |
| Zweiter, separater HTTP-Client mit eigenem UA | Ein Fix erwischt nur einen von mehreren Pfaden |
| UA nur in `server.py` geprüft, `api_client.py` übersehen | Teilbefund als «behoben» gemeldet |
| Prüfung nur an der Quelle, nicht am installierten Paket | Editable Install kann veraltete Metadaten tragen |

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

- Portfolio-Sweep 2026-07-29: 12 von 30 Servern betroffen
- `swiss-electricity-mcp#26` / `#27` — der Fall, den die zeilenweise Suche verfehlte
- IDENT-002 — Herkunft von `__version__`
- IDENT-005 — Fallback-Marker
- SEC-021 — Egress-Allow-List (dieselbe Aussenwirkungs-Familie)
- ARCH-012 — MCP-Protokollversion (nicht zu verwechseln)
