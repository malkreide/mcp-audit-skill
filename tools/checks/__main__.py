"""Der Treiber: fährt die Prüfungen und fasst zusammen.

Die Ausgabe hat absichtlich dieselbe Form wie vorher, als die Prüfungen noch
in `scripts/validate.sh` standen — wer sie kennt, muss nichts neu lernen.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._core import Check, all_checks, run_all

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m tools.checks",
        description="Alle Gates dieses Repositories in einem Kommando.",
    )
    parser.add_argument(
        "numbers",
        nargs="*",
        type=int,
        help="nur diese Prüfungen fahren (Standard: alle)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Wurzel des zu prüfenden Baums (Standard: dieses Repository)",
    )
    parser.add_argument(
        "--include-network",
        action="store_true",
        help=(
            "auch die Prüfungen fahren, die Netz oder Token brauchen; "
            "die CI tut das, der lokale Runner nicht"
        ),
    )
    return parser.parse_args(argv)


def select(numbers: list[int], *, include_network: bool) -> list[Check]:
    available = all_checks(offline_only=not include_network)
    if not numbers:
        return available
    by_number = {check.number: check for check in available}
    unknown = [n for n in numbers if n not in by_number]
    if unknown:
        known = ", ".join(str(c.number) for c in all_checks())
        raise SystemExit(f"unbekannte Prüfung(en): {unknown} — es gibt {known}")
    return [by_number[n] for n in numbers]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    checks = select(args.numbers, include_network=args.include_network)

    print("validate — mcp-data-source-probe-skill")
    print(f"  repo:   {root}")
    print(f"  python: Python {sys.version.split()[0]}")
    print()

    results = run_all(root, checks)
    for result in results:
        status = "ok   " if result.ok else "FAIL "
        print(f"  {status} {result.check.number:<2} {result.check.label}")
        if result.output:
            for line in result.output.splitlines():
                print(f"          {line}")

    failed = [r for r in results if not r.ok]
    noun = "check" if len(results) == 1 else "checks"
    print()
    if not failed:
        print(f"{len(results)} {noun}, all passed")
        return 0
    print(f"{len(results)} {noun}, {len(failed)} failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
