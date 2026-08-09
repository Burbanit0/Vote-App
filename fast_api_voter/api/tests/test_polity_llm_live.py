"""Live smoke test against a real local Ollama instance — v2 increments 1-4.

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
by accident. Since increment 2, test_a_short_live_run_produces_a_valid_journal
also exercises a full candidacy batch pass per presidential election on top
of the existing vote batch pass, roughly doubling that test's cost. Increment
3's party-nomination batches are small (a handful of contested parties, not
citizens) and add comparatively little wall-clock time. Increment 4's
campaign-positioning batches are the same small size (a handful of
nominees) -- but its schema (a bounded list of sub-objects per decision, not
flat scalar fields) is genuinely new; this file is what actually verifies it
survives structured output, not an assumption.
"""
import dataclasses
import json
import os

import pytest

from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import CampaignMotif, CandidacyMotif, PartyNominationMotif, VoteMotif
from api.domain.polity.config import load_config
from api.domain.polity.llm_behavior_engine import (
    build_candidacy_system_prompt,
    build_candidacy_user_prompt,
    build_party_nomination_system_prompt,
    build_party_nomination_user_prompt,
    build_positioning_system_prompt,
    build_positioning_user_prompt,
    build_system_prompt,
    build_user_prompt,
    cast_votes,
    compute_max_tokens,
    decide_campaign_positioning,
    decide_candidacies,
    decide_party_nominations,
)
from api.domain.polity.llm_client import (
    OllamaJsonClient,
    decode_candidacy_batch,
    decode_party_nomination_batch,
    decode_positioning_batch,
    decode_vote_batch,
)
from api.domain.polity.llm_schemas import (
    CANDIDACY_JSON_SCHEMA,
    PARTY_NOMINATION_JSON_SCHEMA,
    POSITIONING_JSON_SCHEMA,
    VOTE_CAST_JSON_SCHEMA,
    CandidacyBatch,
    PartyNominationBatch,
    PositioningBatch,
    VoteCastBatch,
)
from api.domain.polity.parties import Party
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.simple_rules import declare_candidacy, sympathizer_ratio

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
        system_prompt=build_system_prompt(citizens, candidates),
        user_prompt=build_user_prompt(citizens, candidates),
        json_schema=VOTE_CAST_JSON_SCHEMA,
        max_tokens=compute_max_tokens(config.llm.max_batch_size),
    )
    batch = VoteCastBatch.model_validate_json(raw)
    assert [d.cid for d in batch.decisions] == [c.citizen_id for c in citizens]
    assert all(d.motif in {m.value for m in VoteMotif} for d in batch.decisions)
    for decision in batch.decisions:
        assert all(1 <= p <= len(candidates) for p in decision.ranking), (
            f"decision for cid={decision.cid} ranked out-of-range position(s) {decision.ranking} "
            f"(expected 1..{len(candidates)})"
        )


def test_sequential_calls_each_produce_a_valid_response(client):
    """Two textually identical requests are NOT guaranteed to produce
    byte-identical output, even at temperature=0 with a pinned seed --
    ollama_structured_output_results.md's determinism finding: a live run
    of this exact test once got a different `blank` value for the same
    citizen across two back-to-back calls. Most likely cause is
    non-deterministic floating-point reduction order in llama.cpp's
    multi-threaded CPU inference, a known property of that class of
    backend, not something fixable at the prompt/application layer. See
    llm_client.py's module docstring for what this means for
    reproducibility going forward (the response cache's job, not a live-
    model guarantee). This test only proves each call independently
    produces a valid, schema-conformant, correctly-aligned response --
    decoded through decode_vote_batch(), the same path production code
    uses, not raw Pydantic validation, so a malformed decision surfaces as
    the intended LlmResponseError rather than an uncaught ValidationError.
    5 candidates (not 2): a 2-candidate framing measurably increased how
    often the model produced a self-contradictory blank=0/empty-ranking
    decision -- 5 matches the realistic scenario already covered by
    test_cast_votes_against_the_real_client, which has not shown this."""
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [_citizen(i, dims) for i in range(20)]
    candidates = [_candidate(i, dims) for i in range(5)]
    kwargs = dict(
        system_prompt=build_system_prompt(citizens, candidates),
        user_prompt=build_user_prompt(citizens, candidates),
        json_schema=VOTE_CAST_JSON_SCHEMA,
        max_tokens=compute_max_tokens(20),
    )
    expected_cids = [c.citizen_id for c in citizens]
    for raw in (client.complete_json(**kwargs), client.complete_json(**kwargs)):
        decisions = decode_vote_batch(raw, expected_cids)
        assert [d.cid for d in decisions] == expected_cids


def test_cast_votes_against_the_real_client(client):
    config = load_config()
    dims = config.citizens.issue_count
    voters = [_citizen(i, dims) for i in range(config.llm.max_batch_size)]
    candidates = [_candidate(i, dims) for i in range(5)]
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    outcome = cast_votes(voters, candidates, config, client)

    assert len(outcome.ballots) == len(voters)
    assert len(outcome.decisions) == len(voters)


# ── candidacy_considered (v2 increment 2) ─────────────────────────────────

def test_full_size_candidacy_batch_produces_a_valid_reliable_response(client):
    """The candidacy analog of test_full_size_batch_produces_a_valid_reliable_response
    -- max_batch_size citizens, the real prompt builders, the real schema. A
    boolean+motif decision is a different, shorter prompt shape than a
    ranking decision; nothing here assumes it's immune to the failure modes
    that shape did (ollama_structured_output_results.md) without live
    evidence to that effect."""
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [_citizen(i, dims) for i in range(config.llm.max_batch_size)]
    support = {c.citizen_id: sympathizer_ratio(c, citizens) for c in citizens}

    raw = client.complete_json(
        system_prompt=build_candidacy_system_prompt(citizens),
        user_prompt=build_candidacy_user_prompt(citizens, support),
        json_schema=CANDIDACY_JSON_SCHEMA,
        max_tokens=compute_max_tokens(config.llm.max_batch_size),
        think=False,
    )
    batch = CandidacyBatch.model_validate_json(raw)
    assert [d.cid for d in batch.decisions] == [c.citizen_id for c in citizens]
    assert all(d.motif in {m.value for m in CandidacyMotif} for d in batch.decisions)


def test_candidacy_sequential_calls_each_produce_a_valid_response(client):
    """The candidacy analog of test_sequential_calls_each_produce_a_valid_response
    -- 20 citizens, exactly MIN_SAFE_BATCH_SIZE, the size where the vote_cast
    task's own small-batch corruption was twice observed (see
    scripts/batch_size_boundary_results.md: a follow-up sweep found no
    batch-size-dependent boundary for vote_cast in 20-25, evidence the
    corruption was Finding D's known non-determinism rather than a size
    threshold -- this test checks the same isn't uniquely worse for this
    differently-shaped decision)."""
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [_citizen(i, dims) for i in range(20)]
    support = {c.citizen_id: sympathizer_ratio(c, citizens) for c in citizens}
    kwargs = dict(
        system_prompt=build_candidacy_system_prompt(citizens),
        user_prompt=build_candidacy_user_prompt(citizens, support),
        json_schema=CANDIDACY_JSON_SCHEMA,
        max_tokens=compute_max_tokens(20),
        think=False,
    )
    expected_cids = [c.citizen_id for c in citizens]
    for raw in (client.complete_json(**kwargs), client.complete_json(**kwargs)):
        decisions = decode_candidacy_batch(raw, expected_cids)
        assert [d.cid for d in decisions] == expected_cids


def test_decide_candidacies_against_the_real_client(client):
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [_citizen(i, dims) for i in range(config.llm.max_batch_size)]
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    outcome = decide_candidacies(citizens, config, client)

    assert len(outcome.decisions) == len(citizens)
    assert all(d.outcome in (0, 1) for d in outcome.decisions)


# ── party_nomination_choice (v2 increment 3) ──────────────────────────────

def _nomination_party(party_id, dims):
    platform = tuple((party_id * 0.091 + i * 0.013) % 1.0 for i in range(dims))
    return Party(party_id=party_id, platform=platform)


def _contested_fixture(dims, num_parties, per_party):
    """A handful of contested parties (2+ candidates each), real
    dimensionality, ambition_score varied per member so a real model has a
    non-degenerate choice to make."""
    parties = [_nomination_party(pid, dims) for pid in range(num_parties)]
    contested: dict[int, list[Citizen]] = {}
    cid = 0
    for party in parties:
        members = []
        for m in range(per_party):
            c = _citizen(cid, dims)
            c.party_affiliation = party.party_id
            c.ambition_score = 0.2 + 0.2 * m
            members.append(c)
            cid += 1
        contested[party.party_id] = members
    return parties, contested


def test_full_size_party_nomination_batch_produces_a_valid_reliable_response(client):
    """The party-nomination analog of test_full_size_batch_produces_a_valid_reliable_response
    -- a handful of contested parties, the real prompt builders, the real
    schema, think=False. A live run originally tried think=True on the
    theory that small batches would dodge candidacy's reasoning-budget bug
    -- disproved: it hit the identical finish_reason='length' failure
    regardless of batch size (ollama_structured_output_results.md Finding
    E). This test pins the fix, not the original hypothesis."""
    config = load_config()
    dims = config.citizens.issue_count
    parties, contested = _contested_fixture(dims, num_parties=3, per_party=3)
    parties_by_id = {p.party_id: p for p in parties}
    support = {c.citizen_id: 0.5 for members in contested.values() for c in members}

    raw = client.complete_json(
        system_prompt=build_party_nomination_system_prompt(contested),
        user_prompt=build_party_nomination_user_prompt(contested, parties_by_id, support),
        json_schema=PARTY_NOMINATION_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(contested)),
        think=False,
    )
    batch = PartyNominationBatch.model_validate_json(raw)
    assert [d.party_id for d in batch.decisions] == list(contested.keys())
    assert all(d.motif in {m.value for m in PartyNominationMotif} for d in batch.decisions)
    for decision in batch.decisions:
        member_count = len(contested[decision.party_id])
        assert 1 <= decision.winner_position <= member_count, (
            f"decision for party_id={decision.party_id} picked out-of-range position "
            f"{decision.winner_position} (expected 1..{member_count})"
        )


def test_party_nomination_sequential_calls_each_produce_a_valid_response(client):
    """The party-nomination analog of test_sequential_calls_each_produce_a_valid_response
    -- two textually identical requests, checked independently rather than
    for byte-identity (Finding D applies here too until proven otherwise).
    think=False -- see test_full_size_party_nomination_batch_produces_a_valid_reliable_response
    and Finding E."""
    config = load_config()
    dims = config.citizens.issue_count
    parties, contested = _contested_fixture(dims, num_parties=2, per_party=4)
    parties_by_id = {p.party_id: p for p in parties}
    support = {c.citizen_id: 0.5 for members in contested.values() for c in members}
    kwargs = dict(
        system_prompt=build_party_nomination_system_prompt(contested),
        user_prompt=build_party_nomination_user_prompt(contested, parties_by_id, support),
        json_schema=PARTY_NOMINATION_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(contested)),
        think=False,
    )
    expected_party_ids = list(contested.keys())
    for raw in (client.complete_json(**kwargs), client.complete_json(**kwargs)):
        decisions = decode_party_nomination_batch(raw, expected_party_ids)
        assert [d.party_id for d in decisions] == expected_party_ids


def test_decide_party_nominations_against_the_real_client(client):
    config = load_config()
    dims = config.citizens.issue_count
    parties, contested = _contested_fixture(dims, num_parties=2, per_party=3)
    citizens = [c for members in contested.values() for c in members]
    declared_cids = {c.citizen_id for c in citizens}
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    outcome = decide_party_nominations(citizens, parties, declared_cids, config, client)

    assert set(outcome.winners.keys()) == {p.party_id for p in parties}
    for party_id, winner_cid in outcome.winners.items():
        assert winner_cid in {c.citizen_id for c in contested[party_id]}


# ── campaign_positioning (v2 increment 4) ─────────────────────────────────

def _positioning_nominee(cid, dims, party_id, ambition_score):
    c = _citizen(cid, dims)
    c.party_affiliation = party_id
    c.ambition_score = ambition_score
    return c


def _nominee_fixture(dims, num_nominees):
    parties = [_nomination_party(pid, dims) for pid in range(num_nominees)]
    nominees = [
        _positioning_nominee(i, dims, parties[i].party_id, 0.3 + 0.1 * i) for i in range(num_nominees)
    ]
    return nominees, {p.party_id: p for p in parties}


def test_full_size_positioning_batch_produces_a_valid_reliable_response(client):
    """The campaign-positioning analog of
    test_full_size_party_nomination_batch_produces_a_valid_reliable_response
    -- a handful of nominees, the real prompt builders, the real schema,
    think=False (same guess as party nomination, and the same reasoning --
    see decide_campaign_positioning's own docstring). Also the first live
    check of a genuinely new schema shape: a bounded list of sub-objects
    per decision, not flat scalar fields."""
    config = load_config()
    dims = config.citizens.issue_count
    nominees, parties_by_id = _nominee_fixture(dims, num_nominees=3)
    electorate_mean = tuple(0.5 for _ in range(dims))

    raw = client.complete_json(
        system_prompt=build_positioning_system_prompt(nominees, config),
        user_prompt=build_positioning_user_prompt(nominees, parties_by_id, electorate_mean),
        json_schema=POSITIONING_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(nominees)),
        think=False,
    )
    batch = PositioningBatch.model_validate_json(raw)
    assert [d.cid for d in batch.decisions] == [n.citizen_id for n in nominees]
    assert all(d.motif in {m.value for m in CampaignMotif} for d in batch.decisions)
    for decision in batch.decisions:
        # The schema itself only enforces a loose structural ceiling (see
        # PositioningDecision) -- this checks the model actually respects
        # the REAL bounds stated in the system prompt, not just the
        # structural one.
        assert len(decision.shifts) <= config.campaign.max_positioning_shifts, (
            f"decision for cid={decision.cid} used {len(decision.shifts)} shifts, "
            f"exceeding the stated max_positioning_shifts={config.campaign.max_positioning_shifts}"
        )
        for shift in decision.shifts:
            assert 0 <= shift.dimension < dims
            assert abs(shift.delta) <= config.campaign.max_positioning_delta, (
                f"decision for cid={decision.cid} shifted dimension {shift.dimension} by "
                f"{shift.delta}, exceeding the stated max_positioning_delta="
                f"{config.campaign.max_positioning_delta}"
            )


def test_positioning_sequential_calls_each_produce_a_valid_response(client):
    """The campaign-positioning analog of
    test_sequential_calls_each_produce_a_valid_response -- two textually
    identical requests, checked independently rather than for byte-identity
    (Finding D applies here too until proven otherwise)."""
    config = load_config()
    dims = config.citizens.issue_count
    nominees, parties_by_id = _nominee_fixture(dims, num_nominees=4)
    electorate_mean = tuple(0.5 for _ in range(dims))
    kwargs = dict(
        system_prompt=build_positioning_system_prompt(nominees, config),
        user_prompt=build_positioning_user_prompt(nominees, parties_by_id, electorate_mean),
        json_schema=POSITIONING_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(nominees)),
        think=False,
    )
    expected_cids = [n.citizen_id for n in nominees]
    for raw in (client.complete_json(**kwargs), client.complete_json(**kwargs)):
        decisions = decode_positioning_batch(raw, expected_cids)
        assert [d.cid for d in decisions] == expected_cids


def test_decide_campaign_positioning_against_the_real_client(client):
    config = load_config()
    dims = config.citizens.issue_count
    nominees, parties_by_id = _nominee_fixture(dims, num_nominees=3)
    citizens = list(nominees)
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    outcome = decide_campaign_positioning(nominees, citizens, parties_by_id, config, client)

    assert set(outcome.platforms.keys()) == {n.citizen_id for n in nominees}
    for nominee in nominees:
        assert len(outcome.platforms[nominee.citizen_id]) == dims


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
