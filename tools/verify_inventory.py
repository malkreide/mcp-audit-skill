#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prüft, ob `portfolio.yaml` jeden Server im Checkout tatsächlich kennt.

WARUM ES DAS GIBT
-----------------
`portfolio.yaml` ist handgepflegt, und `audit-portfolio.sh` arbeitet genau
diese Liste ab. Was nicht darin steht, wird nie auditiert — und es gibt
keine Rückmeldung darüber, denn ein nicht auditierter Server erzeugt keine
Zeile, keinen Fehler, keine Lücke im Report. Er ist schlicht nicht da.

Der reale Fall: `openparldata-mcp` liegt **verschachtelt** im Repo
`parlament-mcp`, mit eigener `pyproject.toml`. Jede Aufzählung, die
Top-Level-Repos listet, hat ihn übersprungen. Dadurch war er der letzte
Server im Portfolio auf dem alten SDK-Major, und unter dem neuen wäre er
auf HTTP-Transport gar nicht mehr gestartet. Gefunden wurde er zufällig
und spät.

Dieses Modul dreht die Beweislast um: Nicht die Liste behauptet, was es
gibt — der Checkout wird befragt, und **jedes** gefundene Server-Manifest
muss sich einem Listeneintrag zuordnen lassen oder ausdrücklich als
Nicht-Server deklariert sein. Ein Manifest, das keinem von beiden
entspricht, ist ein harter Fehler.

Damit ist die Fehlerklasse «ein Server, den niemand kennt» nicht mehr
davon abhängig, dass jemand daran denkt.

BITTE NICHT WEGRÄUMEN
---------------------
Dieses Gate hat keinen sichtbaren Nutzen, solange es grün ist — genau das
ist die Eigenschaft, die es beim nächsten Aufräumen gefährdet. Es schützt
gegen einen Fehler, der sich nicht meldet. Wenn es stört, gehört die
`ignore`-Liste gepflegt, nicht der Check entfernt.

ZUORDNUNG
---------
Ein gefundenes Manifest gilt als bekannt, wenn eines zutrifft:

1. Es liegt an der Wurzel des Checkouts eines gelisteten Servers.
2. Es liegt an einem Pfad, den ein Listeneintrag über `path:` benennt —
   so wird ein verschachtelter Server erfasst, ohne die Liste zu
   verbiegen (`openparldata-mcp` ist genau dieser Fall).
3. Es liegt unter einem Pfad, den `ignore:` deklariert — global oder pro
   Server.

VERZEICHNISSE, DIE OHNE DEKLARATION ÜBERSPRUNGEN WERDEN
-------------------------------------------------------
Nur solche, die per Konstruktion keinen von Hand geschriebenen,
versionierten Server enthalten: `.git`, virtuelle Umgebungen, installierte
Pakete, Caches, Build-Artefakte von Paketmanagern (siehe VENDOR_DIRS).

Alles andere — Test-Fixtures, Beispiel-Verzeichnisse,
Tooling-Unterprojekte — wird **nicht** geraten. Dafür ist `ignore:` da.
Eine Heuristik, die «examples/» für harmlos hält, hätte `openparldata-mcp`
genauso übersehen wie die Handliste; der Sinn dieses Gates ist, dass die
Entscheidung geschrieben dasteht statt vermutet zu werden.

Übersprungenes wird im Report aufgeführt. Ein still übergangenes
Verzeichnis wäre dieselbe Fehlerklasse in neuer Verpackung (vgl.
`OPS-005`: was nicht geprüft wurde, sieht aus wie bestanden).

Exit codes:
    0 — jedes gefundene Manifest ist zugeordnet
    1 — unbekanntes Manifest gefunden, oder ein Checkout fehlt
    2 — Bedienfehler (Datei nicht da, YAML kaputt)
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402


# Was einen Server ausmacht: ein Manifest, das ihn beschreibt.
MANIFEST_NAMES = ("pyproject.toml", "package.json")

# Verzeichnisse, die ohne Deklaration übersprungen werden. Bewusst kurz und
# bewusst nur solche, in denen kein von Hand geschriebener, versionierter
# Server liegen kann. Das ist keine Aussage darüber, was ein Server ist —
# es ist eine Aussage darüber, was Werkzeuge dort ablegen.
VENDOR_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "site-packages",
        ".eggs",
    }
)


def _is_vendor(rel: Path) -> bool:
    """True, wenn irgendein Pfadsegment ein Vendor-/Cache-Verzeichnis ist."""
    return any(part in VENDOR_DIRS or part.endswith(".egg-info") for part in rel.parts)


def find_manifests(checkout: Path) -> list[Path]:
    """Alle Server-Manifeste unterhalb von `checkout`, relativ, sortiert.

    Vendor-Verzeichnisse werden übersprungen; alles andere wird gemeldet
    und muss sich zuordnen lassen.
    """
    found: list[Path] = []
    for name in MANIFEST_NAMES:
        for path in checkout.rglob(name):
            if not path.is_file():
                continue
            rel = path.relative_to(checkout)
            if _is_vendor(rel.parent):
                continue
            found.append(rel)
    return sorted(found, key=lambda p: (str(p.parent), p.name))


def _norm(path_value: Any) -> str:
    """Ein `path:`-Feld auf die Form normalisieren, die rglob liefert."""
    text = str(path_value or ".").strip().strip("/")
    return text or "."


def _matches_ignore(rel_dir: str, patterns: list[str]) -> str | None:
    """Erstes `ignore`-Muster, das auf das Verzeichnis passt — oder None.

    Gematcht wird gegen das Verzeichnis des Manifests, nicht gegen die
    Datei: `ignore: ["tests/fixtures/*"]` soll das Manifest darin fangen,
    ohne dass jemand `pyproject.toml` ans Muster hängen muss.
    """
    for pattern in patterns:
        p = pattern.strip().strip("/")
        if not p:
            continue
        if rel_dir == p or fnmatch.fnmatch(rel_dir, p):
            return pattern
        # Präfix-Match: `ignore: ["examples"]` deckt `examples/foo` mit ab.
        if rel_dir.startswith(p + "/") or fnmatch.fnmatch(rel_dir, p + "/*"):
            return pattern
    return None


def verify_inventory(
    portfolio: dict[str, Any],
    work_dir: Path,
    skip_missing: bool = False,
) -> dict[str, Any]:
    """Vergleicht die Manifeste in jedem Checkout mit der Portfolio-Liste.

    Returns:
        {
          "consistent": bool,
          "servers": [{"name", "status", "checkout", "known", "ignored", "unlisted"}],
          "unlisted": [{"server", "path", "manifest"}],   # die harten Befunde
          "unverified": [name, ...],                      # Checkout fehlte
        }
    """
    entries = portfolio.get("servers") or []
    global_ignore = [str(p) for p in (portfolio.get("ignore") or [])]

    # Alle deklarierten Pfade pro Repo-URL sammeln: Ein verschachtelter
    # Server teilt sich die Repo-URL mit seinem Eltern-Eintrag, liegt aber
    # an einem anderen Pfad. Ohne diese Gruppierung wäre ein zweiter
    # Eintrag auf dasselbe Repo nicht zuzuordnen.
    paths_by_repo: dict[str, set[str]] = {}
    for entry in entries:
        repo = str(entry.get("repo") or "")
        paths_by_repo.setdefault(repo, set()).add(_norm(entry.get("path")))

    servers: list[dict[str, Any]] = []
    unlisted: list[dict[str, str]] = []
    unverified: list[str] = []

    for entry in entries:
        name = str(entry.get("name") or "<unnamed>")
        repo = str(entry.get("repo") or "")
        checkout = work_dir / name

        if not checkout.is_dir():
            # Nicht geprüft ist nicht bestanden. Der Checkout kann fehlen,
            # weil noch nicht geklont wurde — dann ist die Aussage dieses
            # Laufs für diesen Server schlicht keine.
            unverified.append(name)
            servers.append(
                {
                    "name": name,
                    "status": "unverified",
                    "checkout": str(checkout),
                    "known": [],
                    "ignored": [],
                    "unlisted": [],
                }
            )
            continue

        declared = paths_by_repo.get(repo, {"."})
        ignore_patterns = global_ignore + [str(p) for p in (entry.get("ignore") or [])]

        known: list[str] = []
        ignored: list[dict[str, str]] = []
        server_unlisted: list[str] = []

        for rel in find_manifests(checkout):
            rel_dir = str(rel.parent).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = "."

            if rel_dir in declared:
                known.append(str(rel).replace("\\", "/"))
                continue

            hit = _matches_ignore(rel_dir, ignore_patterns)
            if hit is not None:
                ignored.append({"path": str(rel).replace("\\", "/"), "pattern": hit})
                continue

            server_unlisted.append(str(rel).replace("\\", "/"))
            unlisted.append(
                {
                    "server": name,
                    "path": rel_dir,
                    "manifest": str(rel).replace("\\", "/"),
                }
            )

        servers.append(
            {
                "name": name,
                "status": "drift" if server_unlisted else "ok",
                "checkout": str(checkout),
                "known": known,
                "ignored": ignored,
                "unlisted": server_unlisted,
            }
        )

    consistent = not unlisted and (skip_missing or not unverified)
    return {
        "consistent": consistent,
        "servers": servers,
        "unlisted": unlisted,
        "unverified": unverified,
    }


def _load_portfolio(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        sys.exit(
            "PyYAML wird zum Lesen von portfolio.yaml gebraucht. "
            "Installation: pip install pyyaml"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _print_text(report: dict[str, Any]) -> None:
    for s in report["servers"]:
        if s["status"] == "unverified":
            mark = "?"
        elif s["status"] == "drift":
            mark = "✗"
        else:
            mark = "✓"
        detail = f"{len(s['known'])} bekannt"
        if s["ignored"]:
            detail += f", {len(s['ignored'])} ignoriert"
        if s["status"] == "unverified":
            detail = f"Checkout fehlt ({s['checkout']})"
        print(f"  {mark} {s['name']:<28} {detail}")

    if report["unlisted"]:
        print()
        print(
            "UNBEKANNTE SERVER-MANIFESTE — nicht in portfolio.yaml und nicht ignoriert:"
        )
        for u in report["unlisted"]:
            print(f"  {u['server']}: {u['manifest']}")
        print()
        print("Das ist der Fall, für den dieses Gate existiert (openparldata-mcp lag")
        print("verschachtelt in parlament-mcp und wurde nie auditiert). Entweder:")
        print("  • als eigenen Eintrag in portfolio.yaml aufnehmen, mit `path:` auf")
        print("    das Verzeichnis, oder")
        print("  • unter `ignore:` deklarieren, wenn es kein Server ist.")
        print("Bitte nicht das Gate lockern.")

    if report["unverified"]:
        print()
        print("NICHT GEPRÜFT — Checkout fehlt, das ist kein Bestehen:")
        for name in report["unverified"]:
            print(f"  {name}")
        print("Erst klonen (audit-portfolio.sh) oder --skip-missing setzen.")


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="verify_inventory",
        description=(
            "Prüft, ob jedes Server-Manifest im Checkout einem Eintrag in "
            "portfolio.yaml entspricht. Fängt verschachtelte Server, die "
            "durch handgepflegte Listen fallen."
        ),
    )
    parser.add_argument("--portfolio", default="portfolio.yaml")
    parser.add_argument(
        "--work-dir",
        default=None,
        help="Wo die Checkouts liegen. Default: $WORK_DIR oder ~/mcp-audit-runs",
    )
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Fehlende Checkouts nur melden statt scheitern (Teilläufe)",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    portfolio_path = Path(args.portfolio)
    if not portfolio_path.is_file():
        print(f"Error: {portfolio_path} nicht gefunden", file=sys.stderr)
        return 2

    if args.work_dir:
        work_dir = Path(args.work_dir)
    else:
        import os

        work_dir = Path(os.environ.get("WORK_DIR") or (Path.home() / "mcp-audit-runs"))

    try:
        portfolio = _load_portfolio(portfolio_path)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Error: {portfolio_path} nicht lesbar: {exc}", file=sys.stderr)
        return 2

    report = verify_inventory(portfolio, work_dir, skip_missing=args.skip_missing)

    if args.format == "json":
        text = json.dumps(report, indent=2, ensure_ascii=False)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
    else:
        print(f"Inventar-Abgleich gegen {portfolio_path} (Checkouts: {work_dir})")
        _print_text(report)
        if args.out:
            Path(args.out).write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    return 0 if report["consistent"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
