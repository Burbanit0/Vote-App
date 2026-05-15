"""
gibbard_satterthwaite.py — Empirical manipulability estimation.

Gibbard (1973) and Satterthwaite (1975) proved that any deterministic,
non-dictatorial voting rule with ≥ 3 alternatives is manipulable — there
always exist situations where a voter can improve their outcome by submitting
a non-sincere ballot.

This module estimates the *empirical* manipulability rate for common voting
methods: the proportion of sampled voters who can improve their outcome by
swapping adjacent candidates in their ranking.

Note on ballot format
---------------------
``ballots`` is ``list[list[str]]`` — each inner list is a voter's ranking
of candidate names in preference order (most preferred first), identical to
the format used throughout the simulation pipeline.  The public docstring
uses ``list[list[int]]`` as a generic abstraction but the implementation
works with string candidate names.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Optional


# ── Method dispatch ──────────────────────────────────────────────────────────

def _get_ranked_method(method_name: str) -> Optional[Callable[..., Optional[str]]]:
    """Return the winner function for a ranked-ballot method key, or None."""
    from app.utils.simulation_ranked_utils import (
        get_plurality_winner,
        get_borda_winner,
        get_irv_winner,
        get_two_round_winner,
        get_approval_winner,
        get_coombs_winner,
        get_bucklin_winner,
        get_minimax_winner,
        get_schulze_winner,
        get_condorcet_winner,
        get_positional_score_winner,
    )

    _RANKED_METHODS: dict[str, Callable[..., Any]] = {
        "plurality":        get_plurality_winner,
        "borda":            get_borda_winner,
        "irv":              get_irv_winner,
        "two_round":        get_two_round_winner,
        "approval":         get_approval_winner,
        "coombs":           get_coombs_winner,
        "bucklin":          get_bucklin_winner,
        "minimax":          get_minimax_winner,
        "schulze":          get_schulze_winner,
        "condorcet":        get_condorcet_winner,
        "positional_score": get_positional_score_winner,
    }
    return _RANKED_METHODS.get(method_name)


# ── Core algorithm ───────────────────────────────────────────────────────────

def compute_manipulability_index(
    method_name: str,
    ballots: list[list[str]],
    num_trials: int = 200,
) -> dict[str, Any]:
    """
    Estimate the manipulability rate of a voting method.

    For each sampled voter *i*, the algorithm:
      1. Computes the sincere winner using all voters' honest rankings.
      2. Generates up to 3 alternative ballots by swapping adjacent pairs
         in voter *i*'s ranking (e.g. [A, B, C] → [B, A, C]).
      3. For each alternative, replaces voter *i*'s ballot and re-runs
         the election.  If the new winner is ranked *higher* in voter *i*'s
         *sincere* preferences, the voter is counted as a potential manipulator.
      4. Each voter is counted at most once even if multiple alternatives work.

    Parameters
    ----------
    method_name : str
        Method key (e.g. "plurality", "borda", "irv", "schulze", …).
    ballots : list[list[str]]
        Sincere ranked ballots — one list of candidate names per voter,
        sorted from most to least preferred.
    num_trials : int
        Maximum number of voters to sample.  Use a smaller value for speed;
        larger values give more accurate estimates at the cost of time.

    Returns
    -------
    dict with keys:
        method              : str
        manipulability_rate : float  — % of sampled voters who can manipulate
        average_gain        : float  — average rank improvement among manipulators
        num_manipulators    : int
        num_sampled         : int
        examples            : list[dict]  — up to 3 concrete examples
        error               : str         — present only on failure
    """
    method_fn = _get_ranked_method(method_name)
    if method_fn is None:
        return {
            "method": method_name,
            "manipulability_rate": None,
            "average_gain": 0.0,
            "num_manipulators": 0,
            "num_sampled": 0,
            "examples": [],
            "error": f"Unknown or unsupported method: '{method_name}'",
        }

    n_voters = len(ballots)
    if n_voters == 0:
        return _empty_result(method_name, 0)

    n_candidates = len(ballots[0]) if ballots else 0
    if n_candidates < 2:
        return _empty_result(method_name, min(n_voters, num_trials))

    # ── Sample voters ──────────────────────────────────────────────────────
    sample_indices = list(range(n_voters))
    if n_voters > num_trials:
        sample_indices = random.sample(sample_indices, num_trials)

    # ── Compute sincere winner (all ballots, no manipulation) ──────────────
    try:
        sincere_winner: Optional[str] = method_fn(ballots)
    except Exception:
        sincere_winner = None

    # ── Test each sampled voter ────────────────────────────────────────────
    num_manipulators = 0
    total_gain = 0.0
    examples: list[dict[str, Any]] = []

    for voter_idx in sample_indices:
        sincere_ballot = ballots[voter_idx]

        # Where does the sincere winner appear in this voter's honest ranking?
        sincere_rank = _rank_of(sincere_winner, sincere_ballot)

        # Voter already gets first choice → zero incentive to manipulate.
        if sincere_rank == 0:
            continue

        # Generate alternative ballots (up to 3) by swapping adjacent pairs.
        manipulated = False
        for swap_pos in range(min(3, len(sincere_ballot) - 1)):
            alt_ballot = list(sincere_ballot)
            alt_ballot[swap_pos], alt_ballot[swap_pos + 1] = (
                alt_ballot[swap_pos + 1],
                alt_ballot[swap_pos],
            )

            # Replace voter's ballot and re-run the election.
            test_ballots = list(ballots)
            test_ballots[voter_idx] = alt_ballot

            try:
                new_winner: Optional[str] = method_fn(test_ballots)
            except Exception:
                continue

            if new_winner is None or new_winner == sincere_winner:
                continue

            # Does the new winner rank higher in the voter's *sincere* ballot?
            strategic_rank = _rank_of(new_winner, sincere_ballot)
            if strategic_rank < sincere_rank:
                gain = sincere_rank - strategic_rank
                num_manipulators += 1
                total_gain += gain
                if len(examples) < 3:
                    examples.append({
                        "voter_id": voter_idx,
                        "sincere_rank": sincere_rank,
                        "strategic_rank": strategic_rank,
                        "sincere_winner": sincere_winner,
                        "strategic_winner": new_winner,
                    })
                manipulated = True
                break  # Count each voter at most once.

        _ = manipulated  # suppress unused-variable warning

    n_sampled = len(sample_indices)
    rate = (num_manipulators / n_sampled * 100) if n_sampled > 0 else 0.0
    avg_gain = (total_gain / num_manipulators) if num_manipulators > 0 else 0.0

    return {
        "method": method_name,
        "manipulability_rate": round(rate, 2),
        "average_gain": round(avg_gain, 3),
        "num_manipulators": num_manipulators,
        "num_sampled": n_sampled,
        "examples": examples,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _rank_of(candidate: Optional[str], ballot: list[str]) -> int:
    """Position of *candidate* in *ballot* (0 = first choice).  Returns last position if absent."""
    if candidate is None:
        return len(ballot)
    try:
        return ballot.index(candidate)
    except ValueError:
        return len(ballot)


def _empty_result(method_name: str, n_sampled: int) -> dict[str, Any]:
    return {
        "method": method_name,
        "manipulability_rate": 0.0,
        "average_gain": 0.0,
        "num_manipulators": 0,
        "num_sampled": n_sampled,
        "examples": [],
    }
