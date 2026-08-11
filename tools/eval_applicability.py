#!/usr/bin/env python3
"""Canonical applies_when DSL evaluator for mcp-audit-skill.

The DSL is a small Boolean language used in check frontmatter to declare
when a check applies to a given server profile. This module is the single
source of truth for evaluation. It does NOT use eval() and does NOT defer
to Python operator semantics; the grammar is implemented as a hand-written
recursive-descent parser so that the same expression yields the same
result in every environment.

Grammar (EBNF-ish):
    expr          := or_expr
    or_expr       := and_expr ("or" and_expr)*
    and_expr      := primary ("and" primary)*
    primary       := "(" expr ")"
                   | "always"
                   | includes_call
                   | comparison
    includes_call := dotted_ident "." "includes" "(" string_literal ")"
    comparison    := operand ("==" | "!=") operand
    operand       := dotted_ident | string_literal | bool_literal
    dotted_ident  := ident ("." ident)*
    ident         := [A-Za-z_][A-Za-z0-9_]*
    string_literal:= "\"" ... "\""  |  "'" ... "'"
    bool_literal  := "true" | "false"

Semantics:
    - "always"             → True
    - field == "literal"   → strict equality, both sides resolved
    - field == true/false  → strict equality on booleans
    - field.includes("x")  → x in list(field). LHS must be list-typed.
    - Unknown fields, missing dotted path, or type mismatches raise
      ApplicabilityError. Silent False is forbidden — auditors must see
      profile-schema gaps loudly.
    - Operator precedence: "and" binds tighter than "or".
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Bootstrap so tools.* imports work when invoked as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.compare_guard import (  # noqa: E402
    EmptyComparisonError,
    diff_sets,
    require_non_empty,
)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ApplicabilityError(Exception):
    """Base class for all evaluator errors."""


class ParseError(ApplicabilityError):
    """Raised when the expression is syntactically invalid."""


class UnknownFieldError(ApplicabilityError):
    """Raised when a referenced profile field does not exist."""


class TypeMismatchError(ApplicabilityError):
    """Raised when an operator is applied to incompatible types."""


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


@dataclass
class Token:
    kind: str  # IDENT, STRING, BOOL, ALWAYS, EQ, NE, AND, OR, LP, RP, DOT
    value: Any
    pos: int


_TOKEN_REGEX = re.compile(
    r"""
    \s+
    | (?P<EQ>==)
    | (?P<NE>!=)
    | (?P<LP>\()
    | (?P<RP>\))
    | (?P<DOT>\.)
    | (?P<STRING>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')
    | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)

_KEYWORDS = {
    "and": "AND",
    "or": "OR",
    "true": "BOOL",
    "false": "BOOL",
    "always": "ALWAYS",
}


def tokenize(expr: str) -> list[Token]:
    if expr is None:
        raise ParseError("Expression is None")
    tokens: list[Token] = []
    i = 0
    while i < len(expr):
        m = _TOKEN_REGEX.match(expr, i)
        if not m:
            raise ParseError(
                f"Unexpected character {expr[i]!r} at position {i} in {expr!r}"
            )
        if m.group().isspace():
            i = m.end()
            continue
        kind = m.lastgroup
        raw = m.group(kind)
        if kind == "IDENT":
            kw = _KEYWORDS.get(raw)
            if kw == "BOOL":
                tokens.append(Token("BOOL", raw == "true", i))
            elif kw == "AND":
                tokens.append(Token("AND", "and", i))
            elif kw == "OR":
                tokens.append(Token("OR", "or", i))
            elif kw == "ALWAYS":
                tokens.append(Token("ALWAYS", True, i))
            else:
                tokens.append(Token("IDENT", raw, i))
        elif kind == "STRING":
            # Strip surrounding quotes and process basic escapes.
            inner = raw[1:-1].encode("utf-8").decode("unicode_escape")
            tokens.append(Token("STRING", inner, i))
        else:
            tokens.append(Token(kind, raw, i))
        i = m.end()
    tokens.append(Token("EOF", None, len(expr)))
    return tokens


# ---------------------------------------------------------------------------
# Parser + Evaluator (combined for compactness; AST built on the fly)
# ---------------------------------------------------------------------------


class Parser:
    def __init__(self, tokens: list[Token], expr: str, profile: dict[str, Any]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.expr = expr
        self.profile = profile

    # ---- token helpers ----
    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind: str) -> Token:
        tok = self.peek()
        if tok.kind != kind:
            raise ParseError(
                f"Expected {kind} but got {tok.kind} ({tok.value!r}) "
                f"at position {tok.pos} in {self.expr!r}"
            )
        return self.advance()

    # ---- grammar ----
    def parse_expr(self) -> bool:
        result = self.parse_or()
        if self.peek().kind != "EOF":
            tok = self.peek()
            raise ParseError(
                f"Unexpected trailing token {tok.kind} ({tok.value!r}) "
                f"at position {tok.pos} in {self.expr!r}"
            )
        return result

    def parse_or(self) -> bool:
        left = self.parse_and()
        while self.peek().kind == "OR":
            self.advance()
            right = self.parse_and()
            left = bool(left) or bool(right)
        return left

    def parse_and(self) -> bool:
        left = self.parse_primary()
        while self.peek().kind == "AND":
            self.advance()
            right = self.parse_primary()
            left = bool(left) and bool(right)
        return left

    def parse_primary(self) -> bool:
        tok = self.peek()
        if tok.kind == "LP":
            self.advance()
            inner = self.parse_or()
            self.expect("RP")
            return inner
        if tok.kind == "ALWAYS":
            self.advance()
            return True
        if tok.kind == "IDENT":
            # Could be: dotted_ident.includes("x"), dotted_ident == ...,
            # dotted_ident != ...
            ident_tokens = self._collect_dotted()
            nxt = self.peek()
            if nxt.kind == "DOT":
                # method call: must be .includes(...)
                self.advance()
                method = self.expect("IDENT")
                if method.value != "includes":
                    raise ParseError(
                        f"Only .includes() is supported, got .{method.value} "
                        f"at position {method.pos} in {self.expr!r}"
                    )
                self.expect("LP")
                arg_tok = self.expect("STRING")
                self.expect("RP")
                return self._eval_includes(ident_tokens, arg_tok.value)
            if nxt.kind in ("EQ", "NE"):
                op = self.advance().kind
                rhs = self._parse_operand()
                lhs_value = self._resolve_field(ident_tokens)
                return self._compare(lhs_value, op, rhs)
            raise ParseError(
                f"Expected '==', '!=', or '.' after identifier "
                f"{'.'.join(t.value for t in ident_tokens)!r} "
                f"at position {nxt.pos} in {self.expr!r}"
            )
        if tok.kind in ("STRING", "BOOL"):
            # Bare literal as primary is only valid as part of a comparison;
            # we never start a primary with a literal. This prevents
            # accidental "true" or '"foo"' as standalone expressions.
            raise ParseError(
                f"Unexpected literal {tok.value!r} at position {tok.pos}; "
                f"literals must appear on the right-hand side of '==' or '!='. "
                f"Expression: {self.expr!r}"
            )
        raise ParseError(
            f"Unexpected token {tok.kind} ({tok.value!r}) at position {tok.pos} "
            f"in {self.expr!r}"
        )

    # ---- helpers ----
    def _collect_dotted(self) -> list[Token]:
        """Greedy-collect IDENT (DOT IDENT)*, but only when the dotted form is
        a field path (not a method call). We stop before a DOT followed by
        'includes' so that .includes() parsing happens in parse_primary.
        """
        idents = [self.expect("IDENT")]
        while self.peek().kind == "DOT":
            # Look ahead: is this DOT IDENT('includes') LP ?
            if (
                self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos + 1].kind == "IDENT"
                and self.tokens[self.pos + 1].value == "includes"
                and self.pos + 2 < len(self.tokens)
                and self.tokens[self.pos + 2].kind == "LP"
            ):
                break
            self.advance()  # consume DOT
            idents.append(self.expect("IDENT"))
        return idents

    def _parse_operand(self) -> Any:
        tok = self.peek()
        if tok.kind == "STRING":
            self.advance()
            return tok.value
        if tok.kind == "BOOL":
            self.advance()
            return tok.value
        if tok.kind == "IDENT":
            ident_tokens = self._collect_dotted()
            return self._resolve_field(ident_tokens)
        raise ParseError(
            f"Expected operand (string, bool, or field) but got {tok.kind} "
            f"at position {tok.pos} in {self.expr!r}"
        )

    def _resolve_field(self, ident_tokens: list[Token]) -> Any:
        path = [t.value for t in ident_tokens]
        cur: Any = self.profile
        traversed: list[str] = []
        for segment in path:
            traversed.append(segment)
            if not isinstance(cur, dict):
                raise UnknownFieldError(
                    f"Cannot traverse {'.'.join(path)!r}: "
                    f"{'.'.join(traversed[:-1]) or '<root>'} is not an object"
                )
            if segment not in cur:
                raise UnknownFieldError(
                    f"Profile field {'.'.join(path)!r} not found "
                    f"(missing segment: {segment!r})"
                )
            cur = cur[segment]
        return cur

    def _compare(self, lhs: Any, op: str, rhs: Any) -> bool:
        # Type compatibility: bool with bool, str with str. Disallow mixed.
        if isinstance(lhs, bool) or isinstance(rhs, bool):
            if not (isinstance(lhs, bool) and isinstance(rhs, bool)):
                raise TypeMismatchError(
                    f"Cannot compare {type(lhs).__name__} and {type(rhs).__name__} "
                    f"with {op}: lhs={lhs!r}, rhs={rhs!r}"
                )
        elif isinstance(lhs, str) or isinstance(rhs, str):
            if not (isinstance(lhs, str) and isinstance(rhs, str)):
                raise TypeMismatchError(
                    f"Cannot compare {type(lhs).__name__} and {type(rhs).__name__} "
                    f"with {op}: lhs={lhs!r}, rhs={rhs!r}"
                )
        else:
            raise TypeMismatchError(
                f"Unsupported operand types for {op}: "
                f"{type(lhs).__name__}, {type(rhs).__name__}"
            )
        if op == "EQ":
            return lhs == rhs
        return lhs != rhs

    def _eval_includes(self, ident_tokens: list[Token], needle: str) -> bool:
        value = self._resolve_field(ident_tokens)
        if not isinstance(value, list):
            raise TypeMismatchError(
                f".includes() requires a list field, got {type(value).__name__} "
                f"for {'.'.join(t.value for t in ident_tokens)!r}"
            )
        return needle in value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate(expression: str, profile: dict[str, Any]) -> bool:
    """Evaluate an applies_when expression against a profile.

    Raises ApplicabilityError (or subclass) on parse/lookup/type errors.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ParseError("Expression must be a non-empty string")
    tokens = tokenize(expression)
    parser = Parser(tokens, expression, profile)
    return parser.parse_expr()


# ---------------------------------------------------------------------------
# Spec baseline
# ---------------------------------------------------------------------------

# Which revision of the MCP specification a check is written against.
#
#   2025-11-25   the check measures against the pre-stateless protocol
#   2026-07-28   the check measures against the stateless protocol
#   beide        the check is protocol-shape independent
#
# This is a SECOND axis next to `applies_when`, deliberately not folded into
# it. Technically it could be one: `mcp_spec_version == "2026-07-28"` is an
# ordinary field comparison and the evaluator would handle it. Keeping them
# apart is the decision.
#
# `applies_when` answers *does this server look like the kind of server the
# check is about*. The baseline answers *does this check still describe the
# protocol this server speaks*. Those are different events with different
# fixes — a check that dropped out because the server is stdio-only needs a
# profile correction, a check that dropped out because the server migrated
# needs nothing at all — and §3.4 already draws exactly this line between a
# changed catalogue and a changed profile. Folded into one expression, the
# applicability report renders both as a bare `no-match` and the distinction
# is gone.
#
# The default is `beide`, which is the safe direction: a check that predates
# the field keeps firing for every profile, exactly as before. Narrowing is
# always an explicit act.
VALID_SPEC_BASELINES = ("2025-11-25", "2026-07-28", "beide")
DEFAULT_SPEC_BASELINE = "beide"
SPEC_BASELINE_FIELD = "mcp_spec_version"

# Reason prefixes. `baseline-mismatch` is an ordinary, expected outcome during
# waves A–D. `baseline-unresolved` is not: it means the profile never said
# which protocol the server speaks, so the answer is unknown rather than no.
# They are separate strings because collapsing them would recreate the §2.6
# defect one level up — "not applicable" and "never asked" reading alike.
REASON_BASELINE_MISMATCH = "baseline-mismatch"
REASON_BASELINE_UNRESOLVED = "baseline-unresolved"


def baseline_applies(check_baseline: str, profile_version: Any) -> tuple[bool, str]:
    """Does a check on `check_baseline` measure a server on `profile_version`?

    Returns `(applies, reason)`. The reason is empty when it applies, and
    carries one of the REASON_BASELINE_* prefixes when it does not.

    A check declaring `beide` applies regardless — including when the profile
    is silent, since nothing about it depends on the answer.
    """
    baseline = str(check_baseline or DEFAULT_SPEC_BASELINE).strip()
    if baseline not in VALID_SPEC_BASELINES:
        return False, (
            f"{REASON_BASELINE_UNRESOLVED}: check declares invalid "
            f"spec_baseline {baseline!r}; expected one of {VALID_SPEC_BASELINES}"
        )
    if baseline == DEFAULT_SPEC_BASELINE:
        return True, ""
    if profile_version is None or not str(profile_version).strip():
        return False, (
            f"{REASON_BASELINE_UNRESOLVED}: check is {baseline}-only but the "
            f"profile carries no {SPEC_BASELINE_FIELD}"
        )
    version = str(profile_version).strip()
    if version == baseline:
        return True, ""
    return False, (
        f"{REASON_BASELINE_MISMATCH}: check is {baseline}-only, "
        f"profile speaks {version}"
    )


def baseline_summary(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Count how the baseline gate changed the outcome, with the IDs.

    The counts exist so an applicability report can carry a line naming what
    the baseline removed. A migration in which 14 checks appear and 5 vanish is
    a large silent change to what an audit covers; unreported it looks like a
    clean run over a smaller catalogue, which is the failure `OPS-005` names.
    """
    mismatch = sorted(
        cid
        for cid, r in results.items()
        if str(r.get("reason", "")).startswith(REASON_BASELINE_MISMATCH)
    )
    unresolved = sorted(
        cid
        for cid, r in results.items()
        if str(r.get("reason", "")).startswith(REASON_BASELINE_UNRESOLVED)
    )
    return {
        "dropped_by_baseline": len(mismatch),
        "dropped_ids": mismatch,
        "unresolved": len(unresolved),
        "unresolved_ids": unresolved,
    }


_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---", re.DOTALL)


def parse_check_frontmatter(path: Path) -> dict[str, Any]:
    """Minimal YAML-ish frontmatter parser for our specific format.

    We avoid PyYAML to keep the evaluator dependency-free. The frontmatter
    is line-oriented `key: value` only, which is exactly what every check
    file uses. Tolerates both LF and CRLF line endings so that Windows
    checkouts with autocrlf=true don't break the regex.
    """
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ApplicabilityError(f"No frontmatter in {path}")
    fm: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            value = value[1:-1]
        fm[key] = value
    return fm


def evaluate_catalog(
    profile: dict[str, Any],
    checks_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Evaluate every check in checks_dir against the profile.

    Returns a dict keyed by check ID with shape:
        { "applicable": bool, "reason": str, "expression": str,
          "spec_baseline": str }

    Two gates run, in this order: the spec baseline first, then `applies_when`.
    The order is not cosmetic. If a check describes a protocol this server does
    not speak, its `applies_when` verdict says nothing worth reporting — the
    profile fields it compares (transport, auth model) are still meaningful,
    but the thing being checked no longer exists. Reporting the coarser reason
    is the honest one.
    """
    results: dict[str, dict[str, Any]] = {}
    profile_version = profile.get(SPEC_BASELINE_FIELD)
    for md in sorted(checks_dir.glob("*.md")):
        try:
            fm = parse_check_frontmatter(md)
        except ApplicabilityError as e:
            results[md.stem] = {
                "applicable": False,
                "reason": f"frontmatter-error: {e}",
                "expression": "",
                "spec_baseline": DEFAULT_SPEC_BASELINE,
            }
            continue
        check_id = fm.get("id", md.stem)
        expr = fm.get("applies_when", "always")
        baseline = fm.get("spec_baseline", DEFAULT_SPEC_BASELINE)
        in_baseline, baseline_reason = baseline_applies(baseline, profile_version)
        if not in_baseline:
            results[check_id] = {
                "applicable": False,
                "reason": baseline_reason,
                "expression": expr,
                "spec_baseline": baseline,
            }
            continue
        try:
            applicable = evaluate(expr, profile)
            reason = "match" if applicable else "no-match"
        except UnknownFieldError as e:
            applicable = False
            reason = f"unknown-field: {e}"
        except TypeMismatchError as e:
            applicable = False
            reason = f"type-mismatch: {e}"
        except ParseError as e:
            applicable = False
            reason = f"parse-error: {e}"
        results[check_id] = {
            "applicable": applicable,
            "reason": reason,
            "expression": expr,
            "spec_baseline": baseline,
        }
    return results


def applicable_ids(results: dict[str, dict[str, Any]]) -> list[str]:
    """The check ids an evaluation marked applicable, sorted."""
    return sorted(cid for cid, r in results.items() if r.get("applicable"))


def diff_applicability(
    left_label: str,
    left: dict[str, dict[str, Any]],
    right_label: str,
    right: dict[str, dict[str, Any]],
    allow_empty: bool = False,
) -> dict[str, Any]:
    """Compare two catalog evaluations, refusing empty sides.

    Two things are compared, not one: which checks each side *evaluated* and
    which it found *applicable*. Keeping them apart is the point — a check
    that vanished because the catalogue shrank and a check that vanished
    because the profile changed are different events with different fixes,
    and a single applicable-set diff renders them identically.

    Both evaluations must be non-empty. An applicability diff over two empty
    parses reports `identical` while having compared nothing; see
    `tools/compare_guard.py` for the run where that happened.
    """
    hint = "Check the --checks-dir path: a directory with no *.md parses to nothing."
    require_non_empty(
        f"{left_label} (evaluated checks)", left, hint=hint, allow_empty=allow_empty
    )
    require_non_empty(
        f"{right_label} (evaluated checks)", right, hint=hint, allow_empty=allow_empty
    )

    evaluated = diff_sets(
        left_label, left.keys(), right_label, right.keys(), allow_empty=allow_empty
    )
    # The applicable sets may legitimately be empty even when the catalogue
    # parsed fine — a profile that matches nothing is a real, reportable state,
    # unlike a catalogue that parsed to nothing. The guard above has already
    # established that something *was* looked at, so this diff is allowed to be
    # empty on either side.
    applicable = diff_sets(
        left_label,
        applicable_ids(left),
        right_label,
        applicable_ids(right),
        allow_empty=True,
    )

    changed: list[dict[str, Any]] = []
    for cid in evaluated["common"]:
        lhs, rhs = left[cid], right[cid]
        if bool(lhs.get("applicable")) != bool(rhs.get("applicable")):
            changed.append(
                {
                    "check_id": cid,
                    left_label: {
                        "applicable": bool(lhs.get("applicable")),
                        "reason": lhs.get("reason", ""),
                    },
                    right_label: {
                        "applicable": bool(rhs.get("applicable")),
                        "reason": rhs.get("reason", ""),
                    },
                    "expression": rhs.get("expression", lhs.get("expression", "")),
                }
            )

    return {
        "evaluated": evaluated,
        "applicable": applicable,
        "changed_applicability": changed,
        "identical": evaluated["identical"] and not changed,
    }


def _load_evaluation(
    path: Path,
    checks_dir: Path,
    server: str | None,
) -> dict[str, dict[str, Any]]:
    """Load one side of a diff: either a saved evaluation or a profile.

    A saved evaluation is the JSON this tool's `catalog` subcommand emits —
    that is what makes a diff against an *earlier* run possible, since the
    catalogue of that run may no longer be on disk. Anything else is treated
    as a profile and evaluated against `checks_dir` now.
    """
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data:
            first = next(iter(data.values()))
            if isinstance(first, dict) and "applicable" in first:
                return data
    profile = _load_profile(path, server)
    return evaluate_catalog(profile, checks_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _force_utf8_stdout() -> None:
    enc = (sys.stdout.encoding or "").lower()
    if enc != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def _load_profile(path: Path, server_name: str | None = None) -> dict[str, Any]:
    """Load a profile dict from YAML/JSON.

    Accepts:
      - A bare profile dict: `{transport: ..., auth_model: ..., ...}`
      - A wrapped profile: `{name, repo, profile: {...}}`
      - A portfolio file with `servers: [{name, repo, profile: {...}}, ...]` —
        in which case `server_name` selects the entry (or the first one if
        omitted).
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError:
            sys.exit(
                "PyYAML is required to read .yaml profiles. "
                "Install with: pip install pyyaml. Or pass a .json profile."
            )
        data = yaml.safe_load(text)

    # Portfolio format
    if isinstance(data, dict) and isinstance(data.get("servers"), list):
        servers = data["servers"]
        if not servers:
            sys.exit(f"Portfolio file {path} contains no servers.")
        if server_name is None:
            entry = servers[0]
        else:
            for s in servers:
                if s.get("name") == server_name:
                    entry = s
                    break
            else:
                names = ", ".join(s.get("name", "<unnamed>") for s in servers)
                sys.exit(
                    f"Server {server_name!r} not found in {path}. Available: {names}"
                )
        if "profile" not in entry:
            sys.exit(f"Server {entry.get('name')!r} has no profile section.")
        return entry["profile"]

    # Wrapped profile
    if isinstance(data, dict) and "profile" in data and len(data) <= 3:
        return data["profile"]

    # Bare profile dict
    return data


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(
        prog="eval_applicability",
        description="Canonical applies_when DSL evaluator for mcp-audit-skill.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_expr = sub.add_parser("expr", help="Evaluate a single expression")
    p_expr.add_argument("expression", help="The applies_when expression")
    p_expr.add_argument("profile", help="Path to profile YAML or JSON")
    p_expr.add_argument(
        "--server",
        default=None,
        help="When profile is a portfolio file, pick this server entry",
    )

    p_cat = sub.add_parser(
        "catalog",
        help="Evaluate all checks in a directory against a profile",
    )
    p_cat.add_argument("profile", help="Path to profile YAML or JSON")
    p_cat.add_argument(
        "--server",
        default=None,
        help="When profile is a portfolio file, pick this server entry",
    )
    p_cat.add_argument(
        "--checks-dir",
        default=str(Path(__file__).resolve().parent.parent / "checks"),
        help="Directory containing check markdown files",
    )
    p_cat.add_argument(
        "--format",
        choices=("json", "table"),
        default="json",
        help="Output format",
    )

    p_diff = sub.add_parser(
        "diff",
        help="Compare two applicability evaluations (profiles or saved JSON)",
    )
    p_diff.add_argument(
        "left",
        help="Profile YAML/JSON, or a saved `catalog --format json` evaluation",
    )
    p_diff.add_argument("right", help="The other side, same accepted formats")
    p_diff.add_argument(
        "--checks-dir",
        default=str(Path(__file__).resolve().parent.parent / "checks"),
        help="Catalogue used when a side is a profile rather than a saved evaluation",
    )
    p_diff.add_argument(
        "--server",
        default=None,
        help="When a side is a portfolio file, pick this server entry",
    )
    p_diff.add_argument(
        "--labels",
        default=None,
        help="Comma-separated display labels for the two sides (default: the paths)",
    )
    p_diff.add_argument(
        "--allow-empty",
        action="store_true",
        help=(
            "Compare even when a side parsed to nothing. Off by default: two "
            "empty sides are trivially identical, which says something about "
            "the parse and nothing about the runs"
        ),
    )
    p_diff.add_argument(
        "--format",
        choices=("json", "table"),
        default="json",
        help="Output format",
    )

    args = parser.parse_args(argv)

    if args.cmd == "expr":
        profile = _load_profile(Path(args.profile), getattr(args, "server", None))
        result = evaluate(args.expression, profile)
        print(json.dumps({"applicable": result, "expression": args.expression}))
        return 0

    if args.cmd == "catalog":
        profile = _load_profile(Path(args.profile), getattr(args, "server", None))
        results = evaluate_catalog(profile, Path(args.checks_dir))
        baselines = baseline_summary(results)
        if args.format == "json":
            # No summary key in the payload: this JSON is the saved evaluation
            # the `diff` subcommand reads back, and it is keyed by check ID
            # throughout. A `_meta` entry would parse as a check.
            print(json.dumps(results, indent=2))
        else:
            applicable_count = sum(1 for r in results.values() if r["applicable"])
            version = profile.get(SPEC_BASELINE_FIELD) or "<unset>"
            print(f"Applicable: {applicable_count} / {len(results)}")
            print(
                f"Spec baseline: profile speaks {version}; "
                f"{baselines['dropped_by_baseline']} check(s) dropped as "
                f"written for the other revision"
            )
            if baselines["dropped_ids"]:
                print(f"  dropped: {', '.join(baselines['dropped_ids'])}")
            print(f"{'ID':<12} {'APPL':<6} reason")
            for check_id, r in results.items():
                marker = "YES" if r["applicable"] else "no"
                print(f"{check_id:<12} {marker:<6} {r['reason']}")
        if baselines["unresolved"]:
            print(
                f"Error: {baselines['unresolved']} check(s) declare a spec "
                f"baseline this profile cannot answer — it carries no "
                f"{SPEC_BASELINE_FIELD}. Those checks were neither run nor "
                f"ruled out: {', '.join(baselines['unresolved_ids'])}",
                file=sys.stderr,
            )
            return 3
        return 0

    if args.cmd == "diff":
        checks_dir = Path(args.checks_dir)
        left_path, right_path = Path(args.left), Path(args.right)
        if args.labels:
            parts = [p.strip() for p in args.labels.split(",")]
            if len(parts) != 2 or not all(parts):
                print("Error: --labels needs exactly two names", file=sys.stderr)
                return 2
            left_label, right_label = parts
        else:
            left_label, right_label = str(left_path), str(right_path)
        if left_label == right_label:
            print(
                "Error: both sides carry the label "
                f"{left_label!r}; a diff whose columns cannot be told apart "
                "is not readable",
                file=sys.stderr,
            )
            return 2

        try:
            left = _load_evaluation(left_path, checks_dir, args.server)
            right = _load_evaluation(right_path, checks_dir, args.server)
            report = diff_applicability(
                left_label, left, right_label, right, allow_empty=args.allow_empty
            )
        except EmptyComparisonError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        except OSError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        if args.format == "json":
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            ev, ap = report["evaluated"], report["applicable"]
            print(
                f"Evaluated: {ev['left_count']} ({left_label}) vs "
                f"{ev['right_count']} ({right_label})"
            )
            print(
                f"Applicable: {ap['left_count']} ({left_label}) vs "
                f"{ap['right_count']} ({right_label})"
            )
            for cid in ev["only_in_left"]:
                print(f"  -{cid:<12} only evaluated in {left_label}")
            for cid in ev["only_in_right"]:
                print(f"  +{cid:<12} only evaluated in {right_label}")
            for item in report["changed_applicability"]:
                lhs = "YES" if item[left_label]["applicable"] else "no"
                rhs = "YES" if item[right_label]["applicable"] else "no"
                print(
                    f"  ~{item['check_id']:<12} {lhs} -> {rhs}  ({item['expression']})"
                )
            print("\nidentical" if report["identical"] else "\ndiffers")
        # Exit 1 on a difference so the diff is usable as a gate; 0 means the
        # two sides really were compared and really did match.
        return 0 if report["identical"] else 1

    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
