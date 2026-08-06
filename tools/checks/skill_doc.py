"""Prüfungen an SKILL.md — dem Dokument, das der Skill selbst ist.

Die Zusage «drei Kernschritte» steht an vier Stellen, drei davon hier und eine
ausserhalb jeder Datei (die GitHub-Description, siehe `github_meta`). Vier
Stellen für eine Zahl sind drei zu viel, aber keine davon lässt sich
streichen: Frontmatter ist Metadatum, die Markierungen sind die Struktur, das
Zahlwort ist Prosa. Was bleibt, ist sie gegeneinander zu halten.
"""

from __future__ import annotations

import re
from pathlib import Path

from ._core import CheckFailed, register

FRONTMATTER = re.compile(r"^---\nname: (.+?)\ndescription: (.+?)\n---\n", re.S)
EXPECTED_NAME = "mcp-data-source-probe"
DESCRIPTION_LIMIT = 1024

# Bis «zehn», damit die nächsten Schritte den Wortschatz nicht sprengen: Ein
# Zahlwort, das hier fehlt, ergäbe sonst dieselbe Meldung wie ein echter
# Zahlendreher — der Befund zeigte dann auf die falsche Datei.
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

# Die Ziffer im Frontmatter. `github_meta` hält die GitHub-Description gegen
# denselben Ausdruck — wer ihn hier ändert, muss dort mitziehen.
CLAIM = re.compile(r"Standardisiertes (?P<n>\d+)-Schritte-Vorgehen")


def read_skill(root: Path) -> str:
    path = root / "SKILL.md"
    if not path.is_file():
        raise CheckFailed("SKILL.md: missing")
    return path.read_text(encoding="utf-8")


def core_step_count(text: str) -> int:
    """Die Ziffer aus dem Frontmatter — die eine normative Quelle.

    Steht bewusst hier und nicht in `github_meta`: Check 11 belegt bei jedem
    Lauf, dass diese Ziffer der Zahl der [Kern]-Schritte entspricht. Erst
    deshalb darf die CI die GitHub-Description gegen sie halten, statt gegen
    eine zweite gepflegte Zahl.
    """
    claim = CLAIM.search(text)
    if not claim:
        raise CheckFailed(
            "SKILL.md: die Frontmatter-Wendung 'Standardisiertes "
            "<N>-Schritte-Vorgehen' ist weg — Anker entfernt oder "
            "umformuliert. Sie ist es, wogegen die CI die GitHub-Description "
            "hält; sie zu verlieren stoppt zwei Prüfungen, nicht eine"
        )
    return int(claim.group("n"))


@register(5, "SKILL.md carries a well-formed frontmatter")
def frontmatter(root: Path) -> str:
    match = FRONTMATTER.match(read_skill(root))
    if not match:
        raise CheckFailed("SKILL.md: frontmatter missing or malformed")
    name, description = match.group(1).strip(), match.group(2).strip()
    if name != EXPECTED_NAME:
        raise CheckFailed(f"SKILL.md: expected name {EXPECTED_NAME!r}, got {name!r}")
    if len(description) > DESCRIPTION_LIMIT:
        raise CheckFailed(
            f"SKILL.md: description too long ({len(description)} > {DESCRIPTION_LIMIT})"
        )
    # Als verbleibender Spielraum ausgegeben, nicht bloss als Länge: Die
    # Grenze ist nah genug, dass eine ergänzte Trigger-Wendung sie in einer
    # Bearbeitung reisst.
    left = DESCRIPTION_LIMIT - len(description)
    return (
        f"SKILL.md: name={name}, description={len(description)}/"
        f"{DESCRIPTION_LIMIT} chars ({left} left)"
    )


@register(6, "cross-references resolve to real sections")
def cross_references(root: Path) -> str:
    text = read_skill(root)
    headings = set(re.findall(r"^#{2,4} (\d+\.\d+[a-z]?)", text, re.M))
    referenced = set(re.findall(r"\((\d+\.\d+)[a-z]?\)", text))
    # Beide Seiten sind Anker, aber sie fallen unterschiedlich aus — der
    # Mutationstest fährt beide Fälle:
    #
    #   referenced leer (Klammer-Notation ersetzt): Die Differenz unten ist
    #   zwangsläufig leer, die Prüfung meldet «alle aufgelöst» und prüft in
    #   Wahrheit nichts mehr. Ohne diesen Wächter still grün.
    #
    #   headings leer (Nummerierungsschema geändert): Die Prüfung wird auch
    #   ohne Wächter rot — aber mit einem Befund, der elf angeblich fehlende
    #   Abschnitte auflistet, statt die eine echte Ursache zu nennen. Wer dem
    #   Befund folgt, repariert elf Verweise, die in Ordnung sind.
    if not headings:
        raise CheckFailed(
            "SKILL.md: keine nummerierte Überschrift '## N.M' gefunden — das "
            "Nummerierungsschema hat sich geändert oder ist weg, diese "
            "Prüfung würde stillschweigend aufhören zu prüfen"
        )
    if not referenced:
        raise CheckFailed(
            "SKILL.md: kein Querverweis '(N.M)' gefunden — die "
            "Verweisnotation hat sich geändert oder ist weg, diese Prüfung "
            "würde stillschweigend aufhören zu prüfen"
        )
    missing = sorted(
        r for r in referenced if not any(h.startswith(r) for h in headings)
    )
    if missing:
        raise CheckFailed(f"SKILL.md references non-existent sections: {missing}")
    return (
        f"{len(headings)} numbered sections, {len(referenced)} referenced, all resolve"
    )


@register(11, "the core-step count agrees everywhere in SKILL.md")
def step_count(root: Path) -> str:
    # Die Zusage dieses Skills ist ein Vorgehen aus DREI Kernschritten;
    # Schritt 4 und 5 sind Übergabe und zählen nicht mit. Das stand schon
    # immer im Text («durchläuft die drei Schritte unten», «nach Abschluss
    # der Probe (Schritt 1-3)»), aber nirgends so, dass eine Prüfung es hätte
    # lesen können. Deshalb trägt jede Schritt-Überschrift ihre Einordnung
    # als [Kern] oder [Übergabe].
    text = read_skill(root)

    # Zuerst ohne Marker suchen: So unterscheidet der Befund «Überschriften
    # weg» von «Überschriften da, aber unmarkiert».
    raw = re.findall(r"^## Schritt (\d+):(.*)$", text, re.M)
    if not raw:
        raise CheckFailed(
            "SKILL.md: keine Überschrift '## Schritt N:' gefunden — Anker weg "
            "oder umformuliert, diese Prüfung würde stillschweigend aufhören "
            "zu prüfen"
        )

    numbers = [int(n) for n, _ in raw]
    if numbers != list(range(1, len(numbers) + 1)):
        raise CheckFailed(f"SKILL.md: step headings are not sequential: {numbers}")

    # JEDER Schritt braucht eine Markierung. Kern aus dem FEHLEN einer
    # Markierung abzuleiten wäre die teure Variante: Ein neu eingefügter
    # Schritt ohne Marker zählte still als Kern und bliese die Zusage auf,
    # ohne dass irgendetwas rot würde.
    kinds = []
    for num, rest in raw:
        marker = re.search(r"\[(Kern|Übergabe)\]\s*$", rest)
        if not marker:
            raise CheckFailed(
                f"SKILL.md: '## Schritt {num}:' trägt keine Markierung [Kern] "
                "oder [Übergabe].\n"
                "  Jeder Schritt braucht eine — ein unmarkierter Schritt "
                "zählte sonst als Kern und bliese die Zusage auf, ohne dass "
                "etwas rot wird."
            )
        kinds.append(marker.group(1))

    # Kern muss ein zusammenhängender Anfang sein. Ein [Kern] hinter einem
    # [Übergabe] hiesse, dass nach der Übergabe noch Verfahren kommt — dann
    # stimmt entweder die Reihenfolge nicht oder die Einordnung.
    core = sum(1 for k in kinds if k == "Kern")
    if kinds[:core] != ["Kern"] * core:
        raise CheckFailed(
            f"SKILL.md: die Kernschritte sind kein zusammenhängender Anfang: "
            f"{kinds}.\n"
            "  Ein [Kern]-Schritt nach einem [Übergabe]-Schritt heisst, dass "
            "entweder die Reihenfolge oder die Einordnung nicht stimmt."
        )
    if core == 0:
        raise CheckFailed(
            "SKILL.md: kein Schritt ist [Kern] — die Zusage wäre ein Vorgehen "
            "aus null Schritten, und das ist nichts"
        )

    claimed = core_step_count(text)
    if claimed != core:
        raise CheckFailed(
            f"SKILL.md: das Frontmatter verspricht {claimed} Schritte, das "
            f"Dokument markiert {core} als [Kern] (von {len(kinds)} "
            "insgesamt).\n"
            "  Entweder kam ein Kernschritt dazu, ohne dass die Zusage "
            "mitging, oder ein Schritt hat die Art gewechselt — prüfen, "
            "welche Seite sich bewegt hat."
        )

    # Das Zahlwort in der Einleitung ist die dritte Stelle im Dokument. Es
    # liest sich als Prosa und veraltet genau deshalb unbemerkt.
    lead = re.search(r"durchläuft die (?P<word>\w+) Schritte unten", text)
    if not lead:
        raise CheckFailed(
            "SKILL.md: der Satz 'durchläuft die <Zahlwort> Schritte unten' "
            "ist weg — Anker entfernt oder umformuliert, diese Prüfung würde "
            "aufhören, die eine als Prosa geschriebene Zusage zu prüfen"
        )
    word = lead.group("word")
    if word not in GERMAN_NUMBERS:
        raise CheckFailed(
            f"SKILL.md: die Einleitung sagt {word!r}, und das ist kein "
            "Zahlwort, das diese Prüfung kennt — GERMAN_NUMBERS in "
            "tools/checks/skill_doc.py ergänzen, sonst meldet der Vergleich "
            "unten eine Abweichung, die in Wahrheit eine Lücke hier ist"
        )
    if GERMAN_NUMBERS[word] != core:
        raise CheckFailed(
            f"SKILL.md: die Einleitung sagt {word!r} "
            f"({GERMAN_NUMBERS[word]}) Schritte, {core} sind [Kern]"
        )

    handover = len(kinds) - core
    return (
        f"{core} core step(s) + {handover} handover, frontmatter, intro and "
        "markers agree"
    )
