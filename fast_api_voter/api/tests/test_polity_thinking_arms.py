"""S1.3: request arms for the bake-off -- vLLM's `thinking_token_budget` on the thinking vote
and chamber cases -- and the extra request fields they travel as, through the vLLM client,
the call log and the replay client."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from api.domain.polity.bakeoff_bank import CaseBank
from api.domain.polity.bakeoff_runner import (
    ARMS,
    SESSION_FILENAME,
    RESULTS_FILENAME,
    read_results,
    request_resolver,
    run_session,
)
from api.domain.polity.llm_call_log import CallLoggingClient, CallLogWriter, completion_request_sha256, read_calls, request_sha256
from api.domain.polity.llm_client import VllmJsonClient
from api.domain.polity.llm_replay import ReplayClient
from api.tests.polity_bakeoff_fixtures import BankFakeClient, reference_bank, reference_config

_REQUEST: dict[str, Any] = {"system_prompt": "s", "user_prompt": "u", "json_schema": {"title": "VoteCastBatch"}, "max_tokens": 64}


def test_extra_fields_enter_the_request_hash_only_when_given() -> None:
    assert completion_request_sha256(_REQUEST) == request_sha256(system_prompt="s", user_prompt="u",
                                                                  json_schema={"title": "VoteCastBatch"}, max_tokens=64)
    budgeted = completion_request_sha256({**_REQUEST, "extra_body": {"thinking_token_budget": 2048}})
    assert budgeted != completion_request_sha256(_REQUEST)
    assert budgeted != completion_request_sha256({**_REQUEST, "extra_body": {"thinking_token_budget": 4096}})


def test_the_vllm_client_merges_extra_fields_into_the_body_last() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                                          "usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    client = VllmJsonClient("http://localhost:8000/v1", "qwen3:8b", 0.0, seed=42, timeout=5.0, transport=httpx.MockTransport(handler))
    client.complete_json(**_REQUEST, extra_body={"thinking_token_budget": 2048, "top_k": 20})
    client.complete_json(**_REQUEST)
    assert (bodies[0]["thinking_token_budget"], bodies[0]["top_k"]) == (2048, 20)
    assert "thinking_token_budget" not in bodies[1]
    assert {k: v for k, v in bodies[0].items() if k not in ("thinking_token_budget", "top_k")} == bodies[1]


class _Inner:
    def complete_json(self, **kwargs: Any) -> str:
        return "{}"


def test_the_call_log_records_extra_fields_and_a_replay_answers_by_them(tmp_path: Path) -> None:
    path = tmp_path / "calls.jsonl"
    with CallLogWriter(path) as writer:
        logged = CallLoggingClient(_Inner(), writer, tick_source=lambda: None)
        logged.complete_json(**_REQUEST, extra_body={"thinking_token_budget": 2048})
        logged.complete_json(**_REQUEST)
    calls = read_calls(path)
    assert calls[0]["extra_body"] == {"thinking_token_budget": 2048} and "extra_body" not in calls[1]
    replay = ReplayClient(calls)
    assert replay.complete_json(**_REQUEST, extra_body={"thinking_token_budget": 2048}) == "{}"
    assert replay.complete_json(**_REQUEST) == "{}"


class _KwargsRecorder(BankFakeClient):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[dict[str, Any]] = []

    def complete_json(self, **kwargs: Any) -> str:
        self.requests.append(kwargs)
        return str(super().complete_json(**{k: v for k, v in kwargs.items() if k != "extra_body"}))


def test_a_budget_arm_sends_the_budget_to_thinking_vote_and_chamber_cases_only(tmp_path: Path) -> None:
    bank = reference_bank()
    families = ("vote_first_choice", "chamber_poles", "candidacy_p500")
    small = CaseBank(reference=bank.reference, cases=tuple(c for c in bank.cases if c.family in families))
    client = _KwargsRecorder()
    run_session(small, client, reference_config(), tmp_path / "arm", metadata={"label": "arm"}, warm_up=False, rerun_fraction=0.0,
                families=list(families), arm="thinking_budget_2048")

    assert json.loads((tmp_path / "arm" / SESSION_FILENAME).read_text())["arm"] == "thinking_budget_2048"
    sent = {(r["json_schema"]["title"], json.dumps(r.get("extra_body"), sort_keys=True)) for r in client.requests}
    assert sent == {("VoteCastBatch", '{"thinking_token_budget": 2048}'), ("ChamberBatch", '{"thinking_token_budget": 2048}'),
                    ("CandidacyBatch", "null")}
    assert all(r["valid"] for r in read_results(tmp_path / "arm" / RESULTS_FILENAME))
    assert request_resolver(None)(small.cases[0]) == {}
    assert ARMS["vote_grammar"].request is None and request_resolver("vote_grammar")(small.cases[0]) == {}
    assert ARMS["thinking_budget_4096"].request is not None
