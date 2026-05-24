"""
health.py — Service liveness/readiness endpoint.

GET /api/health
    Returns 200 with a JSON status block when DB + Redis are reachable.
    Returns 503 with the same shape (but degraded fields) when any
    dependency is down — used by uptime monitors, load balancers, and
    deploy scripts to decide whether to route traffic to this instance.

Response shape:
    {
      "status":  "ok" | "degraded",
      "version": "<git sha or 'dev'>",
      "uptime_s": 1234,
      "checks": {
        "db":    { "ok": true,  "latency_ms": 2 },
        "redis": { "ok": false, "error": "Connection refused" }
      }
    }

The endpoint intentionally has NO rate limit and NO auth — that's the
contract a healthcheck needs.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict

from flask import Blueprint, Response, jsonify

from app import db, redis_client
from app.utils.logger import get_logger

health_bp = Blueprint("health", __name__, url_prefix="/api")
log = get_logger(__name__)

_BOOT_TIME = time.time()
_VERSION = os.environ.get("GIT_SHA", "dev")


def _check_db() -> Dict[str, Any]:
    """Roundtrip a trivial query. Latency < 50 ms expected locally."""
    t0 = time.perf_counter()
    try:
        # SQLAlchemy 2.0 idiom — works on both Postgres and SQLite test in-memory.
        with db.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"ok": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
    except Exception as exc:
        return {"ok": False, "error": str(exc).splitlines()[0][:200]}


def _check_redis() -> Dict[str, Any]:
    t0 = time.perf_counter()
    try:
        redis_client.ping()
        return {"ok": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
    except Exception as exc:
        return {"ok": False, "error": str(exc).splitlines()[0][:200]}


@health_bp.route("/health", methods=["GET"])
def health() -> tuple[Response, int]:
    checks = {
        "db":    _check_db(),
        "redis": _check_redis(),
    }
    all_ok = all(c.get("ok") for c in checks.values())
    body = {
        "status":   "ok" if all_ok else "degraded",
        "version":  _VERSION,
        "uptime_s": round(time.time() - _BOOT_TIME, 1),
        "checks":   checks,
    }
    if not all_ok:
        log.warning("health.degraded", checks=checks)
    return jsonify(body), 200 if all_ok else 503
