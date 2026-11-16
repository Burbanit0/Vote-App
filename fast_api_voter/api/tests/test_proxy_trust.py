"""Who the client is behind a reverse proxy (api/core/proxy.py, P4-2).

The two things that matter: a forwarded address is believed only from a proxy named in
TRUSTED_PROXIES, and a spoofed header must not buy a fresh rate-limit bucket.
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import Depends, FastAPI, Request

from api.core.proxy import trust_proxies
from api.core.ratelimit import check_v2_rate_limit

PROXY = "10.0.0.5"


async def _echo(scope: dict[str, Any], receive: Any, send: Any) -> None:
    """A bare ASGI app that records the client its scope ended up with."""
    _echo.seen.append(scope.get("client"))  # type: ignore[attr-defined]


_echo.seen = []  # type: ignore[attr-defined]


async def _call(app: Any, peer: str | None, forwarded: str | None, kind: str = "http") -> Any:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded is not None else []
    scope = {"type": kind, "client": (peer, 40000) if peer else None, "headers": headers}
    _echo.seen.clear()  # type: ignore[attr-defined]
    await app(scope, None, None)
    return _echo.seen[0]  # type: ignore[attr-defined]


@pytest.mark.asyncio
@pytest.mark.parametrize("peer,forwarded,client", [
    # From the proxy: the client it names.
    (PROXY, "203.0.113.7", "203.0.113.7"),
    # A spoofed entry on the left is ignored: the first address from the right that is no proxy.
    (PROXY, "1.2.3.4, 203.0.113.7", "203.0.113.7"),
    (PROXY, "1.2.3.4, 203.0.113.7, 10.0.0.9", "203.0.113.7"),  # 10.0.0.9: a second proxy
    # From a peer that is not a trusted proxy: the header is ignored, whatever it says.
    ("198.51.100.9", "1.2.3.4", "198.51.100.9"),
    ("198.51.100.9", "10.0.0.5, 1.2.3.4", "198.51.100.9"),
    # No header from the proxy: the proxy itself is the best that is known.
    (PROXY, None, PROXY),
])
async def test_the_forwarded_address_is_believed_only_from_a_trusted_proxy(peer, forwarded, client):
    app = trust_proxies(_echo, "10.0.0.0/24")
    seen = await _call(app, peer, forwarded)
    assert seen[0] == client


@pytest.mark.asyncio
async def test_a_websocket_scope_is_read_the_same_way():
    """The Socket.IO start limiter keys on the scope's client, and a socket's scope is a
    websocket one."""
    app = trust_proxies(_echo, PROXY)
    assert (await _call(app, PROXY, "203.0.113.7", kind="websocket"))[0] == "203.0.113.7"
    assert (await _call(app, "198.51.100.9", "203.0.113.7", kind="websocket"))[0] == "198.51.100.9"


@pytest.mark.asyncio
async def test_a_scope_with_no_client_is_left_alone():
    assert await _call(trust_proxies(_echo, PROXY), None, "203.0.113.7") is None


def test_no_trusted_proxy_means_the_app_is_returned_untouched():
    assert trust_proxies(_echo, "") is _echo
    assert trust_proxies(_echo, " , ") is _echo


@pytest.mark.parametrize("trusted", [
    "*", "10.0.0.5, *",  # a wildcard
    "0.0.0.0/0", "::/0", "10.0.0.5, 0.0.0.0/0",  # a range that is every address
    "nginx", "proxy.internal", "10.0.0.5:80", "10.0.0.0/33", "10.0.0.5,,garbage",  # not addresses
])
def test_a_wildcard_a_trust_all_range_or_a_non_address_is_refused(trusted):
    with pytest.raises(ValueError, match="TRUSTED_PROXIES"):
        trust_proxies(_echo, trusted)


@pytest.mark.parametrize("trusted", ["10.0.0.5", "10.0.0.0/8", "::1", "2001:db8::/32", "10.0.0.5, 172.16.0.0/12"])
def test_addresses_and_ranges_are_accepted(trusted):
    assert trust_proxies(_echo, trusted) is not _echo


@pytest.mark.asyncio
async def test_the_scheme_is_taken_from_a_trusted_proxy_only():
    seen: list[Any] = []

    async def app(scope, receive, send):
        seen.append(scope.get("scheme"))

    wrapped = trust_proxies(app, PROXY)
    for peer in (PROXY, "198.51.100.9"):
        scope = {"type": "http", "scheme": "http", "client": (peer, 1),
                 "headers": [(b"x-forwarded-proto", b"https"), (b"x-forwarded-for", b"203.0.113.7")]}
        await wrapped(scope, None, None)
    assert seen == ["https", "http"]


def test_the_app_honours_trusted_proxies_from_the_environment():
    """api.main wraps its outermost app with what TRUSTED_PROXIES says (read at import, so a fresh
    interpreter), and refuses to start on a bad value."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    backend = Path(__file__).resolve().parents[2]
    probe = "import api.main as m; print(type(m.app).__name__)"

    def run(trusted: str) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "TRUSTED_PROXIES": trusted, "REDIS_URL": ""}
        return subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                              env=env, cwd=backend)

    assert run("10.0.0.5").stdout.strip() == "ProxyHeadersMiddleware"
    assert run("").stdout.strip() == "ASGIApp"
    refused = run("0.0.0.0/0")
    assert refused.returncode != 0 and "TRUSTED_PROXIES" in refused.stderr


# ── through the limiter itself ──────────────────────────────────────────────

def _limited_app(path: str, trusted: str) -> Any:
    """A route behind the real v2 limiter (120/minute per client), wrapped as main.py wraps."""
    from api.core.ratelimit import limiter  # the shared, module-level limiter

    api = FastAPI()
    api.state.limiter = limiter

    @api.get(path, dependencies=[Depends(check_v2_rate_limit)])
    async def _route(request: Request) -> dict[str, str]:
        return {"client": request.client.host if request.client else "?"}

    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    api.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    return trust_proxies(api, trusted)


async def _statuses(app: Any, path: str, peer: str, forwarded: list[str], n: int) -> list[int]:
    transport = httpx.ASGITransport(app=app, client=(peer, 50000))
    codes = []
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(n):
            headers = {"X-Forwarded-For": forwarded[i % len(forwarded)]} if forwarded else {}
            codes.append((await client.get(path, headers=headers)).status_code)
    return codes


@pytest.mark.asyncio
async def test_visitors_behind_a_trusted_proxy_get_their_own_buckets():
    path = "/p42/many-clients"
    app = _limited_app(path, PROXY)
    codes = await _statuses(app, path, PROXY, [f"203.0.113.{i}" for i in range(1, 122)], 121)
    assert set(codes) == {200}, "each forwarded client has its own 120/minute, not the proxy's"


@pytest.mark.asyncio
async def test_one_client_behind_a_trusted_proxy_is_limited_whatever_the_proxy_is():
    path = "/p42/one-client"
    app = _limited_app(path, PROXY)
    codes = await _statuses(app, path, PROXY, ["203.0.113.7"], 122)
    assert codes.index(429) == 120 and set(codes) <= {200, 429}, "the 121st request is the first refused"


@pytest.mark.asyncio
async def test_a_spoofed_header_from_an_untrusted_peer_buys_no_fresh_bucket():
    path = "/p42/spoofer"
    app = _limited_app(path, PROXY)  # only 10.0.0.5 is trusted; the spoofer is 198.51.100.9
    codes = await _statuses(app, path, "198.51.100.9", [f"203.0.113.{i}" for i in range(1, 123)], 122)
    assert codes.index(429) == 120, "a new X-Forwarded-For per request must not reset the limit"


@pytest.mark.asyncio
async def test_without_trusted_proxies_the_header_is_never_read():
    path = "/p42/no-proxies"
    app = _limited_app(path, "")
    codes = await _statuses(app, path, PROXY, [f"203.0.113.{i}" for i in range(1, 123)], 122)
    assert codes.index(429) == 120
