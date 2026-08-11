"""Frontmatter, Querverweise und Schrittzahl des Probe-Skills.

DIE ZUSAGE «DREI KERNSCHRITTE» STEHT AN VIER STELLEN: als Ziffer im
Frontmatter, als `[Kern]`-Markierung an den Ueberschriften, als Zahlwort in
der Einleitung und — bis Phase 5 — als GitHub-Description. Vier Stellen fuer
eine Zahl sind drei zu viel, aber keine laesst sich streichen: Frontmatter ist
Metadatum, die Markierungen sind die Struktur, das Zahlwort ist Prosa.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.gates import skill_doc as gates
from tools.harness import CheckFailed, register

from ._suite import SUITE

BASE = "skills/mcp-data-source-probe"
SKILL_PATH = f"{BASE}/SKILL.md"
EXPECTED_NAME = "mcp-data-source-probe"

#: Bis «zehn», damit die naechsten Schritte den Wortschatz nicht sprengen: Ein
#: Zahlwort, das hier fehlt, ergaebe sonst dieselbe Meldung wie ein echter
#: Zahlendreher — der Befund zeigte dann auf die falsche Datei.
GERMAN_NUMBERS = {
    "einen": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
}

#: Die Ziffer im Frontmatter. Bis Phase 5 haelt eine GitHub-Description
#: draussen dieselbe Zahl; wer diesen Ausdruck aendert, stoppt zwei Pruefungen
#: und nicht eine.
CLAIM = re.compile(r"Standardisiertes (?P<n>\d+)-Schritte-Vorgehen")

SCHRITT = re.compile(r"^## Schritt (\d+):(.*)$", re.M)
MARKIERUNG = re.compile(r"\[(Kern|Übergabe)\]\s*$")


def read_skill(root: Path) -> str:
    pfad = root / SKILL_PATH
    if not pfad.is_file():
        raise CheckFailed(
            f"{SKILL_PATH} fehlt — ohne die Datei hat diese Pruefung nichts zu "
            "lesen und meldete das als Erfolg."
        )
    return pfad.read_text(encoding="utf-8")


def core_step_count(text: str) -> int:
    """Die Ziffer aus dem Frontmatter — die eine normative Quelle."""
    claim = CLAIM.search(text)
    if not claim:
        raise CheckFailed(
            f"{SKILL_PATH}: die Frontmatter-Wendung 'Standardisiertes "
            "<N>-Schritte-Vorgehen' ist weg — Anker entfernt oder "
            "umformuliert."
        )
    return int(claim.group("n"))


def step_kinds(text: str) -> list[str]:
    """Die Einordnung jeder Schritt-Ueberschrift, in Dokumentreihenfolge.

    Steht als eigene Funktion, weil ZWEI Pruefungen sie brauchen: `probe/11`
    haelt sie gegen Frontmatter und Einleitung, `probe/19` gegen die
    Schritt-Aufzaehlung der beiden READMEs. Ein zweites Mal hingeschrieben
    waere sie ein zweiter Ort zum Auseinanderlaufen — und eine Pruefung, die
    eine andere Aufteilung liest als die daneben, meldete eine Abweichung, die
    es im Dokument gar nicht gibt.
    """
    # Zuerst OHNE Markierung suchen: So unterscheidet der Befund
    # «Ueberschriften weg» von «Ueberschriften da, aber unmarkiert».
    roh = SCHRITT.findall(text)
    if not roh:
        raise CheckFailed(
            f"{SKILL_PATH}: keine Ueberschrift '## Schritt N:' gefunden — "
            "Anker weg oder umformuliert; diese Pruefung wuerde "
            "stillschweigend aufhoeren zu pruefen."
        )

    nummern = [int(n) for n, _ in roh]
    if nummern != list(range(1, len(nummern) + 1)):
        raise CheckFailed(
            f"{SKILL_PATH}: die Schritt-Ueberschriften sind nicht fortlaufend: "
            f"{nummern}"
        )

    # JEDER Schritt braucht eine Markierung. Kern aus dem FEHLEN einer
    # Markierung abzuleiten waere die teure Variante: Ein neu eingefuegter
    # Schritt ohne Marker zaehlte still als Kern und bliese die Zusage auf,
    # ohne dass irgendetwas rot wuerde.
    arten: list[str] = []
    for nummer, rest in roh:
        marker = MARKIERUNG.search(rest)
        if not marker:
            raise CheckFailed(
                f"{SKILL_PATH}: '## Schritt {nummer}:' traegt keine "
                "Markierung [Kern] oder [Übergabe].\n"
                "  Jeder Schritt braucht eine — ein unmarkierter Schritt "
                "zaehlte sonst als Kern und bliese die Zusage auf, ohne dass "
                "etwas rot wird."
            )
        arten.append(marker.group(1))

    # Kern muss ein zusammenhaengender Anfang sein. Ein [Kern] hinter einem
    # [Übergabe] hiesse, dass nach der Uebergabe noch Verfahren kommt — dann
    # stimmt entweder die Reihenfolge nicht oder die Einordnung.
    kern = sum(1 for a in arten if a == "Kern")
    if arten[:kern] != ["Kern"] * kern:
        raise CheckFailed(
            f"{SKILL_PATH}: die Kernschritte sind kein zusammenhaengender "
            f"Anfang: {arten}.\n"
            "  Ein [Kern]-Schritt nach einem [Übergabe]-Schritt heisst, dass "
            "entweder die Reihenfolge oder die Einordnung nicht stimmt."
        )
    if kern == 0:
        raise CheckFailed(
            f"{SKILL_PATH}: kein Schritt ist [Kern] — die Zusage waere ein "
            "Vorgehen aus null Schritten, und das ist nichts."
        )
    return arten


@register(5, "SKILL.md carries a well-formed frontmatter", suite=SUITE)
def skill_frontmatter(root: Path) -> str:
    return gates.frontmatter(root, skill_path=SKILL_PATH, expected_name=EXPECTED_NAME)


@register(6, "cross-references resolve to real sections", suite=SUITE)
def cross_references(root: Path) -> str:
    """SKILL-EIGEN: Nur dieser Skill nummeriert seine Abschnitte als `N.M`.

    BEIDE SEITEN SIND ANKER, und sie fallen unterschiedlich aus:

      * `referenced` leer (Klammer-Notation ersetzt): Die Differenz unten
        waere zwangslaeufig leer, die Pruefung meldete «alle aufgeloest» und
        pruefte in Wahrheit nichts mehr. Ohne diesen Waechter still gruen.
      * `headings` leer (Nummerierungsschema geaendert): Die Pruefung wird
        auch ohne Waechter rot — aber mit einem Befund, der elf angeblich
        fehlende Abschnitte auflistet statt der einen echten Ursache. Wer dem
        Befund folgt, repariert elf Verweise, die in Ordnung sind.
    """
    text = read_skill(root)
    ueberschriften = set(re.findall(r"^#{2,4} (\d+\.\d+[a-z]?)", text, re.M))
    verwiesen = set(re.findall(r"\((\d+\.\d+)[a-z]?\)", text))
    if not ueberschriften:
        raise CheckFailed(
            f"{SKILL_PATH}: keine nummerierte Ueberschrift '## N.M' gefunden "
            "— das Nummerierungsschema hat sich geaendert oder ist weg; diese "
            "Pruefung wuerde stillschweigend aufhoeren zu pruefen."
        )
    if not verwiesen:
        raise CheckFailed(
            f"{SKILL_PATH}: kein Querverweis '(N.M)' gefunden — die "
            "Verweisnotation hat sich geaendert oder ist weg; diese Pruefung "
            "wuerde stillschweigend aufhoeren zu pruefen."
        )
    fehlend = sorted(
        v for v in verwiesen if not any(h.startswith(v) for h in ueberschriften)
    )
    if fehlend:
        raise CheckFailed(
            f"{SKILL_PATH}: verweist auf Abschnitte, die es nicht gibt: {fehlend}"
        )
    return (
        f"{len(ueberschriften)} nummerierte Abschnitte, {len(verwiesen)} "
        "verwiesen, alle aufgeloest"
    )


@register(11, "the core-step count agrees everywhere in SKILL.md", suite=SUITE)
def step_count(root: Path) -> str:
    """SKILL-EIGEN: Nur dieser Skill trennt Kern- von Uebergabeschritten.

    Das generische Zaehl-Gate (G14) zaehlt EINE Menge; hier sind es zwei, die
    zusammen die Ueberschriften ergeben, und die Zusage haengt an der
    kleineren. Eine generische Fassung dafuer haette einen Gegenstand.
    """
    text = read_skill(root)
    arten = step_kinds(text)
    kern = sum(1 for a in arten if a == "Kern")

    behauptet = core_step_count(text)
    if behauptet != kern:
        raise CheckFailed(
            f"{SKILL_PATH}: das Frontmatter verspricht {behauptet} Schritte, "
            f"das Dokument markiert {kern} als [Kern] (von {len(arten)} "
            "insgesamt).\n"
            "  Entweder kam ein Kernschritt dazu, ohne dass die Zusage "
            "mitging, oder ein Schritt hat die Art gewechselt — pruefen, "
            "welche Seite sich bewegt hat."
        )

    # Das Zahlwort in der Einleitung ist die dritte Stelle im Dokument. Es
    # liest sich als Prosa und veraltet genau deshalb unbemerkt.
    einleitung = re.search(r"durchläuft die (?P<wort>\w+) Schritte unten", text)
    if not einleitung:
        raise CheckFailed(
            f"{SKILL_PATH}: der Satz 'durchläuft die <Zahlwort> Schritte "
            "unten' ist weg — Anker entfernt oder umformuliert; diese "
            "Pruefung wuerde aufhoeren, die eine als Prosa geschriebene "
            "Zusage zu pruefen."
        )
    wort = einleitung.group("wort")
    if wort not in GERMAN_NUMBERS:
        raise CheckFailed(
            f"{SKILL_PATH}: die Einleitung sagt {wort!r}, und das ist kein "
            "Zahlwort, das diese Pruefung kennt — GERMAN_NUMBERS in "
            "tools/suites/mcp_data_source_probe/skill_doc.py ergaenzen.\n"
            "  Das ist eine Luecke HIER: Ohne diese Meldung stuende an dieser "
            "Stelle ein Befund ueber SKILL.md."
        )
    if GERMAN_NUMBERS[wort] != kern:
        raise CheckFailed(
            f"{SKILL_PATH}: die Einleitung sagt {wort!r} "
            f"({GERMAN_NUMBERS[wort]}) Schritte, {kern} sind [Kern]"
        )

    uebergabe = len(arten) - kern
    return (
        f"{kern} Kernschritt(e) + {uebergabe} Uebergabe; Frontmatter, "
        "Einleitung und Markierungen stimmen ueberein"
    )
