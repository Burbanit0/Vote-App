"""
Redis result-cache for deterministic compute endpoints.

Vote Lab's simulation endpoints are deterministic: the same input config
(with the same seed) always produces the same output. That makes them
ideal candidates for memoisation in Redis — a user rerunning the same
simulation gets the answer in ~5 ms instead of 200–500 ms.

Usage — decorate the name the ROUTE reaches, not an inner worker. This
decorator spent its whole life on `workers._simulate_worker`, which nothing
imported, so /simulate paid full compute on every identical request and no test
noticed:

    from api.engine.utils.cache import cache_result

    # api/domain/election/__init__.py — the namespace the routes import from
    simulate = cache_result("election:simulate", ttl_seconds=3600)(_simulate)

Wrapping the namespace rather than the implementation also keeps the underlying
function callable uncached, which the seeded-RNG isolation tests need.

Failure modes (cache miss, redis down, serialisation errors) all log a
warning and fall through to the wrapped worker — never crash the request.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Dict, Tuple

from api.engine.utils.error_handling import safe_call

# Module-level logger: workers wrapped here run inside `asyncio.to_thread`
# (a real OS thread), so anything context-local to the request is unavailable.
log = logging.getLogger(__name__)

WorkerFn = Callable[[Dict[str, Any]], Tuple[Dict[str, Any], int]]


def _stable_hash(data: Dict[str, Any]) -> str:
    """Deterministic SHA-256 of a JSON-serialisable dict. Sort keys so dict
    insertion order doesn't change the hash."""
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()



_redis_client: Any = None
_redis_tried = False


def _get_redis_client() -> Any:
    """Best-effort redis handle built once from REDIS_URL. Returns None (cache
    disabled) when REDIS_URL is unset or the redis package/connection is
    unavailable — all redis ops in cache_result are already try/except'd."""
    global _redis_client, _redis_tried
    if not _redis_tried:
        _redis_tried = True
        url = os.environ.get("REDIS_URL")
        if url:
            def _connect() -> Any:
                import redis
                return redis.from_url(url)

            _redis_client = safe_call(
                _connect, lambda: None,
                log=log, event="cache.redis_client_init_failed",
            )
    return _redis_client


#: Folded into every key so a deploy cannot serve results computed by the
#: previous build. The voting rules are the highest-blast-radius surface in the
#: repo; without this, fixing one and shipping it leaves /simulate answering
#: with the pre-fix winner for up to a full TTL, and no gate can see it (the
#: parity harness tests the engine, not what Redis returns).
_BUILD = os.environ.get("GIT_SHA", "dev")[:12]


def cache_result(prefix: str, ttl_seconds: int = 3600) -> Callable[[WorkerFn], WorkerFn]:
    """Memoise worker results in Redis by hash of the input dict.

    Cached entries are stored as JSON under ``f"{prefix}:{sha256(data)}"``
    with the given TTL. Only 200-status results are cached — error paths
    (4xx/5xx) always re-run.
    """
    def deco(worker: WorkerFn) -> WorkerFn:
        @wraps(worker)
        def wrapped(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
            redis_client = _get_redis_client()
            if redis_client is None:
                return worker(data)

            try:
                key = f"{prefix}:{_BUILD}:{_stable_hash(data)}"
            except (TypeError, ValueError):
                # Input not JSON-serialisable — skip cache entirely.
                return worker(data)

            try:
                cached = redis_client.get(key)
                if cached is not None:
                    parsed = json.loads(cached)
                    # A value that decodes to a list/None/number is not a body.
                    # Returning it would 500 in the route's response_model and,
                    # since the read succeeded, nothing would overwrite the key
                    # -- so it would keep 500ing for the rest of the TTL.
                    # Falling through recomputes and rewrites it.
                    if isinstance(parsed, dict):
                        return parsed, 200
                    log.warning("cache held a non-object at %s; recomputing", key)
            except Exception:
                # Redis down or transient error — log and fall through.
                log.warning("cache read failed for %s", key, exc_info=True)

            body, status = worker(data)

            if status == 200:
                try:
                    redis_client.setex(key, ttl_seconds, json.dumps(body, default=str))
                except Exception:
                    log.warning("cache write failed for %s", key, exc_info=True)

            return body, status

        return wrapped

    return deco
