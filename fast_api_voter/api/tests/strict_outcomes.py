"""What a rule elects when a tie is drawn by lot (LISTING_ORDER_TIES.md).

A rule's criteria (monotonicity, Condorcet-loser avoidance...) are claims about its
algorithm, not about the lot that settles a tie it cannot: a draw over a different pool
of tied candidates can name someone else after an innocent change to the ballots. So a
criterion is checked where the algorithm decides: on profiles with one possible winner.
`possible_winners` is every candidate some seed of the lot elects; a profile whose set
has one member has no tie for the lot to settle.
"""

from typing import Any, Callable, Optional

#: Enough seeds that every member of a tie among up to 4 names is drawn at least once
#: (a member missed by all 64 draws has probability (3/4)^64, about 1e-8).
SEEDS = range(64)


def possible_winners(rule: Callable[..., Optional[str]], rankings: Any) -> set[Optional[str]]:
    """Every winner `rule` gives `rankings` under some seed of the tie lot."""
    return {rule(rankings, seed=s) for s in SEEDS}


def strict_winner(rule: Callable[..., Optional[str]], rankings: Any) -> Optional[str]:
    """The winner when the rule elects the same candidate under every seed, else None
    (a tie the lot settles, or no winner at all)."""
    winners = possible_winners(rule, rankings)
    return next(iter(winners)) if len(winners) == 1 else None
