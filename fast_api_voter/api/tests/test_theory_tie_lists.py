"""A summary statistic over trials or procedures names every winner tied for the
most wins, not whichever won first.

`Counter.most_common(1)` picks by insertion order, so the answer depended on
which candidate happened to win the first trial. On /assumption-testing that
arbitrary pick fed `winner_changed`, and through it the headline
`robust_result`: the 15-15 split below reported a scenario as fragile because
the coin flip landed on the candidate the baseline had not picked.

`tied_extremes` is deliberately NOT used here — it collapses "all values equal"
to empty, which is right for a per-method score but wrong for a winner
distribution, where two candidates on 15 trials each are both leaders. See
`modal_keys` in api/domain/election/_helpers.py.
"""
from collections import Counter

import pytest

from api.domain.election._helpers import modal_keys
from api.domain.theory.workers import _assumption_testing_worker, _collective_will_worker

#: Two candidates either side of centre: 20 voters split 15-15 across the 30
#: trials often enough that seed 10 does it on `stable_preferences`.
PAIR = [{"name": "Alice", "x": -0.3, "y": 0.0}, {"name": "Bob", "x": 0.3, "y": 0.0}]


def _assumptions(candidates=PAIR, voters=20, seed=10):
    body, status = _assumption_testing_worker({
        "base_simulation": {"candidates": candidates, "num_voters": voters, "seed": seed},
    })
    assert status == 200
    return body


def test_modal_keys_lists_every_key_tied_at_the_top():
    assert modal_keys(Counter({"a": 15, "b": 15})) == ["a", "b"]
    assert modal_keys(Counter({"b": 3, "a": 9})) == ["a"]
    assert modal_keys(Counter({"c": 2, "a": 2, "b": 2})) == ["a", "b", "c"]
    assert modal_keys(Counter()) == []


def test_a_tied_trial_split_is_not_a_changed_winner():
    """15-15 on stable_preferences, and Bob is the baseline. Reporting Alice as
    the relaxed winner made `winner_changed` true and the whole scenario
    fragile."""
    body = _assumptions()
    row = body["relaxed_results"]["stable_preferences"]

    assert row["winner_distribution"] == {"Alice": 0.5, "Bob": 0.5}
    assert row["winner"] == ["Alice", "Bob"]
    assert body["baseline_result"]["winner"] == "Bob"
    assert row["winner_changed"] is False
    assert body["robust_result"] is True


def test_the_confidence_interval_reads_the_leading_count_not_a_name():
    """Tied leaders share one win rate, so the interval is the same either way."""
    row = _assumptions()["relaxed_results"]["stable_preferences"]
    low, high = row["confidence_interval"]
    assert low < 0.5 < high


def test_a_single_leader_is_still_a_one_name_list():
    body = _assumptions(voters=100, seed=3)
    for assumption, row in body["relaxed_results"].items():
        top = max(row["winner_distribution"].values())
        leaders = sorted(c for c, share in row["winner_distribution"].items() if share == top)
        assert row["winner"] == leaders, assumption


@pytest.mark.parametrize("names", [("Alice", "Bob"), ("Zed", "Aaron"), ("bob", "alice")])
def test_the_verdict_does_not_depend_on_what_the_candidates_are_called(names):
    """The property the old code broke: renaming the same two positions must not
    move the robustness verdict.

    Note what this does *not* claim. A tied trial is still settled by name, the
    engine's convention since #616, so renaming does shift the trial counts
    themselves (seed 10's 15-15 becomes 16-14 under some namings). What must hold
    is that the verdict no longer rides on an arbitrary pick, and that each row's
    `winner` is exactly the argmax set of its own distribution.
    """
    candidates = [{"name": n, "x": x, "y": 0.0} for n, x in zip(names, (-0.3, 0.3))]
    body = _assumptions(candidates=candidates)

    assert body["robust_result"] is True
    for assumption, row in body["relaxed_results"].items():
        top = max(row["winner_distribution"].values())
        leaders = sorted(c for c, share in row["winner_distribution"].items() if share == top)
        assert row["winner"] == leaders, (names, assumption)
        assert row["winner_changed"] is (body["baseline_result"]["winner"] not in leaders)


def test_collective_will_lists_every_procedure_winner_tied_at_the_top():
    """4 procedures, 2 agendas: Alice and Bob win the same number. The report used
    to name whichever came first in the method list."""
    body, status = _collective_will_worker({
        "num_methods": 4, "num_agendas": 2, "seed": 32, "num_voters": 50,
    })
    assert status == 200
    assert body["most_frequent_winner"] == ["Alice", "Bob"]
    assert body["most_frequent_pct"] == 0.5


def test_collective_will_names_the_one_winner_when_it_leads_alone():
    body, status = _collective_will_worker({"num_methods": 6, "num_agendas": 3, "seed": 0})
    assert status == 200
    assert body["most_frequent_winner"] == ["Bob"]
    assert "'Bob'" in body["philosophical_conclusion"] or body["unique_winner_count"] <= 2
