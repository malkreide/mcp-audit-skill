#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    kind: str   # IDENT, STRING, BOOL, ALWAYS, EQ, NE, AND, OR, LP, RP, DOT
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
            # Could be: dotted_ident.includes("x"), dotted_ident == ..., dotted_ident != ...
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
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        elif value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        fm[key] = value
    return fm


def evaluate_catalog(
    profile: dict[str, Any],
    checks_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Evaluate every check in checks_dir against the profile.

    Returns a dict keyed by check ID with shape:
        { "applicable": bool, "reason": str, "expression": str }
    """
    results: dict[str, dict[str, Any]] = {}
    for md in sorted(checks_dir.glob("*.md")):
        try:
            fm = parse_check_frontmatter(md)
        except ApplicabilityError as e:
            results[md.stem] = {
                "applicable": False,
                "reason": f"frontmatter-error: {e}",
                "expression": "",
            }
            continue
        check_id = fm.get("id", md.stem)
        expr = fm.get("applies_when", "always")
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
        }
    return results


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
                sys.exit(f"Server {server_name!r} not found in {path}. "
                         f"Available: {names}")
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

    args = parser.parse_args(argv)

    if args.cmd == "expr":
        profile = _load_profile(Path(args.profile), getattr(args, "server", None))
        result = evaluate(args.expression, profile)
        print(json.dumps({"applicable": result, "expression": args.expression}))
        return 0

    if args.cmd == "catalog":
        profile = _load_profile(Path(args.profile), getattr(args, "server", None))
        results = evaluate_catalog(profile, Path(args.checks_dir))
        if args.format == "json":
            print(json.dumps(results, indent=2))
        else:
            applicable_count = sum(1 for r in results.values() if r["applicable"])
            print(f"Applicable: {applicable_count} / {len(results)}")
            print(f"{'ID':<12} {'APPL':<6} reason")
            for check_id, r in results.items():
                marker = "YES" if r["applicable"] else "no"
                print(f"{check_id:<12} {marker:<6} {r['reason']}")
        return 0

    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
