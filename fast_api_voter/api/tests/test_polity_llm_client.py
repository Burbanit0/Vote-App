"""llm_client.py — sync Ollama transport + batch envelope decoding.
No real network: httpx.MockTransport exercises the actual request/response
handling (URL, headers, body shape, retry policy) without a live model.
"""
import dataclasses
import json

import httpx
import pytest

from api.domain.polity.llm_client import (
    LlmResponseError,
    LlmTransportError,
    OllamaJsonClient,
    VllmJsonClient,
    build_json_client,
    decode_candidacy_batch,
    decode_coalition_batch,
    decode_party_nomination_batch,
    decode_positioning_batch,
    decode_pressure_batch,
    decode_response_batch,
    decode_vote_batch,
)
from api.domain.polity.config import load_config

BASE_URL = "http://localhost:11434/v1"
VLLM_BASE_URL = "http://localhost:8000/v1"


def _client(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    return OllamaJsonClient(BASE_URL, "qwen3:8b", 0.0, seed=42, timeout=5.0, transport=transport, **kwargs)


def _vllm_client(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    return VllmJsonClient(VLLM_BASE_URL, "qwen3:8b", 0.0, seed=42, timeout=5.0, transport=transport, **kwargs)


def _ok_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"finish_reason": "stop", "message": {"content": content}}]},
    )


def test_request_shape_is_correct():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return _ok_response('{"decisions": []}')

    client = _client(handler)
    client.complete_json(system_prompt="sys", user_prompt="usr", json_schema={"type": "object"}, max_tokens=64)

    assert captured["url"] == f"{BASE_URL}/chat/completions"
    body = captured["body"]
    assert body["model"] == "qwen3:8b"
    assert body["temperature"] == 0.0
    assert body["seed"] == 42
    assert body["stream"] is False
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == {"type": "object"}


def test_nested_ref_schema_is_dereferenced_before_sending():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["schema"] = json.loads(request.content)["response_format"]["json_schema"]["schema"]
        return _ok_response('{"decisions": []}')

    schema = {
        "$defs": {"Inner": {"type": "object", "properties": {"x": {"type": "integer"}}}},
        "type": "object",
        "properties": {"item": {"$ref": "#/$defs/Inner"}},
    }
    client = _client(handler)
    client.complete_json(system_prompt="s", user_prompt="u", json_schema=schema, max_tokens=64)

    sent = captured["schema"]
    assert "$defs" not in sent
    assert sent["properties"]["item"] == {"type": "object", "properties": {"x": {"type": "integer"}}}


def test_successful_response_returns_content():
    client = _client(lambda request: _ok_response('{"decisions": [{"cid": 1}]}'))
    content = client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert content == '{"decisions": [{"cid": 1}]}'


def test_http_500_retries_then_raises_transport_error():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(500, text="server error")

    client = _client(handler)
    with pytest.raises(LlmTransportError):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert calls["count"] == 3


def test_connect_error_retries_then_raises_transport_error():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.ConnectError("refused")

    client = _client(handler)
    with pytest.raises(LlmTransportError):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert calls["count"] == 3


def test_transport_error_recovers_if_a_later_attempt_succeeds():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 2:
            return httpx.Response(500, text="transient")
        return _ok_response('{"decisions": []}')

    client = _client(handler)
    content = client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert content == '{"decisions": []}'
    assert calls["count"] == 2


def test_truncated_generation_raises_response_error_without_retry():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(
            200, json={"choices": [{"finish_reason": "length", "message": {"content": ""}}]}
        )

    client = _client(handler)
    with pytest.raises(LlmResponseError, match="finish_reason"):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert calls["count"] == 1


def test_non_json_response_body_raises_response_error():
    client = _client(lambda request: httpx.Response(200, text="not json"))
    with pytest.raises(LlmResponseError):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)


def test_missing_choices_raises_response_error():
    client = _client(lambda request: httpx.Response(200, json={}))
    with pytest.raises(LlmResponseError, match="choices"):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)


# ── OllamaJsonClient, think=False (native /api/chat path) ────────────────
# No prior offline coverage of this path existed (only the think=True
# OpenAI-compat path above was tested without a live server) -- these
# characterize the shipped behavior before llm_client.py's shared retry
# loop is extracted, so the extraction is provably behavior-preserving.

def _ok_native_response(content: str) -> httpx.Response:
    return httpx.Response(200, json={"done_reason": "stop", "message": {"content": content}})


def test_native_endpoint_is_used_when_think_is_false():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return _ok_native_response('{"decisions": []}')

    client = _client(handler)
    client.complete_json(
        system_prompt="sys", user_prompt="usr", json_schema={"type": "object"}, max_tokens=64, think=False
    )

    assert captured["url"] == "http://localhost:11434/api/chat"


def test_native_request_shape_is_correct():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return _ok_native_response('{"decisions": []}')

    client = _client(handler)
    client.complete_json(system_prompt="sys", user_prompt="usr", json_schema={"type": "object"}, max_tokens=64, think=False)

    body = captured["body"]
    assert body["model"] == "qwen3:8b"
    assert body["stream"] is False
    assert body["think"] is False
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert body["format"] == {"type": "object"}
    assert body["options"] == {"temperature": 0.0, "seed": 42, "num_predict": 64}
    # No response_format/chat_template_kwargs on the native path -- that
    # shape belongs to the OpenAI-compat (think=True) request only.
    assert "response_format" not in body
    assert "chat_template_kwargs" not in body


def test_native_done_reason_not_stop_raises_without_retry():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"done_reason": "length", "message": {"content": ""}})

    client = _client(handler)
    with pytest.raises(LlmResponseError, match="done_reason"):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64, think=False)
    assert calls["count"] == 1


def test_native_http_500_retries_then_raises_transport_error():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(500, text="server error")

    client = _client(handler)
    with pytest.raises(LlmTransportError):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64, think=False)
    assert calls["count"] == 3


# ── VllmJsonClient (v4 vLLM switch, §15bis.6) ─────────────────────────────
# UNVERIFIED against a live server -- see VllmJsonClient's own docstring.
# These pin the request/response SHAPE this codebase sends and expects;
# they cannot confirm vLLM actually behaves this way.

def test_vllm_request_shape_is_correct():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return _ok_response('{"decisions": []}')

    client = _vllm_client(handler)
    client.complete_json(system_prompt="sys", user_prompt="usr", json_schema={"type": "object"}, max_tokens=64)

    assert captured["url"] == f"{VLLM_BASE_URL}/chat/completions"
    body = captured["body"]
    assert body["model"] == "qwen3:8b"
    assert body["temperature"] == 0.0
    assert body["seed"] == 42
    assert body["stream"] is False
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == {"type": "object"}


def test_vllm_think_true_sets_enable_thinking_true():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return _ok_response('{"decisions": []}')

    client = _vllm_client(handler)
    client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64, think=True)

    assert captured["body"]["chat_template_kwargs"] == {"enable_thinking": True}


def test_vllm_think_false_keeps_the_same_endpoint_and_sets_enable_thinking_false():
    """The executable pin for the design's central claim: unlike Ollama,
    vLLM does NOT switch endpoints for think=False -- see
    test_native_endpoint_is_used_when_think_is_false above for the contrast."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return _ok_response('{"decisions": []}')

    client = _vllm_client(handler)
    client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64, think=False)

    assert captured["url"] == f"{VLLM_BASE_URL}/chat/completions"
    assert captured["body"]["chat_template_kwargs"] == {"enable_thinking": False}


def test_vllm_nested_ref_schema_is_dereferenced_before_sending():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["schema"] = json.loads(request.content)["response_format"]["json_schema"]["schema"]
        return _ok_response('{"decisions": []}')

    schema = {
        "$defs": {"Inner": {"type": "object", "properties": {"x": {"type": "integer"}}}},
        "type": "object",
        "properties": {"item": {"$ref": "#/$defs/Inner"}},
    }
    client = _vllm_client(handler)
    client.complete_json(system_prompt="s", user_prompt="u", json_schema=schema, max_tokens=64)

    sent = captured["schema"]
    assert "$defs" not in sent
    assert sent["properties"]["item"] == {"type": "object", "properties": {"x": {"type": "integer"}}}


def test_vllm_sends_the_same_schema_as_the_ollama_client():
    schema = {
        "$defs": {"Inner": {"type": "object"}},
        "type": "object",
        "properties": {"item": {"$ref": "#/$defs/Inner"}},
    }
    captured = {}

    def ollama_handler(request: httpx.Request) -> httpx.Response:
        captured["ollama"] = json.loads(request.content)["response_format"]["json_schema"]["schema"]
        return _ok_response('{"decisions": []}')

    def vllm_handler(request: httpx.Request) -> httpx.Response:
        captured["vllm"] = json.loads(request.content)["response_format"]["json_schema"]["schema"]
        return _ok_response('{"decisions": []}')

    _client(ollama_handler).complete_json(system_prompt="s", user_prompt="u", json_schema=schema, max_tokens=64)
    _vllm_client(vllm_handler).complete_json(system_prompt="s", user_prompt="u", json_schema=schema, max_tokens=64)

    assert captured["ollama"] == captured["vllm"]


def test_vllm_payload_is_canonical_sorted_and_compact():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["raw"] = request.content
        return _ok_response('{"decisions": []}')

    client = _vllm_client(handler)
    client.complete_json(system_prompt="s", user_prompt="u", json_schema={"b": 1, "a": 2}, max_tokens=64)

    raw = captured["raw"]
    assert b", " not in raw and b": " not in raw  # compact separators
    reparsed = json.loads(raw)
    assert json.dumps(reparsed, sort_keys=True, separators=(",", ":")).encode() == raw  # already sorted


def test_vllm_successful_response_returns_content():
    client = _vllm_client(lambda request: _ok_response('{"decisions": [{"cid": 1}]}'))
    content = client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert content == '{"decisions": [{"cid": 1}]}'


def test_vllm_returns_content_when_reasoning_content_is_also_present():
    """The shape vLLM's --reasoning-parser produces: reasoning moved to its
    own field, message.content left as pure JSON. _extract_content only
    ever reads .content, so this should already work unmodified."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"decisions": []}', "reasoning_content": "because..."},
                    }
                ]
            },
        )

    client = _vllm_client(handler)
    content = client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert content == '{"decisions": []}'


def test_vllm_http_500_retries_then_raises_transport_error():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(500, text="server error")

    client = _vllm_client(handler)
    with pytest.raises(LlmTransportError):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert calls["count"] == 3


def test_vllm_connect_error_retries_then_raises_transport_error():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.ConnectError("refused")

    client = _vllm_client(handler)
    with pytest.raises(LlmTransportError):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert calls["count"] == 3


def test_vllm_transport_error_recovers_if_a_later_attempt_succeeds():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 2:
            return httpx.Response(500, text="transient")
        return _ok_response('{"decisions": []}')

    client = _vllm_client(handler)
    content = client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert content == '{"decisions": []}'
    assert calls["count"] == 2


def test_vllm_truncated_generation_raises_response_error_without_retry():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": ""}}]})

    client = _vllm_client(handler)
    with pytest.raises(LlmResponseError, match="finish_reason"):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)
    assert calls["count"] == 1


def test_vllm_non_json_response_body_raises_response_error():
    client = _vllm_client(lambda request: httpx.Response(200, text="not json"))
    with pytest.raises(LlmResponseError):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)


def test_vllm_missing_choices_raises_response_error():
    client = _vllm_client(lambda request: httpx.Response(200, json={}))
    with pytest.raises(LlmResponseError, match="choices"):
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=64)


# ── build_json_client (provider dispatch) ─────────────────────────────────

def test_build_json_client_returns_an_ollama_client_for_the_ollama_provider():
    config = load_config()
    with build_json_client(config.llm, seed=42) as client:
        assert isinstance(client, OllamaJsonClient)


def test_build_json_client_returns_a_vllm_client_for_the_vllm_provider():
    config = load_config()
    llm = dataclasses.replace(config.llm, provider="vllm")
    with build_json_client(llm, seed=42) as client:
        assert isinstance(client, VllmJsonClient)


def test_build_json_client_rejects_the_api_provider():
    config = load_config()
    llm = dataclasses.replace(config.llm, provider="api")
    with pytest.raises(NotImplementedError, match="provider"):
        build_json_client(llm, seed=42)


# ── decode_vote_batch ─────────────────────────────────────────────────────

def _decision(**overrides):
    base = {"cid": 1, "blank": 0, "ranking": [10], "motif": 101}
    base.update(overrides)
    return base


def test_decode_vote_batch_round_trips():
    raw = json.dumps({"decisions": [_decision(cid=1), _decision(cid=2)]})
    decisions = decode_vote_batch(raw, expected_cids=[1, 2])
    assert [d.cid for d in decisions] == [1, 2]


def test_decode_vote_batch_rejects_non_json():
    with pytest.raises(LlmResponseError, match="not valid JSON"):
        decode_vote_batch("not json", expected_cids=[1])


def test_decode_vote_batch_rejects_schema_invalid_content():
    raw = json.dumps({"decisions": [{"cid": 1, "blank": 1, "ranking": [10], "motif": 101}]})  # blank=1 with ranking
    with pytest.raises(LlmResponseError, match="schema validation"):
        decode_vote_batch(raw, expected_cids=[1])


def test_decode_vote_batch_rejects_count_mismatch():
    raw = json.dumps({"decisions": [_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_vote_batch(raw, expected_cids=[1, 2])


def test_decode_vote_batch_rejects_order_mismatch():
    raw = json.dumps({"decisions": [_decision(cid=2), _decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_vote_batch(raw, expected_cids=[1, 2])


def test_decode_vote_batch_strips_think_tags():
    raw = "<think>reasoning here</think>" + json.dumps({"decisions": [_decision(cid=1)]})
    decisions = decode_vote_batch(raw, expected_cids=[1])
    assert decisions[0].cid == 1


# ── decode_candidacy_batch ────────────────────────────────────────────────

def _candidacy_decision(**overrides):
    base = {"cid": 1, "outcome": 1, "motif": 203}
    base.update(overrides)
    return base


def test_decode_candidacy_batch_round_trips():
    raw = json.dumps({"decisions": [_candidacy_decision(cid=1), _candidacy_decision(cid=2)]})
    decisions = decode_candidacy_batch(raw, expected_cids=[1, 2])
    assert [d.cid for d in decisions] == [1, 2]


def test_decode_candidacy_batch_rejects_non_json():
    with pytest.raises(LlmResponseError, match="not valid JSON"):
        decode_candidacy_batch("not json", expected_cids=[1])


def test_decode_candidacy_batch_rejects_schema_invalid_content():
    raw = json.dumps({"decisions": [{"cid": 1, "outcome": 1, "motif": 202}]})  # 202 reserved for rupture
    with pytest.raises(LlmResponseError, match="schema validation"):
        decode_candidacy_batch(raw, expected_cids=[1])


def test_decode_candidacy_batch_rejects_count_mismatch():
    raw = json.dumps({"decisions": [_candidacy_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_candidacy_batch(raw, expected_cids=[1, 2])


def test_decode_candidacy_batch_rejects_order_mismatch():
    raw = json.dumps({"decisions": [_candidacy_decision(cid=2), _candidacy_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_candidacy_batch(raw, expected_cids=[1, 2])


def test_decode_candidacy_batch_strips_think_tags():
    raw = "<think>reasoning here</think>" + json.dumps({"decisions": [_candidacy_decision(cid=1)]})
    decisions = decode_candidacy_batch(raw, expected_cids=[1])
    assert decisions[0].cid == 1


# ── decode_party_nomination_batch ─────────────────────────────────────────

def _nomination_decision(**overrides):
    base = {"party_id": 0, "winner_position": 1, "motif": 206}
    base.update(overrides)
    return base


def test_decode_party_nomination_batch_round_trips():
    raw = json.dumps({"decisions": [_nomination_decision(party_id=0), _nomination_decision(party_id=1)]})
    decisions = decode_party_nomination_batch(raw, expected_party_ids=[0, 1])
    assert [d.party_id for d in decisions] == [0, 1]


def test_decode_party_nomination_batch_rejects_non_json():
    with pytest.raises(LlmResponseError, match="not valid JSON"):
        decode_party_nomination_batch("not json", expected_party_ids=[0])


def test_decode_party_nomination_batch_rejects_schema_invalid_content():
    raw = json.dumps({"decisions": [{"party_id": 0, "winner_position": 0, "motif": 206}]})  # position must be >=1
    with pytest.raises(LlmResponseError, match="schema validation"):
        decode_party_nomination_batch(raw, expected_party_ids=[0])


def test_decode_party_nomination_batch_rejects_count_mismatch():
    raw = json.dumps({"decisions": [_nomination_decision(party_id=0)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_party_nomination_batch(raw, expected_party_ids=[0, 1])


def test_decode_party_nomination_batch_rejects_order_mismatch():
    raw = json.dumps({"decisions": [_nomination_decision(party_id=1), _nomination_decision(party_id=0)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_party_nomination_batch(raw, expected_party_ids=[0, 1])


def test_decode_party_nomination_batch_strips_think_tags():
    raw = "<think>reasoning here</think>" + json.dumps({"decisions": [_nomination_decision(party_id=0)]})
    decisions = decode_party_nomination_batch(raw, expected_party_ids=[0])
    assert decisions[0].party_id == 0


# ── decode_positioning_batch ──────────────────────────────────────────────

def _positioning_decision(**overrides):
    base = {"cid": 1, "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 602}
    base.update(overrides)
    return base


def test_decode_positioning_batch_round_trips():
    raw = json.dumps({"decisions": [_positioning_decision(cid=1), _positioning_decision(cid=2, shifts=[])]})
    decisions = decode_positioning_batch(raw, expected_cids=[1, 2])
    assert [d.cid for d in decisions] == [1, 2]


def test_decode_positioning_batch_rejects_non_json():
    with pytest.raises(LlmResponseError, match="not valid JSON"):
        decode_positioning_batch("not json", expected_cids=[1])


def test_decode_positioning_batch_rejects_schema_invalid_content():
    raw = json.dumps(
        {"decisions": [{"cid": 1, "shifts": [{"dimension": 0, "delta": 0.1}, {"dimension": 0, "delta": -0.1}], "motif": 602}]}
    )  # duplicate dimension
    with pytest.raises(LlmResponseError, match="schema validation"):
        decode_positioning_batch(raw, expected_cids=[1])


def test_decode_positioning_batch_rejects_count_mismatch():
    raw = json.dumps({"decisions": [_positioning_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_positioning_batch(raw, expected_cids=[1, 2])


def test_decode_positioning_batch_rejects_order_mismatch():
    raw = json.dumps({"decisions": [_positioning_decision(cid=2), _positioning_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_positioning_batch(raw, expected_cids=[1, 2])


def test_decode_positioning_batch_strips_think_tags():
    raw = "<think>reasoning here</think>" + json.dumps({"decisions": [_positioning_decision(cid=1)]})
    decisions = decode_positioning_batch(raw, expected_cids=[1])
    assert decisions[0].cid == 1


# ── decode_response_batch (v4 Lot 6) ─────────────────────────────────────

def _response_decision(**overrides):
    base = {"cid": 1, "shifts": [{"dimension": 0, "delta": 0.1}], "stance": 1, "motif": 301}
    base.update(overrides)
    return base


def test_decode_response_batch_round_trips():
    raw = json.dumps(
        {"decisions": [_response_decision(cid=1), _response_decision(cid=2, shifts=[], stance=3, motif=308)]}
    )
    decisions = decode_response_batch(raw, expected_cids=[1, 2])
    assert [d.cid for d in decisions] == [1, 2]


def test_decode_response_batch_rejects_non_json():
    with pytest.raises(LlmResponseError, match="not valid JSON"):
        decode_response_batch("not json", expected_cids=[1])


def test_decode_response_batch_rejects_schema_invalid_content():
    raw = json.dumps({"decisions": [{"cid": 1, "shifts": [], "stance": 3, "motif": 301}]})  # silence w/ concession motif
    with pytest.raises(LlmResponseError, match="schema validation"):
        decode_response_batch(raw, expected_cids=[1])


def test_decode_response_batch_rejects_count_mismatch():
    raw = json.dumps({"decisions": [_response_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_response_batch(raw, expected_cids=[1, 2])


def test_decode_response_batch_rejects_order_mismatch():
    raw = json.dumps({"decisions": [_response_decision(cid=2), _response_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_response_batch(raw, expected_cids=[1, 2])


def test_decode_response_batch_rejects_a_duplicated_cid():
    raw = json.dumps({"decisions": [_response_decision(cid=1), _response_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_response_batch(raw, expected_cids=[1, 2])


def test_decode_response_batch_strips_think_tags():
    raw = "<think>reasoning here</think>" + json.dumps({"decisions": [_response_decision(cid=1)]})
    decisions = decode_response_batch(raw, expected_cids=[1])
    assert decisions[0].cid == 1


# ── decode_pressure_batch (v4 Lot 7) ──────────────────────────────────────

def _pressure_decision(**overrides):
    base = {"cid": 1, "target": 205, "act": 3, "motif": 301}
    base.update(overrides)
    return base


def test_decode_pressure_batch_round_trips():
    raw = json.dumps({"decisions": [_pressure_decision(cid=1), _pressure_decision(cid=2, act=0, motif=304)]})
    decisions = decode_pressure_batch(raw, expected_cids=[1, 2])
    assert [d.cid for d in decisions] == [1, 2]


def test_decode_pressure_batch_rejects_non_json():
    with pytest.raises(LlmResponseError, match="not valid JSON"):
        decode_pressure_batch("not json", expected_cids=[1])


def test_decode_pressure_batch_rejects_schema_invalid_content():
    raw = json.dumps({"decisions": [{"cid": 1, "target": 205, "act": 3, "motif": 303}]})  # 303 is a ResponseMotif
    with pytest.raises(LlmResponseError, match="schema validation"):
        decode_pressure_batch(raw, expected_cids=[1])


def test_decode_pressure_batch_rejects_count_mismatch():
    raw = json.dumps({"decisions": [_pressure_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_pressure_batch(raw, expected_cids=[1, 2])


def test_decode_pressure_batch_rejects_order_mismatch():
    raw = json.dumps({"decisions": [_pressure_decision(cid=2), _pressure_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_pressure_batch(raw, expected_cids=[1, 2])


def test_decode_pressure_batch_rejects_a_duplicated_cid():
    raw = json.dumps({"decisions": [_pressure_decision(cid=1), _pressure_decision(cid=1)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_pressure_batch(raw, expected_cids=[1, 2])


def test_decode_pressure_batch_strips_think_tags():
    raw = "<think>reasoning here</think>" + json.dumps({"decisions": [_pressure_decision(cid=1)]})
    decisions = decode_pressure_batch(raw, expected_cids=[1])
    assert decisions[0].cid == 1


# ── decode_coalition_batch ────────────────────────────────────────────────

def _coalition_decision(**overrides):
    base = {"party_id": 0, "action": 1, "motif": 501}
    base.update(overrides)
    return base


def test_decode_coalition_batch_round_trips():
    raw = json.dumps({"decisions": [_coalition_decision(party_id=0), _coalition_decision(party_id=1)]})
    decisions = decode_coalition_batch(raw, expected_party_ids=[0, 1])
    assert [d.party_id for d in decisions] == [0, 1]


def test_decode_coalition_batch_rejects_non_json():
    with pytest.raises(LlmResponseError, match="not valid JSON"):
        decode_coalition_batch("not json", expected_party_ids=[0])


def test_decode_coalition_batch_rejects_schema_invalid_content():
    raw = json.dumps({"decisions": [{"party_id": 0, "action": 1, "motif": 504}]})  # join with a decline motif
    with pytest.raises(LlmResponseError, match="schema validation"):
        decode_coalition_batch(raw, expected_party_ids=[0])


def test_decode_coalition_batch_rejects_count_mismatch():
    raw = json.dumps({"decisions": [_coalition_decision(party_id=0)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_coalition_batch(raw, expected_party_ids=[0, 1])


def test_decode_coalition_batch_rejects_order_mismatch():
    raw = json.dumps({"decisions": [_coalition_decision(party_id=1), _coalition_decision(party_id=0)]})
    with pytest.raises(LlmResponseError, match="misaligned"):
        decode_coalition_batch(raw, expected_party_ids=[0, 1])


def test_decode_coalition_batch_strips_think_tags():
    raw = "<think>reasoning here</think>" + json.dumps({"decisions": [_coalition_decision(party_id=0)]})
    decisions = decode_coalition_batch(raw, expected_party_ids=[0])
    assert decisions[0].party_id == 0
