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
`weekly-drift.yml` tut es wöchentlich.

DER ABRUF STEHT NICHT HIER. Der Workflow legt den Katalog als Dateien ab und
nennt sie in `$CATALOGUE_MANIFEST` und `$CATALOGUE_CHECKS_DIR`; diese Prüfung
liest sie. Eine Prüfung, die Netz braucht, um überhaupt zu starten, lässt sich
nicht gegen einen Fixture-Baum fahren — und dann bliebe ausgerechnet die
logikreichste Prüfung des Repos ungetestet. «Nicht erreichbar» ist im Workflow
von «abgewichen» getrennt, mit eigenem Text: Sonst sucht man beim nächsten
Netzaussetzer im Katalog nach einem Fehler, den es nicht gibt.

DREI GEGENSTÄNDE, NICHT EINER. Die Prüfung hält drei Dinge gegeneinander, und
das dritte ist später dazugekommen, weil die ersten beiden es nicht fangen:

  1. die ZAHLEN — Katalog-Grösse, Kategorien, `FID`-Anzahl,
  2. die IDENTITÄTEN — jeder verlinkte Check existiert, jeder `FID`-Check ist
     verlinkt,
  3. die EINSTUFUNG — `enforced` oder `advisory`, je verlinktem Check.

Punkt 3 stammt aus einem Befund, den 1 und 2 durchgelassen haben: In SKILL.md
stand «`ARCH-003` ist der einzige `enforced` Check dieser Tabelle», während
sechs weitere es ebenfalls waren. Jede Zahl stimmte dabei, und jede ID
existierte. Eine Einstufung ist kein Zählwert — sie sagt, ob ein Verstoss
blockiert, und das ist die Aussage, auf die jemand seinen Build stützt.

Dass die Einstufung im Frontmatter der Check-Dateien steht und nicht im
Manifest, ist der Grund für den Tarball-Abruf im Workflow: ein Archiv statt
120 Einzelabrufe, und Manifest wie Check-Dateien zwingend aus demselben
Commit.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from ._core import CheckFailed, register
from .skill_doc import TABLE_HEADING, read_skill

MANIFEST_ENV = "CATALOGUE_MANIFEST"
MANIFEST_URL = "https://raw.githubusercontent.com/malkreide/mcp-audit-skill/main/checks/MANIFEST.txt"

# Die Einstufung steht NICHT im Manifest — das führt nur IDs. Sie steht im
# Frontmatter jeder Check-Datei, und deshalb braucht diese Prüfung die Dateien
# selbst.
#
# EIN ARCHIV STATT 120 ABRUFE. Der Wochenplan holt den Baum einmal als Tarball
# und legt `checks/` ab. Das ist ein Abruf statt einer Schleife — und es
# beseitigt ein Rennen, das die getrennten Abrufe hatten: Manifest und
# Check-Dateien stammen jetzt zwingend aus demselben Commit. Vorher konnte
# zwischen beiden ein Release liegen, und der Befund hätte einen Katalog
# beschrieben, den es nie gab.
CHECKS_DIR_ENV = "CATALOGUE_CHECKS_DIR"
CHECKS_URL = (
    "https://codeload.github.com/malkreide/mcp-audit-skill/tar.gz/refs/heads/main"
)

CHECK_ID = re.compile(r"[A-Z]{2,6}-\d{3}")
LINKED = re.compile(r"/checks/([A-Z]{2,6}-\d{3})\.md")

# Nur der Frontmatter, nicht der Fliesstext: `adoption:` kommt drüben auch in
# Begründungen vor, und ein Treffer im Prosateil würde die Einstufung aus einem
# Satz lesen statt aus dem Feld.
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
ADOPTION_FIELD = re.compile(r"^adoption:[ \t]*(?P<value>\S+)", re.M)

# Fehlt das Feld, gilt drüben `enforced`. Genau diese Vorgabe ist der Grund,
# warum die Behauptung hier falsch werden konnte: Vier Checks tragen kein
# `adoption`, und wer nur nach dem Wort sucht, findet sie nicht und hält sie
# für unverbindlich.
DEFAULT_ADOPTION = "enforced"

# Der Satz, der die Einstufung behauptet. Passt er nicht mehr, ist das ein
# Befund und kein Grund weiterzumachen — dieselbe Entscheidung wie bei STATE:
# Eine umformulierte Behauptung stillschweigend nicht mehr zu prüfen, wäre der
# Ausfall, der wie ein Bestehen aussieht.
ADOPTION_CLAIM = re.compile(
    r"\*\*(?P<count>\w+) Checks dieser Tabelle sind `enforced`[^:]*:\*\*"
    r"(?P<enforced>.*?)"
    r"`advisory` sind (?P<advisory>[^:]*):",
    re.S,
)

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


def read_adoption(checks_dir: Path, wanted: set[str]) -> dict[str, str]:
    """Die Einstufung je Check, aus dem Frontmatter der Datei drüben.

    Gelesen wird nur, was die Tabelle **verlinkt** — 13 Dateien statt 120. Die
    Behauptung hier ist eine über *diese* Tabelle; ein Check, den sie nicht
    nennt, kann sie auch nicht falsch einstufen.
    """
    adoption: dict[str, str] = {}
    missing: list[str] = []
    for check_id in sorted(wanted):
        path = checks_dir / f"{check_id}.md"
        if not path.is_file():
            missing.append(check_id)
            continue
        front = FRONTMATTER.match(path.read_text(encoding="utf-8"))
        if front is None:
            raise CheckFailed(
                f"{check_id}.md drüben hat keinen Frontmatter-Block — Format "
                "geändert, die Einstufung bliebe sonst ungeprüft"
            )
        field = ADOPTION_FIELD.search(front.group(1))
        adoption[check_id] = field.group("value") if field else DEFAULT_ADOPTION
    if missing:
        raise CheckFailed(
            f"Im abgelegten Katalog fehlen die Check-Dateien {missing} — der "
            "Abruf ist unvollständig oder die Dateien sind umgezogen. Die "
            "Einstufung ist damit ungeprüft, nicht falsch."
        )
    return adoption


def assert_adoption_matches(section: str, adoption: dict[str, str]) -> list[str]:
    """Die behauptete Einstufung gegen die gemessene.

    **Warum das eine eigene Zusicherung ist und nicht in den Zahlen aufgeht:**
    Der Satz «`ARCH-003` ist der einzige `enforced` Check dieser Tabelle» stand
    hier, während vier `FID`-Checks ebenfalls `enforced` waren. Jede Summe
    dieser Prüfung war dabei richtig. Eine Einstufung ist kein Zählwert — sie
    sagt, ob ein Verstoss blockiert, und das ist die Aussage, auf die jemand
    seinen Build stützt.
    """
    claim = ADOPTION_CLAIM.search(section)
    if not claim:
        raise CheckFailed(
            "SKILL.md: der Satz zur Einstufung passt nicht mehr auf "
            "'**<Wort> Checks dieser Tabelle sind `enforced` …:**  … "
            "`advisory` sind …:' — umformuliert, damit bliebe die Einstufung "
            "ungeprüft"
        )

    claimed_enforced = set(CHECK_ID.findall(claim.group("enforced")))
    claimed_advisory = set(CHECK_ID.findall(claim.group("advisory")))
    claimed_count = GERMAN_NUMBERS.get(claim.group("count").lower())

    problems: list[str] = []

    # 1) Das Zahlwort gegen die eigene Aufzählung. Fängt den Fall, in dem
    #    jemand einen Check ergänzt und die Zahl davor stehen lässt.
    if claimed_count != len(claimed_enforced):
        problems.append(
            f"Einstufung: der Satz sagt {claim.group('count')!r} "
            f"({claimed_count}) `enforced`, zählt aber {len(claimed_enforced)} "
            f"auf ({sorted(claimed_enforced)})"
        )

    # 2) Die beiden Listen müssen die verlinkten Checks GENAU aufteilen. Ohne
    #    das könnte ein neu verlinkter Check unerwähnt bleiben — und
    #    Nichterwähnung liest sich wie «nicht betroffen».
    both = claimed_enforced & claimed_advisory
    if both:
        problems.append(f"Einstufung: {sorted(both)} steht in beiden Listen")
    unclassified = sorted(set(adoption) - claimed_enforced - claimed_advisory)
    if unclassified:
        problems.append(
            f"Einstufung: {unclassified} ist verlinkt, aber weder als "
            "`enforced` noch als `advisory` genannt"
        )
    phantom = sorted((claimed_enforced | claimed_advisory) - set(adoption))
    if phantom:
        problems.append(
            f"Einstufung: {phantom} wird eingestuft, ist aber in der Tabelle "
            "gar nicht verlinkt"
        )

    # 3) Der eigentliche Abgleich, je Check.
    for check_id, measured in sorted(adoption.items()):
        claimed = (
            "enforced"
            if check_id in claimed_enforced
            else "advisory"
            if check_id in claimed_advisory
            else None
        )
        if claimed is not None and claimed != measured:
            note = (
                " (die Datei führt kein `adoption`-Feld, damit gilt `enforced`)"
                if measured == DEFAULT_ADOPTION
                else ""
            )
            problems.append(
                f"Einstufung {check_id}: hier `{claimed}`, drüben `{measured}`{note}"
            )
    return problems


def assert_table_matches(ids: list[str], skill: str, adoption: dict[str, str]) -> str:
    """Die reine Logik: Tabelle gegen Katalog, ohne Netz und ohne Dateien.

    `adoption` ist die gemessene Einstufung je verlinktem Check. Sie kommt aus
    Dateien und deshalb von aussen — diese Funktion bleibt damit rein und
    gegen einen Fixture-Baum fahrbar.

    Der Parameter ist **verpflichtend und hat keinen Vorgabewert**. Ein
    `adoption=None`, das die Einstufung stillschweigend überspringt, wäre
    genau die Bequemlichkeit, gegen die diese Prüfung geschrieben ist: Ein
    Aufrufer, der ihn vergisst, bekäme ein Grün für etwas, das nie angesehen
    wurde.
    """
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
    # daran falsch angeschlagen. Die Tabelle nannte damals ein `FID-007`, das
    # es absichtlich nicht gab («statt ein `FID-007` zu eröffnen»), und ein
    # Wächter, der eine korrekte Gegenrede als Fehler meldet, ist der
    # Fehlalarm aus Regel 5. Ein toter *Link* dagegen ist immer ein Befund.
    #
    # Das Beispiel ist inzwischen Geschichte — `FID-007` gibt es seit dem
    # 7.8.2026 wirklich, und die Tabelle verlinkt es bei Regel 14. Die
    # Unterscheidung bleibt trotzdem richtig, und zwar unabhängig von diesem
    # einen Fall: Eine Erwähnung kann eine Gegenrede sein, ein Link nie.
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
    #    Das ist richtig so, denn der Satz, der sie damals nannte («statt ein
    #    `FID-007` zu eröffnen»), wäre an diesem Tag falsch.
    #
    #    DIESER TAG WAR DER 7.8.2026, und der Punkt hat gehalten: `FID-007`
    #    ging drüben auf, dieser Punkt schlug an, und der Satz oben war
    #    tatsächlich falsch geworden — er nennt inzwischen keine Nummer mehr.
    #    Die Vorhersage steht hier stehen geblieben, weil sie eingetroffen
    #    ist und nicht, obwohl.
    unlinked = sorted(fid - linked)
    if unlinked:
        problems.append(
            f"Neu im Katalog und in der Tabelle nicht verlinkt: {unlinked} — "
            "welche Regel deckt er ab?"
        )

    # 4) Die Einstufung — der Teil, den keine Summe fängt.
    problems.extend(assert_adoption_matches(section, adoption))

    if problems:
        raise CheckFailed(
            "DRIFT — die Zuordnungstabelle in SKILL.md ist gegenüber dem "
            "Katalog veraltet:\n\n"
            + "\n".join(f"  - {p}" for p in problems)
            + "\n\nQuelle ist die Check-Datei drüben, nicht deren CHANGELOG."
        )

    enforced = [k for k, v in adoption.items() if v == DEFAULT_ADOPTION]
    return (
        f"{claimed_total} Checks, {claimed_cats} Kategorien, {claimed_fid} in "
        f"FID; alle {len(linked)} verlinkten Checks existieren, alle FID-Checks "
        f"sind verlinkt; Einstufung stimmt für alle {len(adoption)}, davon "
        f"{len(enforced)} `enforced`"
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
            f".github/workflows/weekly-drift.yml ({MANIFEST_URL}). FAIL "
            "statt skip: Eine übersprungene Prüfung meldete «bestanden», wo "
            "«nicht gelaufen» richtig wäre."
        )
    path = Path(raw)
    if not path.is_file():
        raise CheckFailed(f"${MANIFEST_ENV} zeigt auf {raw}, dort liegt keine Datei")

    raw_dir = os.environ.get(CHECKS_DIR_ENV)
    if not raw_dir:
        raise CheckFailed(
            f"${CHECKS_DIR_ENV} ist nicht gesetzt — ohne die Check-Dateien "
            "bleibt die Einstufung (`enforced`/`advisory`) ungeprüft. Der "
            f"Abruf steht in .github/workflows/weekly-drift.yml ({CHECKS_URL}). "
            "FAIL statt der halben Prüfung: Eine Prüfung, die stillschweigend "
            "weniger prüft als ihr Name sagt, meldet «bestanden» für etwas, "
            "das sie nicht angesehen hat."
        )
    checks_dir = Path(raw_dir)
    if not checks_dir.is_dir():
        raise CheckFailed(
            f"${CHECKS_DIR_ENV} zeigt auf {raw_dir}, dort liegt kein Verzeichnis"
        )

    skill = read_skill(root)
    linked = set(LINKED.findall(table_section(skill)))
    return assert_table_matches(
        parse_manifest(path.read_text(encoding="utf-8")),
        skill,
        read_adoption(checks_dir, linked),
    )
