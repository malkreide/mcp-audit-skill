"""Die GitHub-Description behauptet Zahlen. Stimmen sie noch?

Zusammengefuehrt aus `mcp-data-source-probe-skill`,
`mcp-transport-hardening-skill` (beide `github_meta.py`),
`mcp-data-fidelity-skill` (`repo_metadata.py`) und `tools/check_repo_description.py`
dieses Repos — Familie G13 des Merge-Plans, vier Fassungen derselben Frage.

WARUM DAS UEBERHAUPT EINE PRUEFUNG BRAUCHT. Die Description liegt AUSSERHALB
jeder Arbeitskopie. Kein Commit aendert sie, kein Test der Arbeitskopie
erreicht sie — also driftet sie, und zwar unbemerkt. Sie ist zugleich die
erste Zeile, die jemand liest.

DIE VIER FASSUNGEN PRUEFTEN DASSELBE IN VIER FORMEN:

* dieses Repo zwei ZAHLEN («120 Checks», «12 Kategorien»),
* probe ein ZAHLWORT in einer Wendung («three-step core procedure»),
* transport ein Zahlwort in einer anderen («twelve transport-hardening rules»),
* fidelity wieder anders.

Verallgemeinert ist das eine Liste von ZUSAGEN: je ein Muster mit einer
Gruppe `wert` und die Zahl, die dort stehen muss. Ob dort eine Ziffer oder ein
englisches Zahlwort steht, entscheidet der Text, nicht die Pruefung.

DER GUARD SCHREIBT NICHT. Eine Description zu setzen braucht ein Token mit
Administrationsrechten, und Repo-Metadaten zu aendern gehoert einem Menschen.
Der Guard benennt die Abweichung und druckt das fertige `gh`-Kommando.
"""

from __future__ import annotations

import re

from tools.harness import CheckFailed

#: Zahlwoerter, wie sie in den Descriptions der Kette vorkommen. Ein
#: unbekanntes Wort ist ein Befund UEBER DIESE LISTE und nicht ueber das
#: Repository — sonst meldete der Vergleich eine Abweichung, die in Wahrheit
#: eine Luecke hier ist.
ENGLISH_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def as_number(token: str) -> int | None:
    """Eine Ziffernfolge oder ein englisches Zahlwort als Zahl, sonst `None`."""
    if token.isdigit():
        return int(token)
    return ENGLISH_NUMBERS.get(token.lower())


def assert_description_matches(
    description: str,
    *,
    claims: tuple[tuple[str, re.Pattern[str], int], ...],
    repo_slug: str = "<owner>/<repo>",
) -> str:
    """Die reine Logik — ohne Netz, ohne Umgebung, ohne Datei.

    Getrennt, damit die Tests genau das fahren koennen, was hier schiefgehen
    kann: fehlender Anker, unbekanntes Zahlwort, Abweichung.

    Ein FEHLENDER ANKER ist der teuerste der drei Faelle und deshalb der erste
    im Text: Wurde die Wendung umformuliert, hoert diese Pruefung auf zu
    pruefen, ohne es zu sagen.
    """
    if not claims:
        raise CheckFailed(
            "Keine Zusage genannt — dann prueft diese Pruefung nichts und "
            "meldete genau das als Erfolg."
        )

    befunde = []
    bestaetigt = []
    for label, muster, erwartet in claims:
        # ALLE Vorkommen, nicht nur das erste — uebernommen aus
        # `tools/check_repo_description.py` dieses Repos, der einzigen der vier
        # Fassungen, die das tat. Eine Description, die dieselbe Zusage zweimal
        # mit verschiedenen Zahlen macht, ist in sich widerspruechlich; wer nur
        # das erste Vorkommen liest, meldet sie als in Ordnung.
        alle = list(muster.finditer(description))
        treffer = alle[0] if alle else None
        if not treffer:
            befunde.append(
                f"{label}: die Description traegt die erwartete Wendung nicht "
                f"(Muster {muster.pattern!r}).\n"
                "      Entweder wurde sie umformuliert — dann diesen Anker im "
                "selben Commit nachziehen — oder die Zusage wurde gestrichen. "
                "Ein Anker, der weg ist, laesst diese Pruefung aufhoeren zu "
                "pruefen, ohne es zu sagen."
            )
            continue
        rohwerte = sorted({m.group("wert") for m in alle})
        rohwert = rohwerte[0]
        wert = as_number(rohwert)
        if len(rohwerte) > 1:
            befunde.append(
                f"{label}: die Description nennt mehrere Werte {rohwerte} fuer "
                "dieselbe Zusage — sie widerspricht sich selbst, und welcher "
                "davon gemeint ist, kann diese Pruefung nicht entscheiden."
            )
            continue
        if wert is None:
            befunde.append(
                f"{label}: die Description sagt {rohwert!r}, und das ist keine "
                "Zahl, die diese Pruefung kennt — ENGLISH_NUMBERS in "
                "tools/gates/repo_meta.py ergaenzen. Sonst meldete der "
                "Vergleich eine Abweichung, die in Wahrheit eine Luecke hier "
                "ist."
            )
            continue
        if wert != erwartet:
            befunde.append(
                f"{label}: die Description nennt {wert}, das Repository hat {erwartet}."
            )
            continue
        bestaetigt.append(f"{label}={wert}")

    if befunde:
        raise CheckFailed(
            "Die GitHub-Description stimmt nicht mehr:\n"
            + "\n".join(f"  - {b}" for b in befunde)
            + f"\n  Gelesen wurde: {description!r}\n"
            "  Sie liegt ausserhalb des Repositories — kein Commit repariert "
            "sie:\n"
            f'    gh repo edit {repo_slug} --description "…"'
        )
    return "Description stimmt: " + ", ".join(bestaetigt)
