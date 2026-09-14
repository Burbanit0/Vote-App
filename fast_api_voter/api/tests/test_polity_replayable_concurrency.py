"""S2.1: parallel decisions under `llm.reproducibility: relaxed`, and the comparison the
concurrency sweep is judged on. See api/domain/polity/concurrency_comparison.py."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity import concurrency_comparison as cc
from api.domain.polity.config import PolityConfig, PolityConfigError, validate_config
from api.domain.polity.llm_behavior_engine import decide_candidacies
from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, read_calls
from api.domain.polity.llm_replay import ReplayClient
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.polity_golden import golden_config
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient


def _config(output_dir: Path, *, workers: int = 1, reproducibility: str = "strict", provider: str = "vllm") -> PolityConfig:
    config = golden_config(output_dir, llm=True)
    return dataclasses.replace(
        config,
        vote=dataclasses.replace(config.vote, mode="llm"),  # as the sweep: the model casts every ballot
        llm=dataclasses.replace(config.llm, reproducibility=reproducibility, provider=provider),
        parallel=dataclasses.replace(config.parallel, intra_run_workers=workers),
    )


def test_parallel_workers_need_the_relaxed_mode_on_vllm() -> None:
    with pytest.raises(PolityConfigError, match="requires 'llm.reproducibility: relaxed'"):
        validate_config(_config(Path("x"), workers=4))
    with pytest.raises(PolityConfigError, match="needs 'llm.provider: vllm'"):
        validate_config(_config(Path("x"), workers=4, reproducibility="relaxed", provider="ollama"))
    validate_config(_config(Path("x"), workers=4, reproducibility="relaxed"))
    deterministic = _config(Path("x"), workers=4)
    validate_config(dataclasses.replace(deterministic, llm=dataclasses.replace(deterministic.llm, enabled=False)))
    with pytest.raises(NotImplementedError, match="relaxed on the vllm provider"):
        decide_candidacies([], _config(Path("x"), workers=4), _ElectingFakeLlmClient())


def test_a_relaxed_run_with_parallel_workers_writes_the_sequential_journal_and_replays_to_it(tmp_path: Path) -> None:
    # A deterministic fake answers the same whatever the batching, so parallel chunks must
    # leave the journal byte-identical: results are journaled in chunk order.
    sequential = run_simulation(_config(tmp_path / "w1"), run_id="run", llm_client=_ElectingFakeLlmClient())
    parallel = run_simulation(_config(tmp_path / "w4", workers=4, reproducibility="relaxed"), run_id="run", llm_client=_ElectingFakeLlmClient())
    assert parallel.read_bytes() == sequential.read_bytes()
    metadata = json.loads((parallel.parent / "run_metadata.json").read_text())
    assert (metadata["llm_reproducibility"], metadata["intra_run_workers"]) == ("relaxed", 4)

    replay_config = _config(tmp_path / "replay", workers=4, reproducibility="relaxed")
    replayed = run_simulation(replay_config, run_id="run", llm_client=ReplayClient(read_calls(parallel.parent / CALL_LOG_FILENAME)))
    assert replayed.read_bytes() == parallel.read_bytes()


def _vote_prompt(voters: list[dict[str, Any]], candidates: int = 3) -> str:
    return json.dumps({"candidates": [{"position": i} for i in range(1, candidates + 1)], "voters": voters})


def test_the_sincere_first_choice_is_the_nearest_acceptable_candidate() -> None:
    assert cc.sincere_first_choice({"distances": [0.4, 0.2, 0.2], "blank_threshold": 0.3}) == 2  # tie: lower position
    assert cc.sincere_first_choice({"distances": [0.4, 0.5], "blank_threshold": 0.3}) == "blank"
    assert cc.sincere_first_choice({"distances": [0.3], "blank_threshold": 0.3}) == 1  # at the threshold counts


class _Scripted:
    def __init__(self, answers: dict[str, str]) -> None:
        self.answers = answers

    def complete_json(self, **kwargs: Any) -> str:
        return self.answers[kwargs["user_prompt"]]

    def count_prompt_tokens(self, **kwargs: Any) -> int:
        return 7


def test_the_observer_scores_each_chunks_final_answer_and_skips_what_production_would_replace() -> None:
    agreeing = _vote_prompt([{"cid": 1, "distances": [0.1, 0.5, 0.6], "blank_threshold": 0.3},
                             {"cid": 2, "distances": [0.9, 0.9, 0.9], "blank_threshold": 0.3}])
    undecodable = _vote_prompt([{"cid": 3, "distances": [0.1, 0.2, 0.3], "blank_threshold": 0.5}])
    out_of_range = _vote_prompt([{"cid": 4, "distances": [0.1, 0.2, 0.3], "blank_threshold": 0.5}])
    answers = {
        agreeing: json.dumps({"decisions": [{"cid": 1, "blank": 0, "ranking": [1], "motif": 104},
                                            {"cid": 2, "blank": 0, "ranking": [3], "motif": 104}]}),
        undecodable: "not json",
        out_of_range: json.dumps({"decisions": [{"cid": 4, "blank": 0, "ranking": [9], "motif": 104}]}),
    }
    observer = cc.VoteObserver(_Scripted(answers))
    for prompt in answers:
        observer.complete_json(system_prompt="s", user_prompt=prompt, json_schema=VOTE_CAST_JSON_SCHEMA, max_tokens=1)
    observer.complete_json(system_prompt="s", user_prompt=agreeing, json_schema={"title": "CandidacyBatch"}, max_tokens=1)
    assert observer.agreement() == (1, 2)  # voter 1 agrees; voter 2 should have voted blank
    assert observer.count_prompt_tokens(system_prompt="s", user_prompt="u") == 7


def test_first_attempt_failures_count_what_did_not_stand() -> None:
    calls = [
        {"kind": "decision", "decision_type": "vote_cast", "tick": 0, "unit_ids": [1], "attempt": 0, "started_at": 0, "content": "bad"},
        {"kind": "decision", "decision_type": "vote_cast", "tick": 0, "unit_ids": [1], "attempt": 1, "started_at": 1, "content": "ok"},
        {"kind": "decision", "decision_type": "vote_cast", "tick": 0, "unit_ids": [2], "attempt": 0, "started_at": 2, "finish_reason": "length"},
        {"kind": "decision", "decision_type": "vote_cast", "tick": 0, "unit_ids": [3], "attempt": 0, "started_at": 3, "content": "ok"},
        {"kind": "budget_probe", "decision_type": "vote_cast", "tick": 0, "unit_ids": [3], "attempt": None, "started_at": 3},
        {"kind": "decision", "decision_type": "pressure_action", "tick": 0, "unit_ids": [9], "attempt": 0, "started_at": 4, "content": "ok"},
    ]
    assert cc.first_attempt_failures(calls, "vote_cast") == (2, 3)
    assert cc.first_attempt_failures(calls, "pressure_action") == (0, 1)


def test_a_recorded_arm_is_measured_by_replay_and_compared_on_the_preregistered_bands(tmp_path: Path) -> None:
    baseline_journal = run_simulation(_config(tmp_path / "w1"), run_id="w1", llm_client=_ElectingFakeLlmClient())
    arm_journal = run_simulation(_config(tmp_path / "w4", workers=4, reproducibility="relaxed"), run_id="w4", llm_client=_ElectingFakeLlmClient())
    for journal, seconds in ((baseline_journal, 8.0), (arm_journal, 2.0)):  # a fake run's own wall clock rounds to 0.0
        progress = journal.parent / "progress.json"
        progress.write_text(json.dumps(json.loads(progress.read_text()) | {"wall_clock_elapsed_seconds": seconds}))
    baseline = cc.measure_run(baseline_journal.parent, _config(tmp_path / "unused"), label="w1")
    arm = cc.measure_run(arm_journal.parent, _config(tmp_path / "unused", workers=4, reproducibility="relaxed"), label="w4")

    assert baseline.replays_to_its_journal and arm.replays_to_its_journal
    assert baseline.vote_agreement == arm.vote_agreement and baseline.vote_agreement[1] > 0
    assert arm.workers == 4 and set(arm.first_attempt_failures) >= {"vote_cast", "candidacy_considered"}
    verdict = cc.compare_to_baseline(baseline, arm)
    assert (verdict["vote_agreement_points"], verdict["vote_agreement_within_band"], verdict["vote_first_attempt_failure_within_band"]) == (0.0, True, True)
    assert verdict["speedup"] == 4.0 and verdict["replays_to_its_journal"] is True


def test_the_verdict_is_unmeasured_where_a_measure_is_missing_and_outside_the_band_beyond_it() -> None:
    base = cc.ArmMeasures("w1", 1, (90, 100), {"vote_cast": (10, 100)}, 100.0, True)
    worse = cc.ArmMeasures("w8", 8, (85, 100), {"vote_cast": (20, 100), "chamber_deliberation": (1, 10)}, 25.0, False)
    verdict = cc.compare_to_baseline(base, worse)
    assert verdict["vote_agreement_points"] == pytest.approx(-5.0) and verdict["vote_agreement_within_band"] is False
    assert verdict["first_attempt_failure_points"]["vote_cast"] == pytest.approx(10.0)
    assert verdict["vote_first_attempt_failure_within_band"] is False and verdict["first_attempt_failure_points"]["chamber_deliberation"] is None
    assert verdict["speedup"] == 4.0
    empty = cc.ArmMeasures("w4", 4, (0, 0), {}, None, True)
    assert cc.compare_to_baseline(base, empty) | {"label": "w4"} == {
        "label": "w4", "workers": 4, "vote_agreement_points": None, "vote_agreement_within_band": None,
        "first_attempt_failure_points": {}, "vote_first_attempt_failure_within_band": None, "speedup": None,
        "replays_to_its_journal": True,
    }
