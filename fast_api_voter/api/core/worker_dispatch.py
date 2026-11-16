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

**Stopping a timed-out worker** (P4-3). Python cannot kill an OS thread, and a worker started with
`asyncio.to_thread` used to keep running to the end after its request timed out, discarding its
result (measured: a busy loop's counter kept climbing at full speed after the 503). So each worker
now runs on a thread of its own (api/core/cancellation.py), and a timeout, or the client leaving,
cancels it: a flag the worker may poll, and `WorkCancelled` raised into the thread, which stops
pure-Python work at its next bytecode. A long C call finishes first, and a pool the worker started
itself (the Monte Carlo's) is stopped by its tasks polling the flag. The semaphore slot is released
only once the request is over, as before.

**A work budget** (api/core/work_budget.py): a request whose size fields multiply past
`MAX_WORK_UNITS` is refused with a 422 before a thread is started.
"""
from __future__ import annotations

import asyncio
import contextvars
import threading
from collections.abc import Mapping
from typing import Any, Callable, Dict, Tuple, TypeVar

from fastapi import HTTPException, status as http_status
from pydantic import BaseModel

from api.core import cancellation, work_budget
from api.engine.utils import runtime
from api.engine.utils.logger import get_logger

log = get_logger(__name__)

WorkerFn = Callable[[Dict[str, Any]], Tuple[Dict[str, Any], int]]
_T = TypeVar("_T")
_ResponseT = TypeVar("_ResponseT", bound=BaseModel)

# See module docstring for how these two numbers were chosen.
MAX_CONCURRENT_WORKERS = 4
WORKER_TIMEOUT_SECONDS = 180.0

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_WORKERS)


def _thread_main(
    job: cancellation.Job, fut: asyncio.Future[Any], loop: asyncio.AbstractEventLoop,
    fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any],
) -> None:
    """The worker's thread: run `fn`, hand the outcome to the event loop unless the request
    gave up on it. Everything is inside the `except WorkCancelled`, so a cancellation that lands
    anywhere in here ends the thread quietly."""
    def deliver(setter: Callable[[Any], None], value: Any) -> None:
        def apply() -> None:
            if not fut.done():
                setter(value)

        try:
            loop.call_soon_threadsafe(apply)
        except RuntimeError:  # the loop is closed: nobody is waiting
            pass

    try:
        job.attach()
        cancellation.bind(job)
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — handed to the caller, as to_thread does
            job.detach()
            deliver(fut.set_exception, exc)
        else:
            job.detach()
            deliver(fut.set_result, result)
    except cancellation.WorkCancelled:
        job.detach()


async def run_bounded(fn: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
    """Run any sync callable off the event loop, bounded by the shared
    concurrency limit and timeout. Raises `asyncio.TimeoutError` on timeout —
    see `run_worker_bounded` for the `(body, status)` convenience wrapper. On a timeout, or if
    the caller is cancelled (the client left), the worker is told to stop (see the module
    docstring)."""
    if not runtime.THREADS:
        # Pyodide, in one visitor's browser: no threads to run on, and nobody to share
        # the machine with, so the worker runs inline, with no bound or timeout.
        return fn(*args, **kwargs)
    async with _semaphore:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[_T] = loop.create_future()
        job = cancellation.Job()
        context = contextvars.copy_context()
        threading.Thread(
            target=context.run, args=(_thread_main, job, fut, loop, fn, args, kwargs),
            name="worker-dispatch", daemon=True,
        ).start()
        try:
            return await asyncio.wait_for(fut, timeout=WORKER_TIMEOUT_SECONDS)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            job.cancel()
            raise


async def run_worker_bounded(domain_fn: WorkerFn, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """`(payload) -> (body, status)` worker contract, as used by every
    `routes/*.py` route, through `run_passthrough`/`run_typed` below."""
    over = work_budget.over_budget(payload)
    if over is not None:
        log.warning("worker_dispatch.over_budget", worker=getattr(domain_fn, "__name__", "?"), **over)
        return {"error": work_budget.refusal(over)}, 422
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
