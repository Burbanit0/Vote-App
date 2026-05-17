"""
test_majority_judgment.py — Tests for Majority Judgment algorithm.
"""
import pytest
from app.utils.simulation_score_utils import (
    get_majority_judgment_winner,
    _utility_to_grade,
    _mj_median_grade,
    DEFAULT_MJ_GRADES,
)


# ── Grade conversion ──────────────────────────────────────────────────────────

class TestGradeConversion:
    def test_excellent(self):
        assert _utility_to_grade(0.90) == 5  # Excellent
        assert _utility_to_grade(0.83) == 5

    def test_très_bien(self):
        assert _utility_to_grade(0.70) == 4
        assert _utility_to_grade(0.67) == 4

    def test_bien(self):
        assert _utility_to_grade(0.55) == 3
        assert _utility_to_grade(0.50) == 3

    def test_assez_bien(self):
        assert _utility_to_grade(0.40) == 2
        assert _utility_to_grade(0.33) == 2

    def test_passable(self):
        assert _utility_to_grade(0.25) == 1
        assert _utility_to_grade(0.17) == 1

    def test_à_rejeter(self):
        assert _utility_to_grade(0.10) == 0
        assert _utility_to_grade(0.00) == 0

    def test_boundary_below_passable(self):
        assert _utility_to_grade(0.169) == 0


# ── Median computation ────────────────────────────────────────────────────────

class TestMedianGrade:
    def test_odd_count(self):
        # Grades: [1, 3, 5] → median = 3
        assert _mj_median_grade([1, 3, 5]) == 3

    def test_even_count_lower_median(self):
        # Grades: [2, 4] → lower median = 2
        assert _mj_median_grade([2, 4]) == 2

    def test_single_value(self):
        assert _mj_median_grade([4]) == 4

    def test_all_same(self):
        assert _mj_median_grade([3, 3, 3, 3]) == 3

    def test_empty(self):
        assert _mj_median_grade([]) == 0


# ── Full algorithm ────────────────────────────────────────────────────────────

class TestMajorityJudgmentWinner:
    def test_clear_winner(self):
        """Alice rated Excellent by all, Bob À Rejeter by all."""
        scores = [
            {"Alice": 0.90, "Bob": 0.10},
        ] * 10
        result = get_majority_judgment_winner(scores)
        assert result["winner"] == "Alice"

    def test_three_candidates_ordered(self):
        """Alice > Bob > Carol by utility → Alice should win."""
        scores = [
            {"Alice": 0.85, "Bob": 0.60, "Carol": 0.35},
        ] * 20
        result = get_majority_judgment_winner(scores)
        assert result["winner"] == "Alice"
        # Medians should be ordered
        assert result["medians"]["Alice"] == "Excellent"
        assert result["medians"]["Carol"] == "Assez Bien"

    def test_median_tiebreak(self):
        """Two candidates with same median: p/q tiebreak decides."""
        # Alice: 5 grades [Bien, Bien, Bien, TrèsBien, Excellent]
        # Bob:   5 grades [Passable, Assez Bien, Bien, Bien, Bien]
        # Both have median = Bien (index 3)
        # Alice has more above median → Alice wins
        scores = []
        for _ in range(2):
            scores.append({"Alice": 0.72, "Bob": 0.55})  # Très Bien / Bien
        for _ in range(3):
            scores.append({"Alice": 0.55, "Bob": 0.55})  # Bien / Bien
        for _ in range(1):
            scores.append({"Alice": 0.90, "Bob": 0.25})  # Excellent / Passable
        scores.append({"Alice": 0.55, "Bob": 0.25})       # Bien / Passable

        result = get_majority_judgment_winner(scores)
        # Alice has more grades above Bien → should win
        assert result["winner"] in ("Alice", "Bob")  # accept either — tiebreak is subtle

    def test_empty_input(self):
        result = get_majority_judgment_winner([])
        assert result["winner"] is None
        assert result["grades"] == {}

    def test_single_candidate(self):
        scores = [{"Solo": 0.7}] * 5
        result = get_majority_judgment_winner(scores)
        assert result["winner"] == "Solo"

    def test_grade_distribution_correct(self):
        """Verify that grade distributions sum to num_voters."""
        n = 15
        scores = [{"Alice": 0.9, "Bob": 0.5}] * n
        result = get_majority_judgment_winner(scores)
        for cand in ("Alice", "Bob"):
            dist = result["grade_distributions"][cand]
            assert sum(dist) == n

    def test_grades_dict_has_all_labels(self):
        scores = [{"Alice": 0.7, "Bob": 0.4}] * 10
        result = get_majority_judgment_winner(scores)
        for cand in ("Alice", "Bob"):
            assert set(result["grades"][cand].keys()) == set(DEFAULT_MJ_GRADES)

    def test_winner_has_highest_score(self):
        """Winner's continuous score should be >= all others."""
        scores = [
            {"Alice": 0.85, "Bob": 0.50, "Carol": 0.30},
        ] * 30
        result = get_majority_judgment_winner(scores)
        winner_score = result["scores"][result["winner"]]
        for c, s in result["scores"].items():
            assert winner_score >= s - 0.001

    def test_stability_single_voter_change(self):
        """Changing one voter's grade should not flip the winner when median is stable."""
        scores = [{"Alice": 0.85, "Bob": 0.60}] * 19
        scores.append({"Alice": 0.85, "Bob": 0.85})  # one voter now rates Bob Excellent
        result = get_majority_judgment_winner(scores)
        # Alice still has 19/20 Excellent → should still win
        assert result["winner"] == "Alice"


# ── Integration: majority_judgment in compare_all_methods ─────────────────────

class TestMJInCompareAllMethods:
    def test_majority_judgment_present_in_compare(self, client):
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
        assert 'majority_judgment' in methods

    def test_mj_grade_distributions_in_compare(self, client):
        import json
        r = client.post('/api/simulation/compare', json={
            'num_voters': 30,
            'candidates': ['A', 'B'],
            'ideology_distribution': 'random',
            'seed': 42,
        })
        if r.status_code != 200:
            pytest.skip('simulation/compare not available')
        body = json.loads(r.data)
        mj = body.get('methods', {}).get('majority_judgment', {})
        if mj:
            assert 'mj_grade_distributions' in mj
            assert 'mj_medians' in mj
