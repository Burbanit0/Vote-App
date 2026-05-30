"""
blank_vote_rules.py — Post-election rules governing the blank vote.

The blank vote (vote blanc) expresses an active rejection of all candidates,
distinct from abstention (disengagement) and spoiled ballot (error).
This module defines what happens to the election result when blank participates.

Four constitutional frameworks are modelled:
    SYMBOLIC          — Current French law: blank is counted but cannot win.
    COMPETITIVE       — Blank is a full candidate; it can win the election.
    THRESHOLD_30      — If blank exceeds 30 %, the election is invalidated
                        regardless of who leads among real candidates.
    MAJORITY_REQUIRED — The elected candidate must beat blank in a direct
                        pairwise duel (majority prefers winner over "none").
"""
from enum import Enum
from typing import Any, Dict, Optional


class BlankVoteRule(Enum):
    SYMBOLIC          = "symbolic"
    COMPETITIVE       = "competitive"
    THRESHOLD_30      = "threshold_30"
    MAJORITY_REQUIRED = "majority_required"


_CONSEQUENCES: Dict[BlankVoteRule, Dict[bool, str]] = {
    BlankVoteRule.SYMBOLIC: {
        True:  "Election invalidated: the blank cannot be elected under current law. "
               "The runner-up among real candidates wins.",
        False: "Blank was counted symbolically but did not change the outcome.",
    },
    BlankVoteRule.COMPETITIVE: {
        True:  "Blank wins: all real candidates have been rejected by a plurality. "
               "Constitutional crisis — no government can be formed.",
        False: "Blank participated but did not win.",
    },
    BlankVoteRule.THRESHOLD_30: {
        True:  "Blank exceeded 30 %: the election is declared void. "
               "A new election must be held with new or revised candidatures.",
        False: "Blank remained below the 30 % threshold; the result stands.",
    },
    BlankVoteRule.MAJORITY_REQUIRED: {
        True:  "A majority of voters prefer blank over the declared winner. "
               "The mandate is contested; new candidatures are required.",
        False: "The winner commands more support than blank in a direct duel; "
               "the result is legitimate.",
    },
}


def apply_blank_rule(
    winner: Optional[str],
    blank_pct: float,
    rule: BlankVoteRule,
    blank_name: str = "Blank",
    blank_vs_winner_pct: float = 0.0,
) -> Dict[str, Any]:
    """
    Apply a constitutional blank-vote rule to an election result.

    Args:
        winner:              The raw winner produced by the voting method
                             (may be blank_name itself).
        blank_pct:           Fraction of voters whose first choice is blank
                             (or blank-equivalent approval), in [0, 1].
        rule:                The constitutional framework to apply.
        blank_name:          The string used to identify the blank candidate
                             (default "Blank").
        blank_vs_winner_pct: Fraction of voters who prefer blank over the
                             declared winner in a pairwise duel [0, 1].
                             Used only for MAJORITY_REQUIRED.

    Returns:
        {
            "winner":          str | None,  — effective winner after applying rule
            "blank_triggered": bool,        — True if blank invalidated the election
            "consequence":     str,         — human-readable explanation
            "blank_pct":       float,       — passed through for convenience
            "rule":            str,         — rule name
        }
    """
    blank_wins_raw = (winner == blank_name)
    triggered = False
    effective_winner = winner

    if rule == BlankVoteRule.SYMBOLIC:
        if blank_wins_raw:
            triggered = True
            effective_winner = None  # blank cannot be elected

    elif rule == BlankVoteRule.COMPETITIVE:
        # Blank participates as any candidate — no post-processing needed.
        triggered = blank_wins_raw

    elif rule == BlankVoteRule.THRESHOLD_30:
        if blank_pct >= 0.30:
            triggered = True
            effective_winner = None

    elif rule == BlankVoteRule.MAJORITY_REQUIRED:
        # Blank beats the winner in a direct duel → mandate contested.
        if blank_vs_winner_pct > 0.5:
            triggered = True
            effective_winner = None

    consequence = _CONSEQUENCES[rule][triggered]

    return {
        "winner":          effective_winner,
        "blank_triggered": triggered,
        "consequence":     consequence,
        "blank_pct":       round(blank_pct, 4),
        "rule":            rule.value,
    }
