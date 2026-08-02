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

    @pytest.mark.parametrize(
        "relpath,pattern",
        [
            # | `Transport` | `stdio-only` / `dual` / `HTTP/SSE` | filtert … |
            ("SKILL.md", r"^\|\s*`Transport`\s*\|\s*(?P<values>[^|]+?)\s*\|"),
            # | Transport | stdio-only / dual / HTTP/SSE |
            (
                "templates/audit-report.md",
                r"^\|\s*Transport\s*\|\s*(?P<values>[^|]+?)\s*\|",
            ),
            # | `transport` | `stdio-only`, `dual`, `HTTP/SSE` | `dual` |
            (
                ".claude/commands/audit-mcp.md",
                r"^\|\s*`transport`\s*\|\s*(?P<values>[^|]+?)\s*\|",
            ),
            # transport: dual    # stdio-only | dual | HTTP/SSE
            (
                "portfolio.example.yaml",
                r"^\s*transport:\s*\S+\s*#\s*(?P<values>.+?)\s*$",
            ),
        ],
    )
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
                f"{relpath} nennt {sorted(declared)}, kanonisch ist {sorted(CANONICAL)}"
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


# ---------------------------------------------------------------------------
# `sdk_language` — dieselbe Klasse, andere Behandlung
# ---------------------------------------------------------------------------

SDK_LANGUAGE_DOC_FILES = (
    "portfolio.example.yaml",
    ".claude/commands/audit-mcp.md",
    "SKILL.md",
    "docs/applies-when-dsl.md",
)

SDK_CLAUSE_LITERAL = re.compile(r'\bsdk_language\s*[!=]=\s*"([^"]*)"')


def _sdk_language_literals() -> set[str]:
    out: set[str] = set()
    for path in list_check_files(CHECKS_DIR):
        fm = parse_check_frontmatter(path)
        out |= set(SDK_CLAUSE_LITERAL.findall(str(fm.get("applies_when", ""))))
    return out


class TestSdkLanguageIsDocumented:
    """`sdk_language` war bis v1.3.1 nirgends dokumentiert.

    Sieben Checks fragen es ab (`SDK-001`…`006`, `IDENT-005`), aber es stand
    weder in `REQUIRED_FIELDS` noch im Beispielprofil noch im DSL-Doc — und
    `audit-notion-sync.py` hat es nie gesetzt. Ein aus Notion gezogenes
    Profil kam damit sauber durch das Validierungs-Gate und liess erst im
    Evaluator sieben Checks mit `UnknownFieldError` auflaufen. Also genau
    die Reihenfolge, die das Gate verhindern soll.

    Anders als `transport` ist das Feld **nicht** in `ALLOWED_VALUES`
    gepinnt: Ein Server in Go oder Rust trägt eine Sprache, die kein Check
    abfragt — das ist eine Lücke im Katalog, kein Fehler im Profil. Ein
    harter Reject würde ein korrekt beschriebenes Profil abweisen.
    """

    def test_it_is_a_required_field(self):
        from tools.validate_profile import REQUIRED_FIELDS

        assert REQUIRED_FIELDS.get("sdk_language") is str, (
            "sdk_language muss Pflichtfeld sein — sonst passiert ein Profil "
            "ohne das Feld das Gate und sieben Checks fallen erst im "
            "Evaluator aus."
        )

    def test_the_catalog_actually_uses_it(self):
        """Gegenprobe: Verschwinden die Klauseln, prüft dieser Test nichts mehr."""
        assert _sdk_language_literals(), (
            "Keine `sdk_language`-Klausel im Katalog gefunden — greift das "
            "Muster noch, oder wurde das Feld aufgegeben?"
        )

    @pytest.mark.parametrize("relpath", SDK_LANGUAGE_DOC_FILES)
    def test_every_catalog_value_appears_in_the_docs(self, relpath):
        """Jede Sprache, gegen die der Katalog vergleicht, muss dokumentiert sein.

        Bewusst nur diese Richtung: Die Doku darf mehr nennen als der
        Katalog abfragt (eine Sprache ohne eigene Checks ist zulässig), aber
        keinen Wert weglassen, den eine Klausel testet — sonst schreibt
        niemand ihn ins Profil und die Checks laufen still ins Leere.
        """
        text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
        missing = sorted(v for v in _sdk_language_literals() if v not in text)
        assert not missing, f"{relpath} nennt {missing} nicht"

    def test_it_is_not_pinned_as_a_closed_vocabulary(self):
        """Die Entscheidung gegen den harten Reject, festgehalten.

        Fällt dieser Test, hat jemand `sdk_language` in `ALLOWED_VALUES`
        aufgenommen — dann gehört die Begründung oben neu geführt, denn ab
        da wird ein Go-Server abgewiesen.
        """
        from tools.validate_profile import ALLOWED_VALUES

        assert "sdk_language" not in ALLOWED_VALUES

    def test_notion_sync_sets_the_field(self):
        """Sonst ist jedes gezogene Profil wieder kaputt."""
        text = (REPO_ROOT / "audit-notion-sync.py").read_text(encoding="utf-8")
        assert '"sdk_language": sdk_language' in text, (
            "audit-notion-sync.py setzt sdk_language nicht mehr — jedes "
            "gepullte Profil lässt dann sieben Checks auflaufen."
        )
