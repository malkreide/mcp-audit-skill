# `applies_when` DSL — Formal Specification

This document defines the canonical Boolean DSL used in check-file frontmatter to declare when a check applies to a server profile. The reference implementation is `tools/eval_applicability.py`. The pytest suite under `tests/test_applicability.py` is the conformance test.

## Why a custom DSL

We deliberately do **not** use Python's `eval()`, JavaScript-style expression engines, or YAML-derived booleans. Each of those would leak host-language semantics into audit results, making applicability dependent on which environment the audit runs in. A small hand-rolled evaluator gives us:

- **Reproducibility** — the same expression yields the same result on every machine, every Python version, every shell.
- **Auditable failures** — unknown fields, type mismatches, and parse errors raise distinct exceptions instead of silently coercing to `False` or `True`.
- **Versioning** — when the DSL grows, the catalog can opt in per-check via a future `dsl_version:` frontmatter field.

## Grammar

```
expr           := or_expr
or_expr        := and_expr ("or" and_expr)*
and_expr       := primary ("and" primary)*
primary        := "(" expr ")"
                | "always"
                | includes_call
                | comparison
includes_call  := dotted_ident "." "includes" "(" string_literal ")"
comparison     := operand ("==" | "!=") operand
operand        := dotted_ident | string_literal | bool_literal
dotted_ident   := ident ("." ident)*
ident          := [A-Za-z_][A-Za-z0-9_]*
string_literal := '"' chars '"'  |  "'" chars "'"
bool_literal   := "true" | "false"
```

## Operator precedence

From tightest to loosest binding:

1. Parentheses `(...)`
2. Method call `.includes(...)`
3. Comparison `==`, `!=`
4. Conjunction `and`
5. Disjunction `or`

`and` binds tighter than `or`, matching SQL/Python convention.

## Reserved keywords

- `always` — always evaluates to `True`. Use this for universal checks.
- `and`, `or` — Boolean connectives. Lowercase only.
- `true`, `false` — Boolean literals. Lowercase only.
- `includes` — sole method call, only on list-typed fields.

Capitalised forms (`True`, `AND`, `Always`) are **not** keywords; they are treated as identifiers and will raise `UnknownFieldError` during evaluation.

## Type rules

The evaluator is strictly typed at evaluation time. There is no implicit coercion.

| Operator | Allowed operand types | Result |
|---|---|---|
| `==`, `!=` | both `str` **or** both `bool` | `bool` |
| `.includes(...)` | LHS `list[str]`, argument `str` | `bool` |

Comparing `list` to `str`, `bool` to `str`, or applying `.includes()` to a non-list raises `TypeMismatchError`.

## Field resolution

Fields are looked up in the profile dict by their dotted path:

```yaml
profile:
  data_source:
    is_swiss_open_data: true
```

```text
data_source.is_swiss_open_data    →    True
```

If any segment is missing, evaluation raises `UnknownFieldError`. Silent fallback to `False` is forbidden — audit reproducibility depends on schema completeness.

## Examples

| Expression | Meaning |
|---|---|
| `always` | Universal check |
| `transport == "stdio-only"` | True when transport is exactly `"stdio-only"` |
| `auth_model != "none"` | True when any authentication is configured |
| `deployment.includes("Railway")` | True when Railway is one of the deployment targets |
| `data_source.is_swiss_open_data == true` | Dotted field access |
| `transport == "HTTP/SSE" or transport == "dual"` | Disjunction |
| `auth_model == "OAuth-Proxy" and write_capable == true` | Conjunction |
| `(transport == "HTTP/SSE" or transport == "dual") and tools_make_external_requests == true` | Grouped |

## Anti-patterns and known catalog bugs

### Comparing a list to a string literal

```yaml
# WRONG — `deployment` is a list, `"local-stdio"` is a string.
applies_when: 'deployment != "local-stdio"'
```

The legacy ad-hoc evaluator silently treated this as `True` for any non-empty list, leading to false-positive applicability. The canonical evaluator raises `TypeMismatchError`. Resolved in issue #16: a derived boolean `is_cloud_deployed` was added to the profile schema, and the 9 affected checks were migrated.

**Canonical fix (since #16):**

```yaml
applies_when: 'is_cloud_deployed == true'
```

Semantic: `is_cloud_deployed` is `true` iff the `deployment` list contains at least one entry that is not `local-stdio`. The flag is derived automatically by `audit-notion-sync.py` from the Notion `Deployment` multi-select; portfolio.yaml authors must set it explicitly.

**Alternative for finer-grained checks:**

```yaml
# Multi-select membership without the boolean shortcut
applies_when: 'deployment.includes("Railway")'
```

### Capitalised booleans

```yaml
# WRONG — Python-style booleans are not keywords here.
applies_when: 'write_capable == True'
```

`True` is parsed as an identifier and the evaluator will look for a field named `True` in the profile, which doesn't exist. Use lowercase `true`.

### Bare literals as expressions

```yaml
# WRONG — literals only appear on the RHS of comparisons.
applies_when: 'true'
applies_when: '"stdio-only"'
```

Use `always` for "always applies" or a real comparison for everything else.

## Reference implementation

- Module: [`tools/eval_applicability.py`](../tools/eval_applicability.py)
- Public API:
  - `evaluate(expression: str, profile: dict) -> bool`
  - `evaluate_catalog(profile: dict, checks_dir: Path) -> dict[str, dict]`
- CLI:
  - `python tools/eval_applicability.py expr "<expression>" path/to/profile.yaml`
  - `python tools/eval_applicability.py catalog path/to/profile.yaml --format table`

## Conformance

A DSL implementation is conformant if and only if it passes every test in `tests/test_applicability.py` against the current `checks/` catalog. Any divergence (different applicable count, different error categories) is a defect.

When extending the DSL (e.g. adding `not`, list-literal `==`, or new methods), follow this process:

1. RFC issue describing the new construct and its semantics.
2. Update grammar in this document.
3. Update `eval_applicability.py` and add tests.
4. Increment the DSL version (future: add `dsl_version:` to `_VERSION` constant).
5. Provide a migration guide for the catalog.
