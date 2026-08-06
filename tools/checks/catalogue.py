"""Die Zuordnungstabelle gegen den echten Katalog von mcp-audit-skill.

WARUM NICHT IM PR-LAUF. Prüfung 6 prüft, was ohne Netz prüfbar ist: dass jede
Regel eine Zeile hat. Was sie strukturell NICHT kann, ist der eigentliche
Fehler dieses Repos — eine Zeile, die zum Zeitpunkt des Schreibens stimmte und
seither veraltet ist. Das ist keine Eigenschaft eines Commits, sondern der
verstrichenen Zeit: Die Tabelle stand am 5. August zweimal falsch, ohne dass
hier jemand etwas geändert hätte. Ein zeitbasierter Fehler gehört an einen
Zeitplan, nicht an einen Diff.

Und er gehört nicht vor den Merge-Button: Ein Netzaussetzer oder ein Release
drüben würde sonst einen unbeteiligten Doku-PR rot färben. Regel 5 dieses
Skills sagt, was dann passiert — «ein Test, der ständig falsch anschlägt, wird
abgeschaltet und fängt dann gar nichts mehr».

Deshalb `offline=False`: `scripts/validate.sh` fährt diese Prüfung nicht,
`catalogue-drift.yml` tut es wöchentlich.

DER ABRUF STEHT NICHT HIER. Der Workflow legt das Manifest als Datei ab und
nennt sie in `$CATALOGUE_MANIFEST`; diese Prüfung liest sie. Eine Prüfung, die
Netz braucht, um überhaupt zu starten, lässt sich nicht gegen einen
Fixture-Baum fahren — und dann bliebe ausgerechnet die logikreichste Prüfung
des Repos ungetestet. «Nicht erreichbar» ist im Workflow von «abgewichen»
getrennt, mit eigenem Text: Sonst sucht man beim nächsten Netzaussetzer im
Katalog nach einem Fehler, den es nicht gibt.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from ._core import CheckFailed, register
from .skill_doc import TABLE_HEADING, read_skill

MANIFEST_ENV = "CATALOGUE_MANIFEST"
MANIFEST_URL = "https://raw.githubusercontent.com/malkreide/mcp-audit-skill/main/checks/MANIFEST.txt"

CHECK_ID = re.compile(r"[A-Z]{2,6}-\d{3}")
LINKED = re.compile(r"/checks/([A-Z]{2,6}-\d{3})\.md")

GERMAN_NUMBERS = {
    "fünf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
    "elf": 11,
    "zwölf": 12,
    "dreizehn": 13,
}

STATE = re.compile(
    r"(?P<total>\d+) Checks in (?P<cats>\w+) Kategorien.*?"
    r"davon (?P<fid>\w+) in der Kategorie `FID`",
    re.S,
)


def parse_manifest(raw: str) -> list[str]:
    ids = [line.strip() for line in raw.splitlines() if line.strip()]
    if not ids or not all(CHECK_ID.fullmatch(i) for i in ids):
        raise CheckFailed(
            "MANIFEST.txt sieht nicht aus wie eine Liste von Check-IDs — Format "
            "drüben geändert, diese Prüfung prüft sonst nichts"
        )
    return ids


def table_section(skill: str) -> str:
    match = re.search(
        rf"^{re.escape(TABLE_HEADING)}\n(.*?)(?=^#{{2,3}} |\Z)",
        skill,
        re.M | re.S,
    )
    if not match:
        raise CheckFailed(
            f"SKILL.md: Abschnitt {TABLE_HEADING!r} nicht gefunden — Anker weg, "
            "diese Prüfung würde stillschweigend aufhören zu prüfen"
        )
    return match.group(1)


def assert_table_matches(ids: list[str], skill: str) -> str:
    """Die reine Logik: Tabelle gegen Katalog, ohne Netz und ohne Dateien."""
    catalogue = set(ids)
    categories = {i.split("-")[0] for i in ids}
    fid = {i for i in ids if i.startswith("FID-")}
    section = table_section(skill)

    problems = []

    # 1) Die Zahlen in der Kopfzeile.
    state = STATE.search(section)
    if not state:
        raise CheckFailed(
            "SKILL.md: der Satz zum Katalogstand passt nicht mehr auf "
            "'<N> Checks in <Wort> Kategorien ... davon <Wort> in der Kategorie "
            "`FID`' — umformuliert, damit blieben die Zahlen ungeprüft"
        )
    claimed_total = int(state.group("total"))
    claimed_cats = GERMAN_NUMBERS.get(state.group("cats"))
    claimed_fid = GERMAN_NUMBERS.get(state.group("fid"))
    if claimed_total != len(catalogue):
        problems.append(
            f"Katalog-Grösse: Tabelle sagt {claimed_total}, MANIFEST.txt hat "
            f"{len(catalogue)}"
        )
    if claimed_cats != len(categories):
        problems.append(
            f"Kategorien: Tabelle sagt {state.group('cats')!r} ({claimed_cats}), "
            f"MANIFEST.txt hat {len(categories)} ({sorted(categories)})"
        )
    if claimed_fid != len(fid):
        problems.append(
            f"FID-Checks: Tabelle sagt {state.group('fid')!r} ({claimed_fid}), "
            f"MANIFEST.txt hat {len(fid)} ({sorted(fid)})"
        )

    # 2) Jeder VERLINKTE Check muss existieren — und nur der.
    #
    # Bewusst nicht jede genannte ID: Der erste Lauf dieses Jobs ist genau
    # daran falsch angeschlagen. Die Tabelle nennt ein `FID-007`, das es
    # absichtlich nicht gibt («statt ein `FID-007` zu eröffnen»), und ein
    # Wächter, der eine korrekte Gegenrede als Fehler meldet, ist der
    # Fehlalarm aus Regel 5. Ein toter *Link* dagegen ist immer ein Befund.
    linked = set(LINKED.findall(section))
    gone = sorted(linked - catalogue)
    if gone:
        problems.append(
            f"Die Tabelle verlinkt {gone}, im Katalog gibt es sie nicht (mehr) — "
            "umbenannt, zurückgezogen oder Tippfehler in der URL"
        )

    # 3) Ein FID-Check, den die Tabelle nicht VERLINKT, ist der Fall vom
    #    5. August: Genau so ist `FID-006` entstanden, während hier «kein
    #    Check» stand. Auch hier zählt der Link und nicht die Erwähnung — und
    #    zwar in dieselbe Richtung nützlich: Gäbe es eines Tages ein echtes
    #    `FID-007`, schlägt dieser Punkt an, obwohl die ID im Text vorkommt.
    #    Das ist richtig so, denn der Satz, der sie heute nennt («statt ein
    #    `FID-007` zu eröffnen»), wäre an diesem Tag falsch.
    unlinked = sorted(fid - linked)
    if unlinked:
        problems.append(
            f"Neu im Katalog und in der Tabelle nicht verlinkt: {unlinked} — "
            "welche Regel deckt er ab?"
        )

    if problems:
        raise CheckFailed(
            "DRIFT — die Zuordnungstabelle in SKILL.md ist gegenüber dem "
            "Katalog veraltet:\n\n"
            + "\n".join(f"  - {p}" for p in problems)
            + "\n\nQuelle ist die Check-Datei drüben, nicht deren CHANGELOG."
        )

    return (
        f"{claimed_total} Checks, {claimed_cats} Kategorien, {claimed_fid} in "
        f"FID; alle {len(linked)} verlinkten Checks existieren, alle FID-Checks "
        "sind verlinkt"
    )


@register(
    14,
    "SKILL.md matches the real catalogue of mcp-audit-skill",
    offline=False,
)
def catalogue_drift(root: Path) -> str:
    raw = os.environ.get(MANIFEST_ENV)
    if not raw:
        raise CheckFailed(
            f"${MANIFEST_ENV} ist nicht gesetzt — diese Prüfung liest das "
            "abgelegte Manifest. Der Abruf steht in "
            f".github/workflows/catalogue-drift.yml ({MANIFEST_URL}). FAIL "
            "statt skip: Eine übersprungene Prüfung meldete «bestanden», wo "
            "«nicht gelaufen» richtig wäre."
        )
    path = Path(raw)
    if not path.is_file():
        raise CheckFailed(f"${MANIFEST_ENV} zeigt auf {raw}, dort liegt keine Datei")
    return assert_table_matches(
        parse_manifest(path.read_text(encoding="utf-8")), read_skill(root)
    )
