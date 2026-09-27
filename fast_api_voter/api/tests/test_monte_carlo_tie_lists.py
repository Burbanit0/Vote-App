"""The Monte-Carlo "most common winner" lists every candidate tied for the most
runs won.

It used to be `max(counts, key=counts.get)`, which returns whichever candidate
was counted first — and the runs are collected with `as_completed` over a thread
pool seeded from nothing, so for a tie two identical requests could report
different winners. `num_runs` and the socket stream's `num_iterations` both allow
values small enough for a tie to be the normal case, not an edge one.
"""
from api.domain.election._helpers import modal_keys
from api.domain.simulations.advanced import _monte_carlo_worker
from api.sockets import (
    _monte_carlo_accumulate_run,
    _monte_carlo_checkpoint_payload,
    _monte_carlo_final_payload,
    _monte_carlo_new_stats,
)


def _stats_from_runs(winners_per_run: list[str]) -> dict:
    """Accumulate real iteration payloads through the socket's own accumulator,
    rather than hand-building its state."""
    stats = _monte_carlo_new_stats()
    for winner in winners_per_run:
        _monte_carlo_accumulate_run(
            {"condorcet_winner": winner,
             "methods": {"plurality": {"winner": winner, "bayesian_regret": 0.1,
                                       "majority_satisfaction": 0.5,
                                       "condorcet_consistent": True}}},
            stats,
        )
    return stats


def test_a_tie_is_reported_the_same_whichever_run_finished_first():
    """The only difference between these two tallies is insertion order, which is
    thread-completion order in the worker."""
    alice_first = {"plurality": {"Alice": 1, "Bob": 1}}
    bob_first = {"plurality": {"Bob": 1, "Alice": 1}}

    assert modal_keys(alice_first["plurality"]) == modal_keys(bob_first["plurality"]) \
        == ["Alice", "Bob"]


def test_the_worker_lists_the_leaders_of_its_own_distribution():
    body, status = _monte_carlo_worker({
        "candidates": [{"name": "Alice", "x": -0.4, "y": 0.0},
                       {"name": "Bob", "x": 0.4, "y": 0.0}],
        "num_voters": 50, "num_runs": 4,
    })
    assert status == 200
    for method, stats in body["methods"].items():
        dist = stats["winner_distribution"]
        top = max(dist.values(), default=0)
        assert stats["most_common_winner"] == sorted(c for c, v in dist.items() if v == top), method


def test_a_run_with_no_winner_at_all_crowns_nobody():
    """An empty tally is the one case that still yields an empty list."""
    assert modal_keys({}) == []


def test_the_socket_payloads_list_tied_leaders():
    """Both the checkpoint and the final payload; the final one is what the
    client stores when a stream ends."""
    # Bob wins three iterations, Alice three, Carol one -- Bob counted first.
    stats = _stats_from_runs(["Bob"] * 3 + ["Alice"] * 3 + ["Carol"])

    partial = _monte_carlo_checkpoint_payload(stats, completed_runs=7, num_iterations=7)
    final = _monte_carlo_final_payload(stats, num_iterations=7, num_voters=50)

    assert partial["partial_results"]["plurality"]["most_common_winner"] == ["Alice", "Bob"]
    assert final["final_results"]["plurality"]["most_common_winner"] == ["Alice", "Bob"]
