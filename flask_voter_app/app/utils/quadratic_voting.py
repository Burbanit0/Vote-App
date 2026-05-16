"""
quadratic_voting.py — Quadratic Voting (QV) implementation.

Quadratic Voting was proposed by Lalley & Weyl (2018) and popularised in
"Radical Markets" (Posner & Weyl, 2018).  The key insight is that the cost
of expressing a preference grows quadratically with the number of votes cast,
which allows voters to signal *intensity* while limiting the dominance of
any single bloc.

Mechanic
--------
Each voter receives a budget of B credits.  Casting v votes for candidate c
costs v² credits.  The optimal allocation for sincere preferences is:

    votes[c] = floor( √B × u[c] / Σu ) + possible greedy bonus

where u[c] ∈ [0, 1] is the voter's utility for candidate c.

After the initial floor allocation, remaining credits are redistributed
greedily: at each step, the voter adds one vote to the candidate that
maximises  u[c] / marginal_cost(c),  where
marginal_cost(c) = 2 * votes[c] + 1  (the additional credit cost of the
next vote for c, since (v+1)² − v² = 2v + 1).

References
----------
Lalley, S. & Weyl, E. G. (2018). Quadratic voting: how mechanism design can
    radicalize democracy. AEA Papers and Proceedings, 108, 33–37.
Posner, E. A. & Weyl, E. G. (2018). Radical Markets: Uprooting Capitalism
    and Democracy for a Just Society. Princeton University Press.
"""
from __future__ import annotations

import math
from typing import Any, Optional


def apply_quadratic_voting(
    utilities: list[dict[str, float]],
    budget: int = 100,
) -> dict[str, Any]:
    """
    Simulate Quadratic Voting on a population with known sincere utilities.

    Parameters
    ----------
    utilities : list[dict[str, float]]
        One dict per voter.  Keys are candidate names, values are utilities
        in [0, 1] derived from the spatial model.
    budget : int
        Credit budget per voter (default 100).

    Returns
    -------
    dict with keys:
        winner               : str | None   — candidate with most QV votes
        scores               : dict[str, float]   — total QV votes per candidate
        total_credits_used   : float  — average credits spent per voter
        credit_distribution  : dict[str, float]  — avg credits per candidate per voter
    """
    if not utilities:
        return _empty_result()

    candidates = list(utilities[0].keys())
    n_candidates = len(candidates)
    if n_candidates == 0:
        return _empty_result()

    n_voters = len(utilities)
    total_qv_votes: dict[str, float] = {c: 0.0 for c in candidates}
    total_credits_spent: dict[str, float] = {c: 0.0 for c in candidates}
    total_budget_used = 0.0
    sqrt_b = math.sqrt(budget)

    for voter_utils in utilities:
        util_sum = sum(voter_utils.get(c, 0.0) for c in candidates)
        if util_sum <= 0:
            # No preference — distribute equally
            util_values = {c: 1.0 / n_candidates for c in candidates}
            util_sum = 1.0
        else:
            util_values = {c: voter_utils.get(c, 0.0) for c in candidates}

        # Initial allocation: floor(√B × u[c] / Σu)
        votes: dict[str, int] = {
            c: int(sqrt_b * util_values[c] / util_sum)
            for c in candidates
        }

        # Credits consumed by initial allocation
        credits_used = sum(v * v for v in votes.values())
        remaining = budget - credits_used

        # Greedy redistribution of leftover credits
        while remaining > 0:
            best_c: Optional[str] = None
            best_ratio = -1.0
            for c in candidates:
                marginal_cost = 2 * votes[c] + 1   # cost of one more vote
                if marginal_cost <= remaining:
                    ratio = util_values[c] / marginal_cost
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_c = c
            if best_c is None:
                break
            votes[best_c] += 1
            marginal = 2 * (votes[best_c] - 1) + 1
            credits_used += marginal
            remaining -= marginal

        # Accumulate
        for c in candidates:
            total_qv_votes[c] += votes[c]
            total_credits_spent[c] += votes[c] * votes[c]
        total_budget_used += credits_used

    # Determine winner (most total QV votes; tie → alphabetical first)
    winner: Optional[str] = max(candidates, key=lambda c: total_qv_votes[c]) \
        if candidates else None

    avg_credits: dict[str, float] = {
        c: round(total_credits_spent[c] / n_voters, 3)
        for c in candidates
    }

    return {
        "winner":             winner,
        "scores":             {c: round(total_qv_votes[c], 2) for c in candidates},
        "total_credits_used": round(total_budget_used / n_voters, 2),
        "credit_distribution": avg_credits,
    }


# ── Gini coefficient helper ───────────────────────────────────────────────────

def gini_coefficient(values: list[float]) -> float:
    """
    Compute the Gini coefficient (0 = perfect equality, 1 = maximum inequality)
    for a list of non-negative values.  Returns 0.0 for empty or zero-sum lists.

    Formula (sorted ascending, 1-indexed):
        G = (2 × Σᵢ i·xᵢ) / (n × Σxᵢ) − (n + 1) / n
    """
    n = len(values)
    if n < 2:
        return 0.0
    total = sum(values)
    if total <= 0:
        return 0.0
    sorted_v = sorted(values)
    # 1-indexed sum: Σ_{i=1}^{n} i · x_(i)
    weighted = sum((i + 1) * v for i, v in enumerate(sorted_v))
    return round(2.0 * weighted / (n * total) - (n + 1) / n, 4)


# ── Private helpers ───────────────────────────────────────────────────────────

def _empty_result() -> dict[str, Any]:
    return {
        "winner": None,
        "scores": {},
        "total_credits_used": 0.0,
        "credit_distribution": {},
    }
