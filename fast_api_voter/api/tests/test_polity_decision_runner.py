"""The decision runner (S3.2). See llm_behavior_engine.run_decision."""
from __future__ import annotations

import dataclasses
import json
from typing import Any

from api.domain.polity.citizen import generate_population
from api.domain.polity.config import load_config
from api.domain.polity.llm_behavior_engine import DecisionSpec, run_decision
from api.domain.polity.llm_client import LlmResponseError, decode_candidacy_batch
from api.domain.polity.llm_schemas import CANDIDACY_JSON_SCHEMA, CandidacyDecision


class _ScriptedClient:
    """Answers each call with the next scripted function of the user prompt."""

    def __init__(self, *answers: Any) -> None:
        self._answers = list(answers)
        self.calls = 0

    def complete_json(self, **kwargs: Any) -> str:
        answer = self._answers[min(self.calls, len(self._answers) - 1)]
        self.calls += 1
        return str(answer(kwargs["user_prompt"]))


def _declare_all(user_prompt: str) -> str:
    return json.dumps({"decisions": [{"cid": cid, "outcome": 1, "motif": 203} for cid in json.loads(user_prompt)]})


def _spec(**overrides: Any) -> DecisionSpec[CandidacyDecision]:
    fields: dict[str, Any] = dict(
        decision_type="candidacy_considered", json_schema=CANDIDACY_JSON_SCHEMA, think=False,
        retry_temperature=0.3, retry_seed_base=1000, chunk_size=2, min_batch_size=1,
        system_prompt=lambda chunk: "decide",
        user_prompt=lambda chunk: json.dumps([c.citizen_id for c in chunk]),
        decode=decode_candidacy_batch,
        fallback=lambda chunk: [CandidacyDecision(cid=c.citizen_id, outcome=0, motif=201) for c in chunk],
        fallback_description="a test fallback",
    )
    return DecisionSpec[CandidacyDecision](**{**fields, **overrides})


def _config(replays: int = 0) -> Any:
    config = load_config()
    return dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True, max_batch_replays=replays))


def test_decisions_come_back_in_citizen_order_with_clean_provenance() -> None:
    citizens = generate_population(load_config().citizens, 5, seed=3)
    result = run_decision(_spec(), citizens, _config(), _ScriptedClient(_declare_all))  # type: ignore[arg-type]
    assert [d.cid for d in result.decisions] == [c.citizen_id for c in citizens]
    assert result.llm_fallback == {}
    assert set(result.retry_sampling_varied.values()) == {False}
    assert len(set(result.llm_call_ids.values())) == 3  # chunks of 2, 2, 1: one call each


def test_a_decision_the_validator_rejects_sends_only_its_chunk_to_the_fallback(caplog: Any) -> None:
    citizens = generate_population(load_config().citizens, 4, seed=3)
    rejected = citizens[0].citizen_id

    def validate(decision: CandidacyDecision) -> None:
        if decision.cid == rejected:
            raise LlmResponseError("not allowed")

    result = run_decision(_spec(validate=validate), citizens, _config(), _ScriptedClient(_declare_all))  # type: ignore[arg-type]
    first_chunk = {c.citizen_id for c in citizens[:2]}
    assert set(result.llm_fallback) == first_chunk
    assert {d.cid: d.outcome for d in result.decisions} == {c.citizen_id: 0 if c.citizen_id in first_chunk else 1 for c in citizens}
    assert "candidacy_considered: exhausted every recovery attempt" in caplog.text and "a test fallback" in caplog.text


def test_a_recovered_retry_is_marked_on_its_chunk_only() -> None:
    citizens = generate_population(load_config().citizens, 4, seed=3)
    client = _ScriptedClient(lambda prompt: "not json", _declare_all)
    result = run_decision(_spec(), citizens, _config(replays=1), client)  # type: ignore[arg-type]
    assert client.calls == 3
    marked = {cid for cid, varied in result.retry_sampling_varied.items() if varied}
    assert marked == {c.citizen_id for c in citizens[:2]}
    assert result.llm_fallback == {}
