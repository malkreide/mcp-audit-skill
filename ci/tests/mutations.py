"""Die Mutationen, gegen die sich die Checks beweisen muessen.

Jeder Eintrag beschreibt EINEN Defekt und die Meldung, die dann fallen muss.
Zwei Sorten stecken darin, und die zweite ist der eigentliche Grund fuer diese
Datei:

* SACHDEFEKTE — die Regelzahl laeuft auseinander, ein Badge ist veraltet, ein
  Kettenmitglied fehlt. Das ist, wofuer die Checks gebaut wurden.

* ANKER-ENTFERNUNGEN (`ANKER` im Namen) — die Ueberschrift wird umbenannt, die
  Phrase umformuliert, der Badge verschwindet. Diese Faelle sind die
  gefaehrlicheren: Der Check hat dann nichts mehr, wogegen er vergleicht, und
  die naheliegende Implementierung meldet dafuer «bestanden». Die Doktrin
  dieses Repos ist, dass ein fehlender Anker ein FEHLER ist. Sie stand bislang
  an sechs Stellen in der Prosa und war nirgends nachgeprueft — hier wird sie
  es.

Die Mutationen sind bewusst per Regex formuliert und nicht als feste
Textstellen: Kommt Regel 15 dazu, sollen sie weiter greifen, statt an einer
Zeilennummer zu zerbrechen. Greift eine Mutation NICHT mehr, wirft sie —
stillschweigend nichts zu mutieren und dann «Check hat bestanden» zu messen
waere derselbe Fehler, den die Checks selbst verhindern sollen.
"""

from __future__ import annotations

import re


def _sub(path: str, pattern: str, repl: str, count: int = 1, flags: int = 0):
    def apply(tree):
        p = tree / path
        text = p.read_text(encoding="utf-8")
        new, n = re.subn(pattern, repl, text, count=count, flags=flags)
        if n == 0:
            raise AssertionError(
                f"Mutation griff nicht: {pattern!r} in {path} — der Baum hat sich "
                "geaendert, die Mutation gehoert nachgezogen"
            )
        p.write_text(new, encoding="utf-8")

    return apply


def _last_rule_section(path: str, pattern: str, repl: str):
    """Mutiert nur den LETZTEN '## Regel N'-Abschnitt.

    Im ersten zu mutieren haette auch dann bestanden, wenn der Check nach dem
    ersten Abschnitt aufhoerte. Der letzte belegt, dass die Schleife laeuft.
    """

    def apply(tree):
        p = tree / path
        parts = re.split(r"(?m)^(## Regel )", p.read_text(encoding="utf-8"))
        new, n = re.subn(pattern, repl, parts[-1])
        if n == 0:
            raise AssertionError(
                f"Mutation griff nicht im letzten Regelabschnitt: {pattern!r}"
            )
        parts[-1] = new
        p.write_text("".join(parts), encoding="utf-8")

    return apply


# (id, check, mutate-oder-None, erwartete Teilzeichenkette der Meldung)
MUTATIONS = [
    # --- SKILL.md-Frontmatter ----------------------------------------------
    (
        "frontmatter/name-geaendert",
        "skill_frontmatter",
        _sub(
            "SKILL.md",
            r"^name: mcp-transport-hardening$",
            "name: something-else",
            flags=re.M,
        ),
        "expected name 'mcp-transport-hardening'",
    ),
    (
        "frontmatter/description-zu-lang",
        "skill_frontmatter",
        _sub(
            "SKILL.md",
            r"^description: ",
            "description: " + "x" * 1100 + " ",
            flags=re.M,
        ),
        "description too long",
    ),
    (
        "frontmatter/ANKER-weg",
        "skill_frontmatter",
        _sub("SKILL.md", r"\A---\nname: ", "---\nnaam: "),
        "frontmatter missing or malformed",
    ),
    # --- Regelabschnitte ----------------------------------------------------
    (
        "regelabschnitte/gegenbeispiel-weg-im-letzten-abschnitt",
        "rule_sections",
        _last_rule_section("SKILL.md", r"# ✓", "# okay"),
        "missing the counter-example / example code pair",
    ),
    (
        "regelabschnitte/nachweis-weg",
        "rule_sections",
        _sub("SKILL.md", r"\*\*Nachweis:\*\*", "**Beleg:**"),
        "missing the Nachweis sentence",
    ),
    (
        "regelabschnitte/nummern-nicht-fortlaufend",
        "rule_sections",
        _sub("SKILL.md", r"^## Regel 2\b", "## Regel 7", flags=re.M),
        "rule numbers not sequential",
    ),
    (
        "regelabschnitte/ANKER-weg",
        "rule_sections",
        _sub("SKILL.md", r"^## Regel ", "## Vorschrift ", count=0, flags=re.M),
        "no '## Regel N' sections found",
    ),
    # --- Regelzahl ueber vier Dateien ---------------------------------------
    (
        "regelzahl/readme-eintrag-fehlt",
        "rule_count",
        _sub("README.md", r"^14\. ", "- ", flags=re.M),
        "lists 13 rules, SKILL.md defines 14",
    ),
    (
        "regelzahl/docstring-zahlwort-falsch",
        "rule_count",
        _sub(
            "reference/patterns.py",
            r"patterns for the fourteen ",
            "patterns for the thirteen ",
        ),
        "docstring says 'thirteen' rules, SKILL.md defines 14",
    ),
    (
        "regelzahl/docstring-zahlwort-unbekannt",
        "rule_count",
        _sub(
            "reference/patterns.py",
            r"patterns for the fourteen ",
            "patterns for the sixteen ",
        ),
        "not a number word this check knows",
    ),
    (
        "regelzahl/ANKER-docstring-umformuliert",
        "rule_count",
        _sub(
            "reference/patterns.py",
            r"patterns for the fourteen transport-hardening rules",
            "examples covering the fourteen transport-hardening guidelines",
        ),
        "anchor removed or reworded",
    ),
    (
        "regelzahl/ANKER-readme-ueberschrift-weg",
        "rule_count",
        _sub("README.md", r"^## The fourteen rules$", "## The rules", flags=re.M),
        "section '## The fourteen rules' not found",
    ),
    # Der dokumentierte Fall: Regel 13 nur noch in einer Sammelueberschrift.
    # Genau dieser Mutationstest hat seinerzeit gezeigt, dass das Expandieren
    # von Bereichen den geloeschten Regel-13-Block gruen durchgehen liess.
    (
        "regelzahl/nur-sammelueberschrift",
        "rule_count",
        _sub("reference/patterns.py", r"^# Rule 13 — ", "# Rules 12-14 — ", flags=re.M),
        "nothing for rule(s) [13]",
    ),
    # --- Kettentabelle ------------------------------------------------------
    (
        "kette/mitglied-umbenannt",
        "chain_table",
        _sub(
            "README.md", r"mcp-continuous-auditor", "mcp-continuous-inspector", count=0
        ),
        "does not name ['mcp-continuous-auditor']",
    ),
    # Die beiden folgenden gingen unter dem alten Teilzeichenketten-Vergleich
    # DURCH: der gesuchte Name steckt im umbenannten. So verschwindet ein
    # Mitglied, ohne dass etwas rot wird — nicht durch Loeschen, sondern durch
    # Umbenennen mit Anhang.
    (
        "kette/mitglied-mit-ziffer-angehaengt",
        "chain_table",
        _sub(
            "README.md", r"mcp-continuous-auditor", "mcp-continuous-auditor2", count=0
        ),
        "does not name ['mcp-continuous-auditor']",
    ),
    # Der Fall, an dem ein blosses `\b` nicht reichen wuerde: der Bindestrich
    # ist ein Nicht-Wortzeichen, also waere die Wortgrenze hinter
    # `mcp-audit-skill` erfuellt und die Mutation unbemerkt geblieben.
    (
        "kette/mitglied-mit-bindestrich-suffix",
        "chain_table",
        _sub("README.md", r"mcp-audit-skill(?![\w-])", "mcp-audit-skill-v2", count=0),
        "does not name ['mcp-audit-skill']",
    ),
    (
        "kette/topic-link-weg",
        "chain_table",
        _sub(
            "README.md",
            r"https://github\.com/topics/mcp-quality-chain",
            "https://example.com/",
            count=0,
        ),
        "is not linked",
    ),
    (
        "kette/ANKER-ueberschrift-weg",
        "chain_table",
        _sub(
            "README.md",
            r"^### The MCP quality chain$",
            "### Related repositories",
            flags=re.M,
        ),
        "section '### The MCP quality chain' not found",
    ),
    # --- Version-Badge ------------------------------------------------------
    (
        "badge/veraltet",
        "version_badge",
        _sub("README.md", r"badge/version-\d+\.\d+\.\d+-", "badge/version-1.0.0-"),
        "version badge shows ['1.0.0']",
    ),
    (
        "badge/ANKER-badge-weg",
        "version_badge",
        _sub("README.de.md", r"badge/version-\d+\.\d+\.\d+-", "badge/rules-14-"),
        "no version badge found",
    ),
    (
        "badge/ANKER-release-ueberschrift-weg",
        "version_badge",
        _sub(
            "CHANGELOG.md",
            r"^## \[(\d+\.\d+\.\d+)\]",
            r"## Release \1",
            count=0,
            flags=re.M,
        ),
        "no '## [X.Y.Z]' release heading found",
    ),
    # --- Offene Namen in reference/patterns.py ------------------------------
    # DER FALL, UM DEN ES GEHT: ein Tippfehler in einem offenen Namen. Unter
    # dem pauschalen `--ignore F821` war er unsichtbar; die Positivliste macht
    # ihn zu einem Befund.
    (
        "offene-namen/tippfehler",
        "reference_open_names",
        # Die CODE-Stelle, nicht die Nennung im Modul-Docstring: nur erstere
        # erzeugt ein F821, und nur um sie geht es hier.
        _sub(
            "reference/patterns.py",
            r"settings = get_settings\(\)",
            "settings = get_settngs()",
        ),
        "offene Namen ohne Eintrag auf der Positivliste: ['get_settngs']",
    ),
    # Die andere Richtung: ein Eintrag, den es im Baum nicht mehr gibt. Ohne
    # diesen Zweig waechst die Liste nur und beschreibt irgendwann die
    # Geschichte statt die Datei.
    (
        "offene-namen/verwaister-eintrag",
        "reference_open_names",
        _sub(
            "reference/patterns.py",
            r"raise HeaderMismatchError",
            "raise ValueError",
            count=0,
        ),
        "Namen, die es in reference/ nicht mehr gibt: ['HeaderMismatchError']",
    ),
    # ANKER: die Meldungsform von ruff. Wird sie unlesbar, darf der Check nicht
    # null Namen finden und «sauber» melden — er muss sagen, dass er nichts
    # lesen konnte. Simuliert ueber den Regex im Check selbst.
    (
        "offene-namen/ANKER-meldungsform",
        "reference_open_names",
        _sub(
            "ci/checks/reference_open_names.py",
            r'r"Undefined name `\(\?P<name>\[\^`\]\+\)`"',
            'r"Undefinierter Name `(?P<name>[^`]+)`"',
        ),
        "traegt nicht die Form",
    ),
    # --- GitHub-Description -------------------------------------------------
    # Die ersten beiden mutieren die API-Antwort, nicht den Baum: die
    # Description liegt ausserhalb des Repos. Genau deshalb bekommt das Skript
    # sie als Datei — sonst waeren diese beiden Faelle nicht pruefbar.
    (
        "description/zahlwort-falsch",
        "repo_description",
        None,
        "GitHub description says 'thirteen' rules, the repo has 'fourteen'",
    ),
    (
        "description/ANKER-phrase-umformuliert",
        "repo_description",
        None,
        "does not carry the phrase",
    ),
    (
        "description/ANKER-patterns-zahlwort-weg",
        "repo_description",
        _sub(
            "reference/patterns.py",
            r"patterns for the fourteen transport-hardening rules",
            "examples for the fourteen transport-hardening guidelines",
        ),
        "number word gone",
    ),
]

# Abweichende API-Antworten fuer die zwei Faelle oben.
DESCRIPTIONS = {
    "description/zahlwort-falsch": (
        "Claude Skill with thirteen transport-hardening rules for MCP servers, "
        "across both spec baselines — scope follows where the line sits in the "
        "code, not the transport it runs"
    ),
    "description/ANKER-phrase-umformuliert": (
        "Claude Skill with fourteen hardening rules for MCP servers"
    ),
}
