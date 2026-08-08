"""Die ruff auf dem PATH traegt die Version, die ci.yml pinnt.

`ruff_pin_sync.py` vergleicht zwei TEXTE. Er belegt, dass ci.yml und der
Pre-Commit-Hook dieselbe Zahl nennen — nicht, dass die ruff, die
`ruff format --check` gefahren hat, diese Zahl traegt. Liegt eine andere ruff
weiter vorne im PATH als die gerade installierte, meldet er weiter «beide
Stellen stimmen ueberein», und das Gate laeuft daneben auf einer Version, die
niemand gepinnt hat.

Fuer dieses Repo ist das nicht theoretisch, und ruff.toml sagt warum: Bis
0.15.8 liess `ruff format --check .` Markdown unberuehrt, seit 0.16.1 ist die
Formatierung von Python-Bloecken in Markdown stabil und standardmaessig an.
Genau der Unterschied, gegen den der Pin existiert — und ohne diesen Check
haette der Pin ihn nur behauptet.

Gemessen im Schwester-Repo mcp-data-source-probe-skill (Check 18): ruff 0.15.8
vor 0.16.1 im PATH, der Pin-Sync gruen, das Gate auf der falschen Version.
0.15.8 ist kein ausgedachter Wert — es ist die Version, die das Portfolio
sonst fuehrt. Beim Bau des Lint-Gates trat derselbe Fall in der
Entwicklungsumgebung noch einmal auf.

DREI ANKER, und jeder faellt mit einer eigenen Meldung statt still:
der Pin in ci.yml, die Anwesenheit von ruff auf dem PATH, und die AUSGABEFORM
`ruff <version>`. Aendert upstream die Form, darf dieser Check nicht
stillschweigend nichts mehr vergleichen — er sagt dann, dass er die Antwort
nicht lesen konnte.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys

from _ruff_pin import lies_pin

ANKER_HINWEIS = (
    " — Anker weg. Ohne ihn hat dieser Schritt nichts, wogegen er die laufende "
    "ruff haelt, und haette genau deshalb Erfolg gemeldet."
)

# Die Ausgabeform «ruff 0.16.1» ist selbst ein Anker.
AUSGABE = re.compile(r"^ruff\s+(?P<version>[0-9]\S*)", re.M)


def laufende_version() -> tuple[str, str]:
    pfad = shutil.which("ruff")
    if pfad is None:
        sys.exit(
            "::error::ruff liegt nicht auf dem PATH — die laufende Version "
            "laesst sich nicht ermitteln. FAIL statt skip: ein uebersprungener "
            "Schritt meldete «bestanden», wo «nicht gelaufen» richtig waere."
        )
    p = subprocess.run(  # noqa: S603
        [pfad, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    roh = (p.stdout + p.stderr).strip()
    if p.returncode != 0:
        sys.exit(f"::error::`ruff --version` endete mit einem Fehler: {roh}")
    m = AUSGABE.search(roh)
    if not m:
        sys.exit(
            "::error::`ruff --version` antwortet nicht in der Form "
            f"'ruff <version>' — gelesen wurde: {roh}. Hat upstream die Ausgabe "
            "geaendert, gehoert das Muster in tools/checks/ruff_version.py "
            "nachgezogen; ohne das vergliche dieser Schritt nichts mehr und "
            "meldete es nicht."
        )
    return m.group("version"), pfad


def main() -> None:
    ci = lies_pin(zusatz=ANKER_HINWEIS)
    running, pfad = laufende_version()
    if running != ci:
        sys.exit(
            f"::error::Die ruff auf dem PATH ist {running}, gepinnt ist {ci} "
            f"({pfad}). Das Format-Gate laeuft dann auf einer anderen Version "
            "als der gepinnten. Beide Richtungen kosten: eine aeltere laesst "
            "durch, was spaeter rot wird; eine neuere beanstandet, was der Pin "
            "durchlaesst. Der Pin-Sync merkt es nicht — er vergleicht zwei "
            "Texte miteinander, nicht den Text mit dem laufenden Programm."
        )
    print(f"Ruff-Version OK ({running} auf dem PATH, wie in ci.yml gepinnt).")


if __name__ == "__main__":
    main()
