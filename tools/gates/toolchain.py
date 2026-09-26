"""Der Ruff-Pin hat EINE Quelle. Alles andere richtet sich nach ihr.

SEIT DER UMSTELLUNG AUF `requirements-lint.txt` steht die Version nur noch
dort. Die CI-Workflows installieren mit `pip install -r requirements-lint.txt`
und nennen selbst keine Zahl; die `rev` des Pre-Commit-Hooks muss dieselbe
Version nennen, weil pre-commit eine eigene Umgebung baut und die Datei nicht
lesen kann. Vorher stand die Zahl in `lint.yml`, in `test.yml` und im Hook —
und nur die ersten beiden der drei hielt eine Pruefung zusammen. Die Kopie in
`test.yml` lief ungeprueft mit. Eine Zahl, die dreimal existiert, sind zwei
Gelegenheiten zur Drift; die Kopien zu entfernen ist staerker, als sie zu
bewachen. Dieselbe Umstellung wie in `mcp-continuous-auditor` (#104) und die
Regel aus `github-repo-skill` §8.1.

Dazu zwei neue Befunde, beide unabhaengig vom Wert: ZWEITE QUELLE, wenn ein
Workflow ruff selbst pinnt — auch mit der richtigen Zahl, denn die Kopie ist
der Fehler, nicht die Abweichung —, und NICHT VERDRAHTET, wenn ein Workflow
nicht aus der Datei installiert.

Der Text unten beschreibt die Zusammenfuehrung aus Phase 2; er bleibt als
Herkunft stehen.

Zusammengefuehrt aus den vier Fassungen in `mcp-audit-skill`,
`mcp-data-source-probe-skill`, `mcp-data-fidelity-skill` und
`mcp-transport-hardening-skill` — Familien G1 und G2 des Merge-Plans, heute
vier Registrierungen je Familie.

Zwei der drei Stellen sind Text: `pip install ruff==…` im CI-Workflow und die
`rev` des Pre-Commit-Hooks. Laufen sie auseinander, formatiert der Hook nach
der einen und die CI prueft nach der anderen Version: Der Commit geht lokal
gruen durch und wird erst im Pull Request rot — die teuerste Reihenfolge. Das
haelt `ruff_pin_sync` zusammen.

Die dritte ist keine Deklaration, sondern das Werkzeug selbst — der `ruff`,
den der PATH als ersten findet und den die Gates tatsaechlich starten. Ihn
prueft `ruff_binary_matches_pin`, und sie ist der Grund, warum die beiden
anderen nicht genuegen: Zwei Dateien koennen sich einig sein, waehrend das
ausfuehrende Binary etwas Drittes ist.

Der Anlass ist gemessen und nicht gedacht: In einer Entwicklungsumgebung lag
ein aelterer `ruff` unter `~/.local/bin` vor dem gepinnten unter
`/usr/local/bin`. Der Pin-Sync war gruen — er liest ja Text —, und der lokale
Lauf mass mit 0.15.8, waehrend die CI mit 0.16.1 prueft.

WAS BEIM ZUSAMMENFUEHREN AUS WELCHER FASSUNG KAM:

* Die reinen Vergleichsfunktionen (`workflow_pins`, `precommit_pin`,
  `compare`) stammen aus `mcp-audit-skill`. Sie sind dort ausgelagert, weil
  der Pre-Commit-Hook `tools/check_ruff_pin.py` DIREKT aufruft
  (`language: system`) — dieser Einstiegspunkt muss erhalten bleiben, sonst
  bricht der Hook, und er ist das, was die Zusage «was lokal durchlaeuft,
  laeuft auch in der CI durch» ueberhaupt einloest. Deshalb liegt die Logik
  hier und `tools/check_ruff_pin.py` ist die duenne Huelle darum: EINE
  Implementierung, zwei Einstiege.
* Die Pruefung der HOOK-MENGE und die Auflistung beschattender Binaries
  stammen aus `mcp-data-fidelity-skill`. Beides gab es nur dort. Ein blosses
  «falsche Version» schickt den Lesenden zu `pip install`, und genau dort
  hilft es nicht: Die gepinnte Version ist dann laengst installiert, sie steht
  bloss hinter einer zweiten im PATH.
* Der Pfad des CI-Workflows ist PARAMETER, weil er sich unterscheidet:
  `lint.yml` hier, `ci.yml` in den drei anderen. Er war der einzige Grund,
  warum diese Dateien ueberhaupt auseinanderliefen.

GRENZE, AUSDRUECKLICH. `ruff_binary_matches_pin` sagt nichts darueber, welche
Version `pre-commit` installiert. Der Hook haelt seine eigene Umgebung und
startet nicht den `ruff` vom PATH; was dort laeuft, steht in der `rev`, und
mehr als die beiden Deklarationen gegeneinander zu halten ist von hier aus
nicht pruefbar.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

from tools.harness import CheckFailed

DEFAULT_CI_WORKFLOW = ".github/workflows/lint.yml"
DEFAULT_HOOKS_CONFIG = ".pre-commit-config.yaml"
DEFAULT_PIN_SOURCE = "requirements-lint.txt"

PIP_PIN = re.compile(r"\bruff\s*==\s*([0-9][^\s'\"]*)")
# `pip install -r requirements-lint.txt`, auch `--requirement`.
INSTALLS_FROM = re.compile(r"(?:-r|--requirement)[\s=]+\S*requirements-lint\.txt")
RUFF_REPO_BLOCK = re.compile(
    r"^\s*-\s*repo:\s*\S*ruff-pre-commit\s*$(.*?)(?=^\s*-\s*repo:|\Z)",
    re.MULTILINE | re.DOTALL,
)
REV = re.compile(r"^\s*rev:\s*['\"]?(\S+?)['\"]?\s*$", re.MULTILINE)

# `ruff --version` schreibt «ruff 0.16.1». Aendert sich das Format, ist das ein
# Befund und kein Durchwinken: Eine Pruefung, die ihre eigene Messung nicht
# lesen kann, hat nicht gemessen.
VERSION_LINE = re.compile(r"^ruff\s+([0-9]\S*)", re.MULTILINE)

FEHLT_RUFF = (
    "ruff liegt nicht auf dem PATH — die laufende Version laesst sich nicht "
    "ermitteln. FAIL statt skip: «nicht gelaufen» als «bestanden» zu melden "
    "ist die eine Auskunft, die schlimmer ist als keine."
)


# ---------------------------------------------------------------------------
# Reine Funktionen — ohne Datei-, PATH- oder Unterprozess-Zugriff
# ---------------------------------------------------------------------------


def workflow_pins(text: str) -> list[str]:
    """Alle woertlich gepinnten Ruff-Versionen in einem Text."""
    return PIP_PIN.findall(text)


def source_pins(text: str) -> list[str]:
    """Jede verschiedene Ruff-Version in der Pin-Quelle, Kommentare ignoriert."""
    zeilen = [z.split("#", 1)[0] for z in text.splitlines()]
    return sorted(set(workflow_pins("\n".join(zeilen))))


def requirements_pin(text: str) -> str | None:
    """Die EINE Ruff-Version der Pin-Quelle, oder `None`.

    Mehr als eine Version ist kein Pin, sondern ein Widerspruch, und kommt
    ebenfalls als `None` zurueck; `compare()` unterscheidet die beiden Faelle.
    """
    pins = source_pins(text)
    return pins[0] if len(pins) == 1 else None


def precommit_pin(text: str) -> str | None:
    """Die `rev` des ruff-pre-commit-Repos, ohne `v`-Praefix.

    `None`, wenn das Repo fehlt oder keine `rev` traegt — beides bedeutet,
    dass es nichts zu vergleichen gibt, und wird von `compare()` als Befund
    behandelt.
    """
    block = RUFF_REPO_BLOCK.search(text)
    if block is None:
        return None
    rev = REV.search(block.group(1))
    if rev is None:
        return None
    return rev.group(1).removeprefix("v")


def hook_ids(text: str) -> set[str]:
    """Die `id:`-Werte aller konfigurierten Hooks."""
    return set(re.findall(r"^\s*-\s*id:\s*(\S+)\s*$", text, re.MULTILINE))


def parse_version(raw: str) -> str | None:
    """Die Version aus der Ausgabe von `ruff --version`."""
    match = VERSION_LINE.search(raw)
    return match.group(1) if match else None


def compare(
    source_text: str,
    precommit_text: str,
    workflows: Mapping[str, str] | None = None,
    *,
    source_name: str = DEFAULT_PIN_SOURCE,
    config_name: str = DEFAULT_HOOKS_CONFIG,
    required_hooks: tuple[str, ...] = (),
) -> tuple[bool, str]:
    """Reine Vergleichsfunktion: `(alles_stimmt, Meldung)`.

    `workflows` bildet Namen auf Workflow-Texte ab. Ohne Datei- oder
    Netzzugriff, damit der Test nicht die eigene Annahme ueber das Dateiformat
    abbildet, sondern das echte Verhalten prueft. Jeder Befund wird genannt,
    nicht nur der erste — sonst kostet jede Korrektur eine Runde.

    `required_hooks` ist leer per Vorgabe, und das ist Absicht: Die Menge der
    Hooks unterscheidet sich zwischen den Repos der Kette WIRKLICH, und zwar
    begruendet. Gemessen fuehrt `mcp-transport-hardening-skill` nur
    `ruff-format`, die drei anderen zusaetzlich `ruff-check`. Das ist dort
    kein Versaeumnis: Sein `ruff.toml` fuehrt `select = []` bewusst, damit ein
    `ruff check` im Clone nicht ueber Vorlagen-Code faellt, und seine CI
    prueft stattdessen gezielt mit `ruff check --extend-select …` auf
    `reference/` und `tools/ tests/`. Ein pauschaler `ruff-check`-Hook haette
    dort keinen Gegenstand.

    Eine Vorgabe waere hier also keine gemeinsame Zusage, sondern eine
    erfundene — und der erste, der sie «erfuellt», braeche die Absicht des
    Repos, das sie nicht teilt. Wer die Menge zusichern will, nennt sie.
    """
    pin = requirements_pin(source_text)
    hook = precommit_pin(precommit_text)
    befunde = []

    if pin is None:
        gefunden = source_pins(source_text)
        if len(gefunden) > 1:
            liste = ", ".join(repr(p) for p in gefunden)
            befunde.append(f"DRIFT: {source_name} pinnt Ruff mehrfach: {liste}.")
        else:
            befunde.append(f"KEIN PIN: in {source_name} steht kein `ruff==<version>`.")
    if hook is None:
        missing = "fehlt das ruff-pre-commit-Repo oder dessen `rev:`."
        befunde.append(f"KEIN PIN: in {config_name} {missing}")
    if pin is not None and hook is not None and hook != pin:
        head = f"DRIFT: {source_name} pinnt Ruff auf {pin!r},"
        befunde.append(f"{head} {config_name} auf {hook!r}.")

    for name, text in (workflows or {}).items():
        literale = sorted(set(workflow_pins(text)))
        if literale:
            liste = ", ".join(repr(p) for p in literale)
            rest = f"aus {source_name} installieren statt selbst pinnen."
            befunde.append(f"ZWEITE QUELLE: {name} pinnt Ruff {liste} — {rest}")
        if not INSTALLS_FROM.search(text):
            rest = f"installiert nicht aus {source_name}."
            befunde.append(f"NICHT VERDRAHTET: {name} {rest}")

    fehlend = sorted(set(required_hooks) - hook_ids(precommit_text))
    if fehlend:
        befunde.append(
            f"{config_name} fuehrt {fehlend} nicht mehr. Was lokal nicht "
            "laeuft, meldet der Commit gruen und erst die CI rot — dieselbe "
            "Bruchstelle wie ein abweichender Pin, eine Zeile weiter unten."
        )

    if befunde:
        return False, "\n".join(befunde)
    return True, f"Ruff-Pin OK ({pin}; {source_name}, Hook und Workflows stimmen)."


def compare_binary(
    pinned: str | None,
    raw: str,
    returncode: int,
    *,
    source_name: str = DEFAULT_PIN_SOURCE,
    shadowing: list[str] | None = None,
) -> tuple[bool, str]:
    """Haelt den Text gegen das laufende Programm — ohne PATH, ohne Prozess.

    Alles, was schiefgehen kann, ist hier entscheidbar. Genau deshalb ist
    diese Pruefung testbar und der Workflow-Schritt, den sie ersetzt, war es
    nicht.
    """
    if pinned is None:
        return False, (
            f"{source_name} nennt kein einzelnes `ruff==<version>` — Anker weg. Ohne "
            "ihn hat diese Pruefung nichts, wogegen sie die laufende ruff "
            "haelt, und haette genau deshalb Erfolg gemeldet."
        )
    if returncode != 0:
        return False, f"`ruff --version` endete mit {returncode}: {raw.strip()}"

    running = parse_version(raw)
    if running is None:
        return False, (
            "`ruff --version` antwortet nicht in der Form 'ruff <version>' — "
            f"gelesen wurde: {raw.strip()!r}. Hat upstream die Ausgabe "
            "geaendert, gehoert VERSION_LINE hier nachgezogen; ohne das "
            "verglich diese Pruefung nichts mehr und meldete es nicht."
        )
    if running != pinned:
        listing = ""
        if shadowing:
            zeilen = "\n".join(
                f"      {path}" + ("   <- dieser laeuft" if i == 0 else "")
                for i, path in enumerate(shadowing)
            )
            listing = f"\n  Gefunden auf dem PATH:\n{zeilen}"
        return False, (
            f"Die ruff auf dem PATH ist {running}, gepinnt ist {pinned}. Die "
            "Gates laufen dann auf einer anderen Version als der gepinnten. "
            "Beide Richtungen kosten: eine aeltere laesst durch, was spaeter "
            "rot wird; eine neuere beanstandet, was der Pin durchlaesst. Der "
            "Pin-Sync merkt es nicht — er vergleicht zwei Texte miteinander, "
            "nicht den Text mit dem laufenden Programm."
            f"{listing}\n"
            f"  Ist {pinned} schon installiert, steht sie hinter einer "
            f"zweiten — sonst: pip install ruff=={pinned}"
        )
    return True, f"Ruff-Version OK ({running} auf dem PATH, wie gepinnt)."


# ---------------------------------------------------------------------------
# Die Gates — lesen Dateien und befragen den PATH
# ---------------------------------------------------------------------------


def _read(root: Path, name: str) -> str:
    path = root / name
    if not path.is_file():
        raise CheckFailed(f"Datei nicht lesbar: {path}")
    return path.read_text(encoding="utf-8")


def ruffs_on_path() -> list[str]:
    """Jede ausfuehrbare `ruff`-Datei auf dem PATH, in dessen Reihenfolge.

    Nur fuer den Befundtext. Die Liste macht eine Beschattung sichtbar, statt
    sie erraten zu lassen.
    """
    found = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry) / "ruff"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            found.append(str(candidate))
    return found


def pinned_version(root: Path, *, pin_source: str = DEFAULT_PIN_SOURCE) -> str | None:
    """Die gepinnte Version aus der Pin-Quelle — die EINE Lesung.

    Geteilt zwischen beiden Gates: Hook und Binary werden gegen dieselbe
    Stelle gehalten, nicht gegen zwei Lesungen, die auseinanderlaufen koennen.
    """
    return requirements_pin(_read(root, pin_source))


def ruff_pin_sync(
    root: Path,
    *,
    pin_source: str = DEFAULT_PIN_SOURCE,
    workflows: tuple[str, ...] = (DEFAULT_CI_WORKFLOW,),
    hooks_config: str = DEFAULT_HOOKS_CONFIG,
    required_hooks: tuple[str, ...] = (),
) -> str:
    """G1 — eine Pin-Quelle; Hook und Workflows richten sich nach ihr."""
    ok, message = compare(
        _read(root, pin_source),
        _read(root, hooks_config),
        {name: _read(root, name) for name in workflows},
        source_name=pin_source,
        config_name=hooks_config,
        required_hooks=required_hooks,
    )
    if not ok:
        raise CheckFailed(
            f"{message}\n"
            f"  Die Version steht nur in {pin_source}: dort und `rev:` in "
            f"{hooks_config} im selben Commit anheben; die Workflows "
            "installieren mit `pip install -r` und nennen keine Zahl."
        )
    return message


def ruff_version_matches_pin(
    root: Path,
    *,
    pin_source: str = DEFAULT_PIN_SOURCE,
) -> str:
    """G2 — der `ruff` auf dem PATH traegt die gepinnte Version."""
    pinned = pinned_version(root, pin_source=pin_source)

    # `shutil.which` und nicht irgendein Pfad: Genau so loesen die Ruff-Gates
    # den Namen auf, wenn sie `subprocess.run(["ruff", …])` starten. Eine
    # Pruefung, die einen anderen Binary misst als den, der die Gates faehrt,
    # waere schlimmer als keine.
    executable = shutil.which("ruff")
    if executable is None:
        raise CheckFailed(FEHLT_RUFF)

    done = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, check=False
    )
    ok, message = compare_binary(
        pinned,
        done.stdout + done.stderr,
        done.returncode,
        source_name=pin_source,
        shadowing=ruffs_on_path(),
    )
    if not ok:
        raise CheckFailed(f"{message}\n  Gelaufene ruff: {executable}")
    return message
