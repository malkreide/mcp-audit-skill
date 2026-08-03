#!/usr/bin/env python3
"""A comparison over an empty set is not a comparison.

**What went wrong.** An applicability diff between two audit runs reported
`0 == 0, identical` and was believed. Both sides had parsed to nothing — a
path that pointed at the wrong directory, so neither run contributed a single
check id — and the helper dutifully subtracted one empty set from the other
and found no difference. It was right about the arithmetic and wrong about
everything that mattered: the two runs *were* different, nobody had looked.

That is worse than having no comparison at all. Without the helper the
question stays open and someone eventually answers it. With it, a green line
closes the question using evidence that was never gathered — the same shape
`OPS-005` names for checks that never ran and `FID-003` names for empty result
sets a server interprets on the caller's behalf. An empty input is not a
finding of sameness; it is the absence of an observation.

So every comparison helper in this repo routes through `require_non_empty`
before it subtracts anything. The guard is deliberately blunt: it does not try
to distinguish "legitimately empty" from "accidentally empty", because the
helper cannot tell those apart and neither could the auditor who trusted the
first version. A genuinely empty side is rare enough to be worth an explicit
`--allow-empty`, and asking for that flag is a decision that leaves a trace.
"""

from __future__ import annotations

from collections.abc import Iterable, Sized
from typing import Any, TypeVar

T = TypeVar("T")


class EmptyComparisonError(Exception):
    """Raised when a comparison side holds nothing to compare.

    Carries the side's label so the message names *which* input was empty —
    "left side empty" would send the reader back to the source to work out
    which of the two runs that was.
    """

    def __init__(self, label: str, hint: str = "") -> None:
        self.label = label
        message = (
            f"{label} parsed to an empty set — refusing to compare. "
            "Two empty sides are trivially identical, which is a statement "
            "about the parse, not about the thing being compared."
        )
        if hint:
            message = f"{message} {hint}"
        super().__init__(message)


def require_non_empty(
    label: str,
    items: Sized,
    hint: str = "",
    allow_empty: bool = False,
) -> Sized:
    """Return `items` unchanged, or raise if it is empty.

    `allow_empty` exists for the case where a caller has *established* that a
    side is legitimately empty. It is a parameter rather than a silent
    tolerance so the decision appears in the call site and in the CLI history.
    """
    if not allow_empty and len(items) == 0:
        raise EmptyComparisonError(label, hint)
    return items


def diff_sets(
    left_label: str,
    left: Iterable[T],
    right_label: str,
    right: Iterable[T],
    allow_empty: bool = False,
) -> dict[str, Any]:
    """Set difference between two labelled collections, empty sides refused.

    Returns `only_in_left` / `only_in_right` / `common` as sorted lists plus
    the two input sizes, so a reader of the JSON can see what the verdict was
    computed *from* and not just the verdict.
    """
    left_set = set(left)
    right_set = set(right)
    require_non_empty(left_label, left_set, allow_empty=allow_empty)
    require_non_empty(right_label, right_set, allow_empty=allow_empty)

    only_left = sorted(left_set - right_set)  # type: ignore[type-var]
    only_right = sorted(right_set - left_set)  # type: ignore[type-var]
    common = sorted(left_set & right_set)  # type: ignore[type-var]
    return {
        "left_label": left_label,
        "right_label": right_label,
        "left_count": len(left_set),
        "right_count": len(right_set),
        "only_in_left": only_left,
        "only_in_right": only_right,
        "common": common,
        "identical": not only_left and not only_right,
    }
