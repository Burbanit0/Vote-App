"""Tests that a worker timeout surfaces as 503 through every router's error
handling (Lot 3, PLAN_SOLIDITE_TECHNIQUE.md — "Timeouts & backpressure").

api/tests/test_worker_dispatch.py already covers api/core/worker_dispatch.py
itself (the shared semaphore + timeout logic) in isolation. This file instead
proves a 503 reaches the wire from every router that runs a worker — one
representative endpoint each for election.py, tech.py, theory.py, public.py
and simulations.py. All five now share `run_typed`/`run_passthrough`, so
these are no longer five independent implementations; what each one still
pins is that the route is actually wired through them (the GET on
simulations.py passes a plain payload rather than a request model, the one
shape that could quietly grow its own copy again).

Monkeypatches `asyncio.wait_for` (rather than shrinking
WORKER_TIMEOUT_SECONDS and racing against how fast the real worker happens
to run) so every route deterministically times out regardless of how cheap
its particular domain function is — confirmed live that a near-zero timeout
raced unreliably against genuinely fast workers (some endpoints beat even a
1ms timeout). `asyncio.wait_for` is the single call site `run_bounded` uses
internally, so patching it here covers every route uniformly in one place,
regardless of which module imported `run_bounded`/`run_worker_bounded`.
"""
import asyncio

import pytest



@pytest.fixture
def force_timeout(monkeypatch):
    async def _raise_timeout(coro, *args, **kwargs):
        coro.close()  # avoid a "coroutine was never awaited" warning
        raise asyncio.TimeoutError()
    monkeypatch.setattr(asyncio, "wait_for", _raise_timeout)


class TestWorkerTimeoutSurfacesAs503:
    def test_election_run_typed(self, client, force_timeout):
        payload = {"candidates": [{"name": "A", "x": -0.5, "y": 0.0},
                                   {"name": "B", "x": 0.5, "y": 0.0}]}
        r = client.post("/api/v2/election/simulate", json=payload)
        assert r.status_code == 503, r.text

    def test_tech_run_typed(self, client, force_timeout):
        cands = [{"name": "A", "x": -0.5, "y": 0.0}, {"name": "B", "x": 0.5, "y": 0.0}]
        r = client.post("/api/v2/tech/polis", json={"candidates": cands})
        assert r.status_code == 503, r.text

    def test_theory_run_typed(self, client, force_timeout):
        r = client.post("/api/v2/theory/arrow", json={})
        assert r.status_code == 503, r.text

    def test_public_v1_run_passthrough(self, client, force_timeout):
        payload = {"num_candidates": 2, "num_voters": 50, "methods": ["plurality"]}
        r = client.post("/api/v1/simulate", json=payload)
        assert r.status_code == 503, r.text

    def test_simulations_query_params(self, client, force_timeout):
        r = client.get("/api/v2/simulations/manipulability",
                       params={"num_candidates": 3, "num_voters": 60, "num_trials": 10})
        assert r.status_code == 503, r.text
