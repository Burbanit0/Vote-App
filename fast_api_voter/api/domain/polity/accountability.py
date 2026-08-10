"""api.domain.polity.accountability — §7bis.5/§6bis.1: mandate deviation and
term limits. Lot 2 scope only: measurement, never mutation. `mandate_deviation`
is information given to citizens/analysts, not a pressure lever (§7bis.5) --
nothing here decides anything. Lot 4 adds the awakening gate that consumes
`self_gap`; Lot 6/7 add the LLM decisions that read `mandate_deviation`/
`is_term_limited`.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from api.domain.polity.citizen import Citizen, Office
from api.domain.polity.config import MandateConfig

_SUPPORTED_DEVIATION_METRICS = {"weighted_euclidean"}


def weighted_euclidean(a: Sequence[float], b: Sequence[float], weights: Sequence[float]) -> float:
    """sqrt(sum(w * (x-y)**2)) -- same math as simple_rules._weighted_distance,
    generalized to two arbitrary points instead of a citizen's own position.
    Not a refactor of that function this lot; test_polity_accountability.py
    pins the two implementations equal instead."""
    return math.sqrt(sum(w * (x - y) ** 2 for x, y, w in zip(a, b, weights)))


def current_office_holders(citizens: list[Citizen], office: Office) -> list[Citizen]:
    """Presidency returns 0-or-1 citizens today (Office.DEPUTY is never
    assigned) -- generalizes later without touching call sites."""
    return sorted((c for c in citizens if c.office is office), key=lambda c: c.citizen_id)


def pledge_weights(priorities: Sequence[float], config: MandateConfig) -> tuple[float, ...]:
    """§7bis.5's pledge_scope. full_platform passes priorities through
    unchanged (already sums to 1, dirichlet-drawn). top_k_priorities keeps
    only the pledge_top_k highest-priority dimensions (ties broken by
    ascending dimension index for determinism) and RENORMALIZES the
    survivors to sum to 1 -- without this, pledge_scope would silently
    become a scale change (a top-5 subset of dirichlet weights sums to
    ~0.25-0.3) rather than a scope change, and deviation_log_threshold
    would mean two different things depending on scope."""
    if config.pledge_scope == "full_platform":
        return tuple(priorities)
    if config.pledge_scope != "top_k_priorities":
        raise NotImplementedError(f"mandate.pledge_scope {config.pledge_scope!r} not supported")

    k = min(config.pledge_top_k, len(priorities))
    top_k_dims = {
        dim
        for dim, _ in sorted(enumerate(priorities), key=lambda item: (-item[1], item[0]))[:k]
    }
    kept = [p if dim in top_k_dims else 0.0 for dim, p in enumerate(priorities)]
    total = sum(kept)
    if total <= 0.0:
        return tuple(kept)
    return tuple(p / total for p in kept)


def mandate_deviation(officeholder: Citizen, config: MandateConfig) -> float:
    """§7bis.5: distance(pledged_platform, revealed_position(t)), weighted by
    the officeholder's own issue_priorities per pledge_weights. Provably 0
    throughout Lots 2-5: nothing sets revealed_position independently from
    pledged_platform until Lot 6's representative_response exists."""
    if config.deviation_metric not in _SUPPORTED_DEVIATION_METRICS:
        raise NotImplementedError(f"mandate.deviation_metric {config.deviation_metric!r} not supported")
    if officeholder.pledged_platform is None or officeholder.revealed_position is None:
        raise ValueError(f"citizen {officeholder.citizen_id} has no pledged_platform/revealed_position")
    weights = pledge_weights(officeholder.issue_priorities, config)
    return weighted_euclidean(officeholder.pledged_platform, officeholder.revealed_position, weights)


def self_gap(citizen: Citizen, officeholder: Citizen) -> float:
    """A citizen's own perceived distance between what they want
    (issue_positions) and what they're currently getting (the officeholder's
    revealed_position), weighted by the citizen's OWN priorities -- a
    different axis from mandate_deviation (the officeholder's own promise vs
    delivery). Full platform only: top-k is a pledge-specific concept, not a
    citizen's personal-gap concept. Unused until Lot 4's awakening gate."""
    if officeholder.revealed_position is None:
        raise ValueError(f"citizen {officeholder.citizen_id} has no revealed_position")
    return weighted_euclidean(citizen.issue_positions, officeholder.revealed_position, citizen.issue_priorities)


def is_term_limited(citizen: Citizen, term_limit: int | None) -> bool:
    """§6bis.1: a hard, always-on candidacy block, independent of the LLM --
    `term_limit=None` (shipped default) means illimité, always False. Doubles
    as the `lame_duck` predicate for a sitting officeholder (Lot 6 ctx)."""
    return term_limit is not None and citizen.mandates_served >= term_limit
