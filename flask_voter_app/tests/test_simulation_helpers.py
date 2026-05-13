"""Tests for simulation_helpers route-level helpers."""

import pytest
from app.routes.simulation_helpers import (
    _build_scenario_candidates,
    _build_scenario_voters,
    _parse_candidate_configs,
    _build_population,
    _run_five_methods,
)

_DEFAULT_ISSUES = [
    "economy", "environment", "healthcare", "education", "taxes",
    "social_welfare", "agriculture", "public_transport", "defense",
    "gender_equality", "pensions", "climate_change", "housing",
    "immigration", "crime_safety", "technology_innovation",
    "minimum_wage", "business_regulation", "jobs", "infrastructure",
]


class TestBuildScenarioCandidates:
    def test_skips_blank_candidates(self):
        raw = [
            {"name": "Alice", "ideology": 0.5, "is_blank": False},
            {"name": "Blank", "is_blank": True},
            {"name": "Bob", "ideology": -0.5, "is_blank": False},
        ]
        result = _build_scenario_candidates(raw, _DEFAULT_ISSUES)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"

    def test_clamps_ideology_to_minus_one_to_one(self):
        raw = [{"name": "X", "ideology": -5.0}]
        result = _build_scenario_candidates(raw, _DEFAULT_ISSUES)
        assert result[0]["ideology_position"] == 0.0  # (-1 + 1) / 2

    def test_uses_defaults_when_fields_missing(self):
        raw = [{}]
        result = _build_scenario_candidates(raw, _DEFAULT_ISSUES)
        assert result[0]["name"] == "Candidate 1"
        assert result[0]["ideology_position"] == 0.5

    def test_uses_custom_positions(self):
        raw = [{"name": "A", "ideology": 0.0, "positions": {"economy": 0.8, "environment": 0.2, "social": 0.3}}]
        result = _build_scenario_candidates(raw, _DEFAULT_ISSUES)
        assert result[0]["policies"]["economy"] == 0.8
        assert result[0]["policies"]["environment"] == 0.2
        assert result[0]["policies"]["social_welfare"] == 0.3


class TestBuildScenarioVoters:
    def test_returns_expected_number_of_voters(self):
        electorate = {"num_voters": 50, "ideology_preset": "centrist", "dissatisfaction_rate": 0.1}
        voters = _build_scenario_voters(electorate, _DEFAULT_ISSUES)
        assert len(voters) == 50

    def test_minimum_ten_voters(self):
        electorate = {"num_voters": 3}
        voters = _build_scenario_voters(electorate, _DEFAULT_ISSUES)
        assert len(voters) == 10

    def test_dissatisfaction_override(self):
        electorate = {"num_voters": 20, "dissatisfaction_rate": 0.0}
        voters = _build_scenario_voters(electorate, _DEFAULT_ISSUES, dissatisfaction_override=0.5)
        for v in voters:
            assert v["blank_threshold"] > 0

    def test_zero_dissatisfaction_does_not_increase_threshold(self):
        electorate = {"num_voters": 20, "dissatisfaction_rate": 0.0}
        voters = _build_scenario_voters(electorate, _DEFAULT_ISSUES)
        # With 0 dissatisfaction, no extra is added to blank_threshold.
        # Values come from create_voter's np.random.beta(3, 5).
        assert len(voters) == 20
        for v in voters:
            assert "blank_threshold" in v


class TestParseCandidateConfigs:
    def test_string_list(self):
        raw = ["Alice", "Bob"]
        result = _parse_candidate_configs(raw)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"

    def test_dict_list(self):
        raw = [{"name": "X", "party": "Green"}, {"name": "Y", "party": "Liberal"}]
        result = _parse_candidate_configs(raw)
        assert result[0]["party"] == "Green"
        assert result[1]["party"] == "Liberal"

    def test_mixed_list(self):
        raw = ["Alice", {"name": "Bob", "party": "Green"}]
        result = _parse_candidate_configs(raw)
        assert result[0]["party"] == "Green"
        assert result[1]["party"] == "Green"

    def test_empty_list(self):
        assert _parse_candidate_configs([]) == []

    def test_default_party_cycles(self):
        raw = ["A", "B", "C", "D", "E"]
        result = _parse_candidate_configs(raw)
        assert result[0]["party"] == "Green"
        assert result[1]["party"] == "Conservative"
        assert result[2]["party"] == "Liberal"
        assert result[3]["party"] == "Independent"
        assert result[4]["party"] == "Green"


class TestBuildPopulation:
    def test_returns_voters_candidates_issues(self):
        cfg = _parse_candidate_configs([{"name": "A"}, {"name": "B"}])
        voters, candidates, issues = _build_population(cfg, num_voters=25)
        assert len(voters) == 25
        assert len(candidates) == 2
        assert len(issues) == 20

    def test_ideology_distribution(self):
        cfg = _parse_candidate_configs([{"name": "X"}])
        voters, candidates, issues = _build_population(cfg, num_voters=10, ideology_distribution="polarized")
        assert len(voters) == 10
        assert len(candidates) == 1


class TestRunFiveMethods:
    def test_returns_expected_structure(self):
        cfg = _parse_candidate_configs([{"name": "Alice"}, {"name": "Bob"}])
        voters, candidates, issues = _build_population(cfg, num_voters=50)
        result = _run_five_methods(voters, candidates, issues, blank_vote=False)
        assert "condorcet_winner" in result
        assert "methods" in result
        expected = {"plurality", "irv", "borda", "schulze", "approval"}
        assert set(result["methods"].keys()) == expected

    def test_blank_vote_includes_blank_pct(self):
        cfg = _parse_candidate_configs([{"name": "Alice"}, {"name": "Bob"}])
        voters, candidates, issues = _build_population(cfg, num_voters=50)
        result = _run_five_methods(voters, candidates, issues, blank_vote=True)
        assert "blank_pct" in result

    def test_blank_vote_applies_rule(self):
        cfg = _parse_candidate_configs([{"name": "Alice"}, {"name": "Bob"}])
        voters, candidates, issues = _build_population(cfg, num_voters=50)
        result = _run_five_methods(voters, candidates, issues, blank_vote=True)
        for m in result["methods"].values():
            assert "blank_rule_applied" in m
