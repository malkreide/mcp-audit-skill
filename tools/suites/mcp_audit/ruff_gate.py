"""Die Ruff-Gates dieses Repos — die Bindung der generischen Gates.

DIE LOGIK STEHT IN `tools/gates/ruff.py`. Sie ist dieselbe wie in den drei
Schwesterrepos; was sich unterscheidet, ist das Verzeichnis, in dem die Sonden
liegen.

WARUM ES HIER JETZT VIER PRUEFUNGEN SIND UND VORHER ZWEI. Die Checks 3 und 4
fahren die Gates und gab es hier immer. Die beiden neuen pruefen, ob die Gates
ueberhaupt noch etwas tun — beides gab es nur in den Schwesterrepos, und die
Zusammenfuehrung hat es sichtbar gemacht:

* `audit/6` (aus `mcp-data-source-probe-skill` und `mcp-data-fidelity-skill`)
  legt eine absichtlich fehlerhafte Datei unter das Referenz-Verzeichnis und
  besteht darauf, dass beide Gates sie beim Namen nennen.
* `audit/7` (nur aus `mcp-data-fidelity-skill`) misst, ob die deklarierte
  Zeilenbreite die ist, die beide Gates durchsetzen.

DASS `audit/6` HIER NEU IST, IST KEIN ZUFALL. Phase 3a hat `ruff.toml` um
`[lint.per-file-ignores]` fuer `skills/*/reference/*.py` erweitert — genau die
Sorte Schalter, die ein Gate stillschweigend abschaltet, wenn ihn jemand
weitet. Ohne diese Pruefung waere das Ausschalten des Lint-Gates auf den
Vorlagen-Verzeichnissen von aussen nicht bemerkbar; die uebrigen Pruefungen
melden dann weiter «All checks passed!».

`audit/7` ist NICHT dasselbe wie `tests/test_ruff_line_length.py`. Jener Test
prueft, ob die Zahl die RICHTIGE ist (der schmalste Wert im Portfolio); diese
Pruefung misst, ob sie WIRKT. Beides zusammen ist die Zusage; einzeln ist
jedes davon eine halbe.
"""

from __future__ import annotations

from pathlib import Path

from tools.gates import ruff as gates
from tools.harness import register

from ._suite import SUITE

#: Wo die Sonden liegen. Das Verzeichnis muss von den Gates gelesen werden und
#: Vorlagen-Code enthalten, dessen Abdeckung ueberhaupt fraglich ist — beides
#: trifft auf das Referenz-Verzeichnis des eingezogenen Transport-Skills zu,
#: und genau dort greift die per-file-ignores-Regel aus Phase 3a.
PROBE_DIR = "skills/mcp-transport-hardening/reference"


@register(3, "ruff check passes on the whole tree", suite=SUITE)
def ruff_check(root: Path) -> str:
    return gates.ruff_check(root)


@register(4, "ruff format leaves the tree unchanged", suite=SUITE)
def ruff_format(root: Path) -> str:
    return gates.ruff_format(root)


@register(6, "the ruff gate still bites on the reference sources", suite=SUITE)
def ruff_gate_bites(root: Path) -> str:
    return gates.gate_bites(root, probe_dir=PROBE_DIR)


#: SEIT 2b-iv-c `True`. Bis dahin fuehrte `ruff.toml` E501 ausdruecklich NICHT
#: im `select` («das entscheidet der Formatter»), und die Lint-Haelfte der
#: Pruefung unten haette keinen Gegenstand gehabt.
#:
#: Gefallen ist die Entscheidung am Einzug von `mcp-data-fidelity-skill`: Jenes
#: Repo fuehrte `E` vollstaendig und mass die Breite an BEIDEN Gates. Die
#: Absorption nach hier haette stillschweigend die halbe Zusage behalten. Der
#: Betreiber hat entschieden zu weiten; die 28 dabei gemessenen Befunde sind
#: umbrochen, nicht ausgenommen. Die lange Fassung steht in `ruff.toml`.
LINT_ENFORCES_E501 = True


@register(
    7, "the declared line length is the width the formatter enforces", suite=SUITE
)
def line_length_effective(root: Path) -> str:
    return gates.line_length_effective(
        root, probe_dir=PROBE_DIR, lint_enforces_e501=LINT_ENFORCES_E501
    )
