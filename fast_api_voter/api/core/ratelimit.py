"""
api.core.ratelimit — slowapi limiter for the public research API (/api/v1).

The public API is the one externally-facing, unauthenticated surface, so its
documented per-IP rate limits (10/min on /simulate, 5/min on /compare) are part
of the contract and must survive the FastAPI migration (Phase 4.5.a.4).

Storage mirrors the Flask side exactly (`app/routes/api_public.py`): read the
REDIS_URL env var directly, in-memory otherwise. We deliberately do NOT use
`Settings.redis_url` here — it has a non-empty Docker default, which would push
the test suite onto a Redis that isn't running. Reading the raw env var means
tests (REDIS_URL unset) fall back to `memory://` just like the Flask limiter.

The limiter is wired into the app in api/main.py via `app.state.limiter` +
the RateLimitExceeded handler.

`check_v2_rate_limit` extends the same limiter to the /api/v2/simulations and
/api/v2/election routers (the actual frontend-facing, unauthenticated, CPU-
heavy surface — previously unthrottled). Those routers' handlers all name
their Pydantic body parameter `request` (see api/routes/simulations.py,
api/routes/election.py), which collides with slowapi's `@limiter.limit`
decorator: it locates the real `Request` object by parameter *name*
(`inspect.signature` looking for a parameter literally called `request`), not
by type annotation, and raises if what it finds isn't a
`starlette.requests.Request`. Decorating every handler would mean renaming
that parameter across ~70 functions. Decorating this standalone function
instead — whose only parameter is genuinely named `request: Request` — and
wiring it in as a router-level dependency sidesteps that entirely: slowapi's
per-endpoint storage key is the request path (`key_style="url"`, the
default), so every route sharing this one dependency still gets its own
independent per-IP bucket, not a pooled one.
"""
from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("REDIS_URL") or "memory://",
)


@limiter.limit("120/minute")
async def check_v2_rate_limit(request: Request) -> None:
    """FastAPI dependency form of `@limiter.limit` — see module docstring for
    why this isn't a decorator on each route handler directly. Add via
    `APIRouter(..., dependencies=[Depends(check_v2_rate_limit)])`.

    120/minute (2/s), not the /api/v1-style 5-10/min: /api/v2/election's
    `/profile-simulate` is a live, debounced call fired from a `useEffect` on
    every Playground config change (usePlaygroundData.ts), not an explicit
    "run" action — a first cut at 30/minute measurably flaked
    playground-strategy.spec.ts in CI (two Playwright browser projects x 25
    playground e2e tests, each triggering it on interaction, comfortably
    clears 30/min on one shared per-path bucket well before any single test
    even runs). 120/min still bounds genuine abuse — a real attacker sending
    hundreds of requests/second is unaffected by the difference between 30
    and 120 — while giving interactive, debounced UI traffic (and the test
    suite that exercises it) the same order-of-magnitude headroom the
    endpoint already had with no limit at all.
    """
    return None
