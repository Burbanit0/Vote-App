"""/choice-overload's modelling: each test pins one way the panel's answer was
not the answer its own model implies."""
import random

from api.domain.election import workers_behavioral as wb
from api.domain.election.workers_behavioral import _choice_overload_worker, _co_winner

METHODS = ["plurality", "approval", "borda", "majority_judgment", "irv", "schulze"]


def test_majority_judgment_reads_the_heuristic_votes():
    """Every voter here runs on notoriety and picks the first-listed candidate.
    Every rule follows -- and MJ used to be the exception: it graded each
    voter's sincere utilities, so the heuristic never reached it and it came
    out "most robust" by construction."""
    body, _ = _choice_overload_worker({
        "num_voters": 120, "seed": 3, "overload_threshold": 2, "candidate_counts": [3, 5, 7],
        "heuristic_weights": {"notoriety": 1.0, "primacy": 0.0, "partisan": 0.0},
        "methods": METHODS,
    })
    for row in body["results_by_n"]:
        assert row["heuristic_voters"] == 1.0
        assert row["winner_by_method"]["majority_judgment"] == "A"


def test_an_approval_tie_is_broken_by_name_not_voter_order():
    voters = [{"id": 1}, {"id": 2}]
    voted = {1: "B", 2: "A"}                      # B counted first
    is_h = {1: True, 2: True}                     # each approves only its pick
    assert _co_winner("approval", voters, [["B", "A"], ["A", "B"]], {}, voted, is_h,
                      ["A", "B"]) == "A"


def test_electing_nobody_is_not_electing_the_condorcet_winner():
    """At 5 candidates IRV elects nobody (an exact tie) and there is no Condorcet
    winner. `None == None` used to report that as IRV electing the Condorcet
    winner, and as IRV agreeing with its own sincere result."""
    body, _ = _choice_overload_worker({
        "num_voters": 50, "seed": 0, "overload_threshold": 2, "methods": ["plurality", "irv"],
    })
    row = next(r for r in body["results_by_n"] if r["num_candidates"] == 5)
    assert row["winner_by_method"]["irv"] is None and row["condorcet_winner"] is None
    assert row["methods_elect_condorcet"]["irv"] is False


def test_the_note_quotes_what_happened_not_the_configured_weight():
    none_over, _ = _choice_overload_worker({
        "num_voters": 60, "seed": 1, "overload_threshold": 12, "candidate_counts": [3, 5],
    })
    assert "personne ne vote par heuristique" in none_over["pedagogical_note"]
    assert all(r["heuristic_voters"] == 0 for r in none_over["results_by_n"])

    over, _ = _choice_overload_worker({
        "num_voters": 200, "seed": 1, "overload_threshold": 2, "candidate_counts": [5],
    })
    measured = round(over["results_by_n"][0]["heuristic_voters"] * 100)
    assert f"{measured}% des électeurs ont voté par heuristique" in over["pedagogical_note"]


def test_num_voters_above_300_is_honoured():
    """The schema allows 1000; the worker used to cap at 300 without saying so."""
    def curve(n):
        body, _ = _choice_overload_worker({"num_voters": n, "seed": 4, "candidate_counts": [7]})
        return body["regret_curve"]
    assert curve(300) != curve(600)


def test_the_electorate_ignores_the_process_wide_rng(monkeypatch):
    """The worker used to `random.seed(seed)` the shared generator and build
    voters from it, so another request drawing from it mid-build changed this
    one's electorate. Interleave global draws and the answer must not move."""
    payload = {"num_voters": 80, "seed": 7, "candidate_counts": [3, 7], "methods": METHODS}
    quiet, _ = _choice_overload_worker(payload)

    real = wb.create_voter
    def noisy(*args, **kwargs):
        random.random()                            # a concurrent request, in effect
        return real(*args, **kwargs)
    monkeypatch.setattr(wb, "create_voter", noisy)
    assert _choice_overload_worker(payload)[0] == quiet


def _robust(methods, seed=3):
    return _choice_overload_worker({
        "num_voters": 80, "seed": seed, "overload_threshold": 3,
        "candidate_counts": [3, 5, 7], "methods": methods,
    })[0]


def test_a_tie_for_most_robust_names_every_tied_method_in_any_request_order():
    """Borda, IRV and Schulze match their sincere winner equally often here.
    `max(match_rates, ...)` used to crown whichever the request listed first."""
    body = _robust(METHODS)
    assert body["most_robust_method"] == ["borda", "irv", "schulze"]
    assert body["least_robust_method"] == ["majority_judgment"]
    assert "'borda', 'irv' et 'schulze' sont les méthodes les plus robustes" in body["pedagogical_note"]
    assert sorted(_robust(METHODS[::-1])["most_robust_method"]) == body["most_robust_method"]

    single = _robust(METHODS, seed=0)
    assert single["most_robust_method"] == ["borda"]
    assert "'borda' est la méthode la plus robuste" in single["pedagogical_note"]


def test_the_note_crowns_nobody_when_every_method_ties():
    body, _ = _choice_overload_worker({
        "num_voters": 40, "seed": 0, "overload_threshold": 2,
        "candidate_counts": [3], "methods": ["borda", "schulze"],
    })
    assert body["most_robust_method"] == [] == body["least_robust_method"]
    assert "aucune n'est plus robuste" in body["pedagogical_note"]
