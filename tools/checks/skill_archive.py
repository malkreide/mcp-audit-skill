"""Check 5: das eingecheckte `mcp-audit.skill` gegen die Quellen.

WARUM DAS ARCHIV UEBERHAUPT IM REPOSITORY LIEGT. Ein gebautes Artefakt
einzuchecken ist normalerweise die falsche Wahl — hier ist es die Sache
selbst: Der Download-Link in beiden READMEs zeigt auf diese Datei, und wer
den Skill installieren will, soll ihn nicht erst bauen muessen. Der Preis
dafuer ist eine zweite Stelle, an der derselbe Inhalt steht: die Quellen und
das Archiv darueber.

EINE ZWEITE STELLE, DIE NICHTS ERZWINGT, DRIFTET — das ist die Regel, aus der
in diesem Katalog `DRIFT-003` entstand, und sie gilt fuer das eigene
Repository genauso. Ohne diese Pruefung waere der wahrscheinlichste Verlauf:
Jemand fuegt `checks/SEC-029.md` hinzu, alles wird gruen, das Release geht
raus — und das Archiv enthaelt 120 Checks, waehrend `README.md` von 121
spricht. Der Nutzer merkt davon nichts. Sein Audit prueft einen Check
weniger und sieht dabei vollstaendig aus.

VERGLICHEN WIRD INHALT, NICHT BYTES. Der Build ist zwar bit-identisch
reproduzierbar (fester Zeitstempel, feste Rechte, sortierte Reihenfolge), aber
die Kompressionsstufe haengt an der zlib des Systems. Ein Byte-Vergleich
wuerde damit zwischen zwei Python-Versionen rot, ohne dass sich am Paket etwas
geaendert hat — ein Befund aus dem falschen Grund, und beim naechsten Mal ein
gruenes Ergebnis aus dem falschen Grund.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from tools.skill_package import (
    ARCHIVE_NAME,
    ManifestError,
    frontmatter_problems,
    member_name,
    package_files,
)

from ._core import CheckFailed, register

NACHZIEHEN = (
    "  Nachziehen: `bash scripts/build-skill.sh` (oder "
    "`python tools/build_skill.py`) und das Ergebnis mitcommitten."
)


def vergleiche(
    erwartet: dict[str, bytes],
    vorhanden: dict[str, bytes],
) -> tuple[bool, str]:
    """Rein: zwei Abbildungen `Eintragsname -> Inhalt` gegeneinander.

    Kein Dateisystem, kein ZIP — dieselbe Bauart wie `bewerte()` in
    `ruff_gate.py`. Was hier schiefgehen kann, sind drei Mengen, und alle drei
    lassen sich als Wert pruefen.

    Die Meldung nennt bei jeder der drei Abweichungen ihre eigene Ursache. Ein
    gemeinsames «Archiv ist veraltet» waere kuerzer und schickte den Lesenden
    bei einer geloeschten Datei an dieselbe Stelle wie bei einer geaenderten.
    """
    fehlend = sorted(set(erwartet) - set(vorhanden))
    ueberzaehlig = sorted(set(vorhanden) - set(erwartet))
    geaendert = sorted(
        name
        for name in set(erwartet) & set(vorhanden)
        if erwartet[name] != vorhanden[name]
    )

    if not (fehlend or ueberzaehlig or geaendert):
        return True, f"{ARCHIVE_NAME}: {len(erwartet)} Eintraege, alle aktuell"

    zeilen: list[str] = []
    if fehlend:
        zeilen.append(
            f"{len(fehlend)} Datei(en) fehlen im Archiv: {', '.join(fehlend[:5])}"
            + (" …" if len(fehlend) > 5 else "")
        )
    if ueberzaehlig:
        zeilen.append(
            f"{len(ueberzaehlig)} Eintrag/Eintraege im Archiv stehen nicht im "
            f"Manifest: {', '.join(ueberzaehlig[:5])}"
            + (" …" if len(ueberzaehlig) > 5 else "")
        )
    if geaendert:
        zeilen.append(
            f"{len(geaendert)} Datei(en) weichen vom Archiv ab: "
            f"{', '.join(geaendert[:5])}" + (" …" if len(geaendert) > 5 else "")
        )
    return False, "\n".join(zeilen)


@register(5, "the committed mcp-audit.skill matches the sources")
def skill_archive_is_current(root: Path) -> str:
    """Baut die Sollmenge aus dem Manifest und haelt das Archiv dagegen."""
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        raise CheckFailed(f"SKILL.md fehlt in {root}.")

    probleme = frontmatter_problems(skill_md.read_text(encoding="utf-8"))
    if probleme:
        raise CheckFailed(
            "\n".join(probleme)
            + "\n  Ohne gueltiges Frontmatter weist Claude den Upload ab — "
            "beim Nutzer, nicht hier."
        )

    try:
        dateien = package_files(root)
    except ManifestError as exc:
        raise CheckFailed(str(exc)) from exc

    archiv = root / ARCHIVE_NAME
    if not archiv.is_file():
        raise CheckFailed(
            f"{ARCHIVE_NAME} fehlt. Beide READMEs verlinken diese Datei zum "
            f"Herunterladen.\n{NACHZIEHEN}"
        )

    erwartet = {member_name(p): (root / p).read_bytes() for p in dateien}
    try:
        with zipfile.ZipFile(archiv) as zf:
            vorhanden = {
                name: zf.read(name) for name in zf.namelist() if not name.endswith("/")
            }
    except zipfile.BadZipFile as exc:
        raise CheckFailed(f"{ARCHIVE_NAME} ist kein gueltiges ZIP-Archiv.") from exc

    ok, meldung = vergleiche(erwartet, vorhanden)
    if not ok:
        raise CheckFailed(f"{meldung}\n{NACHZIEHEN}")
    return meldung
