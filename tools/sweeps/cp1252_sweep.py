"""Portfolio-Sweep zu `OPS-005` (siebte Ausprägung, Modus 5): Zeichen ausserhalb
von cp1252 in den Skripten unter `scripts/`.

Aufruf:

    python tools/sweeps/cp1252_sweep.py <verzeichnis> [--lauf] [--zeitschranke S]

`<verzeichnis>` enthält ein Unterverzeichnis je Repo, gelesen wird nur. Braucht
PyYAML und `git`. Das Ergebnis ist JSON auf stdout und eine LESELISTE, kein
Urteil. Jeder Kandidat ist von Hand nachzulesen, bevor er irgendwo als Befund
steht.

Klassiert wird über den Syntaxbaum. Ein Pfeil in einem Kommentar kommt dort
nicht vor und ist damit kein Fund, und eine Escape-Folge im Quelltext ist dort
dasselbe Zeichen wie das Literal. Drei Klassen:

  docstring     Docstring eines Moduls, einer Klasse oder einer Funktion. Gibt
                die Datei ihn aus (`description=__doc__`), bricht auch er;
                deshalb steht je Datei `liest_doc` daneben.
  eingabedatum  Muster oder durchsuchter Text einer Regex-Funktion aus `re`.
                Der Ersatztext von `sub` und `subn` zählt nicht dazu: Er wird
                geschrieben, nicht gelesen.
  kandidat      alles Übrige. Das ist absichtlich zu weit: Auch ein Vergleich
                (`"x" in zeile`), eine Ausgabe nach stderr und eine Datei mit
                `encoding="utf-8"` landen hier und fallen beim Nachlesen.

Was beim Nachlesen zu wissen ist: Python schreibt stderr immer mit
`backslashreplace`, auch unter `PYTHONIOENCODING=cp1252`. `raise SystemExit(...)`
und `print(..., file=sys.stderr)` können an der Kodierung nicht abbrechen. Das
Feld `kontext` nennt dafür den umgebenden Aufruf. `stellt_stdout_um` sagt, dass
die Datei irgendwo `reconfigure()` oder `TextIOWrapper` verwendet, und nicht,
dass das die Fundstelle abdeckt.

Ein Skript ist ein Gate, wenn ein Workflow oder die pre-commit-Konfiguration es
AUFRUFT. Gelesen werden dafür die `run:`- und `entry:`-Werte ohne Kommentare,
aufgelöst gegen `working-directory`. `ruff check scripts/x.py` ist kein Aufruf.
Was nur erwähnt ist, steht unter `erwaehnt`: Dort ist ein Aufruf zu suchen, den
die Erkennung verpasst hat.

Mit `--lauf` werden `check_version_sync.py` und `check_ruff_pin.py` im jeweiligen
Repo unter `PYTHONIOENCODING=cp1252` ausgeführt, mit dem Python, das den Sweep
fährt. Der Lauf kann einen Fund BESTÄTIGEN, aber nicht ENTLASTEN: Ein Gate, das
vorher aus anderem Grund abbricht (falsches ruff, fehlende Datei), erreicht die
Zeile nicht. Andere Skripte laufen nie. Sie brauchen Argumente, das Netz oder
schreiben Dateien.

Was der Sweep NICHT sieht: Zeichen, die erst zur Laufzeit entstehen (gelesene
Dateien, Ausgaben von Subprozessen, `chr(...)`), Texte aus dem Paket unter
`src/`, Skripte in anderen Sprachen und jedes Verzeichnis ausser `scripts/` im
Wurzelverzeichnis. Ein Repo ohne Kandidaten ist nicht entlastet.

Die Ausgabe ist reines ASCII und damit selbst in cp1252 kodierbar. Zeichen
ausserhalb von cp1252 erscheinen überall als `U+XXXX`, in Textstellen als
`<U+XXXX>`.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tomllib
import warnings
from pathlib import Path

#: Regex-Funktion -> Position des Ersatztexts, falls es einen gibt.
REGEX_FUNKTIONEN: dict[str, int | None] = {
    "compile": None,
    "escape": None,
    "findall": None,
    "finditer": None,
    "fullmatch": None,
    "match": None,
    "search": None,
    "split": None,
    "sub": 1,
    "subn": 1,
}

#: Aufrufe, die einen Text zusammensetzen und ihn weder lesen noch schreiben.
TEXTMETHODEN = {"format", "join"}

TEXTBREITE = 60

#: Die einzigen Skripte, die der Sweep ausführt. Beide lesen nur.
LAUF_GATES = ("scripts/check_version_sync.py", "scripts/check_ruff_pin.py")

HINWEIS = (
    "Leseliste, kein Urteil. Jeder Kandidat ist von Hand nachzulesen. Der Lauf "
    "kann einen Fund bestätigen, aber nicht entlasten: Ein Gate, das vorher aus "
    "anderem Grund abbricht, erreicht die Zeile nicht."
)


def ist_cp1252(zeichen: str) -> bool:
    try:
        zeichen.encode("cp1252")
    except UnicodeEncodeError:
        return False
    return True


def codepunkt(zeichen: str) -> str:
    return f"U+{ord(zeichen):04X}"


def lesbar(text: str) -> str:
    """Derselbe Text, jedes Zeichen ausserhalb von cp1252 als `<U+XXXX>`."""
    return "".join(c if ist_cp1252(c) else f"<{codepunkt(c)}>" for c in text)


def alles_lesbar(wert: object) -> object:
    if isinstance(wert, str):
        return lesbar(wert)
    if isinstance(wert, dict):
        return {lesbar(str(k)): alles_lesbar(v) for k, v in wert.items()}
    if isinstance(wert, list):
        return [alles_lesbar(v) for v in wert]
    return wert


def ausschnitt(text: str) -> str:
    """Die Umgebung des ersten Zeichens, das den Text zum Fund macht."""
    stelle = next(i for i, c in enumerate(text) if not ist_cp1252(c))
    ab = max(0, stelle - TEXTBREITE)
    return lesbar(text[ab : stelle + TEXTBREITE])


# --- Klassierung ------------------------------------------------------------


class Datei:
    """Ein Syntaxbaum mit Elternverweisen und den Namen, unter denen `re` läuft."""

    def __init__(self, baum: ast.Module) -> None:
        self.baum = baum
        self.eltern: dict[ast.AST, ast.AST] = {}
        self.docstrings: set[ast.AST] = set()
        self.re_module: set[str] = set()
        self.re_namen: dict[str, str] = {}
        for knoten in ast.walk(baum):
            for kind in ast.iter_child_nodes(knoten):
                self.eltern[kind] = knoten
            self._merke_docstring(knoten)
            self._merke_import(knoten)

    def _merke_docstring(self, knoten: ast.AST) -> None:
        traeger = ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        if not isinstance(knoten, traeger) or not knoten.body:
            return
        erste = knoten.body[0]
        if isinstance(erste, ast.Expr) and isinstance(erste.value, ast.Constant):
            self.docstrings.add(erste.value)

    def _merke_import(self, knoten: ast.AST) -> None:
        if isinstance(knoten, ast.Import):
            self.re_module |= {
                a.asname or a.name for a in knoten.names if a.name == "re"
            }
        elif isinstance(knoten, ast.ImportFrom) and knoten.module == "re":
            for a in knoten.names:
                self.re_namen[a.asname or a.name] = a.name

    def regex_funktion(self, ruf: ast.Call) -> str | None:
        f = ruf.func
        if isinstance(f, ast.Name):
            name = self.re_namen.get(f.id)
        elif (
            isinstance(f, ast.Attribute)
            and isinstance(f.value, ast.Name)
            and f.value.id in self.re_module
        ):
            name = f.attr
        else:
            return None
        return name if name in REGEX_FUNKTIONEN else None

    def ist_eingabedatum(self, knoten: ast.AST) -> bool:
        """Steht der Text in einem gelesenen Argument einer Regex-Funktion?"""
        kind = knoten
        while (vater := self.eltern.get(kind)) is not None:
            if isinstance(vater, ast.Lambda | ast.stmt):
                return False
            if isinstance(vater, ast.Call):
                name = self.regex_funktion(vater)
                if name is not None:
                    return not ist_ersatztext(vater, kind, REGEX_FUNKTIONEN[name])
                if not ist_textmethode(vater):
                    return False
            kind = vater
        return False

    def klasse(self, knoten: ast.AST) -> str:
        if knoten in self.docstrings:
            return "docstring"
        return "eingabedatum" if self.ist_eingabedatum(knoten) else "kandidat"

    def kontext(self, knoten: ast.AST) -> str:
        """Der nächste Aufruf, der den Text entgegennimmt, sonst die Anweisung."""
        kind = knoten
        while (vater := self.eltern.get(kind)) is not None:
            if isinstance(vater, ast.Call) and not ist_textmethode(vater):
                ziel = [k for k in vater.keywords if k.arg == "file"]
                zusatz = f"(file={ast.unparse(ziel[0].value)})" if ziel else ""
                return ast.unparse(vater.func) + zusatz
            if isinstance(vater, ast.stmt):
                return type(vater).__name__
            kind = vater
        return "?"


def ist_textmethode(ruf: ast.Call) -> bool:
    return isinstance(ruf.func, ast.Attribute) and ruf.func.attr in TEXTMETHODEN


def ist_ersatztext(ruf: ast.Call, kind: ast.AST, stelle: int | None) -> bool:
    if stelle is None:
        return False
    if isinstance(kind, ast.keyword):
        return kind.arg == "repl"
    return len(ruf.args) > stelle and ruf.args[stelle] is kind


def grund(fehler: Exception) -> str:
    """Eine Zeile, auch wenn die Meldung mehrere hat."""
    return " ".join(f"{type(fehler).__name__}: {fehler}".split())


def lies_baum(pfad: Path) -> ast.Module:
    with warnings.catch_warnings():
        # Eine ungültige Escape-Folge im fremden Skript ist nicht die Frage.
        warnings.simplefilter("ignore")
        return ast.parse(pfad.read_bytes())


def untersuche_skript(pfad: Path) -> dict:
    try:
        baum = lies_baum(pfad)
    except (SyntaxError, ValueError, OSError) as fehler:
        return {"nicht_erhoben": grund(fehler)}

    datei = Datei(baum)
    funde = []
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Constant) or not isinstance(knoten.value, str):
            continue
        fremd = sorted({c for c in knoten.value if not ist_cp1252(c)})
        if not fremd:
            continue
        funde.append(
            {
                "klasse": datei.klasse(knoten),
                "zeile": knoten.lineno,
                "zeile_ende": knoten.end_lineno,
                "codepunkte": [codepunkt(c) for c in fremd],
                "kontext": datei.kontext(knoten),
                "text": ausschnitt(knoten.value),
            }
        )
    namen = {n.id for n in ast.walk(baum) if isinstance(n, ast.Name)}
    attribute = {n.attr for n in ast.walk(baum) if isinstance(n, ast.Attribute)}
    umsteller = {"reconfigure", "TextIOWrapper"}
    return {
        "liest_doc": "__doc__" in namen | attribute,
        "stellt_stdout_um": bool(umsteller & (namen | attribute)),
        "funde": sorted(funde, key=lambda f: (f["zeile"], f["zeile_ende"])),
    }


# --- Gates ------------------------------------------------------------------

#: Wurzel des Checkouts in den Schreibweisen, die ein Workflow dafür kennt.
WURZEL = re.compile(r"\$(?:\{\{\s*github\.workspace\s*\}\}|\{?GITHUB_WORKSPACE\}?)/")
WURZELMARKE = "@wurzel/"

KOMMENTAR = re.compile(r"(?:^|(?<=\s))#.*$", re.MULTILINE)

AUFRUF = re.compile(
    r"""
    (?: (?:^|[;&|(])\s*                                # direkt ausgeführt
      | [^\s"';&|(]*python[\d.]*"?                     # ein Python
        (?:\s+-(?:[XW]\s*\S+|[A-Za-ln-z]+))*\s+        # mit Schaltern, ohne -m
      | \buv\s+run(?:\s+-\S+)*\s+
    )
    (?: -m\s+(?P<modul>scripts\.\w+)
      | ["']?(?P<pfad>(?:[^\s"';&|(]*/)?scripts/[\w/-]+\.py)\b
    )
    """,
    re.VERBOSE | re.MULTILINE,
)


def ohne_kommentare(befehl: str) -> str:
    return re.sub(r"\\\n\s*", " ", KOMMENTAR.sub("", befehl))


def aufgerufene_skripte(befehl: str, verzeichnis: str = ".") -> set[str]:
    gefunden = set()
    for treffer in AUFRUF.finditer(WURZEL.sub(WURZELMARKE, ohne_kommentare(befehl))):
        if treffer["modul"]:
            pfad = treffer["modul"].replace(".", "/") + ".py"
        else:
            pfad = treffer["pfad"]
        if pfad.startswith(WURZELMARKE):
            pfad = pfad.removeprefix(WURZELMARKE)
        else:
            pfad = posixpath.join(verzeichnis, pfad)
        gefunden.add(posixpath.normpath(pfad))
    return gefunden


def arbeitsverzeichnis(knoten: dict, vorgabe: str) -> str:
    vorgaben = (knoten.get("defaults") or {}).get("run") or {}
    return str(vorgaben.get("working-directory") or vorgabe)


def workflow_befehle(daten: object) -> list[tuple[str, str]]:
    """Jeder `run:`-Block samt dem Verzeichnis, in dem er läuft."""
    if not isinstance(daten, dict):
        return []
    oben = arbeitsverzeichnis(daten, ".")
    # Ein Workflow hat Jobs, eine zusammengesetzte Aktion nur `runs`.
    jobs = [*(daten.get("jobs") or {}).values(), daten.get("runs")]
    befehle = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        mitte = arbeitsverzeichnis(job, oben)
        for schritt in job.get("steps") or []:
            if isinstance(schritt, dict) and isinstance(schritt.get("run"), str):
                ort = str(schritt.get("working-directory") or mitte)
                befehle.append((schritt["run"], ort))
    return befehle


def hook_befehle(daten: object) -> list[tuple[str, str]]:
    befehle = []
    for quelle in (daten.get("repos") if isinstance(daten, dict) else None) or []:
        for hook in quelle.get("hooks") or []:
            teile = [hook.get("entry") or "", *(hook.get("args") or [])]
            befehle.append((" ".join(map(str, teile)).strip(), "."))
    return befehle


class Pipeline:
    """Was Workflows, Aktionen und pre-commit aufrufen."""

    def __init__(self, repo: Path) -> None:
        import yaml  # type: ignore[import-untyped]

        self.befehle: dict[str, list[tuple[str, str]]] = {}
        self.texte: dict[str, str] = {}
        self.hooks: object = None
        self.nicht_erhoben: dict[str, str] = {}
        ablage = repo / ".github"
        pfade = [
            *sorted(ablage.glob("workflows/*.y*ml")),
            *sorted(ablage.glob("actions/**/action.y*ml")),
            repo / ".pre-commit-config.yaml",
        ]
        for pfad in pfade:
            if not pfad.is_file():
                continue
            name = pfad.relative_to(repo).as_posix()
            try:
                self.texte[name] = pfad.read_text(encoding="utf-8")
                daten = yaml.safe_load(self.texte[name])
            except (OSError, ValueError, yaml.YAMLError) as fehler:
                self.nicht_erhoben[name] = grund(fehler)
                continue
            if pfad.parent == repo:
                self.hooks = daten
                self.befehle[name] = hook_befehle(daten)
            else:
                self.befehle[name] = workflow_befehle(daten)

    def einordnung(self, skript: str) -> dict:
        aufrufe = [
            name
            for name, befehle in self.befehle.items()
            if any(skript in aufgerufene_skripte(b, ort) for b, ort in befehle)
        ]
        erwaehnt = [name for name, text in self.texte.items() if skript in text]
        return {
            "gate": bool(aufrufe),
            "aufrufe": aufrufe,
            "erwaehnt": [name for name in erwaehnt if name not in aufrufe],
        }


# --- Zusatzwerte ------------------------------------------------------------


def lies_toml(pfad: Path) -> dict:
    return tomllib.loads(pfad.read_text(encoding="utf-8")) if pfad.is_file() else {}


def ruff_pins(repo: Path, pyproject: dict, pipeline: Pipeline) -> list[dict]:
    """Jede Versionsangabe für ruff, auch eine Spanne, mit ihrer Quelle."""
    pins = []
    projekt = pyproject.get("project") or {}
    listen = {"project.dependencies": projekt.get("dependencies") or []}
    for name, liste in (projekt.get("optional-dependencies") or {}).items():
        listen[f"project.optional-dependencies.{name}"] = liste
    for name, liste in (pyproject.get("dependency-groups") or {}).items():
        listen[f"dependency-groups.{name}"] = liste
    for name, liste in listen.items():
        for angabe in liste:
            if isinstance(angabe, str) and re.match(r"ruff\b(?!-)", angabe):
                pins.append({"angabe": angabe, "quelle": f"pyproject.toml {name}"})

    for pfad in sorted(repo.glob("requirements*.txt")):
        for zeile in KOMMENTAR.sub("", pfad.read_text(encoding="utf-8")).splitlines():
            if re.match(r"\s*ruff\b(?!-)", zeile):
                pins.append({"angabe": zeile.strip(), "quelle": pfad.name})

    for name, befehle in pipeline.befehle.items():
        text = "\n".join(ohne_kommentare(befehl) for befehl, _ in befehle)
        versionen = re.findall(r"\bruff\s*(?:==|@)\s*(\d[\w.]*)", text)
        for version in dict.fromkeys(versionen):
            pins.append({"angabe": f"ruff=={version}", "quelle": name})

    hooks = pipeline.hooks if isinstance(pipeline.hooks, dict) else {}
    for quelle in hooks.get("repos") or []:
        if "ruff-pre-commit" in str(quelle.get("repo")):
            version = str(quelle.get("rev")).removeprefix("v")
            ort = ".pre-commit-config.yaml rev"
            pins.append({"angabe": f"ruff=={version}", "quelle": ort})
    return pins


def ruff_format(repo: Path, pyproject: dict) -> dict:
    """Die Konfiguration, die ruff im Wurzelverzeichnis fände."""
    name, werte = "pyproject.toml", (pyproject.get("tool") or {}).get("ruff") or {}
    for eigene in ("ruff.toml", ".ruff.toml"):
        if (repo / eigene).is_file():
            name, werte = eigene, lies_toml(repo / eigene)
    breite = werte.get("line-length")
    format_ = werte.get("format") or {}
    return {
        "line_length": 88 if breite is None else breite,
        "skip_magic_trailing_comma": bool(format_.get("skip-magic-trailing-comma")),
        "quelle": "Vorgabe von ruff" if breite is None else name,
    }


#: Was einem `pip install` die Zielumgebung gibt (`OPS-006`, Schritt 6).
ZIELUMGEBUNG = re.compile(r"--python\b|venv[/\\]|sys\.executable")


def rat(repo: Path) -> dict:
    """Nennt ein ausgegebener Rat ein `pip install` ohne Zielumgebung?"""
    pfad = repo / "scripts" / "check_ruff_pin.py"
    if not pfad.is_file():
        return {"nicht_erhoben": "scripts/check_ruff_pin.py fehlt"}
    try:
        baum = lies_baum(pfad)
    except (SyntaxError, ValueError, OSError) as fehler:
        return {"nicht_erhoben": grund(fehler)}
    datei = Datei(baum)
    zeilen = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.JoinedStr):
            text = "".join(
                str(teil.value)
                if isinstance(teil, ast.Constant)
                else "{" + ast.unparse(teil.value) + "}"
                for teil in knoten.values
            )
        elif isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
            if isinstance(datei.eltern.get(knoten), ast.JoinedStr):
                continue
            text = knoten.value
        else:
            continue
        if datei.klasse(knoten) != "kandidat":
            continue
        if any(
            "pip install" in zeile and not ZIELUMGEBUNG.search(zeile)
            for zeile in text.splitlines()
        ):
            zeilen.add(knoten.lineno)
    return {"blankes_pip_install": bool(zeilen), "zeilen": sorted(zeilen)}


def claude_md(repo: Path) -> dict:
    pfad = repo / "CLAUDE.md"
    if not pfad.is_file():
        return {"nicht_erhoben": "CLAUDE.md fehlt"}
    roh = pfad.read_bytes()
    ergebnis: dict = {"zeilen": len(roh.splitlines()), "teil_1_sha256": None}
    anfang = re.search(rb"^#+[ \t]+Teil 1\b", roh, re.MULTILINE)
    if anfang is None:
        return ergebnis | {"nicht_erhoben": "keine Überschrift «Teil 1»"}
    ende = re.compile(rb"^#+[ \t]+Teil 2\b", re.MULTILINE).search(roh, anfang.end())
    if ende is None:
        return ergebnis | {"nicht_erhoben": "keine Überschrift «Teil 2» danach"}
    teil = roh[anfang.start() : ende.start()]
    return ergebnis | {"teil_1_sha256": hashlib.sha256(teil).hexdigest()}


# --- git und Lauf -----------------------------------------------------------


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes] | None:
    """Nur lesend. Ohne eigenes `.git` fände git das Repo darüber."""
    if not (repo / ".git").exists():
        return None
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    # `--no-optional-locks`: `git status` schriebe sonst den Index neu.
    befehl = ["git", "--no-optional-locks", "-C", str(repo), *args]
    return subprocess.run(befehl, env=env, capture_output=True)


def commit(repo: Path) -> str | None:
    lauf = git(repo, "rev-parse", "HEAD")
    if lauf is None or lauf.returncode != 0:
        return None
    return lauf.stdout.decode().strip()


def abweichungen(repo: Path) -> int | None:
    """Wie viele Pfade vom Commit abweichen. Nur bei 0 steht er für den Befund."""
    lauf = git(repo, "status", "--porcelain")
    if lauf is None or lauf.returncode != 0:
        return None
    return len(lauf.stdout.splitlines())


def deckt_pycache(repo: Path) -> bool | None:
    """Gilt für das Repo selbst, nicht für die Konfiguration des Rechners."""
    probe = "scripts/__pycache__/x.cpython-311.pyc"
    lauf = git(repo, "check-ignore", "-v", "--no-index", probe)
    if lauf is None or lauf.returncode > 1:
        return None
    # `<quelle>:<zeile>:<muster>\t<pfad>`; ein `!` hebt das Ignorieren auf.
    muster = re.match(r"(.*?):\d+:(.*)\t", lauf.stdout.decode("utf-8", "replace"))
    if muster is None:
        return False
    quelle, regel = muster.groups()
    return posixpath.basename(quelle) == ".gitignore" and not regel.startswith("!")


def letzte_zeile(text: str) -> str:
    zeilen = [z for z in text.splitlines() if z.strip()]
    return zeilen[-1].strip()[:200] if zeilen else ""


def fahre(repo: Path, gate: str, schranke: float) -> dict:
    # os.environ kopieren statt neu bauen: Ohne SYSTEMROOT scheitert unter
    # Windows schon der Subprozess und nicht das Gate.
    env = {
        **os.environ,
        "PYTHONIOENCODING": "cp1252",
        "PYTHONUTF8": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        lauf = subprocess.run(
            [sys.executable, gate],
            cwd=repo,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=schranke,
        )
    except subprocess.TimeoutExpired:
        return {"exit": None, "nicht_erhoben": f"Zeitschranke von {schranke:g} s"}
    stderr = lauf.stderr.decode("cp1252", "replace")
    return {
        "exit": lauf.returncode,
        "unicode_encode_error": "UnicodeEncodeError" in stderr,
        "stderr_letzte_zeile": letzte_zeile(stderr),
    }


def ruff_version(befehl: list[str]) -> str | None:
    try:
        lauf = subprocess.run([*befehl, "--version"], capture_output=True)
    except OSError:
        return None
    return lauf.stdout.decode().strip() if lauf.returncode == 0 else None


def laufumgebung() -> dict:
    """Gegen welches ruff `check_ruff_pin.py` gemessen hat."""
    im_path = shutil.which("ruff")
    return {
        "python": sys.version.split()[0],
        "ruff_im_path": ruff_version([im_path]) if im_path else None,
        "ruff_als_modul": ruff_version([sys.executable, "-m", "ruff"]),
    }


# --- Repo und Einstieg ------------------------------------------------------


def untersuche_repo(repo: Path, schranke: float | None) -> dict:
    pipeline = Pipeline(repo)
    nicht_erhoben = dict(pipeline.nicht_erhoben)
    skripte = {}
    for pfad in sorted((repo / "scripts").rglob("*.py")):
        name = pfad.relative_to(repo).as_posix()
        skripte[name] = pipeline.einordnung(name) | untersuche_skript(pfad)

    ergebnis: dict = {
        "commit": commit(repo),
        "abweichungen_vom_commit": abweichungen(repo),
        "skripte": skripte,
    }
    try:
        pyproject = lies_toml(repo / "pyproject.toml")
        ergebnis["ruff_pins"] = ruff_pins(repo, pyproject, pipeline)
        ergebnis["ruff_format"] = ruff_format(repo, pyproject)
    except (OSError, ValueError) as fehler:
        nicht_erhoben["ruff"] = grund(fehler)
    ergebnis["rat"] = rat(repo)
    gates_test = repo / "tests" / "test_gates_cp1252.py"
    ergebnis["test_gates_cp1252"] = gates_test.is_file()
    ergebnis["gitignore_deckt_pycache"] = deckt_pycache(repo)
    ergebnis["claude_md"] = claude_md(repo)
    ergebnis["nicht_erhoben"] = nicht_erhoben
    if schranke is not None:
        vorhanden = [g for g in LAUF_GATES if (repo / g).is_file()]
        ergebnis["lauf"] = {g: fahre(repo, g, schranke) for g in vorhanden}
    return ergebnis


def untersuche(wurzel: Path, schranke: float | None) -> dict:
    repos = sorted(p for p in wurzel.iterdir() if p.is_dir() and p.name[0] != ".")
    ergebnis: dict = {"hinweis": HINWEIS}
    if schranke is not None:
        ergebnis["laufumgebung"] = laufumgebung()
    ergebnis["repos"] = {r.name: untersuche_repo(r, schranke) for r in repos}
    return ergebnis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Portfolio-Sweep zu OPS-005 Modus 5")
    parser.add_argument("wurzel", type=Path, help="ein Unterverzeichnis je Repo")
    parser.add_argument(
        "--lauf",
        action="store_true",
        help="check_version_sync.py und check_ruff_pin.py unter cp1252 fahren",
    )
    parser.add_argument(
        "--zeitschranke", type=float, default=60, help="Sekunden je Gate (60)"
    )
    args = parser.parse_args(argv)
    schranke = args.zeitschranke if args.lauf else None
    ergebnis = alles_lesbar(untersuche(args.wurzel, schranke))
    # ensure_ascii, damit die Ausgabe an keiner Kodierung bricht. Was ausserhalb
    # von cp1252 liegt, steht zu diesem Zeitpunkt bereits als U+XXXX da.
    print(json.dumps(ergebnis, indent=1, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
