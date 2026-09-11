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

from api.engine.utils.logger import get_logger

log = get_logger(__name__)

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
        log.warning("health.redis_check_failed", exc_info=True)
        return {"ok": False, "error": "unreachable"}


@router.get(
    "/health",
    responses={
        503: {
            "description": (
                "Degraded — one or more subsystem checks failed. Same body "
                "shape as 200 (status='degraded'), not an ErrorDetail."
            ),
        },
    },
)
def health(response: Response) -> Dict[str, Any]:
    """Return 200 when healthy, 503 when degraded — same contract as
    `/api/health` on the Flask side.

    Kept exactly as-is (fly.toml's [[http_service.checks]] hits this exact
    path). `/health/live` and `/health/ready` below are ADDITIVE — a
    conflated liveness+readiness signal on one endpoint is exactly the "reste
    binaire" gap Lot 10 names, but this one has a real deploy dependency, so
    it isn't worth rewriting when adding beside it is just as effective."""
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


@router.get("/health/live")
def liveness() -> Dict[str, Any]:
    """Liveness only: can this process respond to HTTP at all?

    Zero dependency checks, on purpose — this must basically never fail
    unless the process itself is dead, so an orchestrator reading only this
    endpoint never restarts a perfectly-alive process over a transient Redis
    blip (a real gap `/health` alone has: a platform that treats any non-2xx
    from its one health endpoint as "kill and restart" can't tell "the
    process is dead" from "an optional cache is briefly unreachable" apart)."""
    return {
        "status":   "ok",
        "version":  _VERSION,
        "backend":  "fastapi",
        "uptime_s": round(time.time() - _BOOT, 1),
    }


@router.get(
    "/health/ready",
    responses={
        503: {
            "description": (
                "Not ready — see the module docstring on `_check_redis` for "
                "why an UNCONFIGURED Redis never lands here, only a "
                "configured-but-unreachable one."
            ),
        },
    },
)
def readiness(response: Response) -> Dict[str, Any]:
    """Readiness: should this instance receive traffic right now?

    Reuses `_check_redis()` — no new dependency logic. This app has exactly
    one optional backing service, and its own degrade-gracefully design
    (see the comment on `_check_redis`) means an UNCONFIGURED Redis is not a
    "required dependency down" case at all: the documented production deploy
    (fly.toml: "Stateless: no Redis... required") runs with no REDIS_URL set,
    and that is the fully-ready, fully-functional state, not a degraded one.
    The only state this can meaningfully call "not ready" is the one where an
    operator explicitly configured Redis (set REDIS_URL) and it is
    unreachable — exactly what `_check_redis()` already encodes as
    `{"ok": False, ...}` vs. `{"ok": True, "configured": False}` for the
    unset case. So today this has the same pass/fail shape as `/health`
    (there is only one checkable dependency, and it's optional) — the value
    of a separate endpoint is semantic, not behavioural yet: a platform that
    understands the liveness/readiness split can route around a degraded
    instance without restarting it, which `/health` alone (conflated with
    liveness) can't express."""
    checks = {"redis": _check_redis()}
    all_ok = all(c.get("ok") for c in checks.values())
    if not all_ok:
        response.status_code = 503
    return {
        "status":   "ready" if all_ok else "not_ready",
        "backend":  "fastapi",
        "checks":   checks,
    }
