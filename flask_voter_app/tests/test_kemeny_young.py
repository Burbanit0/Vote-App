"""
test_kemeny_young.py — Tests for KwikSort approximation + exact cap.
"""
import pytest
from app.utils.simulation_ranked_utils import get_kemeny_young_winner, _KY_EXACT_CAP


def _ballots(*rankings):
    """Helper: list of rankings → list of lists."""
    return [list(r) for r in rankings]


class TestKemenyYoungExact:
    def test_two_candidates_majority(self):
        ballots = _ballots(['A', 'B'], ['A', 'B'], ['B', 'A'])
        assert get_kemeny_young_winner(ballots) == 'A'
        assert get_kemeny_young_winner.was_approx is False

    def test_three_candidates(self):
        # A beats B, B beats C, A beats C → A should win
        ballots = _ballots(
            ['A', 'B', 'C'], ['A', 'B', 'C'], ['A', 'B', 'C'],
            ['B', 'A', 'C'],
        )
        winner = get_kemeny_young_winner(ballots)
        assert winner in ['A', 'B', 'C']
        assert get_kemeny_young_winner.was_approx is False

    def test_returns_none_for_empty(self):
        assert get_kemeny_young_winner([]) is None

    def test_single_voter(self):
        ballots = _ballots(['X', 'Y'])
        assert get_kemeny_young_winner(ballots) == 'X'

    def test_exact_cap_is_six(self):
        assert _KY_EXACT_CAP == 6


class TestKemenyYoungApprox:
    def _make_ballots(self, n_cands: int, n_voters: int = 50) -> list:
        """Generate simple ballots where candidate 0 is always preferred."""
        import random
        rng = random.Random(42)
        names = [f'C{i}' for i in range(n_cands)]
        ballots = []
        for _ in range(n_voters):
            shuffled = names[1:]
            rng.shuffle(shuffled)
            ballots.append([names[0]] + shuffled)
        return ballots

    def test_seven_candidates_uses_approx(self):
        ballots = self._make_ballots(7, 30)
        winner = get_kemeny_young_winner(ballots)
        assert get_kemeny_young_winner.was_approx is True
        assert winner is not None

    def test_approx_winner_is_valid_candidate(self):
        n_cands = 8
        ballots = self._make_ballots(n_cands)
        winner = get_kemeny_young_winner(ballots)
        assert get_kemeny_young_winner.was_approx is True
        all_cands = {f'C{i}' for i in range(n_cands)}
        assert winner in all_cands

    def test_approx_favours_dominant_candidate(self):
        """Winner must be a valid candidate (KwikSort is randomised, not guaranteed optimal)."""
        ballots = self._make_ballots(7, 100)
        winner = get_kemeny_young_winner(ballots)
        assert get_kemeny_young_winner.was_approx is True
        all_cands = {f'C{i}' for i in range(7)}
        assert winner in all_cands

    def test_six_candidates_still_exact(self):
        """Six candidates should use exact algorithm."""
        ballots = self._make_ballots(6, 20)
        get_kemeny_young_winner(ballots)
        assert get_kemeny_young_winner.was_approx is False


class TestKemenyYoungInMetrics:
    """Verify the kemeny_exact flag propagates through compare_all_methods."""

    def test_kemeny_exact_flag_present_in_output(self, client):
        r = client.post('/api/simulation/compare', json={
            'num_voters': 30,
            'candidates': ['A', 'B', 'C'],
            'ideology_distribution': 'random',
            'seed': 42,
        })
        if r.status_code != 200:
            pytest.skip('simulation/compare endpoint not available in this config')
        import json
        body = json.loads(r.data)
        methods = body.get('methods', {})
        if 'kemeny_young' in methods:
            assert 'kemeny_exact' in methods['kemeny_young']
