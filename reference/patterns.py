"""Copy-paste patterns for the twelve data-fidelity rules (FastMCP, httpx, pydantic).

Each block is self-contained and annotated with the rule it implements. Adapt the
names; keep the shape. The comments are deliberately verbose — they are the part
that survives into the target codebase and explains *why* to the next reader.

Rules 1-6 and 10, 11 and 12 come from incidents. Rules 7-9 are derived from MCP
spec 2026-07-28 and only apply to a server that speaks it — with one exception:
rule 7 (a total sort order) breaks pagination on every spec version.
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
    # Rule 10 — the two fields that keep a suggestion from becoming a hit.
    match_type: Literal["exact", "none"] = Field(
        default="exact",
        description="What produced `entries`. Never 'fuzzy' here: see rule 10.",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description=(
            "Shorter variants of the caller's own term, derived not queried. "
            "Unverified: call the tool again with one of them."
        ),
    )
    entries: list[dict]


def build_result(
    entries: list[dict], *, term: str | None = None, **envelope: Any
) -> SearchResult:
    return SearchResult(
        returned=len(entries),
        hint=EMPTY_HINT if not entries else None,
        match_type="exact" if entries else "none",
        # Rule 10: offered, never executed. See shorter_variants() below.
        suggestions=[] if entries or term is None else shorter_variants(term),
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
    return build_result(entries, term=term, **envelope)


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
# Rule 5, third part — compare exactly; a substring assertion cannot fail
# ---------------------------------------------------------------------------

LIFESPAN_MARKER = "Lifespan gestartet — geteilter HTTP-Client bereit"


def assert_marker(observed: str) -> None:
    """Assert on a structured field with equality, never with a substring.

    ✗ What this deliberately does NOT do::

        assert LIFESPAN_MARKER in observed
        assert observed.startswith("Lifespan gestartet")

    A prefix assertion holds until the field value grows — and then it keeps
    holding while meaning something else, because from there on it only ever
    checks the part that never changes. Same failure shape as the mock above: a
    test that establishes the condition under which the fault cannot occur.

    Measured case: the marker was declared as «Lifespan gestartet» while the
    field read «Lifespan gestartet — geteilter HTTP-Client bereit». The exact
    comparison failed although the server was running correctly, and it pointed
    straight at what was actually wrong — the stale declaration. ``in`` would
    have stayed green, preserved that declaration, and gone on being green once
    the tail of the field came to mean something else entirely.

    No tension with the prefix wildcard under rule 5: that one is aimed at a
    text corpus, this at a value. Full text wants to be fuzzy, a status field
    does not. Nor with rule 1's "exact instead of wildcard" — there exactness
    narrows recall against the source and has to be justified; here it only
    makes the assertion as wide as the field it claims to cover.
    """
    assert observed == LIFESPAN_MARKER, f"marker drifted: {observed!r}"


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


def cache_scope(*, requires_credentials: bool) -> Literal["public", "private"]:
    """The other half of rule 8, with sharper consequences.

    If the result depends on the caller's credentials — every server marked
    ``requires_credentials: true`` — then too wide a cacheScope stops being a
    freshness problem and becomes a data leak: A's answer served to B. Public is
    only for what is identical for every caller.

    SEP-2549 defines exactly two values, ``"public"`` and ``"private"``. There is
    no narrower-sounding third one; an invented value is not a cautious value, it
    fails schema validation.
    """
    return "private" if requires_credentials else "public"


async def test_ttl_does_not_outlive_the_next_publication() -> None:
    """Rule 8, offline: with a known cadence the target value is computable.

    Freeze the clock, mock ``Last-Modified``, assert the TTL ends *before* the
    next publication — plus a second case: no freshness header at all must land
    on ``TTL_FLOOR_MS`` and a ``private`` scope, not on a comfortable default.
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
            return build_result([], term=term)         # swallows the question

    Search first and check the arguments afterwards, and the follow-up question
    has already been through the empty-set branch, hint and suggestions attached.
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
    return build_result(await client.search(term), term=term, **envelope)


async def test_the_three_outcomes_stay_disjoint() -> None:
    """Rule 9, offline: question, empty set and error share no field.

    Three cases against the same tool, asserted in both directions — a follow-up
    question must never carry ``hint`` (rule 3 pointed the wrong way), an empty
    set must never carry ``input_requests`` (the client retries into the void) —
    plus the retry round: answered with ``inputResponses``, the same call has to
    return hits. A question whose answer changes nothing was not a question.
    """
    ...


# ---------------------------------------------------------------------------
# Rule 10 — suggesting is not widening
# ---------------------------------------------------------------------------


def shorter_variants(term: str, *, minimum: int = 5) -> list[str]:
    """Prefix variants of the caller's OWN term — derived, never queried.

    The safety property of rule 10: no entry in a result may be attributable to
    a term the caller did not choose. Everything in ``entries`` answers the term
    that went in, and nothing else.

    Two halves, and they hold each other up. Suggest nothing and the empty set
    carries no next step, which is the rule-3 failure. Run the suggestions and
    return their hits, and the model reports rows for «Quellensteuerverordnung»
    that in fact answer «Quellensteuer» — invisibly, because the response looks
    the same either way.

    Derived from the input on purpose. A list of "popular terms" fetched from
    the source is a second result type with its own recall risk, and one more
    query nobody asked for.
    """
    stem = term.strip()
    out = []
    while len(stem) > minimum:
        stem = stem[:-3]
        out.append(f"{stem}*")
    return out[:3]


async def search_and_suggest(
    client: Client, term: str, **envelope: Any
) -> SearchResult:
    """Rule 10 read path: exactly one query goes out, for exactly what came in.

    ✗ What this deliberately does NOT do::

        entries = await client.search(term)
        if not entries:
            for variant in shorter_variants(term):
                entries = await client.search(variant)      # <- the whole bug
                if entries:
                    return build_result(entries, **envelope)

    Boundary against ``ARCH-003``, which is ``enforced`` in the audit catalogue
    and asks for a fuzzy match *or* a suggestion mechanism plus a ``match_type``
    field: the suggestion arm satisfies the check and this rule at once. Take the
    fuzzy arm instead and the heuristic rows belong in a field of their own, with
    the term that produced them — merged into ``entries`` they are indistinguish-
    able from hits. What is forbidden is the merge, not the help.
    """
    return build_result(await client.search(term), term=term, **envelope)


async def test_suggestions_are_never_searched() -> None:
    """Rule 10, offline — and offline is the point, not a concession.

    The subject under test is what went OUT, not what came back: assert the
    upstream route was called exactly once and with the caller's term verbatim.
    Live, that is unmeasurable — a search with one hit looks like a search whose
    term was quietly swapped. The mock is legitimate here because the assumption
    being tested is the server's own behaviour, not the shape of the source.

    Needs its pair to mean anything (rule 9's shape, applied here): a server that
    suggests nothing passes this test trivially, so the other half asserts that
    an empty result carries suggestions AND that each is a variant of the input.
    """
    ...


# ---------------------------------------------------------------------------
# Rule 11 — the empty set carries the request that produced it
# ---------------------------------------------------------------------------


class EffectiveRequest(BaseModel):
    """What actually went out — resolved, not what the caller passed in.

    "Nothing there" and "asked wrong" differ in exactly one thing: the request.
    Leave it out of the result and the model has nothing to tell them apart, so
    it does what rule 4 describes — this time without a description having
    invited it. Rule 3 asks the empty set for a next step; this is the other
    half of the same answer, and the half that makes the first one checkable.

    The distance between "as sent" and "as received" is rule 1. An omitted scope
    is resolved to the full scope at runtime, best-effort — meaning the
    resolution is allowed to fail, and then the search runs unwidened while the
    empty set afterwards reads like "nothing in the whole corpus". Only
    ``scope_source`` makes that visible; it is itself an instance of rule 12,
    three facts that look identical once flattened to a list of ids.

    Credentials never go in here. The echo is scope, filters and limits, not the
    authentication — an API key in a request echo is a leak, and via too wide a
    ``cacheScope`` (rule 8) a forwarded one.
    """

    search_term: str
    scope_ids: list[int]
    scope_source: Literal["caller", "resolved", "upstream_default"]
    fields: list[str]
    limit: int


class SearchResultWithEcho(SearchResult):
    """Rule 3's envelope, plus the request it answers.

    Mandatory on the empty set. On a result with hits it is cheap and harmless,
    and as soon as any narrowing was applied ``FID-001`` asks for it anyway. NOT
    on an ``input_required`` (rule 9): nothing went out, so there is nothing to
    report — the same reason ``entries`` is absent there instead of empty.
    """

    request: EffectiveRequest


async def search_and_echo(
    client: Client, term: str, *, max_results: int = 25, **envelope: Any
) -> SearchResultWithEcho:
    """Read path for rule 11: one query, and a result that names it.

    ✗ What this deliberately does NOT do::

        entries = await client.search(term)
        return build_result(entries, term=term)      # says that nothing came
                                                     # back, nothing about what
                                                     # went out
    """
    resolved = await client._all_scope_ids()
    entries = await client.search(term, scope_ids=resolved, max_results=max_results)
    return SearchResultWithEcho(
        **build_result(entries, term=term, **envelope).model_dump(),
        request=EffectiveRequest(
            search_term=term,
            scope_ids=resolved or [],
            # Not a cosmetic distinction: "resolved" and "upstream_default"
            # answer different questions about the same empty set.
            scope_source="resolved" if resolved else "upstream_default",
            fields=sorted(SEARCH_FIELDS),
            limit=max_results,
        ),
    )


async def test_the_empty_result_carries_what_actually_went_out() -> None:
    """Rule 11, half 1 — the echo is checked against the request, not the input.

    Called without a scope, the result must report the scope that was actually
    sent. Comparing the echo with the caller's arguments would pass on a server
    that never widens anything; compare it with ``route.calls[-1].request``.
    """
    ...


async def test_two_runs_that_went_out_differently_read_differently() -> None:
    """Rule 11, half 2 — an echo that always reads the same is not one.

    Let the vocabulary endpoint fail on the second run so rule 1's best-effort
    widening degrades, and assert the two empty sets do NOT read alike. This is
    the half that catches the actual incident: a check stage reported the same
    sentence for 38 of 42 servers, so "stays silent" and "words it differently"
    became one message — and the one server that never started at all was lost
    inside it.

    Without half 1 a server passes this with an echo that varies but describes
    something other than the request. Without half 2 a server passes half 1 with
    a hard-wired echo, which is exactly the 38 identical lines.
    """
    ...


# ---------------------------------------------------------------------------
# Rule 12 — absence is three-valued: not collected / empty in source / withheld
# ---------------------------------------------------------------------------


class FieldValue(BaseModel):
    """One value slot, carrying the reason it is empty when it is.

    A single ``null`` collapses three different facts: the server never asked
    for the value (field flag off — rule 2, projection, sub-query not run), the
    source was asked and holds none, or the value exists and is not handed out
    (allow-list, personal data, authorisation). Read as "has none", the first of
    those is a claim about a record that nobody measured.
    """

    state: Literal["present", "empty_in_source", "not_collected", "withheld"]
    value: str | None = None


def pypi_dist_of(entry: dict[str, Any], *, collected: bool) -> FieldValue:
    """Set the third value where the decision was made; never derive it.

    ✗ What this deliberately does NOT do::

        return entry.get("pypi_dist")

    This is rule 6 one level down: ``payload.get("servers", [])`` turns a shape
    change into an empty set, ``entry.get("pypi_dist")`` turns an upstream
    rename into a run of justified omissions — nothing measured, exit 0. Both
    times the lookup's fallback value is the entire cause.

    Caught in review rather than shipped, which is worth saying: it establishes
    the mechanism, not that anyone outside missed it.
    """
    if not collected:
        return FieldValue(state="not_collected")
    if "pypi_dist" not in entry:
        raise UpstreamSchemaError(
            f"'pypi_dist' missing. Keys present: {sorted(entry)[:10]}"
        )
    value = entry["pypi_dist"]
    if not value:
        return FieldValue(state="empty_in_source")
    return FieldValue(state="present", value=value)


class ServerRecord(BaseModel):
    """Rule 12's second half: the meaning belongs on the field, with the duty.

    A house-wide "null means unknown" convention hides the thing that matters —
    silence is fatal on one field and free on the next.
    """

    pypi_dist: FieldValue = Field(
        description=(
            "PyPI distribution. state='not_collected' does NOT mean 'has none': "
            "nothing was measured, and the caller aborts instead of counting "
            "the record as checked. state='empty_in_source' means the source "
            "holds none."
        )
    )
    start_event: FieldValue = Field(
        description=(
            "Start marker. state='not_collected' deliberately falls back to the "
            "default here — unlike pypi_dist, silence costs nothing. That two "
            "fields share one null and carry two different duties is why this "
            "sits on the field and not in a convention."
        )
    )


async def test_a_field_that_was_not_requested_is_not_reported_as_absent() -> None:
    """Rule 12, half 1 — "not asked" and "asked and empty" are two values.

    Query once with the field projected away and once with it in; the first must
    read ``not_collected``, never ``empty_in_source``.
    """
    ...


async def test_a_renamed_upstream_key_is_a_finding_not_an_omission() -> None:
    """Rule 12, half 2 — the third value is set, not found.

    Feed a payload whose key was renamed upstream and expect an
    ``UpstreamSchemaError``, not a well-formed record full of omissions.

    Without half 2, a server that marks every field ``not_collected`` passes
    half 1: it measured nothing and reports that correctly. Without half 1, a
    server passes half 2 while still folding "not asked" and "nothing there"
    into one null. Both directions asserted — rule 9's and rule 10's test shape.
    """
    ...
