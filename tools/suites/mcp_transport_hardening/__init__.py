"""Die Pruefungen des Skills `mcp-transport-hardening` — Suite `transport`.

    python -m tools.harness --suite transport

FUENF DER URSPRUENGLICH ELF PRUEFUNGEN STEHEN HIER NICHT, und das ist die
wichtigste Entscheidung dieses Umzugs. Ihr Gegenstand ist das REPOSITORY und
nicht der Skill: der ruff-Pin, die laufende ruff, der getrackte Bytecode, die
Ketten-Tabelle und die GitHub-Description. Im Herkunftsrepo fielen Skill und
Repository zusammen, hier nicht mehr — es gibt EINE `ruff.toml`, EINEN
git-Index, EIN Manifest. Sie mitzunehmen hiesse, `ruff check` viermal ueber
denselben Baum zu fahren und dieselbe Tabelle viermal gegen dasselbe Manifest
zu halten.

DIE NUMMERN BLEIBEN TROTZDEM STEHEN. Phase 0 hat zugesichert, dass keine
Pruefung umnumeriert wird, weil die Nummern in CHANGELOG-Eintraegen und
Befunden auftauchen. Diese Suite fuehrt deshalb 1, 2, 3, 5, 6 und 10 — mit
Luecken. Damit der Waechter, der eine aus der Registry gefallene Pruefung
faengt, dabei nicht stumpf wird, nennt `ABSORBED` jede Luecke samt ihrem
neuen Ort; der Test haelt die Vereinigung beider Mengen gegen 1..N.

Eine Luecke ohne Eintrag in `ABSORBED` ist also weiterhin ein Befund — und
ein `ABSORBED`-Eintrag, dessen Nummer wieder registriert wird, ebenfalls.
"""

from __future__ import annotations

from . import hygiene, readmes, references, skill_doc
from ._suite import SUITE

#: Nummer -> wohin die Pruefung gegangen ist. Sie sind nicht verschwunden,
#: sondern im Monorepo genau einmal vorhanden statt viermal.
ABSORBED: dict[int, str] = {
    4: "audit/12 — die Ketten-Tabelle steht einmal, gegen ein Manifest",
    7: "audit/1 — es gibt eine ruff.toml und eine lint.yml",
    8: "audit/2 — es gibt einen PATH und eine laufende ruff",
    9: "audit/13 (gebaut, Bindung offen) — es gibt eine GitHub-Description",
    11: "audit/8 — es gibt einen git-Index",
}

__all__ = ["ABSORBED", "SUITE", "hygiene", "readmes", "references", "skill_doc"]
