"""Reference: retry with exponential backoff for upstream HTTP.

Drop this helper into any *-mcp client layer. It handles the common case:
transient 5xx and network errors get retried with 2s / 4s / 8s wait; 4xx
(except 429) fails fast.

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

import httpx

logger = logging.getLogger(__name__)


async def fetch_with_retry(
    http: httpx.AsyncClient,
    url: str,
    *,
    max_attempts: int = 4,
    base_delay: float = 2.0,
    method: str = "GET",
    **request_kwargs,
) -> httpx.Response:
    """Fetch a URL with exponential-backoff retry.

    Retries on: 5xx responses, 429 Too Many Requests, and network errors
    (httpx.RequestError subclasses).
    Fails fast on: other 4xx responses.

    Args:
        http: Shared httpx.AsyncClient.
        url: Target URL.
        max_attempts: 1 initial + (N-1) retries. Default 4 = up to 3 retries.
        base_delay: Seconds for the first retry wait. Default 2 → 2, 4, 8.
        method: HTTP verb.
        **request_kwargs: Forwarded to ``http.request()``.

    Raises:
        httpx.HTTPStatusError for non-retryable 4xx after the first attempt.
        RuntimeError if all attempts exhaust.
    """
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        if attempt > 0:
            wait = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "Fetch attempt %d for %s failed (%s); waiting %.1fs",
                attempt,
                url,
                type(last_error).__name__ if last_error else "?",
                wait,
            )
            await asyncio.sleep(wait)
        try:
            resp = await http.request(method, url, **request_kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status = exc.response.status_code
            # 4xx except 429 is not retryable.
            if 400 <= status < 500 and status != 429:
                raise
        except httpx.RequestError as exc:
            last_error = exc  # Network/timeout: retry.

    assert last_error is not None
    raise RuntimeError(
        f"Upstream {url} unreachable after {max_attempts} attempts: {last_error}"
    ) from last_error
