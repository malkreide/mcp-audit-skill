"""FID-006 sharp portfolio run: response shape and field names, from the parse
boundary outward, across function boundaries.

Three corrections got made along the way, and each one moved the numbers:

1. A line-level grep put a dozen repos on the read-list for
   `scripts/check_version_sync.py` reading a lockfile. Repo tooling is not a
   server reading its source. Scoped out — but only at the repo root, because
   `src/<pkg>/tools/` is where an MCP server keeps the code that *does* read
   responses, and excluding it everywhere hid nine repos entirely.

2. Argument validation counted as a confirmed root path.
   `if not search_term.strip(): raise` says nothing about the shape that
   arrived. A guard now only counts if its test mentions the parsed value or is
   a membership test on a string literal.

3. Intra-function taint saw `sites=1, keys=0` in nineteen repos: the dominant
   shape here is a `_get_json()` helper that returns `resp.json()` while the
   callers read the fields. Measuring only inside the parsing function measures
   the helper, which reads nothing at all, and reports the portfolio as having
   no field reads. Propagation to a fixpoint fixes it.

A fourth limitation showed up only when the sweep was re-run after the CKAN
repair, and it is the one to know before trusting a second reading: this script
**cannot see a confirmation that lives in a helper**. Taint starts at the parse
call, and a helper like `_ckan_result(payload, action)` receives the response as
a *parameter* — so a repo that moved its root-path check into exactly such a
helper still reports zero guards. After seven servers were repaired this way,
the run reported the guard count unchanged at 13. Those numbers were hand-
counted instead; do not read a flat `A_guarded` as "nothing improved".

Still a read-list, not a verdict. Every classification is re-read by hand.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])

SKIP_ANYWHERE = {".venv", "venv", "node_modules", "build", "dist", ".git", "tests"}
SKIP_AT_ROOT = {"scripts", "tools", "docs", "examples", "benchmarks"}


def in_scope(path: Path, repo: Path) -> bool:
    rel = path.relative_to(repo).parts
    if SKIP_ANYWHERE & set(rel):
        return False
    return not (len(rel) > 1 and rel[0] in SKIP_AT_ROOT)


def called_name(node: ast.Call) -> str | None:
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def direct_parse_kind(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    name = called_name(node)
    if name == "json" and not node.args:
        return "json"
    if name == "loads":
        return "json"
    if name in {"DictReader", "reader", "read_csv"}:
        return "csv"
    return None


def functions(tree: ast.Module) -> list[ast.AST]:
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def parse_kind(node: ast.AST, parse_fns: dict[str, str]) -> str | None:
    if (kind := direct_parse_kind(node)) is not None:
        return kind
    if isinstance(node, ast.Call):
        name = called_name(node)
        if name and name in parse_fns:
            return parse_fns[name]
    return None


def taint(fn: ast.AST, parse_fns: dict[str, str]) -> dict[str, str]:
    """Names holding parsed response data, propagated to a fixpoint."""
    tainted: dict[str, str] = {}
    for node in ast.walk(fn):
        value = None
        targets: list[str] = []
        if isinstance(node, ast.Assign):
            value = node.value
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and node.value:
            value = node.value
            if isinstance(node.target, ast.Name):
                targets = [node.target.id]
        if value is None:
            continue
        for sub in ast.walk(value):
            if (kind := parse_kind(sub, parse_fns)) is not None:
                for t in targets:
                    tainted[t] = kind
                break

    for _ in range(5):
        grew = False
        for node in ast.walk(fn):
            src: set[str] = set()
            targets = []
            if isinstance(node, ast.Assign):
                src = {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)}
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.For | ast.comprehension):
                src = {n.id for n in ast.walk(node.iter) if isinstance(n, ast.Name)}
                if isinstance(node.target, ast.Name):
                    targets = [node.target.id]
            hit = src & set(tainted)
            if hit:
                kind = tainted[next(iter(hit))]
                for t in targets:
                    if t not in tainted:
                        tainted[t] = kind
                        grew = True
        if not grew:
            break
    return tainted


def returns_parsed(fn: ast.AST, parse_fns: dict[str, str]) -> str | None:
    """Does this function hand parsed response data back to its caller?"""
    tainted = taint(fn, parse_fns)
    for node in ast.walk(fn):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        for sub in ast.walk(node.value):
            if (kind := parse_kind(sub, parse_fns)) is not None:
                return kind
            if isinstance(sub, ast.Name) and sub.id in tainted:
                return tainted[sub.id]
    return None


def guards(fn: ast.AST, tainted: dict[str, str]) -> list[str]:
    """Raises under a test about the parsed value, not about the arguments."""
    found = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        if not any(isinstance(n, ast.Raise) for n in ast.walk(node)):
            continue
        names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
        literal_membership = any(
            isinstance(c, ast.Compare)
            and any(isinstance(o, ast.In | ast.NotIn) for o in c.ops)
            and isinstance(c.left, ast.Constant)
            and isinstance(c.left.value, str)
            for c in ast.walk(node.test)
        )
        if names & set(tainted) or literal_membership:
            found.append(ast.unparse(node.test)[:90])
    return found


def normalises(fn: ast.AST) -> bool:
    for node in ast.walk(fn):
        if isinstance(node, ast.DictComp):
            key = ast.unparse(node.key)
            if ".lower()" in key or ".casefold()" in key:
                return True
        if isinstance(node, ast.Call):
            name = called_name(node) or ""
            if "normalise_key" in name or "normalize_key" in name:
                return True
    return False


def field_reads(fn: ast.AST, tainted: dict[str, str]) -> tuple[list[str], list[str]]:
    keys: list[str] = []
    defaulted: list[str] = []
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id in tainted
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            keys.append(node.slice.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "get" or not node.args:
                continue
            recv = node.func.value
            if not (isinstance(recv, ast.Name) and recv.id in tainted):
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                keys.append(first.value)
                if len(node.args) > 1:
                    defaulted.append(
                        f"{first.value} -> {ast.unparse(node.args[1])[:24]}"
                    )
    return keys, defaulted


def analyse(repo: Path) -> dict:
    trees: list[tuple[Path, ast.Module]] = []
    for path in repo.rglob("*.py"):
        if not in_scope(path, repo) or path.name.startswith("test_"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            trees.append((path.relative_to(repo), ast.parse(text)))
        except (SyntaxError, OSError):
            continue

    # Fixpoint over "which functions hand parsed data to their callers".
    parse_fns: dict[str, str] = {}
    for _ in range(6):
        grew = False
        for _rel, tree in trees:
            for fn in functions(tree):
                if fn.name in parse_fns:
                    continue
                if (kind := returns_parsed(fn, parse_fns)) is not None:
                    parse_fns[fn.name] = kind
                    grew = True
        if not grew:
            break

    sites = guarded = unguarded = normalised = n_defaults = 0
    keys_all: set[str] = set()
    mixed: set[str] = set()
    kinds: set[str] = set()
    w_guard: list[str] = []
    w_default: list[str] = []
    w_mixed: list[str] = []

    for rel, tree in trees:
        for fn in functions(tree):
            tainted = taint(fn, parse_fns)
            if not tainted:
                continue
            sites += 1
            kinds |= set(tainted.values())
            ks, defaulted = field_reads(fn, tainted)
            gs = guards(fn, tainted)
            if normalises(fn):
                normalised += 1
            if gs:
                guarded += 1
                if len(w_guard) < 5:
                    w_guard.append(f"{rel}:{fn.lineno} {fn.name}: if {gs[0]}")
            elif ks or defaulted:
                unguarded += 1
            for k in ks:
                keys_all.add(k)
                if any(c.isupper() for c in k):
                    mixed.add(k)
                    if len(w_mixed) < 8:
                        w_mixed.append(f"{rel}:{fn.lineno} {fn.name}: [{k!r}]")
            n_defaults += len(defaulted)
            for dflt in defaulted:
                if len(w_default) < 8:
                    w_default.append(f"{rel}:{fn.lineno} {fn.name}: .get({dflt})")

    return {
        "parse_returning_fns": sorted(parse_fns),
        "consuming_fns": sites,
        "kinds": sorted(kinds),
        "A_guarded": guarded,
        "A_unguarded": unguarded,
        "A_guard_where": w_guard,
        "A_defaults": n_defaults,
        "A_default_where": w_default,
        "B_key_count": len(keys_all),
        "B_keys": sorted(keys_all)[:40],
        "B_mixed_case": sorted(mixed),
        "B_mixed_where": w_mixed,
        "B_normalised_fns": normalised,
    }


def main() -> None:
    out = {r.name: analyse(r) for r in sorted(p for p in ROOT.iterdir() if p.is_dir())}
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
