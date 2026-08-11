"""Die Pruefungen des Skills `mcp-data-source-probe` — Suite `probe`.

    python -m tools.harness --suite probe

DIE GROESSTE DER DREI COMPANION-SUITEN, und zwar aus einem Grund, der sich
benennen laesst: Dieser Skill liefert GESCHLOSSENE Vorlagen aus. Sie laufen,
also laesst sich mehr an ihnen messen als «kompiliert» — ein Import (`probe/3`)
und ein Manifest, das je Vorlage Eigenschaften zusichert (`probe/17`). Die
beiden anderen Skills fuehren absichtlich offene Vorlagen; dort waere beides
ein Befund ueber die falsche Sache.

NEUN DER URSPRUENGLICH NEUNZEHN PRUEFUNGEN STEHEN HIER NICHT. Ihr Gegenstand
ist das REPOSITORY und nicht der Skill: die Vorlagen-Syntax, der getrackte
Bytecode, die Ketten-Tabelle, die beiden ruff-Gates samt Biss-Waechter, der
ruff-Pin, die laufende ruff und die GitHub-Description. Im Herkunftsrepo
fielen Skill und Repository zusammen, hier nicht mehr.

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

from . import adoption, companion, readmes, references, skill_doc
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

__all__ = [
    "ABSORBED",
    "SUITE",
    "adoption",
    "companion",
    "readmes",
    "references",
    "skill_doc",
]
