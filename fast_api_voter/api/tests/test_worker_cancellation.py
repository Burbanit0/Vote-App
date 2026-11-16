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


_BEFORE: set[int | None] = set()


@pytest.fixture(autouse=True)
def _threads_before_this_test():
    """Remember the threads alive at the start, so a straggler of an earlier test is not counted."""
    _BEFORE.clear()
    _BEFORE.update(t.ident for t in threading.enumerate())
    yield


def _worker_threads() -> list[threading.Thread]:
    """The dispatcher's threads started since this test began."""
    return [t for t in threading.enumerate() if t.name == "worker-dispatch" and t.ident not in _BEFORE]


async def _until(predicate, tries: int = 100) -> None:
    for _ in range(tries):
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("the condition never became true")


@pytest.mark.asyncio
async def test_baseline_a_plain_to_thread_worker_runs_on_after_its_timeout():
    """The premise of P4-3, kept as a test: what the dispatcher used to do (`asyncio.to_thread`
    under `wait_for`) leaves the worker running after the request timed out. The loop stops when
    the test says so, so the test itself leaves nothing behind."""
    counter = Counter()
    stop = threading.Event()

    def busy():
        while not stop.is_set():
            counter.n += 1

    try:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.to_thread(busy), timeout=0.1)
        assert await counter.settled() > 10_000, "the worker should have kept counting"
    finally:
        stop.set()


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
async def test_a_worker_that_cannot_be_interrupted_keeps_its_slot_until_it_ends(monkeypatch):
    """A long C call (here a sleep) does not see the cancellation until it returns. Its slot stays
    taken until then, so the next request waits for it and gets its own timeout, instead of another
    thread starting on top."""
    monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(wd, "_semaphore", asyncio.Semaphore(1))
    with pytest.raises(asyncio.TimeoutError):
        await wd.run_bounded(time.sleep, 0.6)  # times out, the thread still asleep
    started = time.monotonic()
    with pytest.raises(asyncio.TimeoutError):
        await wd.run_bounded(lambda: "never started")  # waits for the slot, then times out
    assert time.monotonic() - started >= 0.09 and len(_worker_threads()) == 1
    await _until(lambda: not _worker_threads(), tries=100)  # the sleeper wakes, is stopped, ends
    monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 5.0)
    assert await wd.run_bounded(lambda: "free again") == "free again"


@pytest.mark.asyncio
async def test_a_job_cancelled_before_its_thread_starts_never_runs(monkeypatch):
    ran: list[bool] = []
    job = cancellation.Job()
    job.cancel()  # cancelled before attach
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    sem = asyncio.Semaphore(0)
    thread = threading.Thread(target=wd._thread_main, args=(job, fut, loop, sem, lambda: ran.append(True), (), {}))
    thread.start()
    thread.join()
    await asyncio.sleep(0.05)
    assert not ran and not fut.done()
    assert not sem.locked(), "the slot was not given back"


@pytest.mark.asyncio
async def test_a_base_exception_from_the_worker_reaches_the_caller_and_frees_the_slot(monkeypatch):
    monkeypatch.setattr(wd, "_semaphore", asyncio.Semaphore(1))

    def exits():
        raise SystemExit(3)

    with pytest.raises(SystemExit):
        await wd.run_bounded(exits)
    assert await wd.run_bounded(lambda: "slot free") == "slot free"


@pytest.mark.asyncio
async def test_without_the_hard_stop_a_worker_that_polls_still_stops(monkeypatch):
    monkeypatch.setattr(cancellation, "RAISE_INTO_THREAD", False)
    monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 0.2)
    counter = Counter()

    def polite(_payload):
        check = cancellation.cancel_check()
        while True:
            check()
            counter.n += 1

    with pytest.raises(asyncio.TimeoutError):
        await wd.run_bounded(polite, {})
    assert await counter.settled() < 1000
    await _until(lambda: not _worker_threads())


@pytest.mark.asyncio
async def test_a_worker_that_outlives_its_loop_still_gives_the_slot_back():
    """The loop is closed by the time the thread ends (a test's, a shutdown's): the slot must not
    be lost, or the shared semaphore shrinks for good."""
    loop = asyncio.new_event_loop()
    loop.close()
    sem = asyncio.Semaphore(0)
    wd._release_slot(loop, sem)
    assert not sem.locked()


@pytest.mark.asyncio
async def test_a_thread_that_cannot_start_gives_the_slot_back(monkeypatch):
    sem = asyncio.Semaphore(1)
    monkeypatch.setattr(wd, "_semaphore", sem)

    def refuse(self):
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(threading.Thread, "start", refuse)
    with pytest.raises(RuntimeError, match="can't start"):
        await wd.run_bounded(lambda: 1)
    assert not sem.locked()


@pytest.mark.asyncio
async def test_a_cancellation_arriving_while_the_job_detaches_still_frees_the_slot():
    """The stop is posted at most once, but it can arrive in the middle of the final `detach`."""
    class LateJob(cancellation.Job):
        arrived = False

        def detach(self):
            if not LateJob.arrived and self._ident is None:
                LateJob.arrived = True
                raise cancellation.WorkCancelled
            super().detach()

    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(0)
    fut = loop.create_future()
    thread = threading.Thread(target=wd._thread_main, args=(LateJob(), fut, loop, sem, lambda: 1, (), {}))
    thread.start()
    thread.join()
    await asyncio.sleep(0.05)
    assert not sem.locked(), "the slot was not given back"


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
    wd._thread_main(job, fut, loop, asyncio.Semaphore(1), lambda: 1, (), {})  # no exception escapes


@pytest.mark.asyncio
async def test_a_result_for_a_request_that_already_gave_up_is_ignored():
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    fut.cancel()
    thread = threading.Thread(target=wd._thread_main, args=(cancellation.Job(), fut, loop, asyncio.Semaphore(1), lambda: 1, (), {}))
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
    assert status == 400 and "Request too large" in body["error"]
    assert not ran

    body, status = await wd.run_worker_bounded(
        worker, {"num_voters": MAX_NUM_VOTERS, "num_runs": MAX_NUM_RUNS}
    )
    assert status == 200 and ran == [True]
