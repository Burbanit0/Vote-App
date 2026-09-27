"""Live smoke test against a real local Ollama instance — v2 increments 1-5.

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
survives structured output, not an assumption. Increment 5's coalition
batches are the same small size (a handful of seated parties) -- its schema
(a closed 2-value action enum with a CROSS-FIELD motif coherence rule) is
also genuinely new; this file verifies the model actually respects that
coherence rule live, not just that CoalitionDecision's own model_validator
would catch a violation offline. v4 Lot 6's representative_response batches
are also small (0-or-1 officeholders in production; swept here at 1 and 3
for the same reason the pre-flight batch-reliability spike did --
scripts/lot6_batch_reliability_results.md) -- its schema has TWO cross-field
rules at once (stance<->shifts, stance<->motif), and this is the first
decision type verified against `think=False` on Ollama's NATIVE /api/chat
endpoint rather than the /v1 structured-output surface (see
decide_representative_response's own docstring for why -- the spike's own
first smoke-test attempt at think=True on /v1 reliably burned the whole
token budget on invisible reasoning for this exact schema). Runs every tick
rather than once per election, so the short live run below adds
proportionally more wall-clock time than any prior increment's addition did.
v4 Lot 7's pressure_action batches are the largest and most frequent in the
palier (measured mean 51.7 consulted citizens/tick under the shipped
electoral_only arm) -- swept here at 1/5/20/25, the exact sizes the
confirmatory reliability spike (scripts/lot6_batch_reliability_results.md's
"Lot 7 confirmatory pass") already measured clean against the REAL schema
and prompt builders; this file pins the same guarantee as a permanent
regression check.
"""
import dataclasses
import json
import os

import pytest

from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.codebook import (
    CampaignMotif,
    CandidacyMotif,
    ChamberMotif,
    CoalitionMotif,
    PartyNominationMotif,
    PressureMotif,
    ResponseMotif,
    VoteMotif,
)
from api.domain.polity.config import load_config
from api.domain.polity.llm_behavior_engine import (
    ChamberContext,
    PressureContext,
    ResponseContext,
    build_candidacy_system_prompt,
    build_candidacy_user_prompt,
    build_chamber_system_prompt,
    build_chamber_user_prompt,
    build_coalition_system_prompt,
    build_coalition_user_prompt,
    build_party_nomination_system_prompt,
    build_party_nomination_user_prompt,
    build_positioning_system_prompt,
    build_positioning_user_prompt,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    build_response_system_prompt,
    build_response_user_prompt,
    build_system_prompt,
    build_user_prompt,
    cast_votes,
    compute_max_tokens,
    decide_campaign_positioning,
    decide_candidacies,
    decide_chamber_deliberation,
    decide_coalition,
    decide_party_nominations,
    decide_pressure_actions,
    decide_representative_response,
    menu_acts,
)
from api.domain.polity.llm_client import (
    OllamaJsonClient,
    decode_candidacy_batch,
    decode_chamber_batch,
    decode_coalition_batch,
    decode_party_nomination_batch,
    decode_positioning_batch,
    decode_pressure_batch,
    decode_response_batch,
    decode_vote_batch,
)
from api.domain.polity.llm_schemas import (
    CANDIDACY_JSON_SCHEMA,
    CHAMBER_JSON_SCHEMA,
    COALITION_JSON_SCHEMA,
    PARTY_NOMINATION_JSON_SCHEMA,
    POSITIONING_JSON_SCHEMA,
    PRESSURE_JSON_SCHEMA,
    RESPONSE_JSON_SCHEMA,
    VOTE_CAST_JSON_SCHEMA,
    CandidacyBatch,
    ChamberBatch,
    CoalitionBatch,
    PartyNominationBatch,
    PositioningBatch,
    PressureBatch,
    ResponseBatch,
    VoteCastBatch,
)
from api.domain.polity.journal import Journal
from api.domain.polity.parties import Party
from api.domain.polity.run_polity_simulation import _run_accountability_phase, _run_chamber_deliberation, run_simulation
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


# ── coalition_decision (v2 increment 5) ───────────────────────────────────

def _coalition_fixture(dims, seats_by_party):
    """seats_by_party is an ordered list of (party_id, seats) pairs; votes
    mirror seats as floats for simplicity. Platforms spread out via the same
    deterministic formula as _nomination_party so a real model has a
    non-degenerate distance signal to react to."""
    parties = [_nomination_party(pid, dims) for pid, _ in seats_by_party]
    seats = {pid: s for pid, s in seats_by_party}
    votes = {pid: float(s) for pid, s in seats_by_party}
    return parties, seats, votes


def test_full_size_coalition_batch_produces_a_valid_reliable_response(client):
    """The coalition analog of test_full_size_party_nomination_batch_produces_a_valid_reliable_response
    -- a handful of seated, non-initiator parties, the real prompt builders,
    the real schema, think=False (same guess as increments 3/4's
    comparative-judgment shape). Also the live check that the prose-stated
    action<->motif coherence rule is actually respected by the model, not
    just declared in the prompt -- CoalitionDecision's own model_validator
    would already reject a violation at model_validate_json time below, so
    a passing test here is the real evidence, not an assumption."""
    config = load_config()
    dims = config.citizens.issue_count
    parties, seats, votes = _coalition_fixture(dims, [(0, 30), (1, 25), (2, 25), (3, 20)])
    platforms = {p.party_id: p.platform for p in parties}
    initiator = 0
    responders = [1, 2, 3]
    total_seats = sum(seats.values())
    threshold = config.parties.coalition_majority_ratio * total_seats

    raw = client.complete_json(
        system_prompt=build_coalition_system_prompt(responders, initiator, seats[initiator], total_seats, threshold),
        user_prompt=build_coalition_user_prompt(
            responders, initiator, platforms, seats, votes, total_seats, threshold
        ),
        json_schema=COALITION_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(responders)),
        think=False,
    )
    batch = CoalitionBatch.model_validate_json(raw)
    assert [d.party_id for d in batch.decisions] == responders
    assert all(d.action in (1, 2) for d in batch.decisions)
    assert all(d.motif in {m.value for m in CoalitionMotif} for d in batch.decisions)


def test_coalition_sequential_calls_each_produce_a_valid_response(client):
    """The coalition analog of test_party_nomination_sequential_calls_each_produce_a_valid_response
    -- two textually identical requests, checked independently rather than
    for byte-identity (Finding D applies here too until proven otherwise)."""
    config = load_config()
    dims = config.citizens.issue_count
    parties, seats, votes = _coalition_fixture(dims, [(0, 40), (1, 35), (2, 25)])
    platforms = {p.party_id: p.platform for p in parties}
    initiator = 0
    responders = [1, 2]
    total_seats = sum(seats.values())
    threshold = config.parties.coalition_majority_ratio * total_seats
    kwargs = dict(
        system_prompt=build_coalition_system_prompt(responders, initiator, seats[initiator], total_seats, threshold),
        user_prompt=build_coalition_user_prompt(
            responders, initiator, platforms, seats, votes, total_seats, threshold
        ),
        json_schema=COALITION_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(responders)),
        think=False,
    )
    for raw in (client.complete_json(**kwargs), client.complete_json(**kwargs)):
        decisions = decode_coalition_batch(raw, responders)
        assert [d.party_id for d in decisions] == responders


def test_decide_coalition_against_the_real_client(client):
    config = load_config()
    dims = config.citizens.issue_count
    parties, seats, votes = _coalition_fixture(dims, [(0, 30), (1, 25), (2, 25), (3, 20)])
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    outcome = decide_coalition(parties, seats, votes, config, client)

    assert outcome.initiator == 0
    assert outcome.coalition is None or (isinstance(outcome.coalition, list) and outcome.coalition[0] == 0)


# ── representative_response (v4 Lot 6) ────────────────────────────────────

def _response_holder(cid, dims):
    c = _citizen(cid, dims)
    c.pledged_platform = c.issue_positions
    c.revealed_position = c.issue_positions
    return c


def _response_context(cid):
    return ResponseContext(
        cid=cid, legitimacy=0.4, mandate_dev=0.3, street=0.5, lame_duck=False, ticks_left=6
    )


@pytest.mark.parametrize("num_holders", [1, 3])
def test_full_size_response_batch_produces_a_valid_reliable_response(client, num_holders):
    """The representative_response analog of
    test_full_size_positioning_batch_produces_a_valid_reliable_response --
    swept at 1 (production's real batch size, president-only) and 3 (the
    pre-flight spike's own sweep), the real prompt builders, the real
    schema, think=False via the native /api/chat endpoint (see this file's
    module docstring)."""
    config = load_config()
    dims = config.citizens.issue_count
    holders = [_response_holder(2000 + i, dims) for i in range(num_holders)]
    contexts = {h.citizen_id: _response_context(h.citizen_id) for h in holders}

    raw = client.complete_json(
        system_prompt=build_response_system_prompt(holders, config),
        user_prompt=build_response_user_prompt(holders, contexts),
        json_schema=RESPONSE_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(holders)),
        think=False,
    )
    batch = ResponseBatch.model_validate_json(raw)
    assert [d.cid for d in batch.decisions] == [h.citizen_id for h in holders]
    assert all(d.motif in {m.value for m in ResponseMotif} for d in batch.decisions)
    for decision in batch.decisions:
        # The schema itself only enforces a loose structural ceiling -- this
        # checks the model actually respects the REAL bounds stated in the
        # system prompt, not just the structural one, AND the stance<->shifts/
        # stance<->motif coherence the prompt states explicitly (a cross-field
        # rule constrained decoding cannot enforce on its own).
        assert len(decision.shifts) <= config.mandate.max_response_shifts, (
            f"decision for cid={decision.cid} used {len(decision.shifts)} shifts, "
            f"exceeding the stated max_response_shifts={config.mandate.max_response_shifts}"
        )
        for shift in decision.shifts:
            assert 0 <= shift.dimension < dims
            assert abs(shift.delta) <= config.mandate.max_response_delta, (
                f"decision for cid={decision.cid} shifted dimension {shift.dimension} by "
                f"{shift.delta}, exceeding the stated max_response_delta="
                f"{config.mandate.max_response_delta}"
            )
        # ResponseDecision's own model_validator already enforces this on
        # ResponseBatch.model_validate_json above -- reaching this line at
        # all is the live evidence that the model produced a coherent pair.


def test_response_sequential_calls_each_produce_a_valid_response(client):
    """The representative_response analog of
    test_sequential_calls_each_produce_a_valid_response -- two textually
    identical requests, checked independently rather than for byte-identity
    (Finding D applies here too until proven otherwise)."""
    config = load_config()
    dims = config.citizens.issue_count
    holders = [_response_holder(2100 + i, dims) for i in range(3)]
    contexts = {h.citizen_id: _response_context(h.citizen_id) for h in holders}
    kwargs = dict(
        system_prompt=build_response_system_prompt(holders, config),
        user_prompt=build_response_user_prompt(holders, contexts),
        json_schema=RESPONSE_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(holders)),
        think=False,
    )
    expected_cids = [h.citizen_id for h in holders]
    for raw in (client.complete_json(**kwargs), client.complete_json(**kwargs)):
        decisions = decode_response_batch(raw, expected_cids)
        assert [d.cid for d in decisions] == expected_cids


def test_decide_representative_response_against_the_real_client(client):
    config = load_config()
    dims = config.citizens.issue_count
    holders = [_response_holder(2200 + i, dims) for i in range(2)]
    contexts = {h.citizen_id: _response_context(h.citizen_id) for h in holders}
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    outcome = decide_representative_response(holders, contexts, config, client)

    assert set(outcome.positions.keys()) == {h.citizen_id for h in holders}
    for holder in holders:
        assert len(outcome.positions[holder.citizen_id]) == dims
        # decide_representative_response never resolves a pledge -- only
        # decide_campaign_positioning does, at nomination time.
        assert holder.pledged_platform == holder.issue_positions


def test_representative_response_wiring_against_the_real_client_in_a_live_tick(client, tmp_path):
    """Proves run_polity_simulation.py's OWN dt=6 wiring (the gate, the
    frozen ResponseContext, the journal write) against a real client and a
    real tick -- WITHOUT going through run_simulation's full pipeline.

    A `run_simulation(..., duration_years=4)` variant of this test was
    tried first and repeatedly failed for reasons that have nothing to do
    with representative_response: a full run first needs a real president
    ORGANICALLY elected through vote_cast (dt=1, think=True) and
    decide_campaign_positioning (dt=5, think=False), and both of those
    already-shipped v2 decision types turned out to be unreliable enough on
    this model/hardware to make that path itself flaky -- one live run hit
    campaign_positioning's own pre-existing batch-misalignment bug (a
    citizen dropped/duplicated, confirmed 4 times independently, already
    flagged in scripts/lot6_batch_reliability_results.md's Caveat section);
    a follow-up run with a smaller nominee count avoided that bug but then
    hit EVERY voter answering blank=1 on the real vote_cast call, producing
    election_no_winner and therefore no officeholder for dt=6 to ever run
    against. Neither failure involves representative_response's own code at
    all -- both are pre-existing reliability properties of already-shipped
    v2 decision types, out of this lot's scope to fix (see this file's
    module docstring on v2's own precedent for "flagged for live
    verification, not assumed").

    This test sidesteps both by calling _run_accountability_phase directly
    -- the exact function run_simulation's own tick loop calls -- against a
    hand-built, already-elected holder, same "direct call, Lot 2-5 style"
    precedent test_polity_run_simulation.py already uses for its own
    offline accountability-phase tests. One real dt=6 call (batch of 1,
    ~11.5s per the spike), not an organic multi-decision-type election."""
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    config = dataclasses.replace(config, mandate=dataclasses.replace(config.mandate, enabled=True))
    config = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))
    dims = config.citizens.issue_count
    holder = Citizen(
        citizen_id=1,
        issue_positions=tuple(0.5 for _ in range(dims)),
        issue_priorities=tuple(1.0 / dims for _ in range(dims)),
        blank_threshold=0.5,
        ambition_score=0.5,
        role=Role.ELECTED,
        office=Office.PRESIDENT,
        term_end_tick=16,
        mandates_served=1,
        legitimacy_capital=0.5,
        mandate_strength=0.5,
    )
    holder.pledged_platform = holder.issue_positions
    holder.revealed_position = holder.issue_positions

    journal_path = tmp_path / "dt6-live.jsonl"
    with Journal(journal_path, run_id="dt6-live") as journal:
        _run_accountability_phase([holder], config, journal, tick=0, llm_client=client)

    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    response_events = [e for e in events if e["event_type"] == "representative_response"]
    assert len(response_events) == 1
    e = response_events[0]
    assert e["payload"]["office"] == Office.PRESIDENT.value
    assert e["payload"]["stance"] in {1, 2, 3, 4}
    assert e["motif"] in {str(m.value) for m in ResponseMotif}
    assert e["codebook_version"] == config.llm.codebook_version


# ── pressure_action (v4 Lot 7) ─────────────────────────────────────────────

def _pressure_context(cid, target, legal):
    # Alternates availability by cid parity, mirroring the confirmatory
    # spike's own "full_menu" modality: some citizens see an open petition
    # they can sign, others see none and only the non-petition acts.
    if cid % 2 == 0:
        available = legal
        petition_open = True
        expires_at = 14
    else:
        available = tuple(a for a in legal if a not in (1, 2))
        petition_open = False
        expires_at = None
    return PressureContext(
        cid=cid, target=target, self_gap=0.6, mandate_dev=0.3, ticks_to_election=9,
        available=available, petition_open=petition_open, petition_expires_at_tick=expires_at,
        already_signed=False,
    )


@pytest.mark.parametrize("num_citizens", [1, 5, 20, 25])
def test_full_size_pressure_batch_produces_a_valid_reliable_response(client, num_citizens):
    """The pressure_action analog of
    test_full_size_positioning_batch_produces_a_valid_reliable_response --
    swept at the exact chunk sizes chunk_voters actually produces in
    production (1 up to max_batch_size=25), the real prompt builders, the
    real schema, think=False via the native /api/chat endpoint. Already
    confirmed clean at these sizes by the confirmatory reliability spike
    (scripts/lot6_batch_reliability_results.md's "Lot 7 confirmatory
    pass") -- this test pins the same guarantee as a permanent regression
    check, not a first discovery."""
    config = load_config()
    config = dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
        ),
    )
    target = 9000
    consulted = [_citizen(3000 + i, 1) for i in range(num_citizens)]
    legal = menu_acts(config.pressure_menu)
    contexts = {c.citizen_id: _pressure_context(c.citizen_id, target, legal) for c in consulted}

    raw = client.complete_json(
        system_prompt=build_pressure_system_prompt(consulted, config),
        user_prompt=build_pressure_user_prompt(consulted, contexts),
        json_schema=PRESSURE_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(consulted)),
        think=False,
    )
    batch = PressureBatch.model_validate_json(raw)
    assert [d.cid for d in batch.decisions] == [c.citizen_id for c in consulted]
    for decision in batch.decisions:
        # act must be menu-legal -- the ONE batch-rejecting check this lot
        # has (§3.6.6). act being IN this citizen's own `available` is NOT
        # an invariant (the two-tier split), so it's reported below as a
        # rate, never asserted at 100%.
        assert decision.target == target
        assert decision.act in legal, (
            f"decision for cid={decision.cid} chose act={decision.act}, outside the "
            f"stated menu {legal}"
        )
        assert decision.motif in {m.value for m in PressureMotif}

    out_of_available = sum(1 for d in batch.decisions if d.act not in contexts[d.cid].available)
    print(f"[size={num_citizens}] out_of_available_rate={out_of_available / len(batch.decisions):.2f}")


def test_pressure_sequential_calls_each_produce_a_valid_response(client):
    """The pressure_action analog of
    test_sequential_calls_each_produce_a_valid_response -- two textually
    identical requests, checked independently rather than for byte-identity
    (Finding D applies here too until proven otherwise)."""
    config = load_config()
    config = dataclasses.replace(
        config, pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True)
    )
    target = 9100
    consulted = [_citizen(3100 + i, 1) for i in range(3)]
    legal = menu_acts(config.pressure_menu)
    contexts = {c.citizen_id: _pressure_context(c.citizen_id, target, legal) for c in consulted}
    kwargs = dict(
        system_prompt=build_pressure_system_prompt(consulted, config),
        user_prompt=build_pressure_user_prompt(consulted, contexts),
        json_schema=PRESSURE_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(consulted)),
        think=False,
    )
    expected_cids = [c.citizen_id for c in consulted]
    for raw in (client.complete_json(**kwargs), client.complete_json(**kwargs)):
        decisions = decode_pressure_batch(raw, expected_cids)
        assert [d.cid for d in decisions] == expected_cids


def test_decide_pressure_actions_against_the_real_client(client):
    # A 30-citizen cohort at max_batch_size=25 -> two real chunked calls,
    # decisions concatenated in cohort order.
    config = load_config()
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
    )
    target = 9200
    consulted = [_citizen(3200 + i, 1) for i in range(30)]
    legal = menu_acts(config.pressure_menu)
    contexts = {c.citizen_id: _pressure_context(c.citizen_id, target, legal) for c in consulted}

    outcome = decide_pressure_actions(consulted, contexts, config, client)

    assert [d.cid for d in outcome.decisions] == [c.citizen_id for c in consulted]
    assert all(d.act in legal for d in outcome.decisions)


def test_pressure_action_wiring_against_the_real_client_in_a_live_tick(client, tmp_path):
    """Proves run_polity_simulation.py's OWN dt=10 wiring (the gate, the
    frozen PressureContext, applicable_pressure_act, the journal write)
    against a real client and a real tick -- WITHOUT going through
    run_simulation's full pipeline, for the same reason dt=6's own wiring
    test sidesteps it (see
    test_representative_response_wiring_against_the_real_client_in_a_live_tick's
    docstring): a hand-built, already-elected holder plus a hand-built
    population with base_threshold=0.0 (guaranteed consultation), one real
    dt=10 call (a batch of 3, well under max_batch_size)."""
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    config = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
        ),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    dims = config.citizens.issue_count
    holder = Citizen(
        citizen_id=1,
        issue_positions=tuple(0.5 for _ in range(dims)),
        issue_priorities=tuple(1.0 / dims for _ in range(dims)),
        blank_threshold=0.5,
        ambition_score=0.5,
        role=Role.ELECTED,
        office=Office.PRESIDENT,
        term_end_tick=16,
        mandates_served=1,
        legitimacy_capital=0.5,
        mandate_strength=0.5,
    )
    holder.pledged_platform = holder.issue_positions
    holder.revealed_position = holder.issue_positions
    consulted = [
        Citizen(
            citizen_id=100 + i,
            issue_positions=tuple(0.0 for _ in range(dims)),
            issue_priorities=tuple(1.0 / dims for _ in range(dims)),
            blank_threshold=0.0,
            ambition_score=0.5,
            base_threshold=0.0,
        )
        for i in range(3)
    ]

    journal_path = tmp_path / "dt10-live.jsonl"
    with Journal(journal_path, run_id="dt10-live") as journal:
        _run_accountability_phase([holder] + consulted, config, journal, tick=0, llm_client=client)

    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert len(pressure_events) == len(consulted)
    legal = menu_acts(config.pressure_menu)
    for e in pressure_events:
        assert e["payload"]["target"] == holder.citizen_id
        assert e["payload"]["act"] in legal
        assert e["motif"] in {str(m.value) for m in PressureMotif}
        assert e["codebook_version"] == config.llm.codebook_version


# ── chamber_deliberation (v6b Lot 3, §6bis.3) ─────────────────────────────

def _chamber_member(cid, dims, seat_until=16):
    c = _citizen(cid, dims)
    c.sortition_seat_until_tick = seat_until
    c.sortition_terms_served = 1
    c.chamber_position = c.issue_positions
    return c


def _chamber_context(cid, ticks_left=8):
    return ChamberContext(cid=cid, ticks_left=ticks_left)


@pytest.mark.parametrize("num_members", [1, 10])
def test_full_size_chamber_batch_produces_a_valid_reliable_response(client, num_members):
    """The chamber_deliberation analog of
    test_full_size_response_batch_produces_a_valid_reliable_response --
    swept at 1 and 10 (this lot's own measured reliable ceiling,
    _CHAMBER_MAX_CHUNK_SIZE, scripts/lot3_chamber_reliability_results.md).
    Deliberately does NOT sweep 30 here in one raw call -- that's a known,
    measured, DESIGNED failure at this schema's weight; the chunked path is
    what test_decide_chamber_deliberation_against_the_real_client below
    exercises instead."""
    config = load_config()
    dims = config.citizens.issue_count
    members = [_chamber_member(3000 + i, dims) for i in range(num_members)]
    contexts = {m.citizen_id: _chamber_context(m.citizen_id) for m in members}

    raw = client.complete_json(
        system_prompt=build_chamber_system_prompt(members, config),
        user_prompt=build_chamber_user_prompt(members, contexts),
        json_schema=CHAMBER_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(members)),
        think=False,
    )
    batch = ChamberBatch.model_validate_json(raw)
    assert [d.cid for d in batch.decisions] == [m.citizen_id for m in members]
    assert all(d.motif in {m.value for m in ChamberMotif} for d in batch.decisions)
    for decision in batch.decisions:
        # ChamberDecision deliberately has NO shifts<->motif coherence
        # validator (removed after this lot's own spike measured it
        # failing at a high rate) -- only the real numeric bounds are
        # checked here.
        assert len(decision.shifts) <= config.sortition_chamber.max_deliberation_shifts, (
            f"decision for cid={decision.cid} used {len(decision.shifts)} shifts, exceeding the "
            f"stated max_deliberation_shifts={config.sortition_chamber.max_deliberation_shifts}"
        )
        for shift in decision.shifts:
            assert 0 <= shift.dimension < dims
            assert abs(shift.delta) <= config.sortition_chamber.max_deliberation_delta, (
                f"decision for cid={decision.cid} shifted dimension {shift.dimension} by "
                f"{shift.delta}, exceeding the stated max_deliberation_delta="
                f"{config.sortition_chamber.max_deliberation_delta}"
            )


def test_chamber_sequential_calls_each_produce_a_valid_response(client):
    """The chamber_deliberation analog of
    test_response_sequential_calls_each_produce_a_valid_response -- two
    textually identical requests, checked independently."""
    config = load_config()
    dims = config.citizens.issue_count
    members = [_chamber_member(3100 + i, dims) for i in range(3)]
    contexts = {m.citizen_id: _chamber_context(m.citizen_id) for m in members}
    kwargs = dict(
        system_prompt=build_chamber_system_prompt(members, config),
        user_prompt=build_chamber_user_prompt(members, contexts),
        json_schema=CHAMBER_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(members)),
        think=False,
    )
    expected_cids = [m.citizen_id for m in members]
    for raw in (client.complete_json(**kwargs), client.complete_json(**kwargs)):
        decisions = decode_chamber_batch(raw, expected_cids)
        assert [d.cid for d in decisions] == expected_cids


def test_decide_chamber_deliberation_against_the_real_client(client):
    """The real-scale confirmation: a 30-member cohort (sortition_chamber.
    seats shipped) through decide_chamber_deliberation's own chunking
    (_CHAMBER_MAX_CHUNK_SIZE=10, three real chunked calls) -- the exact
    failure mode this lot's own spike measured (one call of 30 silently
    drops all but the last 6 decisions) must not reappear here."""
    config = load_config()
    dims = config.citizens.issue_count
    members = [_chamber_member(3200 + i, dims) for i in range(30)]
    contexts = {m.citizen_id: _chamber_context(m.citizen_id) for m in members}
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))

    outcome = decide_chamber_deliberation(members, contexts, config, client)

    assert set(outcome.positions.keys()) == {m.citizen_id for m in members}
    for member in members:
        assert len(outcome.positions[member.citizen_id]) == dims


def test_chamber_deliberation_wiring_against_the_real_client_in_a_live_tick(client, tmp_path):
    """Proves run_polity_simulation.py's OWN dt=11 wiring (the gate, the
    ChamberContext, the journal write) against a real client and a real
    tick -- calling _run_chamber_deliberation directly (the exact function
    the tick loop calls, dispatched independently of
    _run_accountability_phase, never nested inside it -- see that
    function's own docstring)."""
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    config = dataclasses.replace(
        config, sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=1)
    )
    dims = config.citizens.issue_count
    member = _chamber_member(1, dims)

    journal_path = tmp_path / "dt11-live.jsonl"
    with Journal(journal_path, run_id="dt11-live") as journal:
        _run_chamber_deliberation([member], config, journal, tick=0, llm_client=client)

    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    chamber_events = [e for e in events if e["event_type"] == "chamber_deliberation"]
    assert len(chamber_events) == 1
    e = chamber_events[0]
    assert set(e["payload"]["ctx"].keys()) == {"ticks_left"}
    assert e["motif"] in {str(m.value) for m in ChamberMotif}
    assert e["codebook_version"] == config.llm.codebook_version


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
