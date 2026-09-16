"""S1.2: vote_cast's ballot rules in the grammar. See llm_schemas.vote_cast_json_schema,
the `llm.vote_cast_grammar_invariants` flag, and the bake-off's `vote_grammar` arm.

That the pinned vLLM's xgrammar compiles this schema and rejects the ballots it forbids
is checked in the server image itself: scripts/check_vote_grammar_xgrammar.py."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.bakeoff_bank import CaseBank
from api.domain.polity.bakeoff_runner import RESULTS_FILENAME, SESSION_FILENAME, read_results, run_session, schema_resolver
from api.domain.polity.citizen import generate_population
from api.domain.polity.llm_behavior_engine import cast_votes
from api.domain.polity.llm_call_log import decision_type_for_schema
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA, vote_cast_json_schema
from api.domain.polity.simple_rules import declare_candidacy
from api.tests.polity_bakeoff_fixtures import BankFakeClient, reference_bank, reference_config


def test_the_grammar_splits_a_ballot_into_a_blank_and_a_ranked_branch() -> None:
    schema = vote_cast_json_schema(5)
    blank, ranked = schema["$defs"]["VoteCastDecision"]["anyOf"]
    assert (blank["properties"]["blank"]["const"], blank["properties"]["ranking"]["maxItems"]) == (1, 0)
    assert ranked["properties"]["blank"]["const"] == 0
    assert (ranked["properties"]["ranking"]["minItems"], ranked["properties"]["ranking"]["maxItems"]) == (1, 5)
    assert all(branch["required"] == ["cid", "blank", "ranking", "motif"] and branch["additionalProperties"] is False for branch in (blank, ranked))
    assert list(ranked["properties"]) == list(VOTE_CAST_JSON_SCHEMA["$defs"]["VoteCastDecision"]["properties"])  # key order kept
    assert "enum" not in ranked["properties"]["blank"]
    assert schema["title"] == "VoteCastBatch" and decision_type_for_schema(schema) == "vote_cast"
    with pytest.raises(ValueError, match="at least 1"):
        vote_cast_json_schema(0)


def test_decision_types_are_read_off_the_schema_title() -> None:
    assert decision_type_for_schema(VOTE_CAST_JSON_SCHEMA) == "vote_cast"
    assert decision_type_for_schema({"title": "SomethingElse"}) == "unknown_schema"
    assert decision_type_for_schema(None) == "unknown_schema"


class _SchemaRecorder(BankFakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.schemas: list[dict[str, Any]] = []

    def complete_json(self, **kwargs: Any) -> str:
        self.schemas.append(kwargs["json_schema"])
        return super().complete_json(**kwargs)


def _vote(grammar: bool, candidates: int) -> list[dict[str, Any]]:
    config = reference_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, vote_cast_grammar_invariants=grammar))
    citizens = generate_population(config.citizens, 30, config.run.seed)
    for candidate in citizens[:candidates]:
        declare_candidacy(candidate)
    client = _SchemaRecorder()
    cast_votes(citizens[candidates:candidates + 6], citizens[:candidates], config, client)
    return client.schemas


def test_the_flag_sends_each_field_its_own_ranking_limit_and_is_on_by_default() -> None:
    assert all(schema == VOTE_CAST_JSON_SCHEMA for schema in _vote(grammar=False, candidates=8))
    assert {s["$defs"]["VoteCastDecision"]["anyOf"][1]["properties"]["ranking"]["maxItems"] for s in _vote(True, 8)} == {5}  # top five
    assert {s["$defs"]["VoteCastDecision"]["anyOf"][1]["properties"]["ranking"]["maxItems"] for s in _vote(True, 4)} == {4}
    assert reference_config().llm.vote_cast_grammar_invariants is True  # adopted 2026-09-16 (S1.2)


def test_the_vote_grammar_arm_changes_only_vote_cases_and_is_recorded(tmp_path: Path) -> None:
    bank = reference_bank()
    small = CaseBank(reference=bank.reference, cases=tuple(c for c in bank.cases if c.family in ("vote_first_choice", "candidacy_p500")))
    client = _SchemaRecorder()
    run_session(small, client, reference_config(), tmp_path / "arm", metadata={"label": "arm"}, warm_up=False, rerun_fraction=0.0,
                families=["vote_first_choice", "candidacy_p500"], arm="vote_grammar")

    assert json.loads((tmp_path / "arm" / SESSION_FILENAME).read_text())["arm"] == "vote_grammar"
    sent = {(s["title"], "anyOf" in json.dumps(s)) for s in client.schemas}
    assert sent == {("VoteCastBatch", True), ("CandidacyBatch", False)}  # every vote case gets the grammar, nothing else does
    results = read_results(tmp_path / "arm" / RESULTS_FILENAME)
    assert results and all(r["valid"] for r in results)

    resolve = schema_resolver(small, None)
    assert resolve(small.cases[0]) is small.schemas[small.cases[0].decision_type]
