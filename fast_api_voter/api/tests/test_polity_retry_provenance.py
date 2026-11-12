"""Retry provenance (S0.3): every LLM decision journals `retry_sampling_varied`,
1 when a varied-sampling retry produced it. Before this, only vote_cast and
chamber_deliberation carried the flag, so progress.json's retry_count read 0 for
the seven other types whatever actually happened.

Runs the golden scenario, which is known to reach all nine decision types
(test_polity_golden.py checks it), so a type that stops being exercised fails
here too instead of passing vacuously."""
from __future__ import annotations

import dataclasses
import json
from collections import Counter
from pathlib import Path
from typing import Any

from api.domain.polity.config import PolityConfig
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.polity_golden import LLM_DECISION_TYPES, decision_type_for_schema, golden_config
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient, _events


class _FirstCallOfEachTypeFailsClient:
    """Answers malformed JSON to the first call of every decision type, then
    delegates. Each type's second call is the retry that recovers the first, so
    the number of decisions it returns is the number of events that must carry
    retry_sampling_varied=1 for that type."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.calls: Counter[str] = Counter()
        self.recovered_decisions: dict[str, int] = {}

    def count_prompt_tokens(self, **kwargs: Any) -> int:
        return int(self._inner.count_prompt_tokens(**kwargs))

    def complete_json(self, *, json_schema: dict[str, Any], **kwargs: Any) -> str:
        decision_type = decision_type_for_schema(json_schema)
        self.calls[decision_type] += 1
        if self.calls[decision_type] == 1:
            return "not valid json"
        raw = str(self._inner.complete_json(json_schema=json_schema, **kwargs))
        if self.calls[decision_type] == 2:
            self.recovered_decisions[decision_type] = len(self._decisions(raw))
        return raw

    def _decisions(self, raw: str) -> list[Any]:
        return list(json.loads(raw)["decisions"])


class _RetryDecodesButFailsValidationClient(_FirstCallOfEachTypeFailsClient):
    """Same first-call failure, but vote_cast's recovering retry ranks a
    candidate position that does not exist: it decodes, so the replay loop
    records a varied-sampling success, and then validate_decision rejects it
    and the chunk falls back to the deterministic ranking."""

    def complete_json(self, *, json_schema: dict[str, Any], **kwargs: Any) -> str:
        raw = super().complete_json(json_schema=json_schema, **kwargs)
        if decision_type_for_schema(json_schema) == "vote_cast" and self.calls["vote_cast"] == 2:
            decisions = self._decisions(raw)
            return json.dumps({"decisions": [{**d, "blank": 0, "ranking": [999]} for d in decisions]})
        return raw


def _one_replay(config: PolityConfig) -> PolityConfig:
    return dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=1))


def _decision_events(journal_path: Path) -> list[dict[str, Any]]:
    return [e for e in _events(journal_path) if e["event_type"] in LLM_DECISION_TYPES]


def test_a_recovered_retry_is_journaled_on_every_decision_it_produced_for_all_nine_types(tmp_path: Path) -> None:
    client = _FirstCallOfEachTypeFailsClient(_ElectingFakeLlmClient())
    journal_path = run_simulation(_one_replay(golden_config(tmp_path, llm=True)), run_id="retry", llm_client=client)
    events = _decision_events(journal_path)

    assert set(client.recovered_decisions) == set(LLM_DECISION_TYPES)
    varied_by_type = Counter(e["event_type"] for e in events if e["payload"]["retry_sampling_varied"] == 1)
    assert dict(varied_by_type) == client.recovered_decisions
    # A recovered retry is not a fallback, and the flag is never absent.
    assert all("retry_sampling_varied" in e["payload"] for e in events)
    assert not [e for e in events if e["payload"]["retry_sampling_varied"] and e["payload"].get("llm_fallback")]

    progress = json.loads((journal_path.parent / "progress.json").read_text(encoding="utf-8"))
    assert progress["retry_count"] == sum(client.recovered_decisions.values())


def test_a_retry_that_decodes_then_fails_validation_is_a_fallback_not_a_retry(tmp_path: Path) -> None:
    client = _RetryDecodesButFailsValidationClient(_ElectingFakeLlmClient())
    journal_path = run_simulation(_one_replay(golden_config(tmp_path, llm=True)), run_id="retry", llm_client=client)
    votes = [e for e in _decision_events(journal_path) if e["event_type"] == "vote_cast"]

    fallbacks = [e for e in votes if e["payload"]["llm_fallback"] == 1]
    assert len(fallbacks) == client.recovered_decisions["vote_cast"]
    assert all(e["payload"]["retry_sampling_varied"] == 0 for e in fallbacks)
    assert all(e["payload"]["retry_sampling_varied"] == 0 for e in votes)
