"""Copy-paste patterns for the fourteen transport-hardening rules (MCP SDK 2.x / ASGI / uvicorn).

Each block is self-contained and annotated with the rule it implements. Adapt the
names; keep the shape. The comments are deliberately verbose — they are the part
that survives into the target codebase and explains *why* to the next reader.

Rules 1-7 apply on BOTH spec baselines: bind, wiring, the inbound host allow-list
and the way you prove them hang off the transport, not off the lifecycle. Rules
8-12 apply on spec 2026-07-28, which removes the handshake and the session. The
two baselines coexist inside one process — a legacy `initialize` still caps at
2025-11-25 while the per-request envelope reaches 2026-07-28 — so a stateless
fault is invisible to every client that stayed on the old era.

SCOPE IS DECIDED BY WHERE A LINE SITS, NOT BY THE TRANSPORT IT RUNS. Everything
ahead of the transport branch — imports, settings assignments, the lifespan, the
readiness marker — runs under every transport, stdio included. Rule 1 broke a
published server under stdio for months (zh-education-mcp 0.2.4) precisely
because the assignment stood before `mcp.run(...)`. Only rules 2-4 and 9 need a
network transport; rule 14 is the one where stdio is the MAIN case.

`get_settings()`, `mcp` and the concrete settings fields stand in for whatever the
target project already calls them. Likewise the `settings` and `tool` fixtures in
the test section: supply them from the project's own `conftest.py`. The `client`
fixture *is* defined here, because how it is built is itself one of the rules.

What must not be adapted away is the shape: the bind travels as an argument, one
policy object reaches every path that builds an app, and every control is
removable in a test.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from collections.abc import Sequence
from contextlib import asynccontextmanager
from typing import Any

import pytest
import uvicorn

# Rule 1(a) — the mechanical half of the major bump. Under 1.x this read
#   from mcp.server.fastmcp import FastMCP
# The import error points at every site, so search-and-replace finishes the job.
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# NOT part of this migration, and the most expensive thing to get wrong here:
#
#   `fastmcp` (the standalone PyPI package) is a DIFFERENT PROJECT from
#   `mcp.server.fastmcp` (the module that used to live in the official SDK).
#
#   from fastmcp import FastMCP          <- still valid, leave it alone
#   from mcp.server.fastmcp import FastMCP   <- this one moved
#
# Two projects, one name. Renaming the first because of the second breaks
# working code.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Rule 1, the dependency half — a bound only bites once the lock is re-resolved.
#
#   dependencies = ["mcp[cli]>=2.0.0,<3"]     # pyproject.toml
#
# That line says what SHOULD hold. What gets installed is whatever the lock
# says, so both files move in the same commit:
#
#   uv lock && git add uv.lock
#
# `uv sync` does re-resolve on its own when pyproject moved — but the paths that
# matter do not: `--frozen`, an environment that already exists, a container
# image built from the committed lock. The bound then reads correctly in review
# and has no effect in the process.
#
# The Nachweis is a measurement, not a reading. Run the install path CI runs,
# then:
#
#   python -c "from importlib.metadata import version; print(version('mcp'))"
#
# Old version printed => the lock was not carried along, the bound is decoration.
# ---------------------------------------------------------------------------

log = logging.getLogger(__name__)

mcp = MCPServer("example")

# Binds from which the SDK can derive a meaningful allow-list by itself.
# 0.0.0.0 is deliberately absent: it is the wildcard bind, which is exactly the
# case where the reachable name is unknown inside the process.
_LOOPBACK_BINDS = frozenset({"127.0.0.1", "::1", "localhost"})


# ---------------------------------------------------------------------------
# Rule 1(b) — the bind travels as kwargs; mcp.settings is read-only in 2.x
# ---------------------------------------------------------------------------


def serve(settings: Any) -> None:
    """Start the server.

    Under 1.x, assigning to the settings was the only way to place the bind:

        mcp.settings.host = settings.host       # 1.x
        mcp.settings.port = settings.port
        mcp.run(transport=settings.transport)

    Under 2.x that same assignment raises

        ValueError: "Settings" object has no field "host"

    and a read raises AttributeError. Measured, not assumed. A server that still
    carries those lines does not start **at all** — under ANY transport, not just
    HTTP. Note where the assignment sat: one line ABOVE the branch below, so it
    throws before anything has decided whether this process speaks stdio or HTTP.
    zh-education-mcp 0.2.4, measured against the artifact installed from PyPI in
    an empty venv, died exactly there with transport="stdio", and stayed broken on
    the index for months because nothing ever started the installed artifact.

    So the Nachweis is not only a test. It is also six seconds of measurement,
    and it needs no HTTP, no port and no client:

        # stdin closed = no request possible = whatever lands on stderr is the
        # server talking about itself. exit=124 means it was still standing.
        timeout 6 uv run --no-project --with '<dist>==<version>' \\
          <console-script> </dev/null >/tmp/out.txt 2>/tmp/err.txt
        echo "exit=$?"

    Any exit code other than 124 means it terminated. Whether a MARKER line shows
    up in that same window is rule 14; here only the standing process is at stake.
    """
    if settings.transport == "stdio":
        mcp.run(transport="stdio")
        return
    serve_http(settings)


# ---------------------------------------------------------------------------
# Rule 1(c) — annotations are read in snake_case; the wire format is unchanged
# ---------------------------------------------------------------------------


def is_read_only(tool: Any) -> bool:
    """Read a tool annotation under 2.x.

    `tool.annotations.readOnlyHint` is not an error under 2.x — it is silently
    None, which is the whole problem: a permission check written that way stops
    being a check and nothing says so.

    The wire format is UNCHANGED. camelCase survives as a pydantic alias, so a
    serialised annotation still carries `readOnlyHint` and every client keeps
    working. Only Python-side attribute access moved. Two consequences worth
    stating out loud:

      * a test catches this, never a client — there is no observable protocol
        difference to catch;
      * TypeScript servers stay on camelCase. "Fixing" a Node server because of
        this rule breaks working code.
    """
    return bool(getattr(tool.annotations, "read_only_hint", False))


def test_wire_format_is_unchanged(tool: Any) -> None:
    """The Nachweis for 1(c): serialise both spellings and compare.

    If the alias still produces the camelCase key, the migration is a read-side
    concern only and no client contract is at stake.
    """
    dumped = tool.annotations.model_dump(by_alias=True)
    assert "readOnlyHint" in dumped, (
        "alias lost — this IS a wire change, stop and re-read"
    )
    assert "read_only_hint" not in dumped


# ---------------------------------------------------------------------------
# Rule 4 — the inbound allow-list, built in one place
# ---------------------------------------------------------------------------


def build_transport_security(
    *,
    host: str,
    port: int,
    allowed_hosts: Sequence[str] = (),
    cors_origins: Sequence[str] = (),
) -> TransportSecuritySettings | None:
    """Return the inbound Host/Origin policy, or None to leave it off.

    This is the control that answers inbound DNS rebinding: a page in the
    operator's network resolves its own hostname to this server's address and
    then talks to it from the browser. CORS cannot help — from the browser's
    point of view the request is same-origin. A token cannot help — the
    attacking page runs in a context that already holds one. An egress
    allow-list is the other direction entirely.

    Four properties, each with a reason:

      * port-exact — entries are compared literally, so an entry carries its port
      * loopback always present — container health checks probe 127.0.0.1
      * configured CORS origins folded in — otherwise the transport rejects
        exactly the browser clients CORS was opened for
      * no `*` — origins are compared literally, so a star matches nobody and
        only creates the impression of an open list
    """
    loopback = [f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"]

    if not allowed_hosts:
        if host in _LOOPBACK_BINDS:
            # The SDK would derive this same list from the bind. Passing it
            # explicitly changes nothing at runtime and everything in review:
            # the control is visible at the call site instead of implied.
            return TransportSecuritySettings(
                allowed_hosts=loopback,
                allowed_origins=_origins(cors_origins),
            )

        # Non-loopback bind, nothing configured: fail OPEN — but visibly.
        #
        # Guessing is worse than failing open. On 0.0.0.0 the reachable name is
        # unknown inside the process, and a guessed entry rejects precisely the
        # deployment the list exists to protect: the same HTTP 421 as rule 2,
        # only self-inflicted. So: no protection, and a warning that says so.
        log.warning(
            "transport.host_allowlist_disabled bind=%s — set MCP_ALLOWED_HOSTS "
            "to enforce an inbound Host/Origin allow-list on this deployment",
            host,
        )
        return None

    return TransportSecuritySettings(
        allowed_hosts=[*loopback, *allowed_hosts],
        allowed_origins=_origins(cors_origins),
    )


def _origins(cors_origins: Sequence[str]) -> list[str]:
    """Origins the transport accepts, derived from the CORS configuration.

    Dropping `*` is not a simplification: origins are compared literally, so a
    star would be a literal entry matching nothing. Silently keeping it would
    look like an open list while behaving like an empty one.
    """
    return [o for o in cors_origins if o != "*"]


# ---------------------------------------------------------------------------
# Rules 2 + 3 — one policy object, and every path that builds an app gets it
# ---------------------------------------------------------------------------


def build_http_app(settings: Any, *, transport_security: Any = None) -> Any:
    """Build the ASGI app. Never constructs the policy itself — it receives it.

    Rule 3 lives in that distinction. If each path built its own policy, the two
    would drift; if only one path built one, arming a security control would
    depend on unrelated configuration.
    """
    return mcp.create_http_app(
        host=settings.host,
        port=settings.port,  # rule 3: the port travels WITH the host.
        transport_security=transport_security,
    )


def create_http_app() -> Any:
    """ASGI factory for `uvicorn module:create_http_app --factory`.

    uvicorn calls a factory with NO arguments. `--host` configures uvicorn's own
    listener and never reaches this function. The bind therefore has to be read
    here, from the same configuration `main()` uses — otherwise the app keeps the
    `host` default of 127.0.0.1 while the process listens on 0.0.0.0, and the SDK
    answers every request under a real hostname with HTTP 421.

    This is why MCP_HOST / MCP_PORT are NOT redundant next to --host / --port.
    Say so in the README: it is invisible in the code, it looks like duplication,
    and it has already cost one real deployment.
    """
    settings = get_settings()
    return build_http_app(settings, transport_security=_policy_for(settings))


def _policy_for(settings: Any) -> Any:
    """Single source for the policy, shared by every entry point below."""
    return build_transport_security(
        host=settings.host,
        port=settings.port,
        allowed_hosts=settings.allowed_hosts,
        cors_origins=settings.cors_origins,
    )


def serve_http(settings: Any) -> None:
    """Every branch that can serve HTTP is wired from the same policy.

    Three paths showed up across the three repositories this came from: a custom
    builder reached only when auth or CORS happened to be configured, the
    SDK-served `run()` path, and a deprecated SSE path alongside. Wire one and
    leave the others, and whether the allow-list is armed comes down to whether
    somebody set an unrelated environment variable.
    """
    policy = _policy_for(settings)

    if settings.transport == "sse":
        # Deprecated, still reachable — and therefore still in scope.
        uvicorn.run(
            mcp.create_sse_app(
                host=settings.host,
                port=settings.port,
                transport_security=policy,
            ),
            host=settings.host,
            port=settings.port,
        )
        return

    if settings.auth_token or settings.cors_origins:
        uvicorn.run(
            build_http_app(settings, transport_security=policy),
            host=settings.host,
            port=settings.port,
        )
        return

    mcp.run(
        transport="streamable-http",
        host=settings.host,
        port=settings.port,
        transport_security=policy,
    )


# ---------------------------------------------------------------------------
# Rules 5-7 — the tests, and the ways they lie
#
# Rule 6's mutation table, as it belongs in the PR. A row with zero red tests is
# a finding, not a footnote: either the test is missing, or the control does
# nothing — or the mutation never landed, which is the possibility to rule out
# first, because it produces the same zero:
#
#   sed -i 's/transport_security=policy//' src/server.py
#   git diff --exit-code src/server.py && { echo "no-op mutation"; exit 1; }
#   pytest
#
# `git diff --exit-code` exits 0 when NOTHING changed, so the && branch is the
# error case. The way this bit: the literal being replaced fell across a line
# break in wrapped text, the file never changed, and the green suite read as a
# surviving mutant.
#
# Restore between mutations from a copy of the working tree, not with
# `git checkout --` — that restores HEAD and silently discards every
# uncommitted edit in the same file, which is a bigger no-op than the one above.
#
#   | mutation                                        | failing tests |
#   |-------------------------------------------------|---------------|
#   | transport_security dropped from build_http_app   |             4 |
#   | transport_security dropped from mcp.run()        |             2 |
#   | transport_security dropped from the SSE app      |             1 |
#   | allow-list not port-exact                        |             3 |
#   | port not passed on to the app builder            |             1 |
# ---------------------------------------------------------------------------

# --- Rule 7(a): the harness, because everything below depends on it ---------


@pytest.fixture
def client(settings: Any) -> Any:
    """Drive the app through its lifespan.

    Deliberately NOT this:

        transport = httpx.ASGITransport(app=build_http_app(settings))
        client = httpx.AsyncClient(transport=transport, base_url="http://test")

    Streamable HTTP builds its transport manager in the app LIFESPAN, and
    `ASGITransport` never runs a lifespan. Every request then comes back 500 —
    including the ones that should be 421, which makes a broken allow-list and a
    working one look identical. Reading that 500 as a finding costs an afternoon
    in the wrong file.

    This is unaffected by the 2026-07-28 baseline: what that revision removes is
    the PROTOCOL session, not the construction of the app.

    `TestClient` used as a context manager runs startup and shutdown.
    """
    app = build_http_app(settings, transport_security=_policy_for(settings))
    with TestClient(app) as test_client:
        yield test_client


# --- Rule 5: a negative test needs its positive twin ------------------------
#
# Not written here, on purpose:
#
#     def test_foreign_host_is_rejected(client):
#         assert client.get("/mcp", headers={"Host": "evil.example.com:8000"}) \
#             .status_code == 421
#
# That one is green in three different states — correct list, loopback fallback,
# and a list that matches the hostname while ignoring the port. A test that
# cannot tell those apart reports on the environment, not on the code.


def test_right_host_right_port_is_accepted(client: Any) -> None:
    """The positive twin. Without it, "rejected" cannot be told from "everything
    is rejected".

    This is also the test that catches the loopback fallback: under it the
    server answers 421 to its own documented hostname, and this goes red while
    every negative test stays green.
    """
    resp = client.get("/mcp", headers={"Host": "mcp.example.ch:8000"})
    assert resp.status_code != 421


def test_right_host_wrong_port_is_rejected(client: Any) -> None:
    """Rule 5: a negative test must fail for YOUR reason, not a default's.

    `evil.example.com` is refused in every state — by the correct list, by a
    policy that has fallen back to loopback, and by a list that matches on
    hostname while ignoring the port. Three states, one green test, no
    information.

    Right hostname with the wrong port separates them: a port-exact list
    refuses, a hostname-only list lets it through. Together with the positive
    twin above, the pair pins the state down.
    """
    resp = client.get("/mcp", headers={"Host": "mcp.example.ch:9999"})
    assert resp.status_code == 421


def test_valid_token_does_not_save_a_foreign_host(client: Any) -> None:
    """Rule 4, stated as a test: the two controls answer different questions.

    The second reason this request could fail is a missing or wrong token — so
    the token is supplied and valid. What is left as the only possible cause of
    the 421 is the Host check, which is the point of the test (rule 5).
    """
    resp = client.get(
        "/mcp",
        headers={"Host": "evil.example.com:8000", "Authorization": "Bearer s3cr3t"},
    )
    assert resp.status_code == 421


# --- Rule 6: the test that voids itself -------------------------------------


def test_real_hostname_is_accepted(client: Any, monkeypatch: Any) -> None:
    """Rule 6: the load-bearing test, and the one that is easiest to void.

    The first version of this test set MCP_ALLOWED_HOSTS itself and therefore
    PASSED with the `host` kwarg mutated away: given an explicit allow-list the
    kwarg is irrelevant. It only becomes load-bearing when the SDK has to derive
    the list from the bind, so the environment variable must be absent here.

    A test that establishes the condition under which the fault cannot occur
    checks nothing.
    """
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    resp = client.get("/mcp", headers={"Host": "mcp.example.ch:8000"})
    assert resp.status_code != 421


# --- Rule 7(b): keep the patch level consistent -----------------------------


def _patch_run(monkeypatch: Any) -> list[dict]:
    """Record the kwargs `mcp.run` was called with, patching the INSTANCE.

    The level matters, and mixing levels is what hangs a suite. `monkeypatch`
    remembers the value it read — and when it reads a CLASS attribute through an
    INSTANCE, the rollback writes that value back ONTO THE INSTANCE. `mcp.run`
    then stays shadowed for the rest of the session: a later class-level patch
    has no effect, and real uvicorn starts in the middle of an unrelated test.

    Symptom to recognise: the test passes on its own and hangs the suite.

    So pick the level the repository already uses — the instance, here — and use
    it everywhere.
    """
    calls: list[dict] = []
    monkeypatch.setattr(mcp, "run", lambda **kw: calls.append(kw))
    return calls


# --- Rule 7(c): every branch test claims its branch --------------------------


def test_the_sdk_served_path_gets_the_allowlist_too(
    settings: Any, monkeypatch: Any
) -> None:
    """Assert WHICH branch ran, so taking the wrong one fails instead of hanging."""
    calls = _patch_run(monkeypatch)
    settings.transport = "streamable-http"
    settings.auth_token = None
    settings.cors_origins = []

    serve_http(settings)

    assert len(calls) == 1, (
        "the custom-builder branch ran — this test asserts the run() branch"
    )
    assert calls[0]["transport_security"] is not None


def test_the_custom_builder_path_gets_the_allowlist_too(
    settings: Any, monkeypatch: Any
) -> None:
    """The twin of the test above. Both branches, both claiming their branch.

    Without the pair, a change that routes everything through one branch leaves
    the other silently untested — and the mutation that drops the policy from it
    stays green.
    """
    calls = _patch_run(monkeypatch)
    served: list[Any] = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: served.append(app))
    settings.transport = "streamable-http"
    settings.auth_token = "t"  # forces the custom-builder branch

    serve_http(settings)

    assert not calls, (
        "the run() branch ran — this test asserts the custom-builder branch"
    )
    assert len(served) == 1


def test_the_sse_path_is_wired(settings: Any, monkeypatch: Any) -> None:
    """Check the wiring exactly where an end-to-end test would hang.

    The rejection semantics are deliberately NOT asserted here. Without the
    allow-list an SSE GET under a foreign host is *allowed* and opens an endless
    event stream, so the end-to-end negative test does not go red — it hangs, and
    a hang gets written off as a flake.

    So: this asserts that the SSE app is built WITH the policy, and the rejection
    behaviour itself is proven end-to-end over Streamable HTTP. Both transports
    pass through the same transport-security layer, so one end-to-end proof plus
    one wiring assertion covers both without a test that can hang.
    """
    built: list[dict] = []
    monkeypatch.setattr(
        mcp, "create_sse_app", lambda **kw: built.append(kw) or object()
    )
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: None)
    settings.transport = "sse"

    serve_http(settings)

    assert len(built) == 1
    assert built[0]["transport_security"] is not None
    assert built[0]["port"] == settings.port  # rule 3: the port travels too


# --- Rule 7(d): a fixture must not reach into a foreign module ---------------

# The production side of the pattern. Aliasing the call once, at module level, is
# what lets a fixture skip the wait without touching `asyncio` itself. The alias
# has to be used at EVERY call site: leave one `await asyncio.sleep(...)` in
# place and the fixture patches past it — the same no-op as a mutation that
# misses its target (rule 6).
_sleep = asyncio.sleep


async def poll_until_ready(deadline_s: float, delay_s: float = 0.05) -> None:
    """Stand-in for any production loop that waits. Note `_sleep`, not `asyncio.sleep`."""
    waited = 0.0
    while waited < deadline_s:
        await _sleep(delay_s)
        waited += delay_s


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: Any) -> None:
    """Skip the WAIT, keep the HANDOVER — and patch a name this repository owns.

    Two independent mistakes live in the one-liner this replaces:

        monkeypatch.setattr(server.asyncio, "sleep", _instant)

    (1) WRONG TARGET. It reads as a local handle on `server`, but `server.asyncio`
    IS the module `asyncio` — the same object every other import in the process
    holds. With `autouse=True` that reaches every test in the suite, including
    the ones that never asked for it. Rule 7(b) is about the LEVEL of a patch;
    this is about its TARGET: who owns the name it points at.

    (2) WRONG REPLACEMENT. An `async def` that returns without awaiting anything
    never suspends. `asyncio.sleep(0)` is the standard way to hand the event loop
    the word, so a replacement that drops the await removes the point at which
    another coroutine gets to run. A concurrency test built on it then asserts
    interleaving over a run that has none.

    That is the trap without a symptom. Ours went red — but only because it
    claimed the interleaving directly. Had it checked concurrency indirectly, via
    a counter, an ordering or a result, it would have stayed green and secured
    nothing. It is also the case rule 6 cannot catch on its own: the mutation
    lands, and the test that should have caught it lost its subject to the
    fixture first.

    Proof, and it is rule 6 applied to the fixture itself: swap `_instant` for a
    version without the `await`. If no test loses its assertion, no test was
    checking the concurrency it claims. Alongside that, a grep — a `setattr`
    whose target is an imported foreign module is a finding on sight:

        grep -rnE 'setattr\\(\\s*([A-Za-z_][A-Za-z0-9_.]*\\.)?(asyncio|time|socket|os|random|subprocess)\\s*,' tests/
    """

    async def _instant(_delay: float) -> None:
        await asyncio.sleep(0)  # duration gone, handover to the loop kept

    # In a real repository this is the module under test:
    #     monkeypatch.setattr(server, "_sleep", _instant)
    monkeypatch.setattr(sys.modules[__name__], "_sleep", _instant)


# NOTE ON RUNNING THE SUITE (rule 7): run it under a timeout
# (`pytest --timeout=30`). That turns every hang into a failure with a stack
# trace, which is the difference between a named finding and "the suite is
# flaky again".
#
# And run each branch test alone AND in the full suite. The instance-patch trap
# in `_patch_run` only ever shows up in the second — passing alone is precisely
# the symptom.
#
# Then read the autouse fixtures once, from the point of view of a test that did
# NOT ask for them. That is where 7(d) lives: a fixture that is right for the
# three tests it was written for and quietly defuses the fourth.


# ===========================================================================
# Rules 8-12 — the stateless world of spec 2026-07-28
#
# Everything above survives the revision unchanged. What follows is what the
# revision adds: no handshake, no session, two mandatory headers, a dated end
# for the legacy transport, a request that runs more than once, and an auth
# layer this portfolio records a NEGATIVE FINDING against rather than omitting.
#
# The proof rules 5-7 are not superseded here, they are applied. Every Nachweis
# below names the mutation it goes red under, and every negative test below has
# a second reason it could have been green — which is the reason it is written
# the way it is.
# ===========================================================================


# --- Rule 8: without a session, state is shared silently ---------------------
#
# NOT written here, on purpose — this is the shape the rule exists against:
#
#     _CURSORS: dict[str, int] = {}      # was: per session. Now: per PROCESS.
#
#     @mcp.tool()
#     async def next_page() -> str:
#         offset = _CURSORS.get("current", 0)   # every caller reads the same key
#         _CURSORS["current"] = offset + 50
#         return await fetch(offset)
#
# This does not raise. With one caller it is indistinguishable from correct;
# with two it is a data leak between callers that produces no error at all.

_HANDLE_TTL_SECONDS = 900


def mint_handle(payload: dict, *, now: float) -> str:
    """Return an opaque, server-minted, expiring handle for cross-call state.

    Three words in the spec carry the load, and each maps to one property here:

      * EXPLICIT       — the handle appears in the tool's schema, so a model
                         sees it. It is not an ambient value.
      * SERVER-MINTED  — the server produces it; the client does not invent one.
                         A handle spelled `cursor=42` is a guessable reference
                         to somebody else's state. Removing the session without
                         this property does not remove the attack surface, it
                         moves it into the tool signature — where no auth layer
                         looks at it any more.
      * ORDINARY ARG   — it travels in the arguments, not in a header and not in
                         a table kept beside the request.

    The expiry is the quiet half. A session used to be cleaned up when the
    connection dropped; without a session there is no event left that cleans up
    anything, so a dict of handles is a leak that shows up in days rather than
    in seconds — long after any test suite has finished.
    """
    body = {**payload, "exp": now + _HANDLE_TTL_SECONDS}
    return _sign(body)  # opaque to the caller, verifiable by this server


def decode_handle(handle: str | None, *, now: float) -> dict:
    """Verify signature and expiry, or reject. Never trust an unsigned handle."""
    if handle is None:
        return {}
    body = _verify(handle)  # raises on a forged or tampered handle
    if body["exp"] < now:
        raise ValueError("handle expired — mint a new one, do not extend this")
    return body


async def server_discover() -> dict:
    """`server/discover` — a MUST for servers, a MAY for clients.

    That asymmetry is the whole trap. Because no client is obliged to call it, a
    server without it looks perfectly healthy in day-to-day use: tools run, calls
    arrive, nothing is red. It surfaces when a client wants to select a version —
    or on stdio, where the RPC doubles as the backwards-compatibility probe. The
    client then gets "method not found" and cannot tell an old server from a new
    one with a hole in it.

    A missing `server/discover` is therefore not a missing feature. It is a false
    statement about your own protocol version.
    """
    return {
        "protocolVersions": ["2026-07-28"],
        "serverInfo": {"name": "example", "version": "2.0.0"},
        "capabilities": {"tools": {}},
    }


def test_two_callers_do_not_share_state(client: Any) -> None:
    """Rule 8's Nachweis, and rule 5 applied to it.

    The mutation is: drop the handle argument and fall back to the process-local
    bucket. Under that mutation a ONE-caller test stays green — it never
    establishes the condition under which the fault can appear, which is exactly
    the defect rule 6 names. Only a test with TWO independent callers goes red.

    "Independent" means no shared connection context: two separate requests, in
    the stateless era the only thing they may have in common is what they pass in
    their arguments.
    """
    first = client.post("/mcp", json=_call("next_page", {}))
    second = client.post("/mcp", json=_call("next_page", {}))
    assert first.json()["result"] == second.json()["result"], (
        "the second caller saw the first caller's cursor — process-local state "
        "that used to be addressed per session now lands in one bucket"
    )


def test_expired_handle_is_rejected() -> None:
    """State without an end is the second, quieter half of rule 8."""
    handle = mint_handle({"offset": 50}, now=0.0)
    with pytest.raises(ValueError):
        decode_handle(handle, now=_HANDLE_TTL_SECONDS + 1)


# --- Rule 9: the address is on the outside of the envelope now ---------------


def require_matching_headers(request: Any, body: dict) -> None:
    """Compare `Mcp-Method` / `Mcp-Name` against the body, server-side.

    The headers exist so that a layer which does not parse the body can still
    tell what is passing through: a gateway allow-listing one tool, a rate
    limiter with per-tool budgets, a log path counting methods.

    And that is precisely where the attack comes from. If an intermediary rules
    on the header while the server rules on the body, two parties have ruled on
    two different requests: `Mcp-Name: search_datasets` in the header,
    `delete_record` in the body — the gateway permits, the server executes.
    Comparing them is therefore a SECURITY BOUNDARY, and it has to happen here,
    because this is the only place where both sides are present.

    The missing-header branch is the one most likely to be left out, and leaving
    it out is what disarms the control: a check that only runs when the headers
    are present is bypassed by omitting them. Same shape as the "present" clause
    in rule 12.
    """
    declared_method = request.headers.get("Mcp-Method")
    declared_name = request.headers.get("Mcp-Name")
    if declared_method is None or declared_name is None:
        raise HeaderMismatchError(-32020, "Mcp-Method/Mcp-Name required")
    if (declared_method, declared_name) != (body["method"], _addressed_name(body)):
        raise HeaderMismatchError(-32020, "header does not match body")


# Rule 9 also carries a documentation duty, the sibling of the MCP_HOST one in
# rule 2: the README must say WHICH header values the deployment routes and
# rate-limits on. A gateway allow-listing `Mcp-Name` is part of this server's
# security architecture and appears nowhere in this server's code. Undocumented,
# it is a control nobody maintains, because nobody knows it is there.


def test_header_body_mismatch_is_refused(client: Any) -> None:
    """Three cases, and the third is the one that gets forgotten."""
    ok = client.post(
        "/mcp",
        json=_call("search_datasets", {}),
        headers={"Mcp-Method": "tools/call", "Mcp-Name": "search_datasets"},
    )
    assert ok.status_code == 200, "the positive twin — rule 5"

    mismatch = client.post(
        "/mcp",
        json=_call("delete_record", {}),
        headers={"Mcp-Method": "tools/call", "Mcp-Name": "search_datasets"},
    )
    assert mismatch.json()["error"]["code"] == -32020

    # The omission case. Replace the comparison with plain logging and this is
    # the assertion that stays green if you only wrote the one above.
    absent = client.post("/mcp", json=_call("delete_record", {}))
    assert absent.json()["error"]["code"] == -32020


# --- Rule 10: legacy HTTP+SSE has a date ------------------------------------

# Deprecated since 2025-03-26, but only 2026-07-28 puts it under the feature
# lifecycle policy: formal state Deprecated, twelve-month window, earliest
# removal on the date below. A recommendation without a date produces no work
# item — it produces a compatibility path nobody switches off, because it
# bothers nobody. The same window applies to Roots, Sampling and Logging.
LEGACY_SSE_REMOVAL_EARLIEST = "2027-07-28"

# The detection recipe runs over THREE places, because each can be clean while
# another is not:
#
#   1. code       `create_sse_app`, `transport="sse"`, a mount on `/sse`, an
#                 `sse_app()` call. Grep the whole package, not just the server
#                 module.
#   2. start      what the platform actually launches: [project.scripts], a
#                 Procfile, CMD, the argv in the deployment. A branch present in
#                 code that nothing ever selects is a different situation from a
#                 branch the deployment picks — and the reverse happens too.
#   3. wire       a GET on the endpoint. If an event stream opens or an
#                 Mcp-Session-Id comes back, the path is live regardless of what
#                 the code suggests. Only this one is proof; 1 and 2 are
#                 indications.


def serve_http_with_dated_legacy_path(settings: Any) -> None:
    """Rule 10 on top of rule 3: while the path exists, it is wired like the rest.

    The legacy path is not neutral. It is a second network route with its own
    wiring, and the lesson of rule 3 is that the second route does not inherit
    the first one's hardening. A server enforcing the host allow-list (rule 4)
    and the header check (rule 9) on streamable-http while an SSE endpoint runs
    beside it has neither.
    """
    policy = _policy_for(settings)
    if settings.transport == "sse":
        log.warning(
            "transport.legacy_sse_selected removal_earliest=%s — migrate to "
            "streamable-http; this path speaks a protocol 2026-07-28 dropped",
            LEGACY_SSE_REMOVAL_EARLIEST,
        )
        uvicorn.run(
            mcp.create_sse_app(
                host=settings.host,
                port=settings.port,
                transport_security=policy,
            ),
            host=settings.host,
            port=settings.port,
        )
        return
    serve_http(settings)


def test_no_legacy_sse_app_is_built(settings: Any, monkeypatch: Any) -> None:
    """Make the ABSENCE provable instead of merely asserted.

    Applied and measured on zurich-opendata-mcp v0.7.0, all three places came
    back negative: no `create_sse_app` and no `transport="sse"` in the package, a
    single network path `mcp.run(transport="streamable-http", ...)`, and no
    deploy manifest in the repository that could start a second one. That is what
    a clean result looks like — the more useful half of the recipe, because
    somebody who only knows the positive case cannot tell when they are done.
    """
    built: list[Any] = []
    monkeypatch.setattr(mcp, "create_sse_app", lambda **kw: built.append(kw))
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: None)
    calls = _patch_run(monkeypatch)

    serve_http(settings)

    assert not built, "a legacy SSE app was built — see LEGACY_SSE_REMOVAL_EARLIEST"
    assert calls, "and this is the positive twin: the modern path did run (rule 5)"


# --- Rule 11: MRTR — the server answers, and the work runs more than once ----


async def submit_with_mrtr(params: Any) -> dict:
    """Answer with `input_required` instead of asking the client mid-request.

    Until 2025-11-25 a server could raise its own request in the middle of
    handling one: `roots/list`, `sampling/createMessage`, `elicitation/create`.
    2026-07-28 removes that outright. The server RESPONDS with
    `resultType: "input_required"` and an `inputRequests` field; the client
    obtains what is needed and REPEATS the original request with
    `inputResponses`; the server handles it again, now completely.

    The inversion is what makes it hard: a dialogue INSIDE one handling becomes a
    handling that RUNS FROM THE START AGAIN. Everything before the question point
    happens once per retry. A tool that creates something, then asks for
    confirmation, then starts over on retry, creates it twice — which moves this
    out of "user interface" and into "correctness".

    Two further consequences:

      * No held-open stream. The server answers and finishes. Holding the
        connection open while waiting for the client rebuilds the old model in
        exactly the form rule 7 describes: the fault shows up as a standing suite
        rather than a red test.
      * The retry may NEVER ARRIVE — a client is obliged to nothing. Whatever was
        reserved before the question point has to come back without a completion
        event, the same problem as a handle without an expiry in rule 8.
    """
    if params.confirm is None:
        return {
            "resultType": "input_required",
            "inputRequests": [_CONFIRM_REQUEST],
            # Correlation without a session: `elicitationId` and
            # notifications/elicitation/complete are gone, so a server that has
            # to recognise an out-of-band operation across retries encodes its
            # own identifier here. There is no other channel left. Same
            # properties as a handle in rule 8: server-minted, opaque, expiring.
            "requestState": mint_handle({"params": params.digest()}, now=_now()),
        }
    return await api.create(params, idempotency_key=_key_from(params.request_state))


async def test_the_retry_does_not_duplicate_the_effect(api_spy: Any) -> None:
    """Rule 11's Nachweis — and the second reason it could pass without meaning it.

    Run the retry FOR REAL: once without the input, once with `inputResponses`.
    Then assert on the EFFECT, not on the answer. A test that only checks the
    second call's return value is green even when the side effect happened twice,
    which is rule 5's question — "is there a second reason this passes?" — applied
    to a case that has nothing to do with the network.

    The mutation: remove the idempotency key. This test goes red; a single-call
    test stays green.
    """
    first = await submit_with_mrtr(_params(confirm=None))
    assert first["resultType"] == "input_required"

    await submit_with_mrtr(_params(confirm=True, request_state=first["requestState"]))

    assert api_spy.create_calls == 1, (
        "the effect ran twice — everything before the question point repeats on "
        "every retry, so it belongs behind the question point or behind a key"
    )


# --- Rule 12: auth hardening, and this portfolio's documented negative finding


def redeem_authorization_code(callback: Any, recorded: Any) -> Any:
    """Validate `iss` per RFC 9207 before redeeming, and key credentials by issuer.

    The attack is mix-up: a code issued by authorization server A is redirected
    to the callback belonging to server B and redeemed there with B's
    credentials. `state` does not catch it — the proxy set `state` itself, so it
    only says the round is ours, not who answered it.

    THE "PRESENT" CLAUSE IS THE TRAP. The obligation covers a PRESENT `iss`. A
    proxy that validates only when the parameter is there satisfies the letter
    and is attacked by leaving it out. What the authorization server can do is
    knowable — it is in its metadata — so the absent case is decidable, not a
    guess. Same shape as the missing header in rule 9.
    """
    if callback.state != recorded.state:
        raise AuthError("state mismatch")
    if callback.iss is None and recorded.metadata.iss_parameter_supported:
        raise AuthError("iss absent although this issuer advertises it")
    if callback.iss is not None and callback.iss != recorded.issuer:
        raise AuthError("iss mismatch — not issued by the recorded issuer")

    # The storage side of the same attack. Credentials MUST be keyed by issuer
    # identifier and MUST NOT be reused against a different authorization server;
    # a flat client_id/client_secret in configuration presents itself to every
    # server it talks to. Registration itself is CIMD now — the client publishes
    # its metadata at a URL and that URL IS the client_id. DCR remains only for
    # authorization servers that cannot do CIMD, and there `application_type`
    # has to be set, or OpenID Connect defaults to `web` and refuses a native
    # client's http://127.0.0.1 redirect URI.
    return CREDENTIALS_BY_ISSUER[recorded.issuer]


# THE NEGATIVE FINDING, WRITTEN OUT RATHER THAN LEFT OUT.
#
# For the Swiss Public Data portfolio rule 12 does NOT currently apply, for a
# nameable reason: the servers are read-only, carry `auth_model: none`, and
# redeem no authorization code. There is no redeeming party that could validate
# `iss`, and no persisted client credentials to key by issuer. The only inbound
# control is the host allow-list from rule 4.
#
# It is spelled out because an omitted section cannot be told apart from an
# overlooked one — the same logic rule 5 is made of. And the condition that
# lifts it is precise: the CIMD and issuer-binding obligation applies as soon as
# a server carries ANY auth model; the `iss` obligation as soon as it acts as an
# OAuth proxy. From the first credential onwards, rule 4's "a token only says
# WHO is asking" stops being the whole auth story.


def test_a_code_without_iss_is_refused(auth_client: Any) -> None:
    """Both negative tests need a CORRECT state, or they test the wrong control.

    With a wrong state the request is refused either way, and the test reports on
    `state` validation while claiming to report on `iss`. That is rule 5 in an
    OAuth flow: name the second reason, then remove it.

    The mutation: delete the `iss` checks. Both of these go red — and if only the
    mismatch one does, the omission case is untested.
    """
    recorded = _recorded_flow(iss_parameter_supported=True)

    with pytest.raises(AuthError):
        redeem_authorization_code(_callback(state=recorded.state, iss=None), recorded)

    with pytest.raises(AuthError):
        redeem_authorization_code(
            _callback(state=recorded.state, iss="https://evil.example.com"), recorded
        )

    # The positive twin, without which "refused" cannot be told from "everything
    # is refused".
    redeem_authorization_code(
        _callback(state=recorded.state, iss=recorded.issuer), recorded
    )


# ---------------------------------------------------------------------------
# Rule 13 — every test above holds from the merge commit onward, and only forward.
#
# Two sets sit outside a freshly merged guard, both showing green CI: the state
# already on main (never run against it) and every branch cut before the merge
# (merges without ever having run it).
#
# The mechanical part is the trigger — .github/workflows/*.yml:
#
#   on:
#     pull_request:
#     push:
#       branches: [main]     # <- so the guard also sees the state it never saw
#     workflow_dispatch:     # <- so it can be fired once by hand after merging
#
# The rest is not YAML. After merging a guard:
#
#   1. run it against main once and LOOK at the run — a green PR says nothing
#      about the branch the PR went into;
#   2. list the branches that do not know it yet, and pull them up to main:
#
#        git branch -r --no-contains <merge-sha>
#
#      While that list is non-empty the guard is introduced, not enforced.
#
# The Nachweis is rule 6 applied to the guard itself, on main rather than in the
# PR: create the violation it was written against and watch the run. If it does
# not go red, every green run so far was "did not run", not "passed".
# ---------------------------------------------------------------------------


# ===========================================================================
# Rule 14 — the server announces that it is listening
#
# Every server has a moment where it stops being a process and starts being a
# server: config read, clients built, tools registered, now waiting. From the
# outside both states look identical — a PID doing nothing. On stdio there is
# exactly one channel to tell them apart: stderr. stdout belongs to the protocol,
# an exit code arrives too late, and there is no port. This is the one rule where
# a stdio server is the MAIN case rather than the edge case.
#
# Survey (2026-08-03, 42 published servers): 15 say nothing of their own — 13 no
# output at all, 2 only the banner the SDK itself writes.
# ===========================================================================

# The marker is a CONTRACT, not prose. Changing this string changes an interface:
# the README and any monitoring that greps for it move in the same commit.
READY_MARKER = "server ready"


@asynccontextmanager
async def lifespan(_app: Any) -> Any:
    """Rule 14: everything that can fail sits BEFORE the marker.

    Four properties turn a log line into a marker, each of them measured:

    1. Structured log: the `event`/`msg` field is compared for EQUALITY. Not a
       prefix, not startswith, not "contains". openlex-mcp was documented with
       the marker "Lifespan gestartet" while the field actually read
       "Lifespan gestartet — geteilter HTTP-Client bereit". A prefix comparison
       would have matched, and would have broken the moment somebody rephrased
       the explanatory tail — which nobody reads as an interface change, because
       it looks like log text. Explanations go in their OWN fields.
    2. Plain text: a stable substring. An unstructured line carries logger name,
       level and formatting, so there is no field to compare exactly. The promise
       is then a piece of text the server deliberately keeps as its marker. That
       is weaker than (1) and is the price of unstructured logs — not a reason to
       soften (1).
    3. Never a timestamp, and nothing else that varies per run: no PID, no port,
       no duration, no config-dependent count. Timestamps in the log are correct
       and stay; they just must not be part of what is compared.
    4. The FastMCP banner does not count. It is the SDK talking, not the server —
       it appears as soon as the framework object runs, i.e. BEFORE the lifespan
       has built its clients and validated its config. It would have appeared for
       zh-education-mcp 0.2.4 with the server dead behind it. And its wording
       belongs to somebody else, so it disappears on the next SDK release without
       a release of this server in between — the same mechanic as the version cap
       in rule 1, one level up.
    """
    client = await build_http_client()  # anything that can fail
    tools = register_tools()  # sits ahead of the marker
    # Explanatory values as their own fields — never inside the marker field.
    log.info(READY_MARKER, tools=len(tools), transport=settings.transport)
    try:
        yield
    finally:
        await client.aclose()


# And into the README, in exactly the spelling that gets compared — a marker only
# the source knows is not a contract:
#
#     Bereitschaftsmarker (stderr, JSON field `event`): `server ready`


def test_server_announces_readiness() -> None:
    """Rule 14's Nachweis — the same measurement the boot gate makes.

    Mutations that must turn this red (rule 6):

      * append an explanatory tail inside the `event` field — if it stays green,
        the comparison is a prefix match, not an equality check;
      * move the log.info(READY_MARKER, ...) call ABOVE build_http_client() — if
        it stays green, the test asserts entry into the lifespan, not readiness.

    And the negative control belongs in the evidence (rule 5): start once with an
    invalid argument, where something MUST appear on stderr. If that is empty too,
    the setup measures nothing and "no marker" is not a result — it is a check
    that did not run.
    """
    proc = subprocess.run(
        [sys.executable, "-m", PACKAGE],
        stdin=subprocess.DEVNULL,  # no request possible → stderr is self-report
        capture_output=True,
        text=True,
        timeout=6,
    )
    events = [
        json.loads(line)["event"]
        for line in proc.stderr.splitlines()
        if line.startswith("{")
    ]
    # Equality, deliberately: `in` on a list is an exact match per element.
    assert READY_MARKER in events, (
        f"no readiness marker on stderr. Seen: {events}. The `event` field is "
        "compared exactly — a prefix does not count (openlex-mcp)."
    )
    assert proc.stdout == "", "stdout belongs to the protocol"
