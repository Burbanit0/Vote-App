"""Tests for multi-winner proportional voting methods."""

import pytest
from app.utils.simulation_multiwinner_utils import (
    get_dhondt_winners,
    get_sainte_lague_winners,
    get_largest_remainder_winners,
    get_stv_winners,
    compute_proportionality_metrics,
    compare_multiwinner_methods,
)


class TestDHondt:

    def test_known_three_parties(self):
        result = get_dhondt_winners({"A": 59, "B": 31, "C": 10}, 10)
        assert result == {"A": 6, "B": 3, "C": 1}

    def test_total_seats(self):
        result = get_dhondt_winners({"A": 50, "B": 30, "C": 20}, 10)
        assert sum(result.values()) == 10

    def test_unknown_votes_distribution(self):
        result = get_dhondt_winners({"A": 999, "B": 1, "C": 0}, 5)
        assert result["A"] == 5
        assert result["B"] == 0

    def test_one_seat(self):
        result = get_dhondt_winners({"A": 40, "B": 35, "C": 25}, 1)
        assert result["A"] == 1
        assert result["B"] == 0
        assert result["C"] == 0

    def test_one_hundred_seats(self):
        result = get_dhondt_winners({"A": 51, "B": 49}, 100)
        assert sum(result.values()) == 100
        assert result["A"] >= 50
        assert result["B"] >= 49

    def test_ties_odd_seats(self):
        result = get_dhondt_winners({"A": 50, "B": 50}, 5)
        assert sum(result.values()) == 5
        # With tied votes, the algorithm picks one; both should get some seats
        assert result["A"] > 0
        assert result["B"] > 0

    def test_more_parties_than_seats(self):
        result = get_dhondt_winners({f"P{i}": 10 for i in range(10)}, 3)
        assert sum(result.values()) == 3
        assert len([p for p, s in result.items() if s > 0]) == 3

    def test_zero_votes_excluded(self):
        result = get_dhondt_winners({"A": 100, "B": 0, "C": 0}, 5)
        assert "B" not in result or result.get("B", 0) == 0
        assert result["A"] == 5

    def test_single_party(self):
        result = get_dhondt_winners({"OnlyOne": 100}, 7)
        assert result == {"OnlyOne": 7}


class TestSainteLague:

    def test_known_three_parties(self):
        result = get_sainte_lague_winners({"A": 59, "B": 31, "C": 10}, 10)
        assert result == {"A": 6, "B": 3, "C": 1}

    def test_total_seats(self):
        result = get_sainte_lague_winners({"A": 50, "B": 30, "C": 20}, 10)
        assert sum(result.values()) == 10

    def test_one_seat(self):
        result = get_sainte_lague_winners({"A": 40, "B": 35, "C": 25}, 1)
        assert result["A"] == 1

    def test_one_hundred_seats_split(self):
        result = get_sainte_lague_winners({"A": 51, "B": 49}, 100)
        assert sum(result.values()) == 100
        assert abs(result["A"] - result["B"]) <= 2

    def test_ties_odd_seats(self):
        result = get_sainte_lague_winners({"A": 50, "B": 50}, 5)
        assert sum(result.values()) == 5
        assert result["A"] > 0
        assert result["B"] > 0

    def test_more_parties_than_seats(self):
        result = get_sainte_lague_winners({f"P{i}": 10 for i in range(10)}, 3)
        assert sum(result.values()) == 3

    def test_zero_votes_excluded(self):
        result = get_sainte_lague_winners({"A": 100, "B": 0}, 5)
        assert result["A"] == 5

    def test_single_party(self):
        result = get_sainte_lague_winners({"OnlyOne": 100}, 7)
        assert result == {"OnlyOne": 7}

    def test_small_parties_get_seats(self):
        """Sainte-Laguë is more proportional: small parties can win seats."""
        result = get_sainte_lague_winners({"A": 45, "B": 30, "C": 15, "D": 10}, 10)
        assert result["D"] >= 1


class TestLargestRemainder:

    def test_hare_quota_known(self):
        votes = {"A": 47000, "B": 16000, "C": 15800, "D": 12000}
        result = get_largest_remainder_winners(votes, 10, quota="hare")
        assert sum(result.values()) == 10

    def test_droop_quota(self):
        votes = {"A": 47000, "B": 16000, "C": 15800, "D": 12000}
        result = get_largest_remainder_winners(votes, 10, quota="droop")
        assert sum(result.values()) == 10

    def test_empty_votes(self):
        result = get_largest_remainder_winners({}, 10)
        assert all(v == 0 for v in result.values())

    def test_zero_seats(self):
        result = get_largest_remainder_winners({"A": 100}, 0)
        assert result == {"A": 0}

    def test_single_party(self):
        result = get_largest_remainder_winners({"A": 100}, 5, quota="hare")
        assert result == {"A": 5}

    def test_hare_vs_droop_different(self):
        """Hare and Droop quotas can produce different allocations."""
        votes = {"A": 60, "B": 30, "C": 10}
        hare = get_largest_remainder_winners(votes, 5, quota="hare")
        droop = get_largest_remainder_winners(votes, 5, quota="droop")
        assert sum(hare.values()) == 5
        assert sum(droop.values()) == 5


class TestSTV:

    def test_simple_stv_three_seats_five_candidates(self):
        ballots = [
            ["Alice", "Bob", "Carol", "Dave", "Eve"],
            ["Alice", "Carol", "Bob", "Eve", "Dave"],
            ["Bob", "Alice", "Carol", "Dave", "Eve"],
            ["Bob", "Carol", "Alice", "Eve", "Dave"],
            ["Carol", "Alice", "Bob", "Dave", "Eve"],
            ["Carol", "Bob", "Alice", "Eve", "Dave"],
            ["Dave", "Alice", "Bob", "Carol", "Eve"],
            ["Dave", "Bob", "Carol", "Alice", "Eve"],
            ["Eve", "Alice", "Bob", "Carol", "Dave"],
            ["Eve", "Bob", "Carol", "Alice", "Dave"],
        ]
        winners = get_stv_winners(ballots, 3)
        assert len(winners) == 3
        for w in winners:
            assert w in ["Alice", "Bob", "Carol", "Dave", "Eve"]

    def test_stv_empty_ballots(self):
        winners = get_stv_winners([], 3)
        assert winners == []

    def test_stv_zero_winners(self):
        ballots = [["A", "B", "C"]]
        winners = get_stv_winners(ballots, 0)
        assert winners == []

    def test_stv_dict_format(self):
        ballots = [
            {"voter_id": 1, "ranking": ["A", "B", "C"]},
            {"voter_id": 2, "ranking": ["A", "B", "C"]},
        ]
        winners = get_stv_winners(ballots, 1)
        assert winners == ["A"]

    def test_stv_less_candidates_than_winners(self):
        winners = get_stv_winners([["A"], ["B"]], 5)
        # Should elect available candidates and stop
        assert len(winners) <= 2

    def test_stv_exact_quota(self):
        # 12 ballots, 3 winners → Droop quota = 12//4 + 1 = 4
        ballots = (
            [["A", "B", "C"]] * 4
            + [["B", "A", "C"]] * 4
            + [["C", "A", "B"]] * 4
        )
        winners = get_stv_winners(ballots, 3)
        assert len(winners) == 3


class TestProportionalityMetrics:

    def test_gallagher_index_zero_for_perfect(self):
        metrics = compute_proportionality_metrics(
            {"A": 50, "B": 30, "C": 20},
            {"A": 5, "B": 3, "C": 2},
        )
        assert metrics["gallagher_index"] == 0.0

    def test_gallagher_index_positive_for_mismatch(self):
        metrics = compute_proportionality_metrics(
            {"A": 50, "B": 30, "C": 20},
            {"A": 10, "B": 0, "C": 0},
        )
        g = metrics["gallagher_index"]
        assert g is not None and g > 0

    def test_empty_input(self):
        metrics = compute_proportionality_metrics({}, {})
        assert metrics["gallagher_index"] is None
        assert metrics["largest_deviation"] is None

    def test_effective_parties(self):
        metrics = compute_proportionality_metrics(
            {"A": 60, "B": 40},
            {"A": 6, "B": 4},
        )
        assert metrics["effective_parties_votes"] is not None
        assert metrics["effective_parties_seats"] is not None

    def test_largest_deviation_party(self):
        metrics = compute_proportionality_metrics(
            {"A": 50, "B": 30, "C": 20},
            {"A": 10, "B": 0, "C": 0},
        )
        assert metrics["largest_deviation"]["party"] in ["A", "B", "C"]


class TestCompareMultiwinnerMethods:

    def test_returns_all_methods(self):
        result = compare_multiwinner_methods({"A": 50, "B": 30, "C": 20}, 10)
        for key in ["dhondt", "sainte_lague", "largest_remainder_hare", "largest_remainder_droop"]:
            assert key in result

    def test_each_method_has_seats_and_metrics(self):
        result = compare_multiwinner_methods({"A": 50, "B": 30, "C": 20}, 10)
        for key in ["dhondt", "sainte_lague", "largest_remainder_hare", "largest_remainder_droop"]:
            assert "seats" in result[key]
            assert "metrics" in result[key]

    def test_includes_stv_when_rankings_given(self):
        # 12 ballots, 3 winners → Droop quota = 12//4 + 1 = 4
        rankings = [["A", "B", "C"]] * 4 + [["B", "A", "C"]] * 4 + [["C", "A", "B"]] * 4
        result = compare_multiwinner_methods({"A": 50, "B": 30, "C": 20}, 3, voter_rankings=rankings)
        assert "stv" in result
        assert len(result["stv"]["winners"]) == 3

    def test_comparison_ranking(self):
        result = compare_multiwinner_methods({"A": 50, "B": 30, "C": 20}, 10)
        assert "comparison" in result
        assert "most_proportional" in result["comparison"]
        assert "least_proportional" in result["comparison"]
        assert len(result["comparison"]["gallagher_ranking"]) == 4

    def test_empty_votes(self):
        with pytest.raises(ValueError):
            compare_multiwinner_methods({}, 10)
