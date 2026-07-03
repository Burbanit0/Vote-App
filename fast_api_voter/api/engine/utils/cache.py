"""
Redis result-cache for deterministic compute endpoints.

Vote Lab's simulation endpoints are deterministic: the same input config
(with the same seed) always produces the same output. That makes them
ideal candidates for memoisation in Redis — a user rerunning the same
simulation gets the answer in ~5 ms instead of 200–500 ms.

Usage:
    from api.engine.utils.cache import cache_result

    @cache_result("election:simulate", ttl_seconds=3600)
    def _simulate_worker(data: dict) -> tuple[dict, int]:
        ...
        return body, 200

Stack this BELOW @heavy_endpoint so the cache check runs in the tpool
thread alongside the compute (avoids holding the eventlet event loop).

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

# Use a module-level logger, NOT current_app.logger — workers wrapped here may
# run inside eventlet.tpool (a real OS thread) where the Flask app context is
# not available. current_app would raise RuntimeError there.
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
            try:
                import redis
                _redis_client = redis.from_url(url)
            except Exception:
                _redis_client = None
    return _redis_client


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
                key = f"{prefix}:{_stable_hash(data)}"
            except (TypeError, ValueError):
                # Input not JSON-serialisable — skip cache entirely.
                return worker(data)

            try:
                cached = redis_client.get(key)
                if cached is not None:
                    return json.loads(cached), 200
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
