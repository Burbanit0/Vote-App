"""
api.domain.polity.ballot_and_aggregation — deterministic enclave #1 (Lot 5,
design doc §1 and §3.2).

Adapter, not reimplementation: this module only dispatches already-built
ballots to the existing, golden-fixture-tested engine/utils algorithms and
translates their result into a winner (presidential) or a seat allocation
(legislative, party-list). It has no idea how a ballot got built — that is
simple_rules.py's job (Lot 6) today, and llm_behavior_engine.py's from v2.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from api.engine.utils.simulation_multiwinner_utils import (
    get_dhondt_winners,
    get_largest_remainder_winners,
    get_sainte_lague_winners,
)
from api.engine.utils.simulation_ranked_utils import (
    get_approval_winner,
    get_baldwin_winner,
    get_borda_winner,
    get_bucklin_winner,
    get_coombs_winner,
    get_copeland_winner,
    get_irv_winner,
    get_kemeny_young_winner,
    get_minimax_winner,
    get_nanson_winner,
    get_plurality_winner,
    get_schulze_winner,
    get_two_round_winner,
)
from api.engine.utils.simulation_score_utils import (
    get_majority_judgment_winner,
    get_median_voting_winner,
    get_simple_score_winner,
    get_star_voting_winner,
)

# Ranked methods take list[list[str]] (a ranking per voter).
RANKED_METHODS: dict[str, Callable[[list[Any]], Optional[str]]] = {
    "plurality": get_plurality_winner,
    "two_round": get_two_round_winner,
    "borda": get_borda_winner,
    "approval": get_approval_winner,
    "irv": get_irv_winner,
    "coombs": get_coombs_winner,
    "bucklin": get_bucklin_winner,
    "minimax": get_minimax_winner,
    "schulze": get_schulze_winner,
    "kemeny_young": get_kemeny_young_winner,
    "copeland": get_copeland_winner,
    "nanson": get_nanson_winner,
    "baldwin": get_baldwin_winner,
}

# Score methods take list[dict[str, int | float]] (a score per candidate per
# voter) and return a result dict with a "winner" key, not a bare string.
SCORE_METHODS: dict[str, Callable[[list[Any]], dict[str, Any]]] = {
    "simple_score": get_simple_score_winner,
    "star": get_star_voting_winner,
    "median": get_median_voting_winner,
    "majority_judgment": get_majority_judgment_winner,
}

SEAT_ALLOCATIONS: dict[str, Callable[[dict[str, float], int], dict[str, int]]] = {
    "dhondt": get_dhondt_winners,
    "sainte_lague": get_sainte_lague_winners,
    "largest_remainder": get_largest_remainder_winners,
}


def get_presidential_winner(ballots: list[Any], method: str) -> Optional[str]:
    """Dispatch already-built ballots to the configured presidential method.
    `ballots` is list[list[str]] for every method except the four score-based
    ones (simple_score/star/median/majority_judgment), where it is
    list[dict[str, int | float]]."""
    ranked_fn = RANKED_METHODS.get(method)
    if ranked_fn is not None:
        return ranked_fn(ballots)
    score_fn = SCORE_METHODS.get(method)
    if score_fn is not None:
        winner = score_fn(ballots).get("winner")
        return str(winner) if winner is not None else None
    raise ValueError(f"unknown presidential_method: {method!r}")


def allocate_seats(
    vote_shares: dict[str, float], total_seats: int, method: str, electoral_threshold: float
) -> dict[str, int]:
    """Party-list seat allocation (design doc §6, resolves audit blocker A4).
    Parties below `electoral_threshold` (as a share of the total vote) get
    zero seats; the configured method allocates all `total_seats` among the
    parties that clear it. Every party in `vote_shares` is present in the
    result, defaulting to 0 seats."""
    allocate = SEAT_ALLOCATIONS.get(method)
    if allocate is None:
        raise ValueError(f"unknown seat_allocation method: {method!r}")

    total_votes = sum(v for v in vote_shares.values() if v > 0)
    if total_votes <= 0:
        return {party: 0 for party in vote_shares}

    qualifying = {
        party: votes
        for party, votes in vote_shares.items()
        if votes > 0 and votes / total_votes >= electoral_threshold
    }
    if not qualifying:
        return {party: 0 for party in vote_shares}

    awarded = allocate(qualifying, total_seats)
    return {party: awarded.get(party, 0) for party in vote_shares}
