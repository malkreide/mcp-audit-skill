"""Die Mutationen der Suite `probe`.

Uebernommen aus `mcp-data-source-probe-skill/tests/mutations.py`. Von dessen
achtundsiebzig Mutationen stehen hier fuenfundvierzig — die uebrigen gehoerten
zu den neun Pruefungen, die im Monorepo repo-bezogen sind und in `ABSORBED`
stehen, sowie zu `probe/8`, dessen Gegenstand mit 2b-iv-c weggefallen ist
(`RETIRED`).

DIE DICHTESTE STELLE IST `templates_hold_their_properties` MIT ELF, und das
hat einen Grund, der ausserhalb dieses Repositories liegt:
`reference/retry_backoff.py` verletzte fuenf Eigenschaften, die einen
Halbmeter weiter ueber sie deklariert waren, und wurde in dem Zustand in elf
Server kopiert. Kein Schritt wurde rot, weil kein Schritt hinsah — die Datei
kompilierte, importierte und bestand beide Ruff-Gates. Alle vier hatten recht;
sie pruefen die Form. Beanstandet wurde die ZUSAGE von niemandem.
"""

from __future__ import annotations

from ._mutation import Mutation, append, regex_sub, remove, replace, write

BASE = "skills/mcp-data-source-probe"
SKILL = f"{BASE}/SKILL.md"
README = f"{BASE}/README.md"
README_DE = f"{BASE}/README.de.md"
CHANGELOG = f"{BASE}/CHANGELOG.md"
REFERENCE = f"{BASE}/reference"
SHELL = f"{REFERENCE}/probe_template.sh"
BEFUND = f"{REFERENCE}/befund_tabelle_template.md"
RETRY = f"{REFERENCE}/retry_backoff.py"
ADOPTION = f"{REFERENCE}/adoption.toml"
MUTANT = f"{REFERENCE}/_mutant.py"

MUTATIONS: list[Mutation] = [
    # --- shell_syntax (probe/1) --------------------------------------------
    Mutation(
        "shell_syntax",
        "ANKER: die Shell-Vorlage ist weg",
        remove(SHELL),
        "Anker weg",
    ),
    Mutation(
        "shell_syntax",
        "die Shell-Vorlage parst nicht",
        append(SHELL, "\nif then\n"),
        "parst nicht",
    ),
    # --- reference_imports (probe/3) ---------------------------------------
    Mutation(
        "reference_imports",
        "ANKER: reference/ ist weg",
        remove(REFERENCE),
        f"{REFERENCE} fehlt",
    ),
    Mutation(
        "reference_imports",
        "eine Vorlage importiert ein Paket, das es nicht gibt",
        write(MUTANT, "import kein_solches_paket\n"),
        "requirements-reference.txt",
    ),
    Mutation(
        "reference_imports",
        "eine Vorlage wirft beim Import",
        write(MUTANT, "raise RuntimeError('boom')\n"),
        "RuntimeError",
    ),
    Mutation(
        "reference_imports",
        # BaseException, nicht Exception: Eine Vorlage, die beim Import
        # `sys.exit` ruft, ist genauso kaputt wie eine, die wirft — nur wuerde
        # ein SystemExit sonst den ganzen Lauf mitnehmen.
        "eine Vorlage ruft beim Import sys.exit",
        write(MUTANT, "import sys\n\nsys.exit(3)\n"),
        "SystemExit",
    ),
    Mutation(
        "reference_imports",
        "eine Vorlage ohne kopierbares Symbol",
        write(MUTANT, "_privat = 1\n"),
        "keinen Namen bereit",
    ),
    # --- skill_frontmatter (probe/5) ---------------------------------------
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
        replace(SKILL, "name: mcp-data-source-probe\n", "name: mcp-probe\n"),
        "erwartet wurde name=",
    ),
    Mutation(
        "skill_frontmatter",
        "Description ueber der Grenze",
        replace(
            SKILL,
            "description: Standardisiertes",
            "description: " + "x" * 1024 + " Standardisiertes",
        ),
        "die Grenze liegt bei 1024",
    ),
    # --- cross_references (probe/6) ----------------------------------------
    Mutation(
        "cross_references",
        "ANKER: Nummerierungsschema der Ueberschriften geaendert",
        regex_sub(SKILL, r"^(#{2,4}) (\d+)\.(\d+)", r"\1 \2-\3"),
        "Nummerierungsschema",
    ),
    Mutation(
        "cross_references",
        "ANKER: Verweisnotation geaendert",
        regex_sub(SKILL, r"\((\d+\.\d+)([a-z]?)\)", r"[\1\2]"),
        "Verweisnotation",
    ),
    Mutation(
        "cross_references",
        "Verweis auf einen Abschnitt, den es nicht gibt",
        replace(
            SKILL,
            "\n# MCP Data Source Probe",
            "\nsiehe (9.9)\n\n# MCP Data Source Probe",
        ),
        "Abschnitte, die es nicht gibt",
    ),
    # --- referenced_files_exist (probe/7) ----------------------------------
    Mutation(
        "referenced_files_exist",
        "ANKER: eine referenzierte Datei fehlt",
        remove(BEFUND),
        BEFUND,
    ),
    Mutation(
        "referenced_files_exist",
        # Stand im Herkunftsrepo auf `companion/mcp-data-fidelity/README.md`.
        # Das Verzeichnis ist mit 2b-iv-c aufgeloest; die Mutation zeigt jetzt
        # auf das Adoption-Manifest, das seit dem Umzug in derselben Liste
        # steht.
        "ANKER: das Adoption-Manifest fehlt",
        remove(ADOPTION),
        ADOPTION,
    ),
    # --- version_badge (probe/9) -------------------------------------------
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
    # --- step_count (probe/11) ---------------------------------------------
    Mutation(
        "step_count",
        "ANKER: Schritt-Ueberschriften umbenannt",
        regex_sub(SKILL, r"^## Schritt (\d+):", r"## Phase \1:"),
        "keine Ueberschrift '## Schritt N:' gefunden",
    ),
    Mutation(
        "step_count",
        "ein Schritt ohne [Kern]/[Übergabe]",
        regex_sub(SKILL, r"^(## Schritt 2:.*?) \[Kern\]$", r"\1"),
        "traegt keine Markierung",
    ),
    Mutation(
        "step_count",
        "[Kern] hinter einem [Übergabe]",
        regex_sub(SKILL, r"^(## Schritt 5:.*?) \[Übergabe\]$", r"\1 [Kern]"),
        "kein zusammenhaengender Anfang",
    ),
    Mutation(
        "step_count",
        "ANKER: Frontmatter-Ziffer weg",
        replace(
            SKILL,
            "Standardisiertes 3-Schritte-Vorgehen",
            "Standardisiertes Vorgehen",
        ),
        "Frontmatter-Wendung 'Standardisiertes",
    ),
    Mutation(
        "step_count",
        "Frontmatter-Ziffer und Markierungen laufen auseinander",
        replace(
            SKILL,
            "Standardisiertes 3-Schritte-Vorgehen",
            "Standardisiertes 4-Schritte-Vorgehen",
        ),
        "das Frontmatter verspricht 4",
    ),
    Mutation(
        "step_count",
        "Zahlwort der Einleitung veraltet",
        replace(
            SKILL,
            "durchläuft die drei Schritte unten",
            "durchläuft die vier Schritte unten",
        ),
        "die Einleitung sagt 'vier'",
    ),
    Mutation(
        "step_count",
        "Zahlwort, das die Tabelle nicht kennt",
        replace(
            SKILL,
            "durchläuft die drei Schritte unten",
            "durchläuft die elf Schritte unten",
        ),
        "GERMAN_NUMBERS",
    ),
    Mutation(
        "step_count",
        "ANKER: Einleitungssatz umformuliert",
        replace(
            SKILL,
            "durchläuft die drei Schritte unten",
            "geht die drei Schritte unten durch",
        ),
        "'durchläuft die <Zahlwort> Schritte unten'",
    ),
    # --- templates_hold_their_properties (probe/17) ------------------------
    #
    # DIE BEIDEN ERSTEN SIND DER ANLASSFALL SELBST, nachgestellt: Sie machen
    # aus der Vorlage genau das, was sie einmal war, als sie in elf Server
    # kopiert wurde.
    Mutation(
        "templates_hold_their_properties",
        "der Jitter faellt aus der Vorlage",
        replace(RETRY, "random.random()", "0.5"),
        "jitters — erwartet present",
    ),
    Mutation(
        "templates_hold_their_properties",
        "die Vorlage verpackt den Fehler wieder in ein RuntimeError",
        replace(
            RETRY,
            "    raise last_error\n",
            '    raise RuntimeError(f"Upstream {url} unreachable: {last_error}")\n',
        ),
        "no_bare_runtime_error — erwartet absent",
    ),
    Mutation(
        "templates_hold_their_properties",
        "ANKER: das Manifest ist weg",
        remove(ADOPTION),
        "Anker weg",
    ),
    Mutation(
        "templates_hold_their_properties",
        "Manifest ohne [[template]]",
        write(ADOPTION, "schema = 1\nunmapped_ok = []\n"),
        "enthält kein [[template]]",
    ),
    Mutation(
        "templates_hold_their_properties",
        "Zuordnung zeigt auf eine Datei, die es nicht gibt",
        replace(
            ADOPTION,
            'file = "reference/retry_backoff.py"\nsymbol = "fetch_with_retry"',
            'file = "reference/retry_fortgezogen.py"\nsymbol = "fetch_with_retry"',
        ),
        "zeigt auf eine Datei, die es nicht gibt",
    ),
    Mutation(
        "templates_hold_their_properties",
        "Zuordnung nennt ein Symbol, das es nicht gibt",
        replace(
            ADOPTION,
            'file = "reference/retry_backoff.py"\nsymbol = "fetch_with_retry"',
            'file = "reference/retry_backoff.py"\nsymbol = "fetch_with_backoff"',
        ),
        "es gibt keine Funktion dieses Namens",
    ),
    Mutation(
        "templates_hold_their_properties",
        "eine Eigenschaft mit einer Art, die die Pruefung nicht kennt",
        replace(ADOPTION, 'kind = "literal"', 'kind = "irgendwie"'),
        "kennt sie nicht",
    ),
    Mutation(
        "templates_hold_their_properties",
        "eine Eigenschaft ohne gueltiges expect",
        replace(ADOPTION, 'expect = "absent"', 'expect = "vielleicht"'),
        "Erlaubt sind 'present' und 'absent'",
    ),
    Mutation(
        "templates_hold_their_properties",
        "eine Vorlage ohne deklarierte Eigenschaft",
        regex_sub(ADOPTION, r"^\[\[template\.property\]\]$", "[[template.merkmal]]"),
        "deklariert keine Eigenschaft",
    ),
    Mutation(
        "templates_hold_their_properties",
        # Eine neue Vorlage, die niemand zugeordnet hat, ist eine ungepruefte
        # Vorlage. Sie fiele sonst durch jede Masche: kompiliert, importiert,
        # lintet — und sichert nichts zu.
        "eine neue Vorlage, die niemand zugeordnet hat",
        write(MUTANT, "WERT = 1\n"),
        "ohne [[template]]-Eintrag",
    ),
    Mutation(
        "templates_hold_their_properties",
        "die Vorlage parst nicht",
        append(RETRY, "\ndef (:\n"),
        "`audit/10` meldet dasselbe",
    ),
    # --- readme_step_list (probe/19) ---------------------------------------
    Mutation(
        "readme_step_list",
        "die englische README verliert einen Kernschritt",
        regex_sub(
            README,
            r"^- \*\*Step 3 — .*$",
            "- **Nothing to see here.** Placeholder.",
        ),
        "markiert 3 als [Kern]",
    ),
    Mutation(
        "readme_step_list",
        "die deutsche README verliert einen Kernschritt",
        regex_sub(
            README_DE,
            r"^- \*\*Schritt 3 — .*$",
            "- **Nichts zu sehen.** Platzhalter.",
        ),
        "markiert 3 als [Kern]",
    ),
    Mutation(
        "readme_step_list",
        "die Sammelzeile laesst den letzten Schritt aus",
        replace(README, "- **Steps 4–6 — Handover.**", "- **Steps 4–5 — Handover.**"),
        "laesst einen Schritt ganz aus",
    ),
    Mutation(
        "readme_step_list",
        "die Sammelzeile schluckt einen Kernschritt",
        replace(
            README_DE,
            "- **Schritte 4–6 — Übergabe.**",
            "- **Schritte 3–6 — Übergabe.**",
        ),
        "zaehlt einen Kernschritt zur Uebergabe",
    ),
    Mutation(
        "readme_step_list",
        "ANKER: die Sammelzeile ist ganz weg",
        regex_sub(
            README,
            r"^- \*\*Steps 4–6 — .*$",
            "- **Handover.** Inputs for repository creation.",
        ),
        "keine Sammelzeile",
    ),
    Mutation(
        "readme_step_list",
        "ANKER: der Abschnitt heisst anders",
        replace(README, "\n## Features\n", "\n## What it does\n"),
        "Abschnitt '## Features' nicht gefunden",
    ),
    Mutation(
        "readme_step_list",
        "ANKER: die Aufzaehlung ist umformuliert",
        regex_sub(README_DE, r"^- \*\*Schritt (\d+) — ", r"- **Phase \1 — "),
        "kein Aufzaehlungspunkt",
    ),
]
