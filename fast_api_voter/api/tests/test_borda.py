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
