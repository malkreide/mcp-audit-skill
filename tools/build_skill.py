#!/usr/bin/env python3
"""Baut `mcp-audit.skill` — das Archiv, das man bei Claude hochlädt.

    python tools/build_skill.py          # baut ./mcp-audit.skill
    bash scripts/build-skill.sh          # dasselbe, mit Ausgabe fürs Auge

Das Ergebnis ist ein ZIP mit einem einzigen Wurzelverzeichnis `mcp-audit/`,
dessen Inhalt `skill-manifest.txt` bestimmt. Hochladen: claude.ai →
Settings → Capabilities → Skills → «Upload skill».

WARUM PYTHON UND NICHT `zip`. Die Testmatrix dieses Repos fährt
`windows-latest`, und `zip` ist dort nicht vorhanden. `scripts/build-skill.sh`
bleibt als Einstieg bestehen, ist aber — wie `scripts/validate.sh` — nur eine
dünne Hülle um den Aufruf hier. Eine Implementierung, zwei Einstiege.

WARUM DER BUILD BIT-IDENTISCH REPRODUZIERBAR IST. Jeder Eintrag bekommt
denselben Zeitstempel, dieselben Rechte und dieselbe Reihenfolge. Ohne das
unterschiede sich das Archiv bei jedem Lauf, und die Frage «passt das
eingecheckte `mcp-audit.skill` noch zu den Quellen?» wäre nicht mehr
entscheidbar — genau die Frage, die Check 5 beantwortet und die das
Release-Workflow vor dem Veröffentlichen stellt.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402
from tools.skill_package import (  # noqa: E402
    ARCHIVE_NAME,
    ManifestError,
    frontmatter_problems,
    member_name,
    package_files,
)

# 1980-01-01 00:00:00 — der früheste Zeitstempel, den das ZIP-Format kennt.
# Ein fester Wert statt der Datei-mtime: sonst hinge der Archivinhalt daran,
# wann jemand ausgecheckt hat.
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

# rw-r--r--, plus create_system=3 (Unix). Beides festgeschrieben, damit ein
# Build unter Windows dieselben Bytes liefert wie einer unter Linux.
FILE_MODE = 0o644
UNIX = 3


def build(root: Path, output: Path) -> list[str]:
    """Schreibt das Archiv und gibt die aufgenommenen Pfade zurück."""
    problems = frontmatter_problems((root / "SKILL.md").read_text(encoding="utf-8"))
    if problems:
        raise ManifestError("\n".join(problems))

    files = package_files(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Erst schreiben, dann ersetzen: Ein abgebrochener Lauf soll kein halbes
    # Archiv hinterlassen, das anschliessend als «gebaut» durchgeht.
    temporary = output.with_suffix(output.suffix + ".part")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in files:
            info = zipfile.ZipInfo(member_name(relative), date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = UNIX
            info.external_attr = FILE_MODE << 16
            archive.writestr(info, (root / relative).read_bytes())
    temporary.replace(output)
    return files


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="python tools/build_skill.py",
        description=f"Baut {ARCHIVE_NAME} aus den Quellen dieses Repositories.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_REPO_ROOT,
        help="Wurzel des zu packenden Baums (Standard: dieses Repository)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Zieldatei (Standard: <root>/{ARCHIVE_NAME})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="nur den Pfad des Archivs ausgeben",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    output = (args.output or root / ARCHIVE_NAME).resolve()

    try:
        files = build(root, output)
    except (ManifestError, OSError) as exc:
        print(f"Build abgebrochen: {exc}", file=sys.stderr)
        return 1

    if args.quiet:
        print(output)
        return 0

    size_bytes = output.stat().st_size
    print(f"gebaut: {output}")
    print(f"  Einträge: {len(files)}")
    print(f"  Größe:    {size_bytes / 1024:.0f} KiB")
    print()
    print("Hochladen: claude.ai → Settings → Capabilities → Skills →")
    print(f"           «Upload skill» → {output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
