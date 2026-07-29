"""Reference: response envelope with attribution + provenance.

Copy this pattern into every new *-mcp server. Pydantic's default-value
mechanism makes it impossible to forget the attribution.

Usage:

    from .models import ServerResponse, MyPayload

    @mcp.tool()
    async def my_tool(...) -> dict:
        payload = do_work(...)
        return ServerResponse(
            provenance="live_api",          # or "weekly_dump" / "cached"
            payload=payload,
        ).model_dump()
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# --- Attribution strings by data source type -------------------------------

ATTRIBUTION_OGD_CH = (
    "Data: {source} — Open Government Data Switzerland. "
    "https://opendata.swiss/en/terms-of-use"
)

ATTRIBUTION_CC_BY_40 = (
    "Data: {source} — CC BY 4.0 "
    "(https://creativecommons.org/licenses/by/4.0/)."
)

ATTRIBUTION_CC_BY_SA_40 = (
    "Data: {source} — CC BY-SA 4.0 "
    "(https://creativecommons.org/licenses/by-sa/4.0/). "
    "Derivative datasets must be shared under the same licence."
)

ATTRIBUTION_BUND = (
    "Data: {source} — Swiss Confederation. "
    "Not an official statement; always verify against the primary source."
)


# --- Provenance enum --------------------------------------------------------

PROVENANCE_VALUES = {
    "weekly_dump": "Served from a cached weekly bulk export",
    "live_api": "Fetched live from the upstream REST/GraphQL/SPARQL endpoint",
    "cached": "Served from in-memory cache, not refetched this call",
    "fallback_stale": (
        "Upstream was unreachable; served from last-known-good cache. "
        "Treat as potentially stale."
    ),
}


# --- Base envelope ---------------------------------------------------------


class ServerResponse(BaseModel):
    """Base envelope. All tool responses inherit from this or include it."""

    model_config = ConfigDict(extra="allow")

    source: str = Field(
        description="Data attribution. Set the default on your subclass to pin the licence.",
    )
    provenance: str = Field(
        description=(
            "One of: weekly_dump, live_api, cached, fallback_stale. "
            "Enables downstream consumers to reason about freshness."
        ),
    )
    retrieved_at: str | None = Field(
        default=None,
        description="ISO-8601 UTC timestamp when the data was retrieved. Optional.",
    )


# --- Example subclass with pinned attribution ------------------------------


class MyServerResponse(ServerResponse):
    """Example: set the source default once, use everywhere."""

    source: str = Field(
        default=ATTRIBUTION_CC_BY_40.format(source="Example.ch")
    )
