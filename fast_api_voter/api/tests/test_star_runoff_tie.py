"""STAR runoff tie-break, aligned with the client engine via the parity harness.

A tied automatic runoff is broken by SCORE: the higher-scored finalist wins. The
old code returned the lower-scored finalist on a tie (it used `>` not `>=`).
"""

from api.engine.utils.simulation_score_utils import get_star_voting_winner


def test_star_runoff_tie_goes_to_higher_score():
    # A is the higher-total finalist (8 vs 5). The runoff is tied 1–1 (one ballot
    # prefers each, one is equal) → STAR awards the tie to A on score.
    ballots = [{"A": 5, "B": 0}, {"A": 0, "B": 2}, {"A": 3, "B": 3}]
    assert get_star_voting_winner(ballots)["winner"] == "A"
