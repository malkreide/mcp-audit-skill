"""Der Treiber: faehrt die Pruefungen aller Suiten und fasst zusammen.

Die Ausgabe hat absichtlich dieselbe Form wie die vier Runner, die hier
zusammenlaufen — wer sie kennt, muss nichts neu lernen. Neu ist nur die
Suite vor der Nummer.

Auswahl:

    python -m tools.harness                    # alles
    python -m tools.harness --suite audit      # eine Suite
    python -m tools.harness audit/1 probe/16   # einzelne Pruefungen
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ._core import Check, all_checks, python_version, run_all, suites

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m tools.harness",
        description="Alle Gates dieses Repositories in einem Kommando.",
    )
    parser.add_argument(
        "ids",
        nargs="*",
        help="nur diese Pruefungen fahren, als «suite/nummer» (Standard: alle)",
    )
    parser.add_argument(
        "--suite",
        help="nur die Pruefungen dieser Suite fahren",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Wurzel des zu pruefenden Baums (Standard: dieses Repository)",
    )
    # `--include-context-bound` ist der Name, unter dem mcp-data-fidelity-skill
    # dieselbe Sache fuehrte. Beide Schreibweisen bleiben gueltig: Die
    # dokumentierten Aufrufe der Herkunftsrepos sollen weiter funktionieren,
    # sonst verlagert die Zusammenfuehrung ihre Kosten nur in fremde READMEs.
    parser.add_argument(
        "--include-network",
        "--include-context-bound",
        dest="include_network",
        action="store_true",
        help=(
            "auch die Pruefungen fahren, die Netz, Token oder einen "
            "Tag-Kontext brauchen; die CI tut das dort, wo der Kontext "
            "existiert, der lokale Runner nicht"
        ),
    )
    return parser.parse_args(argv)


def select(
    ids: list[str],
    *,
    suite: str | None = None,
    include_network: bool = False,
) -> list[Check]:
    """Uebersetzt die Kommandozeile in eine Liste von Pruefungen.

    Ein unbekanntes Kuerzel ist ein Abbruch mit Aufzaehlung, kein leerer Lauf:
    «nichts gefahren» und «alles bestanden» sehen am Ende sonst gleich aus.
    """
    available = all_checks(suite=suite, offline_only=not include_network)
    if suite is not None and not all_checks(suite=suite):
        bekannt = ", ".join(suites()) or "keine"
        raise SystemExit(f"unbekannte Suite: {suite!r} — es gibt {bekannt}")
    if not ids:
        return available
    by_id = {c.id: c for c in available}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        known = ", ".join(sorted(by_id))
        raise SystemExit(f"unbekannte Pruefung(en): {unknown} — es gibt {known}")
    return [by_id[i] for i in ids]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    checks = select(args.ids, suite=args.suite, include_network=args.include_network)

    print("validate — mcp-audit")
    print(f"  repo:   {root}")
    print(f"  suiten: {', '.join(suites()) or 'keine'}")
    print(f"  python: Python {python_version()}")
    print()

    # Ein leerer Lauf ist ROT, nicht gruen. «0 checks, all passed» ist die
    # Meldung, die eine leere Registry von einem bestandenen Lauf nicht mehr
    # unterscheidbar macht — und eine leere Registry ist genau der Fehler,
    # gegen den die Importzeilen-Pruefung der Suiten gerichtet ist.
    if not checks:
        print("keine Pruefung ausgewaehlt — das ist ein Befund, kein Erfolg.")
        return 1

    results = run_all(root, checks)
    for result in results:
        status = "ok   " if result.ok else "FAIL "
        print(f"  {status} {result.check.id:<12} {result.check.label}")
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
