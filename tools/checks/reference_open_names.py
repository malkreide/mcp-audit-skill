"""Die offenen Namen in reference/patterns.py stehen auf einer Positivliste.

WARUM ES DIESEN CHECK GIBT. Das Lint-Gate fuer `reference/` faehrt
`--ignore F821`, weil die Vorlagen absichtlich Namen aus der Zielumgebung
referenzieren. Der Preis stand seither im Kommentar: Ein echter Tippfehler in
einem solchen Namen — `sttings.host` statt `settings.host` — faellt unter einer
pauschalen Ausnahme ebenfalls nicht auf. Genau diesen Preis loest dieser Check
ein. `--ignore F821` bleibt im Lint-Schritt; hier wird F821 einzeln geprueft,
gegen eine Liste statt gegen nichts.

GEPRUEFT WIRD IN BEIDE RICHTUNGEN, und die zweite ist die, die die Liste am
Leben haelt:

* Ein offener Name, der NICHT auf der Liste steht, ist ein Fehler. Das ist der
  Tippfehler-Fall, um den es geht.
* Ein Name auf der Liste, den es im Baum NICHT MEHR gibt, ist ebenfalls ein
  Fehler. Eine Liste, die nur waechst, beschreibt irgendwann nicht mehr die
  Datei, sondern ihre Geschichte — und haette dann jeden Tippfehler
  durchgelassen, der zufaellig einem geloeschten Namen gleicht.

Der Preis davon gehoert dazugesagt: Wer einen Vorlagen-Block hinzufuegt oder
loescht, muss diese Liste im selben Commit nachziehen. Das ist dieselbe Sorte
Pflege wie die WORDS-Tabelle in rule_count.py, und aus demselben Grund
in Kauf genommen.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

TARGET = "reference/"

# Die offenen Namen, jeder mit dem Grund, warum er offen sein DARF. Der Grund
# ist der eigentliche Inhalt dieser Datei: eine stumme Namensliste waere nur
# eine zweite Stelle, an der «schon immer so» steht.
ERWARTET = {
    # Aus der Zielumgebung — das Projekt bringt sie mit, die Vorlage nicht.
    "get_settings": "Settings-Zugriff des Zielprojekts",
    "settings": "Settings-Objekt, im Zielprojekt via Fixture oder Parameter",
    "api": "der Client des Zielprojekts",
    "build_http_client": "Client-Factory des Zielprojekts",
    "register_tools": "Tool-Registrierung des Zielprojekts",
    "PACKAGE": "Paketname des Zielprojekts (fuer `python -m <paket>`)",
    "CREDENTIALS_BY_ISSUER": "Credential-Store des Zielprojekts, nach Issuer",
    # Fehlertypen, die das Zielprojekt definiert.
    "AuthError": "Fehlertyp des Zielprojekts",
    "HeaderMismatchError": "Fehlertyp des Zielprojekts",
    # Krypto-Primitiven fuer Handles — bewusst offen, weil die Wahl des
    # Verfahrens beim Zielprojekt liegt.
    "_sign": "Signatur-Primitive des Zielprojekts",
    "_verify": "Verifikations-Primitive des Zielprojekts",
    # Testhelfer, die das Zielprojekt in seiner conftest.py stellt.
    "_call": "Testhelfer: baut eine JSON-RPC-Anfrage",
    "_callback": "Testhelfer: baut einen OAuth-Callback",
    "_params": "Testhelfer: baut Tool-Parameter",
    "_recorded_flow": "Testhelfer: baut einen aufgezeichneten OAuth-Flow",
    "_now": "Testhelfer: einfrierbare Uhr",
    "_key_from": "Testhelfer: Idempotenzschluessel aus Parametern",
    "_addressed_name": "Testhelfer: liest den adressierten Tool-Namen",
    "_CONFIRM_REQUEST": "Testkonstante: die Bestaetigungs-Anfrage",
}

# Die Meldungsform ist selbst ein Anker. Aendert ruff sie, darf dieser Check
# nicht stillschweigend null Namen finden und «alles sauber» melden.
MESSAGE = re.compile(r"Undefined name `(?P<name>[^`]+)`")


def gefundene_namen() -> set[str]:
    p = subprocess.run(  # noqa: S603
        ["ruff", "check", "--extend-select", "F821", "--output-format", "json", TARGET],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    # exit 0 = keine Treffer, 1 = Treffer. Alles andere ist ruff selbst.
    if p.returncode not in (0, 1):
        sys.exit(
            f"`ruff check` endete mit {p.returncode} — das ist kein Befund, "
            f"sondern ein Fehler im Werkzeug:\n{p.stderr.strip()}"
        )
    try:
        befunde = json.loads(p.stdout)
    except json.JSONDecodeError as exc:
        sys.exit(
            f"`ruff check --output-format json` lieferte kein JSON ({exc}). "
            "Hat upstream die Ausgabe geaendert, gehoert dieser Check "
            "nachgezogen; ohne das faende er nichts mehr und meldete es nicht."
        )

    namen = set()
    for b in befunde:
        m = MESSAGE.search(b.get("message", ""))
        if not m:
            sys.exit(
                "Ein F821-Befund traegt nicht die Form 'Undefined name `x`' — "
                f"gelesen wurde: {b.get('message')!r}. Aendert upstream die "
                "Meldung, liest dieser Check keine Namen mehr aus und haette "
                "genau deshalb Erfolg gemeldet."
            )
        namen.add(m.group("name"))
    return namen


def main() -> None:
    gefunden = gefundene_namen()

    # Der Fall, der sonst als «alles sauber» durchginge: ruff liefert auf einen
    # falschen Pfad eine leere Trefferliste UND exit 0 (nachgemessen). Ohne
    # diesen Zweig meldete der Check dann «keine unerwarteten Namen».
    if not gefunden and ERWARTET:
        sys.exit(
            f"Kein einziger offener Name in {TARGET} gefunden, die Liste "
            f"kennt aber {len(ERWARTET)}. Das ist kein sauberer Baum, sondern "
            "ein Check, der nichts geprueft hat — falscher Pfad, falsche "
            "Flags oder eine geaenderte ruff-Ausgabe."
        )

    unerwartet = sorted(gefunden - ERWARTET.keys())
    if unerwartet:
        sys.exit(
            f"{TARGET}: offene Namen ohne Eintrag auf der Positivliste: "
            f"{unerwartet}\n"
            "  Ist es ein Tippfehler, gehoert der Name berichtigt — genau "
            "dafuer gibt es diese Liste.\n"
            "  Ist es Absicht (ein neuer Name aus der Zielumgebung), gehoert "
            "er mit Begruendung in ERWARTET in tools/checks/reference_open_names.py."
        )

    veraltet = sorted(ERWARTET.keys() - gefunden)
    if veraltet:
        sys.exit(
            f"Positivliste nennt Namen, die es in {TARGET} nicht mehr gibt: "
            f"{veraltet}\n"
            "  Der Block dazu wurde geloescht oder der Name geschlossen. Den "
            "Eintrag im selben Commit entfernen — eine Liste, die nur waechst, "
            "laesst irgendwann jeden Tippfehler durch, der einem geloeschten "
            "Namen gleicht."
        )

    print(
        f"ok — {len(gefunden)} offene Namen in {TARGET}, alle auf der "
        "Positivliste, keine verwaisten Eintraege"
    )


if __name__ == "__main__":
    main()
