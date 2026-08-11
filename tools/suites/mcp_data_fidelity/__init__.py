"""Die Pruefungen des Skills `mcp-data-fidelity` — Suite `fidelity`.

    python -m tools.harness --suite fidelity

ZWOELF DER URSPRUENGLICH ACHTZEHN PRUEFUNGEN STEHEN HIER NICHT. Ihr Gegenstand
ist das REPOSITORY und nicht der Skill: die beiden ruff-Gates, ihre zwei
Waechter, der ruff-Pin, die laufende ruff, der getrackte Bytecode, die
Vorlagen-Syntax, die Ketten-Tabelle, die Workflow-Verweise, der Release-Tag
und die GitHub-Description. Im Herkunftsrepo fielen Skill und Repository
zusammen, hier nicht mehr — es gibt EINE `ruff.toml`, EINEN git-Index, EIN
Manifest. Dieselbe Entscheidung wie bei `transport`, nur haeufiger: Dieser
Skill fuehrte die vollstaendigste der vier Pruefsammlungen, und genau deshalb
ueberschneidet er sich am meisten.

DIE NUMMERN BLEIBEN TROTZDEM STEHEN. Phase 0 hat zugesichert, dass keine
Pruefung umnumeriert wird, weil die Nummern in CHANGELOG-Eintraegen und
Befunden auftauchen. Diese Suite fuehrt deshalb 2, 4, 5, 6, 7 und 14 — mit
Luecken. `ABSORBED` nennt jede Luecke samt ihrem neuen Ort; der Test haelt die
VEREINIGUNG beider Mengen gegen 1..N. Eine Luecke ohne Eintrag ist weiterhin
ein Befund — und ein `ABSORBED`-Eintrag, dessen Nummer wieder registriert
wird, ebenfalls.

`fidelity/14` IST DER ANLASS FUER PHASE 4. Sie hielt die Zuordnungstabelle
gegen den Katalog dieses Repositories und brauchte dafuer einen Wochenplan,
einen gepinnten Commit und 640 Zeilen Abruf-Apparat. Der Katalog liegt jetzt
daneben; sie ist ein gewoehnliches Offline-Gate. Was dabei ersatzlos
entfaellt, steht im Docstring von `catalogue.py`.

EINE ABSORPTION IST NICHT VERLUSTFREI, UND EINE HIER IST ES NACHWEISLICH
NICHT. `fidelity/17` mass die Zeilenbreite an BEIDEN Gates — `format` UND
`check` —, weil das Herkunftsrepo `E` vollstaendig im `select` fuehrte und
E501 damit als Lint-Regel griff. Die `ruff.toml` dieses Repos fuehrt
`E4,E7,E9` und sagt dazu ausdruecklich: «E501 bleibt bewusst aussen vor — das
entscheidet der Formatter». `audit/7` misst deshalb nur die Formatter-Haelfte
(`lint_enforces_e501 = False`), und dasselbe gilt fuer `W`, das dieses Repo
ebenfalls nicht fuehrt.

Das ist eine ENTSCHEIDUNG und kein Versehen — aber eine ueber fremdes Gut:
Sie ist beim Zusammenlegen der Konfigurationen in Phase 3a getroffen worden,
und der Skill, dessen Vorlagen sie betrifft, zieht erst jetzt ein. Sie steht
als offener Punkt im Merge-Plan unter 4.2l und wird hier nicht stillschweigend
zugedeckt, weil «weniger geprueft als vorher» genau die Auskunft ist, die
diese Repositories sonst einfordern.
"""

from __future__ import annotations

from . import catalogue, hygiene, readmes, skill_doc
from ._suite import SUITE

#: Nummer -> wohin die Pruefung gegangen ist. Sie sind nicht verschwunden,
#: sondern im Monorepo genau einmal vorhanden statt viermal.
ABSORBED: dict[int, str] = {
    1: "audit/10 — die Vorlagen aller drei Skills kompilieren in einem Lauf",
    3: "audit/8 — es gibt einen git-Index",
    8: "audit/12 — die Ketten-Tabelle steht einmal, gegen ein Manifest",
    9: "audit/6 — es gibt ein Lint-Gate, dessen Biss einmal gemessen wird",
    10: "audit/3 — `ruff check` faehrt einmal ueber den Baum",
    11: "audit/4 — `ruff format` faehrt einmal ueber den Baum",
    12: "audit/1 — es gibt eine ruff.toml und eine lint.yml",
    13: "audit/13 — es gibt ein Repo-CHANGELOG und einen Repo-Tag",
    15: "G13 (tools/gates/repo_meta.py, gebaut, Bindung offen) — es gibt eine "
    "GitHub-Description",
    16: "audit/15 — es gibt ein .github/workflows/ und einen Scope darauf",
    17: "audit/7 — die Zeilenbreite wird einmal gemessen, aber nur am "
    "Formatter (siehe den Docstring oben)",
    18: "audit/2 — es gibt einen PATH und eine laufende ruff",
}

__all__ = [
    "ABSORBED",
    "SUITE",
    "catalogue",
    "hygiene",
    "readmes",
    "skill_doc",
]
