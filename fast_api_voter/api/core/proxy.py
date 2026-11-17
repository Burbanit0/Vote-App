"""api.core.proxy — who the client is when a reverse proxy sits in front of the API.

Behind a proxy the connecting address is the proxy's, so the rate limiter (slowapi keys on
`request.client.host`) would put every visitor in one bucket, and so would anything else that keys
on the ASGI scope's client (the Socket.IO sessions' address too). The proxy says who it is serving
in `X-Forwarded-For`, but anyone can send that header, so it is read only on a connection that
comes FROM a proxy named in `TRUSTED_PROXIES`, and then right to left: the client is the first
address that is not itself a trusted proxy. A spoofed entry on the left of the chain, or a header
from a peer that is not a trusted proxy, changes nothing.

The reading itself is uvicorn's `ProxyHeadersMiddleware`; this only gives it the list from
`Settings`, checks the list, and wraps the outermost app, so HTTP and WebSocket scopes are both
rewritten before anything reads them. Two things follow from using it:
- It also takes `X-Forwarded-Proto` from a trusted proxy (the request's scheme becomes https/wss).
- uvicorn runs the same middleware itself (`--proxy-headers`, on by default) for peers in its own
  `FORWARDED_ALLOW_IPS`, which defaults to 127.0.0.1. That layer is outside this one and is not
  checked here: run uvicorn with `--no-proxy-headers` to make TRUSTED_PROXIES the only list, and
  never set FORWARDED_ALLOW_IPS to "*".
"""
from __future__ import annotations

import ipaddress
from typing import Any

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def _check(entry: str) -> None:
    """Each entry must be one IP address or one CIDR range, and not every address."""
    try:
        network = ipaddress.ip_network(entry, strict=False)
    except ValueError:
        raise ValueError(
            f"TRUSTED_PROXIES: {entry!r} is not an IP address or a CIDR range (no host names, no ports)"
        ) from None
    if network.prefixlen == 0:
        raise ValueError(
            f"TRUSTED_PROXIES: {entry!r} covers every address, so any peer could choose its own"
        )


def trust_proxies(app: Any, trusted: str) -> Any:
    """`app`, with `X-Forwarded-For` honoured from the proxies in `trusted` (comma-separated
    addresses or CIDR ranges), or `app` itself when there are none. A wildcard, a range that covers
    every address, or an entry that is not an address is a ValueError at startup, so a typo is not
    mistaken for a configured proxy."""
    hosts = [h.strip() for h in trusted.split(",") if h.strip()]
    for host in hosts:
        _check(host)
    return ProxyHeadersMiddleware(app, trusted_hosts=hosts) if hosts else app
