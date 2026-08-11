"""Der Ruff-Pin steht an drei Stellen. Sie muessen dasselbe sagen.

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
from pathlib import Path

from tools.harness import CheckFailed

DEFAULT_CI_WORKFLOW = ".github/workflows/lint.yml"
DEFAULT_HOOKS_CONFIG = ".pre-commit-config.yaml"

PIP_PIN = re.compile(r"\bruff\s*==\s*([0-9][^\s'\"]*)")
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
    """Alle im Workflow gepinnten Ruff-Versionen."""
    return PIP_PIN.findall(text)


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
    workflow_text: str,
    precommit_text: str,
    *,
    workflow_name: str = DEFAULT_CI_WORKFLOW,
    config_name: str = DEFAULT_HOOKS_CONFIG,
    required_hooks: tuple[str, ...] = (),
) -> tuple[bool, str]:
    """Reine Vergleichsfunktion: `(stimmt_ueberein, Meldung)`.

    Ohne Datei- oder Netzzugriff, damit der Test nicht die eigene Annahme
    ueber das Dateiformat abbildet, sondern das echte Verhalten prueft.

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
    pins = workflow_pins(workflow_text)
    hook = precommit_pin(precommit_text)

    if not pins:
        return False, f"KEIN PIN: in {workflow_name} steht kein `ruff==<version>`."
    if hook is None:
        missing = "fehlt das ruff-pre-commit-Repo oder dessen `rev:`."
        return False, f"KEIN PIN: in {config_name} {missing}"

    divergent = sorted({p for p in pins if p != hook})
    if divergent:
        others = ", ".join(repr(p) for p in divergent)
        head = f"DRIFT: {config_name} pinnt Ruff auf {hook!r},"
        return False, f"{head} {workflow_name} auf {others}."

    fehlend = sorted(set(required_hooks) - hook_ids(precommit_text))
    if fehlend:
        return False, (
            f"{config_name} fuehrt {fehlend} nicht mehr. Was lokal nicht "
            "laeuft, meldet der Commit gruen und erst die CI rot — dieselbe "
            "Bruchstelle wie ein abweichender Pin, eine Zeile weiter unten."
        )

    return True, f"Ruff-Pin OK ({hook}; beide Stellen stimmen ueberein)."


def compare_binary(
    pinned: str | None,
    raw: str,
    returncode: int,
    *,
    workflow_name: str = DEFAULT_CI_WORKFLOW,
    shadowing: list[str] | None = None,
) -> tuple[bool, str]:
    """Haelt den Text gegen das laufende Programm — ohne PATH, ohne Prozess.

    Alles, was schiefgehen kann, ist hier entscheidbar. Genau deshalb ist
    diese Pruefung testbar und der Workflow-Schritt, den sie ersetzt, war es
    nicht.
    """
    if pinned is None:
        return False, (
            f"{workflow_name} nennt kein `ruff==<version>` — Anker weg. Ohne "
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


def pinned_version(root: Path, *, ci_workflow: str) -> str | None:
    """Die gepinnte Version aus dem CI-Workflow — die EINE Lesung.

    Geteilt zwischen beiden Gates: Hook und Binary werden gegen dieselbe
    Stelle gehalten, nicht gegen zwei Lesungen, die auseinanderlaufen koennen.
    """
    pins = workflow_pins(_read(root, ci_workflow))
    return pins[0] if pins else None


def ruff_pin_sync(
    root: Path,
    *,
    ci_workflow: str = DEFAULT_CI_WORKFLOW,
    hooks_config: str = DEFAULT_HOOKS_CONFIG,
    required_hooks: tuple[str, ...] = (),
) -> str:
    """G1 — der Pin im CI-Workflow und der im Pre-Commit-Hook sagen dasselbe."""
    ok, message = compare(
        _read(root, ci_workflow),
        _read(root, hooks_config),
        workflow_name=ci_workflow,
        config_name=hooks_config,
        required_hooks=required_hooks,
    )
    if not ok:
        raise CheckFailed(
            f"{message}\n"
            f"  Beide Stellen im selben Commit bumpen: `rev:` in "
            f"{hooks_config} und `pip install ruff==…` in {ci_workflow}."
        )
    return message


def ruff_version_matches_pin(
    root: Path,
    *,
    ci_workflow: str = DEFAULT_CI_WORKFLOW,
) -> str:
    """G2 — der `ruff` auf dem PATH traegt die gepinnte Version."""
    pinned = pinned_version(root, ci_workflow=ci_workflow)

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
        workflow_name=ci_workflow,
        shadowing=ruffs_on_path(),
    )
    if not ok:
        raise CheckFailed(f"{message}\n  Gelaufene ruff: {executable}")
    return message
