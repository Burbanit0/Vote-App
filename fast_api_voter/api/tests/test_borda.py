"""Unit tests for the Borda count: a positional rule using linear weights
(rank k out of n candidates scores n-1-k). No dedicated test file existed
before -- CODE_AUDIT.md §7 item 6 flagged `simulation_ranked_utils.py`'s
`get_*_winner` family as under-tested ahead of a planned decomposition of
that file; Borda was only ever exercised as a supporting comparison inside
test_black.py/test_dowdall.py or via the axiom matrix, never in isolation."""

from api.engine.utils.simulation_ranked_utils import get_borda_winner, get_plurality_winner


def test_borda_rewards_broad_second_choice_support_over_a_narrow_plurality_lead():
    """A classic Borda-vs-plurality divergence: A leads on first preferences
    but is everyone else's last choice, while B is a strong second choice for
    both blocs that reject A. Plurality only counts first place and picks A;
    Borda's positional weights (2-1-0 over 3 candidates) let B's broad
    support overtake A's narrow bloc.

    Borda scores: A = 3*2 = 6; B = 3*1 + 2*2 + 2*1 = 9; C = 2*1 + 2*2 = 6.
    """
    ballots = [["A", "B", "C"]] * 3 + [["B", "C", "A"]] * 2 + [["C", "B", "A"]] * 2
    assert get_plurality_winner(ballots) == "A"
    assert get_borda_winner(ballots) == "B"


def test_borda_elects_the_unanimous_first_choice():
    ballots = [["A", "B", "C"], ["A", "C", "B"], ["A", "B", "C"]]
    assert get_borda_winner(ballots) == "A"


def test_borda_exact_tie_breaks_alphabetically():
    # Perfectly symmetric: each candidate is first once and last once ->
    # every candidate scores the same total.
    ballots = [["A", "B"], ["B", "A"]]
    assert get_borda_winner(ballots) == "A"


def test_borda_single_and_empty():
    assert get_borda_winner([]) is None
    assert get_borda_winner([["A"]]) == "A"


def test_borda_ballots_with_no_ranked_candidates():
    # Non-empty ballot list, but every ranking is itself empty -> no scores
    # ever get recorded, distinct from the get_borda_winner([]) case above.
    assert get_borda_winner([[], []]) is None


def test_borda_truncated_ballot_scores_by_its_own_length():
    """A truncated ballot scores its ranked candidates n-1-k with n the BALLOT's
    length, so its last-ranked candidate gets 0, the same as an unranked one.
    On complete ballots, any offset added to every score (n+1-k, n-2-k) never
    changes the winner; truncated ballots are the case where it does, so this
    pins the exact weights.

    Scores: ["A"] -> A 0; ["A", "C"] -> A 1, C 0; ["C", "B", "A"] -> C 2, B 1, A 0.
    Totals A 1, B 1, C 2 -> C. With n+1-k, A wins (7 vs C 6); with n-2-k, B
    (tied with C at 0, ahead alphabetically; A -2).
    """
    ballots = [["A"], ["A", "C"], ["C", "B", "A"]]
    assert get_borda_winner(ballots) == "C"
