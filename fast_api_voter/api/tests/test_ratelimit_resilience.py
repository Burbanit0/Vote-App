"""Tests for rate-limiter resilience when its storage backend is unreachable
(Lot 3, PLAN_SOLIDITE_TECHNIQUE.md — "Résilience Redis").

Before this fix (api/core/ratelimit.py's `swallow_errors=True` + api/main.py's
`default_rate_limit_state` middleware), a storage failure raised a raw
redis.exceptions.ConnectionError out of slowapi's internals on every request
to every rate-limited route — Redis being unreachable took down the entire
/api/v2 surface and both /api/v1 endpoints, not just the throttling. Confirmed
live against a real unreachable Redis before writing this test.

Monkeypatches the limiter's own storage.incr (rather than pointing REDIS_URL
at a dead host) so this exercises the same failure regardless of whether the
test environment's limiter backend is memory:// or a real Redis — the
resilience code path being tested doesn't care which storage raised.
"""
import pytest
from fastapi.testclient import TestClient

from api.core.ratelimit import limiter
from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _boom(*args, **kwargs):
    raise ConnectionError("storage backend unreachable")


class TestRateLimiterResilience:
    def test_v2_route_survives_storage_failure(self, client, monkeypatch):
        monkeypatch.setattr(limiter.limiter.storage, "incr", _boom)
        r = client.post("/api/v2/simulations/get_closest_candidate", json={})
        # 400: the worker's own validation (empty voters/candidates), reached
        # normally — proves the request was NOT rejected by the rate limiter
        # or the app's catch-all 500 handler.
        assert r.status_code == 400, r.text

    def test_v1_route_survives_storage_failure(self, client, monkeypatch):
        monkeypatch.setattr(limiter.limiter.storage, "incr", _boom)
        payload = {"num_candidates": 2, "num_voters": 50, "methods": ["plurality"]}
        r = client.post("/api/v1/simulate", json=payload)
        assert r.status_code == 200, r.text
