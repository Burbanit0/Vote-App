"""
Unit tests for the simulation voting utilities.

Pure Python — no Flask app context required (utils have no DB dependencies).
Run with:
    FLASK_ENV=testing pytest tests/test_simulation_methods.py -v
"""

import pytest
from app.utils.simulation_ranked_utils import (
    get_borda_winner,
    get_condorcet_winner,
    get_irv_winner,
    get_plurality_winner,
    get_schulze_winner,
)
from app.utils.simulation_multiwinner_utils import (
    get_dhondt_winners,
    get_sainte_lague_winners,
)
from app.utils.simulation_metrics import compare_all_methods
from app.utils.arrow_criteria import check_all_criteria, RANKED_METHODS


# ── Fixtures ───────────────────────────────────────────────────────────────

ISSUES = ["economy", "environment", "healthcare"]


def _voter(voter_id: int, lean: float) -> dict:
    """Minimal voter dict compatible with calculate_utility."""
    return {
        "id": voter_id,
        "gender": "male",
        "political_lean_normalized": lean,
        "issue_priorities": {"economy": 0.4, "environment": 0.3, "healthcare": 0.3},
        "issue_positions": {"economy": lean, "environment": lean, "healthcare": lean},
        "party_loyalty": 0.5,
        "mood": 0.0,
        "likelihood_to_vote": 1.0,
    }


def _candidate(cand_id: int, name: str, position: float) -> dict:
    """Minimal candidate dict compatible with calculate_utility."""
    return {
        "id": cand_id,
        "name": name,
        "party": "Independent",
        "party_lean": (position * 2) - 1,   # [0,1] → [-1,1]
        "ideology_position": position,
        "policies": {"economy": position, "environment": position, "healthcare": position},
        "charisma": 0.7,
        "scandals": 0,
    }


def _make_population():
    """
    10 voters, 3 candidates.
    - 6 voters at lean=0.1 → prefer Alice > Bob > Carol
    - 3 voters at lean=0.5 → prefer Bob > Alice > Carol
    - 1 voter  at lean=0.9 → prefer Carol > Bob > Alice
    Alice is both the Condorcet winner and the plurality winner.
    """
    voters = (
        [_voter(i, 0.1) for i in range(6)]
        + [_voter(i, 0.5) for i in range(6, 9)]
        + [_voter(9, 0.9)]
    )
    candidates = [
        _candidate(0, "Alice", 0.1),
        _candidate(1, "Bob",   0.5),
        _candidate(2, "Carol", 0.9),
    ]
    return voters, candidates


# ── 1. Ranked voting methods ───────────────────────────────────────────────


class TestPluralityWinner:
    def test_clear_winner(self):
        # A: 4 first-choice votes, B: 3, C: 2
        rankings = (
            [["A", "B", "C"]] * 4
            + [["B", "C", "A"]] * 3
            + [["C", "A", "B"]] * 2
        )
        assert get_plurality_winner(rankings) == "A"

    def test_empty(self):
        assert get_plurality_winner([]) is None

    def test_single_candidate(self):
        assert get_plurality_winner([["X"]]) == "X"

    def test_dict_format(self):
        votes = [
            {"voter_id": 1, "ranking": ["A", "B"]},
            {"voter_id": 2, "ranking": ["A", "B"]},
            {"voter_id": 3, "ranking": ["B", "A"]},
        ]
        assert get_plurality_winner(votes) == "A"


class TestBordaWinner:
    def test_borda_paradox(self):
        """
        Classic case: plurality elects A, Borda elects B.

        6 voters: A > B > C  → Borda pts: A+=12, B+=6,  C+=0
        3 voters: B > C > A  → Borda pts: B+=6,  C+=3,  A+=0
        3 voters: C > B > A  → Borda pts: C+=6,  B+=3,  A+=0
        Totals  : A=12, B=15, C=9  → Borda winner: B
        Plurality: A (6 first-choice votes)
        """
        rankings = (
            [["A", "B", "C"]] * 6
            + [["B", "C", "A"]] * 3
            + [["C", "B", "A"]] * 3
        )
        assert get_plurality_winner(rankings) == "A"
        assert get_borda_winner(rankings) == "B"

    def test_borda_empty(self):
        assert get_borda_winner([]) is None

    def test_borda_unanimous(self):
        rankings = [["X", "Y", "Z"]] * 5
        assert get_borda_winner(rankings) == "X"


class TestCondorcetWinner:
    def test_clear_condorcet_winner(self):
        """A beats B (6:4) and beats C (9:1) — clear Condorcet winner."""
        rankings = (
            [["A", "B", "C"]] * 6
            + [["B", "A", "C"]] * 3
            + [["C", "B", "A"]] * 1
        )
        assert get_condorcet_winner(rankings) == "A"

    def test_condorcet_cycle_returns_none(self):
        """
        Classic Condorcet cycle — no winner should exist.

        1 voter: A > B > C  → A>B, A>C, B>C
        1 voter: B > C > A  → B>C, B>A, C>A
        1 voter: C > A > B  → C>A, C>B, A>B

        Pairwise: A beats B (2:1), B beats C (2:1), C beats A (2:1) → cycle.
        """
        rankings = [
            ["A", "B", "C"],
            ["B", "C", "A"],
            ["C", "A", "B"],
        ]
        assert get_condorcet_winner(rankings) is None

    def test_condorcet_empty(self):
        assert get_condorcet_winner([]) is None

    def test_condorcet_two_candidates(self):
        rankings = [["X", "Y"]] * 3 + [["Y", "X"]] * 1
        assert get_condorcet_winner(rankings) == "X"


class TestIRVWinner:
    def test_irv_elimination_then_majority(self):
        """
        9 voters, threshold = 4.5.
        Round 1: A=4, B=3, C=2 → C eliminated.
        Round 2: A=4, B=5    → B exceeds threshold → B wins.
        Plurality would have elected A.
        """
        rankings = (
            [["A", "B", "C"]] * 4
            + [["B", "C", "A"]] * 3
            + [["C", "B", "A"]] * 2
        )
        assert get_irv_winner(rankings) == "B"
        assert get_plurality_winner(rankings) == "A"   # demonstrates divergence

    def test_irv_immediate_majority(self):
        rankings = [["A", "B", "C"]] * 4 + [["B", "A", "C"]] * 2
        assert get_irv_winner(rankings) == "A"

    def test_irv_empty(self):
        assert get_irv_winner([]) is None


class TestSchulzeWinner:
    def test_schulze_elects_condorcet_winner(self):
        """When a Condorcet winner exists, Schulze must elect them."""
        rankings = (
            [["A", "B", "C"]] * 5
            + [["A", "C", "B"]] * 2
            + [["B", "A", "C"]] * 1
        )
        cw = get_condorcet_winner(rankings)
        assert cw == "A"
        assert get_schulze_winner(rankings) == "A"

    def test_schulze_two_candidates(self):
        rankings = [["X", "Y"]] * 3 + [["Y", "X"]] * 1
        assert get_schulze_winner(rankings) == "X"

    def test_schulze_empty(self):
        assert get_schulze_winner([]) is None


# ── 2. Multi-winner proportional methods ───────────────────────────────────


class TestDHondt:
    def test_total_seats(self):
        result = get_dhondt_winners({"A": 50, "B": 30, "C": 20}, 10)
        assert sum(result.values()) == 10

    def test_all_nonnegative(self):
        result = get_dhondt_winners({"A": 50, "B": 30, "C": 20}, 10)
        assert all(v >= 0 for v in result.values())

    def test_ordering_matches_votes(self):
        """Largest-vote party must win the most seats."""
        result = get_dhondt_winners({"A": 50, "B": 30, "C": 20}, 10)
        assert result["A"] > result["B"] > result["C"]

    def test_known_result_no_ties(self):
        """
        A=59, B=31, C=10, 10 seats — computed manually (no tied rounds).
        D'Hondt allocation: A=6, B=3, C=1.
        """
        result = get_dhondt_winners({"A": 59, "B": 31, "C": 10}, 10)
        assert result == {"A": 6, "B": 3, "C": 1}

    def test_single_party(self):
        result = get_dhondt_winners({"OnlyOne": 100}, 5)
        assert result == {"OnlyOne": 5}

    def test_zero_votes_excluded(self):
        result = get_dhondt_winners({"A": 100, "B": 0}, 4)
        assert "B" not in result or result.get("B", 0) == 0
        assert result.get("A", 0) == 4


class TestSainteLague:
    def test_total_seats(self):
        result = get_sainte_lague_winners({"A": 50, "B": 30, "C": 20}, 10)
        assert sum(result.values()) == 10

    def test_all_nonnegative(self):
        result = get_sainte_lague_winners({"A": 50, "B": 30, "C": 20}, 10)
        assert all(v >= 0 for v in result.values())

    def test_known_result_no_ties(self):
        """
        A=59, B=31, C=10, 10 seats — computed manually (no tied rounds).
        Sainte-Laguë allocation: A=6, B=3, C=1.
        """
        result = get_sainte_lague_winners({"A": 59, "B": 31, "C": 10}, 10)
        assert result == {"A": 6, "B": 3, "C": 1}


class TestDHondtVsSainteLague:
    def test_dhondt_favors_large_parties(self):
        """
        Classic 4-party, 7-seat example (also used in Wikipedia).
        D'Hondt gives the small party D=0 seats; Sainte-Laguë gives D≥1.

        A=100 000, B=80 000, C=30 000, D=20 000, 7 seats.
        Expected D'Hondt  : A=3, B=3, C=1, D=0
        Expected Sainte-L : A=3, B=2, C=1, D=1
        """
        votes = {"A": 100_000, "B": 80_000, "C": 30_000, "D": 20_000}
        dhondt = get_dhondt_winners(votes, 7)
        sl = get_sainte_lague_winners(votes, 7)

        assert sum(dhondt.values()) == 7
        assert sum(sl.values()) == 7
        assert dhondt["D"] == 0        # D'Hondt excludes the smallest party
        assert sl["D"] >= 1            # Sainte-Laguë gives at least 1 seat


# ── 3. compare_all_methods ─────────────────────────────────────────────────


class TestCompareAllMethods:
    @pytest.fixture
    def result(self):
        voters, candidates = _make_population()
        return compare_all_methods(voters, candidates, ISSUES)

    def test_top_level_keys(self, result):
        assert "condorcet_winner" in result
        assert "methods" in result

    def test_has_methods(self, result):
        assert len(result["methods"]) > 0

    def test_each_method_has_required_fields(self, result):
        required = {
            "winner",
            "bayesian_regret",
            "condorcet_consistent",
            "majority_satisfaction",
            "strategic_vulnerability",
        }
        for method_name, data in result["methods"].items():
            assert required.issubset(data.keys()), (
                f"{method_name} is missing fields: {required - data.keys()}"
            )

    def test_bayesian_regret_nonnegative(self, result):
        for method_name, data in result["methods"].items():
            br = data["bayesian_regret"]
            if br is not None:
                assert br >= 0, f"{method_name}: bayesian_regret={br} is negative"

    def test_majority_satisfaction_bounded(self, result):
        for method_name, data in result["methods"].items():
            ms = data["majority_satisfaction"]
            if ms is not None:
                assert 0.0 <= ms <= 1.0, (
                    f"{method_name}: majority_satisfaction={ms} out of [0,1]"
                )

    def test_strategic_vulnerability_bounded(self, result):
        for method_name, data in result["methods"].items():
            sv = data["strategic_vulnerability"]
            if sv is not None:
                assert 0.0 <= sv <= 1.0, (
                    f"{method_name}: strategic_vulnerability={sv} out of [0,1]"
                )

    def test_condorcet_winner_is_alice(self, result):
        # Alice is the Condorcet winner for our population (beats Bob 6:4 and Carol 9:1).
        assert result["condorcet_winner"] == "Alice"

    def test_empty_inputs_return_empty(self):
        r = compare_all_methods([], [], ISSUES)
        assert r["condorcet_winner"] is None
        assert r["methods"] == {}


# ── 4. check_all_criteria ──────────────────────────────────────────────────


class TestCheckAllCriteria:
    @pytest.fixture
    def result(self):
        voters, candidates = _make_population()
        return check_all_criteria(voters, candidates, ISSUES)

    def test_top_level_keys(self, result):
        assert "methods" in result
        assert "summary" in result

    def test_all_ranked_methods_present(self, result):
        for method_name in RANKED_METHODS:
            assert method_name in result["methods"], (
                f"{method_name} missing from check_all_criteria result"
            )

    def test_each_method_has_required_criteria_keys(self, result):
        required = {
            "winner",
            "condorcet_winner",
            "condorcet_loser",
            "monotonicity",
            "iia",
            "iia_violation_rate",
            "majority",
            "reversal_symmetry",
        }
        for method_name, criteria in result["methods"].items():
            assert required.issubset(criteria.keys()), (
                f"{method_name} missing criteria keys: {required - criteria.keys()}"
            )

    def test_satisfaction_counts_bounded(self, result):
        """Each method can satisfy at most 6 criteria (excluding 'winner' and rate field)."""
        counts = result["summary"].get("criteria_satisfaction_count", {})
        assert len(counts) > 0
        for method_name, count in counts.items():
            assert 0 <= count <= 6, (
                f"{method_name}: satisfaction count={count} outside [0, 6]"
            )

    def test_iia_violation_rate_bounded(self, result):
        for method_name, criteria in result["methods"].items():
            rate = criteria["iia_violation_rate"]
            if rate is not None:
                assert 0.0 <= rate <= 1.0, (
                    f"{method_name}: iia_violation_rate={rate} out of [0,1]"
                )

    def test_summary_has_best_and_worst(self, result):
        summary = result["summary"]
        assert "most_criteria_satisfied" in summary
        assert "least_criteria_satisfied" in summary

    def test_empty_inputs_return_empty(self):
        r = check_all_criteria([], [], ISSUES)
        assert r["methods"] == {}
        assert r["summary"] == {}
