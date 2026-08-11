"""Die Zuordnungstabelle gegen den echten Katalog — jetzt im selben Commit.

DIESE PRUEFUNG IST DER GROESSTE EINZELNE ERTRAG DER ZUSAMMENFUEHRUNG, und ihr
Herkunfts-Docstring sagt selbst, warum. Er begruendete ausfuehrlich, dass sie
NICHT vor den Merge-Button gehoert:

  > «Das ist keine Eigenschaft eines Commits, sondern der verstrichenen Zeit:
  > Die Tabelle stand am 5. August zweimal falsch, ohne dass hier jemand etwas
  > geaendert haette. Ein zeitbasierter Fehler gehoert an einen Zeitplan,
  > nicht an einen Diff.»

Das stimmte — SOLANGE Tabelle und Katalog in verschiedenen Repositories lagen.
Genau diese Voraussetzung ist mit Phase 3a weggefallen. Der Katalog liegt
unter `checks/`, die Tabelle unter `skills/mcp-data-fidelity/SKILL.md`, beide
im selben Baum: Eine Abweichung ist damit keine Eigenschaft der verstrichenen
Zeit mehr, sondern eine des Diffs. Sie wird ein gewoehnliches PR-Gate.

WAS DAMIT ERSATZLOS ENTFAELLT — und es steht nur noch im Herkunftsrepo:

  * `scripts/linked_checks.py` (52 Zeilen), das dem Workflow sagte, welche
    Check-Dateien er ueberhaupt holen muss;
  * der Wochenplan-Workflow `weekly-drift.yml` (179 Zeilen), der Manifest und
    verlinkte Dateien per `raw.githubusercontent.com` ablegte — OHNE
    Pfad-Praefix genannt, wie schon in `tools/gates/workflows.py`: Ein
    `.github/workflows/…` hier waere ein Zeiger in DIESEN Baum, und
    `audit/15` liest ihn zu Recht als toten Verweis. Die Datei liegt im
    Herkunftsrepo; der Satz redet ueber einen fremden Baum;
  * `$CATALOGUE_MANIFEST`, `$CATALOGUE_CHECKS_DIR` und `$CATALOGUE_COMMIT`,
    ueber die der Workflow und die Pruefung sich verstaendigten;
  * und die Unterscheidung «nicht erreichbar» vs. «abgewichen», die es
    brauchte, damit ein Netzaussetzer nicht wie ein Befund aussieht.

Der gepinnte Commit war die aufwendigste dieser Vorkehrungen und ist die
lehrreichste: Zwei Abrufe von `main` koennten ein Release auseinanderliegen,
und der Befund beschriebe dann einen Katalog, den es nie gegeben hat. Ein
Arbeitsbaum kann das nicht — er IST ein Stand. Die Zusicherung ist damit nicht
schwaecher geworden, sondern billiger.

DREI GEGENSTAENDE, NICHT EINER. Die Pruefung haelt drei Dinge gegeneinander,
und das dritte ist spaeter dazugekommen, weil die ersten beiden es nicht
fangen:

  1. die ZAHLEN — Katalog-Groesse, Kategorien, `FID`-Anzahl,
  2. die IDENTITAETEN — jeder verlinkte Check existiert, jeder `FID`-Check ist
     verlinkt,
  3. die EINSTUFUNG — `enforced` oder `advisory`, je verlinktem Check.

Punkt 3 stammt aus einem Befund, den 1 und 2 durchgelassen haben: In SKILL.md
stand «`ARCH-003` ist der einzige `enforced` Check dieser Tabelle», waehrend
sechs weitere es ebenfalls waren. Jede Zahl stimmte dabei, und jede ID
existierte. Eine Einstufung ist kein Zaehlwert — sie sagt, ob ein Verstoss
blockiert, und das ist die Aussage, auf die jemand seinen Build stuetzt.

SKILL-EIGEN UND DESHALB HIER, nicht unter `tools/gates/`: Nur dieser Skill
fuehrt eine Zuordnung Regel → Katalog-Check. Eine generische Fassung haette
einen Gegenstand und zwoelf Parameter.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.harness import CheckFailed, register

from ._suite import SUITE
from .skill_doc import CHECK_ID, read_skill, table_section

#: Der Katalog. Kein Abruf, kein Pin, keine Umgebungsvariable — er liegt im
#: selben Baum wie die Tabelle, die ihn beschreibt.
MANIFEST = "checks/MANIFEST.txt"
CHECKS_DIR = "checks"

CHECK_ID_EXACT = re.compile(r"[A-Z]{2,6}-\d{3}")
LINKED = re.compile(r"/checks/([A-Z]{2,6}-\d{3})\.md")

#: Nur der Frontmatter, nicht der Fliesstext: `adoption:` kommt in den
#: Check-Dateien auch in Begruendungen vor, und ein Treffer im Prosateil wuerde
#: die Einstufung aus einem Satz lesen statt aus dem Feld.
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
ADOPTION_FIELD = re.compile(r"^adoption:[ \t]*(?P<value>\S+)", re.M)

#: Fehlt das Feld, gilt `enforced`. Genau diese Vorgabe ist der Grund, warum
#: die Behauptung drueben falsch werden konnte: Mehrere Checks tragen kein
#: `adoption`, und wer nur nach dem Wort sucht, findet sie nicht und haelt sie
#: fuer unverbindlich.
DEFAULT_ADOPTION = "enforced"

#: Der Satz, der die Einstufung behauptet. Passt er nicht mehr, ist das ein
#: Befund und kein Grund weiterzumachen — dieselbe Entscheidung wie bei STATE:
#: Eine umformulierte Behauptung stillschweigend nicht mehr zu pruefen, waere
#: der Ausfall, der wie ein Bestehen aussieht.
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


def als_zahl(wort: str, feld: str) -> int:
    """Ein deutsches Zahlwort, oder ein Befund UEBER DIESE TABELLE.

    BEIM UMZUG ERGAENZT, und der Grund ist ein Loch in der Herkunftsfassung:
    Dort stand `GERMAN_NUMBERS.get(...)`, und ein unbekanntes Wort wurde damit
    zu `None`. Der Vergleich darunter schlug dann an und meldete «Tabelle sagt
    'vier' (None), Katalog hat 4» — einen DRIFT, wo in Wahrheit dieser
    Tabelle ein Eintrag fehlt. Ein Befund, der auf die falsche Datei zeigt,
    kostet genau die Zeit, die diese Pruefungen sparen sollen.

    Der Fall ist nicht theoretisch: Die Tabelle faengt bei fuenf an, weil
    nichts darunter je vorkam. Faellt ein `enforced`-Check weg, kommt «vier».
    """
    zahl = GERMAN_NUMBERS.get(wort.lower())
    if zahl is None:
        raise CheckFailed(
            f"SKILL.md: {feld} sagt {wort!r}, und das ist kein Zahlwort, das "
            "diese Pruefung kennt — GERMAN_NUMBERS in "
            "tools/suites/mcp_data_fidelity/catalogue.py ergaenzen.\n"
            "  Das ist eine Luecke HIER und kein Drift dort: Ohne diese "
            "Meldung stuende an dieser Stelle ein Befund ueber den Katalog."
        )
    return zahl


STATE = re.compile(
    r"(?P<total>\d+) Checks in (?P<cats>\w+) Kategorien.*?"
    r"davon (?P<fid>\w+) in der Kategorie `FID`",
    re.S,
)


def parse_manifest(raw: str) -> list[str]:
    ids = [zeile.strip() for zeile in raw.splitlines() if zeile.strip()]
    if not ids or not all(CHECK_ID_EXACT.fullmatch(i) for i in ids):
        raise CheckFailed(
            f"{MANIFEST} sieht nicht aus wie eine Liste von Check-IDs — Format "
            "geaendert; diese Pruefung prueft sonst nichts."
        )
    return ids


def read_manifest(root: Path) -> list[str]:
    pfad = root / MANIFEST
    if not pfad.is_file():
        raise CheckFailed(
            f"{MANIFEST} fehlt — ohne den Katalog hat diese Pruefung nichts, "
            "wogegen sie die Tabelle haelt."
        )
    return parse_manifest(pfad.read_text(encoding="utf-8"))


def read_adoption(root: Path, wanted: set[str]) -> dict[str, str]:
    """Die Einstufung je Check, aus dem Frontmatter der Check-Datei.

    Gelesen wird nur, was die Tabelle **verlinkt** — dreizehn Dateien statt
    120. Die Behauptung ist eine ueber *diese* Tabelle; ein Check, den sie
    nicht nennt, kann sie auch nicht falsch einstufen.
    """
    verzeichnis = root / CHECKS_DIR
    if not verzeichnis.is_dir():
        raise CheckFailed(f"{CHECKS_DIR}/ fehlt — der Katalog ist nicht da.")

    adoption: dict[str, str] = {}
    fehlend: list[str] = []
    for check_id in sorted(wanted):
        pfad = verzeichnis / f"{check_id}.md"
        if not pfad.is_file():
            fehlend.append(check_id)
            continue
        front = FRONTMATTER.match(pfad.read_text(encoding="utf-8"))
        if front is None:
            raise CheckFailed(
                f"{CHECKS_DIR}/{check_id}.md hat keinen Frontmatter-Block — "
                "Format geaendert; die Einstufung bliebe sonst ungeprueft."
            )
        feld = ADOPTION_FIELD.search(front.group(1))
        adoption[check_id] = feld.group("value") if feld else DEFAULT_ADOPTION
    if fehlend:
        raise CheckFailed(
            f"Die Tabelle verlinkt {fehlend}, unter {CHECKS_DIR}/ liegt dazu "
            "keine Datei. Im Herkunftsrepo war das ein unvollstaendiger Abruf; "
            "hier ist es ein toter Link — der Katalog liegt daneben."
        )
    return adoption


def assert_adoption_matches(section: str, adoption: dict[str, str]) -> list[str]:
    """Die behauptete Einstufung gegen die gemessene.

    WARUM DAS EINE EIGENE ZUSICHERUNG IST UND NICHT IN DEN ZAHLEN AUFGEHT: Der
    Satz «`ARCH-003` ist der einzige `enforced` Check dieser Tabelle» stand
    dort, waehrend sechs weitere es ebenfalls waren. Jede Summe war dabei
    richtig.
    """
    claim = ADOPTION_CLAIM.search(section)
    if not claim:
        raise CheckFailed(
            "SKILL.md: der Satz zur Einstufung passt nicht mehr auf "
            "'**<Wort> Checks dieser Tabelle sind `enforced` …:**  … "
            "`advisory` sind …:' — umformuliert; damit bliebe die Einstufung "
            "ungeprueft."
        )

    behauptet_enforced = set(CHECK_ID.findall(claim.group("enforced")))
    behauptet_advisory = set(CHECK_ID.findall(claim.group("advisory")))
    behauptete_zahl = als_zahl(claim.group("count"), "der Einstufungssatz")

    befunde: list[str] = []

    # 1) Das Zahlwort gegen die eigene Aufzaehlung. Faengt den Fall, in dem
    #    jemand einen Check ergaenzt und die Zahl davor stehen laesst.
    if behauptete_zahl != len(behauptet_enforced):
        befunde.append(
            f"Einstufung: der Satz sagt {claim.group('count')!r} "
            f"({behauptete_zahl}) `enforced`, zaehlt aber "
            f"{len(behauptet_enforced)} auf ({sorted(behauptet_enforced)})"
        )

    # 2) Die beiden Listen muessen die verlinkten Checks GENAU aufteilen. Ohne
    #    das koennte ein neu verlinkter Check unerwaehnt bleiben — und
    #    Nichterwaehnung liest sich wie «nicht betroffen».
    beides = behauptet_enforced & behauptet_advisory
    if beides:
        befunde.append(f"Einstufung: {sorted(beides)} steht in beiden Listen")
    uneingestuft = sorted(set(adoption) - behauptet_enforced - behauptet_advisory)
    if uneingestuft:
        befunde.append(
            f"Einstufung: {uneingestuft} ist verlinkt, aber weder als "
            "`enforced` noch als `advisory` genannt"
        )
    phantom = sorted((behauptet_enforced | behauptet_advisory) - set(adoption))
    if phantom:
        befunde.append(
            f"Einstufung: {phantom} wird eingestuft, ist aber in der Tabelle "
            "gar nicht verlinkt"
        )

    # 3) Der eigentliche Abgleich, je Check.
    for check_id, gemessen in sorted(adoption.items()):
        behauptung = (
            "enforced"
            if check_id in behauptet_enforced
            else "advisory"
            if check_id in behauptet_advisory
            else None
        )
        if behauptung is not None and behauptung != gemessen:
            hinweis = (
                " (die Datei fuehrt kein `adoption`-Feld, damit gilt `enforced`)"
                if gemessen == DEFAULT_ADOPTION
                else ""
            )
            befunde.append(
                f"Einstufung {check_id}: hier `{behauptung}`, im Katalog "
                f"`{gemessen}`{hinweis}"
            )
    return befunde


def assert_table_matches(ids: list[str], skill: str, adoption: dict[str, str]) -> str:
    """Die reine Logik: Tabelle gegen Katalog, ohne Dateisystem.

    `adoption` ist die gemessene Einstufung je verlinktem Check. Sie kommt aus
    Dateien und deshalb von aussen — diese Funktion bleibt damit rein und
    gegen einen Fixture-Baum fahrbar.

    Der Parameter ist **verpflichtend und hat keinen Vorgabewert**. Ein
    `adoption=None`, das die Einstufung stillschweigend ueberspringt, waere
    genau die Bequemlichkeit, gegen die diese Pruefung geschrieben ist: Ein
    Aufrufer, der ihn vergisst, bekaeme ein Gruen fuer etwas, das nie
    angesehen wurde.
    """
    katalog = set(ids)
    kategorien = {i.split("-")[0] for i in ids}
    fid = {i for i in ids if i.startswith("FID-")}
    section = table_section(skill)

    befunde: list[str] = []

    # 1) Die Zahlen in der Kopfzeile.
    state = STATE.search(section)
    if not state:
        raise CheckFailed(
            "SKILL.md: der Satz zum Katalogstand passt nicht mehr auf "
            "'<N> Checks in <Wort> Kategorien … davon <Wort> in der Kategorie "
            "`FID`' — umformuliert; damit blieben die Zahlen ungeprueft."
        )
    behauptet_total = int(state.group("total"))
    behauptet_cats = als_zahl(state.group("cats"), "die Kategorien-Zahl")
    behauptet_fid = als_zahl(state.group("fid"), "die FID-Zahl")
    if behauptet_total != len(katalog):
        befunde.append(
            f"Katalog-Groesse: Tabelle sagt {behauptet_total}, {MANIFEST} hat "
            f"{len(katalog)}"
        )
    if behauptet_cats != len(kategorien):
        befunde.append(
            f"Kategorien: Tabelle sagt {state.group('cats')!r} "
            f"({behauptet_cats}), {MANIFEST} hat {len(kategorien)} "
            f"({sorted(kategorien)})"
        )
    if behauptet_fid != len(fid):
        befunde.append(
            f"FID-Checks: Tabelle sagt {state.group('fid')!r} ({behauptet_fid}), "
            f"{MANIFEST} hat {len(fid)} ({sorted(fid)})"
        )

    # 2) Jeder VERLINKTE Check muss existieren — und nur der.
    #
    # Bewusst nicht jede genannte ID: Der erste Lauf dieses Jobs ist genau
    # daran falsch angeschlagen. Die Tabelle nannte damals ein `FID-007`, das
    # es absichtlich nicht gab («statt ein `FID-007` zu eroeffnen»), und ein
    # Waechter, der eine korrekte Gegenrede als Fehler meldet, ist der
    # Fehlalarm aus Regel 5 dieses Skills. Ein toter *Link* dagegen ist immer
    # ein Befund. Eine Erwaehnung kann eine Gegenrede sein, ein Link nie.
    linked = set(LINKED.findall(section))
    weg = sorted(linked - katalog)
    if weg:
        befunde.append(
            f"Die Tabelle verlinkt {weg}, im Katalog gibt es sie nicht (mehr) — "
            "umbenannt, zurueckgezogen oder Tippfehler in der URL"
        )

    # 3) Ein FID-Check, den die Tabelle nicht VERLINKT, ist der Fall vom
    #    5. August: Genau so ist `FID-006` entstanden, waehrend dort «kein
    #    Check» stand.
    unverlinkt = sorted(fid - linked)
    if unverlinkt:
        befunde.append(
            f"Neu im Katalog und in der Tabelle nicht verlinkt: {unverlinkt} — "
            "welche Regel deckt er ab?"
        )

    # 4) Die Einstufung — der Teil, den keine Summe faengt.
    befunde.extend(assert_adoption_matches(section, adoption))

    if befunde:
        raise CheckFailed(
            "DRIFT — die Zuordnungstabelle in SKILL.md ist gegenueber dem "
            "Katalog veraltet:\n\n"
            + "\n".join(f"  - {b}" for b in befunde)
            + "\n\nQuelle ist die Check-Datei unter checks/, nicht deren "
            "CHANGELOG."
        )

    enforced = [k for k, v in adoption.items() if v == DEFAULT_ADOPTION]
    return (
        f"{behauptet_total} Checks, {behauptet_cats} Kategorien, "
        f"{behauptet_fid} in FID; alle {len(linked)} verlinkten Checks "
        f"existieren, alle FID-Checks sind verlinkt; Einstufung stimmt fuer "
        f"alle {len(adoption)}, davon {len(enforced)} `enforced`"
    )


@register(14, "SKILL.md matches the real catalogue", suite=SUITE)
def catalogue_drift(root: Path) -> str:
    """Der Einstieg — vier Zeilen, wo vorher ein Workflow stand.

    `offline=True` und damit im PR-Lauf: Der Katalog liegt im selben Commit.
    """
    skill = read_skill(root)
    verlinkt = set(LINKED.findall(table_section(skill)))
    return assert_table_matches(
        read_manifest(root), skill, read_adoption(root, verlinkt)
    )
