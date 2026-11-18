"""The vLLM client's grammar mode (llm_client.wire_grammar) and its generated artifact, wire_grammars.json."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from api.domain.polity.llm_client import _WIRE_GRAMMARS_PATH, WIRE_ORDER, VllmJsonClient, wire_grammar
from api.domain.polity.llm_schemas import RESPONSE_JSON_SCHEMA

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "gen_wire_grammars.py"
_spec = importlib.util.spec_from_file_location("gen_wire_grammars", SCRIPT)
assert _spec is not None and _spec.loader is not None
generator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generator)


def _bodies(mode: str, schema: dict[str, Any]) -> dict[str, Any]:
    sent: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})

    client = VllmJsonClient("http://localhost:8000/v1", "qwen3:8b", 0.0, seed=42, timeout=5.0, transport=httpx.MockTransport(handler))
    client.structured_output = mode  # type: ignore[assignment]
    client.complete_json(system_prompt="s", user_prompt="u", json_schema=schema, max_tokens=64)
    return sent[0]


def test_the_artifact_holds_exactly_the_schemas_the_client_can_send() -> None:
    """A schema, a field order or a bake-off arm changed without `python scripts/gen_wire_grammars.py` fails here."""
    committed = json.loads(_WIRE_GRAMMARS_PATH.read_text(encoding="utf-8"))["grammars"]
    assert set(generator.wire_schemas()) == set(committed)


def test_grammar_mode_sends_the_grammar_in_place_of_the_schema_and_nothing_else_changes() -> None:
    as_schema, as_grammar = _bodies("schema", RESPONSE_JSON_SCHEMA), _bodies("grammar", RESPONSE_JSON_SCHEMA)
    assert "structured_outputs" not in as_schema and "response_format" not in as_grammar
    assert as_grammar["structured_outputs"] == {"grammar": wire_grammar(RESPONSE_JSON_SCHEMA, WIRE_ORDER)}
    assert {k: v for k, v in as_schema.items() if k != "response_format"} == {k: v for k, v in as_grammar.items() if k != "structured_outputs"}


def test_the_grammar_carries_the_spacing_and_the_wire_order() -> None:
    grammar = wire_grammar(RESPONSE_JSON_SCHEMA, WIRE_ORDER)
    assert '", "' in grammar and '": "' in grammar  # the separators vLLM 0.31 wrote, now ours
    assert grammar != wire_grammar(RESPONSE_JSON_SCHEMA, {})  # the alphabetical order is another grammar


def test_a_schema_with_no_grammar_is_an_error_not_a_fall_back_to_the_servers_spacing() -> None:
    with pytest.raises(LookupError, match="gen_wire_grammars.py"):
        _bodies("grammar", {"type": "object", "title": "NotGenerated", "properties": {"x": {"type": "integer"}}})
