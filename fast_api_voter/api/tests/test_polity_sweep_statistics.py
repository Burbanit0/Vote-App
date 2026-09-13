"""Sweep statistics and pre-registered red flags (S0.7).
See api/domain/polity/sweep_statistics.py."""
from __future__ import annotations

import pytest

from api.domain.polity.sweep_statistics import (
    SweepRun,
    clopper_pearson,
    first_completed_runs,
    mean_bca_interval,
    prediction_interval,
    provenance_differences,
    red_flags,
    sweep_run_plan,
)

# The 8-year population-100 sweep's office_occupancy, seeds 1-10 (33 presided ticks each).
P100_OCCUPANCY = [32 / 33, 32 / 33, 32 / 33, 30 / 33, 29 / 33, 27 / 33, 32 / 33, 30 / 33, 32 / 33, 31 / 33]


def test_the_intervals_reproduce_the_p100_correction() -> None:
    low, high = prediction_interval(P100_OCCUPANCY) or (0.0, 0.0)
    assert (round(low, 2), round(high, 2)) == (0.81, 1.05)
    cp_low, cp_high = clopper_pearson(2, 10) or (0.0, 0.0)
    assert (round(cp_low, 3), round(cp_high, 3)) == (0.025, 0.556)
    bca_low, bca_high = mean_bca_interval(P100_OCCUPANCY) or (0.0, 0.0)
    assert bca_low == pytest.approx(0.888, abs=0.002)
    assert bca_high == pytest.approx(0.955, abs=0.002)


def test_intervals_are_absent_rather_than_invented_on_too_little_data() -> None:
    assert mean_bca_interval([0.9, 0.95]) is None
    assert mean_bca_interval([0.9, 0.9, 0.9]) is None  # the bootstrap distribution is a single point
    assert prediction_interval([0.9]) is None
    assert clopper_pearson(0, 0) is None
    low, high = clopper_pearson(0, 200) or (1.0, 1.0)
    assert low == 0.0 and high == pytest.approx(0.0183, abs=0.0001)


def test_a_seed_listed_twice_is_planned_as_a_repeat() -> None:
    assert sweep_run_plan([1, 2, 42, 1]) == [(1, 1), (2, 1), (42, 1), (1, 2)]


def _run(seed: int, repeat: int = 1, *, occupancy: float | None = 0.93, outcome: str = "completed",
         decisions: dict[str, int] | None = None, fallbacks: dict[str, int] | None = None) -> SweepRun:
    return SweepRun(
        seed=seed, repeat=repeat, run_id=f"s{seed}r{repeat}", outcome=outcome, office_occupancy=occupancy,
        decisions_by_type=decisions if decisions is not None else {"vote_cast": 100},
        fallback_by_type=fallbacks or {},
    )


def test_across_seed_statistics_use_each_seeds_first_completed_run() -> None:
    runs = [_run(1, 1, outcome="crashed"), _run(1, 2, occupancy=0.8), _run(1, 3, occupancy=0.9), _run(2)]
    assert [(r.seed, r.repeat) for r in first_completed_runs(runs)] == [(1, 2), (2, 1)]


def _statuses(runs: list[SweepRun]) -> list[str]:
    return [flag.status for flag in red_flags(runs)]


def test_red_flags_all_clear() -> None:
    runs = [_run(1, occupancy=0.97), _run(2, occupancy=0.85), _run(42, occupancy=0.91), _run(1, 2, occupancy=0.95)]
    assert _statuses(runs) == ["clear", "clear", "clear"]


def test_occupancy_below_the_bar_raises_the_first_flag() -> None:
    flags = red_flags([_run(1, occupancy=0.69), _run(2)])
    assert flags[0].status == "raised" and "s1r1 0.6900" in flags[0].detail


def test_any_type_above_the_alert_raises_the_second_flag_party_nomination_included() -> None:
    runs = [_run(1, decisions={"vote_cast": 500, "party_nomination_choice": 15}, fallbacks={"party_nomination_choice": 2})]
    flag = red_flags(runs)[1]
    assert flag.status == "raised" and "party_nomination_choice 13.3%" in flag.detail
    exactly_at_the_alert = [_run(1, decisions={"vote_cast": 100}, fallbacks={"vote_cast": 10})]
    assert red_flags(exactly_at_the_alert)[1].status == "clear"


def test_a_repeat_diverging_more_than_the_seeds_do_raises_the_third_flag() -> None:
    runs = [_run(1, occupancy=0.90), _run(2, occupancy=0.92), _run(42, occupancy=0.91), _run(1, 2, occupancy=0.70)]
    flag = red_flags(runs)[2]
    assert flag.status == "raised"
    assert "spread across seeds 0.0200" in flag.detail and "seed 1 repeat 2: |Δ| 0.2000" in flag.detail


def test_flags_that_cannot_be_evaluated_say_so() -> None:
    assert _statuses([_run(1, outcome="crashed")]) == ["not evaluable"] * 3
    assert _statuses([_run(1, occupancy=None, decisions={})]) == ["not evaluable", "clear", "not evaluable"]
    no_repeat = red_flags([_run(1), _run(2)])[2]
    assert no_repeat.status == "not evaluable" and "0 comparable repeats" in no_repeat.detail


def _provenance(sha: str, **overrides: object) -> dict[str, object]:
    return {"git_sha": sha, "git_dirty_paths": [], "prompt_source_sha256": "p" * 64, "vllm_version": "0.28.0",
            "vllm_image_id": "sha256:61fc", "served_model_repo": "Qwen/Qwen3-8B-AWQ", "served_model_revision": "4da05a8e",
            **overrides}


def test_a_batch_run_under_one_code_and_server_has_no_provenance_differences() -> None:
    runs = [SweepRun(seed=s, repeat=1, run_id=f"s{s}", outcome="completed", run_metadata=_provenance("a" * 40)) for s in (1, 2)]
    assert provenance_differences(runs) == {}
    assert provenance_differences([_run(1), _run(2)]) == {}  # nothing recorded: nothing to compare


def test_provenance_differences_name_the_runs_and_resumes_that_differ() -> None:
    edited = _provenance("a" * 40, resumes=[_provenance("b" * 40, git_dirty_paths=["fast_api_voter/api/domain/polity/config.py"])])
    runs = [
        SweepRun(seed=1, repeat=1, run_id="s1", outcome="completed", run_metadata=_provenance("a" * 40)),
        SweepRun(seed=2, repeat=1, run_id="s2", outcome="completed", run_metadata=edited),
        SweepRun(seed=3, repeat=1, run_id="s3", outcome="crashed", run_metadata=_provenance("c" * 40)),
    ]
    differences = provenance_differences(runs)
    assert set(differences) == {"git_sha", "git_dirty_paths"}
    assert differences["git_sha"] == {"s1": "a" * 40, "s2": "a" * 40, "s2@resume1": "b" * 40}
