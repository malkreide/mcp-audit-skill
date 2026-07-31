#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a server profile YAML/JSON against the canonical schema.

Closes issue #14. In the first audit the user pasted a template with `...`
placeholders into the chat instead of a real profile. Claude caught it
on its own — but that was defensive behaviour, not skill specification.
This module is the canonical gate at the top of Step 1.

What it catches:
- Required fields that are missing entirely
- Required fields whose value is a placeholder (`...`, `<...>`, `TODO`,
  empty string, None)
- Type mismatches (string where bool was expected, etc.)
- Closed-vocabulary fields carrying a value the catalog never compares
  against (see ALLOWED_VALUES)

The last category used to be out of scope, with this justification in
place of an implementation: "the canonical evaluator surfaces those
mismatches loudly via UnknownFieldError / TypeMismatchError once
applies_when runs". That was wrong, and the error was self-concealing.
`UnknownFieldError` fires for an unknown *field*; `TypeMismatchError`
for a mismatched *type*. An unknown *value* is a perfectly ordinary
string, so `transport == "HTTP/SSE"` against a profile saying
`transport: "HTTP"` simply evaluates to False — no exception, no
warning, nothing in the report.

The cost was measured, not assumed: a profile written `transport: HTTP`
(a spelling this repo's own docs recommended) lost SCALE-002, SCALE-003,
SCALE-007 and SDK-004 — two of them `high` — while every
`transport != "stdio-only"` check still fired. Half the profile was
recognised, and the audit reported a clean run over a smaller catalog
than it claimed. `OPS-005` names exactly this failure: a check that did
not run looks identical to one that passed.

Exit codes:
    0 — profile is clean
    1 — placeholder or schema error
    2 — usage error (missing file, etc.)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Bootstrap so tools.* imports work when invoked as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402


# Canonical required fields. The list mirrors the profile shape used in
# applies_when expressions across the v0.5.0+ catalog.
REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "transport": str,
    "auth_model": str,
    "data_class": str,
    "write_capable": bool,
    "deployment": list,
    "is_cloud_deployed": bool,
    "uses_sampling": bool,
    "uses_sequential_thinking": bool,
    "tools_include_filesystem": bool,
    "tools_make_external_requests": bool,
    "stadt_zuerich_context": bool,
    "schulamt_context": bool,
    "volksschule_context": bool,
    "enterprise_context": bool,
    # Sieben Checks fragen dieses Feld ab (SDK-001…006, IDENT-005). Fehlte es,
    # kam das Profil hier sauber durch und erst der Evaluator warf sieben
    # UnknownFieldError — nach dem Gate, das genau solche Löcher fangen soll.
    # `audit-notion-sync.py` hat es bis v1.3.0 nie gesetzt.
    "sdk_language": str,
    "data_source": dict,
}

# Fields with a closed vocabulary — every value the catalog's `applies_when`
# clauses can meaningfully compare against.
#
# Only fields that are genuinely closed belong here. `auth_model` and
# `data_class` are not: they carry documented values no check singles out
# (`OIDC`, `Verwaltungsdaten`), and those are handled correctly by the
# `!=` clauses. A value nobody compares against is a gap in the catalog,
# not an error in the profile — pinning them here would reject valid
# profiles for describing a server accurately.
#
# `transport` is different, and it is the reason this constant exists.
# `HTTP` and `SSE` were never additional transports; they were a second
# spelling of `HTTP/SSE`, recommended by portfolio.example.yaml and the
# slash command while the catalog only ever compared against the joined
# form. Same concept, two spellings, and the mismatch cost four checks
# in silence.
#
# Adding a value here is a catalog-wide decision: it must be a value some
# `applies_when` clause actually tests, or the vocabulary grows a member
# that can never change an audit outcome.
ALLOWED_VALUES: dict[str, tuple[str, ...]] = {
    "transport": ("stdio-only", "dual", "HTTP/SSE"),
}

# A field whose value matches one of these patterns is a placeholder.
_PLACEHOLDER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*$"),                  # empty / whitespace
    re.compile(r"^\s*\.\.\.\s*$"),         # bare "..."
    re.compile(r"^\s*<.*>\s*$"),           # "<placeholder>", "<TODO>"
    re.compile(r"^\s*TODO\s*$", re.IGNORECASE),
    re.compile(r"^\s*FIXME\s*$", re.IGNORECASE),
    re.compile(r"^\s*XXX\s*$"),
)


def _is_placeholder_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return any(p.match(value) for p in _PLACEHOLDER_PATTERNS)
    if isinstance(value, list):
        return len(value) == 0 or any(_is_placeholder_value(v) for v in value)
    return False


def validate_profile(
    profile: dict[str, Any],
    required: dict[str, type | tuple[type, ...]] = REQUIRED_FIELDS,
    allowed: dict[str, tuple[str, ...]] = ALLOWED_VALUES,
) -> dict[str, Any]:
    """Check `profile` for missing/placeholder/wrong-type/unknown-value fields.

    Returns:
        {
          "consistent": bool,
          "missing": [field, ...],
          "placeholder": [field, ...],
          "type_mismatch": [{"field": ..., "expected": ..., "got": ...}, ...],
          "enum_mismatch": [{"field": ..., "allowed": [...], "got": ...}, ...]
        }
    """
    if not isinstance(profile, dict):
        return {
            "consistent": False,
            "missing": list(required),
            "placeholder": [],
            "type_mismatch": [],
            "enum_mismatch": [],
            "error": (
                f"profile is {type(profile).__name__}, not an object"
            ),
        }

    missing: list[str] = []
    placeholder: list[str] = []
    type_mismatch: list[dict[str, str]] = []
    enum_mismatch: list[dict[str, Any]] = []

    for field, expected_type in required.items():
        if field not in profile:
            missing.append(field)
            continue
        value = profile[field]
        if _is_placeholder_value(value):
            placeholder.append(field)
            continue
        if not isinstance(value, expected_type):
            # bool is a subclass of int in Python; treat them strictly.
            if expected_type is bool and not isinstance(value, bool):
                type_mismatch.append({
                    "field": field,
                    "expected": "bool",
                    "got": type(value).__name__,
                })
                continue
            if not isinstance(value, expected_type):
                expected_name = (
                    expected_type.__name__
                    if isinstance(expected_type, type)
                    else str(expected_type)
                )
                type_mismatch.append({
                    "field": field,
                    "expected": expected_name,
                    "got": type(value).__name__,
                })

    # Closed vocabularies. Deliberately checked only for fields that got
    # this far clean: a missing or placeholder `transport` is already
    # reported once, and naming it a second time as "unknown value" would
    # describe the same defect twice in different words.
    for field, choices in allowed.items():
        if field in missing or field in placeholder:
            continue
        if any(m["field"] == field for m in type_mismatch):
            continue
        value = profile.get(field)
        if value not in choices:
            enum_mismatch.append({
                "field": field,
                "allowed": list(choices),
                "got": value,
            })

    # data_source has a known nested field
    ds = profile.get("data_source")
    if isinstance(ds, dict):
        if "is_swiss_open_data" not in ds:
            missing.append("data_source.is_swiss_open_data")
        elif _is_placeholder_value(ds["is_swiss_open_data"]):
            placeholder.append("data_source.is_swiss_open_data")
        elif not isinstance(ds["is_swiss_open_data"], bool):
            type_mismatch.append({
                "field": "data_source.is_swiss_open_data",
                "expected": "bool",
                "got": type(ds["is_swiss_open_data"]).__name__,
            })

    consistent = not (missing or placeholder or type_mismatch or enum_mismatch)
    return {
        "consistent": consistent,
        "missing": missing,
        "placeholder": placeholder,
        "type_mismatch": type_mismatch,
        "enum_mismatch": enum_mismatch,
    }


def _load_profile(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        sys.exit(
            "PyYAML is required to read .yaml profiles. "
            "Install with: pip install pyyaml. Or pass a .json profile."
        )
    data = yaml.safe_load(text)
    # Unwrap common shapes.
    if isinstance(data, dict) and isinstance(data.get("servers"), list) and data["servers"]:
        first = data["servers"][0]
        return first.get("profile", first) if isinstance(first, dict) else {}
    if isinstance(data, dict) and "profile" in data and len(data) <= 3:
        return data["profile"]
    return data if isinstance(data, dict) else {}


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="validate_profile",
        description=(
            "Verify a profile YAML/JSON has no placeholders, no missing "
            "fields, no type mismatches before Step 2 starts."
        ),
    )
    parser.add_argument("profile", help="Path to profile YAML or JSON")
    parser.add_argument(
        "--out",
        default=None,
        help="Write JSON report to this path (otherwise print to stdout)",
    )
    args = parser.parse_args(argv)

    profile_path = Path(args.profile)
    if not profile_path.exists():
        print(f"Error: {profile_path} not found", file=sys.stderr)
        return 2

    profile = _load_profile(profile_path)
    report = validate_profile(profile)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["consistent"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
