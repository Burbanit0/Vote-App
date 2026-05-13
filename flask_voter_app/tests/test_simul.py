"""Tests for simul.py"""

import pytest
from app.utils.simul import (
    init,
    simulate_voters,
    simulate_ranked_voters,
    simulate_score_voters,
)

_DEMOGRAPHICS = {
    "age": {"18-30": 0.3, "31-50": 0.4, "51+": 0.3},
    "gender": {"M": 0.5, "F": 0.5},
    "location": {"Urban": 0.6, "Rural": 0.4},
    "education": {"High": 0.4, "Medium": 0.4, "Low": 0.2},
    "income": {"High": 0.3, "Medium": 0.4, "Low": 0.3},
    "ideology": {"Left": 0.3, "Center": 0.4, "Right": 0.3},
}

_CANDIDATES = ["Alice", "Bob", "Carol"]

_INFLUENCE = {
    "age": {"18-30": {"Alice": 1.2, "Bob": 0.8}, "51+": {"Carol": 1.5}},
    "ideology": {
        "Left": {"Alice": 2.0, "Bob": 1.0},
        "Right": {"Bob": 2.0, "Carol": 1.5},
    },
}


class TestInit:
    def test_returns_correct_number_of_voters(self):
        voters = init(50, _DEMOGRAPHICS, 0.7)
        assert len(voters) == 50

    def test_each_voter_has_required_keys(self):
        voters = init(10, _DEMOGRAPHICS, 0.7)
        for v in voters:
            assert "id" in v
            assert "age" in v
            assert "gender" in v
            assert "location" in v
            assert "education" in v
            assert "income" in v
            assert "ideology" in v
            assert "turnout" in v

    def test_turnout_is_boolean(self):
        voters = init(100, _DEMOGRAPHICS, 0.7)
        for v in voters:
            assert isinstance(v["turnout"], bool)

    def test_turnout_rate_approximation(self):
        voters = init(1000, _DEMOGRAPHICS, 0.5)
        turnout_count = sum(1 for v in voters if v["turnout"])
        # With 1000 voters and 0.5 rate, should be roughly 50%
        assert 300 < turnout_count < 700

    def test_ids_are_unique(self):
        voters = init(100, _DEMOGRAPHICS, 0.7)
        ids = [v["id"] for v in voters]
        assert len(set(ids)) == 100


class TestSimulateVoters:
    def test_returns_tuple_of_three(self):
        result = simulate_voters(50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 0.7)
        assert len(result) == 3

    def test_voters_list_has_correct_length(self):
        voters, votes, tally = simulate_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 0.7
        )
        assert len(voters) == 50
        assert len(votes) == 50

    def test_tally_sums_to_voter_count(self):
        voters, votes, tally = simulate_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 0.7
        )
        assert sum(tally.values()) == 50

    def test_preference_is_valid(self):
        voters, votes, tally = simulate_voters(
            50, ["Alice", "Bob"], _DEMOGRAPHICS, _INFLUENCE, 1.0
        )
        valid = {"Alice", "Bob", "No Vote"}
        for v in voters:
            assert v["preference"] in valid

    def test_non_turnout_voters_have_no_vote(self):
        voters, votes, tally = simulate_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 0.0
        )
        for v in voters:
            assert v["preference"] == "No Vote"

    def test_all_turnout_voters_have_some_preference(self):
        voters, votes, tally = simulate_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 1.0
        )
        # All turned out, but some may still have "No Vote" (abstention is a choice)
        valid = {"Alice", "Bob", "Carol", "No Vote"}
        for v in voters:
            assert v["preference"] in valid


class TestSimulateRankedVoters:
    def test_returns_tuple_of_three(self):
        result = simulate_ranked_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 0.7
        )
        assert len(result) == 3

    def test_rankings_is_list_of_lists(self):
        voters, rankings, tally = simulate_ranked_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 0.7
        )
        assert isinstance(rankings, list)
        for r in rankings:
            assert isinstance(r, list)

    def test_each_ranking_contains_all_candidates(self):
        voters, rankings, tally = simulate_ranked_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 1.0
        )
        expected = set(_CANDIDATES)
        for r in rankings:
            assert set(r) == expected

    def test_ranking_has_no_duplicates(self):
        voters, rankings, tally = simulate_ranked_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 1.0
        )
        for r in rankings:
            assert len(r) == len(set(r))

    def test_non_turnout_voters_have_empty_ranking(self):
        voters, rankings, tally = simulate_ranked_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 0.0
        )
        for v in voters:
            assert v["ranking"] == []
        assert rankings == []

    def test_tally_counts_first_choices(self):
        voters, rankings, tally = simulate_ranked_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 1.0
        )
        assert sum(tally.values()) == 50


class TestSimulateScoreVoters:
    def test_returns_tuple_of_three(self):
        result = simulate_score_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 0.7
        )
        assert len(result) == 3

    def test_scores_are_in_0_to_5_range(self):
        voters, all_scores, avg_scores = simulate_score_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 1.0
        )
        for scores in all_scores:
            for candidate, score in scores.items():
                assert 0 <= score <= 5

    def test_non_turnout_voters_have_zero_scores(self):
        voters, all_scores, avg_scores = simulate_score_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 0.0
        )
        for v in voters:
            for score in v["scores"].values():
                assert score == 0

    def test_avg_scores_has_all_candidates(self):
        voters, all_scores, avg_scores = simulate_score_voters(
            50, _CANDIDATES, _DEMOGRAPHICS, _INFLUENCE, 1.0
        )
        for c in _CANDIDATES:
            assert c in avg_scores
