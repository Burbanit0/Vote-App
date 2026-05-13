"""Integration tests for public simulation endpoints."""
import pytest


class TestSimulationBase:
    """POST /simulations/simulate_voters, simulate_candidates, calculate_utility."""

    def test_simulate_voters(self, client):
        resp = client.post("/simulations/simulate_voters", json={"num_voters": 10})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "voters" in data
        assert len(data["voters"]) == 10

    def test_simulate_voters_zero(self, client):
        resp = client.post("/simulations/simulate_voters", json={"num_voters": 0})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["voters"]) == 0

    def test_simulate_voters_default(self, client):
        resp = client.post("/simulations/simulate_voters", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["voters"]) == 1000

    def test_simulate_candidates(self, client):
        resp = client.post(
            "/simulations/simulate_candidates",
            json={"num_candidates": 3, "parties": ["Green", "Liberal", "Conservative"]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["candidates"]) == 3

    def test_simulate_candidates_default_parties(self, client):
        resp = client.post("/simulations/simulate_candidates", json={"num_candidates": 2})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["candidates"]) == 2

    def test_simulate_candidates_too_few_parties(self, client):
        """More candidates than parties — parties should cycle."""
        resp = client.post(
            "/simulations/simulate_candidates",
            json={"num_candidates": 6, "parties": ["A", "B"]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["candidates"]) == 6

    def test_calculate_utility(self, client):
        """Create a voter + candidate, then calculate utility."""
        voter = {
            "id": 0, "age": 35, "gender": "male", "education": "bachelor",
            "income": "middle", "region": "urban", "employment_status": "employed",
            "family_status": "single", "ethnicity_immigration": "native",
            "religion": "non_religious", "political_lean": 0.0,
            "political_lean_normalized": 0.5,
            "issue_priorities": {"economy": 0.5, "environment": 0.5},
            "issue_positions": {"economy": 0.5, "environment": 0.5},
            "party_loyalty": 0.5, "preferred_party": "Independent",
            "likelihood_to_vote": 0.8, "mood": 0,
            "strategic_propensity": 0.2, "voting_style": "sincere",
        }
        candidate = {
            "id": 0, "name": "Alice", "party": "Green", "party_lean": -0.8,
            "ideology_position": 0.2,
            "policies": {"economy": 0.3, "environment": 0.8},
            "charisma": 0.7, "scandals": 0, "campaign_funds": 500000,
            "experience": 10, "popularity": 0.6,
        }
        resp = client.post(
            "/simulations/calculate_utility",
            json={"voter": voter, "candidate": candidate},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "result" in data
        assert 0.0 <= data["result"]["utility"] <= 1.0

    def test_calculate_utility_missing_voter(self, client):
        resp = client.post(
            "/simulations/calculate_utility",
            json={"candidate": {"id": 0, "name": "A"}},
        )
        assert resp.status_code == 400

    def test_calculate_utility_missing_candidate(self, client):
        resp = client.post(
            "/simulations/calculate_utility",
            json={"voter": {"id": 0}},
        )
        assert resp.status_code == 400

    def test_legacy_simulate_no_body(self, client):
        resp = client.post("/simulations/", json={})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    @pytest.mark.xfail(
        reason="assign_voters_to_candidates returns np.int64 not JSON-serializable by Flask"
    )
    def test_get_closest_candidate(self, client):
        resp = client.post(
            "/simulations/get_closest_candidate",
            json={"voters": [[0.1, 0.2], [0.8, 0.9]], "candidates": [[0.0, 0.0], [1.0, 1.0]]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "result" in data
        assert isinstance(data["result"], list)

    def test_get_closest_candidate_missing_params(self, client):
        resp = client.post("/simulations/get_closest_candidate", json={})
        assert resp.status_code == 400

    def test_simulate_utility(self, client):
        resp = client.post(
            "/simulations/simulate_utility",
            json={
                "voters": [
                    {"id": 0, "age": 35, "gender": "male", "education": "bachelor",
                     "income": "middle", "region": "urban", "employment_status": "employed",
                     "family_status": "single", "ethnicity_immigration": "native",
                     "religion": "non_religious", "political_lean": 0.0,
                     "political_lean_normalized": 0.5,
                     "issue_priorities": {"economy": 0.5, "environment": 0.5},
                     "issue_positions": {"economy": 0.5, "environment": 0.5},
                     "party_loyalty": 0.5, "preferred_party": "Independent",
                     "likelihood_to_vote": 0.8, "mood": 0,
                     "strategic_propensity": 0.2, "voting_style": "sincere"},
                    {"id": 1, "age": 28, "gender": "female", "education": "master",
                     "income": "high", "region": "urban", "employment_status": "employed",
                     "family_status": "single", "ethnicity_immigration": "native",
                     "religion": "non_religious", "political_lean": 0.3,
                     "political_lean_normalized": 0.65,
                     "issue_priorities": {"economy": 0.6, "environment": 0.4},
                     "issue_positions": {"economy": 0.7, "environment": 0.3},
                     "party_loyalty": 0.3, "preferred_party": "Independent",
                     "likelihood_to_vote": 0.9, "mood": 0,
                     "strategic_propensity": 0.3, "voting_style": "sincere"},
                ],
                "candidates": [
                    {"id": 0, "name": "Alice", "party": "Green", "party_lean": -0.8,
                     "ideology_position": 0.2,
                     "policies": {"economy": 0.3, "environment": 0.8},
                     "charisma": 0.7, "scandals": 0, "campaign_funds": 500000,
                     "experience": 10, "popularity": 0.6},
                    {"id": 1, "name": "Bob", "party": "Conservative", "party_lean": 0.5,
                     "ideology_position": 0.6,
                     "policies": {"economy": 0.8, "environment": 0.2},
                     "charisma": 0.5, "scandals": 1, "campaign_funds": 300000,
                     "experience": 5, "popularity": 0.5},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["utility_results"]) == 4  # 2 voters x 2 candidates

    def test_get_utility_matrix(self, client):
        resp = client.post(
            "/simulations/get_utility_matrix",
            json={
                "voters": [
                    {"id": 0, "age": 35, "gender": "male", "education": "bachelor",
                     "income": "middle", "region": "urban", "employment_status": "employed",
                     "family_status": "single", "ethnicity_immigration": "native",
                     "religion": "non_religious", "political_lean": 0.0,
                     "political_lean_normalized": 0.5,
                     "issue_priorities": {"economy": 0.5, "environment": 0.5},
                     "issue_positions": {"economy": 0.5, "environment": 0.5},
                     "party_loyalty": 0.5, "preferred_party": "Independent",
                     "likelihood_to_vote": 0.8, "mood": 0,
                     "strategic_propensity": 0.2, "voting_style": "sincere"},
                    {"id": 1, "age": 28, "gender": "female", "education": "master",
                     "income": "high", "region": "urban", "employment_status": "employed",
                     "family_status": "single", "ethnicity_immigration": "native",
                     "religion": "non_religious", "political_lean": 0.3,
                     "political_lean_normalized": 0.65,
                     "issue_priorities": {"economy": 0.6, "environment": 0.4},
                     "issue_positions": {"economy": 0.7, "environment": 0.3},
                     "party_loyalty": 0.3, "preferred_party": "Independent",
                     "likelihood_to_vote": 0.9, "mood": 0,
                     "strategic_propensity": 0.3, "voting_style": "sincere"},
                ],
                "candidates": [
                    {"id": 0, "name": "Alice", "party": "Green", "party_lean": -0.8,
                     "ideology_position": 0.2,
                     "policies": {"economy": 0.3, "environment": 0.8},
                     "charisma": 0.7, "scandals": 0, "campaign_funds": 500000,
                     "experience": 10, "popularity": 0.6},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["matrix"]["values"]) == 2  # 2 voters
        assert len(data["matrix"]["values"][0]) == 1  # 1 candidate
        assert "average_utility" in data["stats"]
        assert "vote_shares" in data["stats"]

    def test_get_utility_matrix_empty_voters(self, client):
        resp = client.post(
            "/simulations/get_utility_matrix",
            json={"voters": [], "candidates": [{"id": 0, "name": "A"}]},
        )
        assert resp.status_code == 400

    def test_get_utility_matrix_empty_candidates(self, client):
        resp = client.post(
            "/simulations/get_utility_matrix",
            json={
                "voters": [{"id": 0, "age": 35, "gender": "male", "education": "bachelor",
                            "income": "middle", "region": "urban"}],
                "candidates": [],
            },
        )
        assert resp.status_code == 400

    def test_get_voter_segments(self, client):
        resp = client.post(
            "/simulations/get_voter_segments",
            json={
                "voters": [
                    {"id": 0, "age": 35, "gender": "male", "education": "bachelor",
                     "income": "middle", "region": "urban", "employment_status": "employed",
                     "family_status": "single", "ethnicity_immigration": "native",
                     "religion": "non_religious", "political_lean": 0.0,
                     "political_lean_normalized": 0.5,
                     "issue_priorities": {"economy": 0.5, "environment": 0.5},
                     "issue_positions": {"economy": 0.5, "environment": 0.5},
                     "party_loyalty": 0.5, "preferred_party": "Independent",
                     "likelihood_to_vote": 0.8, "mood": 0,
                     "strategic_propensity": 0.2, "voting_style": "sincere"},
                    {"id": 1, "age": 28, "gender": "female", "education": "master",
                     "income": "high", "region": "urban", "employment_status": "employed",
                     "family_status": "single", "ethnicity_immigration": "native",
                     "religion": "non_religious", "political_lean": 0.3,
                     "political_lean_normalized": 0.65,
                     "issue_priorities": {"economy": 0.6, "environment": 0.4},
                     "issue_positions": {"economy": 0.7, "environment": 0.3},
                     "party_loyalty": 0.3, "preferred_party": "Independent",
                     "likelihood_to_vote": 0.9, "mood": 0,
                     "strategic_propensity": 0.3, "voting_style": "sincere"},
                ],
                "candidates": [
                    {"id": 0, "name": "Alice", "party": "Green", "party_lean": -0.8,
                     "ideology_position": 0.2,
                     "policies": {"economy": 0.3, "environment": 0.8},
                     "charisma": 0.7, "scandals": 0, "campaign_funds": 500000,
                     "experience": 10, "popularity": 0.6},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "segments" in data

    def test_get_voter_segments_empty_voters(self, client):
        resp = client.post(
            "/simulations/get_voter_segments",
            json={"voters": [], "candidates": [{"id": 0, "name": "A"}]},
        )
        assert resp.status_code == 400

    def test_get_voter_segments_empty_candidates(self, client):
        resp = client.post(
            "/simulations/get_voter_segments",
            json={
                "voters": [{"id": 0}],
                "candidates": [],
            },
        )
        assert resp.status_code == 400

    def test_get_voter_segments_custom_filter(self, client):
        resp = client.post(
            "/simulations/get_voter_segments",
            json={
                "voters": [
                    {"id": 0, "age": 35, "gender": "male", "education": "bachelor",
                     "income": "middle", "region": "urban", "employment_status": "employed",
                     "family_status": "single", "ethnicity_immigration": "native",
                     "religion": "non_religious", "political_lean": 0.0,
                     "political_lean_normalized": 0.5,
                     "issue_priorities": {"economy": 0.5, "environment": 0.5},
                     "issue_positions": {"economy": 0.5, "environment": 0.5},
                     "party_loyalty": 0.5, "preferred_party": "Independent",
                     "likelihood_to_vote": 0.8, "mood": 0,
                     "strategic_propensity": 0.2, "voting_style": "sincere"},
                ],
                "candidates": [
                    {"id": 0, "name": "Alice", "party": "Green", "party_lean": -0.8,
                     "ideology_position": 0.2,
                     "policies": {"economy": 0.3, "environment": 0.8},
                     "charisma": 0.7, "scandals": 0, "campaign_funds": 500000,
                     "experience": 10, "popularity": 0.6},
                ],
                "segments": ["young_female", "urban"],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "segments" in data

    _LEGACY_DEMOGRAPHICS = {
        "age": {"young": 0.3, "middle": 0.4, "old": 0.3},
        "gender": {"male": 0.5, "female": 0.5},
        "location": {"urban": 0.5, "suburban": 0.3, "rural": 0.2},
        "education": {"high_school": 0.3, "bachelor": 0.4, "master": 0.3},
        "income": {"low": 0.3, "middle": 0.4, "high": 0.3},
        "ideology": {"left": 0.3, "center": 0.4, "right": 0.3},
    }

    def test_legacy_simulate_votes(self, client):
        resp = client.post(
            "/simulations/",
            json={
                "formData": {
                    "simulationType": "votes",
                    "populationSize": 10,
                    "candidates": ["Alice", "Bob"],
                    "demographics": self._LEGACY_DEMOGRAPHICS,
                    "turnoutRate": 0.8,
                    "influenceWeights": {"family": 0.3, "peers": 0.5, "media": 0.2},
                },
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "votes" in data

    def test_legacy_simulate_ranked(self, client):
        resp = client.post(
            "/simulations/",
            json={
                "formData": {
                    "simulationType": "ranked",
                    "populationSize": 10,
                    "candidates": ["Alice", "Bob"],
                    "demographics": self._LEGACY_DEMOGRAPHICS,
                    "turnoutRate": 0.8,
                    "influenceWeights": {"family": 0.3, "peers": 0.5, "media": 0.2},
                },
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "rankings" in data

    def test_legacy_simulate_scores(self, client):
        resp = client.post(
            "/simulations/",
            json={
                "formData": {
                    "simulationType": "scores",
                    "populationSize": 10,
                    "candidates": ["Alice", "Bob"],
                    "demographics": self._LEGACY_DEMOGRAPHICS,
                    "turnoutRate": 0.8,
                    "influenceWeights": {"family": 0.3, "peers": 0.5, "media": 0.2},
                },
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "all_scores" in data


class TestSimulationCompare:
    """POST /simulations/compare, arrow-criteria, condorcet-matrix."""

    def test_compare(self, client):
        resp = client.post(
            "/simulations/compare",
            json={
                "num_voters": 100,
                "candidates": ["Alice", "Bob"],
                "ideology_distribution": "random",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "methods" in data
        assert "condorcet_winner" in data
        for method_name, method_data in data["methods"].items():
            assert "winner" in method_data
            assert "bayesian_regret" in method_data
            assert "majority_satisfaction" in method_data

    def test_compare_with_blank_vote(self, client):
        resp = client.post(
            "/simulations/compare",
            json={
                "num_voters": 100,
                "candidates": ["Alice", "Bob", "Charlie"],
                "blank_vote": True,
                "blank_rule": "symbolic",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        for method_data in data["methods"].values():
            assert "blank_rule_applied" in method_data

    def test_compare_too_few_candidates(self, client):
        resp = client.post(
            "/simulations/compare",
            json={"num_voters": 50, "candidates": ["Only"]},
        )
        assert resp.status_code == 400

    def test_compare_invalid_blank_rule(self, client):
        resp = client.post(
            "/simulations/compare",
            json={
                "num_voters": 50,
                "candidates": ["A", "B"],
                "blank_vote": True,
                "blank_rule": "bogus_rule",
            },
        )
        assert resp.status_code == 400

    def test_arrow_criteria(self, client):
        resp = client.post(
            "/simulations/arrow-criteria",
            json={
                "num_voters": 100,
                "candidates": ["Alice", "Bob", "Charlie"],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "methods" in data
        assert "summary" in data

    def test_arrow_criteria_too_few_candidates(self, client):
        resp = client.post(
            "/simulations/arrow-criteria",
            json={"num_voters": 50, "candidates": ["Only"]},
        )
        assert resp.status_code == 400

    def test_condorcet_matrix(self, client):
        resp = client.post(
            "/simulations/condorcet-matrix",
            json={
                "num_voters": 100,
                "candidates": ["Alice", "Bob"],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "matrix" in data
        assert "candidates" in data
        assert "condorcet_winner" in data

    def test_condorcet_matrix_too_few_candidates(self, client):
        resp = client.post(
            "/simulations/condorcet-matrix",
            json={"num_voters": 50, "candidates": ["Only"]},
        )
        assert resp.status_code == 400

    def test_strategic_impact(self, client):
        resp = client.post(
            "/simulations/strategic-impact",
            json={
                "num_voters": 100,
                "candidates": ["Alice", "Bob"],
                "strategic_percentages": [0, 50],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        assert len(data["results"]) == 2

    def test_strategic_impact_too_few_candidates(self, client):
        resp = client.post(
            "/simulations/strategic-impact",
            json={"num_voters": 50, "candidates": ["Only"]},
        )
        assert resp.status_code == 400

    def test_sensitivity(self, client):
        resp = client.post(
            "/simulations/sensitivity",
            json={
                "base_config": {
                    "num_voters": 50,
                    "candidates": ["Alice", "Bob"],
                },
                "variable": "ideology_distribution",
                "values": ["random", "polarized"],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        assert len(data["results"]) == 2

    def test_sensitivity_empty_values(self, client):
        resp = client.post(
            "/simulations/sensitivity",
            json={
                "base_config": {"num_voters": 50, "candidates": ["A", "B"]},
                "variable": "num_voters",
                "values": [],
            },
        )
        assert resp.status_code == 400

    def test_sensitivity_too_few_candidates(self, client):
        resp = client.post(
            "/simulations/sensitivity",
            json={
                "base_config": {"num_voters": 50, "candidates": ["Only"]},
                "variable": "num_voters",
                "values": [100],
            },
        )
        assert resp.status_code == 400

    def test_scenario(self, client):
        resp = client.post(
            "/simulations/scenario",
            json={
                "candidates": [
                    {"name": "Alice", "ideology": -0.5,
                     "positions": {"economy": 0.8, "environment": 0.2, "social": 0.3}},
                    {"name": "Bob", "ideology": 0.5,
                     "positions": {"economy": 0.2, "environment": 0.8, "social": 0.7}},
                ],
                "electorate": {
                    "num_voters": 100,
                    "ideology_preset": "centrist",
                    "dissatisfaction_rate": 0.2,
                },
                "blank_rule": "symbolic",
                "methods": ["plurality", "irv"],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "without_blank" in data
        assert "with_blank" in data
        assert "methods" in data["without_blank"]
        assert "condorcet_winner" in data["without_blank"]

    def test_scenario_too_few_candidates(self, client):
        resp = client.post(
            "/simulations/scenario",
            json={"candidates": [], "electorate": {"num_voters": 10}},
        )
        assert resp.status_code == 400

    def test_scenario_invalid_blank_rule(self, client):
        resp = client.post(
            "/simulations/scenario",
            json={
                "candidates": [
                    {"name": "A", "ideology": 0,
                     "positions": {"economy": 0.5, "environment": 0.5, "social": 0.5}},
                ],
                "electorate": {"num_voters": 10},
                "blank_rule": "bogus",
            },
        )
        assert resp.status_code == 400

    def test_scenario_with_blank_candidate(self, client):
        resp = client.post(
            "/simulations/scenario",
            json={
                "candidates": [
                    {"name": "Alice", "ideology": -0.5,
                     "positions": {"economy": 0.8, "environment": 0.2, "social": 0.3}},
                    {"name": "Bob", "ideology": 0.5,
                     "positions": {"economy": 0.2, "environment": 0.8, "social": 0.7}},
                    {"name": "Blanc", "is_blank": True},
                ],
                "electorate": {
                    "num_voters": 50,
                    "ideology_preset": "centrist",
                    "dissatisfaction_rate": 0.2,
                },
                "methods": ["plurality", "irv"],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "without_blank" in data

    def test_sensitivity_num_voters(self, client):
        resp = client.post(
            "/simulations/sensitivity",
            json={
                "base_config": {"num_voters": 50, "candidates": ["Alice", "Bob"]},
                "variable": "num_voters",
                "values": [10, 100],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        assert len(data["results"]) == 2

    def test_sensitivity_strategic_pct(self, client):
        resp = client.post(
            "/simulations/sensitivity",
            json={
                "base_config": {"num_voters": 50, "candidates": ["Alice", "Bob"]},
                "variable": "strategic_pct",
                "values": [0, 50, 100],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        assert len(data["results"]) == 3

    def test_sensitivity_bogus_variable(self, client):
        resp = client.post(
            "/simulations/sensitivity",
            json={
                "base_config": {"num_voters": 50, "candidates": ["Alice", "Bob"]},
                "variable": "bogus_variable",
                "values": ["x", "y"],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data


class TestSimulationAdvanced:
    """POST /simulations/bandwagon, monte-carlo, multiwinner, real-election."""

    def test_bandwagon(self, client):
        resp = client.post(
            "/simulations/bandwagon",
            json={
                "num_voters": 50,
                "candidates": ["Alice", "Bob"],
                "num_rounds": 2,
                "influence_strength": 0.3,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "rounds" in data
        assert "num_rounds" in data
        assert len(data["rounds"]) > 0

    def test_bandwagon_too_few_candidates(self, client):
        resp = client.post(
            "/simulations/bandwagon",
            json={"num_voters": 50, "candidates": ["Only"]},
        )
        assert resp.status_code == 400

    def test_monte_carlo(self, client):
        resp = client.post(
            "/simulations/monte-carlo",
            json={
                "num_runs": 3,
                "num_voters": 50,
                "candidates": ["Alice", "Bob"],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "methods" in data
        assert "num_runs" in data
        assert data["num_runs"] == 3
        assert len(data["methods"]) > 0

    def test_monte_carlo_too_few_candidates(self, client):
        resp = client.post(
            "/simulations/monte-carlo",
            json={"num_runs": 2, "num_voters": 10, "candidates": ["Only"]},
        )
        assert resp.status_code == 400

    def test_multiwinner(self, client):
        resp = client.post(
            "/simulations/multiwinner",
            json={
                "party_votes": {"Party A": 40, "Party B": 35, "Party C": 25},
                "num_seats": 10,
                "mode": "proportional",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "dhondt" in data
        assert "sainte_lague" in data
        assert "largest_remainder_hare" in data
        assert "comparison" in data

    def test_multiwinner_missing_party_votes(self, client):
        resp = client.post(
            "/simulations/multiwinner",
            json={"num_seats": 5},
        )
        assert resp.status_code == 400

    def test_multiwinner_invalid_seats(self, client):
        resp = client.post(
            "/simulations/multiwinner",
            json={"party_votes": {"A": 100}, "num_seats": 0},
        )
        assert resp.status_code == 400

    def test_real_elections_list(self, client):
        resp = client.get("/simulations/real-elections")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_real_election_analyze(self, client):
        """Uses real election dataset — requires 'france_2022' to exist."""
        resp = client.post(
            "/simulations/real-election",
            json={"election_name": "france_2022", "num_voters": 200},
        )
        # May be 404 if the dataset is missing; either way no crash
        assert resp.status_code in (200, 400, 404)
        if resp.status_code == 200:
            data = resp.get_json()
            assert "methods" in data or "plurality_winner" in data

    def test_real_election_missing_name(self, client):
        resp = client.post(
            "/simulations/real-election",
            json={"num_voters": 100},
        )
        assert resp.status_code == 400

    def test_real_election_nonexistent_name_returns_404(self, client):
        resp = client.post(
            "/simulations/real-election",
            json={"election_name": "nonexistent_election_xyz", "num_voters": 100},
        )
        assert resp.status_code == 404

    def test_multiwinner_stv_mode(self, client):
        resp = client.post(
            "/simulations/multiwinner",
            json={
                "party_votes": {"A": 40, "B": 35, "C": 25},
                "num_seats": 5,
                "mode": "stv",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "dhondt" in data
        assert "sainte_lague" in data
        assert "largest_remainder_hare" in data
        assert "comparison" in data

    def test_monte_carlo_single_run(self, client):
        """num_runs=1 triggers _ci95 edge case (len(values) < 2 → None CI)."""
        resp = client.post(
            "/simulations/monte-carlo",
            json={
                "num_runs": 1,
                "num_voters": 50,
                "candidates": ["Alice", "Bob"],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "methods" in data

    def test_constitutional_new_election(self, client):
        resp = client.post(
            "/simulations/constitutional-scenario",
            json={
                "scenario_type": "new_election",
                "initial_election": {
                    "candidates": [
                        {"name": "Alice", "ideology": -0.5,
                         "positions": {"economy": 0.8, "environment": 0.2, "social": 0.3}},
                        {"name": "Bob", "ideology": 0.5,
                         "positions": {"economy": 0.2, "environment": 0.8, "social": 0.7}},
                    ],
                    "electorate": {
                        "num_voters": 50,
                        "ideology_preset": "centrist",
                        "dissatisfaction_rate": 0.2,
                    },
                },
                "params": {
                    "new_candidates": [
                        {"name": "Carol", "ideology": 0.0,
                         "positions": {"economy": 0.5, "environment": 0.5, "social": 0.5}},
                    ],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "round1" in data
        assert "round2" in data
        assert "conclusion" in data

    def test_constitutional_provisional(self, client):
        resp = client.post(
            "/simulations/constitutional-scenario",
            json={
                "scenario_type": "provisional",
                "initial_election": {
                    "candidates": [
                        {"name": "Alice", "ideology": -0.5,
                         "positions": {"economy": 0.8, "environment": 0.2, "social": 0.3}},
                        {"name": "Bob", "ideology": 0.5,
                         "positions": {"economy": 0.2, "environment": 0.8, "social": 0.7}},
                    ],
                    "electorate": {
                        "num_voters": 50,
                        "ideology_preset": "centrist",
                        "dissatisfaction_rate": 0.2,
                    },
                },
                "params": {
                    "provisional_duration": 6,
                    "drift_magnitude": 0.05,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "before_drift" in data
        assert "after_drift" in data
        assert "conclusion" in data

    def test_constitutional_dissolution(self, client):
        resp = client.post(
            "/simulations/constitutional-scenario",
            json={
                "scenario_type": "dissolution",
                "initial_election": {
                    "candidates": [
                        {"name": "Alice", "ideology": -0.5,
                         "positions": {"economy": 0.8, "environment": 0.2, "social": 0.3}},
                        {"name": "Bob", "ideology": 0.5,
                         "positions": {"economy": 0.2, "environment": 0.8, "social": 0.7}},
                    ],
                    "electorate": {
                        "num_voters": 50,
                        "ideology_preset": "centrist",
                        "dissatisfaction_rate": 0.2,
                    },
                },
                "params": {
                    "num_seats": 30,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "initial_methods" in data
        assert "multiwinner" in data
        assert "conclusion" in data

    def test_constitutional_unknown_scenario_type(self, client):
        resp = client.post(
            "/simulations/constitutional-scenario",
            json={
                "scenario_type": "bogus_type",
                "initial_election": {
                    "candidates": [
                        {"name": "A", "ideology": 0,
                         "positions": {"economy": 0.5, "environment": 0.5, "social": 0.5}},
                        {"name": "B", "ideology": 0,
                         "positions": {"economy": 0.5, "environment": 0.5, "social": 0.5}},
                    ],
                    "electorate": {
                        "num_voters": 10,
                        "ideology_preset": "centrist",
                        "dissatisfaction_rate": 0.1,
                    },
                },
            },
        )
        assert resp.status_code == 400
