"""Theory and tech endpoints: each rejects a method it does not compute, and
computes the ones it names with the rule of that name."""
import pytest

from api.domain.theory.workers import (
    _arrow_worker, _manipulation_analysis_worker, _majority_tyranny_worker,
)

CANDS = [{"name": "Alice", "x": -0.5, "y": -0.2}, {"name": "Bob", "x": 0.5, "y": 0.2},
         {"name": "Carol", "x": 0.0, "y": 0.3}]


@pytest.mark.parametrize("url,payload", [
    ("/api/v2/theory/arrow", {"method": "copeland"}),
    ("/api/v2/theory/iia-rate", {"method": "majority_judgment"}),
    ("/api/v2/theory/manipulation-analysis", {"candidates": CANDS, "method": "approval"}),
    ("/api/v2/theory/majority-tyranny", {"decision_rules": ["simple_majority", "kemeny_young"]}),
    ("/api/v2/theory/identity-voting", {"candidates": CANDS, "method": "borda"}),
    ("/api/v2/tech/polis", {"candidates": CANDS, "method_to_compare": "irv"}),
])
def test_the_schema_rejects_a_name_the_endpoint_does_not_compute(client, url, payload):
    assert client.post(url, json=payload).status_code == 422


@pytest.mark.parametrize("worker,payload", [
    (_arrow_worker, {"method": "copeland"}),
    (_manipulation_analysis_worker, {"candidates": CANDS, "method": "approval"}),
    (_majority_tyranny_worker, {"decision_rules": ["simple_majority", "not_a_rule"]}),
])
def test_a_direct_call_with_an_unknown_name_is_a_400(worker, payload):
    body, status = worker(payload)
    assert status == 400 and "unknown voting method" in body["error"]


SIX = [{"name": "Alice", "x": 0.28, "y": 0.46}, {"name": "Bob", "x": 0.03, "y": 0.02},
       {"name": "Carol", "x": -0.17, "y": 0.79}, {"name": "Dave", "x": -0.34, "y": -0.56},
       {"name": "Eve", "x": -0.38, "y": -0.38}, {"name": "Frank", "x": -0.28, "y": -0.37}]


def test_manipulation_analysis_runs_two_round_as_two_round():
    """It used to answer "two_round" with IRV. On this electorate both rules
    decide, and differently."""
    def winner(method):
        return _manipulation_analysis_worker(
            {"candidates": SIX, "num_voters": 60, "seed": 19, "method": method}
        )[0]["sincere_winner"]
    assert (winner("irv"), winner("two_round")) == ("Frank", "Dave")


def test_a_tied_sincere_result_has_nothing_to_manipulate():
    """IRV ties on this electorate. `or cand_names[0]` used to elect Alice, the
    first-listed candidate, and any ballot that broke the tie then counted as a
    successful manipulation."""
    cands = [{"name": "Alice", "x": 0.68, "y": 0.72}, {"name": "Bob", "x": 0.63, "y": -0.67},
             {"name": "Carol", "x": 0.15, "y": -0.12}, {"name": "Dave", "x": 0.05, "y": -0.59},
             {"name": "Eve", "x": -0.49, "y": -0.09}]
    body, status = _manipulation_analysis_worker(
        {"candidates": cands, "num_voters": 40, "seed": 23, "method": "irv"}
    )
    assert status == 200
    assert body["sincere_winner"] is None
    assert body["manipulation_count"] == 0 and body["manipulable"] is False
