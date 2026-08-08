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
    # Umbenannt, nicht angehaengt: der Check vergleicht per Teilzeichenkette,
    # `mcp-continuous-auditor2` haette also weiter bestanden — der Name steckt
    # darin. Diese Mutation muss den Namen ERSETZEN, um etwas zu zeigen.
    (
        "kette/mitglied-fehlt",
        "chain_table",
        _sub(
            "README.md", r"mcp-continuous-auditor", "mcp-continuous-inspector", count=0
        ),
        "does not name ['mcp-continuous-auditor']",
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
