---
id: IDENT-002
title: "__version__ aus der installierten Distribution, nicht von Hand gepflegt"
category: IDENT
severity: medium
applies_when: 'always'
pdf_ref: "Custom (Portfolio-Sweep 2026-07-29, 30 Server)"
evidence_required: 2
---

# IDENT-002 — `__version__` aus den Paket-Metadaten

## Description

`__version__` im Paket-Root ist die naheliegende Quelle für jede Integration, die wissen will, welche Serverversion läuft. Wird der Wert von Hand gepflegt, driftet er — und zwar unbemerkter als der User-Agent, weil er oft nirgends ausgewertet wird und deshalb nie auffällt.

Der Portfolio-Sweep vom 2026-07-29 fand **20 von 30 Servern** mit abgedriftetem `__version__`:

| Server | `__version__` | Paket |
|---|---|---|
| `bag-epl-mcp` | 0.2.0 | **1.0.1** (volle Major-Version) |
| `zurich-opendata-mcp` | 0.2.0 | 0.5.1 (drei Minor-Bumps) |
| `swiss-efv-mcp` | 0.1.0 | 0.3.0 |
| `swiss-environment-mcp` | 0.1.0 | 0.5.1 (seit dem Initial-Release nie mitgezogen) |

Der letzte Fall ist der aufschlussreichste: Der Wert stand seit dem ersten Release unverändert auf `0.1.0`, während das Paket bei `0.5.1` lag. Niemand hatte ihn je ausgewertet — was ihn nicht harmlos macht, sondern nur unentdeckt.

`pyproject.toml` ist die einzige Quelle der Wahrheit. Alles andere liest von dort, statt sie zu wiederholen.

## Verification

### Modus 1: code_review

```bash
# Literal-Zuweisungen finden — Fallback-Marker (siehe IDENT-005) ausgenommen
grep -rnE '__version__\s*=\s*"[0-9]+\.[0-9]' src/ | grep -v '+'

# Gegenprobe: wird überhaupt aus den Metadaten gelesen?
grep -rn "importlib.metadata\|from importlib import metadata" src/
```

**Pass-Pattern:**

```python
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

try:
    __version__ = _distribution_version("<dist-name>")
except PackageNotFoundError:
    __version__ = "0.0.0+source"
```

**Fail-Pattern:**

```python
__version__ = "0.1.0"       # muss bei jedem Release von Hand mit
```

Für Node/TypeScript gilt dasselbe Prinzip: Version aus `package.json` lesen (`createRequire`/Import-Assertion), nicht als Konstante duplizieren.

### Modus 2: runtime_test

```bash
pip install -e . && python -c "import <pkg>; print(<pkg>.__version__)"
# Muss der Version in pyproject.toml entsprechen.
```

**Wichtiger Stolperstein:** Metadaten entstehen beim **Installieren**, nicht beim Import. Nach einem Versionsbump meldet ein editable Install weiter die alte Nummer, bis erneut installiert wird. Ein Test, der `__version__` gegen `pyproject.toml` prüft, deckt genau das auf — und muss den nächsten Schritt in die Fehlermeldung schreiben, sonst sucht man an der falschen Stelle:

```python
assert pkg.__version__ == expected, (
    f"Installierte Metadaten melden {pkg.__version__}, pyproject.toml steht auf "
    f"{expected}. Bei einem editable Install nach einem Versionsbump: "
    "`pip install -e .` erneut ausführen."
)
```

Im Sweep hat genau dieser Test beim Schreiben sofort einen veralteten Editable-Install aufgedeckt (0.4.1 gegen 0.5.1).

**Reichweite: der Checkout, und zwar mit Absicht.** Dieser Modus vergleicht die installierten Metadaten gegen `pyproject.toml` — beide aus demselben Baum. Das ist für die Frage dieses Checks richtig: Ob `__version__` *abgeleitet* statt von Hand gepflegt wird, ist eine Eigenschaft der Quelle, und ein Vergleich mit dem Index würde sie nicht schärfer beantworten.

Es heisst aber auch, dass der Vergleich **über das publizierte Artefakt nichts aussagt**. Beide Seiten stammen aus derselben Datei; sie können gar nicht widersprechen. Ein Server kann diesen Check vollständig bestehen, während das Paket auf dem Index eine andere Nummer meldet — weil der Fix nie released wurde (`IDENT-006`) oder weil die Pipeline den Wert unterwegs ersetzt (`IDENT-003`). Wer aus einem grünen `IDENT-002` auf die Identität des ausgelieferten Pakets schliesst, macht denselben Fehler, den `IDENT-006` beschreibt: Er vergleicht Etiketten innerhalb einer Quelle und hält das Ergebnis für eine Aussage über das Artefakt.

## Pass Criteria

- [ ] `__version__` wird über `importlib.metadata.version()` (bzw. das Sprach-Äquivalent) gelesen
- [ ] Kein Versionsliteral unter `src/` ausser dem Fallback-Marker (IDENT-005)
- [ ] Ein Test vergleicht die installierten Metadaten gegen `pyproject.toml`
- [ ] Die Fehlermeldung dieses Tests nennt den Editable-Install-Fall
- [ ] Der Test wird ohne Installation **übersprungen**, nicht rot (sonst scheitert er im reinen Quell-Checkout)
- [ ] Bei Submodul-Importen in `__init__.py`: Versionsblock steht **vor** ihnen (Zirkelimport)
- [ ] Aus dem Bestehen dieses Checks wurde **nicht** auf die Identität des publizierten Pakets geschlossen — dafür sind `IDENT-001` (Modus 3) und `IDENT-006` zuständig

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| `__version__ = "0.1.0"` als Literal | Driftet ab dem ersten Bump |
| Test pinnt das Literal (`assert __version__ == "0.3.0"`) | Schreibt die Drift fest, statt sie zu finden — real vorgekommen |
| Wert wird nirgends ausgewertet | Drift bleibt jahrelang unentdeckt |
| Versionsblock nach `from .server import mcp` | Zirkelimport, sobald das Submodul `__version__` nutzt |
| Metadaten-Lesung ohne `except PackageNotFoundError` | Import bricht im Quell-Checkout |

## Remediation

```diff
  """<Server> MCP Server."""
+
+ from importlib.metadata import PackageNotFoundError
+ from importlib.metadata import version as _distribution_version

- __version__ = "0.2.0"
+ try:
+     __version__ = _distribution_version("<dist-name>")
+ except PackageNotFoundError:
+     # Quell-Checkout ohne Installation. Bewusst kein plausibel aussehender
+     # Platzhalter — siehe IDENT-005.
+     __version__ = "0.0.0+source"
```

Ein bestehender Test, der das Literal festnagelt, muss mitgeändert werden:

```diff
- assert __version__ == "0.3.0"
+ from importlib.metadata import version
+ assert __version__ == version("<dist-name>")
```

## Effort

S — Pro Server 10 Minuten. Der Testumbau ist der grössere Teil.

## References

- Portfolio-Sweep 2026-07-29: 20 von 30 Servern betroffen
- `eth-library-mcp#12` — Test, der das Literal festschrieb statt die Drift zu erkennen
- `seco-labor-mcp#12` — Zirkelimport durch Blockreihenfolge
- IDENT-001 — User-Agent, der aus diesem Wert gebaut wird; dessen Modus 3 misst am Artefakt, was hier an der Quelle geprüft wird
- IDENT-005 — Fallback-Marker
- `IDENT-003` / `IDENT-006` — wo die Aussage über das *publizierte* Paket herkommt. Dieser Check trifft sie nicht
