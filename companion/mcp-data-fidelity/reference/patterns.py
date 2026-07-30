"""Copy-paste patterns for the five data-fidelity rules (FastMCP / httpx / pydantic v2).

Each block is self-contained and annotated with the rule it implements. Adapt the
names; keep the shape. The comments are deliberately verbose — they are the part
that survives into the target codebase and explains *why* to the next reader.
"""

from __future__ import annotations

from typing import Any

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
                raise ValueError(f"Unknown field {field!r}; expected one of {SEARCH_FIELDS}")

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
    assert len(narrow) < len(broad), "`fields` does not narrow — flags sent incompletely?"


async def test_wildcard_finds_compounds(client: Client) -> None:
    """Rule 5: whole-word matching means compounds need a wildcard."""
    exact = await client.search("Quellensteuer", max_results=100)
    prefix = await client.search("Quellensteuer*", max_results=100)
    assert len(prefix) > len(exact)
