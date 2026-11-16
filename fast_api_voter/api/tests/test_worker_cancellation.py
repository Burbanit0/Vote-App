"""A timed-out request's worker stops (api/core/cancellation.py, P4-3), and an over-budget request
is refused before a thread starts (api/core/work_budget.py).

Before P4-3 a worker kept running to the end after its request got a 503: measured with a busy
loop, its counter went from 10.9M to 40.1M in the half second after the timeout. The tests below
use the same shape: a pure-Python loop that counts, and a check that the count stops.
"""
from __future__ import annotations

import asyncio
import threading
import time

import pytest

import api.core.worker_dispatch as wd
from api.core import cancellation, work_budget
from api.schemas.simulations import MAX_NUM_RUNS, MAX_NUM_VOTERS


class Counter:
    def __init__(self) -> None:
        self.n = 0

    def busy(self, _payload):
        while True:
            self.n += 1

    async def settled(self, pause: float = 0.3) -> int:
        """How far the count moved over `pause` seconds."""
        before = self.n
        await asyncio.sleep(pause)
        return self.n - before


def _worker_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "worker-dispatch"]


async def _until(predicate, tries: int = 100) -> None:
    for _ in range(tries):
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("the condition never became true")


@pytest.mark.asyncio
async def test_a_timed_out_worker_stops_consuming_cpu(monkeypatch):
    monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 0.2)
    counter = Counter()
    with pytest.raises(asyncio.TimeoutError):
        await wd.run_bounded(counter.busy, {})
    assert await counter.settled() < 1000, "the worker is still counting after its request timed out"
    await _until(lambda: not _worker_threads())


@pytest.mark.asyncio
async def test_a_worker_whose_client_left_stops_too(monkeypatch):
    counter = Counter()
    task = asyncio.create_task(wd.run_bounded(counter.busy, {}))
    await _until(lambda: counter.n > 0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await counter.settled() < 1000
    await _until(lambda: not _worker_threads())


@pytest.mark.asyncio
async def test_a_worker_that_swallows_exceptions_still_stops(monkeypatch):
    """`WorkCancelled` is a BaseException: the worker's own `except Exception` cannot eat it."""
    monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 0.2)
    counter = Counter()

    def stubborn(_payload):
        while True:
            try:
                counter.n += 1
            except Exception:  # noqa: BLE001
                pass

    with pytest.raises(asyncio.TimeoutError):
        await wd.run_bounded(stubborn, {})
    assert await counter.settled() < 1000


@pytest.mark.asyncio
async def test_the_semaphore_slot_is_free_after_a_timeout(monkeypatch):
    monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(wd, "_semaphore", asyncio.Semaphore(1))
    with pytest.raises(asyncio.TimeoutError):
        await wd.run_bounded(Counter().busy, {})
    monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 5.0)
    assert await wd.run_bounded(lambda: "next") == "next"


@pytest.mark.asyncio
async def test_a_worker_exception_reaches_the_caller():
    def boom():
        raise ValueError("bad")

    with pytest.raises(ValueError, match="bad"):
        await wd.run_bounded(boom)


@pytest.mark.asyncio
async def test_context_variables_reach_the_worker_thread():
    import contextvars

    var: contextvars.ContextVar[str] = contextvars.ContextVar("v", default="unset")
    var.set("request-scoped")
    assert await wd.run_bounded(var.get) == "request-scoped"


@pytest.mark.asyncio
async def test_a_result_arriving_after_the_loop_closed_is_dropped_quietly():
    """The worker finishing when nobody is waiting (the loop is gone) must not raise in its
    thread."""
    loop = asyncio.new_event_loop()
    fut = loop.create_future()
    loop.close()
    job = cancellation.Job()
    wd._thread_main(job, fut, loop, lambda: 1, (), {})  # no exception escapes


@pytest.mark.asyncio
async def test_a_result_for_a_request_that_already_gave_up_is_ignored():
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    fut.cancel()
    thread = threading.Thread(target=wd._thread_main, args=(cancellation.Job(), fut, loop, lambda: 1, (), {}))
    thread.start()
    thread.join()
    await asyncio.sleep(0.05)  # the loop runs what the thread scheduled
    assert fut.cancelled()


# ── the pieces ───────────────────────────────────────────────────────────────

def test_cancel_check_is_a_no_op_outside_a_dispatched_worker():
    cancellation.cancel_check()()


def test_cancel_check_raises_from_any_thread_once_the_job_is_cancelled():
    job = cancellation.Job()
    cancellation.bind(job)
    try:
        check = cancellation.cancel_check()
        check()  # not cancelled yet
        job.cancelled.set()
        raised: list[bool] = []

        def from_pool_thread():
            try:
                check()
            except cancellation.WorkCancelled:
                raised.append(True)

        t = threading.Thread(target=from_pool_thread)
        t.start()
        t.join()
        assert raised == [True]
    finally:
        cancellation.bind(None)  # type: ignore[arg-type]


def test_a_cancel_after_the_work_has_returned_raises_nothing_into_the_thread():
    job = cancellation.Job()
    done = threading.Event()
    survived: list[bool] = []

    def run():
        job.attach()
        job.detach()
        done.wait(2)
        time.sleep(0.05)  # bytecode after the cancel, where a stray exception would land
        survived.append(True)

    t = threading.Thread(target=run)
    t.start()
    time.sleep(0.05)
    job.cancel()
    done.set()
    t.join()
    assert survived == [True]


# ── the Monte Carlo's own pool ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_timed_out_monte_carlo_does_not_work_through_its_queued_runs(monkeypatch):
    """The Monte Carlo fans out to a ThreadPoolExecutor, whose threads the dispatcher cannot reach:
    its runs poll the cancel flag, so the ones still queued are skipped."""
    import api.domain.simulations.advanced as advanced

    calls = 0

    def slow_run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        time.sleep(0.02)
        return {"methods": {}, "condorcet_winner": None}

    monkeypatch.setattr(advanced, "compare_all_methods_mc", slow_run)
    monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 0.3)
    payload = {"num_runs": 500, "num_voters": 10, "candidates": ["Alice", "Bob", "Carol"]}
    with pytest.raises(asyncio.TimeoutError):
        await wd.run_bounded(advanced._monte_carlo_worker, payload)
    at_timeout = calls
    await asyncio.sleep(0.5)
    assert calls - at_timeout <= 8, (
        f"{calls - at_timeout} more runs after the timeout: the queued runs were not skipped"
    )
    assert at_timeout < 500


# ── the budget ───────────────────────────────────────────────────────────────

def test_the_ceiling_is_the_largest_request_http_accepts():
    assert work_budget.MAX_WORK_UNITS == MAX_NUM_RUNS * MAX_NUM_VOTERS


@pytest.mark.parametrize("payload,units", [
    ({"num_voters": 1000, "num_runs": 500}, 500_000),
    ({"num_voters": 200, "num_simulations": 50, "num_runs": 10}, 10_000),  # the largest repetition
    ({"num_voters": 300}, 300),
    ({"num_runs": 500}, 0),  # no voter count: nothing to size
    ({"num_voters": True, "num_runs": 5}, 0),
    ({"num_voters": -5, "num_runs": 5}, 0),
    ({"num_voters": "1000", "num_runs": 500}, 0),
])
def test_work_units(payload, units):
    assert work_budget.work_units(payload) == units


@pytest.mark.asyncio
async def test_a_request_over_budget_is_refused_before_a_thread_starts():
    ran: list[bool] = []

    def worker(payload):
        ran.append(True)
        return {"ok": True}, 200

    body, status = await wd.run_worker_bounded(
        worker, {"num_voters": MAX_NUM_VOTERS, "num_runs": MAX_NUM_RUNS + 1}
    )
    assert status == 422 and "Request too large" in body["error"]
    assert not ran and not _worker_threads()

    body, status = await wd.run_worker_bounded(
        worker, {"num_voters": MAX_NUM_VOTERS, "num_runs": MAX_NUM_RUNS}
    )
    assert status == 200 and ran == [True]
