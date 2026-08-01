"""llm_client.py — sync Ollama transport + batch envelope decoding.
No real network: httpx.MockTransport exercises the actual request/response
handling (URL, headers, body shape, retry policy) without a live model.
"""
import json

import httpx
import pytest

from api.domain.polity.llm_client import (
    LlmResponseError,
    LlmTransportError,
    OllamaJsonClient,
    decode_vote_batch,
)

BASE_URL = "http://localhost:11434/v1"


def _client(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    return OllamaJsonClient(BASE_URL, "qwen3:8b", 0.0, seed=42, timeout=5.0, transport=transport, **kwargs)


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
