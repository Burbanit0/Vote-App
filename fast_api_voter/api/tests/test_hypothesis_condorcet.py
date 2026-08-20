"""Property-based test — the Condorcet criterion.

Theory: any voting method that satisfies the Condorcet criterion must elect
the Condorcet winner whenever one exists (a candidate who beats every other
candidate in a pairwise majority comparison). Schulze, Copeland, and Minimax
are all Condorcet methods (THEORY.md §2.1) — this checks that guarantee holds
for randomly generated profiles, not just the hand-picked fixtures in
test_schulze_beatpath.py / test_black.py / etc.

Ground truth for "does a Condorcet winner exist, and who is it" comes from
get_condorcet_winner itself (already covered by its own unit tests) rather
than reimplementing pairwise-majority counting here.
"""
from hypothesis import assume, given, settings, strategies as st

from api.engine.utils.simulation_ranked_utils import (
    get_condorcet_winner,
    get_copeland_winner,
    get_minimax_winner,
    get_schulze_winner,
)

_CANDIDATES = ["A", "B", "C", "D"]

# Full rankings (permutations of all candidates) from 3 to 12 voters — enough
# to exercise both cycles and clear Condorcet winners without CI time blowing
# up (each example runs 3 winner functions on top of get_condorcet_winner).
_profiles = st.lists(st.permutations(_CANDIDATES), min_size=3, max_size=12)


@settings(max_examples=200, deadline=None)
@given(_profiles)
def test_condorcet_winner_is_elected_by_schulze_copeland_and_minimax(votes: list[list[str]]) -> None:
    condorcet_winner = get_condorcet_winner(votes)
    assume(condorcet_winner is not None)  # only meaningful when one exists
    assert get_schulze_winner(votes) == condorcet_winner
    assert get_copeland_winner(votes) == condorcet_winner
    assert get_minimax_winner(votes) == condorcet_winner
