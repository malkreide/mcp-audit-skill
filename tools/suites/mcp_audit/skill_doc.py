"""Dokumentations-Anker dieses Repos — die Bindung der generischen Gates.

ZWEI DER DREI FAMILIEN AUS 2b-iii SIND HIER VERDRAHTET. Die dritte, G11 (das
Versions-Badge), ist implementiert und gegen die drei Companions abgenommen —
verdrahtet ist sie nicht, weil sie hier keinen Gegenstand hat: Die READMEs
dieses Repos tragen kein Versions-Badge. Eines einzufuehren waere eine
Aenderung am Produkt und nicht an der Zusammenfuehrung; sie steht als Befund
im Merge-Plan unter 4.2f.

`audit/13` ERSETZT KEINE PRUEFUNG, SIE VEREINIGT ZWEI. Die Ketten-Tabelle
wurde hier schon geprueft — als pytest in `tests/test_quality_chain.py` —, und
in den drei Schwesterrepos als Check. Jetzt gibt es EINE Implementierung in
`tools/gates/readmes.py`, und beide Einstiege rufen sie: der Check hier, der
Test dort. Dieselbe Bewegung wie bei `tools/check_ruff_pin.py` in Phase 2a.
"""

from __future__ import annotations

from pathlib import Path

from tools.gates import readmes as readme_gates
from tools.gates import skill_doc as gates
from tools.harness import register

from ._suite import SUITE

#: Die Wurzel-`SKILL.md` ist der `mcp-audit`-Skill selbst — sie liegt nicht
#: unter `skills/`, weil das Paket den Repo-Baum spiegelt (siehe
#: `skills/README.md`). Die drei Companions pruefen ihre eigene in 2b-iv.
SKILL_PATH = "SKILL.md"
EXPECTED_NAME = "mcp-audit"

#: Wo die Ketten-Tabelle steht — ACHT Dateien, nicht zwei.
#:
#: Bis 2b-iv-c waren es die beiden READMEs der Repo-Wurzel. Die drei Companions
#: fuehren dieselbe Tabelle in ihren eigenen READMEs, und in den Herkunftsrepos
#: hat sie dort auch je eine Pruefung gehalten (`transport/4`, `fidelity/8`,
#: `probe/10`). Beim Einzug sind die drei nach hier absorbiert worden — mit der
#: Begruendung, die Tabelle stehe jetzt «einmal, gegen ein Manifest». Das
#: stimmte fuer die Implementierung und nicht fuer den GEGENSTAND: Sechs
#: Tabellen blieben ungeprueft zurueck, und alle sechs beschrieben in genau
#: diesem Zeitraum noch fuenf Repositories statt vier Skills.
#:
#: Die Absorption ist damit nachgeholt statt bloss behauptet. Ein Mitglied
#: laesst sich jetzt nicht mehr an einer Stelle ergaenzen und an sieben
#: vergessen.
CHAIN_SECTIONS = (
    ("README.md", "The MCP quality chain"),
    ("README.de.md", "Die MCP-Qualitätskette"),
    ("skills/mcp-data-source-probe/README.md", "The MCP quality chain"),
    ("skills/mcp-data-source-probe/README.de.md", "Die MCP-Qualitätskette"),
    ("skills/mcp-data-fidelity/README.md", "The MCP quality chain"),
    ("skills/mcp-data-fidelity/README.de.md", "Die MCP-Qualitätskette"),
    ("skills/mcp-transport-hardening/README.md", "The MCP quality chain"),
    ("skills/mcp-transport-hardening/README.de.md", "Die MCP-Qualitätskette"),
    # Und die drei `SKILL.md` — die Dateien, die Claude tatsaechlich laedt.
    # Sie fuehren dieselbe Tabelle unter einer `##`-Ueberschrift; dass das
    # Gate bis 2b-iv-c nur `###` kannte, ist der Grund, warum sie am
    # laengsten «Fuenf Repos» sagten.
    ("skills/mcp-data-source-probe/SKILL.md", "Verwandte Skills"),
    ("skills/mcp-data-fidelity/SKILL.md", "Verwandte Skills"),
    ("skills/mcp-transport-hardening/SKILL.md", "Verwandte Skills"),
)


@register(11, "SKILL.md carries a well-formed frontmatter", suite=SUITE)
def frontmatter(root: Path) -> str:
    return gates.frontmatter(root, skill_path=SKILL_PATH, expected_name=EXPECTED_NAME)


@register(12, "the quality-chain table names every member", suite=SUITE)
def chain_table(root: Path) -> str:
    return readme_gates.chain_table(root, sections=CHAIN_SECTIONS)


@register(16, "the version badge matches the latest CHANGELOG release", suite=SUITE)
def version_badge(root: Path) -> str:
    """G11, hier zuletzt gebunden — weil es bis 2b-iv keinen Gegenstand gab.

    Die READMEs dieses Repos trugen kein Versions-Badge; die der drei
    Companions schon. Eines einzufuehren war eine Aenderung am PRODUKT und
    nicht an der Zusammenfuehrung, und deshalb eine Entscheidung des
    Betreibers. Sie ist getroffen: Das Badge steht in beiden READMEs und wird
    seither gegen die CHANGELOG-Spitze gehalten.
    """
    return readme_gates.version_badge(root)
