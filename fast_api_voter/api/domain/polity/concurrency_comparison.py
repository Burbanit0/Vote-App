"""S2.1's pre-registered comparison: runs with parallel decisions against the sequential
run of the same config, on the three things the plan names before any sweep runs.

- **vote_cast agreement with build_ranking** -- the share of the model's accepted ballots
  whose first choice (or blank) is the voter's sincere one. Read by replaying the run from
  its own call log (S0.6) through `VoteObserver`, which sees each vote_cast request as the
  model did: every voter's distance to each candidate and blank threshold are in the
  prompt, so the sincere first choice is `build_ranking`'s rule on those same values.
- **first-attempt failure rate** -- the share of a decision type's first attempts that did
  not stand (rejected, truncated or failed), from the call log.
- **wall-clock speedup** -- reported whatever it is.

Pre-registered bands against workers = 1: agreement within ±2 points, first-attempt failure
within ±5 points. The replay doubles as the plan's other requirement: each run must replay
to its own journal.
"""
from __future__ import annotations

import dataclasses
import json
import tempfile
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from api.domain.polity.config import PolityConfig
from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, decision_type_for_schema, read_calls
from api.domain.polity.llm_client import LlmResponseError, decode_vote_batch
from api.domain.polity.llm_replay import ReplayClient
from api.domain.polity.llm_time_attribution import call_category, superseded_call_indexes
from api.domain.polity.run_polity_simulation import run_simulation

AGREEMENT_BAND_POINTS = 2.0
FAILURE_BAND_POINTS = 5.0
_FAILED_FIRST_ATTEMPT = frozenset({"rejected", "truncation", "failed"})


def sincere_first_choice(voter: dict[str, Any]) -> int | str:
    """A vote_cast prompt's voter block -> the position of the nearest candidate within
    the voter's blank threshold (ties to the lower position, as build_ranking breaks them
    by citizen id and positions follow citizen ids), or "blank"."""
    within = [(distance, position) for position, distance in enumerate(voter["distances"], start=1) if distance <= voter["blank_threshold"]]
    return min(within)[1] if within else "blank"


def _chunk_agreement(user_prompt: str, content: str) -> tuple[int, int]:
    """(ballots matching the sincere first choice, ballots) for one chunk's final answer;
    (0, 0) when production would have fallen back to the deterministic ballot instead."""
    request = json.loads(user_prompt)
    voters = {voter["cid"]: voter for voter in request["voters"]}
    try:
        decisions = decode_vote_batch(content, list(voters))
    except LlmResponseError:
        return 0, 0
    if any(position > len(request["candidates"]) for d in decisions for position in d.ranking):
        return 0, 0
    agree = sum(("blank" if d.blank else d.ranking[0]) == sincere_first_choice(voters[d.cid]) for d in decisions)
    return agree, len(decisions)


class VoteObserver:
    """Wraps a client and keeps each vote_cast chunk's last answer (retries of a chunk
    repeat its user prompt, so the last one is the attempt that stood or failed last)."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._lock = threading.Lock()
        self.final_answers: dict[str, str] = {}

    def count_prompt_tokens(self, **kwargs: Any) -> int:
        return int(self._inner.count_prompt_tokens(**kwargs))

    def complete_json(self, **kwargs: Any) -> str:
        content = str(self._inner.complete_json(**kwargs))
        if decision_type_for_schema(kwargs["json_schema"]) == "vote_cast":
            with self._lock:
                self.final_answers[kwargs["user_prompt"]] = content
        return content

    def agreement(self) -> tuple[int, int]:
        pairs = [_chunk_agreement(prompt, content) for prompt, content in self.final_answers.items()]
        return sum(a for a, _ in pairs), sum(t for _, t in pairs)


def first_attempt_failures(calls: Sequence[dict[str, Any]], decision_type: str) -> tuple[int, int]:
    """(first attempts that did not stand, first attempts) for one decision type."""
    superseded = superseded_call_indexes(calls)
    firsts = [(i, c) for i, c in enumerate(calls)
              if c.get("kind") == "decision" and c.get("decision_type") == decision_type and not c.get("attempt")]
    failed = sum(call_category(c, i in superseded) in _FAILED_FIRST_ATTEMPT for i, c in firsts)
    return failed, len(firsts)


@dataclass(frozen=True)
class ArmMeasures:
    label: str
    workers: int
    vote_agreement: tuple[int, int]
    first_attempt_failures: dict[str, tuple[int, int]]
    wall_clock_seconds: float | None
    replays_to_its_journal: bool


def _rate(pair: tuple[int, int]) -> float | None:
    return pair[0] / pair[1] if pair[1] else None


def measure_run(run_dir: Path, config: PolityConfig, *, label: str) -> ArmMeasures:
    """Replay a recorded run from its call log under `config` (the config it ran with), and
    read the three measures off the replay and the log."""
    calls = read_calls(run_dir / CALL_LOG_FILENAME)
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    progress_path = run_dir / "progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.is_file() else {}
    observer = VoteObserver(ReplayClient(calls))
    with tempfile.TemporaryDirectory() as tmp:
        replay_config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=tmp, index_after_run=False))
        replayed = run_simulation(replay_config, run_id=str(metadata["run_id"]), llm_client=observer)
        identical = replayed.read_bytes() == (run_dir / "events.jsonl").read_bytes()
    types = sorted({str(c["decision_type"]) for c in calls if c.get("kind") == "decision" and c.get("decision_type")})
    return ArmMeasures(
        label=label, workers=config.parallel.intra_run_workers, vote_agreement=observer.agreement(),
        first_attempt_failures={t: first_attempt_failures(calls, t) for t in types},
        wall_clock_seconds=progress.get("wall_clock_elapsed_seconds"), replays_to_its_journal=identical,
    )


def _points(arm: tuple[int, int], baseline: tuple[int, int]) -> float | None:
    arm_rate, base_rate = _rate(arm), _rate(baseline)
    return None if arm_rate is None or base_rate is None else 100 * (arm_rate - base_rate)


def compare_to_baseline(baseline: ArmMeasures, arm: ArmMeasures) -> dict[str, Any]:
    """The pre-registered verdict for one arm: each measure's difference in points, and
    whether it is inside its band."""
    agreement = _points(arm.vote_agreement, baseline.vote_agreement)
    failures = {t: _points(pair, baseline.first_attempt_failures.get(t, (0, 0))) for t, pair in arm.first_attempt_failures.items()}
    vote_failures = failures.get("vote_cast")
    speedup = baseline.wall_clock_seconds / arm.wall_clock_seconds if baseline.wall_clock_seconds and arm.wall_clock_seconds else None
    return {
        "label": arm.label, "workers": arm.workers,
        "vote_agreement_points": agreement,
        "vote_agreement_within_band": None if agreement is None else abs(agreement) <= AGREEMENT_BAND_POINTS,
        "first_attempt_failure_points": failures,
        "vote_first_attempt_failure_within_band": None if vote_failures is None else abs(vote_failures) <= FAILURE_BAND_POINTS,
        "speedup": speedup,
        "replays_to_its_journal": arm.replays_to_its_journal,
    }
