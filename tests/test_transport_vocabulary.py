# -*- coding: utf-8 -*-
"""Hält das `transport`-Vokabular an einer einzigen Stelle fest.

Das Repo beschrieb dieselbe geschlossene Werteliste an fünf Orten und
kam auf zwei verschiedene Antworten: `SKILL.md`, `templates/` und der
Katalog sagten `stdio-only / dual / HTTP/SSE`, während
`portfolio.example.yaml` und der Slash-Command `HTTP` und `SSE` als
getrennte Werte empfahlen. `HTTP` und `SSE` waren nie eigene Transporte,
sondern eine zweite Schreibweise für `HTTP/SSE`.

Der Schaden lief still: Ein Profil mit `transport: HTTP` verlor
`SCALE-002`, `SCALE-003`, `SCALE-007` und `SDK-004` — zwei davon `high`
—, während jede `transport != "stdio-only"`-Klausel weiter griff. Halb
erkanntes Profil, sauberer Report, kleinerer Katalog als behauptet.

Quelle der Wahrheit ist `ALLOWED_VALUES["transport"]` in
`tools/validate_profile.py`. Dieser Test prüft, dass der Katalog, die
Doku und das Beispielprofil dieselbe Liste tragen.

Jede Prüfung scheitert auch, wenn ihr Muster **gar nichts** findet: Ein
Regex, der nach einer Umformulierung ins Leere greift, prüft
stillschweigend nichts mehr — dieselbe Fehlerklasse, die `OPS-005`
beschreibt.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.eval_applicability import parse_check_frontmatter
from tools.parse_catalog import list_check_files
from tools.validate_profile import ALLOWED_VALUES


REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"

CANONICAL = set(ALLOWED_VALUES["transport"])

# `transport == "dual"` / `transport != "stdio-only"` in einer
# applies_when-Klausel. Bewusst auf `transport` verankert: Die Check-Bodies
# enthalten Python-Beispiele wie `settings.transport == "stdio"`, die den
# Config-Wert des *geprüften Servers* meinen und mit dem Profil-Vokabular
# nichts zu tun haben. Deshalb wird nur das Frontmatter gelesen, nie der Body.
CLAUSE_LITERAL = re.compile(r'\btransport\s*[!=]=\s*"([^"]*)"')

# Trennzeichen der Aufzählungen in der Doku. Der Slash muss **umschlossen**
# sein: `a / b` trennt zwei Werte, `HTTP/SSE` ist einer. Genau diese
# Unterscheidung ist der Grund, warum das Vokabular überhaupt auseinanderlief
# — wer `HTTP/SSE` als zwei Werte liest, schreibt `HTTP` ins Profil.
SEPARATOR = re.compile(r"\s*[|,]\s*|\s+/\s+")


def _catalog_literals() -> dict[str, set[str]]:
    """Jeder `transport`-Literalwert aus den applies_when-Klauseln, je Check."""
    out: dict[str, set[str]] = {}
    for path in list_check_files(CHECKS_DIR):
        fm = parse_check_frontmatter(path)
        found = set(CLAUSE_LITERAL.findall(str(fm.get("applies_when", ""))))
        if found:
            out[fm.get("id", path.stem)] = found
    return out


class TestCatalogUsesCanonicalVocabulary:
    def test_every_clause_literal_is_allowed(self):
        literals = _catalog_literals()
        assert literals, (
            "Keine `transport`-Klausel im Katalog gefunden — greift das "
            "Muster noch? Sonst prüft dieser Test nichts mehr."
        )
        for cid, values in sorted(literals.items()):
            unknown = values - CANONICAL
            assert not unknown, (
                f"{cid}: applies_when vergleicht gegen {sorted(unknown)}, "
                f"erlaubt ist {sorted(CANONICAL)}. Ein Wert, den kein Profil "
                f"je trägt, lässt den Check still wegfallen."
            )

    def test_every_allowed_value_is_actually_tested(self):
        """Ein Vokabular-Mitglied, das keine Klausel abfragt, ist tot.

        Es kann kein Audit-Ergebnis verändern, aber es steht in der Doku
        und lädt dazu ein, es ins Profil zu schreiben — dieselbe Falle,
        aus der `HTTP` und `SSE` kamen.
        """
        used = set().union(*_catalog_literals().values())
        unused = CANONICAL - used
        assert not unused, (
            f"{sorted(unused)} steht in ALLOWED_VALUES, wird aber von keiner "
            f"applies_when-Klausel abgefragt."
        )


class TestDocumentationDeclaresSameVocabulary:
    """Jede Datei, die dem Autor eines Profils sagt, was er schreiben darf."""

    @pytest.mark.parametrize("relpath,pattern", [
        # | `Transport` | `stdio-only` / `dual` / `HTTP/SSE` | filtert … |
        ("SKILL.md", r"^\|\s*`Transport`\s*\|\s*(?P<values>[^|]+?)\s*\|"),
        # | Transport | stdio-only / dual / HTTP/SSE |
        ("templates/audit-report.md", r"^\|\s*Transport\s*\|\s*(?P<values>[^|]+?)\s*\|"),
        # | `transport` | `stdio-only`, `dual`, `HTTP/SSE` | `dual` |
        (".claude/commands/audit-mcp.md",
         r"^\|\s*`transport`\s*\|\s*(?P<values>[^|]+?)\s*\|"),
        # transport: dual    # stdio-only | dual | HTTP/SSE
        ("portfolio.example.yaml", r"^\s*transport:\s*\S+\s*#\s*(?P<values>.+?)\s*$"),
    ])
    def test_declared_values_match_canonical(self, relpath, pattern):
        path = REPO_ROOT / relpath
        rx = re.compile(pattern, re.MULTILINE)
        matches = rx.findall(path.read_text(encoding="utf-8"))
        assert matches, (
            f"{relpath}: keine `transport`-Vokabularzeile gefunden. Wurde sie "
            f"umformuliert? Dann gehört das Muster nachgezogen — sonst prüft "
            f"dieser Test stillschweigend nichts mehr."
        )
        for cell in matches:
            declared = {
                tok.strip().strip("`").strip()
                for tok in re.split(SEPARATOR, cell)
                if tok.strip().strip("`").strip()
            }
            assert declared == CANONICAL, (
                f"{relpath} nennt {sorted(declared)}, kanonisch ist "
                f"{sorted(CANONICAL)}"
            )

    def test_example_profile_values_are_canonical(self):
        """Nicht nur der Kommentar — auch die tatsächlich gesetzten Werte."""
        text = (REPO_ROOT / "portfolio.example.yaml").read_text(encoding="utf-8")
        values = re.findall(r"^\s*transport:\s*(\S+)", text, re.MULTILINE)
        assert values, "Kein `transport:`-Wert in portfolio.example.yaml gefunden"
        for v in values:
            assert v in CANONICAL, (
                f"portfolio.example.yaml setzt transport: {v}, "
                f"kanonisch ist {sorted(CANONICAL)}"
            )
