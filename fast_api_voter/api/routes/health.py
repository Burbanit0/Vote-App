"""
api/health — liveness/readiness for the FastAPI sibling.

Mirrors the Flask /api/health endpoint (app/routes/health.py) so uptime
monitors and deploy scripts have a uniform contract on both backends.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict

from fastapi import APIRouter, Response

router = APIRouter(prefix="/api/v2", tags=["meta"])

_BOOT = time.time()
_VERSION = os.environ.get("GIT_SHA", "dev")


def _check_redis() -> Dict[str, Any]:
    """Lazy import so the route doesn't pay redis cost when uncalled."""
    url = os.environ.get("REDIS_URL")
    if not url:
        # Redis is an OPTIONAL compute cache (see engine/utils/cache.py and
        # core/ratelimit.py — both treat an unset REDIS_URL as "disabled", not an
        # error). When it isn't configured the app runs fully stateless, so its
        # absence must not fail liveness (would kill the container on hosts that
        # gate on /health, e.g. Fly.io single-container deploys).
        return {"ok": True, "configured": False}
    t0 = time.perf_counter()
    try:
        import redis
        client = redis.StrictRedis.from_url(url)
        client.ping()
        return {"ok": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
    except Exception:
        # Don't surface the raw exception text to callers (info exposure); the
        # health contract only needs ok/not-ok. Details stay in server logs.
        return {"ok": False, "error": "unreachable"}


@router.get("/health")
def health(response: Response) -> Dict[str, Any]:
    """Return 200 when healthy, 503 when degraded — same contract as
    `/api/health` on the Flask side."""
    checks = {"redis": _check_redis()}
    all_ok = all(c.get("ok") for c in checks.values())
    if not all_ok:
        response.status_code = 503
    return {
        "status":   "ok" if all_ok else "degraded",
        "version":  _VERSION,
        "backend":  "fastapi",                 # disambiguator vs Flask /api/health
        "uptime_s": round(time.time() - _BOOT, 1),
        "checks":   checks,
    }
