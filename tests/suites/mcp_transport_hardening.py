"""Die Mutationen der Suite `transport`.

Uebernommen aus `mcp-transport-hardening-skill/tests/mutations.py`. Von dessen
vierunddreissig Mutationen sind siebzehn mit umgezogen — die uebrigen
gehoerten zu den fuenf Pruefungen, die im Monorepo repo-bezogen sind und in
`ABSORBED` stehen.

DAZU DREI, DIE ES IM HERKUNFTSREPO NICHT GAB: `transport/12` haelt die Vorlage
gegen die gepinnte SDK-Oberflaeche und lief dort nur als CI-Schritt, also ohne
Mutationen. Diese Datei fuehrt damit ZWANZIG.

ZWEI SORTEN STECKEN DARIN, und die zweite ist der eigentliche Grund fuer diese
Datei — der Herkunfts-Docstring sagt es besser, als es sich neu formulieren
laesst:

* SACHDEFEKTE — die Regelzahl laeuft auseinander, ein Badge ist veraltet. Das
  ist, wofuer die Pruefungen gebaut wurden.

* ANKER-ENTFERNUNGEN (`ANKER` im Namen) — die Ueberschrift wird umbenannt, die
  Wendung umformuliert, das Badge verschwindet. Diese Faelle sind die
  gefaehrlicheren: Die Pruefung hat dann nichts mehr, wogegen sie vergleicht,
  und die naheliegende Implementierung meldet dafuer «bestanden». Die Doktrin
  dieses Portfolios ist, dass ein fehlender Anker ein FEHLER ist. Sie stand
  lange in der Prosa und war nirgends nachgeprueft — hier wird sie es.

Die Mutationen sind bewusst als Muster formuliert und nicht als feste
Textstellen: Kommt Regel 15 dazu, sollen sie weiter greifen, statt an einer
Zeilennummer zu zerbrechen.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from ._mutation import Mutation, MutationStale, append, regex_sub, remove

BASE = "skills/mcp-transport-hardening"
SKILL = f"{BASE}/SKILL.md"
README = f"{BASE}/README.md"
README_DE = f"{BASE}/README.de.md"
CHANGELOG = f"{BASE}/CHANGELOG.md"
PATTERNS = f"{BASE}/reference/patterns.py"
REFERENCE_DIR = f"{BASE}/reference"


def letzter_regelabschnitt(muster: str, ersatz: str) -> Callable[[Path], None]:
    """Mutiert nur den LETZTEN `## Regel N`-Abschnitt von `SKILL.md`.

    Im ersten zu mutieren haette auch dann bestanden, wenn die Pruefung nach
    dem ersten Abschnitt aufhoerte. Der letzte belegt, dass die Schleife
    laeuft.
    """

    def apply(root: Path) -> None:
        pfad = root / SKILL
        teile = re.split(r"(?m)^(## Regel )", pfad.read_text(encoding="utf-8"))
        neu, n = re.subn(muster, ersatz, teile[-1])
        if n == 0:
            raise MutationStale(
                f"Im letzten Regelabschnitt greift {muster!r} nicht (mehr)"
            )
        teile[-1] = neu
        pfad.write_text("".join(teile), encoding="utf-8")

    return apply


MUTATIONS: list[Mutation] = [
    # --- skill_frontmatter (transport/1) -----------------------------------
    Mutation(
        "skill_frontmatter",
        "Name geaendert",
        regex_sub(SKILL, r"^name: mcp-transport-hardening$", "name: something-else"),
        "erwartet wurde name='mcp-transport-hardening'",
    ),
    Mutation(
        "skill_frontmatter",
        "Description ueber der Grenze",
        regex_sub(
            SKILL, r"^description: ", "description: " + "x" * 1100 + " ", count=1
        ),
        "die Grenze liegt bei 1024",
    ),
    Mutation(
        "skill_frontmatter",
        "ANKER: Frontmatter weg",
        regex_sub(SKILL, r"\A---\nname: ", "---\nnaam: ", flags=0),
        "Frontmatter fehlt oder ist unvollstaendig",
    ),
    # --- rule_sections (transport/2) ---------------------------------------
    Mutation(
        "rule_sections",
        "Gegenbeispiel weg, im LETZTEN Abschnitt",
        letzter_regelabschnitt(r"# ✓", "# okay"),
        "das Gegenbeispiel-Paar fehlt",
    ),
    Mutation(
        "rule_sections",
        "Nachweis-Satz weg",
        regex_sub(SKILL, r"\*\*Nachweis:\*\*", "**Beleg:**"),
        "der Nachweis-Satz fehlt",
    ),
    Mutation(
        "rule_sections",
        "ANKER: Regel-Ueberschriften umbenannt",
        regex_sub(SKILL, r"^## Regel ", "## Vorschrift "),
        "keine '## Regel N'-Abschnitte gefunden",
    ),
    # --- rule_count (transport/3) ------------------------------------------
    Mutation(
        "rule_count",
        "ein README-Eintrag fehlt",
        regex_sub(README, r"^14\. \*\*", "- **"),
        "fuehrt nicht dieselben Regeln",
    ),
    Mutation(
        "rule_count",
        "ANKER: README-Ueberschrift weg",
        regex_sub(README, r"^## The fourteen rules$", "## The rules"),
        "Abschnitt '## The fourteen rules' nicht gefunden",
    ),
    Mutation(
        "rule_count",
        "Regelnummern nicht fortlaufend",
        regex_sub(SKILL, r"^## Regel 2\b", "## Regel 7"),
        "nicht fortlaufend",
    ),
    # --- version_badge (transport/5) ---------------------------------------
    Mutation(
        "version_badge",
        "Badge veraltet",
        regex_sub(README, r"badge/version-\d+\.\d+\.\d+-", "badge/version-1.0.0-"),
        "das Versions-Badge zeigt ['1.0.0']",
    ),
    Mutation(
        "version_badge",
        "ANKER: Badge weg",
        regex_sub(README_DE, r"badge/version-\d+\.\d+\.\d+-", "badge/rules-14-"),
        "kein Versions-Badge gefunden",
    ),
    Mutation(
        "version_badge",
        "ANKER: Release-Ueberschriften weg",
        regex_sub(CHANGELOG, r"^## \[(\d+\.\d+\.\d+)\]", r"## Release \1"),
        "keine Release-Ueberschrift",
    ),
    # --- reference_open_names (transport/6) --------------------------------
    Mutation(
        "reference_open_names",
        # Die CODE-Stelle, nicht die Nennung im Modul-Docstring: nur erstere
        # erzeugt ein F821, und nur um sie geht es hier.
        "Tippfehler in einem offenen Namen",
        regex_sub(PATTERNS, r"settings = get_settings\(\)", "settings = get_settngs()"),
        "offene Namen ohne Eintrag auf der Positivliste: ['get_settngs']",
    ),
    Mutation(
        "reference_open_names",
        "verwaister Eintrag auf der Positivliste",
        regex_sub(PATTERNS, r"raise HeaderMismatchError", "raise ValueError"),
        "die Positivliste nennt Namen, die dort nicht mehr offen sind",
    ),
    Mutation(
        "reference_open_names",
        # DER TEUERSTE FALL DIESER SUITE: `ruff check` auf einem Pfad, den es
        # nicht gibt, liefert eine leere Trefferliste UND exit 0. Ohne die
        # Leer-Pruefung meldete diese Pruefung «alles sauber».
        "ANKER: die Vorlage ist weg",
        remove(PATTERNS),
        "Kein einziger offener Name",
    ),
    # --- reference_imports (transport/12) ----------------------------------
    #
    # DIE ZUSAGE, DIE SONST MIT DEM REPO VERSCHWUNDEN WAERE. Sie lief dort als
    # CI-Schritt und hatte hier bis Phase 5 keinen Gegenstand — `audit/10`
    # uebersetzt die Vorlage, mehr nicht.
    Mutation(
        "reference_imports",
        # GENAU DER FALL, UM DEN ES GEHT: Die 1.x-Fassung des Imports parst
        # einwandfrei, und `mcp.server.fastmcp` gibt es in 2.0.0 nachweislich
        # nicht mehr. `audit/10` bleibt dabei gruen.
        "die Vorlage nennt die alte SDK-Oberflaeche",
        regex_sub(
            PATTERNS,
            r"^from mcp\.server\.mcpserver import",
            "from mcp.server.fastmcp import",
        ),
        "Import scheitert an fehlendem Paket 'mcp.server.fastmcp'",
    ),
    Mutation(
        "reference_imports",
        "die Vorlage wirft beim Import",
        append(PATTERNS, "\nraise RuntimeError('boom')\n"),
        "RuntimeError",
    ),
    Mutation(
        "reference_imports",
        "ANKER: das Vorlagen-Verzeichnis ist weg",
        remove(REFERENCE_DIR),
        "Verzeichnis fehlt",
    ),
    # --- referenced_files_exist (transport/10) -----------------------------
    #
    # ANKER: Bei dieser Pruefung IST die referenzierte Datei der Anker. Ist sie
    # weg, hat der Verweis darauf nichts mehr — und das muss ein Befund sein,
    # nicht ein stilles Bestehen.
    Mutation(
        "referenced_files_exist",
        "ANKER: eine referenzierte Datei fehlt",
        remove(CHANGELOG),
        CHANGELOG,
    ),
    Mutation(
        "referenced_files_exist",
        "ANKER: die Vorlage fehlt",
        remove(PATTERNS),
        PATTERNS,
    ),
]
