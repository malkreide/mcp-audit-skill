"""Liest den ruff-Pin aus ci.yml — der gemeinsame Anker beider Ruff-Gates.

Warum eigenes Modul und keine zwei Kopien: `ruff_pin_sync.py` und
`ruff_version.py` haengen an DERSELBEN Stelle in ci.yml. Zwei Regexe dafuer
waeren zwei Stellen, die auseinanderlaufen koennen — und ausgerechnet diese
beiden Checks existieren, weil zwei Stellen auseinanderlaufen koennen.

Der Regex bildet die Vorlage aus der Shell nach, die hier ersetzt wurde:
`sed -n 's/.*ruff==\\([0-9][^ "'"'"']*\\).*/\\1/p' … | head -1`. Die Forderung
nach einer ZIFFER am Anfang ist tragend und kein Zufall: Ohne sie faengt das
Muster auch Fliesstext wie «ruff==<version>» aus einem Kommentar und
vergliche dann eine Nennung gegen eine Zahl.
"""

from __future__ import annotations

import pathlib
import re
import sys

CI_YML = pathlib.Path(".github/workflows/ci.yml")

# `ruff==0.16.1` — die Ziffer vorn haelt Kommentar-Nennungen wie
# `ruff==<version>` draussen.
PIN = re.compile(r"""ruff==(?P<version>[0-9][^\s"']*)""")


def lies_pin(*, zusatz: str = "") -> str:
    """Der erste `ruff==<version>`-Treffer in ci.yml.

    Fehlt er, ist das ein FEHLER und kein Grund zum Ueberspringen: Dann hat
    der aufrufende Check nichts, wogegen er vergleicht, und haette genau
    deshalb Erfolg gemeldet.
    """
    if not CI_YML.is_file():
        sys.exit(f"{CI_YML} gibt es nicht — von hier aus laesst sich kein Pin lesen.")
    m = PIN.search(CI_YML.read_text(encoding="utf-8"))
    if not m:
        sys.exit(f"::error::{CI_YML} nennt kein ruff==<version>.{zusatz}")
    return m.group("version")
