"""Tests that a worker timeout surfaces as 503 through every router's error
handling (Lot 3, PLAN_SOLIDITE_TECHNIQUE.md — "Timeouts & backpressure").

api/tests/test_worker_dispatch.py already covers api/core/worker_dispatch.py
itself (the shared semaphore + timeout logic) in isolation. This file
instead proves each router's own (body, status) -> HTTPException handling
correctly maps a 503 through, one representative endpoint per router
(election.py, tech.py, theory.py, public.py, export.py — simulations.py's
_run_worker already propagates any status code generically and is covered
by its own existing tests).

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
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


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

    def test_tech_run_passthrough(self, client, force_timeout):
        r = client.post("/api/v2/tech/e2e-demo", json={})
        assert r.status_code == 503, r.text

    def test_theory_run_typed(self, client, force_timeout):
        r = client.post("/api/v2/theory/arrow", json={})
        assert r.status_code == 503, r.text

    def test_public_v1_run_passthrough(self, client, force_timeout):
        payload = {"num_candidates": 2, "num_voters": 50, "methods": ["plurality"]}
        r = client.post("/api/v1/simulate", json=payload)
        assert r.status_code == 503, r.text

    def test_export_csv(self, client, force_timeout):
        r = client.post("/api/v2/export/simulation-dataset", json={})
        assert r.status_code == 503, r.text

    def test_export_json(self, client, force_timeout):
        r = client.post("/api/v2/export/simulation-dataset-json", json={})
        assert r.status_code == 503, r.text
