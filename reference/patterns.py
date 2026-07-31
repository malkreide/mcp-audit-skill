"""Copy-paste patterns for the seven transport-hardening rules (MCP SDK 2.x / ASGI / uvicorn).

Each block is self-contained and annotated with the rule it implements. Adapt the
names; keep the shape. The comments are deliberately verbose — they are the part
that survives into the target codebase and explains *why* to the next reader.

`get_settings()`, `mcp` and the concrete settings fields stand in for whatever the
target project already calls them. Likewise the `settings` and `tool` fixtures in
the test section: supply them from the project's own `conftest.py`. The `client`
fixture *is* defined here, because how it is built is itself one of the rules.

What must not be adapted away is the shape: the bind travels as an argument, one
policy object reaches every path that builds an app, and every control is
removable in a test.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import pytest
import uvicorn
from starlette.testclient import TestClient

# Rule 1(a) — the mechanical half of the major bump. Under 1.x this read
#   from mcp.server.fastmcp import FastMCP
# The import error points at every site, so search-and-replace finishes the job.
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

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
    carries those lines does not start under HTTP **at all** — and because tool
    tests run over stdio, nothing in an ordinary suite goes near it. The failure
    waits for the first HTTP deployment.
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
    assert "readOnlyHint" in dumped, "alias lost — this IS a wire change, stop and re-read"
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
        port=settings.port,          # rule 3: the port travels WITH the host.
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
# a finding, not a footnote: either the test is missing or the control does
# nothing.
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

    Streamable HTTP starts its session manager in the app LIFESPAN, and
    `ASGITransport` never runs a lifespan. Every request then comes back 500 —
    including the ones that should be 421, which makes a broken allow-list and a
    working one look identical. Reading that 500 as a finding costs an afternoon
    in the wrong file.

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

def test_the_sdk_served_path_gets_the_allowlist_too(settings: Any, monkeypatch: Any) -> None:
    """Assert WHICH branch ran, so taking the wrong one fails instead of hanging."""
    calls = _patch_run(monkeypatch)
    settings.transport = "streamable-http"
    settings.auth_token = None
    settings.cors_origins = []

    serve_http(settings)

    assert len(calls) == 1, "the custom-builder branch ran — this test asserts the run() branch"
    assert calls[0]["transport_security"] is not None


def test_the_custom_builder_path_gets_the_allowlist_too(settings: Any, monkeypatch: Any) -> None:
    """The twin of the test above. Both branches, both claiming their branch.

    Without the pair, a change that routes everything through one branch leaves
    the other silently untested — and the mutation that drops the policy from it
    stays green.
    """
    calls = _patch_run(monkeypatch)
    served: list[Any] = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: served.append(app))
    settings.transport = "streamable-http"
    settings.auth_token = "t"          # forces the custom-builder branch

    serve_http(settings)

    assert not calls, "the run() branch ran — this test asserts the custom-builder branch"
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
    monkeypatch.setattr(mcp, "create_sse_app", lambda **kw: built.append(kw) or object())
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: None)
    settings.transport = "sse"

    serve_http(settings)

    assert len(built) == 1
    assert built[0]["transport_security"] is not None
    assert built[0]["port"] == settings.port      # rule 3: the port travels too


# NOTE ON RUNNING THE SUITE (rule 7): run it under a timeout
# (`pytest --timeout=30`). That turns every hang into a failure with a stack
# trace, which is the difference between a named finding and "the suite is
# flaky again".
#
# And run each branch test alone AND in the full suite. The instance-patch trap
# in `_patch_run` only ever shows up in the second — passing alone is precisely
# the symptom.
