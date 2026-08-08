"""Pruefungen an reference/patterns.py: die offenen Namen der Vorlage."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from ._core import CheckFailed, register

TARGET = "reference/"

# Die offenen Namen, jeder mit dem Grund, warum er offen sein DARF. Der Grund
# ist der eigentliche Inhalt dieser Tabelle: eine stumme Namensliste waere nur
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

# Die Meldungsform ist selbst ein Anker. Aendert ruff sie, darf diese Pruefung
# nicht stillschweigend null Namen finden und «alles sauber» melden.
MESSAGE = re.compile(r"Undefined name `(?P<name>[^`]+)`")


def gefundene_namen(root: Path) -> set[str]:
    """Die F821-Namen, die ruff in `reference/` meldet."""
    p = subprocess.run(
        ["ruff", "check", "--extend-select", "F821", "--output-format", "json", TARGET],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    # exit 0 = keine Treffer, 1 = Treffer. Alles andere ist ruff selbst.
    if p.returncode not in (0, 1):
        raise CheckFailed(
            f"`ruff check` endete mit {p.returncode} — das ist kein Befund, "
            f"sondern ein Fehler im Werkzeug:\n{p.stderr.strip()}"
        )
    try:
        befunde = json.loads(p.stdout)
    except json.JSONDecodeError as exc:
        raise CheckFailed(
            f"`ruff check --output-format json` lieferte kein JSON ({exc}). "
            "Hat upstream die Ausgabe geaendert, gehoert diese Pruefung "
            "nachgezogen; ohne das faende sie nichts mehr und meldete es nicht."
        ) from exc

    namen = set()
    for b in befunde:
        m = MESSAGE.search(b.get("message", ""))
        if not m:
            raise CheckFailed(
                "Ein F821-Befund traegt nicht die Form 'Undefined name `x`' — "
                f"gelesen wurde: {b.get('message')!r}. Aendert upstream die "
                "Meldung, liest diese Pruefung keine Namen mehr aus und haette "
                "genau deshalb Erfolg gemeldet."
            )
        namen.add(m.group("name"))
    return namen


@register(6, "the open names in reference/patterns.py are on the allow-list")
def reference_open_names(root: Path) -> str:
    """Loest den Preis ein, den das Lint-Gate sonst nur benennt.

    Das Lint-Gate fuer `reference/` faehrt `--ignore F821`, weil die Vorlagen
    absichtlich Namen aus der Zielumgebung referenzieren. Ein echter
    Tippfehler in einem solchen Namen — `sttings.host` statt `settings.host` —
    faellt unter einer pauschalen Ausnahme ebenfalls nicht auf.

    Geprueft wird in BEIDE Richtungen, und die zweite haelt die Liste am
    Leben: Ein Name ohne Eintrag ist der Tippfehler-Fall; ein Eintrag ohne
    Namen im Baum ist der Faeulnis-Fall. Eine Liste, die nur waechst,
    beschreibt irgendwann nicht mehr die Datei, sondern ihre Geschichte — und
    liesse jeden Tippfehler durch, der einem geloeschten Namen gleicht.
    """
    gefunden = gefundene_namen(root)

    # Der Fall, der sonst als «alles sauber» durchginge: ruff liefert auf einen
    # falschen Pfad eine leere Trefferliste UND exit 0 (nachgemessen).
    if not gefunden and ERWARTET:
        raise CheckFailed(
            f"Kein einziger offener Name in {TARGET} gefunden, die Liste kennt "
            f"aber {len(ERWARTET)}. Das ist kein sauberer Baum, sondern eine "
            "Pruefung, die nichts geprueft hat — falscher Pfad, falsche Flags "
            "oder eine geaenderte ruff-Ausgabe."
        )

    unerwartet = sorted(gefunden - ERWARTET.keys())
    if unerwartet:
        raise CheckFailed(
            f"{TARGET}: offene Namen ohne Eintrag auf der Positivliste: "
            f"{unerwartet}\n"
            "  Ist es ein Tippfehler, gehoert der Name berichtigt — genau "
            "dafuer gibt es diese Liste.\n"
            "  Ist es Absicht (ein neuer Name aus der Zielumgebung), gehoert "
            "er mit Begruendung in ERWARTET in tools/checks/references.py."
        )

    veraltet = sorted(ERWARTET.keys() - gefunden)
    if veraltet:
        raise CheckFailed(
            f"Positivliste nennt Namen, die es in {TARGET} nicht mehr gibt: "
            f"{veraltet}\n"
            "  Der Block dazu wurde geloescht oder der Name geschlossen. Den "
            "Eintrag im selben Commit entfernen — eine Liste, die nur waechst, "
            "laesst irgendwann jeden Tippfehler durch, der einem geloeschten "
            "Namen gleicht."
        )

    return (
        f"{len(gefunden)} offene Namen in {TARGET}, alle auf der Positivliste, "
        "keine verwaisten Eintraege"
    )
