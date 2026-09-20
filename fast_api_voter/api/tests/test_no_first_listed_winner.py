"""A rule that cannot separate the leaders elects nobody. These endpoints used
to write `winner or cand_names[0]`, reporting each tie below as a win for the
first-listed candidate -- and then comparing that phantom winner to others."""
from api.domain.election.workers import _primary_worker
from api.domain.election.workers_advanced import _demographic_turnout_worker, _dt_winner
from api.domain.election.workers_behavioral import _behavioral_biases_worker


def test_a_tied_general_election_has_no_winner_runner_up_or_median_distance():
    """25-25 between L1 and R2. L1, first on the ballot, used to win it."""
    parties = [
        {"name": "Left", "ideology_center": -0.5, "primary_voters_pct": 0.3,
         "primary_candidates": [{"name": "L1", "ideology_position": -0.6},
                                {"name": "L2", "ideology_position": -0.3}]},
        {"name": "Right", "ideology_center": 0.5, "primary_voters_pct": 0.3,
         "primary_candidates": [{"name": "R1", "ideology_position": 0.6},
                                {"name": "R2", "ideology_position": 0.3}]},
    ]
    body, status = _primary_worker({
        "parties": parties, "general_num_voters": 50, "seed": 447, "general_method": "irv",
    })
    assert status == 200
    assert body["general_vote_shares"] == {"L1": 0.5, "R2": 0.5}
    assert body["general_winner"] is None
    assert body["general_runner_up"] is None and body["median_voter_distance"] is None


def test_a_tie_among_actual_voters_is_a_change_not_a_first_listed_win():
    """IRV ties among those who turned out; everyone voting elects Alice. The
    tie used to read as Alice too, so the panel said turnout changed nothing."""
    body, _ = _demographic_turnout_worker({"num_voters": 50, "seed": 35, "method": "irv"})
    assert body["biased_result"]["winner"] is None
    assert body["corrected_result"]["winner"] == "Alice"
    assert body["winner_changed"] is True
    assert "égalité → 'Alice'" in body["pedagogical_note"]


def test_a_tied_sincere_result_is_not_reported_as_alice():
    body, _ = _behavioral_biases_worker({"num_voters": 50, "seed": 38, "method": "irv"})
    assert body["sincere_winner"] is None and body["biased_winner"] == "Alice"
    assert body["winner_changed"] is True
    assert "égalité → 'Alice'" in body["pedagogical_note"]


def test_nobody_voting_elects_nobody():
    assert _dt_winner([], {}, ["Alice", "Bob"], "plurality") == (None, {"Alice": 0.0, "Bob": 0.0})


def test_a_tied_primary_nominee_does_not_depend_on_listing_order():
    """L1 and L2 split Left's primary 9-9 and IRV elects nobody. The party still
    needs a nominee; it used to be whichever candidate was listed first."""
    def nominee(left_candidates):
        parties = [
            {"name": "Left", "ideology_center": -0.5, "primary_voters_pct": 0.3,
             "primary_candidates": left_candidates},
            {"name": "Right", "ideology_center": 0.5, "primary_voters_pct": 0.3,
             "primary_candidates": [{"name": "R1", "ideology_position": 0.6},
                                    {"name": "R2", "ideology_position": 0.3}]},
        ]
        body, _ = _primary_worker({"parties": parties, "general_num_voters": 60, "seed": 2,
                                   "primary_method": "irv"})
        left = body["primaries"][0]
        assert left["vote_shares"] == {"L1": 0.5, "L2": 0.5}
        return left["winner"]
    listed = [{"name": "L1", "ideology_position": -0.6}, {"name": "L2", "ideology_position": -0.3}]
    assert nominee(listed) == nominee(listed[::-1])


def test_duplicate_candidate_names_are_rejected_across_the_api(client):
    """A duplicate name collapses two candidates into one tally key, discarding
    the other's votes. Four endpoints accepted it silently; vote-steps' Schulze
    branch raised KeyError as a 500. It is a 422 at the boundary now."""
    dup = [{"name": "Alice", "x": -0.5, "y": -0.2}, {"name": "Alice", "x": 0.5, "y": 0.2},
           {"name": "Bob", "x": 0.0, "y": 0.3}]
    for path in ("/api/v2/election/simulate", "/api/v2/election/nota",
                 "/api/v2/election/behavioral-biases", "/api/v2/election/cascade"):
        response = client.post(path, json={"candidates": dup, "num_voters": 60})
        assert response.status_code == 422, (path, response.text)
        assert "Duplicate candidate name" in response.text

    # And the loose shape the simulation endpoints accept: bare name strings.
    loose = client.post("/api/v2/simulations/monte-carlo",
                        json={"candidates": ["Alice", "Alice", "Bob"], "num_runs": 3})
    assert loose.status_code == 422 and "Duplicate candidate name" in loose.text
