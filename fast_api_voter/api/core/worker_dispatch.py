"""
Shared semaphore + timeout wrapper around `asyncio.to_thread` for CPU-heavy
domain workers (Lot 3, PLAN_SOLIDITE_TECHNIQUE.md — "Timeouts & backpressure").

Every `routes/*.py` module hands its domain function straight to
`asyncio.to_thread` today, with unlimited concurrency and no timeout, all
sharing the same default executor (`min(32, cpu_count + 4)` threads) as
every other route — including cheap ones like `/health`. A burst of heavy
requests (Monte Carlo, coalition, ...) can starve that pool for everyone
else, and a genuinely stuck worker (deadlock, unbounded loop) holds its
thread forever with no way to recover short of restarting the process.

Four pieces:

- `run_bounded(fn, *args, **kwargs)` — the low-level primitive. Runs any
  sync callable off the event loop, bounded by the shared semaphore and
  timeout. Raises `asyncio.TimeoutError` on timeout; callers decide how to
  surface that in their own response shape (`api/sockets/__init__.py`'s
  Monte Carlo streaming loop catches it and emits a `monte_carlo_error`
  event — it has no HTTP status to return, so it can't share the
  `(body, status)` tuple below).
- `run_worker_bounded(domain_fn, payload)` — the `(payload) -> (body,
  status)` worker contract. Converts a timeout into a same-shaped
  `({"error": ...}, 503)` tuple, so existing status-code handling covers it
  with no changes on the caller's side.
- `raise_for_status(body, status_code)` — the `(body, status)` ->
  `HTTPException` mapping on top of `run_worker_bounded`.
- `run_passthrough(domain_fn, request)` / `run_typed(domain_fn, request,
  response_model)` — the two of those composed, which is all a route needs.

They all share ONE semaphore — a Socket.IO Monte Carlo stream and a heavy
`/election/simulate` compete for the same 4 concurrent slots, which is the
point: the bound is on total CPU-heavy work in flight, not per-endpoint.

Numbers, and why:

- `MAX_CONCURRENT_WORKERS = 4` — matches the existing
  `ThreadPoolExecutor(max_workers=min(4, num_runs))` precedent already used
  *inside* the Monte Carlo worker itself
  (`api/domain/simulations/advanced.py`), so heavy requests aren't left to
  compete unbounded for CPU against each other on top of that.
- `WORKER_TIMEOUT_SECONDS = 180.0` — started at 90s, measured against the
  two heaviest workers found during this session's Schemathesis pass (PR
  #346) at their documented max request bounds: Monte Carlo
  (`num_runs=500, num_voters=1000`) took 34s, `/election/coalition`
  (`num_voters=1000, total_seats=1000`, 8 candidates) took 57s. That 90s
  value then failed for real in CI: `/simulations/what-if` capped at its
  documented 10 variant values took 71s **in isolation, on a local dev
  machine, with zero contention** — GitHub Actions runners are both slower
  per-core and run this suite under `pytest-xdist` (several worker
  *processes* competing for the runner's few vCPUs), so the actual CI wall
  clock for that same request exceeded 90s and failed the PR
  (`test_caps_at_10_values`, PR #349). None of these are bugs this item
  fixes — real, pre-existing compute cost at the product's own documented
  bounds, not a hang — but a timeout calibrated only against an isolated
  local measurement doesn't have enough headroom for CI's slower, shared,
  parallel-worker reality. 180s leaves real margin above the worst *CI*
  case observed so far while still bounding a truly pathological worker (an
  actual deadlock or infinite loop) rather than letting it run forever, and
  is still a small fraction of backend-ci-cd-pipeline.yml's own 20-minute
  job timeout for the ~1800-test suite as a whole.

**Known limitation, not a bug**: Python cannot forcibly kill a running OS
thread. When `asyncio.wait_for` times out, the semaphore slot is released
immediately (so a new request can be dispatched right away) and the client
gets a clean response instead of hanging — but the orphaned thread itself
keeps running in the background until it finishes on its own, discarding
its result. This is the same tradeoff every `asyncio.to_thread`-based
timeout in Python has; the alternative (killable compute) needs separate
worker processes, a materially bigger change out of scope here.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, Callable, Dict, Tuple, TypeVar

from fastapi import HTTPException, status as http_status
from pydantic import BaseModel

from api.engine.utils.logger import get_logger

log = get_logger(__name__)

WorkerFn = Callable[[Dict[str, Any]], Tuple[Dict[str, Any], int]]
_T = TypeVar("_T")
_ResponseT = TypeVar("_ResponseT", bound=BaseModel)

# See module docstring for how these two numbers were chosen.
MAX_CONCURRENT_WORKERS = 4
WORKER_TIMEOUT_SECONDS = 180.0

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_WORKERS)


async def run_bounded(fn: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
    """Run any sync callable off the event loop, bounded by the shared
    concurrency limit and timeout. Raises `asyncio.TimeoutError` on timeout —
    see `run_worker_bounded` for the `(body, status)` convenience wrapper."""
    async with _semaphore:
        return await asyncio.wait_for(
            asyncio.to_thread(fn, *args, **kwargs), timeout=WORKER_TIMEOUT_SECONDS
        )


async def run_worker_bounded(domain_fn: WorkerFn, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """`(payload) -> (body, status)` worker contract, as used by every
    `routes/*.py` route, through `run_passthrough`/`run_typed` below."""
    try:
        return await run_bounded(domain_fn, payload)
    except asyncio.TimeoutError:
        worker_name = getattr(domain_fn, "__name__", repr(domain_fn))
        log.error(
            "worker_dispatch.timeout",
            worker=worker_name,
            timeout_s=WORKER_TIMEOUT_SECONDS,
        )
        return {"error": "Request took too long to process"}, 503


def raise_for_status(body: Dict[str, Any], status_code: int) -> Dict[str, Any]:
    """Convert a domain worker's `(body, status)` tuple into either a plain
    return (200) or the matching `HTTPException`.

    - Any 4xx → the worker's own status, verbatim: a domain worker that says
      404/409/422 is describing the request, not failing (400 is the common
      one — domain-level validation, distinct from Pydantic's 422, which
      fires before the worker is even called).
    - 503 → `run_bounded`'s own timeout (see module docstring).
    - Any other non-200 → an unexpected worker failure, reported as 500.
    """
    if status_code == 200:
        return body
    if 400 <= status_code < 500:
        raise HTTPException(status_code=status_code, detail=body.get("error", "Bad request"))
    if status_code == 503:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=body.get("error", "Service unavailable"),
        )
    raise HTTPException(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=body.get("error", "Internal error"),
    )


async def run_passthrough(
    domain_fn: WorkerFn, request: BaseModel | Mapping[str, Any]
) -> Dict[str, Any]:
    """Run a worker and return its body, or raise. `request` is the endpoint's
    Pydantic model, or a plain payload for a query-param route (`/manipulability`
    builds one by hand — it has no request model to dump)."""
    payload = request.model_dump() if isinstance(request, BaseModel) else dict(request)
    body, status_code = await run_worker_bounded(domain_fn, payload)
    return raise_for_status(body, status_code)


async def run_typed(
    domain_fn: WorkerFn,
    request: BaseModel | Mapping[str, Any],
    response_model: type[_ResponseT],
) -> _ResponseT:
    """`run_passthrough` parsed through the endpoint's response model (which may
    carry `extra="allow"`, so unmodeled worker fields still pass through)."""
    return response_model.model_validate(await run_passthrough(domain_fn, request))
