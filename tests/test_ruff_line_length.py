"""Hält die Zeilenbreite dieses Repos am schmalsten Wert des Portfolios fest.

Warum es diesen Test gibt: `ruff.toml` hatte lange keinen `line-length`-Eintrag
und lief auf dem ruff-Default 88. Das war der richtige Wert — die Regel in
`SKILL.md` («Portfolio-Hygiene») verlangt den schmalsten im Portfolio
konfigurierten, und das sind die 88 aus `swiss-snb-mcp`. Nur war er nirgends
als Entscheidung erkennbar, und weil 24 der 32 gezählten Repos auf 100 stehen,
liest sich eine Abwesenheit wie ein Versehen. Der nächstliegende «Fix» wäre
gewesen, an die Mehrheit anzugleichen — und hätte damit genau den Bruch
erzeugt, den `OPS-005` in seiner fünften Ausprägung beschreibt.

Geprüft wird deshalb nicht «der Wert ist 88», sondern die Eigenschaft, aus der
die 88 folgt: **der konfigurierte Wert ist der schmalste, gegen den dieses Repo
seine Portfolio-Regel formuliert.** Sinkt der Boden im Portfolio irgendwann auf
80, wird dieser Test rot, statt eine überholte Zahl zu zementieren.

Quelle für die Breiten ist die Prüfschleife in `SKILL.md` — dieselbe, die
`OPS-005` Modus 3 als Gate verlangt. Damit hängen Konfiguration, Prosa und
Kriterium an einer Zahlenreihe statt an drei Kopien davon.

Was dieser Test ausdrücklich **nicht** belegt: dass die Dateien dieses Repos
zwischen Repos kopierbar sind. Das entscheidet nicht die Konfiguration, sondern
die Schleife über alle Breiten. Ein grüner Test hier heisst «der lokale Boden
stimmt», nicht «der Kopiervorgang ist sicher».
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUFF_TOML = REPO_ROOT / "ruff.toml"
SKILL = REPO_ROOT / "SKILL.md"

# Die Prüfschleife aus SKILL.md, «Portfolio-Hygiene»:
#     for W in 88 100 110 120; do
PRUEFSCHLEIFE = re.compile(r"for W in ((?:\d+ )*\d+); do")


def portfolio_breiten() -> list[int]:
    """Die Breiten, gegen die SKILL.md einen Rollout prüfen lässt."""
    treffer = PRUEFSCHLEIFE.search(SKILL.read_text(encoding="utf-8"))
    assert treffer, "Prüfschleife in SKILL.md nicht gefunden — Test blind"
    return [int(w) for w in treffer.group(1).split()]


def test_die_breite_steht_explizit_in_der_konfiguration():
    """Ein fehlender Eintrag ist keine Wahl, sondern eine Abwesenheit.

    Der Default ist derselbe Wert; geprüft wird nicht das Ergebnis, sondern dass
    jemand sich entschieden hat. Ohne Eintrag ist «bewusst 88» von «nie darüber
    nachgedacht» nicht unterscheidbar, und die nächste Bearbeitung entscheidet
    neu, ohne zu merken, dass sie etwas entscheidet.
    """
    konfiguration = tomllib.loads(RUFF_TOML.read_text(encoding="utf-8"))
    assert "line-length" in konfiguration, (
        "ruff.toml nennt keine line-length — damit gilt der ruff-Default, "
        "und die Wahl ist wieder unsichtbar."
    )


def test_die_breite_ist_der_schmalste_wert_des_portfolios():
    """«Der schmalste Wert im Portfolio schreibt den Code» — auch hier."""
    konfiguration = tomllib.loads(RUFF_TOML.read_text(encoding="utf-8"))
    breiten = portfolio_breiten()
    assert konfiguration["line-length"] == min(breiten), (
        f"ruff.toml steht auf {konfiguration['line-length']}, der schmalste "
        f"Wert der Prüfschleife in SKILL.md ist {min(breiten)}. Ein breiterer "
        f"Wert bricht dieses Repos eigene Portfolio-Regel."
    )


def test_die_wahl_ist_im_repo_begruendet_nicht_nur_im_pull_request():
    """Ein Wert ohne Begründung wird beim nächsten Aufräumen wegoptimiert.

    Geprüft wird bewusst nur, dass unmittelbar über dem Eintrag Kommentarzeilen
    stehen — nicht deren Wortlaut. Ein Test auf Formulierungen prüft den Test,
    nicht die Sache.
    """
    zeilen = RUFF_TOML.read_text(encoding="utf-8").splitlines()
    index = next(i for i, z in enumerate(zeilen) if z.startswith("line-length"))
    kommentar = []
    for zeile in reversed(zeilen[:index]):
        if not zeile.startswith("#"):
            break
        kommentar.append(zeile)
    assert len(kommentar) >= 3, (
        "line-length steht ohne Begründung da — dann ist der Wert wieder nur "
        "eine Zahl, und die nächste Bearbeitung ändert sie folgenlos."
    )
