"""Die Vorlagen müssen halten, was `reference/adoption.toml` über sie behauptet.

SKILL-EIGEN und deshalb hier: Nur dieser Skill führt ein Adoption-Manifest.
Die Pfade im Manifest bleiben `reference/…` — sie beschreiben den Skill und
nicht das Repository; aufgelöst werden sie gegen `BASE`.

Das Manifest deklariert je Vorlage eine Handvoll Eigenschaften — «liest
`Retry-After`», «streut den Backoff», «wirft kein nacktes `RuntimeError`». Bis
1.8.0 prüfte diese Liste ausschliesslich `reference_drift_probe.py` in
`mcp-continuous-auditor`, also ein anderes Repository, gegen die *Server*. Für
die Vorlage selbst nahm sie niemand in die Hand.

Das ist genau die Lücke, durch die der Defekt kam. `reference/retry_backoff.py`
verletzte fünf der sieben Eigenschaften, die einen Halbmeter weiter über sie
deklariert waren, und wurde in dem Zustand in elf Server kopiert. Kein Schritt
wurde rot, weil kein Schritt hinsah: Die Datei kompilierte (heute `audit/10`),
importierte (`probe/3`) und bestand beide Ruff-Gates. Alle vier haben recht — sie
prüfen die Form, und die war in Ordnung. Beanstandet wurde die Zusage von
niemandem.

Diese Prüfung schliesst das, und zwar lokal und offline: Manifest und Vorlagen
liegen beide in diesem Baum, es braucht weder Netz noch die Server. Was sie
NICHT kann, ist die andere Richtung — ob ein Server die Vorlage korrekt
übernommen hat, sagt weiter nur der Auditor. Sie prüft die Seite, die hier
liegt, und das ist die Seite, die kopiert wird.

DIE EIGENSCHAFTSWERTE STEHEN NUR IM MANIFEST. `any_of`, `outer`, `inner` und
`expect` werden gelesen, nicht nachgebaut. Eine zweite Kopie der Liste hier
driftete von der ersten weg, und eine gedriftete Prüfung, die grün meldet, ist
schlimmer als keine — dieselbe Begründung, aus der `scripts/validate.sh` die
Gates nicht ein zweites Mal hinschreibt.

`wraps` AKZEPTIERT BEIDE FORMEN, und das ist gemessen, nicht grosszügig. Am
2026-08-07 gegen die siebzehn Server gelesen: Alle sechs Server, die den Deckel
nach dem Jitter anwenden, binden erst einen Namen (`jittered = …`) und decken
dann (`min(jittered, MAX)`). Eine rein lexikalische Lesart — steht der
`random.*`-Aufruf in den Argumenten von `min`? — fällt bei 6 von 6 Servern
durch, die genau das Verhalten haben, das die Eigenschaft beschreibt. Die
Vorlage schreibt es andersherum und bestünde nur die lexikalische. Kein
einziger Ausdruck erfüllt beide, denn die Wahl *ist*, ob ein Name gebunden
wird. Wer nur eine Form akzeptiert, misst eine Schreibgewohnheit statt der
Reihenfolge, für die die Eigenschaft existiert.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

from tools.harness import CheckFailed, register

from ._suite import SUITE
from .skill_doc import BASE

#: BASE-relativ statt repo-relativ, und das ist der einzige inhaltliche
#: Unterschied zur Herkunftsfassung. Das Manifest fuehrt seine Pfade als
#: `reference/…` — sie beschreiben den SKILL, nicht das Repository, und
#: bleiben deshalb unveraendert. Aufgeloest werden sie gegen `BASE`.
MANIFEST = f"{BASE}/reference/adoption.toml"
REFERENCE_DIR = f"{BASE}/reference"

# Wie tief Helfer verfolgt werden, die das deklarierte Symbol aufruft. Die
# Vorlage legt `parse_retry_after` und `compute_delay` neben die Retry-Schleife,
# und das Manifest sagt ausdrücklich, dass Umbenennen und Umbauen eine korrekte
# Übernahme ist — eine Prüfung, die nur in den Rumpf des einen Symbols sieht,
# beanstandete jede Vorlage, die ihre Teile benennt.
HELPER_DEPTH = 3


def _dotted(node: ast.expr) -> str:
    """Voller punktierter Name einer Attribut-Kette, oder ''."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _functions(tree: ast.Module) -> dict[str, ast.AST]:
    out: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            out.setdefault(node.name, node)
    return out


def _scope(tree: ast.Module, symbol: str, where: str) -> list[ast.AST]:
    """Die AST-Knoten, in denen eine Eigenschaft gelten muss.

    Ohne `symbol` das ganze Modul — `response_envelope.py` deklariert seine
    Zusage bewusst auf Modulebene, nicht in einer Klasse. Mit `symbol` das
    Symbol plus die Modulfunktionen, die es aufruft.
    """
    if not symbol:
        return [tree]

    funcs = _functions(tree)
    entry = funcs.get(symbol.split(".")[-1])
    if entry is None:
        raise CheckFailed(
            f"{MANIFEST}: {where} deklariert das Symbol {symbol!r}, aber "
            f"es gibt keine Funktion dieses Namens.\n"
            "  Die Zuordnung zeigt ins Leere: Jede Eigenschaft darauf würde "
            "einen leeren Rumpf befragen und, je nach `expect`, grundlos "
            "bestehen oder grundlos fallen.\n"
            f"  vorhanden: {sorted(funcs) or '— keine Funktion in der Datei'}"
        )

    seen, stack, out = {entry}, [entry], [entry]
    for _ in range(HELPER_DEPTH):
        nxt: list[ast.AST] = []
        for fn in stack:
            for node in ast.walk(fn):
                if not isinstance(node, ast.Call):
                    continue
                helper = funcs.get(_dotted(node.func).split(".")[-1])
                if helper is not None and helper not in seen:
                    seen.add(helper)
                    nxt.append(helper)
                    out.append(helper)
        stack = nxt
        if not stack:
            break
    return out


# --- Die Eigenschaftsarten -------------------------------------------------


def _calls(scope: list[ast.AST], names: set[str]) -> bool:
    return any(
        isinstance(node, ast.Call) and _dotted(node.func) in names
        for root in scope
        for node in ast.walk(root)
    )


def _literal(scope: list[ast.AST], needles: set[str]) -> bool:
    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.strip().lower() in needles
        for root in scope
        for node in ast.walk(root)
    )


def _raises(scope: list[ast.AST], names: set[str]) -> bool:
    short = {n.rsplit(".", 1)[-1] for n in names}
    for root in scope:
        for node in ast.walk(root):
            if isinstance(node, ast.Raise) and node.exc is not None:
                exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
                if _dotted(exc).rsplit(".", 1)[-1] in short:
                    return True
    return False


def _handles(scope: list[ast.AST], names: set[str]) -> bool:
    short = {n.rsplit(".", 1)[-1] for n in names}
    for root in scope:
        for node in ast.walk(root):
            if not isinstance(node, ast.ExceptHandler) or node.type is None:
                continue
            caught = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
            if any(_dotted(t).rsplit(".", 1)[-1] in short for t in caught):
                return True
    return False


def _wraps(scope: list[ast.AST], outer: str, inner: set[str]) -> bool:
    """Steht ein `inner`-Aufruf innerhalb der Argumente eines `outer`-Aufrufs?

    Beide Formen zählen — siehe die Modul-Kopfnotiz. Lexikalisch:
    `min(x * random.random(), MAX)`. Über einen gebundenen Namen:
    `jittered = x * random.random()` … `min(jittered, MAX)`.
    """
    for root in scope:
        bound = {
            target.id
            for node in ast.walk(root)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(s, ast.Call) and _dotted(s.func) in inner
                for s in ast.walk(node.value)
            )
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for node in ast.walk(root):
            if not isinstance(node, ast.Call) or _dotted(node.func) != outer:
                continue
            for arg in node.args:
                for sub in ast.walk(arg):
                    if isinstance(sub, ast.Call) and _dotted(sub.func) in inner:
                        return True
                    if isinstance(sub, ast.Name) and sub.id in bound:
                        return True
    return False


def _evaluate(prop: dict, scope: list[ast.AST], where: str) -> bool:
    kind = prop.get("kind")
    any_of = set(prop.get("any_of", []))
    if kind == "calls":
        return _calls(scope, any_of)
    if kind == "literal":
        return _literal(scope, {n.strip().lower() for n in any_of})
    if kind == "raises":
        return _raises(scope, any_of)
    if kind == "handles":
        return _handles(scope, any_of)
    if kind == "wraps":
        return _wraps(scope, prop.get("outer", ""), set(prop.get("inner", [])))
    raise CheckFailed(
        f"{MANIFEST}: {where} hat die Art {kind!r}, und diese Prüfung kennt "
        "sie nicht.\n"
        "  Ausdrücklich ein Befund und kein Überspringen: Eine unbekannte Art "
        "stillschweigend zu übergehen hiesse, dass eine neu deklarierte "
        "Eigenschaft ungeprüft bleibt, während der Lauf grün meldet.\n"
        "  Entweder die Art in tools/suites/mcp_data_source_probe/adoption.py "
        "ergaenzen, oder sie im "
        "Manifest auf eine der bekannten ziehen: calls, literal, raises, "
        "handles, wraps."
    )


# --- Die Prüfung -----------------------------------------------------------


def _load(root: Path) -> dict:
    path = root / MANIFEST
    if not path.is_file():
        raise CheckFailed(
            f"{MANIFEST} fehlt — Anker weg. Das Manifest ist die einzige "
            "Stelle, an der steht, was die Vorlagen zusichern; ohne es hätte "
            "diese Prüfung nichts zu prüfen und hätte genau deshalb Erfolg "
            "gemeldet."
        )
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise CheckFailed(f"{MANIFEST} parst nicht als TOML: {exc}") from exc


@register(17, "the templates hold what the adoption manifest claims", suite=SUITE)
def templates_hold_their_properties(root: Path) -> str:
    manifest = _load(root)
    templates = manifest.get("template", [])
    if not templates:
        raise CheckFailed(
            f"{MANIFEST} enthält kein [[template]] — die Prüfung hätte nichts "
            "zu tun und hätte genau deshalb Erfolg gemeldet.\n"
            "  Eine Vorlage ohne deklarierte Eigenschaften sichert nichts zu, "
            "und dieses Repository liefert sie zum Kopieren aus."
        )

    findings: list[str] = []
    lines: list[str] = []
    checked = 0
    mapped: set[str] = set()

    for template in templates:
        rel = template.get("file", "")
        symbol = template.get("symbol", "")
        where = f"[[template]] {rel or '(ohne file)'}"
        mapped.add(rel)

        path = root / BASE / rel
        if not rel or not path.is_file():
            raise CheckFailed(
                f"{MANIFEST}: {where} zeigt auf eine Datei, die es nicht "
                "gibt.\n"
                "  Die Zuordnung ist der ganze Zweck dieses Manifests. Zeigt "
                "sie ins Leere, prüft niemand mehr etwas — und nichts wird rot."
            )

        properties = template.get("property", [])
        if not properties:
            raise CheckFailed(
                f"{MANIFEST}: {where} deklariert keine Eigenschaft.\n"
                "  Ein Eintrag ohne Eigenschaften sichert nichts zu und lässt "
                "die Prüfung leer durchlaufen — sie meldete grün über eine "
                "Vorlage, die sie nie befragt hat."
            )

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            # Ein Befund, kein Absturz. Der Unterschied ist nicht Kosmetik:
            # Eine abstürzende Prüfung meldet «tools/checks ist kaputt» und
            # schickt den Lesenden in die falsche Datei — hier ist die Vorlage
            # kaputt, und `audit/10` sagt es genauer.
            raise CheckFailed(
                f"{rel}: Syntaxfehler in Zeile {exc.lineno} — {exc.msg}.\n"
                "  Ohne lesbaren Quelltext lässt sich keine Eigenschaft "
                "messen. `audit/10` meldet dasselbe und ist die Stelle, an "
                "der das zu reparieren ist."
            ) from exc
        scope = _scope(tree, symbol, where)

        for prop in properties:
            pid = prop.get("id", "(ohne id)")
            expect = prop.get("expect")
            if expect not in ("present", "absent"):
                raise CheckFailed(
                    f"{MANIFEST}: {where} / {pid} hat expect={expect!r}. "
                    "Erlaubt sind 'present' und 'absent' — alles andere liesse "
                    "offen, wogegen verglichen wird."
                )
            checked += 1
            found = _evaluate(prop, scope, f"{where} / {pid}")
            if found != (expect == "present"):
                findings.append(
                    f"  {rel}: {pid} — erwartet {expect}, gemessen "
                    f"{'present' if found else 'absent'}\n"
                    f"      «{prop.get('says', '')}»"
                )

        lines.append(
            f"{rel}"
            f"{f' ({symbol})' if symbol else ' (ganzes Modul)'}: "
            f"{len(properties)} Eigenschaft(en) erfüllt"
        )

    # Eine neue Vorlage, die niemand zugeordnet hat, ist eine ungeprüfte
    # Vorlage. Sie fiele sonst durch jede Masche: kompiliert, importiert,
    # lintet — und sichert nichts zu.
    unmapped = sorted(
        f"reference/{p.name}"
        for p in sorted((root / REFERENCE_DIR).glob("*.py"))
        if f"reference/{p.name}" not in mapped
        and f"reference/{p.name}" not in manifest.get("unmapped_ok", [])
    )
    if unmapped:
        raise CheckFailed(
            f"{MANIFEST}: Vorlage(n) ohne [[template]]-Eintrag: {unmapped}.\n"
            "  Sie werden kopiert wie die anderen und sichern nichts zu. "
            "Entweder Eigenschaften deklarieren, oder bewusst in `unmapped_ok` "
            "aufnehmen — dann steht die Entscheidung wenigstens da."
        )

    if findings:
        raise CheckFailed(
            "Vorlage(n) halten nicht, was das Manifest über sie behauptet:\n"
            + "\n".join(findings)
            + "\n\n  Das ist der Fall, der diese Prüfung veranlasst hat: "
            "`reference/retry_backoff.py` verletzte fünf hier deklarierte "
            "Eigenschaften und wurde so in elf Server kopiert.\n"
            "  Die Vorlage reparieren, nicht die Eigenschaft streichen."
        )

    lines.append(
        f"{len(templates)} Vorlage(n), {checked} deklarierte Eigenschaft(en) "
        "gegen den Quelltext gehalten"
    )
    return "\n".join(lines)
