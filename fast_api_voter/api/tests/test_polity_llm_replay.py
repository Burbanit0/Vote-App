"""Replay client (S0.6). See api/domain/polity/llm_replay.py."""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, llm_call_id, read_calls, request_sha256
from api.domain.polity.llm_client import LlmResponseError, LlmTransportError
from api.domain.polity.llm_replay import ReplayClient, UnrecordedRequestError
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.polity_golden import golden_config
from api.tests.test_polity_retry_provenance import _FirstCallOfEachTypeFailsClient, _one_replay
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient

_REQUEST = {"system_prompt": "s", "user_prompt": "u", "json_schema": {"type": "object"}, "max_tokens": 64}


def _record(kind: str = "decision", *, request: dict[str, Any] = _REQUEST, **fields: Any) -> dict[str, Any]:
    if kind == "budget_probe":
        digest = request_sha256(system_prompt=request["system_prompt"], user_prompt=request["user_prompt"],
                                json_schema=None, max_tokens=None)
    else:
        digest = request_sha256(**request)
    return {"kind": kind, "call_id": llm_call_id(digest), "request_sha256": digest, **fields}


def test_a_replayed_run_reproduces_the_recorded_journal_byte_for_byte(tmp_path: Path) -> None:
    # Recorded with a retry on every decision type and token-budget probes, so replay
    # must reproduce rejected answers, recovering retries and probes in order.
    config = _one_replay(golden_config(tmp_path / "recorded", llm=True))
    recorded = run_simulation(config, run_id="run", llm_client=_FirstCallOfEachTypeFailsClient(_ElectingFakeLlmClient()))

    replay = ReplayClient.from_run_dir(recorded.parent)
    replay_config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(tmp_path / "replayed")))
    replayed = run_simulation(replay_config, run_id="run", llm_client=replay)

    assert replayed.read_bytes() == recorded.read_bytes()
    assert replay.unserved == 0
    assert replay.served == len(read_calls(recorded.parent / CALL_LOG_FILENAME))


def test_a_replay_under_a_different_seed_fails_on_its_first_unrecorded_request(tmp_path: Path) -> None:
    config = golden_config(tmp_path / "recorded", llm=True)
    recorded = run_simulation(config, run_id="run", llm_client=_ElectingFakeLlmClient())
    other = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, seed=config.run.seed + 1),
        journal=dataclasses.replace(config.journal, output_dir=str(tmp_path / "replayed")),
    )
    with pytest.raises(UnrecordedRequestError, match="diverged"):
        run_simulation(other, run_id="run", llm_client=ReplayClient.from_run_dir(recorded.parent))


def test_identical_requests_are_answered_in_recorded_order_and_no_more_times() -> None:
    replay = ReplayClient([_record(content="first"), _record(content="second"), _record("warm_up", content="skipped")])
    assert replay.unserved == 2  # warm-up records are never asked for by an injected client
    assert [replay.complete_json(**_REQUEST), replay.complete_json(**_REQUEST)] == ["first", "second"]
    with pytest.raises(UnrecordedRequestError):
        replay.complete_json(**_REQUEST)
    with pytest.raises(UnrecordedRequestError):
        replay.complete_json(**{**_REQUEST, "seed": 7})  # a retry's sampling override is part of the request


def test_a_budget_probe_is_answered_with_its_recorded_prompt_tokens() -> None:
    replay = ReplayClient([_record("budget_probe", prompt_tokens=812), _record("budget_probe")])
    assert replay.count_prompt_tokens(system_prompt="s", user_prompt="u") == 812
    with pytest.raises(UnrecordedRequestError, match="without prompt_tokens"):
        replay.count_prompt_tokens(system_prompt="s", user_prompt="u")


@pytest.mark.parametrize(
    ("error", "raised"),
    [
        ("LlmResponseError: generation did not finish cleanly: finish_reason='length'", LlmResponseError),
        ("LlmTransportError: request to http://vllm/v1 failed: refused", LlmTransportError),
        ("KeyError: 'choices'", UnrecordedRequestError),
    ],
)
def test_a_recorded_failure_is_replayed_as_the_same_failure(error: str, raised: type[Exception]) -> None:
    replay = ReplayClient([_record(content='{"decisions": [', error=error)])
    with pytest.raises(raised):
        replay.complete_json(**_REQUEST)


def test_a_decision_recorded_without_content_cannot_be_replayed() -> None:
    with pytest.raises(UnrecordedRequestError, match="without content"):
        ReplayClient([_record()]).complete_json(**_REQUEST)
