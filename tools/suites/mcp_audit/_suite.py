"""Der Name dieser Suite, EINMAL.

Eine eigene Datei und nicht `__init__.py`: Dort stehen die Modul-Importe, die
die Registrierung ausloesen, und die Pruefmodule brauchen den Namen genau
waehrend dieses Imports. Beides in einer Datei waere ein Zyklus.

Die Zeichenkette je Registrierung zu wiederholen waere die Alternative — und
ein Tippfehler darin waere keine Fehlermeldung, sondern eine stille zweite
Suite mit einer einzigen Pruefung darin.
"""

from __future__ import annotations

SUITE = "audit"
