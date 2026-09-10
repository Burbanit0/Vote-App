"""Tests for api/core/worker_dispatch.py (Lot 3, PLAN_SOLIDITE_TECHNIQUE.md —
"Timeouts & backpressure")."""
import asyncio
import time

import pytest

import api.core.worker_dispatch as wd


def _sleepy(seconds: float):
    def worker(payload):
        time.sleep(seconds)
        return {"ok": True, "payload": payload}, 200
    return worker


class TestRunBounded:
    @pytest.mark.asyncio
    async def test_returns_the_callable_result(self):
        def add(a, b):
            return a + b
        assert await wd.run_bounded(add, 2, 3) == 5

    @pytest.mark.asyncio
    async def test_raises_timeout_error_when_exceeded(self, monkeypatch):
        monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 0.01)
        with pytest.raises(asyncio.TimeoutError):
            await wd.run_bounded(_sleepy(0.2), {})

    @pytest.mark.asyncio
    async def test_bounds_concurrency_to_the_semaphore_size(self, monkeypatch):
        """N+1 concurrent calls to a worker that blocks until released proves
        at most MAX_CONCURRENT_WORKERS run at once: the (N+1)th can only
        start once one of the first N has been let through."""
        monkeypatch.setattr(wd, "MAX_CONCURRENT_WORKERS", 2)
        monkeypatch.setattr(wd, "_semaphore", asyncio.Semaphore(2))

        started = 0
        max_concurrent = 0

        def worker(_payload):
            nonlocal started, max_concurrent
            started += 1
            max_concurrent = max(max_concurrent, started)
            time.sleep(0.05)
            started -= 1
            return {}, 200

        tasks = [asyncio.create_task(wd.run_bounded(worker, {})) for _ in range(4)]
        await asyncio.gather(*tasks)
        assert max_concurrent <= 2


class TestRunWorkerBounded:
    @pytest.mark.asyncio
    async def test_passes_through_a_normal_result(self):
        def worker(payload):
            return {"echo": payload}, 200
        body, status = await wd.run_worker_bounded(worker, {"x": 1})
        assert (body, status) == ({"echo": {"x": 1}}, 200)

    @pytest.mark.asyncio
    async def test_timeout_becomes_a_503_tuple(self, monkeypatch, caplog):
        monkeypatch.setattr(wd, "WORKER_TIMEOUT_SECONDS", 0.01)
        body, status = await wd.run_worker_bounded(_sleepy(0.2), {})
        assert status == 503
        assert "error" in body
        assert "worker_dispatch.timeout" in caplog.text
