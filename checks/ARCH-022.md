---
id: ARCH-022
title: "Die Versionsquelle importiert das Paket-Root nicht"
category: ARCH
severity: medium
applies_when: 'always'
adoption: advisory
pdf_ref: "Custom (Portfolio-Fundstücke i14y-mcp / bag-health-mcp, 2026-08-03)"
evidence_required: 2
---

# ARCH-022 — Die Version kommt aus einem eigenen Modul, nicht aus dem Root

## Description

`IDENT-002` sagt, **woher** die Version kommt: aus den Paket-Metadaten, nicht aus einem Literal. Dieser Check betrifft die Frage danach — **wo** dieser Wert steht und wer ihn holen darf, ohne einen Zyklus zu bauen.

**Der Fall** (`i14y-mcp`): Das Submodul `client` braucht die Version für seinen User-Agent (`IDENT-001`). Es holt sie so:

```python
# src/i14y_mcp/client.py
from i14y_mcp import __version__          # aus dem Paket-Root
```

Das Paket-Root sieht so aus:

```python
# src/i14y_mcp/__init__.py
__version__ = _distribution_version("i14y-mcp")
from .server import mcp                   # und server importiert client
```

Damit läuft der Import im Kreis: Root → `server` → `client` → Root. Dass es trotzdem funktioniert, hängt an einer einzigen Eigenschaft dieser Datei — dass `__version__` **oberhalb** von `from .server import mcp` steht. Beim Rückgriff aus `client` ist das Root-Modul erst halb initialisiert; gefunden wird nur, was bis dahin zugewiesen wurde.

> Die Version aus einem halb initialisierten Root zu ziehen hält, bis jemand zwei Zeilen umsortiert.

Und das Umsortieren ist genau die Art Änderung, die durch jedes Review geht: Importe nach oben, Zuweisungen nach unten — die Konvention, die fast jeder Formatierer und fast jede Stilfibel nahelegt. Der Zyklus bricht dann sofort und vollständig, mit einem `ImportError`, der auf `client.py` zeigt und nichts über seine Ursache sagt.

`bag-health-mcp` trägt dieselbe Form. Beide sind bestätigt.

### Die Lösung ist ein eigenes Modul

```python
# src/i14y_mcp/_version.py — importiert nichts aus dem eigenen Paket
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

try:
    __version__ = _distribution_version("i14y-mcp")
except PackageNotFoundError:
    __version__ = "0.0.0+source"
```

Root und Submodule lesen beide von dort:

```python
# src/i14y_mcp/__init__.py
from ._version import __version__

# src/i14y_mcp/client.py
from ._version import __version__
```

`_version.py` ist ein **Blatt** im Importgraphen: Es importiert nichts aus dem eigenen Paket, also kann kein Pfad durch es hindurch zurückführen. Damit ist die Reihenfolge der Zeilen im Root keine tragende Eigenschaft mehr, sondern wieder das, wonach sie aussieht — Formatierung.

Das ist auch der Unterschied zu `IDENT-002`. Dessen Kriterium «Versionsblock steht **vor** den Submodul-Importen» beschreibt, wie man mit dem Zyklus lebt. Dieser Check entfernt ihn.

### Die Doppelmessung — und warum sie in den Check gehört

Ein Zyklus ist keine Eigenschaft, die man einem Importfehler ansieht. Ein einzelner Lauf, der scheitert, kann auch ein Artefakt der Reihenfolge sein: falsches Arbeitsverzeichnis, unvollständige Installation, ein `sys.path`, der ein anderes Paket zuerst findet. Und ein einzelner Lauf, der **gelingt**, sagt noch weniger — er hat womöglich nur den günstigen Pfad genommen.

Deshalb wird zweimal gemessen, jedes Mal in einem **frischen Interpreter**:

| Messung | Was importiert wird | Was sie zeigt |
|---|---|---|
| **KALT** | das Submodul zuerst (`import pkg.client`) | Der Root wird erst durch diesen Import initialisiert. Der Rückgriff aus `client` trifft ihn halb fertig — hier schlägt ein echter Zyklus zu |
| **WARM** | das Root zuerst (`import pkg`, dann `pkg.client`) | Der Root ist vollständig, `__version__` liegt vor. Ein echter Zyklus ist hier **unsichtbar** |

Erst der Vergleich trägt die Aussage:

- **KALT scheitert, WARM gelingt** → echter Zyklus. Das Ergebnis hängt daran, wer zuerst importiert — also an der Aufrufreihenfolge des Konsolen-Skripts, die kein Test festhält.
- **Beide scheitern** → kein Zyklus, sondern ein kaputter Aufbau. Der Befund liegt woanders (Installation, Pfad, Paketname).
- **Beide gelingen** → kein Befund aus dieser Messung. Der statische Pfad in Modus 2 kann trotzdem einen Zyklus zeigen, der heute nur nicht getroffen wird.

**Diese Unterscheidung ist der Grund, warum der Check existiert, und ich habe sie zuerst nicht gemacht.** Der `bag-health-mcp`-Befund wurde beim ersten Durchgang als Reihenfolge-Artefakt abgetan — auf Basis eines einzigen warmen Laufs, der erwartungsgemäss grün war. Erst der kalte Lauf im frischen Interpreter zeigte den Zyklus. Ein einzelner Lauf beantwortet diese Frage nicht, egal wie er ausgeht.

### Positivbeispiel

```
src/pkg/
├── __init__.py     from ._version import __version__
│                   from .server import mcp
├── _version.py     importiert nur importlib.metadata      ← Blatt
├── server.py       from ._version import __version__
└── client.py       from ._version import __version__
```

KALT und WARM liefern beide dieselbe Version; die Zeilenreihenfolge im Root trägt nichts.

### Negativbeispiel

```
src/pkg/
├── __init__.py     __version__ = _distribution_version("pkg")   ← muss oben stehen
│                   from .server import mcp
├── server.py       from .client import Client
└── client.py       from pkg import __version__                  ← zurück ins Root
```

KALT scheitert, sobald die beiden Zeilen im Root tauschen:

```
ImportError: cannot import name '__version__' from partially initialized
module 'pkg' (most likely due to a circular import)
```

WARM gelingt weiterhin — deshalb findet ein Test, der irgendwo vorher `import pkg` gemacht hat, diesen Fehler nie.

## Verification

### Modus 1: runtime_test — die Doppelmessung

Zwei **getrennte** Prozesse. Ein einzelner Interpreter, der beides nacheinander tut, misst die zweite Frage nicht mehr: Nach dem ersten Import steht das Paket in `sys.modules` und jeder weitere Lauf ist warm.

```bash
PKG=<pkg>; MOD=client        # das Submodul, das die Version braucht

# KALT — Submodul zuerst, frischer Interpreter
python -c "import $PKG.$MOD as m; print('KALT ok:', m.__version__ if hasattr(m,'__version__') else 'importiert')"
echo "kalt_exit=$?"

# WARM — Root zuerst, frischer Interpreter
python -c "import $PKG; import $PKG.$MOD; print('WARM ok:', $PKG.__version__)"
echo "warm_exit=$?"
```

Auswertung nach der Tabelle oben. **Beide Exit-Codes gehören in die Evidenz**, nicht nur der auffällige — ein gemeldetes «KALT scheitert» ohne den warmen Gegenlauf ist genau die Messung, die beim ersten Durchgang zur falschen Einordnung führte.

Zusätzlich der Pfad, den das publizierte Artefakt wirklich nimmt:

```bash
# Welchen Einstieg deklariert das Paket?
grep -A 3 "\[project.scripts\]" pyproject.toml
```

Ein Konsolen-Skript auf `pkg.server:main` importiert `pkg.server` — das ist der **kalte** Pfad. Genau er läuft bei Nutzenden, und genau er wird in Tests fast nie genommen.

### Modus 2: code_review — führt ein Pfad zurück ins Root?

```bash
# Submodule, die aus dem eigenen Paket-Root lesen
grep -rnE "from (\.|<pkg>) import .*__version__|from <pkg> import" src/<pkg>/ \
  | grep -v "^src/<pkg>/__init__.py"

# Und importiert das Root seinerseits Submodule?
grep -nE "^from \.|^import \." src/<pkg>/__init__.py
```

Treffer in **beiden** Aufrufen heisst: Es gibt einen Zyklus, unabhängig davon, ob er heute zuschlägt.

```bash
# Gibt es ein Blatt-Modul für die Version?
ls src/<pkg>/_version.py 2>/dev/null && grep -nE "^from|^import" src/<pkg>/_version.py
```

`_version.py` darf ausschliesslich aus der Standardbibliothek importieren. Ein `from .settings import ...` darin baut den Zyklus an derselben Stelle neu auf.

### Modus 3: config_check — hält ein Test den kalten Pfad fest?

```bash
grep -rn "import <pkg>\." tests/ | head
```

Ein Test, der das Submodul in einem **eigenen** Prozess importiert (`subprocess`), hält die Eigenschaft fest. Ein Test innerhalb der laufenden Suite tut das nicht: `conftest.py`, ein Fixture oder ein früherer Testfall hat das Root längst importiert, und ab da ist jeder Import warm.

## Pass Criteria

- [ ] Die Version steht in einem eigenen Modul (`_version.py` o. ä.), das **nichts** aus dem eigenen Paket importiert
- [ ] Kein Submodul liest `__version__` aus dem Paket-Root
- [ ] Das Paket-Root liest die Version ebenfalls aus diesem Modul, statt sie selbst zu ermitteln
- [ ] Die Korrektheit hängt **nicht** an der Reihenfolge der Zeilen in `__init__.py`
- [ ] KALT (Submodul zuerst) und WARM (Root zuerst) wurden in je **frischen** Interpretern gemessen, und **beide** Ergebnisse stehen in der Evidenz
- [ ] Der Pfad des deklarierten Konsolen-Skripts wurde bestimmt und mitgemessen — er ist der kalte
- [ ] Ein einzelner Lauf wurde **nicht** als Beleg für «kein Zyklus» gewertet
- [ ] Sofern ein Test die Eigenschaft hält: Er importiert in einem eigenen Prozess, nicht innerhalb der laufenden Suite

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Submodul liest `__version__` aus dem Paket-Root | Zyklus. Hält nur, solange der Versionsblock oben steht |
| Korrektheit ruht auf der Zeilenreihenfolge in `__init__.py` | Die erste Import-Sortierung bricht den Server — eine Änderung, die jedes Review passiert |
| Nur WARM gemessen | Der Zyklus ist im warmen Lauf unsichtbar; das Ergebnis ist erwartungsgemäss grün und sagt nichts |
| Nur KALT gemessen | Nicht von einem kaputten Aufbau zu unterscheiden — der Befund wird zu Recht angezweifelt und dann verworfen |
| Beide Messungen im selben Interpreter | Der zweite Lauf ist per Konstruktion warm; gemessen wird einmal dasselbe |
| Einzelner Lauf als Beleg gewertet | Genau die Fehleinschätzung, die diesen Check verzögert hat |
| `_version.py` importiert wieder aus dem Paket | Der Zyklus ist verschoben, nicht entfernt |
| Konsolen-Skript-Pfad nie gemessen | Der Pfad, den Nutzende nehmen, ist der, den Tests auslassen |

## Remediation

```diff
+ # src/pkg/_version.py  (neu — Blatt im Importgraphen)
+ from importlib.metadata import PackageNotFoundError
+ from importlib.metadata import version as _distribution_version
+
+ try:
+     __version__ = _distribution_version("<dist-name>")
+ except PackageNotFoundError:
+     __version__ = "0.0.0+source"
```

```diff
  # src/pkg/__init__.py
- __version__ = _distribution_version("<dist-name>")
+ from ._version import __version__
  from .server import mcp
```

```diff
  # src/pkg/client.py
- from pkg import __version__
+ from ._version import __version__
```

Danach die Doppelmessung erneut, in frischen Interpretern — und diesmal muss KALT ebenso gelingen wie WARM. Ein Fix, der nur warm belegt ist, ist nicht belegt.

## Effort

S — Eine neue Datei und zwei geänderte Importzeilen. Die Zeit geht in die Doppelmessung und darin, den Pfad des Konsolen-Skripts tatsächlich zu bestimmen statt anzunehmen.

## References

- Portfolio-Fundstück `i14y-mcp` — `client` → Root → `server` → `client`; hielt allein durch die Zeilenreihenfolge im Root
- Portfolio-Fundstück `bag-health-mcp` — dieselbe Form; bestätigt, KALT und WARM in je frischen Interpretern gemessen
- `IDENT-002` — woher die Version kommt (Metadaten statt Literal); dessen Kriterium «Versionsblock vor den Submodul-Importen» lebt mit dem Zyklus, dieser Check entfernt ihn
- `IDENT-001` — der User-Agent, für den das Submodul die Version überhaupt braucht
- `IDENT-007` — startet das publizierte Artefakt? Ein Zyklus schlägt genau dort zu, auf dem kalten Pfad des Konsolen-Skripts
- `OPS-005` — ein einzelner grüner Lauf ist keine Messung dieser Eigenschaft
