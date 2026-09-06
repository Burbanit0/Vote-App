"""Shared pytest fixtures for api/tests/.

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

from api.core.ratelimit import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()
