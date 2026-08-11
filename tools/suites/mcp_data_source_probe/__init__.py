"""Die Pruefungen des Skills `mcp-data-source-probe` — Suite `probe`.

    python -m tools.harness --suite probe

DIE GROESSTE DER DREI COMPANION-SUITEN, und zwar aus einem Grund, der sich
benennen laesst: Dieser Skill liefert GESCHLOSSENE Vorlagen aus. Sie laufen,
also laesst sich mehr an ihnen messen als «kompiliert» — ein Import (`probe/3`)
und ein Manifest, das je Vorlage Eigenschaften zusichert (`probe/17`). Die
beiden anderen Skills fuehren absichtlich offene Vorlagen; dort waere beides
ein Befund ueber die falsche Sache.

ZEHN DER URSPRUENGLICH NEUNZEHN PRUEFUNGEN STEHEN HIER NICHT, aus ZWEI
verschiedenen Gruenden — und die auseinanderzuhalten ist der Punkt. Ihr Gegenstand
ist das REPOSITORY und nicht der Skill: die Vorlagen-Syntax, der getrackte
Bytecode, die Ketten-Tabelle, die beiden ruff-Gates samt Biss-Waechter, der
ruff-Pin, die laufende ruff und die GitHub-Description. Im Herkunftsrepo
fielen Skill und Repository zusammen, hier nicht mehr. Sie stehen in
`ABSORBED`: die Zusage ist weiter da, nur einmal statt viermal.

Eine steht in `RETIRED`, und dort ist der GEGENSTAND weg: `probe/8` bewachte
den Zeiger auf `companion/mcp-data-fidelity/`. Das Verzeichnis existierte nur,
weil die beiden Skills einmal in einem Repo lagen und dann nicht mehr — jetzt
liegen sie wieder in einem, als Geschwister. Es ist mit 2b-iv-c aufgeloest.

DIE NUMMERN BLEIBEN TROTZDEM STEHEN. `ABSORBED` nennt jede Luecke samt ihrem
neuen Ort; der Test haelt die VEREINIGUNG beider Mengen gegen 1..N. Eine
Luecke ohne Eintrag ist weiterhin ein Befund.

`probe/3` IST DIE EINZIGE PRUEFUNG DIESES REPOSITORIES MIT EINER
LAUFZEIT-ABHAENGIGKEIT. Sie importiert die Vorlagen wirklich und braucht dafuer
`pydantic` und `httpx` aus `requirements-reference.txt` — die Datei ist mit
dieser Suite eingezogen und wird in `.github/workflows/lint.yml` installiert.
Fehlen die Pakete, wird die Pruefung ROT und nicht uebersprungen: «nicht
gelaufen» als «bestanden» zu melden ist die eine Auskunft, die schlimmer ist
als keine.
"""

from __future__ import annotations

from . import adoption, readmes, references, skill_doc
from ._suite import SUITE

#: Nummer -> wohin die Pruefung gegangen ist. Sie sind nicht verschwunden,
#: sondern im Monorepo genau einmal vorhanden statt viermal.
ABSORBED: dict[int, str] = {
    2: "audit/10 — die Vorlagen aller drei Skills kompilieren in einem Lauf",
    4: "audit/8 — es gibt einen git-Index",
    10: "audit/12 — die Ketten-Tabelle steht einmal, gegen ein Manifest",
    12: "audit/6 — es gibt ein Lint-Gate, dessen Biss einmal gemessen wird",
    13: "audit/3 — `ruff check` faehrt einmal ueber den Baum",
    14: "audit/4 — `ruff format` faehrt einmal ueber den Baum",
    15: "G13 (tools/gates/repo_meta.py, gebaut, Bindung offen) — es gibt eine "
    "GitHub-Description",
    16: "audit/1 — es gibt eine ruff.toml und eine lint.yml",
    18: "audit/2 — es gibt einen PATH und eine laufende ruff",
}

#: Nummer -> warum es die Pruefung NICHT MEHR GIBT. Der zweite Grund fuer eine
#: Luecke, und er ist ein anderer als `ABSORBED`: Dort ist die Zusage weiter da,
#: nur an einer Stelle statt an vieren. Hier ist der GEGENSTAND weg.
#:
#: Beides in einen Topf zu werfen waere bequem und unwahr — «steht jetzt in
#: audit/N» ist nachpruefbar, «gibt es nicht mehr» muss begruendet sein. Der
#: Registry-Test haelt die Vereinigung aus registrierten, absorbierten und
#: zurueckgezogenen Nummern gegen 1..N; eine Luecke ohne Eintrag in einer der
#: beiden Tabellen bleibt ein Befund.
RETIRED: dict[int, str] = {
    8: (
        "zurueckgezogen mit 2b-iv-c — `companion/mcp-data-fidelity/` ist "
        "aufgeloest. Das Verzeichnis existierte nur, weil die beiden Skills "
        "einmal in einem Repo lagen und dann nicht mehr; sie liegen jetzt "
        "wieder in einem, als Geschwister unter `skills/`. Ein Zeiger auf das "
        "Nachbarverzeichnis ist kein Zeiger, sondern ein Umweg."
    ),
}

__all__ = [
    "ABSORBED",
    "RETIRED",
    "SUITE",
    "adoption",
    "readmes",
    "references",
    "skill_doc",
]
