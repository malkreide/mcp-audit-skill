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

It does NOT validate semantics like "is `transport` a valid enum value".
That's intentionally out of scope; the canonical evaluator surfaces
those mismatches loudly via UnknownFieldError / TypeMismatchError once
applies_when runs.

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
    "data_source": dict,
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
) -> dict[str, Any]:
    """Check `profile` for missing/placeholder/wrong-type fields.

    Returns:
        {
          "consistent": bool,
          "missing": [field, ...],
          "placeholder": [field, ...],
          "type_mismatch": [{"field": ..., "expected": ..., "got": ...}, ...]
        }
    """
    if not isinstance(profile, dict):
        return {
            "consistent": False,
            "missing": list(required),
            "placeholder": [],
            "type_mismatch": [],
            "error": (
                f"profile is {type(profile).__name__}, not an object"
            ),
        }

    missing: list[str] = []
    placeholder: list[str] = []
    type_mismatch: list[dict[str, str]] = []

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

    consistent = not (missing or placeholder or type_mismatch)
    return {
        "consistent": consistent,
        "missing": missing,
        "placeholder": placeholder,
        "type_mismatch": type_mismatch,
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
