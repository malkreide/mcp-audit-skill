"""Die GENERISCHEN Pruefungen — eine Implementierung fuer alle Suiten.

Hier steht, was in mehreren Skills dasselbe prueft. Was nur einen Skill
betrifft, steht unter `tools/suites/<name>/`. Die Grenze ist nicht
Aehnlichkeit, sondern Identitaet: Ein Gate gehoert hierher, wenn zwei Suiten
es mit denselben Worten beschreiben wuerden und sich nur die Datei- oder
Zaehl-Namen unterscheiden.

WIE EINE SUITE EIN GENERISCHES GATE BENUTZT. Die Funktionen hier nehmen ihre
repo-abhaengigen Teile als Schluesselwort-Argumente und wissen nichts von der
Registry. Die Suite bindet sie und registriert das Ergebnis:

    from tools.gates import toolchain as gates

    CI_WORKFLOW = ".github/workflows/lint.yml"

    @register(1, "…", suite=SUITE)
    def ruff_pin_sync(root: Path) -> str:
        return gates.ruff_pin_sync(root, ci_workflow=CI_WORKFLOW)

Ausgeschrieben statt `functools.partial`: Der registrierte Name bleibt so
stabil (`CHECKS_BY_NAME` in den Tests haengt daran), die Bindung ist an der
Stelle lesbar, an der die Nummer steht, und ein zusaetzliches Argument ist
eine Zeile statt einer neuen Fabrik.

WARUM DIE PARAMETER UND NICHT VIER KOPIEN. Gemessen ueber die vier
Herkunftsrepos war der Unterschied zwischen den Fassungen fast nie die Logik,
sondern ein Dateiname: Der ruff-Pin steht in `lint.yml` (dieses Repo) und in
`ci.yml` (die drei anderen). Vier Kopien wegen eines Pfades sind vier Stellen,
an denen eine Verbesserung haengenbleibt — und genau das ist passiert:
`mcp-data-fidelity-skill` prueft zusaetzlich, dass die Pre-Commit-Hooks
ueberhaupt noch da sind, und listet beschattende `ruff`-Binaries im Befund.
Die anderen drei tun das nicht, ohne dass jemand dagegen entschieden haette.

Der Plan der Zusammenfuehrung steht in `docs/consolidation/MERGE-PLAN.md`.
"""
