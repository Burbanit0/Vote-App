"""Every endpoint that takes a method name rejects one it does not implement.

Each of these answered 200 for any string: /hotelling, /demographic-turnout and
/primary fell through to plurality and reported its result under the requested
name; /party-dynamics fell to its sincere model; /sortition, /compulsory-voting
and /deliberation never read the field at all. Some real names were mislabelled
too -- /hotelling's "irv" was plurality's first-choice share, /party-dynamics'
"irv" tactical plurality and its "borda" the sincere model -- so those names
are no longer accepted rather than answered wrongly.
"""
import pytest

from api.domain.election import workers, workers_advanced, workers_dynamics

CANDS = [{"name": "Alice", "x": -0.5, "y": -0.2}, {"name": "Bob", "x": 0.5, "y": 0.2},
         {"name": "Carol", "x": 0.0, "y": 0.3}]
PARTIES = [
    {"name": side, "ideology_center": c, "primary_voters_pct": 0.3,
     "primary_candidates": [{"name": f"{side[0]}1", "ideology_position": c * 1.2},
                            {"name": f"{side[0]}2", "ideology_position": c * 0.6}]}
    for side, c in (("Left", -0.5), ("Right", 0.5))
]

CASES = [
    ("/api/v2/election/hotelling", {"candidates": CANDS}, "method", "irv"),
    ("/api/v2/election/demographic-turnout", {"candidates": CANDS}, "method", "kemeny_young"),
    ("/api/v2/election/primary", {"parties": PARTIES}, "primary_method", "borda"),
    ("/api/v2/election/primary", {"parties": PARTIES}, "general_method", "schulze"),
    ("/api/v2/election/party-dynamics", {}, "method", "irv"),
    ("/api/v2/election/party-dynamics", {}, "method", "borda"),
    ("/api/v2/election/sortition", {"candidates": CANDS}, "method", "borda"),
    ("/api/v2/election/compulsory-voting", {"candidates": CANDS}, "method", "irv"),
    ("/api/v2/election/deliberation", {"candidates": CANDS}, "method", "borda"),
]


@pytest.mark.parametrize("url,base,field,name", CASES)
def test_the_schema_rejects_a_method_the_endpoint_does_not_compute(client, url, base, field, name):
    assert client.post(url, json={**base, field: name}).status_code == 422
    assert client.post(url, json={**base, field: "plurality"}).status_code == 200


@pytest.mark.parametrize("worker,payload", [
    (workers_dynamics._hotelling_worker, {"candidates": CANDS, "method": "irv"}),
    (workers_advanced._demographic_turnout_worker, {"candidates": CANDS, "method": "kemeny_young"}),
    (workers._primary_worker, {"parties": PARTIES, "general_method": "not_a_method"}),
    (workers_advanced._party_dynamics_worker, {"method": "borda"}),
])
def test_a_direct_call_with_an_unknown_method_is_a_400(worker, payload):
    body, status = worker(payload)
    assert status == 400 and "unknown voting method" in body["error"]


def test_demographic_turnout_reports_the_rule_it_was_asked_for():
    """With five candidates the requested rule and plurality can disagree, and the
    response then contradicted itself: `winner` came from plurality while
    `winners_by_method[method]` came from the rule."""
    cands = CANDS + [{"name": "Dave", "x": -0.2, "y": 0.6}, {"name": "Eve", "x": 0.7, "y": -0.5}]
    for method in ("borda", "irv", "schulze"):
        for seed in range(6):
            body, _ = workers_advanced._demographic_turnout_worker(
                {"candidates": cands, "method": method, "seed": seed, "num_voters": 300}
            )
            biased = body["biased_result"]
            assert biased["winner"] == biased["winners_by_method"][method], (method, seed)
