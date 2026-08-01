"""
api.domain.polity.metrics — the v0 subset of output metrics (Lot 9, design
doc §10).

Only the three metrics computable without an LLM or legitimacy (both off in
v0): effective number of parties, cohabitation rate, coalition lifespans.
Every other row of §10's table depends on mandate_deviation, L(t), or
pressure_action — all v4+.

Pure functions over caller-assembled observations, not journal readers: an
indexer that replays the raw journal into these shapes is indexer.py's job,
which is not part of the v0 lot breakdown.
"""
from __future__ import annotations


def effective_number_of_parties(seats: dict[int, int]) -> float:
    """Laakso & Taagepera (1979): N = 1 / sum(share_i^2) over seat shares.
    2 parties at 50/50 seats -> N = 2.0 (the dev-plan's own worked example)."""
    total = sum(seats.values())
    if total == 0:
        return 0.0
    return 1.0 / sum((s / total) ** 2 for s in seats.values())


def is_cohabitation(president_party_id: int | None, coalition: list[int] | None) -> bool:
    """design doc §6: cohabitation is a president whose own party is not
    part of the governing coalition. Neither a vacant presidency nor a
    failed coalition (coalition_failed, §4 point 3) counts as cohabitation
    — there is no government to be at odds with the president."""
    if president_party_id is None or coalition is None:
        return False
    return president_party_id not in coalition


def cohabitation_rate(observations: list[bool]) -> float:
    """Fraction of observed periods (design doc §10: cumulative) under
    cohabitation. Each observation should weight equal time (e.g. one tick,
    or one inter-election period of fixed length) — this function does not
    itself weight by duration."""
    if not observations:
        return 0.0
    return sum(observations) / len(observations)


def coalition_lifespans(events: list[tuple[int, list[int] | None]], total_ticks: int) -> list[int]:
    """`events`: chronological (tick, coalition) pairs, one per legislative
    election, coalition None for a coalition_failed outcome. Returns the
    duration in ticks of each coalition that actually formed — until the
    next legislative election, or until the end of the run for the last
    one. A coalition_failed event produces no lifespan entry."""
    lifespans = []
    for i, (tick, coalition) in enumerate(events):
        if coalition is None:
            continue
        next_tick = events[i + 1][0] if i + 1 < len(events) else total_ticks
        lifespans.append(next_tick - tick)
    return lifespans
