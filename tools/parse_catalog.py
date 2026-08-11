#!/usr/bin/env python3
"""Parse the check catalog (checks/*.md frontmatter) into structured data.

Replaces the inline awk/heredoc loops that the slash command and Step 2 of
the SKILL workflow used to generate ad-hoc — the original audit run on
Windows hit Bash quoting crashes when those heredocs got too clever
(issue #11). This module is the canonical replacement.

Usage:
    python tools/parse_catalog.py             # JSON to stdout
    python tools/parse_catalog.py --format table
    python tools/parse_catalog.py --format manifest-check
    python tools/parse_catalog.py --checks-dir path/to/checks
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Make `tools.*` importable when this script is invoked directly
# (e.g. `python tools/parse_catalog.py`) and not as part of a package.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.eval_applicability import (  # noqa: E402
    DEFAULT_SPEC_BASELINE,
    VALID_SPEC_BASELINES,
    parse_check_frontmatter,
)
from tools.path_utils import force_utf8_stdio  # noqa: E402

REQUIRED_FIELDS = ("id", "title", "category", "severity", "applies_when")

# Adoption stage — how hard a check bites while the portfolio catches up.
#
#   enforced  a failure at critical/high blocks production-readiness
#   advisory  the finding is reported and counted, but never blocks
#
# Severity says how bad a violation is; adoption says whether the catalogue is
# yet entitled to hold the portfolio to it. Without the distinction a new check
# arrives as a red pipeline across 30+ servers on the day it is merged, which
# is how checks get reverted rather than adopted.
#
# The field is OPTIONAL and defaults to `enforced`: every check that predates
# it keeps blocking exactly as before, so adding the mechanism changes no
# verdict. An unknown value is a hard error — a typo must not silently demote
# a check to advisory, which would be the quietest possible way to lose one.
VALID_ADOPTIONS = ("advisory", "enforced")
DEFAULT_ADOPTION = "enforced"

# Spec baseline vocabulary lives in `eval_applicability` — that module owns the
# gate that applies it, and importing the other way round would be circular.
# The reasoning behind the field is documented at the definition.

# How many observations a result for this check must carry before it counts as
# verified — for `pass` just as much as for `fail`.
#
# The field has been in every check's frontmatter from the start, and SKILL.md
# states the rule ("at least `evidence_required` points observed"). Nothing
# under `tools/` ever read it, so a `pass` carrying an empty evidence list went
# through the gate untouched. That is the same defect as an empty finding
# document, pointing the way that ends the conversation: a `fail` gets worked
# on, a `pass` closes the subject.
#
# Normalised to an int here so no consumer has to guess whether the frontmatter
# said "2" or 2. A missing field defaults to 1 — the least that still means
# somebody looked — and a non-integer is a hard error, because a typo must not
# quietly drop the requirement to nothing.
DEFAULT_EVIDENCE_REQUIRED = 1


def _coerce_evidence_required(raw: Any, source: str) -> int:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return DEFAULT_EVIDENCE_REQUIRED
    try:
        value = int(str(raw).strip())
    except ValueError:
        raise ValueError(
            f"{source}: invalid evidence_required {raw!r}; expected a whole number"
        ) from None
    if value < 0:
        raise ValueError(f"{source}: evidence_required must not be negative ({value})")
    return value


def _default_checks_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "checks"


def list_check_files(checks_dir: Path) -> list[Path]:
    """All `*.md` files in checks_dir, sorted by stem.

    MANIFEST.txt is intentionally not a `.md` so it isn't picked up.
    """
    return sorted(p for p in checks_dir.glob("*.md") if p.is_file())


def parse_catalog(checks_dir: Path) -> dict[str, dict[str, Any]]:
    """Parse every check file into a frontmatter dict, keyed by check ID.

    Raises ValueError if two files declare the same `id` or if a file is
    missing required fields.
    """
    catalog: dict[str, dict[str, Any]] = {}
    for path in list_check_files(checks_dir):
        fm = parse_check_frontmatter(path)
        cid = fm.get("id") or path.stem
        missing = [f for f in REQUIRED_FIELDS if not fm.get(f)]
        if missing:
            raise ValueError(
                f"{path.name}: frontmatter missing required field(s) {missing}"
            )
        adoption = str(fm.get("adoption") or DEFAULT_ADOPTION).strip()
        if adoption not in VALID_ADOPTIONS:
            raise ValueError(
                f"{path.name}: invalid adoption {adoption!r}; "
                f"expected one of {VALID_ADOPTIONS}"
            )
        fm["adoption"] = adoption
        baseline = str(fm.get("spec_baseline") or DEFAULT_SPEC_BASELINE).strip()
        if baseline not in VALID_SPEC_BASELINES:
            raise ValueError(
                f"{path.name}: invalid spec_baseline {baseline!r}; "
                f"expected one of {VALID_SPEC_BASELINES}"
            )
        fm["spec_baseline"] = baseline
        fm["evidence_required"] = _coerce_evidence_required(
            fm.get("evidence_required"), path.name
        )
        if cid in catalog:
            raise ValueError(
                f"Duplicate check id {cid!r} in {path.name} "
                f"(also in {catalog[cid].get('_source')})"
            )
        fm["_source"] = path.name
        catalog[cid] = fm
    return catalog


def manifest_check(checks_dir: Path) -> dict[str, Any]:
    """Compare MANIFEST.txt against parsed catalog. Returns a diff report.

    The manifest is the authoritative list of catalog IDs; the goal of
    this check is to detect drift (missing files, orphan files, etc).
    """
    manifest_path = checks_dir / "MANIFEST.txt"
    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path} not found")
    manifest_ids = [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    catalog = parse_catalog(checks_dir)
    catalog_ids = list(catalog.keys())
    in_manifest_only = sorted(set(manifest_ids) - set(catalog_ids))
    in_catalog_only = sorted(set(catalog_ids) - set(manifest_ids))
    return {
        "manifest_count": len(manifest_ids),
        "catalog_count": len(catalog_ids),
        "consistent": not (in_manifest_only or in_catalog_only),
        "in_manifest_only": in_manifest_only,
        "in_catalog_only": in_catalog_only,
    }


def category_counts(catalog: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fm in catalog.values():
        cat = fm.get("category", "?")
        counts[cat] = counts.get(cat, 0) + 1
    return dict(sorted(counts.items()))


def severity_counts(catalog: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fm in catalog.values():
        sev = fm.get("severity", "?")
        counts[sev] = counts.get(sev, 0) + 1
    return dict(sorted(counts.items()))


def adoption_counts(catalog: dict[str, dict[str, Any]]) -> dict[str, int]:
    """How many checks are enforced vs advisory.

    Both keys are always present, including when one is zero: a missing key
    reads as "not measured" rather than "none", and the whole point of the
    stage is that nobody should have to guess which checks are blocking.
    """
    counts: dict[str, int] = dict.fromkeys(VALID_ADOPTIONS, 0)
    for fm in catalog.values():
        counts[fm.get("adoption", DEFAULT_ADOPTION)] += 1
    return counts


def spec_baseline_counts(catalog: dict[str, dict[str, Any]]) -> dict[str, int]:
    """How many checks sit on each spec baseline.

    Every key is always present, including at zero — for the same reason
    `adoption_counts` does it. During waves A–D both baselines exist in the
    portfolio simultaneously, and "no checks for that revision" and "never
    counted" must not read alike.
    """
    counts: dict[str, int] = dict.fromkeys(VALID_SPEC_BASELINES, 0)
    for fm in catalog.values():
        counts[fm.get("spec_baseline", DEFAULT_SPEC_BASELINE)] += 1
    return counts


def ids_for_baseline(catalog: dict[str, dict[str, Any]], baseline: str) -> list[str]:
    """IDs of the checks declaring exactly `baseline`, sorted.

    Exact match, not "would fire for" — `beide` is its own answer here. The
    retirement question at the end of wave D ("which checks describe a protocol
    nobody speaks any more") needs the narrow set, not the firing set.
    """
    if baseline not in VALID_SPEC_BASELINES:
        raise ValueError(
            f"invalid spec_baseline {baseline!r}; expected one of "
            f"{VALID_SPEC_BASELINES}"
        )
    return sorted(
        cid
        for cid, fm in catalog.items()
        if fm.get("spec_baseline", DEFAULT_SPEC_BASELINE) == baseline
    )


def advisory_ids(catalog: dict[str, dict[str, Any]]) -> list[str]:
    """IDs of the checks that report but do not block, sorted."""
    return sorted(
        cid
        for cid, fm in catalog.items()
        if fm.get("adoption", DEFAULT_ADOPTION) == "advisory"
    )


def _print_table(catalog: dict[str, dict[str, Any]]) -> None:
    print(
        f"{'ID':<14} {'CAT':<6} {'SEV':<10} {'ADOPTION':<10} "
        f"{'BASELINE':<12} APPLIES_WHEN"
    )
    for cid, fm in catalog.items():
        print(
            f"{cid:<14} "
            f"{fm.get('category', '?'):<6} "
            f"{fm.get('severity', '?'):<10} "
            f"{fm.get('adoption', DEFAULT_ADOPTION):<10} "
            f"{fm.get('spec_baseline', DEFAULT_SPEC_BASELINE):<12} "
            f"{fm.get('applies_when', '?')}"
        )
    print()
    print(f"Total: {len(catalog)} checks")
    print(f"By category: {category_counts(catalog)}")
    print(f"By severity: {severity_counts(catalog)}")
    print(f"By adoption: {adoption_counts(catalog)}")
    print(f"By spec baseline: {spec_baseline_counts(catalog)}")
    advisory = advisory_ids(catalog)
    if advisory:
        print(f"Advisory (reported, never blocking): {', '.join(advisory)}")


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="parse_catalog",
        description=(
            "Parse the check catalog into structured data. Replaces the "
            "ad-hoc awk/heredoc loops that the SKILL Step 2 used to "
            "generate during audit runs."
        ),
    )
    parser.add_argument(
        "--checks-dir",
        default=str(_default_checks_dir()),
        help="Directory containing check markdown files",
    )
    parser.add_argument(
        "--format",
        choices=("json", "table", "manifest-check"),
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Write output to file instead of stdout",
    )
    args = parser.parse_args(argv)

    checks_dir = Path(args.checks_dir)
    if not checks_dir.is_dir():
        print(f"Error: {checks_dir} is not a directory", file=sys.stderr)
        return 2

    if args.format == "manifest-check":
        report = manifest_check(checks_dir)
        text = json.dumps(report, indent=2, ensure_ascii=False)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0 if report["consistent"] else 1

    catalog = parse_catalog(checks_dir)

    if args.format == "json":
        text = json.dumps(catalog, indent=2, ensure_ascii=False)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    if args.format == "table":
        if args.out:
            print("--out is not supported with --format table", file=sys.stderr)
            return 2
        _print_table(catalog)
        return 0

    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
