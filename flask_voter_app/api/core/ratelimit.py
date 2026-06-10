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
"""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("REDIS_URL") or "memory://",
)
