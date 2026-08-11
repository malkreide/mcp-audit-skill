"""Die Mutationen der Suite `fidelity`.

Uebernommen aus `mcp-data-fidelity-skill/tests/mutations.py`. Von dessen
achtzig Mutationen stehen hier sechsunddreissig — die uebrigen gehoerten zu
den zwoelf Pruefungen, die im Monorepo repo-bezogen sind und in `ABSORBED`
stehen. Sie sind nicht verloren: `audit` prueft dieselben Gegenstaende einmal
statt viermal, und die zugehoerigen Mutationen ziehen mit jenen Pruefungen um,
nicht mit dieser Suite.

DIE FUENFZEHN MUTATIONEN AUF `catalogue_drift` SIND DIE INTERESSANTESTEN, weil
sich unter ihnen der Boden bewegt hat. Im Herkunftsrepo mutierten sie einen
Katalog, den ein Wochenplan-Workflow zuvor per HTTP abgelegt hatte, samt einer
`conftest.py`, die einen SYNTHETISCHEN Katalog erzeugen musste — 230 Zeilen,
die einen Manifest-Stand nachbauten, der zu SKILL.md passt. Der Grund stand
dort ausgeschrieben: Der echte Katalog lag hinter einer Repo-Grenze.

Hier mutieren sie `checks/` selbst. Der Generator entfaellt ersatzlos, und mit
ihm seine eingestandene Grenze — er belegte, dass die Pruefung einen STIMMIGEN
Katalog durchlaesst, und ausdruecklich nicht, dass der echte stimmt. Genau das
belegt jetzt `test_der_unveraenderte_baum_ist_gruen`, gegen den echten.
"""

from __future__ import annotations

from ._mutation import (
    Mutation,
    append,
    chain,
    drop_last_line,
    regex_sub,
    remove,
    replace,
    write,
)

BASE = "skills/mcp-data-fidelity"
SKILL = f"{BASE}/SKILL.md"
README = f"{BASE}/README.md"
README_DE = f"{BASE}/README.de.md"
CHANGELOG = f"{BASE}/CHANGELOG.md"
PATTERNS = f"{BASE}/reference/patterns.py"
MANIFEST = "checks/MANIFEST.txt"
CHECKS = "checks"

MUTATIONS: list[Mutation] = [
    # --- referenced_files_exist (fidelity/2) -------------------------------
    Mutation(
        "referenced_files_exist",
        "Vorlage weg",
        remove(PATTERNS),
        PATTERNS,
    ),
    Mutation(
        "referenced_files_exist",
        "CHANGELOG weg",
        remove(CHANGELOG),
        CHANGELOG,
    ),
    # --- skill_frontmatter (fidelity/4) ------------------------------------
    Mutation(
        "skill_frontmatter",
        "SKILL.md weg",
        remove(SKILL),
        "fehlt",
    ),
    Mutation(
        "skill_frontmatter",
        "Frontmatter-Zaun beschaedigt",
        replace(SKILL, "---\nname:", "----\nname:"),
        "Frontmatter fehlt oder ist unvollstaendig",
    ),
    Mutation(
        "skill_frontmatter",
        "falscher Skill-Name",
        replace(SKILL, "name: mcp-data-fidelity\n", "name: mcp-fidelity\n"),
        "erwartet wurde name=",
    ),
    Mutation(
        "skill_frontmatter",
        "Description ueber der Grenze",
        regex_sub(
            SKILL, r"^description: ", "description: " + "x" * 1100 + " ", count=1
        ),
        "die Grenze liegt bei 1024",
    ),
    # --- rule_count_consistent (fidelity/5) --------------------------------
    Mutation(
        "rule_count_consistent",
        "ANKER: Regel-Ueberschriften umbenannt",
        regex_sub(SKILL, r"^## Regel (\d+)", r"## Rule \1"),
        "Anker weg oder umformuliert",
    ),
    Mutation(
        "rule_count_consistent",
        "Regelnummern nicht fortlaufend",
        regex_sub(SKILL, r"^## Regel 3\b", "## Regel 33"),
        "nicht fortlaufend",
    ),
    Mutation(
        "rule_count_consistent",
        "eine Regel faellt aus einem README",
        regex_sub(README, r"^14\. \*\*.*$\n", ""),
        "fuehrt nicht dieselben Regeln",
    ),
    Mutation(
        "rule_count_consistent",
        "ANKER: README-Abschnitt umformuliert",
        replace(README_DE, "## Die vierzehn Regeln", "## Die Regeln"),
        "Abschnitt '## Die vierzehn Regeln' nicht gefunden",
    ),
    Mutation(
        "rule_count_consistent",
        "ANKER: Docstring-Wendung in patterns.py weg",
        replace(PATTERNS, "patterns for the fourteen", "patterns for fourteen"),
        "die erwartete Wendung fehlt",
    ),
    Mutation(
        "rule_count_consistent",
        "Docstring nennt eine andere Zahl",
        replace(PATTERNS, "patterns for the fourteen", "patterns for the nine"),
        "die Prosa behauptet 9 Regeln",
    ),
    Mutation(
        "rule_count_consistent",
        # Das Zahlwort muss eines sein, das ENGLISH_NUMBERS NICHT kennt. Die
        # Tabelle reicht bis `twenty`; `fifteen` waere hier also die falsche
        # Wahl gewesen — die Pruefung waere rot geworden, aber mit dem Befund
        # «behauptet 15 Regeln» statt «kenne das Zahlwort nicht», und der
        # Zweig, um den es geht, bliebe ungetestet.
        "Zahlwort, das die Tabelle nicht kennt",
        replace(PATTERNS, "patterns for the fourteen", "patterns for the umpteen"),
        "ENGLISH_NUMBERS",
    ),
    Mutation(
        "rule_count_consistent",
        # ZWEI SCHRITTE, weil Regel 9 auf zwei Arten genannt wird: einzeln
        # («Rule 9 — input_required …») und als Bereich («Rules 7-9»). Nur
        # einen zu treffen laesst die Regel abgedeckt, und die Mutation bliebe
        # gruen, ohne dass es jemandem auffiele.
        "patterns.py deckt eine Regel nicht mehr ab",
        chain(
            regex_sub(PATTERNS, r"[Rr]ules\s+7-9", "Rules 7 and 8"),
            regex_sub(PATTERNS, r"([Rr])ule 9\b", r"\1ule IX"),
        ),
        "nichts zu Regel [9]",
    ),
    # --- rule_to_check_table (fidelity/6) ----------------------------------
    Mutation(
        "rule_to_check_table",
        "ANKER: Tabellenueberschrift umformuliert",
        replace(SKILL, "### Welche Regel welcher Check ist", "### Regel und Check"),
        "nicht gefunden",
    ),
    Mutation(
        "rule_to_check_table",
        "eine Regel ohne Tabellenzeile",
        regex_sub(SKILL, r"^\| 3 — .*\n", ""),
        "keine Tabellenzeile fuer Regel [3]",
    ),
    Mutation(
        "rule_to_check_table",
        "eine Regel doppelt in der Tabelle",
        regex_sub(SKILL, r"^(\| 2 — .*)$", r"\1\n\1"),
        "mehr als eine Tabellenzeile",
    ),
    Mutation(
        "rule_to_check_table",
        "eine Zeile nennt keinen Check",
        regex_sub(
            SKILL,
            r"^\| 2 — (.*?) \|.*\|$",
            r"| 2 — \1 | dazu gibt es im Katalog nichts |",
        ),
        "nennt gar keinen Check",
    ),
    # --- version_badge (fidelity/7) ----------------------------------------
    Mutation(
        "version_badge",
        "Badge nicht mitgezogen",
        regex_sub(README, r"badge/version-\d+\.\d+\.\d+-", "badge/version-0.9.0-"),
        "das Versions-Badge zeigt",
    ),
    Mutation(
        "version_badge",
        "ANKER: Badge weg",
        regex_sub(README_DE, r"badge/version-(\d+\.\d+\.\d+)-", r"badge/v\1-"),
        "kein Versions-Badge gefunden",
    ),
    Mutation(
        "version_badge",
        "ANKER: Release-Ueberschriften umformatiert",
        regex_sub(CHANGELOG, r"^## \[v?(\d+\.\d+\.\d+)\]", r"## \1"),
        "keine Release-Ueberschrift",
    ),
    # --- catalogue_drift (fidelity/14) -------------------------------------
    #
    # DIE ZAHLEN.
    Mutation(
        "catalogue_drift",
        "Manifest weg",
        remove(MANIFEST),
        f"{MANIFEST} fehlt",
    ),
    Mutation(
        "catalogue_drift",
        "Manifest-Format geaendert",
        write(MANIFEST, "FID-001\nnicht mehr eine Check-ID\n"),
        "sieht nicht aus wie eine Liste von Check-IDs",
    ),
    Mutation(
        "catalogue_drift",
        "Katalog um einen Check geschrumpft",
        drop_last_line(MANIFEST),
        "Katalog-Groesse",
    ),
    Mutation(
        "catalogue_drift",
        "ANKER: Satz zum Katalogstand umformuliert",
        replace(SKILL, "Checks in zwölf Kategorien", "Checks, zwölf Kategorien"),
        "der Satz zum Katalogstand passt nicht mehr",
    ),
    Mutation(
        "catalogue_drift",
        "ANKER: Tabellenabschnitt weg",
        replace(SKILL, "### Welche Regel welcher Check ist", "### Regel und Check"),
        "nicht gefunden",
    ),
    # DIE IDENTITAETEN — der Teil, den Summen nicht fangen.
    Mutation(
        "catalogue_drift",
        "ein verlinkter Check ist aus dem Katalog verschwunden",
        regex_sub(MANIFEST, r"^HITL-006\n", ""),
        "Die Tabelle verlinkt",
    ),
    Mutation(
        "catalogue_drift",
        "neuer FID-Check, in der Tabelle nicht verlinkt",
        append(MANIFEST, "FID-099\n"),
        "in der Tabelle nicht verlinkt",
    ),
    Mutation(
        "catalogue_drift",
        "eine verlinkte Check-Datei fehlt",
        remove(f"{CHECKS}/ARCH-003.md"),
        "liegt dazu keine Datei",
    ),
    Mutation(
        "catalogue_drift",
        "Frontmatter einer Check-Datei weg",
        write(f"{CHECKS}/OPS-009.md", "# OPS-009\n\nkein Frontmatter mehr\n"),
        "keinen Frontmatter-Block",
    ),
    Mutation(
        "catalogue_drift",
        "der ganze Katalog fehlt",
        remove(CHECKS),
        f"{MANIFEST} fehlt",
    ),
    # DIE EINSTUFUNG — der Teil, den WEDER Summen NOCH Identitaeten fangen.
    # Der Anlass steht im CHANGELOG drueben: «`ARCH-003` ist der einzige
    # `enforced` Check dieser Tabelle» war falsch, waehrend jede Summe stimmte
    # und jede ID existierte. Die erste Mutation ist genau dieser Fall — sie
    # kippt eine Einstufung und laesst alle Zahlen in Ruhe.
    Mutation(
        "catalogue_drift",
        "ein Check ist im Katalog advisory geworden",
        write(
            f"{CHECKS}/FID-001.md",
            "---\nid: FID-001\nseverity: high\nadoption: advisory\n---\n\n# FID-001\n",
        ),
        "Einstufung FID-001: hier `enforced`, im Katalog `advisory`",
    ),
    Mutation(
        "catalogue_drift",
        "ein verlinkter Check fehlt in beiden Listen",
        replace(SKILL, "`FID-002`, `FID-003`,", "`FID-003`,"),
        "weder als `enforced` noch als `advisory` genannt",
    ),
    Mutation(
        "catalogue_drift",
        "Zahlwort und Aufzaehlung laufen auseinander",
        replace(
            SKILL,
            "**Sieben Checks dieser Tabelle sind `enforced`",
            "**Acht Checks dieser Tabelle sind `enforced`",
        ),
        "zaehlt aber",
    ),
    Mutation(
        "catalogue_drift",
        "ANKER: Satz zur Einstufung umformuliert",
        replace(
            SKILL,
            "Checks dieser Tabelle sind `enforced`",
            "Checks dieser Tabelle blockieren",
        ),
        "der Satz zur Einstufung passt nicht mehr",
    ),
    Mutation(
        "catalogue_drift",
        # Beim Umzug dazugekommen: Die Herkunftsfassung las ein unbekanntes
        # Zahlwort still als `None` und meldete dann einen DRIFT — einen Befund
        # ueber den Katalog, waehrend der Fehler in der Pruefdatei lag.
        "Zahlwort, das GERMAN_NUMBERS nicht kennt",
        replace(SKILL, "Checks in zwölf Kategorien", "Checks in siebzehn Kategorien"),
        "GERMAN_NUMBERS",
    ),
]
