"""
api/routes/metrics.py — Prometheus metrics exposition.

Lot 10, PLAN_SOLIDITE_TECHNIQUE.md ("/metrics Prometheus" + readiness/liveness):
`/api/v2/health` already existed but stayed binary (ok/degraded) with no
counters or latency histograms behind it. `prometheus-fastapi-instrumentator`
(chosen over hand-rolling `prometheus_client` directly — see
docs/exploration/EXP-012-prometheus-metrics-and-health-split.md for the
maintenance check that justified it) wraps the app in one middleware that
records the default HTTP metrics (`http_requests_total`,
`http_request_duration_seconds`, `http_request_size_bytes`,
`http_response_size_bytes`) by path template + method + status, and exposes
them at `/api/v2/metrics` in Prometheus text-exposition format.

Unlike every other module in `api/routes/`, this one has no `APIRouter`: the
instrumentator installs its own ASGI middleware AND its own route via
`Instrumentator.expose()`, so there's nothing to `app.include_router(...)`.
`setup_metrics(app)` is called once from api/main.py on the raw FastAPI
instance (`fastapi_app`), not the `router` pattern the rest of this package
uses.
"""
from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator

from api.core.config import get_settings

METRICS_PATH = "/api/v2/metrics"


def _check_metrics_auth(authorization: Optional[str] = Header(default=None)) -> None:
    """Optional shared-secret guard on GET /api/v2/metrics.

    `METRICS_AUTH_TOKEN` unset (default) -> open, same "optional, degrades to
    off" posture as `_check_redis()` in health.py. This app has no auth system
    anywhere else, carries no secrets/PII, and is meant to be poked at freely
    for a pedagogical demo — so an unauthenticated `/metrics` isn't a
    meaningful new exposure on its own. It's still a real, if minor,
    information-disclosure surface on a public-internet deploy (live request
    volume, endpoint names, error rates), and ZAP's baseline DAST scan
    (.github/workflows/dast.yml) never discovers or exercises this path — it
    only spiders assets reachable from `/api/v2/docs`'s rendered HTML, and
    `/metrics` is neither linked from there nor part of the OpenAPI schema's
    documented request/response bodies it could fuzz. So this guard is the
    only check that will ever cover this endpoint; set the token to require
    `Authorization: Bearer <token>` on a real deployment that wants it closed.
    """
    token = get_settings().metrics_auth_token
    if not token:
        return
    expected = f"Bearer {token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Not authorized")


def setup_metrics(app: FastAPI) -> None:
    """Wire the instrumentator onto the raw FastAPI app.

    Must run on `fastapi_app` (the plain FastAPI instance), and must run
    BEFORE the catch-all SPA static mount in api/main.py: `.expose()` adds a
    plain route, and Starlette matches routes in registration order — a
    mount at "/" registered first would shadow `/api/v2/metrics` since it
    prefix-matches everything.
    """
    Instrumentator(
        # Exclude the metrics endpoint from its own counters -- otherwise
        # every scrape both produces and observes a request, a standard
        # self-observation trap, not a custom metric.
        excluded_handlers=[METRICS_PATH],
    ).instrument(app).expose(
        app,
        endpoint=METRICS_PATH,
        include_in_schema=True,
        tags=["meta"],
        dependencies=[Depends(_check_metrics_auth)],
        # The handler returns a plain Response it builds itself (Prometheus
        # text-exposition format), bypassing FastAPI's usual response_model
        # inference -- without this override the generated OpenAPI schema
        # falsely documents `application/json`, which api/tests/
        # test_schema_contract.py's Schemathesis contract fuzzing caught for
        # real (an "Undocumented Content-Type" failure) the first time this
        # was wired up. CONTENT_TYPE_LATEST (imported, not hand-copied) is
        # exactly the header value the handler itself sets.
        responses={200: {"content": {CONTENT_TYPE_LATEST: {"schema": {"type": "string"}}}}},
    )
