"""Tests for real_election_data.py"""

import pytest
from app.utils.real_election_data import (
    list_elections,
    analyze_real_election,
    convert_to_rankings,
    REAL_ELECTIONS,
)


class TestListElections:
    def test_returns_list(self):
        result = list_elections()
        assert isinstance(result, list)

    def test_each_entry_has_name_and_year(self):
        result = list_elections()
        for entry in result:
            assert "name" in entry
            assert "year" in entry
            assert "key" in entry
            assert "country" in entry

    def test_contains_known_elections(self):
        result = list_elections()
        keys = [e["key"] for e in result]
        assert "france_2022" in keys
        assert "us_1992" in keys
        assert "crisis_election" in keys


class TestAnalyzeRealElection:
    def test_returns_expected_structure(self):
        result = analyze_real_election("us_1992", num_voters=500)
        assert "election" in result
        assert "plurality_winner" in result
        assert "first_round_results" in result
        assert "methods" in result
        assert "divergences" in result
        assert "summary" in result
        assert "blank_vote_analysis" in result

    def test_plurality_winner_is_clinton(self):
        result = analyze_real_election("us_1992", num_voters=500)
        assert result["plurality_winner"] == "Clinton"

    def test_election_metadata(self):
        result = analyze_real_election("france_2002", num_voters=500)
        meta = result["election"]
        assert meta["name"] == "French Presidential Election — 1st round"
        assert meta["year"] == 2002
        assert meta["country"] == "France"
        assert meta["key"] == "france_2002"

    def test_returns_all_methods(self):
        result = analyze_real_election("us_1992", num_voters=500)
        # 11 ranked + 5 score + kemeny_young (≤5 candidates)
        assert len(result["methods"]) == 17

    def test_returns_methods_without_kemeny_young(self):
        result = analyze_real_election("france_2022", num_voters=500)
        # 11 ranked + 5 score, no kemeny_young (>5 candidates)
        assert len(result["methods"]) == 16

    def test_methods_all_have_winners(self):
        result = analyze_real_election("us_1992", num_voters=500)
        for method, winner in result["methods"].items():
            assert winner is not None, f"{method} returned None winner"

    def test_divergences_list_length(self):
        result = analyze_real_election("us_1992", num_voters=500)
        assert len(result["divergences"]) == len(result["methods"])

    def test_first_round_results_are_percentages(self):
        result = analyze_real_election("us_1992", num_voters=500)
        total = sum(result["first_round_results"].values())
        assert abs(total - 100.0) < 0.1

    def test_summary_counts(self):
        result = analyze_real_election("us_1992", num_voters=500)
        assert result["summary"]["total_methods_with_winner"] > 0

    def test_with_blank_vote_true(self):
        result = analyze_real_election("us_1992", num_voters=500, blank_vote=True)
        assert "methods_with_blank" in result
        assert result["methods_with_blank"] is not None

    def test_with_blank_vote_false(self):
        result = analyze_real_election("us_1992", num_voters=500, blank_vote=False)
        assert result["methods_with_blank"] is None

    def test_blank_vote_analysis_structure(self):
        result = analyze_real_election("crisis_election", num_voters=500, blank_vote=True)
        analysis = result["blank_vote_analysis"]
        assert "competitive" in analysis
        assert "threshold_30" in analysis
        assert "blank_wins" in analysis["competitive"]
        assert "triggered" in analysis["threshold_30"]

    def test_blank_vote_analysis_threshold_30(self):
        result = analyze_real_election("crisis_election", num_voters=500, blank_vote=True)
        assert result["blank_vote_analysis"]["threshold_30"]["triggered"] is True

    def test_blank_vote_does_not_win_when_low(self):
        result = analyze_real_election("us_1992", num_voters=500, blank_vote=True)
        assert result["blank_vote_analysis"]["competitive"]["blank_wins"] is False
        assert result["blank_vote_analysis"]["threshold_30"]["triggered"] is False


class TestInvalidElectionName:
    def test_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown election"):
            analyze_real_election("nonexistent_election")


class TestConvertToRankings:
    def test_returns_list_of_lists(self):
        rankings = convert_to_rankings("us_1992", REAL_ELECTIONS["us_1992"], num_voters=100)
        assert isinstance(rankings, list)
        assert len(rankings) == 100
        for r in rankings:
            assert isinstance(r, list)
            assert len(r) > 0

    def test_each_rank_contains_all_candidates(self):
        rankings = convert_to_rankings("us_1992", REAL_ELECTIONS["us_1992"], num_voters=100)
        expected = {"Clinton", "Bush", "Perot"}
        for r in rankings:
            assert set(r) == expected
            assert len(r) == 3

    def test_ranking_respects_ideology(self):
        rankings = convert_to_rankings("us_1992", REAL_ELECTIONS["us_1992"], num_voters=100)
        # A Clinton voter ranks Clinton first, then Perot (0.52) is closer than Bush (0.70)
        clinton_voters = [r for r in rankings if r[0] == "Clinton"]
        if clinton_voters:
            assert clinton_voters[0][1] in ("Perot",)
