"""Tests for the core spatial voting pipeline in simulation_voting_utils.py."""

import random
import pytest
from unittest.mock import patch

from app.utils.simulation_voting_utils import (
    assign_issue_priorities,
    _sample_ideology_position,
    create_voter,
    create_candidate,
    calculate_utility,
    compute_sincere_ranking,
    compute_strategic_plurality_vote,
    compute_strategic_borda_vote,
    compute_strategic_irv_vote,
    compute_strategic_approval_vote,
    compute_strategic_score_vote,
    apply_social_influence,
    run_bandwagon_simulation,
    vote_plurality,
    vote_ranked,
    vote_score,
    simulate_vote,
    run_simulation,
)

ISSUES = ["economy", "environment", "healthcare", "education"]


def _voter(voter_id=0, lean=0.5, party_loyalty=0.0, mood=0.0, likelihood=1.0):
    return {
        "id": voter_id,
        "age": 40,
        "region": "suburban",
        "income": "medium",
        "gender": "male",
        "education": "bachelor",
        "employment_status": "employed",
        "family_status": "single",
        "ethnicity_immigration": "native",
        "religion": "non-religious",
        "political_lean": 0.0,
        "political_lean_normalized": lean,
        "issue_priorities": {i: 1.0 / len(ISSUES) for i in ISSUES},
        "issue_positions": {i: lean for i in ISSUES},
        "party_loyalty": party_loyalty,
        "preferred_party": "Independent",
        "likelihood_to_vote": likelihood,
        "mood": mood,
        "strategic_propensity": 0.0,
        "voting_style": "sincere",
        "social_conformity": 0.0,
        "blank_threshold": 0.5,
    }


def _candidate(cand_id=0, name="A", position=0.5, charisma=0.5, scandals=0):
    return {
        "id": cand_id,
        "name": name,
        "party": "Independent",
        "party_lean": (position * 2) - 1,
        "ideology_position": position,
        "policies": {i: position for i in ISSUES},
        "charisma": charisma,
        "scandals": scandals,
        "campaign_funds": 500000,
        "experience": 10,
        "popularity": 0.6,
    }


class TestAssignIssuePriorities:
    def test_returns_tuple_of_three(self):
        result = assign_issue_priorities(
            40, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        assert len(result) == 3

    def test_issue_priorities_has_all_issues(self):
        priorities, _, _ = assign_issue_priorities(
            40, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        expected = [
            "economy", "environment", "healthcare", "education", "taxes",
            "social_welfare", "agriculture", "public_transport", "defense",
            "gender_equality", "pensions", "climate_change", "housing",
            "immigration", "crime_safety", "technology_innovation",
            "minimum_wage", "business_regulation", "infrastructure",
        ]
        for issue in expected:
            assert issue in priorities

    def test_issue_priorities_are_nonnegative(self):
        priorities, _, _ = assign_issue_priorities(
            40, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        for v in priorities.values():
            assert v >= 0

    def test_political_lean_is_float(self):
        _, lean, _ = assign_issue_priorities(
            40, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        assert isinstance(lean, float)

    def test_issue_positions_are_in_01_range(self):
        _, _, positions = assign_issue_priorities(
            40, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        for v in positions.values():
            assert 0.0 <= v <= 1.0

    def test_young_voter_increases_environment_priority(self):
        p_y, _, _ = assign_issue_priorities(
            25, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        p_o, _, _ = assign_issue_priorities(
            65, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        assert p_y["environment"] >= 0.5
        assert p_o["pensions"] >= 0.5

    def test_female_voter_has_gender_equality_boost(self):
        p_f, _, _ = assign_issue_priorities(
            40, "female", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        p_m, _, _ = assign_issue_priorities(
            40, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        assert p_f["gender_equality"] > p_m["gender_equality"]

    def test_immigrant_has_immigration_priority(self):
        p_im, _, _ = assign_issue_priorities(
            40, "male", "urban", "bachelor", "medium",
            "employed", "single", "immigrant", "non-religious"
        )
        assert p_im["immigration"] >= 0.8

    def test_religious_voter_has_conservative_lean(self):
        _, lean_r, _ = assign_issue_priorities(
            40, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "religious"
        )
        _, lean_n, _ = assign_issue_priorities(
            40, "male", "urban", "bachelor", "medium",
            "employed", "single", "native", "non-religious"
        )
        assert lean_r > lean_n


class TestSampleIdeologyPosition:
    def test_centrist_returns_around_05(self):
        positions = [_sample_ideology_position("centrist") for _ in range(100)]
        avg = sum(positions) / len(positions)
        assert 0.3 < avg < 0.7

    def test_polarized_returns_extreme_values(self):
        positions = [_sample_ideology_position("polarized") for _ in range(200)]
        low = sum(1 for p in positions if p < 0.4)
        high = sum(1 for p in positions if p > 0.6)
        assert low > 30
        assert high > 30

    def test_left_skewed_tends_low(self):
        positions = [_sample_ideology_position("left_skewed") for _ in range(200)]
        avg = sum(positions) / len(positions)
        assert avg < 0.5

    def test_right_skewed_tends_high(self):
        positions = [_sample_ideology_position("right_skewed") for _ in range(200)]
        avg = sum(positions) / len(positions)
        assert avg > 0.5

    def test_random_returns_none(self):
        assert _sample_ideology_position("random") is None

    def test_values_in_01_range(self):
        for dist in ["centrist", "polarized", "left_skewed", "right_skewed"]:
            for _ in range(20):
                p = _sample_ideology_position(dist)
                assert 0.0 <= p <= 1.0


class TestCreateVoter:
    def test_default_voter_has_all_keys(self):
        voter = create_voter(ISSUES, 0)
        required = {
            "id", "age", "region", "income", "gender", "education",
            "employment_status", "family_status", "ethnicity_immigration",
            "religion", "political_lean", "political_lean_normalized",
            "issue_positions", "issue_priorities", "party_loyalty",
            "preferred_party", "likelihood_to_vote", "mood",
            "strategic_propensity", "voting_style", "social_conformity",
            "blank_threshold",
        }
        assert required.issubset(voter.keys()), f"Missing: {required - voter.keys()}"

    def test_voter_with_custom_params(self):
        voter = create_voter(ISSUES, 42)
        assert voter["id"] == 42
        assert 0 <= voter["likelihood_to_vote"] <= 1
        assert 0 <= voter["political_lean_normalized"] <= 1

    def test_voter_issue_positions_match_issues(self):
        voter = create_voter(ISSUES, 0)
        for issue in ISSUES:
            assert issue in voter["issue_positions"]
            assert issue in voter["issue_priorities"]

    def test_voter_priorities_normalized(self):
        voter = create_voter(ISSUES, 0)
        total = sum(voter["issue_priorities"].values())
        assert abs(total - 1.0) < 0.01

    def test_centrist_ideology(self):
        voter = create_voter(ISSUES, 0, ideology_distribution="centrist")
        assert 0.0 <= voter["political_lean_normalized"] <= 1.0

    def test_polarized_ideology(self):
        voter = create_voter(ISSUES, 0, ideology_distribution="polarized")
        assert 0.0 <= voter["political_lean_normalized"] <= 1.0

    def test_single_voter_single_issue(self):
        voter = create_voter(["economy"], 0)
        # create_voter builds all global issues; "jobs" is added conditionally by age
        assert "economy" in voter["issue_positions"]
        assert len(voter["issue_positions"]) >= 19

    def test_strategic_propensity_bounded(self):
        voter = create_voter(ISSUES, 0)
        assert 0.0 <= voter["strategic_propensity"] <= 0.8

    def test_social_conformity_bounded(self):
        voter = create_voter(ISSUES, 0)
        assert 0.0 <= voter["social_conformity"] <= 0.8

    def test_blank_threshold_bounded(self):
        voter = create_voter(ISSUES, 0)
        assert 0.0 <= voter["blank_threshold"] <= 1.0


class TestCreateCandidate:
    def test_default_candidate_has_all_keys(self):
        cand = create_candidate(ISSUES, 0, "Alice", "Green")
        required = {
            "id", "name", "party", "party_lean", "ideology_position",
            "policies", "charisma", "scandals", "campaign_funds",
            "experience", "popularity",
        }
        assert required.issubset(cand.keys())

    def test_candidate_id_and_name(self):
        cand = create_candidate(ISSUES, 1, "Bob", "Conservative")
        assert cand["id"] == 1
        assert cand["name"] == "Bob"
        assert cand["party"] == "Conservative"

    def test_ideology_position_override(self):
        cand = create_candidate(ISSUES, 0, "Alice", "Green", ideology_position=0.8)
        assert cand["ideology_position"] == 0.8

    def test_ideology_position_clamped_high(self):
        cand = create_candidate(ISSUES, 0, "Alice", "Green", ideology_position=1.5)
        assert cand["ideology_position"] == 1.0

    def test_ideology_position_clamped_low(self):
        cand = create_candidate(ISSUES, 0, "Alice", "Green", ideology_position=-0.5)
        assert cand["ideology_position"] == 0.0

    def test_party_determines_position_when_not_given(self):
        cg = create_candidate(ISSUES, 0, "G", "Green")
        cc = create_candidate(ISSUES, 1, "C", "Conservative")
        assert cg["ideology_position"] < cc["ideology_position"]

    def test_policies_contains_all_issues(self):
        cand = create_candidate(ISSUES, 0, "Alice", "Green")
        for issue in ISSUES:
            assert issue in cand["policies"]

    def test_policies_in_01_range(self):
        cand = create_candidate(ISSUES, 0, "Alice", "Green")
        for v in cand["policies"].values():
            assert 0.0 <= v <= 1.0

    def test_single_issue_candidate(self):
        cand = create_candidate(["economy"], 0, "A", "Green")
        assert "economy" in cand["policies"]
        assert len(cand["policies"]) == 1

    def test_position_variance_narrow(self):
        cand = create_candidate(ISSUES, 0, "A", "Green", ideology_position=0.5, position_variance=0.01)
        for v in cand["policies"].values():
            assert abs(v - 0.5) < 0.05


class TestCalculateUtility:
    def test_perfect_alignment(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        cand = _candidate(position=0.5, charisma=0.5, scandals=0)
        result = calculate_utility(voter, cand, ISSUES)
        # issue_score = 1.0, loyalty=0, charisma=0.5, scandals=0, mood=0
        # utility = 0.6*1 + 0.2*0 + 0.15*0.5 + 0 + 0 = 0.675
        assert abs(result["utility"] - 0.675) < 0.001
        assert result["voter_id"] == 0
        assert result["candidate_id"] == 0

    def test_max_distance(self):
        voter = _voter(lean=0.0, party_loyalty=0.0, mood=0.0)
        cand = _candidate(position=1.0, charisma=0.5, scandals=0)
        result = calculate_utility(voter, cand, ISSUES)
        # issue_score = 0, utility = 0 + 0 + 0.075 + 0 + 0 = 0.075
        assert abs(result["utility"] - 0.075) < 0.001

    def test_utility_bounds(self):
        for lean in [0.0, 0.25, 0.5, 0.75, 1.0]:
            voter = _voter(lean=lean, party_loyalty=0.0, mood=0.0)
            cand = _candidate(position=lean, charisma=0.5, scandals=0)
            result = calculate_utility(voter, cand, ISSUES)
            assert 0.5 <= result["utility"] <= 1.0

    def test_empty_issues(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        cand = _candidate(position=0.5, charisma=0.5, scandals=0)
        result = calculate_utility(voter, cand, [])
        # No issues → issue_score = 0
        # utility = 0 + 0 + 0.075 + 0 + 0 = 0.075
        assert abs(result["utility"] - 0.075) < 0.001

    def test_result_has_breakdown(self):
        voter = _voter(lean=0.5)
        cand = _candidate(position=0.5)
        result = calculate_utility(voter, cand, ISSUES)
        assert "breakdown" in result
        assert "issue_score" in result["breakdown"]
        assert "loyalty_bonus" in result["breakdown"]
        assert "charisma_effect" in result["breakdown"]
        assert "scandal_penalty" in result["breakdown"]

    def test_will_vote_with_high_utility(self):
        with patch.object(random, "random", return_value=0.5):
            voter = _voter(lean=0.5, likelihood=1.0)
            cand = _candidate(position=0.5)
            result = calculate_utility(voter, cand, ISSUES)
            assert result["will_vote"] is True

    def test_will_vote_false_when_low_utility(self):
        voter = _voter(lean=0.0, likelihood=1.0)
        cand = _candidate(position=1.0)
        result = calculate_utility(voter, cand, ISSUES)
        assert result["will_vote"] is False

    def test_scandal_penalty(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        cand = _candidate(position=0.5, charisma=0.5, scandals=2)
        result = calculate_utility(voter, cand, ISSUES)
        # scandal_penalty = -0.3 * 2 = -0.6
        # utility = 0.675 - 0.6 = 0.075
        assert abs(result["utility"] - 0.075) < 0.001

    def test_low_charisma_amplifies_scandals(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        cand = _candidate(position=0.5, charisma=0.3, scandals=1)
        result = calculate_utility(voter, cand, ISSUES)
        # charisma=0.3 < 0.5 → scandal_penalty = -0.3 * 1 * 1.5 = -0.45
        # utility = 0.6*1 + 0.15*0.3 + (-0.45) + 0 = 0.6 + 0.045 - 0.45 = 0.195
        assert abs(result["utility"] - 0.195) < 0.001

    def test_gender_bonus_for_female_voter(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        voter["gender"] = "female"
        cand = _candidate(position=0.5, charisma=0.5, scandals=0)
        cand["policies"]["gender_equality"] = 0.8
        result = calculate_utility(voter, cand, ISSUES + ["gender_equality"])
        assert result["breakdown"]["gender_bonus"] > 0

    def test_high_dimension(self):
        many = [f"issue_{i}" for i in range(10)]
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        voter["issue_priorities"] = {i: 1.0 / 10 for i in many}
        voter["issue_positions"] = {i: 0.5 for i in many}
        cand = _candidate(position=0.5)
        cand["policies"] = {i: 0.5 for i in many}
        result = calculate_utility(voter, cand, many)
        assert 0.5 <= result["utility"] <= 1.0


class TestComputeSincereRanking:
    def test_returns_sorted_by_utility(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "C", position=0.9),
            _candidate(1, "A", position=0.1),
            _candidate(2, "B", position=0.5),
        ]
        ranking = compute_sincere_ranking(voter, candidates, ISSUES)
        names = [c["name"] for c in ranking]
        assert names[0] == "B"

    def test_empty_candidates(self):
        voter = _voter()
        assert compute_sincere_ranking(voter, [], ISSUES) == []

    def test_single_candidate(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        ranking = compute_sincere_ranking(voter, candidates, ISSUES)
        assert len(ranking) == 1
        assert ranking[0]["name"] == "A"


class TestComputeStrategicPluralityVote:
    def test_honest_when_preferred_in_top2(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.5),
            _candidate(1, "B", position=0.9),
        ]
        poll = {"A": 0.4, "B": 0.6}
        result = compute_strategic_plurality_vote(voter, candidates, ISSUES, poll)
        assert result == "A"

    def test_switch_to_viable_when_preferred_not_in_top2(self):
        voter = _voter(lean=0.1, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.1),
            _candidate(1, "B", position=0.5),
            _candidate(2, "C", position=0.9),
        ]
        poll = {"B": 0.5, "C": 0.4, "A": 0.1}
        result = compute_strategic_plurality_vote(voter, candidates, ISSUES, poll)
        assert result == "B"

    def test_returns_winner_key(self):
        voter = _voter(lean=0.5)
        candidates = [
            _candidate(0, "A", position=0.5),
            _candidate(1, "B", position=0.9),
        ]
        poll = {"A": 0.6, "B": 0.4}
        result = compute_strategic_plurality_vote(voter, candidates, ISSUES, poll)
        assert isinstance(result, str)

    def test_no_viable_top2_falls_back_to_preferred(self):
        voter = _voter(lean=0.1, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.1),
            _candidate(1, "X", position=0.5),  # not in poll
        ]
        poll = {"Y": 0.6, "Z": 0.4}  # neither in candidates
        result = compute_strategic_plurality_vote(voter, candidates, ISSUES, poll)
        assert result == "A"


class TestComputeStrategicBordaVote:
    def test_buries_threat(self):
        voter = _voter(lean=0.1, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.1),
            _candidate(1, "B", position=0.5),
            _candidate(2, "C", position=0.9),
        ]
        poll = {"B": 0.5, "A": 0.3, "C": 0.2}
        result = compute_strategic_borda_vote(voter, candidates, ISSUES, poll)
        assert result[0] == "A"
        assert result[-1] == "B"

    def test_sincere_when_preferred_leads(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.5),
            _candidate(1, "B", position=0.9),
        ]
        poll = {"A": 0.6, "B": 0.4}
        result = compute_strategic_borda_vote(voter, candidates, ISSUES, poll)
        assert result[0] == "A"


class TestComputeStrategicIRVVote:
    def test_compromise_when_preferred_not_viable(self):
        voter = _voter(lean=0.1, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.1),
            _candidate(1, "B", position=0.5),
            _candidate(2, "C", position=0.9),
        ]
        poll = {"B": 0.5, "C": 0.4, "A": 0.1}
        result = compute_strategic_irv_vote(voter, candidates, ISSUES, poll)
        assert result[0] == "B"

    def test_sincere_when_preferred_viable(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.5),
            _candidate(1, "B", position=0.9),
        ]
        poll = {"A": 0.6, "B": 0.4}
        result = compute_strategic_irv_vote(voter, candidates, ISSUES, poll)
        assert result[0] == "A"

    def test_no_viable_candidates_returns_sincere(self):
        voter = _voter(lean=0.1, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.1),
            _candidate(1, "X", position=0.5),
        ]
        poll = {"Y": 0.6, "Z": 0.4}
        result = compute_strategic_irv_vote(voter, candidates, ISSUES, poll)
        assert isinstance(result, list)
        assert result[0] == "A"


class TestComputeStrategicApprovalVote:
    def test_approves_only_top_when_clear_lead(self):
        voter = _voter(lean=0.1, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.1),
            _candidate(1, "B", position=0.9),
        ]
        result = compute_strategic_approval_vote(voter, candidates, ISSUES)
        assert result == ["A"]

    def test_approves_two_when_close(self):
        voter = _voter(lean=0.5, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.5),
            _candidate(1, "B", position=0.51),
        ]
        result = compute_strategic_approval_vote(voter, candidates, ISSUES)
        assert len(result) == 2
        assert "A" in result
        assert "B" in result

    def test_single_candidate(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        result = compute_strategic_approval_vote(voter, candidates, ISSUES)
        assert result == ["A"]


class TestComputeStrategicScoreVote:
    def test_preferred_gets_5_threat_gets_0(self):
        voter = _voter(lean=0.1, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.1),
            _candidate(1, "B", position=0.5),
        ]
        poll = {"B": 0.6, "A": 0.4}
        result = compute_strategic_score_vote(voter, candidates, ISSUES, poll)
        assert result["A"] == 5
        assert result["B"] == 0

    def test_others_get_proportional_scores(self):
        voter = _voter(lean=0.1, party_loyalty=0.0, mood=0.0)
        candidates = [
            _candidate(0, "A", position=0.1),
            _candidate(1, "B", position=0.5),
            _candidate(2, "C", position=0.3),
        ]
        poll = {"B": 0.5, "A": 0.3, "C": 0.2}
        result = compute_strategic_score_vote(voter, candidates, ISSUES, poll)
        assert result["A"] == 5
        assert result["B"] == 0
        assert "C" in result

    def test_single_candidate(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        poll = {"A": 1.0}
        result = compute_strategic_score_vote(voter, candidates, ISSUES, poll)
        assert result == {"A": 5}


class TestApplySocialInfluence:
    def test_returns_same_length(self):
        voters = [_voter(i, lean=0.5) for i in range(5)]
        poll = {"A": 0.6, "B": 0.4}
        candidates = [_candidate(0, "A", 0.5), _candidate(1, "B", 0.5)]
        result = apply_social_influence(voters, poll, candidates)
        assert len(result) == len(voters)

    def test_no_change_with_zero_conformity(self):
        voters = [_voter(i, lean=0.5) for i in range(3)]
        for v in voters:
            v["social_conformity"] = 0.0
        poll = {"A": 0.6, "B": 0.4}
        candidates = [_candidate(0, "A", 0.5), _candidate(1, "B", 0.5)]
        result = apply_social_influence(voters, poll, candidates)
        for orig, new in zip(voters, result):
            assert orig["political_lean_normalized"] == new["political_lean_normalized"]

    def test_moves_toward_leader(self):
        voters = [_voter(0, lean=0.5)]
        voters[0]["social_conformity"] = 0.8
        poll = {"A": 0.6, "B": 0.4}
        candidates = [_candidate(0, "A", 0.9), _candidate(1, "B", 0.5)]
        result = apply_social_influence(voters, poll, candidates, influence_strength=1.0)
        assert result[0]["political_lean_normalized"] > 0.5

    def test_empty_poll_returns_original(self):
        voters = [_voter(0, lean=0.5)]
        result = apply_social_influence(voters, {}, [], influence_strength=1.0)
        assert len(result) == 1

    def test_preserves_voter_count(self):
        voters = [_voter(i, lean=0.5) for i in range(10)]
        for v in voters:
            v["social_conformity"] = 0.0
        poll = {"A": 0.6}
        candidates = [_candidate(0, "A", 0.8)]
        result = apply_social_influence(voters, poll, candidates)
        assert len(result) == 10


class TestRunBandwagonSimulation:
    def test_basic_run(self):
        result = run_bandwagon_simulation(num_voters=10, num_rounds=2, seed=42)
        assert isinstance(result["rounds"], list)
        assert len(result["rounds"]) >= 1

    def test_trajectory_length(self):
        result = run_bandwagon_simulation(num_voters=10, num_rounds=3, seed=42)
        assert len(result["rounds"]) == result["num_rounds"] + 1

    def test_round_has_poll_standings(self):
        result = run_bandwagon_simulation(num_voters=10, num_rounds=1, seed=42)
        for r in result["rounds"]:
            assert "poll_standings" in r
            assert "methods" in r

    def test_with_explicit_candidates(self):
        issues = ["economy", "environment"]
        candidates = [
            create_candidate(issues, 0, "X", "Green"),
            create_candidate(issues, 1, "Y", "Conservative"),
        ]
        result = run_bandwagon_simulation(
            num_voters=10, candidates=candidates, issues=issues, num_rounds=1, seed=42,
        )
        assert len(result["rounds"]) == 2

    def test_amplification_by_method_present(self):
        result = run_bandwagon_simulation(num_voters=10, num_rounds=2, seed=42)
        assert "amplification_by_method" in result
        assert "plurality" in result["amplification_by_method"]

    def test_convergence_round_may_be_none(self):
        result = run_bandwagon_simulation(num_voters=5, num_rounds=1, seed=42)
        assert "convergence_round" in result


class TestVotePlurality:
    def test_returns_best_candidate_name(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5), _candidate(1, "B", position=0.9)]
        result = vote_plurality(voter, candidates, ISSUES)
        assert result == "A"

    def test_returns_none_when_all_utility_low(self):
        voter = _voter(lean=0.0, party_loyalty=0.0, mood=0.0)
        candidates = [_candidate(0, "A", position=1.0, charisma=0.0, scandals=5)]
        result = vote_plurality(voter, candidates, ISSUES)
        assert result is None

    def test_single_candidate(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        result = vote_plurality(voter, candidates, ISSUES)
        assert result == "A"


class TestVoteRanked:
    def test_returns_sorted_candidate_names(self):
        voter = _voter(lean=0.5)
        candidates = [
            _candidate(0, "C", position=0.9),
            _candidate(1, "A", position=0.5),
            _candidate(2, "B", position=0.51),
        ]
        result = vote_ranked(voter, candidates, ISSUES)
        names = [c["name"] for c in result]
        assert names[0] == "A"

    def test_empty_returns_empty_list(self):
        voter = _voter(lean=0.5)
        assert vote_ranked(voter, [], ISSUES) == []


class TestVoteScore:
    def test_returns_score_dict(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5), _candidate(1, "B", position=0.9)]
        result = vote_score(voter, candidates, ISSUES)
        assert isinstance(result, dict)
        assert "A" in result
        assert "B" in result
        assert 0 <= result["A"] <= 5
        assert 0 <= result["B"] <= 5

    def test_empty_candidates(self):
        voter = _voter(lean=0.5)
        assert vote_score(voter, [], ISSUES) == {}

    def test_single_candidate(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        result = vote_score(voter, candidates, ISSUES)
        assert result["A"] >= 3


class TestSimulateVote:
    def test_plurality_sincere(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        result = simulate_vote(voter, candidates, ISSUES, method="plurality")
        assert result == "A"

    def test_ranked_sincere(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        result = simulate_vote(voter, candidates, ISSUES, method="ranked")
        assert isinstance(result, list)
        assert result[0] == "A"

    def test_score_sincere(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        result = simulate_vote(voter, candidates, ISSUES, method="score")
        assert isinstance(result, dict)
        assert 0 <= result["A"] <= 5

    def test_approval_sincere(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        result = simulate_vote(voter, candidates, ISSUES, method="approval")
        assert isinstance(result, list)
        assert "A" in result

    def test_borda_sincere(self):
        voter = _voter(lean=0.5)
        candidates = [_candidate(0, "A", position=0.5)]
        result = simulate_vote(voter, candidates, ISSUES, method="borda")
        assert isinstance(result, list)
        assert result[0] == "A"

    def test_voter_does_not_vote(self):
        voter = _voter(lean=0.5, likelihood=0.0)
        candidates = [_candidate(0, "A", position=0.5)]
        result = simulate_vote(voter, candidates, ISSUES, method="plurality")
        assert result is None

    def test_strategic_plurality(self):
        voter = _voter(lean=0.1, likelihood=1.0)
        voter["voting_style"] = "strategic"
        candidates = [_candidate(0, "A", position=0.1), _candidate(1, "B", position=0.5)]
        poll = {"B": 0.6, "A": 0.4}
        result = simulate_vote(voter, candidates, ISSUES, method="plurality", poll_standings=poll)
        assert result == "A"

    def test_strategic_approval_no_poll_needed(self):
        voter = _voter(lean=0.1, likelihood=1.0)
        voter["voting_style"] = "strategic"
        candidates = [_candidate(0, "A", position=0.1), _candidate(1, "B", position=0.9)]
        result = simulate_vote(voter, candidates, ISSUES, method="approval")
        assert isinstance(result, list)
        assert "A" in result

    def test_strategic_score_with_poll(self):
        voter = _voter(lean=0.1, likelihood=1.0)
        voter["voting_style"] = "strategic"
        candidates = [_candidate(0, "A", position=0.1), _candidate(1, "B", position=0.5)]
        poll = {"B": 0.6, "A": 0.4}
        result = simulate_vote(voter, candidates, ISSUES, method="score", poll_standings=poll)
        assert isinstance(result, dict)
        assert result["A"] == 5

    def test_strategic_irv_with_poll(self):
        voter = _voter(lean=0.1, likelihood=1.0)
        voter["voting_style"] = "strategic"
        candidates = [
            _candidate(0, "A", position=0.1),
            _candidate(1, "B", position=0.5),
            _candidate(2, "C", position=0.9),
        ]
        poll = {"B": 0.5, "C": 0.4, "A": 0.1}
        result = simulate_vote(voter, candidates, ISSUES, method="irv", poll_standings=poll)
        assert isinstance(result, list)

    def test_strategic_without_poll_falls_through(self):
        voter = _voter(lean=0.5, likelihood=1.0)
        voter["voting_style"] = "strategic"
        candidates = [_candidate(0, "A", position=0.5)]
        result = simulate_vote(voter, candidates, ISSUES, method="plurality")
        assert result == "A"

    def test_unknown_method_returns_none(self):
        voter = _voter(lean=0.5, likelihood=1.0)
        candidates = [_candidate(0, "A", position=0.5)]
        result = simulate_vote(voter, candidates, ISSUES, method="unknown")
        assert result is None


class TestRunSimulation:
    def test_returns_list_of_results(self):
        results = run_simulation(num_voters=5, num_candidates=2, method="plurality", seed=42)
        assert isinstance(results, list)
        assert len(results) == 5

    def test_each_result_has_keys(self):
        results = run_simulation(num_voters=3, num_candidates=2, method="plurality", seed=42)
        for r in results:
            assert "voter" in r
            assert "vote" in r
            assert "utilities" in r

    def test_single_voter_single_candidate(self):
        results = run_simulation(num_voters=1, num_candidates=1, method="plurality", seed=42)
        assert len(results) == 1
        assert "vote" in results[0]
        assert "utilities" in results[0]

    def test_ranked_method(self):
        results = run_simulation(num_voters=3, num_candidates=2, method="ranked", seed=42)
        for r in results:
            assert isinstance(r["vote"], list) or r["vote"] is None

    def test_score_method(self):
        results = run_simulation(num_voters=3, num_candidates=2, method="score", seed=42)
        for r in results:
            assert isinstance(r["vote"], dict) or r["vote"] is None

    def test_high_dimension(self):
        many = [f"issue_{i}" for i in range(8)]
        results = run_simulation(num_voters=3, num_candidates=2, method="plurality", seed=42)
        assert len(results) == 3

    def test_ideology_distributions(self):
        for dist in ["centrist", "polarized", "left_skewed", "right_skewed"]:
            results = run_simulation(num_voters=3, num_candidates=2, method="plurality", seed=42, ideology_distribution=dist)
            assert len(results) == 3
