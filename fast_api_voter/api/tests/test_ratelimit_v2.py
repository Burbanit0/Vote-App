"""Tests for check_v2_rate_limit (api/core/ratelimit.py) — Lot 3, PLAN_SOLIDITE_TECHNIQUE.md.

The 120/minute value is calibrated (see the dependency's own docstring: a
first cut at 30/min measurably flaked playground-strategy.spec.ts), but
nothing previously tested that the limit actually fires — this closes that
gap, mirroring the existing /api/v1 pattern in test_public_v1.py's
TestRateLimits.

/api/v2/simulations/get_closest_candidate is used as the target: every field
has a default (empty voters/candidates), so `{}` is a valid, cheap request —
the worker 400s on empty input, but that happens *after* the rate-limit
dependency runs, so the count towards the limit is unaffected. slowapi keys
by path (key_style="url"), so this is isolated from every other v2 endpoint.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_v2_rate_limit_triggers_after_120(client):
    codes = [
        client.post("/api/v2/simulations/get_closest_candidate", json={}).status_code
        for _ in range(122)
    ]
    assert 429 in codes, f"Expected 429 within 122 requests (limit 120/min), got: {set(codes)}"
    # Everything before the limit trips is either the worker's own 400
    # (empty voters/candidates) or 429 once tripped — never something else,
    # which would mean the dependency isn't even running.
    assert set(codes) <= {400, 429}
