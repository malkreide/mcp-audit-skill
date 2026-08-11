"""Der Companion-Zeiger — und die eine Frage, die dieser Umzug offen laesst.

VORGESCHICHTE. `mcp-data-fidelity` wurde eine Zeit lang INNERHALB dieses
Skills ausgeliefert, als `companion/mcp-data-fidelity/`. Beim Umzug in ein
eigenes Repository blieb das Verzeichnis stehen — mit einer README statt einer
`SKILL.md`, die sagt, wo der Skill jetzt liegt. Die Pruefung bewacht beides:
dass dort keine zweite `SKILL.md` auftaucht (zwei Kopien driften), und dass
der Zeiger auf das kanonische Zuhause zeigt.

OFFENER PUNKT, AUSDRUECKLICH NICHT ENTSCHIEDEN. Das kanonische Zuhause hat
sich mit Phase 3a schon einmal verschoben: `mcp-data-fidelity` liegt jetzt als
Geschwister-Verzeichnis unter `skills/mcp-data-fidelity/`, im selben Baum wie
dieser Skill. Der Zeiger nennt weiterhin das Herkunftsrepo, und Phase 5 wird
das archivieren.

Der Zeiger zeigt damit heute noch richtig und ab Phase 5 nicht mehr. Diese
Pruefung haelt fest, was DA STEHT, statt zu raten, was da stehen soll — die
Entscheidung («Verzeichnis aufloesen» oder «Zeiger auf das
Geschwister-Verzeichnis umbiegen») gehoert zum Neufassen der Companion-READMEs
(2b-iv-c) und ist eine Aenderung am Produkt, nicht an der Zusammenfuehrung.
Sie steht als offener Punkt im Merge-Plan unter 4.2m.

Was diese Pruefung dabei leistet: Wird der Zeiger umgebogen, ohne dass
`CANONICAL_REPO` mitgeht, wird sie rot. Sie kann den Umzug nicht anstossen,
aber sie kann nicht mit ihm auseinanderlaufen.
"""

from __future__ import annotations

from pathlib import Path

from tools.harness import CheckFailed, register

from ._suite import SUITE
from .skill_doc import BASE

COMPANION_DIR = f"{BASE}/companion/mcp-data-fidelity"
POINTER = f"{COMPANION_DIR}/README.md"

#: Was der Zeiger heute nennt. Siehe den offenen Punkt im Modul-Docstring.
CANONICAL_REPO = "malkreide/mcp-data-fidelity-skill"


@register(8, "the companion pointer still points somewhere", suite=SUITE)
def companion_pointer(root: Path) -> str:
    if (root / COMPANION_DIR / "SKILL.md").exists():
        raise CheckFailed(
            f"{COMPANION_DIR} traegt wieder eine SKILL.md — der Skill liegt "
            "als Geschwister unter skills/mcp-data-fidelity/, zwei Kopien "
            "driften.\n"
            "  Im Herkunftsrepo war das eine Kopie ueber eine Repo-Grenze "
            "hinweg; hier waere es eine zweite Kopie im SELBEN Baum, und die "
            "faellt beim Lesen noch weniger auf."
        )

    # Der Anker ist der Dateipfad. Fehlt die Datei, meldete eine Inhaltssuche
    # dasselbe wie ein falscher Inhalt — der Befund zeigte auf die falsche
    # Ursache, und der Zeiger waere ganz weg statt nur falsch.
    zeiger = root / POINTER
    if not zeiger.is_file():
        raise CheckFailed(
            f"{POINTER} fehlt — der Zeiger ist nicht falsch, sondern weg; "
            "diese Pruefung haette nichts zu lesen."
        )
    if CANONICAL_REPO not in zeiger.read_text(encoding="utf-8"):
        raise CheckFailed(
            f"{POINTER} nennt nicht {CANONICAL_REPO} — ein Zeiger, der nicht "
            "zeigt, ist ein toter Ordner mit Text darin.\n"
            "  Wurde er auf das Geschwister-Verzeichnis umgebogen, gehoert "
            "CANONICAL_REPO in tools/suites/mcp_data_source_probe/companion.py "
            "im selben Commit mitgezogen — siehe den offenen Punkt 4.2m im "
            "Merge-Plan."
        )
    return f"{POINTER} nennt {CANONICAL_REPO}, keine zweite SKILL.md daneben"
