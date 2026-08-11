"""Versions-Badge und Schritt-Aufzaehlung der beiden READMEs."""

from __future__ import annotations

import re
from pathlib import Path

from tools.gates import readmes as gates
from tools.harness import CheckFailed, register

from ._suite import SUITE
from .skill_doc import BASE, SKILL_PATH, read_skill, step_kinds

#: Die Schritt-Aufzaehlung der beiden READMEs. Pro Sprache: die Ueberschrift
#: des Abschnitts, das Wort fuer EINEN Schritt und das fuer mehrere.
#:
#: Getrennte Woerter statt eines optionalen Suffixes, weil genau dieser
#: Unterschied das Urteil traegt: «Schritt 3» zaehlt als eigener
#: Aufzaehlungspunkt, «Schritte 4-6» ist die Sammelzeile fuer die Uebergabe.
#: Wer beides gleich laese, zaehlte die Sammelzeile als vierten Kernschritt.
STEP_SECTIONS = (
    (f"{BASE}/README.md", "Features", "Step", "Steps"),
    (f"{BASE}/README.de.md", "Funktionen", "Schritt", "Schritte"),
)

#: Die READMEs setzen ein Halbgeviert zwischen die beiden Zahlen. Als Escape
#: geschrieben, nicht als Zeichen: RUF001 beanstandet ein woertlich gesetztes
#: Halbgeviert zu Recht, weil es im Quelltext nicht vom Bindestrich zu
#: unterscheiden ist. Akzeptiert werden alle drei Striche — welchen ein Editor
#: einsetzt, ist Typografie und darf keinen Befund ausloesen.
SPAN_DASH = r"[-–—]"


@register(9, "version badge matches the latest CHANGELOG release", suite=SUITE)
def version_badge(root: Path) -> str:
    return gates.version_badge(root, base=BASE)


@register(19, "both READMEs enumerate the steps SKILL.md defines", suite=SUITE)
def readme_step_list(root: Path) -> str:
    """SKILL-EIGEN: die Kern/Uebergabe-Aufteilung, gespiegelt in Prosa.

    `probe/11` haelt die Aufteilung innerhalb von `SKILL.md` zusammen. Was es
    NICHT erreicht, sind die beiden READMEs: Sie zaehlen dieselben Schritte
    ein zweites Mal auf, und niemand hielt sie gegen die Quelle. Kaeme ein
    vierter Kernschritt dazu, listeten sie weiter «Step 1-3» samt «Steps 4-6»
    — vollstaendig aussehend und falsch.

    Das generische Zaehl-Gate (G14) kann das nicht ausdruecken: Es haelt EINE
    nummerierte Menge gegen eine andere. Hier stehen im Spiegel eine
    Aufzaehlung UND eine Sammelzeile mit zwei Zahlen, und beide Zahlen sind
    pruefbar.
    """
    arten = step_kinds(read_skill(root))
    kern = sum(1 for a in arten if a == "Kern")
    gesamt = len(arten)

    zeilen = []
    for name, ueberschrift, singular, plural in STEP_SECTIONS:
        pfad = root / name
        if not pfad.is_file():
            raise CheckFailed(f"{name} fehlt")
        abschnitt = re.search(
            rf"^## {re.escape(ueberschrift)}\n(.*?)(?=^## |\Z)",
            pfad.read_text(encoding="utf-8"),
            re.M | re.S,
        )
        if not abschnitt:
            raise CheckFailed(
                f"{name}: Abschnitt '## {ueberschrift}' nicht gefunden — "
                "Anker weg oder umformuliert; diese Pruefung wuerde "
                "stillschweigend aufhoeren zu pruefen."
            )
        rumpf = abschnitt.group(1)

        # Nur EINZELNE Nennungen zaehlen als Kernschritt. Die Sammelzeile
        # «Steps 4-6» benennt die Uebergabe; sie als Aufzaehlungspunkt
        # mitzuzaehlen hiesse, drei Schritte fuer einen zu nehmen.
        gelistet = [
            int(n) for n in re.findall(rf"^- \*\*{singular} (\d+) — ", rumpf, re.M)
        ]
        if not gelistet:
            raise CheckFailed(
                f"{name}: kein Aufzaehlungspunkt '- **{singular} N — ' im "
                f"Abschnitt '## {ueberschrift}' — Anker weg oder "
                "umformuliert; diese Pruefung wuerde aufhoeren, die "
                "Schritt-Liste zu pruefen."
            )
        if gelistet != list(range(1, kern + 1)):
            raise CheckFailed(
                f"{name}: der Abschnitt '## {ueberschrift}' zaehlt die "
                f"Schritte {gelistet} einzeln auf, {SKILL_PATH} markiert "
                f"{kern} als [Kern] (von {gesamt} insgesamt).\n"
                "  Entweder kam ein Kernschritt dazu, ohne dass die READMEs "
                "mitgingen, oder ein Schritt hat die Art gewechselt — "
                "pruefen, welche Seite sich bewegt hat."
            )

        uebergabe = gesamt - kern
        if uebergabe == 0:
            zeilen.append(f"{name}: {kern} Kernschritt(e) einzeln, keine Uebergabe")
            continue

        # Die Sammelzeile traegt zwei Zahlen, und beide sind pruefbar: Der
        # Anfang muss auf den letzten Kernschritt folgen, das Ende die
        # Gesamtzahl treffen. Eine Luecke dazwischen liesse einen Schritt aus.
        spanne = re.search(rf"^- \*\*{plural} (\d+){SPAN_DASH}(\d+) — ", rumpf, re.M)
        if not spanne:
            raise CheckFailed(
                f"{name}: keine Sammelzeile '- **{plural} N-M — ' im "
                f"Abschnitt '## {ueberschrift}' — Anker weg oder "
                f"umformuliert. {SKILL_PATH} fuehrt {uebergabe} "
                "Uebergabeschritt(e); ohne diese Zeile nennt die README sie "
                "nicht, und diese Pruefung merkte es nicht mehr."
            )
        erster, letzter = int(spanne.group(1)), int(spanne.group(2))
        if (erster, letzter) != (kern + 1, gesamt):
            raise CheckFailed(
                f"{name}: die Uebergabe steht als '{plural} {erster}-"
                f"{letzter}', {SKILL_PATH} fuehrt Schritt {kern + 1} bis "
                f"{gesamt} als [Übergabe].\n"
                "  Eine Sammelzeile, die zu frueh anfaengt, zaehlt einen "
                "Kernschritt zur Uebergabe; eine, die zu frueh endet, laesst "
                "einen Schritt ganz aus."
            )
        zeilen.append(
            f"{name}: {kern} Kernschritt(e) einzeln, "
            f"{plural} {erster}-{letzter} als Uebergabe"
        )

    return "; ".join(zeilen)
