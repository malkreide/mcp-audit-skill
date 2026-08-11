"""Eine Zahl, viele Stellen: Was nummeriert ist, muss ueberall gleich zaehlen.

Zusammengefuehrt aus `mcp-data-source-probe-skill` (Schritte),
`mcp-data-fidelity-skill` und `mcp-transport-hardening-skill` (Regeln) —
Familie G14 des Merge-Plans. Sie war die am staerksten verzweigte der
sechzehn: dreimal dieselbe Bewegung, dreimal mit anderer EINHEIT.

DAS MUSTER, DAS ALLE DREI TEILEN:

  1. EINE normative Quelle — die nummerierten Abschnitte in `SKILL.md`. Sie
     muessen luckenlos sein; eine Luecke ist fast immer ein geloeschter
     Abschnitt, den niemand nachgezogen hat.
  2. Jede andere Stelle, die dieselbe Menge aufzaehlt, wird dagegen gehalten.

Was sich unterschied, war nur, wie die Ueberschrift heisst («## Regel N»,
«## Schritt N») und wie die Einheit im Befundtext genannt wird. Beides ist
jetzt Parameter.

WARUM DIE LUECKENLOSIGKEIT MITGEPRUEFT WIRD und nicht bloss die Anzahl: Wer
Abschnitt 4 von sechs loescht, hat fuenf Abschnitte — und eine reine
Anzahl-Pruefung gegen eine ebenfalls angepasste Zaehlung waere gruen, waehrend
die Numerierung 1,2,3,5,6 lautet. Die Zahl stimmt dann, die Sache nicht.

DER ANLASS IST BELEGT: `mcp-data-fidelity-skill` beschrieb zwei Wochen lang
«fuenf Regeln», nachdem die sechste dazugekommen war. Beide Aussagen waren
richtig, als sie geschrieben wurden.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.gates.repo_meta import as_number
from tools.harness import CheckFailed


def _lies(root: Path, name: str) -> str:
    pfad = root / name
    if not pfad.is_file():
        raise CheckFailed(
            f"{name} fehlt — ohne die Datei hat diese Pruefung nichts zu "
            "zaehlen und meldete das als Erfolg."
        )
    return pfad.read_text(encoding="utf-8")


def numbered(
    text: str, *, pattern: re.Pattern[str], quelle: str, unit: str
) -> list[int]:
    """Die Nummern der Abschnitte, aufsteigend — oder ein Befund.

    `pattern` muss eine Gruppe `nummer` haben. Fehlt jeder Treffer, ist das
    ein Befund und keine leere Menge: Ein Anker, der weg ist, laesst diese
    Pruefung stillschweigend aufhoeren zu pruefen.
    """
    nummern = [int(m.group("nummer")) for m in pattern.finditer(text)]
    if not nummern:
        raise CheckFailed(
            f"{quelle}: keine nummerierte {unit}-Ueberschrift gefunden "
            f"(Muster {pattern.pattern!r}) — Anker weg oder umformuliert; "
            "diese Pruefung wuerde stillschweigend aufhoeren zu pruefen."
        )
    erwartet = list(range(nummern[0], nummern[0] + len(nummern)))
    if nummern != erwartet:
        raise CheckFailed(
            f"{quelle}: die {unit}-Nummern sind nicht fortlaufend: {nummern}.\n"
            "  Eine Luecke ist fast immer ein geloeschter Abschnitt, den "
            "niemand nachgezogen hat — und eine reine Anzahl-Pruefung waere "
            "daneben gruen geblieben."
        )
    return nummern


def _abschnitt(text: str, ueberschrift: str, quelle: str) -> str:
    r"""Der Rumpf unter einer `##`-Ueberschrift, bis zur naechsten.

    Ohne diese Einschraenkung zaehlt ein Muster wie `^\d+\. \*\*` JEDE
    nummerierte Liste des Dokuments mit — gemessen beim Umzug von
    `mcp-transport-hardening`: Dessen README fuehrt nach den vierzehn Regeln
    noch zwei weitere Listen, und die Nummern lasen sich zusammen als
    1..14,1..5,1..3.
    """
    treffer = re.search(
        rf"^## {re.escape(ueberschrift)}\n(.*?)(?=^## |\Z)", text, re.M | re.S
    )
    if not treffer:
        raise CheckFailed(
            f"{quelle}: Abschnitt '## {ueberschrift}' nicht gefunden — Anker "
            "weg oder umformuliert; diese Pruefung wuerde stillschweigend "
            "aufhoeren zu pruefen."
        )
    return treffer.group(1)


def count_agrees(
    root: Path,
    *,
    source: str,
    pattern: re.Pattern[str],
    unit: str,
    mirrors: tuple[tuple[str, re.Pattern[str], str | None], ...] = (),
    claims: tuple[tuple[str, re.Pattern[str]], ...] = (),
) -> str:
    """G14 — jede Stelle, die dieselbe Menge aufzaehlt, zaehlt dieselbe Zahl.

    `mirrors` sind die abhaengigen Stellen: je eine Datei, das Muster, mit dem
    dort dieselbe Menge nummeriert auftaucht, und optional die Ueberschrift des
    Abschnitts, auf den das Muster beschraenkt bleibt (`None` = ganze
    Datei). Sie muessen nicht nur gleich VIELE, sondern DIESELBEN Nummern
    nennen — eine Datei, die 0..7
    fuehrt, waehrend die Quelle 1..8 sagt, hat dieselbe Anzahl und meint
    etwas anderes.
    """
    nummern = numbered(_lies(root, source), pattern=pattern, quelle=source, unit=unit)

    zeilen = [f"{source}: {len(nummern)} {unit} ({nummern[0]}–{nummern[-1]})"]
    for name, spiegel, ueberschrift in mirrors:
        text = _lies(root, name)
        if ueberschrift is not None:
            text = _abschnitt(text, ueberschrift, name)
        gespiegelt = numbered(text, pattern=spiegel, quelle=name, unit=unit)
        if gespiegelt != nummern:
            fehlend = sorted(set(nummern) - set(gespiegelt))
            zuviel = sorted(set(gespiegelt) - set(nummern))
            teile = []
            if fehlend:
                teile.append(f"fehlt {fehlend}")
            if zuviel:
                teile.append(f"zusaetzlich {zuviel}")
            if not teile:
                teile.append(f"andere Reihenfolge: {gespiegelt}")
            raise CheckFailed(
                f"{name}: fuehrt nicht dieselben {unit} wie {source} — "
                + ", ".join(teile)
                + f".\n  {source} definiert {nummern}, {name} nennt "
                f"{gespiegelt}. Die Quelle ist {source}; wer dort etwas "
                "aendert, zieht hier nach."
            )
        zeilen.append(f"{name}: dieselben {len(gespiegelt)} {unit}")

    # Aussagen in PROSA — «der 8-Schritte-Workflow», «patterns for the twelve
    # rules». Sie zaehlen nicht auf, sie behaupten eine Zahl. Ziffer oder
    # englisches Zahlwort entscheidet der Text; `as_number` liest beides,
    # dieselbe Funktion, die `gates/repo_meta.py` fuer die GitHub-Description
    # benutzt.
    for name, muster in claims:
        text = _lies(root, name)
        treffer = muster.search(text)
        if not treffer:
            raise CheckFailed(
                f"{name}: die erwartete Wendung fehlt (Muster "
                f"{muster.pattern!r}) — Anker weg oder umformuliert; diese "
                "Pruefung wuerde stillschweigend aufhoeren zu pruefen."
            )
        behauptet = as_number(treffer.group("wert"))
        if behauptet is None:
            raise CheckFailed(
                f"{name}: die Wendung sagt {treffer.group('wert')!r}, und das "
                "ist keine Zahl, die diese Pruefung kennt — ENGLISH_NUMBERS in "
                "tools/gates/repo_meta.py ergaenzen."
            )
        if behauptet != len(nummern):
            raise CheckFailed(
                f"{name}: die Prosa behauptet {behauptet} {unit}, {source} "
                f"fuehrt {len(nummern)}.\n"
                f"  Die Quelle ist {source}; wer dort etwas aendert, zieht hier "
                "nach."
            )
        zeilen.append(f"{name}: sagt {behauptet}")

    return "; ".join(zeilen)
