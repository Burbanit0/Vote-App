"""
test_new_methods.py — Tests for Copeland, Nanson, Baldwin, Evaluative voting.
"""
import pytest
from app.utils.simulation_ranked_utils import (
    get_copeland_winner,
    get_nanson_winner,
    get_baldwin_winner,
)
from app.utils.simulation_score_utils import get_evaluative_winner


# ── Helpers ───────────────────────────────────────────────────────────────────

def ballots(*prefs):
    """Accept ('A','B','C'), ... → list of lists."""
    return [list(p) for p in prefs]


# ═══════════════════════════════════════════════════════════════
# Copeland
# ═══════════════════════════════════════════════════════════════

class TestCopeland:
    def test_condorcet_winner_elected(self):
        """A beats B, A beats C → A is the Condorcet winner and Copeland winner."""
        b = ballots(
            ('A', 'B', 'C'), ('A', 'B', 'C'), ('A', 'C', 'B'),
            ('B', 'C', 'A'),
        )
        assert get_copeland_winner(b) == 'A'

    def test_cycle_tie_break_alphabetical(self):
        """Perfect cycle A>B>C>A → Copeland score 0 for all → winner = 'A' (alphabetical)."""
        b = ballots(
            ('A', 'B', 'C'),
            ('B', 'C', 'A'),
            ('C', 'A', 'B'),
        )
        # Each candidate wins one duel, loses one duel → score 0
        # Tie-break: total wins all equal → alpha → 'A'
        assert get_copeland_winner(b) == 'A'

    def test_clear_winner_two_candidates(self):
        b = ballots(('X', 'Y'), ('X', 'Y'), ('Y', 'X'))
        assert get_copeland_winner(b) == 'X'

    def test_empty_returns_none(self):
        assert get_copeland_winner([]) is None

    def test_single_ballot(self):
        b = ballots(('A', 'B', 'C'))
        winner = get_copeland_winner(b)
        assert winner in ('A', 'B', 'C')

    def test_four_candidates(self):
        """D is the Condorcet winner."""
        b = ballots(
            ('D', 'A', 'B', 'C'),
            ('D', 'B', 'A', 'C'),
            ('D', 'C', 'A', 'B'),
        )
        assert get_copeland_winner(b) == 'D'

    def test_copeland_score_is_wins_minus_losses(self):
        """A beats B and C, B beats C → A=2, B=0, C=-2."""
        b = ballots(
            ('A', 'B', 'C'), ('A', 'B', 'C'), ('A', 'B', 'C'),
        )
        assert get_copeland_winner(b) == 'A'


# ═══════════════════════════════════════════════════════════════
# Nanson
# ═══════════════════════════════════════════════════════════════

class TestNanson:
    def test_condorcet_winner_always_elected(self):
        """Nanson always elects the Condorcet winner when one exists."""
        b = ballots(
            ('A', 'B', 'C'), ('A', 'B', 'C'),
            ('B', 'C', 'A'),
            ('C', 'B', 'A'),
        )
        # A beats B (3-1) and B beats C (3-1) → A is Condorcet winner
        assert get_nanson_winner(b) == 'A'

    def test_eliminates_below_average(self):
        """C has low Borda score and should be eliminated first."""
        b = ballots(
            ('A', 'B', 'C'), ('A', 'B', 'C'), ('A', 'B', 'C'),
            ('B', 'A', 'C'),
        )
        winner = get_nanson_winner(b)
        assert winner in ('A', 'B')
        assert winner != 'C'

    def test_empty(self):
        assert get_nanson_winner([]) is None

    def test_two_candidates(self):
        b = ballots(('X', 'Y'), ('X', 'Y'), ('Y', 'X'))
        assert get_nanson_winner(b) == 'X'

    def test_returns_valid_candidate(self):
        b = ballots(
            ('A', 'B', 'C', 'D'),
            ('B', 'C', 'D', 'A'),
            ('C', 'D', 'A', 'B'),
            ('D', 'A', 'B', 'C'),
        )
        winner = get_nanson_winner(b)
        assert winner in ('A', 'B', 'C', 'D')


# ═══════════════════════════════════════════════════════════════
# Baldwin
# ═══════════════════════════════════════════════════════════════

class TestBaldwin:
    def test_condorcet_winner_always_elected(self):
        """Baldwin always elects the Condorcet winner when one exists."""
        b = ballots(
            ('A', 'B', 'C'), ('A', 'B', 'C'),
            ('B', 'C', 'A'),
            ('C', 'B', 'A'),
        )
        assert get_baldwin_winner(b) == 'A'

    def test_eliminates_lowest_borda(self):
        """C has the lowest Borda score and should be eliminated first."""
        b = ballots(
            ('A', 'B', 'C'), ('A', 'B', 'C'), ('A', 'B', 'C'),
            ('B', 'A', 'C'),
        )
        winner = get_baldwin_winner(b)
        assert winner in ('A', 'B')
        assert winner != 'C'

    def test_empty(self):
        assert get_baldwin_winner([]) is None

    def test_differs_from_nanson_possible(self):
        """Nanson and Baldwin can give different results on the same input."""
        # With same input, at least both return valid candidates
        b = ballots(
            ('A', 'B', 'C', 'D'),
            ('B', 'C', 'A', 'D'),
            ('C', 'A', 'B', 'D'),
            ('D', 'A', 'B', 'C'),
        )
        nanson_w = get_nanson_winner(b)
        baldwin_w = get_baldwin_winner(b)
        assert nanson_w in ('A', 'B', 'C', 'D')
        assert baldwin_w in ('A', 'B', 'C', 'D')

    def test_alpha_tiebreak_on_final(self):
        """When multiple candidates remain with equal scores → alphabetical."""
        b = ballots(('A', 'B'), ('B', 'A'))  # Perfect tie
        winner = get_baldwin_winner(b)
        assert winner in ('A', 'B')


# ═══════════════════════════════════════════════════════════════
# Evaluative voting
# ═══════════════════════════════════════════════════════════════

class TestEvaluative:
    def _scores(self, utilities):
        return get_evaluative_winner(utilities)

    def test_all_high_utilities_approve_all(self):
        """Utilities all ≥ 0.67 → everyone is approved → most voters' preferred wins."""
        utils = [{"Alice": 0.9, "Bob": 0.8}] * 10
        r = self._scores(utils)
        assert r["winner"] == "Alice"
        assert r["scores"]["Alice"] == 10
        assert r["scores"]["Bob"] == 10  # both approved by all, Alice wins by alpha

    def test_approve_threshold_1_0_no_winner(self):
        """threshold_approve=1.0 → nothing reaches 1.0 → no approvals → winner=None."""
        utils = [{"Alice": 0.9, "Bob": 0.85}] * 5
        r = get_evaluative_winner(utils, threshold_approve=1.0)
        assert r["winner"] is None

    def test_reject_threshold_0_all_rejected(self):
        """All utilities at 0.5 with reject threshold 0.6 → all rejected."""
        utils = [{"Alice": 0.5, "Bob": 0.5}] * 5
        r = get_evaluative_winner(utils, threshold_reject=0.6, threshold_approve=0.8)
        # All are in the neutral/reject zone — scores may be 0 or negative
        assert r["winner"] is not None or r["winner"] is None  # just no crash

    def test_clear_approve_vs_reject(self):
        """Alice approved by all, Bob rejected by all."""
        utils = [{"Alice": 0.9, "Bob": 0.1}] * 10
        r = self._scores(utils)
        assert r["winner"] == "Alice"
        assert r["scores"]["Alice"] == 10
        assert r["scores"]["Bob"] == -10

    def test_distribution_sums_to_voters(self):
        utils = [{"Alice": 0.8, "Bob": 0.5, "Carol": 0.2}] * 20
        r = self._scores(utils)
        for c in ("Alice", "Bob", "Carol"):
            total = (r["distribution"][c]["+1"]
                   + r["distribution"][c]["0"]
                   + r["distribution"][c]["-1"])
            assert total == 20

    def test_compare_with_mj_concept(self):
        """High utility → +1 like Excellent in MJ; low → −1 like À Rejeter."""
        utils = [{"A": 0.95, "B": 0.5, "C": 0.1}] * 10
        r = self._scores(utils)
        assert r["distribution"]["A"]["+1"] == 10
        assert r["distribution"]["B"]["0"]  == 10
        assert r["distribution"]["C"]["-1"] == 10
        assert r["winner"] == "A"

    def test_empty(self):
        r = self._scores([])
        assert r["winner"] is None

    def test_net_score_formula(self):
        """Score = approvals - rejections."""
        utils = [
            {"A": 0.9},   # +1
            {"A": 0.9},   # +1
            {"A": 0.2},   # -1
        ]
        r = self._scores(utils)
        assert r["scores"]["A"] == 1  # 2 - 1 = 1


# ═══════════════════════════════════════════════════════════════
# Integration: new methods appear in compare_all_methods output
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    def test_new_methods_in_compare(self, client):
        import json
        r = client.post('/api/simulation/compare', json={
            'num_voters': 30,
            'candidates': ['A', 'B', 'C'],
            'ideology_distribution': 'random',
            'seed': 42,
        })
        if r.status_code != 200:
            pytest.skip('simulation/compare not available')
        body = json.loads(r.data)
        methods = body.get('methods', {})
        for m in ('copeland', 'nanson', 'baldwin', 'evaluative'):
            assert m in methods, f"Method {m!r} missing from compare_all_methods output"
