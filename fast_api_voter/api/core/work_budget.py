"""api.core.work_budget — a request too large to start.

Each schema bounds its own fields (`num_voters` 10-1000, `num_runs` 1-500, ...), but the work is
their product. This counts it in voter-repetitions (voters x the largest repetition field) and
refuses a request over `MAX_WORK_UNITS` before a thread is started.

The ceiling is the largest request the HTTP API accepts today, 500 runs x 1000 voters (measured at
34 s, see worker_dispatch), so nothing that is allowed now is refused: it stops a product that the
per-field bounds let through, such as a field added later, and it is the one number to lower if
the owner wants a smaller envelope.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: The 500 x 1000 of POST /simulations/monte-carlo at its documented maximum.
MAX_WORK_UNITS = 500_000

#: The fields that say how many times the electorate is processed.
REPETITION_FIELDS = (
    "num_runs", "num_iterations", "num_simulations", "num_elections", "num_polls", "num_options",
)


def _whole(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def work_units(payload: Mapping[str, Any]) -> int:
    """voters x repetitions, 0 when the payload has no voter count (nothing to size)."""
    voters = _whole(payload.get("num_voters"))
    if voters is None:
        return 0
    repetitions = max((_whole(payload.get(f)) or 1 for f in REPETITION_FIELDS), default=1)
    return voters * repetitions


def over_budget(payload: Mapping[str, Any]) -> dict[str, int] | None:
    """The numbers of a refused request, or None when it is within budget."""
    units = work_units(payload)
    return {"units": units, "limit": MAX_WORK_UNITS} if units > MAX_WORK_UNITS else None


def refusal(over: Mapping[str, int]) -> str:
    return (
        f"Request too large: about {over['units']:,} voter-repetitions "
        f"(num_voters x runs), the limit is {over['limit']:,}"
    )
