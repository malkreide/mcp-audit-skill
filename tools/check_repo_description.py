#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hält die GitHub-Repo-Description am Katalog fest.

Die Zahlen des Katalogs stehen an sechs Orten, und fünf davon sichert die
Testsuite: `checks/MANIFEST.txt`, `README.md`, `SKILL.md`, die `Stand:`-Zeile
in `docs/roadmap.md` und die Kategorienliste im Slash-Command. Der sechste
liegt **ausserhalb des Repos** — die Repository-Description auf GitHub — und
war deshalb bis hierher unerreichbar für jeden Test.

Sie ist prompt gedriftet: Während der Katalog von 68 über 78 auf 85 Checks in
elf Kategorien wuchs, stand in der Description unverändert
«68 Checks · 8 Kategorien». Kein Fehler mit Folgen für ein Audit, aber die
erste Zeile, die jemand liest, der das Repo findet — und ein Wert, den nichts
erzwingt, driftet. Das ist dieselbe Regel, aus der `IDENT-004` entstand
(README-Badges), nur eine Ebene ausserhalb der Arbeitskopie.

Die Description ist über die API **lesbar**, also auch prüfbar. Schreiben kann
dieses Skript sie nicht und soll es nicht: Repo-Metadaten zu ändern ist ein
Eingriff, der einer Person gehört. Der Guard benennt die Abweichung und gibt
den fertigen Text aus.

ZWEI ENTSCHEIDUNGEN, DIE NICHT VERHANDELBAR SIND
------------------------------------------------
1. **Eine nicht erreichbare API ist kein Bestehen.** Ohne Antwort hat der
   Vergleich nicht stattgefunden; dann meldet der Guard `UNKNOWN` und endet
   mit 1, statt aus dem lokalen Katalog allein «stimmt» zu drucken. Grün aus
   der halben Evidenz zu melden wäre genau der Fehler, den `DRIFT-003` im
   Katalog beschreibt.

2. **Der Vergleich ist eine reine Funktion.** `compare()` nimmt den
   Description-String entgegen und ist ohne Netz testbar. Ein Test, der die
   API mocken müsste, würde die eigene Annahme über deren Antwort abbilden —
   die Grenze, an der `DRIFT-004` ansetzt. Netz braucht nur `fetch()`, und das
   ist absichtlich die dünnste Funktion der Datei.

Geprüft werden ausschliesslich die Zahlen, nicht die Formulierung: «85 Checks»
und «11 Kategorien». Der beschreibende Teil gehört der Autorin.

Exit-Codes:
  0  Description stimmt mit dem Katalog überein
  1  Abweichung, oder die Description konnte nicht geholt werden
  2  Aufruffehler (Katalog nicht lesbar, Repo-Angabe fehlt)

Aufruf:
    python tools/check_repo_description.py --repo malkreide/mcp-audit-skill
    python tools/check_repo_description.py --repo <o/r> --format json
    python tools/check_repo_description.py --description "…"   # ohne Netz
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.parse_catalog import category_counts, parse_catalog  # noqa: E402
from tools.path_utils import force_utf8_stdio  # noqa: E402

API = "https://api.github.com/repos/{repo}"

# «85 Checks», «11 Kategorien» — dieselbe Form wie die Prosa-Prüfung in
# tests/test_readme_counts.py, damit beide dasselbe verlangen.
CHECKS = re.compile(r"(\d+)\s+Checks")
CATEGORIES = re.compile(r"(\d+)\s+Kategorien")


def _default_checks_dir() -> Path:
    return _REPO_ROOT / "checks"


def compare(description: str, n_checks: int, n_categories: int) -> list[str]:
    """Abweichungen zwischen Description und Katalog. Leer heisst: stimmt.

    Reine Funktion, absichtlich ohne Netz und ohne Dateizugriff — siehe
    Modul-Docstring, Punkt 2.
    """
    problems: list[str] = []

    found_checks = [int(n) for n in CHECKS.findall(description)]
    found_categories = [int(n) for n in CATEGORIES.findall(description)]

    if not found_checks:
        problems.append(
            f"Description nennt keine Check-Zahl — erwartet «{n_checks} Checks»"
        )
    for n in found_checks:
        if n != n_checks:
            problems.append(f"Description nennt {n} Checks, Katalog hat {n_checks}")

    if not found_categories:
        problems.append(
            f"Description nennt keine Kategorien-Zahl — erwartet «{n_categories} Kategorien»"
        )
    for n in found_categories:
        if n != n_categories:
            problems.append(
                f"Description nennt {n} Kategorien, Katalog hat {n_categories}"
            )

    return problems


def suggest(description: str, n_checks: int, n_categories: int) -> str:
    """Die Description mit korrigierten Zahlen — Formulierung unangetastet."""
    out = CHECKS.sub(f"{n_checks} Checks", description)
    return CATEGORIES.sub(f"{n_categories} Kategorien", out)


def fetch(repo: str, timeout: float = 15.0) -> tuple[str | None, str]:
    """(description, status). Wirft nie — der Aufrufer meldet den Status.

    Absichtlich die dünnste Funktion der Datei: alles, was hier passiert, ist
    für Tests unerreichbar, also soll hier so wenig wie möglich passieren.
    """
    req = urllib.request.Request(API.format(repo=repo))
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return None, f"GitHub antwortete HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"GitHub nicht erreichbar: {exc}"
    except (ValueError, KeyError) as exc:
        return None, f"Antwort nicht lesbar: {exc}"
    return payload.get("description") or "", "ok"


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="check_repo_description",
        description=(
            "Vergleicht die GitHub-Repo-Description mit dem Katalog. Der "
            "sechste Ort, an dem die Katalog-Zahlen stehen — und der einzige "
            "ausserhalb des Repos."
        ),
    )
    parser.add_argument("--repo", default=None, help="owner/name auf GitHub")
    parser.add_argument(
        "--description",
        default=None,
        help="Description direkt übergeben statt holen (für Tests und Trockenläufe)",
    )
    parser.add_argument("--checks-dir", default=str(_default_checks_dir()))
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    checks_dir = Path(args.checks_dir)
    if not checks_dir.is_dir():
        print(f"Fehler: {checks_dir} ist kein Verzeichnis", file=sys.stderr)
        return 2
    if args.repo is None and args.description is None:
        print("Fehler: --repo oder --description nötig", file=sys.stderr)
        return 2

    catalog = parse_catalog(checks_dir)
    n_checks = len(catalog)
    n_categories = len(category_counts(catalog))

    if args.description is not None:
        description, status = args.description, "ok"
    else:
        description, status = fetch(args.repo, args.timeout)

    result: dict[str, Any] = {
        "repo": args.repo,
        "status": status,
        "catalog_checks": n_checks,
        "catalog_categories": n_categories,
        "description": description,
        "problems": [],
        "suggestion": None,
        "ok": False,
    }

    if description is None:
        # Der Vergleich hat nicht stattgefunden — das ist kein Bestehen.
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"UNKNOWN  {status} — die Description wurde NICHT verglichen.")
        return 1

    problems = compare(description, n_checks, n_categories)
    result["problems"] = problems
    result["ok"] = not problems
    if problems:
        result["suggestion"] = suggest(description, n_checks, n_categories)

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if not problems:
            print(
                f"Description OK ({n_checks} Checks, {n_categories} Kategorien)"
            )
        else:
            for p in problems:
                print(f"DRIFT    {p}")
            print()
            print("Vorschlag (Formulierung unverändert, nur die Zahlen):")
            print(f"  {result['suggestion']}")
            print()
            print(
                f"Eintragen unter https://github.com/{args.repo}/settings — "
                "dieses Skript schreibt bewusst nicht."
            )

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
