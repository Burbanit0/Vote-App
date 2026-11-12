"""Per-call LLM log (S0.5). See api/domain/polity/llm_call_log.py."""
from __future__ import annotations

import dataclasses
import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest

from api.domain.polity import llm_call_log
from api.domain.polity import run_polity_simulation as run_polity_simulation_module
from api.domain.polity.config import load_config
from api.domain.polity.llm_call_log import (
    CALL_LOG_FILENAME,
    CALL_LOG_SUMMARY_FILENAME,
    PROMPT_LOG_ENV,
    PROMPT_LOG_FILENAME,
    CallLoggingClient,
    CallLogWriter,
    PromptLogWriter,
    call_context,
    call_logged,
    llm_call_id,
    read_prompts,
    record_http_response,
    request_sha256,
    response_fields,
)
from api.domain.polity.llm_client import LlmResponseError, VllmJsonClient
from api.domain.polity.run_polity_simulation import _llm_client_scope, run_simulation
from api.tests.polity_golden import LLM_DECISION_TYPES, golden_config
from api.tests.test_polity_retry_provenance import (
    _FirstCallOfEachTypeFailsClient,
    _one_replay,
    _RetryDecodesButFailsValidationClient,
)
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient, _events

# A real vLLM 0.28 response body (qwen3:8b, thinking on), trimmed to the fields read.
_VLLM_BODY = {
    "choices": [{
        "finish_reason": "stop",
        "message": {"content": '{"ok": true}', "reasoning": "\nOkay, the user is asking if 7 is prime.", "role": "assistant"},
    }],
    "usage": {
        "prompt_tokens": 31, "completion_tokens": 278, "total_tokens": 309,
        "prompt_tokens_details": {"cached_tokens": 16}, "completion_tokens_details": {"reasoning_tokens": 270},
    },
}


def _calls(run_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (run_dir / CALL_LOG_FILENAME).read_text(encoding="utf-8").splitlines()]


def _golden_run(tmp_path: Path, client: Any, *, replays: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    config = golden_config(tmp_path, llm=True)
    journal_path = run_simulation(_one_replay(config) if replays else config, run_id="log", llm_client=client)
    return _events(journal_path), _calls(journal_path.parent)


def _unit_of(event: dict[str, Any]) -> int | None:
    if event["event_type"] in ("party_nomination_choice", "coalition_decision"):
        return None  # keyed by party, not by the event's citizen
    return int(event["citizen_id"])


def test_every_llm_derived_event_resolves_to_the_call_that_produced_it(tmp_path: Path) -> None:
    events, calls = _golden_run(tmp_path, _ElectingFakeLlmClient())
    decisions = {(c["call_id"], c["tick"]): c for c in calls if c["kind"] == "decision"}
    llm_events = [e for e in events if e["codebook_version"]]

    assert {e["event_type"] for e in llm_events} == set(LLM_DECISION_TYPES)
    for event in llm_events:
        call = decisions[(event["payload"]["llm_call_id"], event["tick"])]
        assert call["decision_type"] == event["event_type"]
        assert _unit_of(event) is None or _unit_of(event) in call["unit_ids"]


def test_logged_lines_carry_the_request_identity_and_what_came_back(tmp_path: Path) -> None:
    _, calls = _golden_run(tmp_path, _ElectingFakeLlmClient())
    for call in calls:
        assert call["call_id"] == llm_call_id(call["request_sha256"])
        assert call["latency_ms"] >= 0 and call["started_at"] > 0
        assert "error" not in call
    decisions = [c for c in calls if c["kind"] == "decision"]
    assert all(c["content"] and c["attempt"] == 0 for c in decisions)
    # A token-budget probe precedes its batch, and names the same batch.
    probes = [c for c in calls if c["kind"] == "budget_probe"]
    assert probes and {c["decision_type"] for c in probes} == {"vote_cast", "chamber_deliberation"}
    batches = {(c["tick"], c["decision_type"], tuple(c["unit_ids"])) for c in decisions}
    assert all((p["tick"], p["decision_type"], tuple(p["unit_ids"])) in batches for p in probes)
    summary = json.loads((tmp_path / "log" / CALL_LOG_SUMMARY_FILENAME).read_text(encoding="utf-8"))
    assert summary["calls"] == len(calls) and summary["bytes"] > 0 and summary["writer_ms_mean"] is not None


def test_a_retried_decision_points_at_the_recovering_attempt(tmp_path: Path) -> None:
    events, calls = _golden_run(tmp_path, _FirstCallOfEachTypeFailsClient(_ElectingFakeLlmClient()), replays=True)
    by_id = {c["call_id"]: c for c in calls if c["kind"] == "decision"}
    retried = [e for e in events if e["codebook_version"] and e["payload"]["retry_sampling_varied"]]
    assert {e["event_type"] for e in retried} == set(LLM_DECISION_TYPES)
    for event in retried:
        recovering = by_id[event["payload"]["llm_call_id"]]
        assert recovering["attempt"] == 1 and recovering["temperature"] is not None
        # The attempt just before it on the same batch -- coalition rounds reuse the
        # same parties within a tick, so "same units" alone would also match later rounds.
        rejected = max(
            (
                c for c in calls
                if c["kind"] == "decision" and c["attempt"] == 0 and c["tick"] == recovering["tick"]
                and c["unit_ids"] == recovering["unit_ids"] and c["decision_type"] == recovering["decision_type"]
                and c["started_at"] <= recovering["started_at"]
            ),
            key=lambda c: c["started_at"],
        )
        assert rejected["content"] == "not valid json"


def test_a_fallback_decision_points_at_the_attempt_whose_failure_caused_it(tmp_path: Path) -> None:
    events, calls = _golden_run(tmp_path, _RetryDecodesButFailsValidationClient(_ElectingFakeLlmClient()), replays=True)
    by_id = {c["call_id"]: c for c in calls if c["kind"] == "decision"}
    fallbacks = [e for e in events if e["event_type"] == "vote_cast" and e["payload"]["llm_fallback"]]
    assert fallbacks
    assert {by_id[e["payload"]["llm_call_id"]]["attempt"] for e in fallbacks} == {1}


def test_response_fields_read_vllm_and_ollama_bodies_and_ignore_anything_else() -> None:
    assert response_fields(_VLLM_BODY) == {
        "prompt_tokens": 31, "completion_tokens": 278, "reasoning_tokens": 270, "cached_tokens": 16,
        "finish_reason": "stop", "reasoning": "\nOkay, the user is asking if 7 is prime.", "content": '{"ok": true}',
    }
    ollama = {"message": {"content": "{}", "thinking": "hmm"}, "done_reason": "length", "prompt_eval_count": 9, "eval_count": 4}
    assert response_fields(ollama) == {
        "prompt_tokens": 9, "completion_tokens": 4, "finish_reason": "length", "reasoning": "hmm", "content": "{}",
    }
    assert response_fields(["not", "a", "body"]) == {}
    assert response_fields({"choices": [], "usage": {"prompt_tokens": True}}) == {}


def test_record_http_response_fills_only_an_in_flight_record() -> None:
    record_http_response(httpx.Response(200, json=_VLLM_BODY))  # nothing in flight: a no-op
    llm_call_log._in_flight.record = record = {}
    try:
        record_http_response(httpx.Response(200, content=b"not json"))
        assert record == {}
        record_http_response(httpx.Response(200, json=_VLLM_BODY))
        assert record["reasoning_tokens"] == 270
    finally:
        llm_call_log._in_flight.record = None


def _vllm_client(body: dict[str, Any]) -> VllmJsonClient:
    return VllmJsonClient(
        "http://vllm.test/v1", "qwen3:8b", 0.0, 42, 5.0,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
    )


def test_a_truncated_generation_is_logged_with_its_reasoning_before_the_client_rejects_it(tmp_path: Path) -> None:
    truncated = {
        "choices": [{"finish_reason": "length", "message": {"content": '{"decisions": [', "reasoning": "looping..."}}],
        "usage": {"prompt_tokens": 500, "completion_tokens": 3000},
    }
    with CallLogWriter(tmp_path / CALL_LOG_FILENAME) as writer:
        client = CallLoggingClient(_vllm_client(truncated), writer, tick_source=lambda: 16)
        with call_context(decision_type="vote_cast", unit_ids=[3, 4, 5], attempt=0), pytest.raises(LlmResponseError):
            client.complete_json(system_prompt="s", user_prompt="u", json_schema={"type": "object"}, max_tokens=3000)
    (call,) = _calls(tmp_path)
    assert call["finish_reason"] == "length" and call["completion_tokens"] == 3000
    assert call["reasoning"] == "looping..." and call["content"] == '{"decisions": ['
    assert call["error"].startswith("LlmResponseError")
    assert (call["tick"], call["decision_type"], call["unit_ids"], call["attempt"]) == (16, "vote_cast", [3, 4, 5], 0)


def test_a_budget_probe_through_a_real_client_logs_its_prompt_tokens(tmp_path: Path) -> None:
    probe = {"choices": [{"finish_reason": "length", "message": {"content": ""}}], "usage": {"prompt_tokens": 812, "completion_tokens": 1}}
    with CallLogWriter(tmp_path / CALL_LOG_FILENAME) as writer:
        client = CallLoggingClient(_vllm_client(probe), writer, tick_source=lambda: None)
        assert client.count_prompt_tokens(system_prompt="s", user_prompt="u") == 812
    (call,) = _calls(tmp_path)
    assert (call["kind"], call["prompt_tokens"], call["decision_type"]) == ("budget_probe", 812, None)


def test_the_engine_and_the_log_hash_a_request_the_same_way(tmp_path: Path) -> None:
    class Echo:
        def complete_json(self, **kwargs: Any) -> str:
            return "{}"

    with CallLogWriter(tmp_path / CALL_LOG_FILENAME) as writer:
        CallLoggingClient(Echo(), writer, tick_source=lambda: None).complete_json(
            system_prompt="s", user_prompt="u", json_schema={"type": "object"}, max_tokens=10, think=False, seed=7,
        )
    expected = request_sha256(system_prompt="s", user_prompt="u", json_schema={"type": "object"}, max_tokens=10, think=False, seed=7)
    assert _calls(tmp_path)[0]["request_sha256"] == expected
    assert _calls(tmp_path)[0]["decision_type"] == "unknown_schema"


def test_concurrent_calls_each_log_their_own_thread_context(tmp_path: Path) -> None:
    class Slow:
        def complete_json(self, **kwargs: Any) -> str:
            time.sleep(0.01)
            return kwargs["user_prompt"]

    with CallLogWriter(tmp_path / CALL_LOG_FILENAME) as writer:
        client = CallLoggingClient(Slow(), writer, tick_source=lambda: 1)

        def worker(unit: int) -> None:
            with call_context(decision_type="vote_cast", unit_ids=[unit], attempt=0):
                client.complete_json(system_prompt="s", user_prompt=str(unit), json_schema={}, max_tokens=1)

        threads = [threading.Thread(target=worker, args=(unit,)) for unit in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    calls = _calls(tmp_path)
    assert len(calls) == 16
    assert all(call["unit_ids"] == [int(call["content"])] for call in calls)


def test_the_writer_never_fails_the_run(tmp_path: Path) -> None:
    blocked = tmp_path / "a-file"
    blocked.write_text("x", encoding="utf-8")
    with CallLogWriter(blocked / CALL_LOG_FILENAME) as unopenable:  # its parent is a file
        unopenable.write({"call_id": "a"})
    assert unopenable.calls == 0

    writer = CallLogWriter(tmp_path / CALL_LOG_FILENAME)

    class Broken:
        def write(self, text: str) -> int:
            raise OSError("disk full")

        def close(self) -> None:
            return None

    writer._handle = Broken()
    writer.write({"call_id": "a"})
    writer.write({"call_id": "b"})  # disabled after the first error, still silent
    writer.close()
    assert writer.calls == 0
    assert json.loads((tmp_path / CALL_LOG_SUMMARY_FILENAME).read_text(encoding="utf-8"))["writer_ms_mean"] is None


def test_call_logged_without_a_path_leaves_the_client_untouched() -> None:
    client = object()
    with call_logged(client, None, lambda: None) as logged:
        assert logged is client


def test_an_owned_client_logs_its_warm_up_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def fake_build(llm: Any, *, seed: int) -> Iterator[Any]:
        yield _ElectingFakeLlmClient()

    monkeypatch.setattr(run_polity_simulation_module, "build_json_client", fake_build)
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    with _llm_client_scope(config, None, None, call_log_path=tmp_path / CALL_LOG_FILENAME):
        pass
    calls = _calls(tmp_path)
    assert [(c["kind"], c["think"]) for c in calls] == [("warm_up", True), ("warm_up", False)]


class _EchoClient:
    def complete_json(self, **kwargs: Any) -> str:
        return '{"ok": true}'


def test_prompts_are_kept_only_when_asked_and_once_per_distinct_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request: dict[str, Any] = {"system_prompt": "S", "user_prompt": "U1", "json_schema": {"title": "T"}, "max_tokens": 10}
    monkeypatch.delenv(PROMPT_LOG_ENV, raising=False)
    with call_logged(_EchoClient(), tmp_path / CALL_LOG_FILENAME, lambda: 1) as client:
        client.complete_json(**request)
    assert not (tmp_path / PROMPT_LOG_FILENAME).exists()  # off unless asked

    (tmp_path / CALL_LOG_FILENAME).unlink()
    monkeypatch.setenv(PROMPT_LOG_ENV, "1")
    with call_logged(_EchoClient(), tmp_path / CALL_LOG_FILENAME, lambda: 1) as client:
        client.complete_json(**request)
        client.complete_json(**request)  # the same request again: a second call line, no second prompt line
        client.complete_json(**{**request, "user_prompt": "U2"})
    calls = _calls(tmp_path)
    prompts = read_prompts(tmp_path / PROMPT_LOG_FILENAME)
    assert len(calls) == 3 and len(prompts) == 2
    assert {p["user"] for p in prompts.values()} == {"U1", "U2"}
    assert all(p["system"] == "S" and p["schema"] == {"title": "T"} for p in prompts.values())
    assert set(prompts) == {c["call_id"] for c in calls}  # every call resolves to its prompts
    assert (tmp_path / PROMPT_LOG_FILENAME).read_text(encoding="utf-8").count('"text": "S"') == 1  # the shared system prompt, once
    assert not any({"system_prompt", "user_prompt"} & set(c) for c in calls)  # llm_calls.jsonl itself is unchanged


def test_the_prompts_sidecar_survives_bad_input_and_a_missing_directory(tmp_path: Path) -> None:
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("x", encoding="utf-8")
    unopenable = PromptLogWriter(blocker / PROMPT_LOG_FILENAME)  # cannot open: the sidecar disables itself
    unopenable.write("c1", system_prompt="S", user_prompt="U", json_schema=None)
    unopenable.close()

    path = tmp_path / PROMPT_LOG_FILENAME
    writer = PromptLogWriter(path)
    writer.write("c1", system_prompt="S", user_prompt="U", json_schema=None)  # a request without a schema
    writer.write("c2", system_prompt="S", user_prompt="U", json_schema={"x": object()})  # cannot be serialised: disables the sidecar
    writer.write("c3", system_prompt="S", user_prompt="U3", json_schema=None)  # ignored once disabled
    writer.close()
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n")  # a blank line, as a reader may meet after a crash
    assert read_prompts(path) == {"c1": {"system": "S", "user": "U", "schema": None}}
