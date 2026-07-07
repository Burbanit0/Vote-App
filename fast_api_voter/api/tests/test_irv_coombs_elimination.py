"""Elimination semantics for IRV and Coombs, aligned with the client engine via
the parity harness (voter-app/src/lib/playgroundVoting.parity.test.ts). Both now
eliminate ALL candidates tied at the extreme (neutral, candidate-order-independent).
"""

from api.engine.utils.simulation_ranked_utils import get_coombs_winner, get_irv_winner


def test_irv_eliminates_zero_first_pref_candidate():
    # D is every voter's last choice → 0 first-prefs. It must be eliminated, never
    # win. The previous code skipped 0-vote candidates from the min and instead
    # wiped the three tied-at-1 front-runners, absurdly electing D.
    profile = [["A", "B", "C", "D"], ["B", "C", "A", "D"], ["C", "A", "B", "D"]]
    assert get_irv_winner(profile) != "D"


def test_irv_basic_runoff():
    # No first-round majority; B is eliminated (fewest), its vote transfers to C.
    profile = [["A", "B", "C"]] * 2 + [["C", "B", "A"]] * 2 + [["B", "C", "A"]]
    assert get_irv_winner(profile) == "C"


def test_coombs_first_pref_majority_wins_immediately():
    profile = [["A", "B", "C"]] * 3 + [["B", "C", "A"]] * 2
    assert get_coombs_winner(profile) == "A"
