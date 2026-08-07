"""Reference: retry with jittered backoff, Retry-After and a wall-clock budget.

THIS FILE IS COPIED, NOT IMPORTED — A CHANGE HERE IS A PORTFOLIO CHANGE.
``reference/adoption.toml`` names every server that took this template: 18
adoptions across 17 repositories at the time of writing, each with the file and
the symbol the copy lives under. Anyone editing this file owes the same
statement — *who has already taken this version* — because until an adoption is
listed, the defect this file used to ship is still running somewhere. The
2026-08-03 sweep that produced the repair below read eleven of those servers;
not one honoured ``Retry-After`` and not one jittered, because they all had
this template.

What the template guarantees, and what ``adoption.toml`` checks a copy for:

* ``Retry-After`` beats our own curve. Both RFC 9110 §10.2.3 forms are read
  (delta-seconds and HTTP-date); an unreadable header yields ``None`` and falls
  back to the curve. It must never crash on the error path.
* Every wait is jittered — exponential into ``[0.5x, 1.5x]``, a ``Retry-After``
  one-sided into ``[1.0x, 1.25x]``. The source said *when*; later is polite,
  earlier ignores the very value being read.
* The ceiling is applied AFTER the jitter: ``min(jittered, MAX)``. The other
  order is not a bound — 20s capped, then multiplied by 1.5, is 30s.
* The budget is seconds, not attempts, and it hangs off ``asyncio.timeout``.
  Not off the httpx timeout: httpx bounds each *operation*, and its read
  timeout restarts with every chunk, so a slowly trickling response outlives
  the budget without any single read expiring.
* The original exception is re-raised. Wrapping it cost the portfolio a CI run
  that read ``RuntimeError: Upstream unreachable after retries:`` and stopped
  at the colon: ``httpx.ConnectTimeout``, ``ReadTimeout`` and ``ConnectError``
  carry an EMPTY ``str()``, and they are the only errors a real outage
  produces. A wrapper that must exist has to name the type and the host.

Usage:

    import httpx
    from .retry import fetch_with_retry

    async def fetch_dump(http: httpx.AsyncClient, url: str) -> bytes:
        resp = await fetch_with_retry(http, url)
        return resp.content
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

# --- Retry policy -----------------------------------------------------------
# Three questions: *what* is retried, *how fast*, and *how long*. The first is
# settled in `fetch_with_retry` (4xx except 429 fails fast); these settle the
# other two.

MAX_ATTEMPTS = 4
BASE_DELAY_SECONDS = 2.0  # ladder before jitter: 2, 4, 8

# Ceiling on the WHOLE call — every attempt and every wait together.
#
# An attempt count is not a bound: four attempts against an upstream that takes
# 30s to time out is two minutes inside one tool call, and `max_attempts = 4`
# never says so. Worse, the limit that matters is not ours — the caller has its
# own timeout, and past it nobody is listening: the work continues, the load
# lands on the source, and the result goes nowhere.
#
# The anchor is measured, not guessed: the Python MCP SDK ships
# `MCP_DEFAULT_TIMEOUT = 30.0` for general operations
# (`mcp/shared/_httpx_utils.py`). 25s leaves headroom for MCP framing, parsing
# and the tool layer above the fetch.
#
# The trade-off is deliberate: a slow first attempt can consume the budget and
# leave no room for a retry. That is the intended answer — a retry that
# finishes after the caller gave up buys nothing and costs the source a
# request.
TOTAL_BUDGET_SECONDS = 25.0

# Ceiling for a single wait. Guards two things at once: an exponential ladder
# that would otherwise grow without bound, and a `Retry-After` the source is
# entitled to send but we are not obliged to sit through.
MAX_DELAY_SECONDS = 20.0

# Jitter spread. Without it every client that hit the same outage retries in
# lockstep and the load returns as a wave exactly when the source recovers —
# the retry storm extends the outage it was meant to bridge. Eleven servers
# behind one upstream, all retrying at exactly 2s / 4s / 8s, is what the
# 2026-08-03 sweep found.
JITTER_SPREAD = 0.5  # exponential delays land in [0.5x, 1.5x]

# Applied on top of a `Retry-After`, and deliberately one-sided: the source
# told us when to come back, so coming back *later* is fine and coming back
# *earlier* is not.
RETRY_AFTER_JITTER = 0.25  # lands in [1.0x, 1.25x]

# Statuses that carry a meaningful `Retry-After` (RFC 9110 §10.2.3). A 429 or a
# 503 is the source answering the very question the backoff curve is guessing
# at. Reading the header on anything else means honouring a number that was
# never about waiting.
RETRY_AFTER_STATUSES = frozenset({429, 503})


class UpstreamUnavailableError(Exception):
    """No request was attempted — the budget was gone before the first try.

    Deliberately a named type and not ``RuntimeError``: a caller can branch on
    this, and cannot tell a bare ``RuntimeError`` apart from a bug in the
    server's own code. It is raised only when there is no upstream exception to
    re-raise; whenever there is one, the original travels out untouched.
    """


def parse_retry_after(resp: httpx.Response | None) -> float | None:
    """Seconds to wait per the response's ``Retry-After``, or ``None``.

    RFC 9110 §10.2.3 allows two forms — delta-seconds (``120``) and an
    HTTP-date (``Wed, 21 Oct 2026 07:28:00 GMT``). Both appear in the wild, so
    both are read. Anything unparseable yields ``None`` and the caller falls
    back to its own curve: a malformed header must not become a crash on the
    error path, which is the one path that is already going badly.
    """
    if resp is None or resp.status_code not in RETRY_AFTER_STATUSES:
        return None
    # Lower-case on purpose: httpx header lookup is case-insensitive, and the
    # wire spelling varies by server.
    raw = (resp.headers.get("retry-after") or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return float(raw)
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:  # RFC 9110 dates are GMT; a naive one means UTC
        when = when.replace(tzinfo=UTC)
    # Never negative: a date in the past means "now".
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def compute_delay(
    attempt: int,
    last_error: Exception | None,
    *,
    base_delay: float = BASE_DELAY_SECONDS,
) -> float:
    """Seconds to wait before ``attempt`` (1-based for the first retry).

    The source's own answer beats our guess: a ``Retry-After`` on a 429 or 503
    wins over the exponential curve. Everything is spread and then capped.

    The ``min(...)`` wraps the jitter rather than the other way round, and that
    ordering is the whole point. ``min(cap, base) * jitter`` and
    ``min(cap, base * jitter)`` both contain a cap and a jitter; only the
    second is bounded. The first shipped in six servers, where a value capped
    at 20s was then multiplied by up to 1.5 and landed at 30s — the constant
    claimed a ceiling it did not hold.
    """
    hinted = parse_retry_after(getattr(last_error, "response", None))
    if hinted is not None:
        return min(
            hinted * (1.0 + random.random() * RETRY_AFTER_JITTER),
            MAX_DELAY_SECONDS,
        )
    return min(
        base_delay
        * 2 ** (attempt - 1)
        * (1.0 - JITTER_SPREAD + random.random() * 2 * JITTER_SPREAD),
        MAX_DELAY_SECONDS,
    )


async def fetch_with_retry(
    http: httpx.AsyncClient,
    url: str,
    *,
    max_attempts: int = MAX_ATTEMPTS,
    base_delay: float = BASE_DELAY_SECONDS,
    total_budget: float = TOTAL_BUDGET_SECONDS,
    method: str = "GET",
    **request_kwargs,
) -> httpx.Response:
    """Fetch a URL with jittered backoff, ``Retry-After`` and a time budget.

    Retries on: 5xx responses, 429 Too Many Requests, and network errors
    (``httpx.RequestError`` subclasses).
    Fails fast on: other 4xx responses.

    Args:
        http: Shared httpx.AsyncClient.
        url: Target URL.
        max_attempts: 1 initial + (N-1) retries. Default 4 = up to 3 retries.
        base_delay: Seconds for the first retry wait, before jitter.
        total_budget: Wall-clock ceiling for the whole call, in seconds. This
            is the real bound; ``max_attempts`` only bounds the count.
        method: HTTP verb.
        **request_kwargs: Forwarded to ``http.request()``.

    Raises:
        The last upstream exception, unwrapped — ``httpx.HTTPStatusError``,
        ``httpx.RequestError`` or ``TimeoutError``. Callers branch on the type
        and read ``.response`` where it exists; a wrapper takes both away, and
        for the three errors an outage actually produces (``ConnectTimeout``,
        ``ReadTimeout``, ``ConnectError``) it also interpolates an empty
        ``str()``.
        UpstreamUnavailableError if the budget was spent before any request
        went out — the one case with no original exception to re-raise.
    """
    deadline = time.monotonic() + total_budget
    last_error: Exception | None = None
    attempts = 0

    for attempt in range(max_attempts):
        if attempt > 0:
            delay = compute_delay(attempt, last_error, base_delay=base_delay)
            # A wait that outlasts the budget is a wait for nobody: the caller
            # has given up by the time it ends. Stop instead of sleeping.
            if delay >= deadline - time.monotonic():
                break
            logger.warning(
                "Fetch attempt %d for %s failed (%s); waiting %.1fs",
                attempt,
                url,
                type(last_error).__name__ if last_error else "?",
                delay,
            )
            await asyncio.sleep(delay)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        attempts += 1
        try:
            # httpx bounds each operation (connect/read/write/pool) and its
            # read timeout restarts with every chunk — that bounds each step,
            # not the call, so a slowly trickling response can outlast the
            # budget without a single read expiring. `asyncio.timeout` is the
            # wall-clock deadline the budget actually promises; any httpx
            # timeout stays alongside it as the finer per-operation bound.
            async with asyncio.timeout(remaining):
                resp = await http.request(method, url, **request_kwargs)
                resp.raise_for_status()
                return resp
        except TimeoutError as exc:  # the budget is gone, not just this try
            last_error = exc
            break
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status = exc.response.status_code
            # 4xx except 429 is not retryable.
            if 400 <= status < 500 and status != 429:
                raise
        except httpx.RequestError as exc:
            last_error = exc  # Network/timeout: retry.

    host = urlsplit(url).hostname
    if last_error is None:
        # Budget gone before a single request went out. Nothing to re-raise,
        # so this is the one place that constructs its own error.
        raise UpstreamUnavailableError(
            f"no attempt made: the {total_budget:g}s budget was already "
            f"spent (host={host})"
        )

    # Logged, not wrapped. The diagnosis the old `RuntimeError` was reaching
    # for — type, host, and which of the two limits ran out — belongs in the
    # log, where it costs the caller nothing. `str(last_error)` is empty for
    # exactly the errors an outage produces, so the type is what carries it.
    why = (
        f"all {max_attempts} attempts used"
        if attempts >= max_attempts
        else f"{total_budget:g}s budget spent"
    )
    logger.warning(
        "Upstream unreachable after %d attempt(s), %s: %s: %s (host=%s)",
        attempts,
        why,
        type(last_error).__name__,
        str(last_error) or "no further detail",
        host,
    )
    raise last_error
