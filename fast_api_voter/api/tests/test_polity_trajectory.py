"""Trajectory metrics, archetypes, the plausibility band and the divergence test (plan-scenarios-v1, step 1).
See api/domain/polity/trajectory.py."""
from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from api.domain.polity.indexer import Term
from api.domain.polity.trajectory import (
    ARCHETYPE_RULES,
    FEATURES,
    archetype,
    divergence_by_year,
    divergence_verdict,
    diversity,
    election_points,
    feature_cube,
    legislative_points,
    office_summary,
    pairwise_distances,
    pedersen_volatility,
    plausibility,
    polarization,
    polarization_by_year,
    presidential_margins,
    trajectory_summary,
)


def _event(tick: int, event_type: str, payload: dict[str, Any], citizen_id: int | None = None) -> dict[str, Any]:
    return {"tick": tick, "event_type": event_type, "citizen_id": citizen_id, "payload": payload}


def _term(holder: int, start: int, end: int, ended_by: str = "election") -> Term:
    return Term(holder_id=holder, start_tick=start, end_tick=end, lame_duck=False, mandate_strength=None, ended_by=ended_by)


def _legislative(tick: int, seats: dict[int, int], votes: dict[int, float]) -> dict[str, Any]:
    return _event(tick, "legislative_result", {"seats": seats, "votes": votes, "blank_count": 0})


# ── per run ───────────────────────────────────────────────────────────────


def test_pedersen_volatility_is_half_the_absolute_share_change_over_the_union_of_parties() -> None:
    # Party 2 vanishes (50% -> 0), party 3 appears (0 -> 50%): two full swings of 0.5, halved.
    assert pedersen_volatility({1: 50, 2: 50}, {1: 50, 3: 50}) == pytest.approx(0.5)
    assert pedersen_volatility({1: 50, 2: 50}, {1: 50, 2: 50}) == 0.0
    assert pedersen_volatility({1: 0}, {1: 50}) is None


def test_legislative_points_read_enp_majority_seating_and_volatility() -> None:
    events = [
        _legislative(8, {1: 60, 2: 40}, {1: 60.0, 2: 40.0}),
        _legislative(24, {}, {1: 4.9, 2: 4.8}),  # nobody cleared the threshold
        _legislative(40, {1: 50, 2: 50}, {1: 50.0, 2: 50.0}),
    ]
    first, empty, last = legislative_points(events)
    assert first == {"tick": 8, "enp_seats": pytest.approx(1 / (0.6**2 + 0.4**2)), "majority": True, "seated": True, "volatility": None}
    # 60/40 of the vote became 4.9/4.8 of 9.7: two swings of 0.0948, halved.
    assert empty == {"tick": 24, "enp_seats": None, "majority": False, "seated": False, "volatility": pytest.approx(0.0948, abs=1e-4)}
    assert last["enp_seats"] == pytest.approx(2.0) and last["majority"] is False
    assert last["volatility"] == pytest.approx(0.00515, abs=1e-4)  # 0.505/0.495 of the vote became 50/50


def test_election_points_keep_votes_held_and_drop_elections_nobody_stood_in() -> None:
    events = [
        _event(0, "elected", {"office": "president", "abstained": 25}, citizen_id=7),
        _event(16, "election_no_winner", {"reason": "no_candidates"}),
        _event(32, "election_no_winner", {"reason": "blank_won", "abstained": 0}),
    ]
    assert election_points(events, population=100, last_tick=32) == [
        {"tick": 0, "winner": 7, "turnout": 0.75}, {"tick": 32, "winner": None, "turnout": 1.0},
    ]


def test_presidential_margins_from_the_poll_with_two_one_and_no_candidates() -> None:
    events = [
        _event(0, "vote_intention_poll", {"shares": [{"citizen_id": 1, "share": 0.2}, {"citizen_id": 2, "share": 0.5}], "blank": 0.1, "abstain": 0.2}),
        _event(16, "vote_intention_poll", {"shares": [{"citizen_id": 1, "share": 0.4}], "blank": 0.3, "abstain": 0.3}),
        _event(32, "vote_intention_poll", {"shares": [], "blank": 0.5, "abstain": 0.5}),
    ]
    assert presidential_margins(events) == [
        {"tick": 0, "candidates": 2, "leader_share": 0.5, "margin": pytest.approx(0.3)},
        {"tick": 16, "candidates": 1, "leader_share": 0.4, "margin": 0.4},
        {"tick": 32, "candidates": 0, "leader_share": None, "margin": None},
    ]


def test_polarization_tells_two_camps_from_one_cloud_and_is_absent_when_undefined() -> None:
    rng = np.random.default_rng(0)
    one_cloud = rng.normal(0.5, 0.1, size=(200, 3))
    two_camps = np.vstack([rng.normal(0.2, 0.02, size=(100, 3)), rng.normal(0.8, 0.02, size=(100, 3))])
    cloud, camps = polarization(one_cloud), polarization(two_camps)
    assert cloud["bimodality"] is not None and camps["bimodality"] is not None
    assert camps["bimodality"] > 5 / 9 > cloud["bimodality"]
    assert camps["dispersion"] is not None and cloud["dispersion"] is not None and camps["dispersion"] > cloud["dispersion"]
    assert polarization(np.zeros((3, 2))) == {"dispersion": None, "bimodality": None}
    assert polarization(np.ones((5, 2))) == {"dispersion": 0.0, "bimodality": None}


def test_polarization_by_year_measures_how_far_the_mean_moved_since_the_first_census() -> None:
    year0 = [{"year": 0, "issue_positions": [x, x]} for x in (0.1, 0.2, 0.3, 0.4)]
    year1 = [{"year": 1, "issue_positions": [x + 0.3, x + 0.3]} for x in (0.1, 0.2, 0.3, 0.4)]
    first, second = polarization_by_year([*year1, *year0])  # order in the file does not matter
    assert (first["year"], first["mean_shift"]) == (0, 0.0)
    assert second["year"] == 1 and second["mean_shift"] == pytest.approx(0.3 * 2**0.5)
    assert second["dispersion"] == pytest.approx(first["dispersion"])


def test_office_summary_counts_alternations_reelections_recalls_and_the_longest_hold() -> None:
    terms = [
        _term(1, 0, 16), _term(1, 16, 32), _term(1, 32, 40, "legitimacy_floor"),  # re-elected twice, then recalled
        _term(2, 40, 48, "confidence_vote"), _term(1, 48, 64), _term(3, 64, 80, "run_end"),
    ]
    assert office_summary(terms) == {
        "terms": 6, "distinct_holders": 3, "alternations": 3, "reelections": 2, "recalls": 2,
        "longest_hold": 3, "mean_term_ticks": pytest.approx(80 / 6),
    }
    assert office_summary([]) == {
        "terms": 0, "distinct_holders": 0, "alternations": 0, "reelections": 0, "recalls": 0,
        "longest_hold": 0, "mean_term_ticks": None,
    }


def _summary(**overrides: Any) -> dict[str, Any]:
    """A run that satisfies no rule but the last: stasis."""
    base: dict[str, Any] = {
        "office_occupancy": 1.0,
        "office": {"longest_hold": 1, "recalls": 0, "alternations": 1},
        "legislative": [
            {"tick": 8, "enp_seats": 3.0, "majority": False, "seated": True, "volatility": None},
            {"tick": 24, "enp_seats": 3.5, "majority": False, "seated": True, "volatility": 0.1},
        ],
        "elections": [{"tick": 0, "winner": 1, "turnout": 0.7}],
        "polarization": [{"year": 0, "mean_shift": 0.0}, {"year": 1, "mean_shift": 0.02}],
        "refused_to_leave": False,
    }
    return {**base, **overrides}


def _with_legislative(**fields: Any) -> list[dict[str, Any]]:
    return [{**row, **fields} for row in _summary()["legislative"]]


@pytest.mark.parametrize(
    ("label", "overrides"),
    [
        ("stasis", {}),
        ("collapse", {"office_occupancy": 0.4}),
        ("collapse", {"legislative": _with_legislative(seated=False)}),
        ("entrenchment", {"office": {"longest_hold": 3, "recalls": 0, "alternations": 0}}),
        ("entrenchment", {"refused_to_leave": True}),
        ("recall_cycle", {"office": {"longest_hold": 1, "recalls": 2, "alternations": 0}}),
        ("fragmentation", {"legislative": [
            {"tick": 8, "enp_seats": 6.0, "majority": False, "seated": True, "volatility": None},
            {"tick": 24, "enp_seats": 9.0, "majority": False, "seated": True, "volatility": 0.1},
        ]}),
        ("dominant_party", {"legislative": _with_legislative(majority=True)}),
        ("realignment", {"polarization": [{"year": 0, "mean_shift": 0.0}, {"year": 1, "mean_shift": 0.12}]}),
        ("churn", {"legislative": _with_legislative(volatility=0.45)}),
        ("alternation", {"office": {"longest_hold": 1, "recalls": 0, "alternations": 2}}),
    ],
)
def test_archetype_rules_in_order_first_match_wins(label: str, overrides: dict[str, Any]) -> None:
    assert archetype(_summary(**overrides)) == label
    assert label in dict(ARCHETYPE_RULES)


def test_a_collapse_outranks_every_later_rule_and_a_stable_majority_is_not_fragmentation() -> None:
    assert archetype(_summary(office_occupancy=0.1, refused_to_leave=True)) == "collapse"
    one_election = _summary(legislative=[{"tick": 8, "enp_seats": 9.0, "majority": True, "seated": True, "volatility": None}])
    assert archetype(one_election) == "stasis"  # fragmentation and dominance both need two elections


def test_plausibility_names_the_band_checks_a_run_fails_and_skips_what_it_cannot_read() -> None:
    assert plausibility(_summary()) == []
    assert plausibility(_summary(elections=[{"tick": 0, "winner": 1, "turnout": 0.3}])) == ["turnout"]
    assert plausibility(_summary(legislative=_with_legislative(enp_seats=9.0, volatility=0.5))) == ["enp_seats", "volatility"]
    assert plausibility(_summary(elections=[], legislative=[])) == []


def test_trajectory_summary_builds_the_yearly_series_and_notes_a_successful_refusal_to_leave() -> None:
    events = [
        _event(0, "elected", {"office": "president", "abstained": 2}, citizen_id=1),
        _event(0, "legitimacy_updated", {"office": "president", "legitimacy": 0.8, "mandate_strength": 0.7}, citizen_id=1),
        _event(1, "legitimacy_updated", {"office": "president", "legitimacy": 0.6, "mandate_strength": 0.7}, citizen_id=1),
        _event(1, "legitimacy_updated", {"office": "chamber", "legitimacy": 0.1}, citizen_id=9),  # not the president's
        _event(1, "pressure_action", {"act": 3}, citizen_id=4),
        _event(1, "pressure_action", {"act": 0}, citizen_id=5),  # doing nothing is not pressure
        _event(5, "pressure_action", {"act": 1}, citizen_id=4),
        _legislative(2, {1: 6, 2: 4}, {1: 60.0, 2: 40.0}),
        _legislative(6, {1: 5, 2: 5}, {1: 50.0, 2: 50.0}),
        _event(7, "extra_legal_act", {"act": "refuse_to_leave", "approval": 0.6, "probability": 0.2, "success": 1}, citizen_id=1),
    ]
    snapshots = [{"year": y, "issue_positions": [x, 1 - x]} for y in (0, 1) for x in (0.1, 0.4, 0.6, 0.9)]
    summary = trajectory_summary(
        events, snapshots, terms=[_term(1, 0, 8, "run_end")], population=10, ticks_per_year=4, last_tick=7, office_occupancy=1.0,
    )
    assert summary["refused_to_leave"] is True and summary["archetype"] == "entrenchment"
    assert summary["plausibility_failed"] == []  # turnout 0.8, ENP 2.0, volatility 0.1
    yearly = summary["yearly"]
    assert set(yearly) == set(FEATURES) and all(len(series) == 2 for series in yearly.values())
    assert yearly["legitimacy"] == [pytest.approx(0.7), None]
    assert yearly["enp_seats"] == [pytest.approx(1 / (0.6**2 + 0.4**2)), pytest.approx(2.0)]
    # An election that seats nobody resets the carried ENP instead of leaving the previous one standing.
    reset = trajectory_summary(
        [*events, _legislative(7, {}, {1: 4.0, 2: 4.0})], snapshots, terms=[_term(1, 0, 8, "run_end")],
        population=10, ticks_per_year=4, last_tick=7, office_occupancy=1.0,
    )
    assert reset["yearly"]["enp_seats"] == [pytest.approx(1 / (0.6**2 + 0.4**2)), None] and reset["archetype"] == "collapse"
    assert yearly["turnout"] == [0.8, 0.8]
    assert yearly["volatility"] == [None, pytest.approx(0.1)]
    assert yearly["pressure"] == [pytest.approx(1 / 40), pytest.approx(1 / 40)]
    assert yearly["mean_shift"] == [0.0, 0.0] and yearly["dispersion"][0] == pytest.approx(yearly["dispersion"][1])


def test_trajectory_summary_without_a_census_has_no_polarization_rather_than_a_guess() -> None:
    summary = trajectory_summary([], [], terms=[], population=10, ticks_per_year=4, last_tick=3, office_occupancy=0.0)
    assert summary["polarization"] == [] and summary["archetype"] == "collapse"
    assert summary["yearly"]["dispersion"] == [None] and summary["yearly"]["pressure"] == [0.0]


# ── across runs ───────────────────────────────────────────────────────────


def _series(*values: float | None) -> dict[str, list[float | None]]:
    return {feature: list(values) for feature in FEATURES}


def test_feature_cube_standardises_each_feature_and_sets_an_absent_value_at_the_mean() -> None:
    runs, cube = feature_cube({"b": _series(1.0, 3.0), "a": _series(3.0, None, 9.0)}, features=("legitimacy",))
    assert runs == ["a", "b"] and cube.shape == (2, 2, 1)  # cut to the shortest run: a's 9.0 is dropped
    present = np.array([cube[0, 0, 0], cube[1, 0, 0], cube[1, 1, 0]])  # the values 3, 1, 3, standardised
    assert present.mean() == pytest.approx(0.0) and present.std() == pytest.approx(1.0)
    assert cube[1, 0, 0] < 0 < cube[0, 0, 0]  # 1 sits below the mean, 3 above
    assert cube[0, 1, 0] == 0.0  # the absent value sits at the mean


def test_feature_cube_treats_a_run_missing_a_feature_as_having_no_years() -> None:
    partial = {"a": _series(1.0, 2.0), "b": {"legitimacy": [1.0, 2.0]}}  # b lacks the other features
    runs, cube = feature_cube(partial)
    assert runs == ["a", "b"] and cube.shape == (2, 0, len(FEATURES))
    assert pairwise_distances(partial) == {} and divergence_by_year(partial) == []


def test_feature_cube_with_nothing_to_read_is_all_zeros() -> None:
    runs, cube = feature_cube({"a": _series(None), "b": _series(None)}, features=("turnout",))
    assert runs == ["a", "b"] and cube.tolist() == [[[0.0]], [[0.0]]]


def test_divergence_and_distances_grow_with_runs_that_drift_apart() -> None:
    apart = {"a": _series(0.0, 0.0, 0.0), "b": _series(0.0, 1.0, 2.0)}
    by_year = divergence_by_year(apart)
    assert len(by_year) == 3 and by_year[0] == 0.0 and by_year[0] < by_year[1] < by_year[2]
    assert set(pairwise_distances(apart)) == {("a", "b")} and pairwise_distances(apart)["a", "b"] == pytest.approx(sum(by_year) / 3)
    assert divergence_by_year({"a": _series(0.0)}) == []
    assert pairwise_distances({"a": _series(), "b": _series()}) == {}


def test_diversity_reports_counts_entropy_and_the_largest_share() -> None:
    ensemble = diversity({"a": "stasis", "b": "churn", "c": "stasis", "d": "collapse"}, {("a", "b"): 2.0, ("c", "d"): 4.0})
    assert ensemble["runs"] == 4 and ensemble["archetypes"] == {"churn": 1, "collapse": 1, "stasis": 2}
    assert ensemble["archetype_entropy_bits"] == pytest.approx(1.5) and ensemble["largest_archetype_share"] == 0.5
    assert ensemble["mean_pairwise_distance"] == 3.0
    assert diversity({}, {}) == {"runs": 0, "archetypes": {}, "archetype_entropy_bits": 0.0, "largest_archetype_share": None, "mean_pairwise_distance": None}


def test_divergence_verdict_judges_the_four_criteria_and_abstains_without_enough_to_read() -> None:
    varied = diversity({"a": "stasis", "b": "churn", "c": "collapse", "d": "stasis"}, {})
    assert divergence_verdict([1.0, 1.0, 2.0, 3.0, 4.0, 5.0], varied, 0.8) == {
        "grows": True, "varied": True, "no_dominant_story": True, "plausible": True,
    }
    one_story = diversity({"a": "stasis", "b": "stasis", "c": "churn"}, {})
    assert divergence_verdict([5.0, 4.0, 3.0], one_story, 0.5) == {
        "grows": False, "varied": False, "no_dominant_story": False, "plausible": False,
    }
    assert divergence_verdict([1.0, 2.0], diversity({}, {}), None) == {
        "grows": None, "varied": None, "no_dominant_story": None, "plausible": None,
    }


# ── the digest ────────────────────────────────────────────────────────────


def test_build_digest_carries_the_trajectory_with_polarization_only_when_a_census_exists(tmp_path) -> None:
    import json

    from api.domain.polity.config import load_config
    from api.domain.polity.run_digest import build_digest

    events = [
        _event(0, "elected", {"office": "president", "abstained": 0}, citizen_id=5),
        _legislative(2, {1: 6, 2: 4}, {1: 60.0, 2: 40.0}),
    ]
    journal = tmp_path / "events.jsonl"
    journal.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")

    without_census = build_digest(journal, load_config(), run_id="r", outcome="completed", resume=False)["trajectory"]
    assert without_census["polarization"] == [] and without_census["office"]["terms"] == 1
    assert without_census["legislative"][0]["enp_seats"] == pytest.approx(1 / (0.6**2 + 0.4**2))
    assert without_census["archetype"] == "stasis" and list(without_census["yearly"]) == list(FEATURES)

    census = [{"citizen_id": i, "year": 0, "tick": 0, "issue_positions": [x, 1 - x]} for i, x in enumerate((0.1, 0.4, 0.6, 0.9))]
    journal.with_name("snapshots.jsonl").write_text("".join(json.dumps(row) + "\n" for row in census), encoding="utf-8")
    with_census = build_digest(journal, load_config(), run_id="r", outcome="completed", resume=False)["trajectory"]
    assert [row["year"] for row in with_census["polarization"]] == [0] and with_census["yearly"]["mean_shift"][0] == 0.0
    assert with_census["snapshot_lines_skipped"] == 0

    with journal.with_name("snapshots.jsonl").open("a", encoding="utf-8") as handle:
        handle.write('{"citizen_id": 4, "year": 0, "tick": 0, "issue_pos')  # a torn last line
    torn = build_digest(journal, load_config(), run_id="r", outcome="crashed", resume=False)["trajectory"]
    assert torn["snapshot_lines_skipped"] == 1 and torn["polarization"][0]["dispersion"] == with_census["polarization"][0]["dispersion"]
