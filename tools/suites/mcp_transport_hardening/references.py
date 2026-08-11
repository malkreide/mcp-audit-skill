"""Die offenen Namen in `reference/patterns.py`, gegen eine Positivliste.

LOEST DEN PREIS EIN, DEN DAS LINT-GATE SONST NUR BENENNT. `ruff.toml` nimmt
`skills/*/reference/*.py` von F821 aus (siehe die Begruendung dort): Die
Vorlagen referenzieren absichtlich Namen aus der Zielumgebung. Ein echter
Tippfehler in einem solchen Namen — `sttings.host` statt `settings.host` —
faellt unter einer pauschalen Ausnahme ebenfalls nicht auf.

GEPRUEFT WIRD IN BEIDE RICHTUNGEN, und die zweite haelt die Liste am Leben:
Ein Name ohne Eintrag ist der Tippfehler-Fall; ein Eintrag ohne Namen im Baum
ist der Faeulnis-Fall. Eine Liste, die nur waechst, beschreibt irgendwann
nicht mehr die Datei, sondern ihre Geschichte — und liesse jeden Tippfehler
durch, der einem geloeschten Namen gleicht.

SKILL-EIGEN und deshalb hier: Nur dieser Skill fuehrt eine Positivliste
offener Namen. Die anderen Vorlagen der Kette sind kuerzer und kommen ohne
aus; eine generische Fassung haette einen Gegenstand und einen leeren
Parameter.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from tools.gates import references as ref_gates
from tools.harness import CheckFailed, register

from ._suite import SUITE
from .skill_doc import BASE

TARGET = f"{BASE}/reference/"
REFERENCE_DIR = f"{BASE}/reference"

#: Die offenen Namen, jeder mit dem Grund, warum er offen sein DARF. Der Grund
#: ist der eigentliche Inhalt dieser Tabelle: eine stumme Namensliste waere nur
#: eine zweite Stelle, an der «schon immer so» steht.
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

#: Die Meldungsform ist selbst ein Anker. Aendert ruff sie, darf diese Pruefung
#: nicht stillschweigend null Namen finden und «alles sauber» melden.
MESSAGE = re.compile(r"Undefined name `(?P<name>[^`]+)`")


def gefundene_namen(root: Path) -> set[str]:
    """Die F821-Namen, die ruff im Vorlagen-Verzeichnis meldet.

    `shutil.which` und nicht `["ruff", …]`: derselbe Binary, dessen Version
    `audit/2` zusichert. Das war im Herkunftsrepo anders und ist beim Umzug
    angeglichen worden.
    """
    executable = shutil.which("ruff")
    if executable is None:
        raise CheckFailed(
            "ruff liegt nicht auf dem PATH — diese Pruefung kann nicht laufen. "
            "FAIL statt skip: «nicht gelaufen» als «bestanden» zu melden ist "
            "die eine Auskunft, die schlimmer ist als keine."
        )
    done = subprocess.run(
        [
            executable,
            "check",
            "--no-cache",
            # HEBT DIE AUSNAHME AUF, DIE `ruff.toml` FUER GENAU DIESE DATEIEN
            # SETZT. Beides gehoert zusammen: Der Ignore macht den Baum
            # lintbar, obwohl die Vorlagen absichtlich offene Namen fuehren —
            # und diese Pruefung sorgt dafuer, dass er dabei keinen Tippfehler
            # mitverdeckt. Ohne diese Zeile faende sie null Namen und meldete
            # es (siehe die Leer-Pruefung unten) als Befund, nicht als Erfolg.
            "--config",
            "lint.per-file-ignores = {}",
            "--extend-select",
            "F821",
            "--output-format",
            "json",
            TARGET,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    # exit 0 = keine Treffer, 1 = Treffer. Alles andere ist ruff selbst.
    if done.returncode not in (0, 1):
        raise CheckFailed(
            f"`ruff check` endete mit {done.returncode} — das ist kein Befund, "
            f"sondern ein Fehler im Werkzeug:\n{done.stderr.strip()}"
        )
    try:
        befunde = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise CheckFailed(
            f"`ruff check --output-format json` lieferte kein JSON ({exc}). "
            "Hat upstream die Ausgabe geaendert, gehoert diese Pruefung "
            "nachgezogen; ohne das faende sie nichts mehr und meldete es nicht."
        ) from exc

    namen = set()
    for befund in befunde:
        treffer = MESSAGE.search(befund.get("message", ""))
        if not treffer:
            raise CheckFailed(
                "Ein F821-Befund traegt nicht die Form 'Undefined name `x`' — "
                f"gelesen wurde: {befund.get('message')!r}. Aendert upstream "
                "die Meldung, liest diese Pruefung keine Namen mehr aus und "
                "haette genau deshalb Erfolg gemeldet."
            )
        namen.add(treffer.group("name"))
    return namen


@register(6, "the open names in reference/ are on the allow-list", suite=SUITE)
def reference_open_names(root: Path) -> str:
    gefunden = gefundene_namen(root)

    # Der Fall, der sonst als «alles sauber» durchginge: ruff liefert auf einen
    # falschen Pfad eine leere Trefferliste UND exit 0.
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
            "er mit Begruendung in ERWARTET."
        )

    veraltet = sorted(ERWARTET.keys() - gefunden)
    if veraltet:
        raise CheckFailed(
            f"{TARGET}: die Positivliste nennt Namen, die dort nicht mehr "
            f"offen sind: {veraltet}\n"
            "  Eine Liste, die nur waechst, beschreibt irgendwann nicht mehr "
            "die Datei, sondern ihre Geschichte — und liesse jeden Tippfehler "
            "durch, der einem geloeschten Namen gleicht."
        )

    return f"{len(gefunden)} offene Namen, alle mit Begruendung auf der Liste"


@register(12, "reference/patterns.py imports against the pinned SDK", suite=SUITE)
def reference_imports(root: Path) -> str:
    """MIT PHASE 5 HERUEBERGEHOLT — sonst waere sie mit dem Repo verschwunden.

    Diese Zusage lief im Herkunftsrepo als CI-Schritt und hatte hier bis
    Phase 5 KEINEN Gegenstand: `audit/10` uebersetzt die Vorlage, mehr nicht.
    `compileall` beweist, dass die Datei PARST, und das ist weniger, als es
    klingt — die Vorlage importiert `from mcp.server.mcpserver import
    MCPServer` und `from mcp.server.transport_security import
    TransportSecuritySettings`. Das sind die zwei Zeilen, um die es in Regel 1
    geht, und die 1.x-Fassung (`mcp.server.fastmcp`) gibt es in 2.0.0
    nachweislich nicht mehr. Ein Import auf ein Modul, das es nicht mehr gibt,
    parst einwandfrei.

    DERSELBE MECHANISMUS WIE `probe/3`, ABER AUS EINEM ANDEREN GRUND. Dort
    lautet die Frage «laedt die Vorlage ueberhaupt?», hier «beschreibt sie noch
    die Oberflaeche, die es gibt?». Der zweite Gegenstand ist der Anlass, die
    Mechanik nach `tools/gates/references.py` zu heben — vorher waere es eine
    Abstraktion ohne zweiten Fall gewesen.

    GEGEN DIE GEPINNTE SDK, nicht gegen die neueste. Der Pin steht in
    `requirements-reference.txt` und ist Absicht: Ungepinnt faerbte ein fremdes
    Release die CI an unberuehrtem Vorlagen-Code rot. Was diese Pruefung damit
    NICHT merkt — dass upstream die Oberflaeche in 2.1 verschiebt —, misst
    `.github/workflows/sdk-drift.yml` woechentlich gegen die jeweils neueste.
    Die beiden gehoeren zusammen; einzeln ist jede eine halbe Zusage.
    """
    return ref_gates.python_imports(
        root, source_dirs=(REFERENCE_DIR,), praefix="_transport_reference_"
    )
