"""Shared pytest fixtures for api/tests/.

`client` is a plain `TestClient(app)`: 31 test modules each defined that same
fixture. `CANDS` is the three-candidate spatial trio the /api/v2/election
perturber suites all posted (7 identical copies).

slowapi's rate-limit counters live in a process-global `Limiter` (in-memory
storage by default — see api/core/ratelimit.py), so without a reset they
accumulate across the whole test session. Every test that hits a rate-limited
route (the /api/v1 public API, and since the v2 rate-limit rollout, every
/api/v2/simulations and /api/v2/election route) shares one counter per path,
so a test file with many calls to the same endpoint can trip a limit meant
for real per-IP abuse, not a fast local test run.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.core.ratelimit import limiter
from api.main import app

# A spatial trio: Alice left-ish, Bob right-ish, Carol near the centre.
CANDS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.1},
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()
