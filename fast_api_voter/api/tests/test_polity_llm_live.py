"""Live smoke test against a real local Ollama instance — v2 increment 1.

Opt-in only, never runs in CI: set POLITY_LLM_LIVE=1. Everything else about
this feature (config parsing, schema validation, chunking, ballot
translation, envelope decoding, the request/response shape via
httpx.MockTransport) is unit-tested offline in test_polity_llm_client.py
and test_polity_llm_behavior_engine.py — this file only proves the real
code path works end-to-end against the actual pinned model.

Setup:
    docker run -d -p 11434:11434 --name ollama ollama/ollama
    docker exec ollama ollama pull qwen3:8b
    POLITY_LLM_LIVE=1 python -m pytest api/tests/test_polity_llm_live.py -o addopts="" -v

Wall-clock warning: each 25-citizen batch takes ~3.5-4 minutes on CPU
(ollama_structured_output_results.md) -- this file is slow by nature, not
by accident.
"""
import dataclasses
import json
import os

import pytest

from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import VoteMotif
from api.domain.polity.config import load_config
from api.domain.polity.llm_behavior_engine import build_system_prompt, build_user_prompt, cast_votes
from api.domain.polity.llm_client import OllamaJsonClient
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA, VoteCastBatch
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.simple_rules import declare_candidacy

pytestmark = pytest.mark.skipif(
    os.getenv("POLITY_LLM_LIVE") != "1",
    reason="requires a live Ollama with qwen3:8b pulled; set POLITY_LLM_LIVE=1",
)


def _citizen(cid, dims):
    positions = tuple((cid * 0.037 + i * 0.017) % 1.0 for i in range(dims))
    priorities = tuple(1.0 / dims for _ in range(dims))
    return Citizen(citizen_id=cid, issue_positions=positions, issue_priorities=priorities, blank_threshold=0.5,
                   ambition_score=0.5)


def _candidate(cid, dims):
    c = _citizen(1000 + cid, dims)
    declare_candidacy(c)
    return c


@pytest.fixture(scope="module")
def client():
    config = load_config().llm
    with OllamaJsonClient.from_config(config, seed=42) as client:
        yield client


def test_full_size_batch_produces_a_valid_reliable_response(client):
    """The validated recipe from the Lot 0 spike: max_batch_size citizens,
    the real dimensionality, the real schema, the real prompt builders."""
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [_citizen(i, dims) for i in range(config.llm.max_batch_size)]
    candidates = [_candidate(i, dims) for i in range(10)]

    raw = client.complete_json(
        system_prompt=build_system_prompt(citizens, len(candidates)),
        user_prompt=build_user_prompt(citizens, candidates),
        json_schema=VOTE_CAST_JSON_SCHEMA,
        max_tokens=config.llm.max_batch_size * 60 + 256,
    )
    batch = VoteCastBatch.model_validate_json(raw)
    assert [d.cid for d in batch.decisions] == [c.citizen_id for c in citizens]
    assert all(d.motif in {m.value for m in VoteMotif} for d in batch.decisions)


def test_sequential_calls_are_byte_identical(client):
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [_citizen(i, dims) for i in range(20)]
    candidates = [_candidate(i, dims) for i in range(2)]
    kwargs = dict(
        system_prompt=build_system_prompt(citizens, len(candidates)),
        user_prompt=build_user_prompt(citizens, candidates),
        json_schema=VOTE_CAST_JSON_SCHEMA,
        max_tokens=20 * 60 + 256,
    )
    first = client.complete_json(**kwargs)
    second = client.complete_json(**kwargs)
    assert first == second


def test_cast_votes_against_the_real_client(client):
    config = load_config()
    dims = config.citizens.issue_count
    voters = [_citizen(i, dims) for i in range(config.llm.max_batch_size)]
    candidates = [_candidate(i, dims) for i in range(5)]
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    outcome = cast_votes(voters, candidates, config, client)

    assert len(outcome.ballots) == len(voters)
    assert len(outcome.decisions) == len(voters)


def test_a_short_live_run_produces_a_valid_journal(tmp_path):
    config = load_config()
    config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(tmp_path)))
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.1))
    # Keep this smoke test to a single presidential+legislative cycle --
    # each presidential election needs population_size/max_batch_size
    # sequential LLM calls at ~3.5-4 min each (measured, CPU-only).
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=4))

    journal_path = run_simulation(config, run_id="live-smoke")

    lines = journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0
    for line in lines:
        json.loads(line)  # every line is valid, complete JSON
