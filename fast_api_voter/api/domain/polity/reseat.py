"""Re-seat a run's recorded legislative votes under another electoral threshold
(PLAN_BEYOND_CI W2.1/W2.2 item 4): the mechanical effect of the threshold, on CPU.

Voters and founders do not see the new bar here -- that is the point. Where voters
deserted parties below the bar in force (ADR-024), a re-seat at another bar starts from
the vote before desertion (`sincere_votes`), so they do not see that bar either. The difference
between a re-seated run and a run actually played at that threshold is what the
agents did about it (the behavioural effect). OBS-040 did this by hand once.

The rules in force at each election are followed through the journal's own
`constitution_amended` events, replayed in journal order: an amended threshold, seat
method or assembly size governs every election journaled after it, its own tick's
included (the constitution phase runs before that tick's election). Seat ties draw from the same seeded lot
as the simulation (`legislative-seats:{seed}:{tick}`), so with the threshold left as
recorded the seats come back identical -- the check that this reads the run right.
"""
from __future__ import annotations

import random
from collections.abc import Iterable, Mapping
from typing import Any

from api.domain.polity.ballot_and_aggregation import allocate_seats
from api.domain.polity.metrics import effective_number_of_parties

_RULES = ("institutions.electoral_threshold", "institutions.seat_allocation", "institutions.assembly_seats")


def _enp(seats: Mapping[str, int]) -> float | None:
    """None, not 0.0, when no seat was won: the number of parties is then undefined."""
    return round(effective_number_of_parties({int(p): n for p, n in seats.items()}), 4) if sum(seats.values()) > 0 else None


def _election_row(
    event: Mapping[str, Any], rules: Mapping[str, Any], seed: int, threshold: float | None,
) -> dict[str, Any]:
    """One election re-seated under the rules in force, at `threshold` if one is given."""
    tick, payload = event["tick"], event["payload"]
    in_force = float(rules["institutions.electoral_threshold"])
    applied = in_force if threshold is None else threshold
    # The recorded vote reproduces the record; another bar starts from the vote no bar shaped (ADR-024).
    votes = payload["votes"] if threshold is None else payload.get("sincere_votes", payload["votes"])
    seats = allocate_seats(
        {str(party): float(count) for party, count in votes.items()},
        total_seats=int(rules["institutions.assembly_seats"]),
        method=str(rules["institutions.seat_allocation"]),
        electoral_threshold=applied,
        rng=random.Random(f"legislative-seats:{seed}:{tick}"),
    )
    recorded = {str(party): int(count) for party, count in payload["seats"].items()}
    return {
        "tick": tick,
        "threshold_in_force": in_force,
        "threshold_applied": applied,
        "recorded_seats": recorded,
        "reseated_seats": seats,
        "recorded_enp": _enp(recorded),
        "reseated_enp": _enp(seats),
        "recorded_parties_seated": sum(n > 0 for n in recorded.values()),
        "reseated_parties_seated": sum(n > 0 for n in seats.values()),
    }


def reseat(
    events: Iterable[Mapping[str, Any]], founding: Mapping[str, Any], *, threshold: float | None = None,
) -> list[dict[str, Any]]:
    """One row per legislative election: the recorded seats and the seats re-allocated from the
    same votes, at `threshold` (None: the threshold in force, which must reproduce the record).
    `founding` is the run's config.json; `events` its journal, in order."""
    institutions = founding["institutions"]
    rules: dict[str, Any] = {path: institutions[path.removeprefix("institutions.")] for path in _RULES}
    rows = []
    for event in events:
        if event["event_type"] == "constitution_amended" and event["payload"]["article"] in _RULES:
            rules[event["payload"]["article"]] = event["payload"]["new"]
        elif event["event_type"] == "legislative_result":
            rows.append(_election_row(event, rules, founding["run"]["seed"], threshold))
    return rows
