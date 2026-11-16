"""api.sockets.limits — how much one client address may run at once and how often it may start.

The HTTP routes are throttled by slowapi (api/core/ratelimit.py), which works on a Starlette
`Request`; a Socket.IO event has none, so the stream was the one expensive door with no limit at
all. This is the same idea in a few lines, kept in this process (like the stop flags beside it):
a sliding window of start times per client address, and a count of the runs still going.
"""
from __future__ import annotations

import time
from collections import deque

#: At most this many starts per address per window: the /api/v1 /simulate limit (10/minute).
MAX_STARTS = 10
WINDOW_SECONDS = 60.0
#: ...and this many runs still going at once (the app runs one at a time; a second tab, two).
MAX_LIVE = 2
#: Once this many addresses are held, the idle ones are forgotten (and again at double that).
_PRUNE_ABOVE = 10_000


class StartLimiter:
    def __init__(
        self, max_starts: int = MAX_STARTS, window: float = WINDOW_SECONDS, max_live: int = MAX_LIVE
    ) -> None:
        self._max = max_starts
        self._window = window
        self._max_live = max_live
        self._starts: dict[str, deque[float]] = {}
        self._live: dict[str, int] = {}
        self._prune_at = _PRUNE_ABOVE

    def allow(self, address: str, now: float | None = None) -> bool:
        """Record a start for `address` and return True, or return False (recording nothing)
        when it has `max_live` runs going or has started `max_starts` inside the window. Every
        True is to be paired with a `finish(address)` when that run ends."""
        now = time.monotonic() if now is None else now
        if self._live.get(address, 0) >= self._max_live:
            return False
        recent = self._starts.setdefault(address, deque())
        while recent and now - recent[0] >= self._window:
            recent.popleft()
        if len(recent) >= self._max:
            return False
        recent.append(now)
        self._live[address] = self._live.get(address, 0) + 1
        if len(self._starts) > self._prune_at:
            self._forget_idle(now)
        return True

    def finish(self, address: str) -> None:
        """A run that `allow` accepted has ended."""
        left = self._live.get(address, 0) - 1
        if left > 0:
            self._live[address] = left
        else:
            self._live.pop(address, None)

    def _forget_idle(self, now: float) -> None:
        idle = [
            a for a, r in self._starts.items()
            if a not in self._live and (not r or now - r[-1] >= self._window)
        ]
        for address in idle:
            del self._starts[address]
        self._prune_at = max(_PRUNE_ABOVE, 2 * len(self._starts))

    def clear(self) -> None:
        self._starts.clear()
        self._live.clear()
        self._prune_at = _PRUNE_ABOVE
