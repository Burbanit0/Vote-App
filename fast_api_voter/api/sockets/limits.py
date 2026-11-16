"""api.sockets.limits — how often one client address may start a streaming Monte Carlo.

The HTTP routes are throttled by slowapi (api/core/ratelimit.py), which works on a Starlette
`Request`; a Socket.IO event has none, so the stream was the one expensive door with no limit at
all. This is the same idea in a few lines: a sliding window of start times per client address,
kept in this process (like the stop flags beside it).
"""
from __future__ import annotations

import time
from collections import deque

#: At most this many starts per address per window: the /api/v1 /simulate limit (10/minute).
MAX_STARTS = 10
WINDOW_SECONDS = 60.0
#: Past this many addresses seen, the ones whose window is empty are forgotten.
_PRUNE_ABOVE = 10_000


class StartLimiter:
    def __init__(self, max_starts: int = MAX_STARTS, window: float = WINDOW_SECONDS) -> None:
        self._max = max_starts
        self._window = window
        self._starts: dict[str, deque[float]] = {}

    def allow(self, address: str, now: float | None = None) -> bool:
        """Record a start for `address` and return True, or return False (recording nothing)
        when it has already started `max_starts` runs inside the window."""
        now = time.monotonic() if now is None else now
        recent = self._starts.setdefault(address, deque())
        while recent and now - recent[0] >= self._window:
            recent.popleft()
        if len(recent) >= self._max:
            return False
        recent.append(now)
        if len(self._starts) > _PRUNE_ABOVE:
            self._forget_idle(now)
        return True

    def _forget_idle(self, now: float) -> None:
        for address in [a for a, r in self._starts.items() if not r or now - r[-1] >= self._window]:
            del self._starts[address]

    def clear(self) -> None:
        self._starts.clear()
