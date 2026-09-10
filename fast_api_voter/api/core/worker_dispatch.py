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

Three pieces:

- `run_bounded(fn, *args, **kwargs)` — the low-level primitive. Runs any
  sync callable off the event loop, bounded by the shared semaphore and
  timeout. Raises `asyncio.TimeoutError` on timeout; callers decide how to
  surface that in their own response shape (export.py's `_generate_rows`
  returns a bare list, not the `(body, status)` tuple below, so it can't
  share a single fallback shape with the rest).
- `run_worker_bounded(domain_fn, payload)` — the `(payload) -> (body,
  status)` worker contract used by every `routes/*.py` helper
  (`_run_worker`/`_run_typed`/`_run_passthrough`). Converts a timeout into
  a same-shaped `({"error": ...}, 503)` tuple, so each route's existing
  status-code handling covers it with no changes on the caller's side.
- `raise_for_status(body, status_code)` — the `(body, status)` ->
  `HTTPException` mapping that most `_run_typed`/`_run_passthrough` helpers
  need on top of `run_worker_bounded`. Shared here instead of duplicated
  per router (it used to be — see the function's own docstring).

Both share ONE semaphore — a heavy CSV export and a heavy Monte Carlo run
compete for the same 4 concurrent slots, which is the point: the bound is on
total CPU-heavy work in flight, not per-endpoint.

Numbers, and why:

- `MAX_CONCURRENT_WORKERS = 4` — matches the existing
  `ThreadPoolExecutor(max_workers=min(4, num_runs))` precedent already used
  *inside* the Monte Carlo worker itself
  (`api/domain/simulations/advanced.py`), so heavy requests aren't left to
  compete unbounded for CPU against each other on top of that.
- `WORKER_TIMEOUT_SECONDS = 90.0` — measured live against the two heaviest
  workers found during this session's Schemathesis pass (PR #346), each at
  their documented max request bounds: Monte Carlo (`num_runs=500,
  num_voters=1000`) took 34s, `/election/coalition` (`num_voters=1000,
  total_seats=1000`, 8 candidates) took 57s. Neither is a bug this item
  fixes (that's real, pre-existing compute cost at the product's own
  documented bounds, not a hang) — 90s leaves real margin above the worst
  measured case while still bounding a truly pathological worker (an actual
  deadlock or infinite loop) rather than letting it run forever.

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
from typing import Any, Callable, Dict, Tuple, TypeVar

from fastapi import HTTPException, status as http_status

from api.engine.utils.logger import get_logger

log = get_logger(__name__)

WorkerFn = Callable[[Dict[str, Any]], Tuple[Dict[str, Any], int]]
_T = TypeVar("_T")

# See module docstring for how these two numbers were chosen.
MAX_CONCURRENT_WORKERS = 4
WORKER_TIMEOUT_SECONDS = 90.0

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
    `routes/*.py` module's `_run_worker`/`_run_typed`/`_run_passthrough`."""
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
    return (200) or the matching `HTTPException` — the mapping every
    `routes/*.py` module's `_run_typed`/`_run_passthrough` used to duplicate
    independently (4 near-identical copies, which is what pushed jscpd's
    clone count up when the 503 branch below was added to each one — this
    function is the fix, not the duplication).

    - 400 → domain-level validation (distinct from Pydantic 422, which fires
      before the worker is even called).
    - 503 → `run_bounded`'s own timeout (see module docstring).
    - anything else non-200 → treated as an unexpected worker failure.
    """
    if status_code == 200:
        return body
    if status_code == 400:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=body.get("error", "Bad request"),
        )
    if status_code == 503:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=body.get("error", "Service unavailable"),
        )
    raise HTTPException(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=body.get("error", "Internal error"),
    )
