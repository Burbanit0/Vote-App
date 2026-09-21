"""Model profiles (S2.3). See api/domain/polity/model_profiles.py."""
from __future__ import annotations

import dataclasses
import json
from typing import Any

import httpx
import pytest

from api.domain.polity import model_profiles
from api.domain.polity.config import PolityConfigError, load_config, validate_config
from api.domain.polity.llm_behavior_engine import _chamber_chunk_size, _dynamic_max_tokens, _vote_cast_chunk_size, compute_max_tokens
from api.domain.polity.llm_client import VllmJsonClient
from api.domain.polity.model_profiles import (
    QWEN3_8B_AWQ_VLLM,
    QWEN3_8B_OLLAMA,
    ThinkingControl,
    UnknownModelProfileError,
    model_profile,
)


def _llm_config(provider: str = "vllm", model: str = "qwen3:8b", **overrides: Any) -> Any:
    config = load_config()
    return dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True, provider=provider, model=model, **overrides))


@pytest.mark.parametrize(
    ("control", "on", "off"),
    [
        (ThinkingControl("chat_template_kwargs", key="enable_thinking"),
         {"chat_template_kwargs": {"enable_thinking": True}}, {"chat_template_kwargs": {"enable_thinking": False}}),
        (ThinkingControl("chat_template_kwargs", key="thinking"),
         {"chat_template_kwargs": {"thinking": True}}, {"chat_template_kwargs": {"thinking": False}}),
        (ThinkingControl("reasoning_effort", on="high", off="low"), {"reasoning_effort": "high"}, {"reasoning_effort": "low"}),
        (ThinkingControl("none"), {}, {}),
    ],
)
def test_each_thinking_control_writes_its_own_request_fields(control: ThinkingControl, on: dict[str, Any], off: dict[str, Any]) -> None:
    assert control.request_fields(True) == on
    assert control.request_fields(False) == off


def test_profiles_are_looked_up_by_provider_and_model() -> None:
    assert model_profile("vllm", "qwen3:8b") is QWEN3_8B_AWQ_VLLM
    assert model_profile("ollama", "qwen3:8b") is QWEN3_8B_OLLAMA
    with pytest.raises(UnknownModelProfileError, match="no model profile for 'gemma4:12b' on 'vllm'.*ollama/qwen3:8b, vllm/qwen3:8b"):
        model_profile("vllm", "gemma4:12b")


def test_the_precision_probe_profile_inherits_everything_but_the_weights() -> None:
    probe = model_profile("vllm", "qwen3:8b-nvfp4a16")
    assert probe.weights == "ELVISIO/Qwen3-8B-NVFP4A16"
    assert dataclasses.replace(probe, model=QWEN3_8B_AWQ_VLLM.model, weights=QWEN3_8B_AWQ_VLLM.weights) == QWEN3_8B_AWQ_VLLM


def test_an_llm_run_on_an_unprofiled_model_is_refused_by_validate_config() -> None:
    with pytest.raises(PolityConfigError, match="'llm.model' 'gemma4:12b' has no model profile on provider 'vllm'"):
        validate_config(_llm_config(model="gemma4:12b"))
    validate_config(dataclasses.replace(_llm_config(model="gemma4:12b"), llm=dataclasses.replace(_llm_config().llm, enabled=False, model="gemma4:12b")))
    # An unsupported provider is _check_supported's error to raise, with its own message. Its
    # thinking budget is null: a budget is a vLLM request field, refused on any other provider.
    validate_config(_llm_config(provider="api", model="whatever:1", thinking_token_budget=None))


def test_the_engine_reads_chunk_sizes_and_budgets_from_the_runs_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    probe = dataclasses.replace(
        QWEN3_8B_AWQ_VLLM, model="probe:1b", vote_cast_chunk_size=2, chamber_chunk_size=4, context_limit=8192,
    )
    monkeypatch.setitem(model_profiles.PROFILES, ("vllm", "probe:1b"), probe)
    config = _llm_config(model="probe:1b")
    assert (_vote_cast_chunk_size(config), _chamber_chunk_size(config)) == (2, 4)
    assert (_vote_cast_chunk_size(_llm_config()), _chamber_chunk_size(_llm_config())) == (3, 5)
    assert (_vote_cast_chunk_size(_llm_config(provider="ollama")), _chamber_chunk_size(_llm_config(provider="ollama"))) == (1, 1)

    class Probe:
        def count_prompt_tokens(self, **kwargs: Any) -> int:
            return 1000

    budget = _dynamic_max_tokens(Probe(), config, system_prompt="s", user_prompt="u", chunk_size=2, flat_allowance=500)  # type: ignore[arg-type]
    assert budget == 8192 - 1000 - 300
    unprobed = dataclasses.replace(probe, model="flat:1b", probe_token_budget=False)
    monkeypatch.setitem(model_profiles.PROFILES, ("vllm", "flat:1b"), unprobed)
    flat = _dynamic_max_tokens(Probe(), _llm_config(model="flat:1b"), system_prompt="s", user_prompt="u", chunk_size=2, flat_allowance=500)  # type: ignore[arg-type]
    assert flat == compute_max_tokens(2) + 500


def _captured_bodies(client_factory: Any) -> list[dict[str, Any]]:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}], "usage": {"prompt_tokens": 9}})

    client = client_factory(httpx.MockTransport(handler))
    client.complete_json(system_prompt="s", user_prompt="u", json_schema={"type": "object"}, max_tokens=64, think=False)
    client.count_prompt_tokens(system_prompt="s", user_prompt="u", think=True)
    return bodies


def test_the_qwen_request_body_is_pinned_byte_for_byte() -> None:
    # S2.3's acceptance: Qwen requests unchanged by model profiles. Checked when the change
    # was made against payloads captured from the previous client; pinned here so a later
    # change to the thinking switch cannot drift silently.
    payloads: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(request.content.decode())
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})

    client = VllmJsonClient.from_config(_llm_config().llm, seed=42)
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    client.complete_json(system_prompt="s", user_prompt="u", json_schema={"type": "object"}, max_tokens=64, think=True)
    assert payloads == [
        '{"chat_template_kwargs":{"enable_thinking":true},"max_tokens":64,"messages":[{"content":"s","role":"system"},'
        '{"content":"u","role":"user"}],"model":"qwen3:8b","response_format":{"json_schema":{"name":"polity_decision_batch",'
        '"schema":{"type":"object"},"strict":true},"type":"json_schema"},"seed":42,"stream":false,"temperature":0.0}'
    ]


def test_a_non_qwen_profile_changes_only_the_thinking_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    effort = dataclasses.replace(QWEN3_8B_AWQ_VLLM, model="effort:20b", thinking=ThinkingControl("reasoning_effort", on="high", off="low"))
    silent = dataclasses.replace(QWEN3_8B_AWQ_VLLM, model="plain:12b", thinking=ThinkingControl("none"))
    monkeypatch.setitem(model_profiles.PROFILES, ("vllm", "effort:20b"), effort)
    monkeypatch.setitem(model_profiles.PROFILES, ("vllm", "plain:12b"), silent)

    def client_for(model: str) -> Any:
        return lambda transport: VllmJsonClient(
            "http://vllm.test/v1", model, 0.0, 42, 5.0, transport=transport,
            thinking=model_profile("vllm", model).thinking,
        )

    qwen = _captured_bodies(client_for("qwen3:8b"))
    with_effort = _captured_bodies(client_for("effort:20b"))
    without = _captured_bodies(client_for("plain:12b"))
    assert [b["reasoning_effort"] for b in with_effort] == ["low", "high"]
    assert all("chat_template_kwargs" not in b and "reasoning_effort" not in b for b in without)
    strip = {"chat_template_kwargs", "reasoning_effort", "model"}
    assert [{k: v for k, v in b.items() if k not in strip} for b in with_effort] == [{k: v for k, v in b.items() if k not in strip} for b in qwen]
    assert VllmJsonClient.from_config(_llm_config(model="effort:20b").llm, seed=1)._thinking == effort.thinking
