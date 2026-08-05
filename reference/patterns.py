"""Copy-paste patterns for the nine data-fidelity rules (FastMCP / httpx / pydantic v2).

Each block is self-contained and annotated with the rule it implements. Adapt the
names; keep the shape. The comments are deliberately verbose — they are the part
that survives into the target codebase and explains *why* to the next reader.

Rules 1-6 come from incidents. Rules 7-9 are derived from MCP spec 2026-07-28 and
only apply to a server that speaks it — with one exception: rule 7 (a total sort
order) breaks pagination on every spec version.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

SEARCH_FIELDS = ("Terminus", "Name", "Abbreviation", "Definition", "Note", "Source")


# ---------------------------------------------------------------------------
# Rule 1 — resolve the full scope when the caller does not narrow it
# ---------------------------------------------------------------------------


class Client:
    async def _all_scope_ids(self) -> list[int] | None:
        """Every scope ID, so that an unfiltered query really is unfiltered.

        Many APIs restrict an ID-less query to a "default set" — one slice of the
        corpus, often the residual one — and report the shortfall as an ordinary
        empty result. Sending the full set is the only way to search everything.

        Best-effort by design: if the vocabulary is unreachable the query still
        runs, just unwidened. A widening optimisation must never be able to break
        the thing it widens.
        """
        try:
            values, _, _ = await self.vocabulary("Classification")
        except Exception:  # noqa: BLE001 — best-effort, never fatal
            log.warning("upstream.scope_widening_unavailable")
            return None
        return [v["id"] for v in values if isinstance(v.get("id"), int)] or None

    async def search(
        self,
        term: str,
        *,
        fields: tuple[str, ...] = SEARCH_FIELDS,
        scope_ids: list[int] | None = None,
        max_results: int = 25,
    ) -> list[dict]:
        if not term.strip():
            raise ValueError("term must not be empty")
        for field in fields:
            if field not in SEARCH_FIELDS:
                raise ValueError(
                    f"Unknown field {field!r}; expected one of {SEARCH_FIELDS}"
                )

        # Rule 1: None means "search everything", not "let the API decide".
        if scope_ids is None:
            scope_ids = await self._all_scope_ids()

        params: dict[str, Any] = {"SearchTerm": term, "MaxEntryCount": max_results}

        # Rule 2: every flag of the group is sent explicitly. Unsent flags keep
        # their API-side default (often true), which would make `fields` able to
        # widen the search but never to narrow it — a silent no-op.
        requested = set(fields)
        for field in SEARCH_FIELDS:
            params[f"Field.{field}"] = "true" if field in requested else "false"

        if scope_ids:
            params["ScopeIds"] = scope_ids

        resp = await self._http.get(f"{self.base_url}/Search", params=params)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Rule 3 — an empty result carries the next step, not just a zero
# ---------------------------------------------------------------------------

EMPTY_HINT = (
    "No entry matched. `search_term` is Lucene syntax: try a prefix wildcard "
    "(e.g. 'Quellensteuer*') to catch compounds, or the fuzzy operator ('~'). "
    "Widen `fields` to cover definition and note text. Only then conclude that "
    "the term is absent — and do not substitute a guess for the official value."
)


class SearchResult(BaseModel):
    source: str
    provenance: str
    retrieved_at: str
    returned: int
    truncated: bool
    hint: str | None = Field(
        default=None,
        description="Set when the search returned nothing; suggests how to widen it",
    )
    entries: list[dict]


def build_result(entries: list[dict], **envelope: Any) -> SearchResult:
    return SearchResult(
        returned=len(entries),
        hint=EMPTY_HINT if not entries else None,
        entries=entries,
        **envelope,
    )


# ---------------------------------------------------------------------------
# Rule 3, boundary — a failed request is not an empty result
# ---------------------------------------------------------------------------


class UpstreamUnreachableError(RuntimeError):
    """The request never reached the source: rejected, refused or timed out.

    Deliberately an error and not an empty result — the same line rule 6 draws
    for a shape change, one layer further out. To the calling layer a rejected
    request looks like "failed, no data", which is indistinguishable from zero
    hits for anything that only asks "any records?".

    Measured case: a request carrying a foreign Host header comes back as
    HTTP 421 with the body ``Invalid Host header``. Formatted as an empty set it
    arrives at the model with EMPTY_HINT attached — try a wildcard, widen the
    fields — while the query never reached the source at all. The next step here
    is a different one: check the configuration, do not widen the search.
    """


def _unreachable(exc: Exception) -> UpstreamUnreachableError:
    return UpstreamUnreachableError(
        f"The source did not answer the query ({exc}). This is not an empty "
        "result: the request was turned away before any search ran. Check the "
        "endpoint, the Host header and the credentials — widening the query "
        "will not help."
    )


async def search_or_raise(client: Client, term: str, **envelope: Any) -> SearchResult:
    """Read path for rule 3, with the boundary in place.

    ✗ What this deliberately does NOT do::

        try:
            entries = await client.search(term)
        except httpx.HTTPError:
            entries = []          # a 421/401/403 becomes "nothing found"
        return build_result(entries, **envelope)

    That except clause is the whole bug: it hands a configuration error to the
    model dressed as a fact about the corpus, and a hint that sends it the wrong
    way. Note that a passing mock cannot see this either — the failure only
    exists on the wire.
    """
    try:
        entries = await client.search(term)
    except httpx.HTTPStatusError as exc:  # 4xx/5xx — rejected, not answered
        raise _unreachable(exc) from exc
    except httpx.RequestError as exc:  # DNS, TLS, refused, timeout
        raise _unreachable(exc) from exc
    return build_result(entries, **envelope)


# ---------------------------------------------------------------------------
# Rules 4 + 5 — the tool description does the heavy lifting
# ---------------------------------------------------------------------------


async def search_terms(search_term: str, fields: str = "") -> SearchResult:
    """Search the source for official designations.

    `search_term` is **Lucene query syntax**: `*` and `?` wildcards and the `~`
    fuzzy operator work. Matching is on whole words, so a compound is not found
    by its parts — «Quellensteuer» does not match «Quellensteuerverordnung», but
    «Quellensteuer*» does. Reach for a wildcard before concluding a term is
    absent. By default the search spans the whole corpus; pass `scope_ids` to
    narrow it.

    Scope caveat: the source holds administrative nomenclature, not domain
    vocabulary, so a term may genuinely be absent. Establish that with a wildcard
    retry, not from a single empty result, and never fill the gap with a guessed
    designation.

    NOTE ON PHRASING (rule 4): the caveat above asks for a retry. It deliberately
    does NOT say "an empty result usually means the term is out of scope" — that
    earlier wording handed the model a ready-made excuse for the tool's own
    silence, and the model used it to invent an answer for a term that was in the
    database all along.
    """
    ...


# ---------------------------------------------------------------------------
# Rule 5 — the recall canary. Mocks cannot catch this class; only live can.
# ---------------------------------------------------------------------------

RECALL_FLOORS = [
    # (query, minimum entries). Set each floor generously below the measured
    # value — roughly half. The canary must catch a collapse from 21 to 1, not
    # go red on routine corpus maintenance. A test that cries wolf gets muted,
    # and a muted test catches nothing.
    ("Pensionskasse", 10),
    ("Quellensteuer", 1),
]


async def test_recall_floor(client: Client) -> None:
    """Live regression guard: scope regressions AND upstream default changes."""
    for term, floor in RECALL_FLOORS:
        entries = await client.search(term, max_results=100)
        assert len(entries) >= floor, (
            f"{term}: {len(entries)} entries < floor {floor} — scope shrunk? "
            "Re-run the omitted-vs-maximal comparison for every optional filter."
        )


async def test_fields_can_narrow(client: Client) -> None:
    """Rule 2: an argument whose effect cannot be measured does not exist."""
    broad = await client.search("Steuer", max_results=1000)
    narrow = await client.search("Steuer", fields=("Abbreviation",), max_results=1000)
    assert len(narrow) < len(broad), (
        "`fields` does not narrow — flags sent incompletely?"
    )


async def test_wildcard_finds_compounds(client: Client) -> None:
    """Rule 5: whole-word matching means compounds need a wildcard."""
    exact = await client.search("Quellensteuer", max_results=100)
    prefix = await client.search("Quellensteuer*", max_results=100)
    assert len(prefix) > len(exact)


# ---------------------------------------------------------------------------
# Rule 6 — confirm the response shape before counting it
# ---------------------------------------------------------------------------


class UpstreamSchemaError(RuntimeError):
    """The upstream answered, but not in the shape this client reads.

    Deliberately an error and not an empty result. A misread nesting produces
    exactly the same empty list as a genuine zero-hit answer — no exception, no
    status code, no log line — and the model cannot tell the two apart. That is
    the same confabulation surface as rule 3, one layer down.
    """


def rows_of(payload: dict[str, Any], envelope: str, *required: str) -> list[dict]:
    """Return the row list, or raise if the payload is not shaped as assumed.

    Checks only what the caller actually reads: the envelope key and the fields
    named in ``required`` on the first row. This is not schema validation — a
    full schema breaks on every harmless upstream addition and buys nothing.

    The failure this guards against is real: an MCP Registry query returned
    nothing for a while because the fields sit under ``servers[].server.*`` and
    the client looked one level up. Syntactically fine, semantically blind.
    """
    rows = payload.get(envelope)
    if rows is None:
        raise UpstreamSchemaError(
            f"Response has no {envelope!r}. Keys present: {sorted(payload)[:10]}"
        )
    if not isinstance(rows, list):
        raise UpstreamSchemaError(
            f"{envelope!r} is {type(rows).__name__}, expected list"
        )
    if rows:
        missing = [f for f in required if f not in rows[0]]
        if missing:
            raise UpstreamSchemaError(
                f"Row misses {missing}; shape was {json.dumps(rows[0])[:200]}"
            )
    return rows


async def fetch_rows(client: httpx.AsyncClient, url: str) -> list[dict]:
    """Read path with the guard in place.

    Note what is NOT written here: ``payload.get("servers", [])``. That default
    turns an upstream shape change into a valid-looking empty result — the tool
    reports "nothing found" for data that is present.
    """
    resp = await client.get(url)
    resp.raise_for_status()
    return rows_of(resp.json(), "servers", "name")


# ---------------------------------------------------------------------------
# Rule 7 — a total order, or pagination silently loses rows
# ---------------------------------------------------------------------------

# Documented in two places on purpose: in the tool description, so the model
# knows what the order means, and in the envelope, so a caller can rely on it.
# An order nobody can name is not one anybody may depend on.
SORT_KEY = "score desc, id asc"


def in_stable_order(rows: list[dict]) -> list[dict]:
    """Sort with a unique last element, so the order is total.

    A relevance score alone is not an order: it has ties, and what happens to
    ties is decided by the source's sort — often by shard layout, i.e. by
    accident. Two effects, one cause:

    * ``tools/list`` coming back re-ordered invalidates the client's prompt
      cache on an unchanged server. Spec 2026-07-28 dropped ``initialize`` and
      ``Mcp-Session-Id``, so reconnects are the normal case, not the exception.
    * Across page boundaries an unstable order *loses rows*: anything that moves
      between fetching page 1 and page 2 shows up twice or not at all. Same
      silent-incompleteness class as rule 1, arrived at by paging rather than by
      filtering — and it happens with every parameter correctly sent.

    Applies regardless of spec version. The tool registry itself needs the same
    treatment: a list in source is stable, a ``set``, a directory glob or a dict
    assembled across modules is not.
    """
    return sorted(rows, key=lambda r: (-float(r.get("score") or 0.0), str(r["id"])))


async def test_order_survives_upstream_permutation(client: Client) -> None:
    """Rule 7, offline: the *server* sorts, not the source.

    The mock has to permute. Mocking the same order twice and then asserting
    equality is the rule-5 failure shape — a test that establishes the condition
    under which the fault cannot occur.

    ✗ What this deliberately does NOT do::

        respx.get(url).mock(return_value=httpx.Response(200, json=PAGE))
        assert await client.search("x") == await client.search("x")   # tautology
    """
    ...


async def test_pagination_is_disjoint(client: Client) -> None:
    """Rule 7, live: the page cut only exists against the real source."""
    page1 = await client.search("Steuer", offset=0, limit=50)
    page2 = await client.search("Steuer", offset=50, limit=50)
    ids1, ids2 = {r["id"] for r in page1}, {r["id"] for r in page2}
    assert not ids1 & ids2, f"{len(ids1 & ids2)} rows duplicated — order not total"
    assert len(ids1 | ids2) == len(page1) + len(page2)


# ---------------------------------------------------------------------------
# Rule 8 — ttlMs is a promise; derive it, never guess it
# ---------------------------------------------------------------------------

# Unknown freshness means a short TTL, not a comfortable one. Without a ttlMs the
# client asks again; with a wrong one it declines to ask, on good grounds.
TTL_FLOOR_MS = 60_000


def ttl_from_freshness(
    last_modified: datetime | None,
    cadence: timedelta | None,
    now: datetime,
    *,
    floor_ms: int = TTL_FLOOR_MS,
) -> int:
    """Cap the TTL at the next publication of the source.

    A ttlMs that outlives the next update lets the client serve an answer the
    server already knew would be stale. Same class as a dropped filter
    parameter: rule 1 loses rows in space (outside the default scope), this
    loses them in time (added after the fetch). Both are formally fine, both are
    substantively incomplete, neither is visible to the caller.

    Derived from the freshness the envelope carries anyway (``source_freshness``,
    ``Last-Modified``, ``Cache-Control``, a published cadence) — not estimated.
    A source overdue for its own update promises nothing: the result is 0.
    """
    if last_modified is None or cadence is None:
        return floor_ms
    remaining_ms = int((last_modified + cadence - now).total_seconds() * 1000)
    return max(0, min(remaining_ms, int(cadence.total_seconds() * 1000)))


def cache_scope(*, requires_credentials: bool) -> Literal["public", "session"]:
    """The other half of rule 8, with sharper consequences.

    If the result depends on the caller's credentials — every server marked
    ``requires_credentials: true`` — then too wide a cacheScope stops being a
    freshness problem and becomes a data leak: A's answer served to B. Public is
    only for what is identical for every caller.
    """
    return "session" if requires_credentials else "public"


async def test_ttl_does_not_outlive_the_next_publication() -> None:
    """Rule 8, offline: with a known cadence the target value is computable.

    Freeze the clock, mock ``Last-Modified``, assert the TTL ends *before* the
    next publication — plus a second case: no freshness header at all must land
    on ``TTL_FLOOR_MS`` and a ``session`` scope, not on a comfortable default.
    """
    ...


async def test_ttl_against_real_source_freshness(client: Client) -> None:
    """Rule 8, live: an upper-bound canary, mirroring the rule-5 floor.

    Generous for the same reason: it must catch a cadence change upstream, not
    go red because a publication ran twenty minutes late.
    """
    ...


# ---------------------------------------------------------------------------
# Rule 9 — input_required is not an empty answer (MRTR, spec 2026-07-28)
# ---------------------------------------------------------------------------


class InputRequest(BaseModel):
    """One missing argument, with what would be an acceptable answer."""

    name: str
    description: str
    allowed_values: list[str] | None = None


class InputRequired(BaseModel):
    """The third outcome, and the dangerous one: it looks successful.

    HTTP 200, well-formed result, no hits in it. Format a follow-up question as
    an empty set and you get the rule-4 confabulation — this time about a
    question the server asked and nobody answered. The inverse costs as much: a
    genuine zero-hit dressed as ``input_required`` sends the client into a retry
    loop for data that does not exist.

    Note what is NOT on this model: ``entries`` and ``hint``. Their absence is
    the difference between "I did not search" and "I searched and found
    nothing". An ``input_required`` carrying ``entries: []`` is already the
    confusion.
    """

    result_type: Literal["input_required"] = "input_required"
    input_requests: list[InputRequest]


async def search_or_ask(
    client: Client, term: str, scope: str | None, **envelope: Any
) -> InputRequired | SearchResult:
    """State before quantity — the order is the whole point.

    ✗ What this deliberately does NOT do::

        entries = await client.search(term)
        if not entries:
            return build_result([], hint=EMPTY_HINT)   # swallows the question

    Search first and check the arguments afterwards, and the follow-up question
    has already been through the empty-set branch, hint attached.
    """
    if scope is None:
        return InputRequired(
            input_requests=[
                InputRequest(
                    name="scope",
                    description=(
                        "Which part of the corpus to search. Required: an "
                        "unscoped query would silently cover one slice only."
                    ),
                    allowed_values=["ALL", "VARIA"],
                )
            ]
        )
    return build_result(await client.search(term), **envelope)


async def test_the_three_outcomes_stay_disjoint() -> None:
    """Rule 9, offline: question, empty set and error share no field.

    Three cases against the same tool, asserted in both directions — a follow-up
    question must never carry ``hint`` (rule 3 pointed the wrong way), an empty
    set must never carry ``input_requests`` (the client retries into the void) —
    plus the retry round: answered with ``inputResponses``, the same call has to
    return hits. A question whose answer changes nothing was not a question.
    """
    ...
