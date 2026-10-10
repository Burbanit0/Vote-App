"""Sweep statistics and pre-registered red flags (S0.7).
See api/domain/polity/sweep_statistics.py."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.sweep_statistics import (
    SweepRun,
    clopper_pearson,
    constitution_groups,
    first_completed_runs,
    mean_bca_interval,
    paired_contrast,
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
    return {"git_sha": sha, "git_dirty_paths": [], "prompt_source_sha256": "p" * 64, "vllm_version": "0.31.0",
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


# ── paired_contrast (PLAN_BEYOND_CI W2.1) ──────────────────────────────────


def test_a_shift_on_every_seed_is_significant_and_its_p_is_exact() -> None:
    arm_a = {seed: 5.0 for seed in range(1, 11)}
    arm_b = {seed: 6.0 + seed / 100 for seed in range(1, 11)}
    contrast = paired_contrast(arm_a, arm_b)
    assert contrast is not None
    assert contrast.seeds == tuple(range(1, 11))
    assert contrast.mean_difference == pytest.approx(1.055)
    assert contrast.p_value == pytest.approx(2 / 2**10)  # only "all +" and "all -" are as extreme
    assert contrast.interval is not None and contrast.interval[0] > 0


def test_no_effect_gives_no_signal() -> None:
    arm_a = {seed: 5.0 for seed in range(1, 11)}
    arm_b = {seed: 5.0 + (1 if seed % 2 else -1) for seed in range(1, 11)}
    contrast = paired_contrast(arm_a, arm_b)
    assert contrast is not None and contrast.mean_difference == 0 and contrast.p_value == pytest.approx(1.0)
    same = paired_contrast(arm_a, dict(arm_a))
    assert same is not None and same.p_value == 1.0 and same.interval is None


def test_only_shared_seeds_are_paired() -> None:
    contrast = paired_contrast({1: 1.0, 2: 2.0, 3: 3.0}, {2: 4.0, 3: 3.0, 4: 9.0})
    assert contrast is not None and contrast.seeds == (2, 3) and contrast.differences == (2.0, 0.0)
    assert paired_contrast({1: 1.0}, {2: 1.0}) is None


def test_one_shared_seed_is_p_one_and_a_non_finite_value_raises() -> None:
    one = paired_contrast({1: 0.0}, {1: 5.0})
    assert one is not None and one.p_value == 1.0 and one.mean_difference == 5.0
    with pytest.raises(ValueError, match="non-finite"):
        paired_contrast({1: 1.0, 2: 2.0, 3: float("nan")}, {1: 2.0, 2: 3.0, 3: 1.0})


def test_many_seeds_fall_back_to_seeded_random_flips() -> None:
    arm_a = {seed: 0.0 for seed in range(30)}
    arm_b = {seed: 1.0 for seed in range(30)}
    contrast = paired_contrast(arm_a, arm_b)
    assert contrast is not None and contrast.p_value < 1e-3
    assert paired_contrast(arm_a, arm_b) == contrast  # seeded: the same p twice


def test_two_arms_on_the_same_seed_stay_apart() -> None:
    runs = [SweepRun(seed=1, repeat=1, run_id="a", outcome="completed", arm="3pct"),
            SweepRun(seed=1, repeat=1, run_id="b", outcome="completed", arm="5pct")]
    assert {run.run_id for run in first_completed_runs(runs)} == {"a", "b"}


# ── constitution versions (ADR-015): never pooled across ──────────────────

THRESHOLD = ((2, "institutions.electoral_threshold", 0.08),)


def test_completed_runs_are_grouped_by_their_constitutional_history() -> None:
    later = (*THRESHOLD, (6, "institutions.electoral_threshold", 0.05))
    same_rule_later = ((6, "institutions.electoral_threshold", 0.08),)
    runs = [_run(1), _run(2), dataclasses.replace(_run(3), constitution=THRESHOLD),
            dataclasses.replace(_run(4), constitution=later), dataclasses.replace(_run(5), constitution=same_rule_later),
            dataclasses.replace(_run(6), constitution=None), dataclasses.replace(_run(7, outcome="crashed"), constitution=THRESHOLD)]
    groups = constitution_groups(runs)
    assert {k: [r.seed for r in v] for k, v in groups.items()} == {
        (): [1, 2], THRESHOLD: [3], later: [4], same_rule_later: [5], None: [6]}


def test_the_summary_pools_occupancy_within_a_constitutional_history_never_across(seed_sweep: Any) -> None:
    one_rule = [_run(1, occupancy=0.9), _run(2, occupancy=0.8)]
    assert any("95% BCa" in line for line in seed_sweep._occupancy_section(one_rule))
    mixed = [*one_rule, dataclasses.replace(_run(3, occupancy=0.5), constitution=THRESHOLD),
             dataclasses.replace(_run(4, occupancy=0.4), constitution=None)]
    lines = seed_sweep._occupancy_section(mixed)
    assert any("not pooled across seeds" in line and "3 constitutional histories" in line for line in lines)
    assert any(line.startswith("- unamended (seed 1, seed 2)") for line in lines)
    assert "- not summarised (alone in their history, or history unknown): seed 3, seed 4" in lines
    assert not any("0.5000" in line or "0.4000" in line for line in lines)

    unknown = [dataclasses.replace(r, constitution=None) for r in one_rule]
    assert not any("95% BCa" in line for line in seed_sweep._occupancy_section(unknown))

    repeats = [*mixed, dataclasses.replace(_run(3, 2), constitution=())]
    section = seed_sweep._constitution_section(repeats)
    assert "- unamended: seed 1, seed 2, seed 3 rep 2" in section
    assert "- electoral_threshold 0.08 at t2: seed 3" in section
    assert "- unknown (journal missing or damaged): seed 4" in section


def test_the_history_is_read_from_the_journal_and_unknown_when_it_cannot_be(seed_sweep: Any, tmp_path: Path) -> None:
    journal = tmp_path / "events.jsonl"
    amended = {"event_type": "constitution_amended", "tick": 2,
               "payload": {"article": "institutions.electoral_threshold", "new": 0.08}}
    body = json.dumps({"event_type": "elected", "tick": 1, "payload": {}}) + "\n" + json.dumps(amended) + "\n"
    journal.write_text(body + '{"event_type": "constitution_amended", "payl', encoding="utf-8")  # torn last line
    assert seed_sweep._amendments(journal) == THRESHOLD
    journal.write_text("{oops\n" + body + '{"event_type": "constitution_amended", "payl', encoding="utf-8")
    assert seed_sweep._amendments(journal) is None
    assert seed_sweep._amendments(tmp_path / "missing.jsonl") is None


def test_the_written_summary_reads_each_runs_history_and_notes_it_under_the_red_flags(seed_sweep: Any, tmp_path: Path) -> None:
    amended = {"event_type": "constitution_amended", "tick": 2,
               "payload": {"article": "institutions.electoral_threshold", "new": 0.08}}
    for seed, journal in ((1, []), (2, []), (3, [amended])):
        run_dir = tmp_path / f"sweep-1y-p10-seed{seed}" / "run" / f"sweep-1y-p10-seed{seed}"
        run_dir.mkdir(parents=True)
        (run_dir / "digest.json").write_text(json.dumps({"outcome": "completed", "office_occupancy": 0.9}), encoding="utf-8")
        (run_dir / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in journal), encoding="utf-8")
    text = seed_sweep._write_sweep_summary(tmp_path, 1, 10, [1, 2, 3]).read_text(encoding="utf-8")
    assert "- electoral_threshold 0.08 at t2: seed 3" in text
    assert "- note: the runs behind these flags span 2 constitutional histories (see Constitutions)" in text
