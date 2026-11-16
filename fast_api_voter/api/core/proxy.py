"""api.core.proxy — who the client is when a reverse proxy sits in front of the API.

Behind a proxy the connecting address is the proxy's, so the rate limiter (slowapi keys on
`request.client.host`) and the Socket.IO start limiter (api/sockets/limits.py, on the scope's
client) would put every visitor in one bucket. The proxy says who it is serving in
`X-Forwarded-For`, but anyone can send that header, so it is read only on a connection that comes
FROM a proxy named in `TRUSTED_PROXIES`, and then right to left: the client is the first address
that is not itself a trusted proxy. A spoofed entry on the left of the chain, or a header from a
peer that is not a trusted proxy, changes nothing.

The reading itself is uvicorn's `ProxyHeadersMiddleware` (the same one `--proxy-headers` runs, which
trusts 127.0.0.1 by default); this only gives it the list from `Settings` instead of a server flag,
refuses "*", and wraps the outermost app, so HTTP and WebSocket scopes are both rewritten before
any limiter reads them.
"""
from __future__ import annotations

from typing import Any

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def trust_proxies(app: Any, trusted: str) -> Any:
    """`app`, with `X-Forwarded-For` honoured from the proxies in `trusted` (comma-separated
    addresses or CIDR ranges), or `app` itself when there are none."""
    hosts = [h.strip() for h in trusted.split(",") if h.strip()]
    if "*" in hosts:
        raise ValueError(
            "TRUSTED_PROXIES must name the proxies: '*' would let any peer choose its own address"
        )
    return ProxyHeadersMiddleware(app, trusted_hosts=hosts) if hosts else app
