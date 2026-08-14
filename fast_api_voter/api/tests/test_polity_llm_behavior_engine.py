"""llm_behavior_engine.py — v2 increment 1's LLM replacement for build_ranking.
Offline only: a FakeLlmClient stands in for OllamaJsonClient, no network.
"""
import dataclasses
import json
import math

import pytest

from api.domain.polity.ballot_and_aggregation import get_presidential_winner
from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import VoteMotif
from api.domain.polity.config import PressureMenuConfig, load_config
from api.domain.polity.llm_behavior_engine import (
    MIN_SAFE_BATCH_SIZE,
    PressureContext,
    ResponseContext,
    apply_shifts,
    assemble_coalition,
    build_candidacy_system_prompt,
    build_candidacy_user_prompt,
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
    chunk_voters,
    compute_max_tokens,
    decide_campaign_positioning,
    decide_candidacies,
    decide_coalition,
    decide_party_nominations,
    decide_pressure_actions,
    decide_representative_response,
    menu_acts,
    resolve_party_nomination_cid,
    truncation_limit,
    validate_coalition_decision,
    validate_decision,
    validate_positioning_decision,
    validate_pressure_decision,
    validate_response_decision,
)
from api.domain.polity.llm_client import LlmResponseError, LlmTransportError
from api.domain.polity.llm_schemas import (
    CoalitionDecision,
    PartyNominationDecision,
    PositioningDecision,
    PositionShift,
    PressureDecision,
    ResponseDecision,
    VoteCastDecision,
)
from api.domain.polity.parties import Party
from api.domain.polity.simple_rules import (
    BLANK_LABEL,
    build_ranking,
    declare_candidacy,
    form_coalition,
    sympathizer_ratio,
    weighted_distance,
)


def _citizen(cid, positions, priorities=None, blank_threshold=1.0):
    k = len(positions)
    priorities = priorities or tuple(1.0 / k for _ in range(k))
    return Citizen(
        citizen_id=cid,
        issue_positions=tuple(positions),
        issue_priorities=tuple(priorities),
        blank_threshold=blank_threshold,
        ambition_score=0.5,
    )


def _candidate(cid, positions):
    c = _citizen(cid, positions)
    declare_candidacy(c)
    return c


def _population(n, dims=1):
    return [_citizen(i, tuple((i * 0.01 + d) % 1.0 for d in range(dims))) for i in range(n)]


# ── chunk_voters ──────────────────────────────────────────────────────────

def test_chunk_voters_splits_evenly_when_it_divides():
    voters = _population(100)
    chunks = chunk_voters(voters, 25)
    assert [len(c) for c in chunks] == [25, 25, 25, 25]
    assert [v.citizen_id for v in chunks[0]] == list(range(25))


def test_chunk_voters_uses_near_equal_sizes_not_a_small_remainder():
    voters = _population(110)
    chunks = chunk_voters(voters, 25)
    assert [len(c) for c in chunks] == [22, 22, 22, 22, 22]


def test_chunk_voters_boundary_at_exactly_min_safe_batch_size_is_allowed():
    voters = _population(80)  # ceil(80/25)=4, 80/4=20 == MIN_SAFE_BATCH_SIZE
    chunks = chunk_voters(voters, 25)
    assert [len(c) for c in chunks] == [20, 20, 20, 20]


def test_chunk_voters_below_min_safe_batch_size_raises():
    voters = _population(39)  # ceil(39/25)=2, base=19 < 20
    with pytest.raises(NotImplementedError, match="min_batch_size=20"):
        chunk_voters(voters, 25)


# ── chunk_voters min_batch_size override (v4 Lot 7) ──────────────────────

def test_chunk_voters_min_batch_size_defaults_to_min_safe_batch_size():
    voters = _population(39)  # ceil(39/25)=2, base=19 < MIN_SAFE_BATCH_SIZE
    with pytest.raises(NotImplementedError, match="min_batch_size=20"):
        chunk_voters(voters, 25)


def test_chunk_voters_honours_an_explicit_min_batch_size():
    voters = _population(3)
    chunks = chunk_voters(voters, 25, min_batch_size=1)
    assert chunks == [voters]


def test_chunk_voters_empty_population_returns_no_chunks():
    assert chunk_voters([], 25) == []


def test_min_safe_batch_size_is_20():
    # Pinned so a change is deliberate, not accidental -- see
    # ollama_structured_output_results.md for the empirical basis.
    assert MIN_SAFE_BATCH_SIZE == 20


# ── truncation_limit ──────────────────────────────────────────────────────

def test_truncation_limit_none_at_or_below_six():
    assert truncation_limit(1) is None
    assert truncation_limit(6) is None


def test_truncation_limit_five_above_six():
    assert truncation_limit(7) == 5
    assert truncation_limit(20) == 5


# ── compute_max_tokens ────────────────────────────────────────────────────

def test_compute_max_tokens_has_flat_reasoning_headroom():
    # A live consolidation run hit finish_reason='length' on a 20-citizen
    # batch under the old chunk_size*60+256 formula (1456 tokens) --
    # Qwen3's invisible <think> reasoning shares the same budget as the
    # visible answer. Pin real headroom above that failure point.
    assert compute_max_tokens(20) >= 20 * 60 + 1024


def test_compute_max_tokens_has_a_floor_for_tiny_chunks():
    assert compute_max_tokens(0) == 1536


# ── build_system_prompt / build_user_prompt ──────────────────────────────

def test_system_prompt_enumerates_every_expected_cid():
    citizens = _population(3)
    candidates = [_candidate(10, (0.1,)), _candidate(11, (0.9,))]
    prompt = build_system_prompt(citizens, candidates)
    assert "[0,1,2]" in prompt
    assert "EXACTEMENT ces 3" in prompt


def test_system_prompt_describes_candidates_by_position_not_cid():
    # Positions (1..N), never raw candidate cids -- a live consolidation
    # run found the model conflates candidate cids with the voter cid list
    # above, since a candidate is also a citizen and the two number spaces
    # can collide. See build_system_prompt's docstring.
    citizens = _population(2)
    candidates = [_candidate(11, (0.9,)), _candidate(10, (0.1,))]
    prompt = build_system_prompt(citizens, candidates)
    assert "(1 a 2)" in prompt
    assert "position" in prompt


def test_system_prompt_notes_truncation_above_six_candidates():
    citizens = _population(2)
    seven = [_candidate(i, (0.1,)) for i in range(7)]
    six = [_candidate(i, (0.1,)) for i in range(6)]
    assert "5 meilleurs" in build_system_prompt(citizens, seven)
    assert "5 meilleurs" not in build_system_prompt(citizens, six)


def test_user_prompt_is_deterministic_for_the_same_inputs():
    voters = _population(3)
    candidates = [_candidate(10, (0.1,)), _candidate(11, (0.9,))]
    assert build_user_prompt(voters, candidates) == build_user_prompt(voters, candidates)


def test_user_prompt_is_independent_of_candidate_iteration_order():
    voters = _population(2)
    a = _candidate(10, (0.1,))
    b = _candidate(11, (0.9,))
    assert build_user_prompt(voters, [a, b]) == build_user_prompt(voters, [b, a])


def test_user_prompt_distances_match_weighted_distance_exactly():
    # v4 Lot 8 fix: the model is handed a precomputed distance instead of
    # deriving "is this candidate acceptable" from raw vectors itself --
    # this pins that the precomputed value is provably the SAME quantity
    # build_ranking already compares against blank_threshold on the
    # deterministic path (Lot 2's own "pin the equivalence" precedent).
    voters = [_citizen(0, (0.2, 0.7), priorities=(0.6, 0.4))]
    a = _candidate(10, (0.5, 0.1))
    b = _candidate(11, (0.0, 1.0))
    payload = json.loads(build_user_prompt(voters, [a, b]))
    got = payload["voters"][0]["distances"]
    expected = [
        round(weighted_distance(voters[0], (0.5, 0.1)), 4),
        round(weighted_distance(voters[0], (0.0, 1.0)), 4),
    ]
    assert got == expected


def test_user_prompt_distances_follow_the_same_position_order_as_candidates():
    voters = [_citizen(0, (0.5,))]
    a = _candidate(10, (0.9,))
    b = _candidate(5, (0.1,))
    payload = json.loads(build_user_prompt(voters, [a, b]))
    # sorted_candidates orders by citizen_id: b (5) before a (10).
    assert [c["cid"] for c in payload["candidates"]] == [5, 10]
    assert payload["voters"][0]["distances"] == [
        round(weighted_distance(voters[0], (0.1,)), 4),
        round(weighted_distance(voters[0], (0.9,)), 4),
    ]


def test_system_prompt_explains_the_distance_precomputation_and_threshold_rule():
    citizens = _population(2)
    candidates = [_candidate(10, (0.1,)), _candidate(11, (0.9,))]
    prompt = build_system_prompt(citizens, candidates)
    assert "distances" in prompt
    assert "blank_threshold" in prompt
    assert "105" in prompt


def test_system_prompt_tells_the_model_to_prefer_an_acceptable_candidate_over_blank():
    citizens = _population(2)
    candidates = [_candidate(10, (0.1,)), _candidate(11, (0.9,))]
    prompt = build_system_prompt(citizens, candidates)
    assert "DOIT etre prefere au vote" in prompt


# ── validate_decision ─────────────────────────────────────────────────────

def _decision(**overrides):
    base = {"cid": 1, "blank": 0, "ranking": [1, 2], "motif": VoteMotif.NO_MATCHING_PRIORITY.value}
    base.update(overrides)
    return VoteCastDecision.model_validate(base)


def test_validate_decision_accepts_positions_within_count():
    validate_decision(_decision(), candidate_count=3, truncate_at=None)  # must not raise


def test_validate_decision_rejects_out_of_range_position():
    with pytest.raises(LlmResponseError, match="out-of-range"):
        validate_decision(_decision(ranking=[1, 99]), candidate_count=2, truncate_at=None)


def test_validate_decision_rejects_exceeding_truncation_limit():
    with pytest.raises(LlmResponseError, match="truncation"):
        validate_decision(_decision(ranking=[1, 2, 3, 4, 5, 6]), candidate_count=6, truncate_at=5)


def test_validate_decision_allows_up_to_the_truncation_limit():
    validate_decision(_decision(ranking=[1, 2, 3, 4, 5]), candidate_count=6, truncate_at=5)


# ── cast_votes (FakeLlmClient, mirrors build_ranking's own ordering) ─────

class FakeLlmClient:
    """Computes the same nearest-candidate ranking build_ranking would,
    returning it in VoteCastBatch's wire shape -- lets a test prove
    cast_votes' output is interchangeable with the deterministic baseline's,
    the 'zero changes needed downstream' contract.

    Returns `ranking` as 1-indexed positions into the candidate list
    sorted by citizen_id, exactly the convention cast_votes/build_user_prompt
    use (see llm_behavior_engine.sorted_candidates) -- a real model reads
    `position` off the candidate blocks in the user prompt; this fake
    computes the same mapping directly since it never actually parses the
    candidate blocks."""

    def __init__(self, voters_by_id, candidates):
        self._voters_by_id = voters_by_id
        self._candidates = candidates
        self._cid_to_position = {
            c.citizen_id: i for i, c in enumerate(sorted(candidates, key=lambda c: c.citizen_id), start=1)
        }
        self.calls: list[list[int]] = []

    def _distance(self, voter, platform):
        return math.sqrt(
            sum(w * (vx - px) ** 2 for vx, px, w in zip(voter.issue_positions, platform, voter.issue_priorities))
        )

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        cids = [v["cid"] for v in payload["voters"]]
        self.calls.append(cids)
        decisions = []
        for cid in cids:
            voter = self._voters_by_id[cid]
            ranked = sorted(self._candidates, key=lambda c: (self._distance(voter, c.pledged_platform), c.citizen_id))
            within = [c for c in ranked if self._distance(voter, c.pledged_platform) <= voter.blank_threshold]
            if not within:
                decisions.append({"cid": cid, "blank": 1, "ranking": [], "motif": 101})
            else:
                decisions.append(
                    {
                        "cid": cid,
                        "blank": 0,
                        "ranking": [self._cid_to_position[c.citizen_id] for c in within],
                        "motif": 101,
                    }
                )
        return json.dumps({"decisions": decisions})


def _config_with_llm_enabled(max_batch_size=25):
    config = load_config()
    return dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True, max_batch_size=max_batch_size),
    )


def test_cast_votes_matches_build_ranking_when_nobody_votes_blank():
    voters = _population(20, dims=1)
    candidates = [_candidate(100, (0.1,)), _candidate(101, (0.9,))]
    config = _config_with_llm_enabled()
    client = FakeLlmClient({v.citizen_id: v for v in voters}, candidates)

    outcome = cast_votes(voters, candidates, config, client)

    expected_ballots = [build_ranking(v, candidates) for v in voters]
    assert outcome.ballots == expected_ballots
    llm_winner = get_presidential_winner(outcome.ballots, config.institutions.presidential_method)
    baseline_winner = get_presidential_winner(expected_ballots, config.institutions.presidential_method)
    assert llm_winner == baseline_winner


def test_cast_votes_preserves_voter_order_across_chunk_boundaries():
    voters = _population(50, dims=1)
    candidates = [_candidate(100, (0.5,))]
    config = _config_with_llm_enabled(max_batch_size=25)
    client = FakeLlmClient({v.citizen_id: v for v in voters}, candidates)

    outcome = cast_votes(voters, candidates, config, client)

    assert client.calls == [list(range(25)), list(range(25, 50))]
    assert len(outcome.ballots) == 50
    for ballot in outcome.ballots:
        assert BLANK_LABEL in ballot


def test_cast_votes_ballot_from_decision_blank_is_always_just_blank():
    voters = _population(20, dims=1, )
    candidates = [_candidate(100, (0.9,))]
    config = _config_with_llm_enabled()
    # blank_threshold=1.0 on every voter means nobody actually goes blank
    # in this fixture; force it via a client that always answers blank.
    client = FakeLlmClient({v.citizen_id: v for v in voters}, candidates)
    client.complete_json = lambda **kwargs: json.dumps(  # type: ignore[method-assign]
        {"decisions": [{"cid": v.citizen_id, "blank": 1, "ranking": [], "motif": 101} for v in voters]}
    )

    outcome = cast_votes(voters, candidates, config, client)
    assert all(ballot == [BLANK_LABEL] for ballot in outcome.ballots)


def test_cast_votes_raises_notimplementederror_for_unsupported_provider():
    voters = _population(20)
    candidates = [_candidate(100, (0.5,))]
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm"))
    with pytest.raises(NotImplementedError, match="provider"):
        cast_votes(voters, candidates, config, FakeLlmClient({}, candidates))


def test_cast_votes_raises_for_dynamic_batch_sharding():
    voters = _population(20)
    candidates = [_candidate(100, (0.5,))]
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, batch_sharding="dynamic"))
    with pytest.raises(NotImplementedError, match="batch_sharding"):
        cast_votes(voters, candidates, config, FakeLlmClient({}, candidates))


def test_cast_votes_raises_for_intra_run_workers_above_one():
    voters = _population(20)
    candidates = [_candidate(100, (0.5,))]
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parallel=dataclasses.replace(config.parallel, intra_run_workers=2))
    with pytest.raises(NotImplementedError, match="intra_run_workers"):
        cast_votes(voters, candidates, config, FakeLlmClient({}, candidates))


def test_cast_votes_raises_for_codebook_version_mismatch():
    voters = _population(20)
    candidates = [_candidate(100, (0.5,))]
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, codebook_version="0.9"))
    with pytest.raises(Exception, match="codebook_version"):
        cast_votes(voters, candidates, config, FakeLlmClient({}, candidates))


def test_cast_votes_propagates_llm_response_error_on_count_mismatch():
    voters = _population(20)
    candidates = [_candidate(100, (0.5,))]
    config = _config_with_llm_enabled()

    class ShortClient:
        def complete_json(self, **kwargs):
            return json.dumps({"decisions": [{"cid": 0, "blank": 1, "ranking": [], "motif": 101}]})

    with pytest.raises(LlmResponseError, match="misaligned"):
        cast_votes(voters, candidates, config, ShortClient())


# ── build_candidacy_system_prompt / build_candidacy_user_prompt ─────────────

def test_candidacy_system_prompt_enumerates_every_expected_cid():
    citizens = _population(3)
    prompt = build_candidacy_system_prompt(citizens)
    assert "[0,1,2]" in prompt
    assert "EXACTEMENT ces 3" in prompt


def test_candidacy_user_prompt_carries_the_precomputed_support_signal():
    citizens = _population(3)
    support = {0: 0.1, 1: 0.5, 2: 0.9}
    payload = json.loads(build_candidacy_user_prompt(citizens, support))
    by_cid = {c["cid"]: c for c in payload["citizens"]}
    assert by_cid[0]["perceived_support"] == 0.1
    assert by_cid[2]["perceived_support"] == 0.9


# ── decide_candidacies (FakeCandidacyLlmClient) ──────────────────────────────

class FakeCandidacyLlmClient:
    """Declares whenever ambition_score >= 0.5, mirroring how a real model
    would use the two signals build_candidacy_user_prompt actually sends --
    lets tests assert on chunking/order/support-signal behavior without a
    live model."""

    def __init__(self):
        self.calls: list[list[int]] = []
        self.received_support: dict[int, float] = {}

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        cids = [c["cid"] for c in payload["citizens"]]
        self.calls.append(cids)
        for c in payload["citizens"]:
            self.received_support[c["cid"]] = c["perceived_support"]
        decisions = [
            {"cid": c["cid"], "outcome": 1, "motif": 203}
            if c["ambition_score"] >= 0.5
            else {"cid": c["cid"], "outcome": 0, "motif": 201}
            for c in payload["citizens"]
        ]
        return json.dumps({"decisions": decisions})


def _citizen_with_ambition(cid, ambition_score):
    c = _citizen(cid, (0.5,))
    return dataclasses.replace(c, ambition_score=ambition_score)


def test_decide_candidacies_preserves_order_across_chunk_boundaries():
    citizens = _population(50, dims=1)
    config = _config_with_llm_enabled(max_batch_size=25)
    client = FakeCandidacyLlmClient()

    outcome = decide_candidacies(citizens, config, client)

    assert client.calls == [list(range(25)), list(range(25, 50))]
    assert [d.cid for d in outcome.decisions] == list(range(50))


def test_decide_candidacies_outcome_reflects_ambition_threshold():
    citizens = [_citizen_with_ambition(i, ambition_score) for i, ambition_score in enumerate([0.9] * 20 + [0.1] * 20)]
    config = _config_with_llm_enabled(max_batch_size=40)
    client = FakeCandidacyLlmClient()

    outcome = decide_candidacies(citizens, config, client)

    assert [d.outcome for d in outcome.decisions[:20]] == [1] * 20
    assert [d.outcome for d in outcome.decisions[20:]] == [0] * 20


def test_decide_candidacies_support_signal_is_population_wide_not_chunk_scoped():
    # sympathizer_ratio's denominator is len(population) -- if
    # decide_candidacies recomputed it per-chunk instead of once against the
    # full population before chunking, every citizen's ratio would be
    # inflated (smaller denominator) relative to the population-wide truth.
    citizens = _population(40, dims=1)
    config = _config_with_llm_enabled(max_batch_size=20)
    client = FakeCandidacyLlmClient()
    full_population_support = {c.citizen_id: round(sympathizer_ratio(c, citizens), 4) for c in citizens}

    decide_candidacies(citizens, config, client)

    assert client.received_support == full_population_support


def test_decide_candidacies_raises_notimplementederror_for_unsupported_provider():
    citizens = _population(20)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm"))
    with pytest.raises(NotImplementedError, match="provider"):
        decide_candidacies(citizens, config, FakeCandidacyLlmClient())


def test_decide_candidacies_raises_for_dynamic_batch_sharding():
    citizens = _population(20)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, batch_sharding="dynamic"))
    with pytest.raises(NotImplementedError, match="batch_sharding"):
        decide_candidacies(citizens, config, FakeCandidacyLlmClient())


def test_decide_candidacies_raises_for_intra_run_workers_above_one():
    citizens = _population(20)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parallel=dataclasses.replace(config.parallel, intra_run_workers=2))
    with pytest.raises(NotImplementedError, match="intra_run_workers"):
        decide_candidacies(citizens, config, FakeCandidacyLlmClient())


def test_decide_candidacies_raises_for_codebook_version_mismatch():
    citizens = _population(20)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, codebook_version="0.9"))
    with pytest.raises(Exception, match="codebook_version"):
        decide_candidacies(citizens, config, FakeCandidacyLlmClient())


def test_decide_candidacies_propagates_llm_response_error_on_count_mismatch():
    citizens = _population(20)
    config = _config_with_llm_enabled()

    class ShortClient:
        def complete_json(self, **kwargs):
            return json.dumps({"decisions": [{"cid": 0, "outcome": 0, "motif": 201}]})

    with pytest.raises(LlmResponseError, match="misaligned"):
        decide_candidacies(citizens, config, ShortClient())


# ── build_party_nomination_system_prompt / build_party_nomination_user_prompt ──

def _party(party_id, platform):
    return Party(party_id=party_id, platform=tuple(platform))


def test_party_nomination_system_prompt_enumerates_every_expected_party_id():
    contested = {
        0: [_citizen(0, (0.5,)), _citizen(1, (0.5,))],
        2: [_citizen(2, (0.5,)), _citizen(3, (0.5,))],
    }
    prompt = build_party_nomination_system_prompt(contested)
    assert "[0,2]" in prompt
    assert "EXACTEMENT ces 2 party_id" in prompt


def test_party_nomination_system_prompt_describes_candidates_by_position_not_cid():
    contested = {0: [_citizen(11, (0.5,)), _citizen(10, (0.5,))]}
    prompt = build_party_nomination_system_prompt(contested)
    assert "position" in prompt
    assert "cid" in prompt


def test_party_nomination_user_prompt_carries_signals_per_candidate():
    citizens = [_citizen_with_ambition(0, 0.8), _citizen_with_ambition(1, 0.2)]
    contested = {0: citizens}
    parties_by_id = {0: _party(0, (0.5,))}
    support = {0: 0.3, 1: 0.7}

    payload = json.loads(build_party_nomination_user_prompt(contested, parties_by_id, support))

    party_block = payload["parties"][0]
    assert party_block["party_id"] == 0
    by_cid = {c["cid"]: c for c in party_block["candidates"]}
    assert by_cid[0]["ambition_score"] == 0.8
    assert by_cid[0]["perceived_support"] == 0.3
    assert by_cid[1]["perceived_support"] == 0.7
    assert by_cid[0]["position"] == 1  # sorted by citizen_id ascending, not input order
    assert by_cid[1]["position"] == 2


def test_party_nomination_user_prompt_platform_distance_is_zero_at_the_platform():
    citizen = _citizen(0, (0.5, 0.5))
    contested = {0: [citizen]}
    parties_by_id = {0: _party(0, (0.5, 0.5))}
    payload = json.loads(build_party_nomination_user_prompt(contested, parties_by_id, {0: 0.0}))
    assert payload["parties"][0]["candidates"][0]["platform_distance"] == 0.0


def test_party_nomination_user_prompt_is_deterministic_for_the_same_inputs():
    citizens = [_citizen_with_ambition(0, 0.8), _citizen_with_ambition(1, 0.2)]
    contested = {0: citizens}
    parties_by_id = {0: _party(0, (0.5,))}
    support = {0: 0.3, 1: 0.7}
    assert build_party_nomination_user_prompt(contested, parties_by_id, support) == build_party_nomination_user_prompt(
        contested, parties_by_id, support
    )


# ── resolve_party_nomination_cid ──────────────────────────────────────────

def test_resolve_party_nomination_cid_maps_position_back_to_the_right_citizen():
    members = [_citizen(5, (0.5,)), _citizen(2, (0.5,)), _citizen(9, (0.5,))]  # sorted by cid: 2, 5, 9
    decision = PartyNominationDecision(party_id=0, winner_position=2, motif=206)
    assert resolve_party_nomination_cid(decision, members) == 5


# ── decide_party_nominations (FakePartyNominationLlmClient) ─────────────────

class FakePartyNominationLlmClient:
    """Picks the highest-ambition candidate per party, mirroring one of the
    signals build_party_nomination_user_prompt actually sends -- lets tests
    assert on order/resolution/skip-when-uncontested behavior without a live
    model."""

    def __init__(self):
        self.calls: list[list[int]] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        party_ids = [p["party_id"] for p in payload["parties"]]
        self.calls.append(party_ids)
        decisions = [
            {
                "party_id": p["party_id"],
                "winner_position": max(p["candidates"], key=lambda c: c["ambition_score"])["position"],
                "motif": 206,
            }
            for p in payload["parties"]
        ]
        return json.dumps({"decisions": decisions})


def test_decide_party_nominations_returns_empty_and_skips_the_client_when_nothing_is_contested():
    citizens = _population(3, dims=1)
    for c in citizens:
        c.party_affiliation = 0
    parties = [_party(0, (0.5,))]
    config = _config_with_llm_enabled()
    client = FakePartyNominationLlmClient()

    # Only citizen 0 is "declared" -- a single declared member needs no
    # arbitration at all.
    outcome = decide_party_nominations(citizens, parties, {0}, config, client)

    assert outcome.decisions == []
    assert outcome.winners == {}
    assert client.calls == []


def test_decide_party_nominations_preserves_party_id_order_regardless_of_input_order():
    citizens = _population(6, dims=1)
    for i, c in enumerate(citizens):
        c.party_affiliation = i // 3  # cids 0,1,2 -> party 0; cids 3,4,5 -> party 1
    parties = [_party(1, (0.5,)), _party(0, (0.5,))]  # deliberately out of order
    config = _config_with_llm_enabled()
    client = FakePartyNominationLlmClient()
    declared_cids = {c.citizen_id for c in citizens}

    outcome = decide_party_nominations(citizens, parties, declared_cids, config, client)

    assert client.calls == [[0, 1]]  # sorted ascending, never the input `parties` order
    assert set(outcome.winners.keys()) == {0, 1}


def test_decide_party_nominations_resolves_winner_position_back_to_the_right_cid():
    citizens = [_citizen_with_ambition(0, 0.9), _citizen_with_ambition(1, 0.1)]
    for c in citizens:
        c.party_affiliation = 0
    parties = [_party(0, (0.5,))]
    config = _config_with_llm_enabled()
    client = FakePartyNominationLlmClient()

    outcome = decide_party_nominations(citizens, parties, {0, 1}, config, client)

    assert outcome.winners[0] == 0  # citizen 0 has the higher ambition_score
    assert outcome.decisions[0].motif == 206


def test_decide_party_nominations_raises_notimplementederror_for_unsupported_provider():
    citizens = _population(2)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm"))
    with pytest.raises(NotImplementedError, match="provider"):
        decide_party_nominations(citizens, [], set(), config, FakePartyNominationLlmClient())


def test_decide_party_nominations_raises_for_dynamic_batch_sharding():
    citizens = _population(2)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, batch_sharding="dynamic"))
    with pytest.raises(NotImplementedError, match="batch_sharding"):
        decide_party_nominations(citizens, [], set(), config, FakePartyNominationLlmClient())


def test_decide_party_nominations_raises_for_intra_run_workers_above_one():
    citizens = _population(2)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parallel=dataclasses.replace(config.parallel, intra_run_workers=2))
    with pytest.raises(NotImplementedError, match="intra_run_workers"):
        decide_party_nominations(citizens, [], set(), config, FakePartyNominationLlmClient())


def test_decide_party_nominations_raises_for_codebook_version_mismatch():
    citizens = _population(2)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, codebook_version="0.9"))
    with pytest.raises(Exception, match="codebook_version"):
        decide_party_nominations(citizens, [], set(), config, FakePartyNominationLlmClient())


def test_decide_party_nominations_propagates_llm_response_error_on_count_mismatch():
    citizens = [
        _citizen_with_ambition(0, 0.9),
        _citizen_with_ambition(1, 0.1),
        _citizen_with_ambition(2, 0.9),
        _citizen_with_ambition(3, 0.1),
    ]
    citizens[0].party_affiliation = 0
    citizens[1].party_affiliation = 0
    citizens[2].party_affiliation = 1
    citizens[3].party_affiliation = 1
    parties = [_party(0, (0.5,)), _party(1, (0.5,))]
    config = _config_with_llm_enabled()
    declared_cids = {0, 1, 2, 3}

    class ShortClient:
        def complete_json(self, **kwargs):
            return json.dumps({"decisions": [{"party_id": 0, "winner_position": 1, "motif": 206}]})

    with pytest.raises(LlmResponseError, match="misaligned"):
        decide_party_nominations(citizens, parties, declared_cids, config, ShortClient())


# ── apply_shifts ──────────────────────────────────────────────────────────

def test_apply_shifts_moves_only_the_targeted_dimension():
    sincere = (0.5, 0.5, 0.5)
    shifted = apply_shifts(sincere, [PositionShift(dimension=1, delta=0.2)])
    assert shifted == (0.5, 0.7, 0.5)


def test_apply_shifts_clamps_at_the_upper_bound():
    shifted = apply_shifts((0.9,), [PositionShift(dimension=0, delta=0.5)])
    assert shifted == (1.0,)


def test_apply_shifts_clamps_at_the_lower_bound():
    shifted = apply_shifts((0.1,), [PositionShift(dimension=0, delta=-0.5)])
    assert shifted == (0.0,)


def test_apply_shifts_with_no_shifts_returns_the_sincere_position_unchanged():
    sincere = (0.3, 0.7)
    assert apply_shifts(sincere, []) == sincere


# ── validate_positioning_decision ────────────────────────────────────────

def _positioning_decision(**overrides):
    base = {"cid": 1, "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 602}
    base.update(overrides)
    return PositioningDecision.model_validate(base)


def test_validate_positioning_decision_accepts_within_bounds():
    config = _config_with_llm_enabled()
    validate_positioning_decision(_positioning_decision(), config)  # must not raise


def test_validate_positioning_decision_rejects_too_many_shifts():
    config = _config_with_llm_enabled()  # default campaign.max_positioning_shifts=3
    decision = _positioning_decision(shifts=[{"dimension": i, "delta": 0.1} for i in range(4)])
    with pytest.raises(LlmResponseError, match="max_positioning_shifts"):
        validate_positioning_decision(decision, config)


def test_validate_positioning_decision_rejects_delta_exceeding_the_cap():
    config = _config_with_llm_enabled()  # default campaign.max_positioning_delta=0.3
    decision = _positioning_decision(shifts=[{"dimension": 0, "delta": 0.9}])
    with pytest.raises(LlmResponseError, match="max_positioning_delta"):
        validate_positioning_decision(decision, config)


def test_validate_positioning_decision_rejects_out_of_range_dimension():
    config = _config_with_llm_enabled()  # default citizens.issue_count=20
    decision = _positioning_decision(shifts=[{"dimension": 999, "delta": 0.1}])
    with pytest.raises(LlmResponseError, match="out of range"):
        validate_positioning_decision(decision, config)


# ── build_positioning_system_prompt / build_positioning_user_prompt ────────

def test_positioning_system_prompt_enumerates_every_expected_cid():
    nominees = [_citizen(0, (0.5,)), _citizen(1, (0.5,)), _citizen(2, (0.5,))]
    config = _config_with_llm_enabled()
    prompt = build_positioning_system_prompt(nominees, config)
    assert "[0,1,2]" in prompt
    assert "EXACTEMENT ces 3" in prompt


def test_positioning_system_prompt_states_the_actual_numeric_bounds():
    # The JSON schema only enforces a loose structural ceiling (max 5
    # shifts, delta in [-1,1]) -- the model needs the REAL, tighter,
    # config-driven bound stated explicitly or it has no way to comply.
    nominees = [_citizen(0, (0.5,))]
    config = _config_with_llm_enabled()  # default max_positioning_shifts=3, max_positioning_delta=0.3
    prompt = build_positioning_system_prompt(nominees, config)
    assert "3 ajustements" in prompt
    assert "0.3" in prompt


def test_positioning_user_prompt_carries_rivals_and_electorate_mean():
    a = _citizen(0, (0.2, 0.2))
    b = _citizen(1, (0.8, 0.8))
    payload = json.loads(build_positioning_user_prompt([a, b], {}, electorate_mean=(0.5, 0.5)))
    assert payload["electorate_mean"] == [0.5, 0.5]
    by_cid = {n["cid"]: n for n in payload["nominees"]}
    assert by_cid[0]["rivals"] == [{"cid": 1, "position": [0.8, 0.8]}]
    assert by_cid[1]["rivals"] == [{"cid": 0, "position": [0.2, 0.2]}]
    assert by_cid[0]["party_platform"] is None  # party_affiliation is None by default


def test_positioning_user_prompt_includes_party_platform_when_affiliated():
    a = _citizen(0, (0.2,))
    a.party_affiliation = 7
    parties_by_id = {7: _party(7, (0.6,))}
    payload = json.loads(build_positioning_user_prompt([a], parties_by_id, electorate_mean=(0.5,)))
    assert payload["nominees"][0]["party_platform"] == [0.6]


def test_positioning_user_prompt_is_deterministic_for_the_same_inputs():
    nominees = [_citizen(0, (0.5,)), _citizen(1, (0.5,))]
    assert build_positioning_user_prompt(nominees, {}, (0.5,)) == build_positioning_user_prompt(nominees, {}, (0.5,))


# ── decide_campaign_positioning (FakePositioningLlmClient) ──────────────────

class FakePositioningLlmClient:
    """Always answers sincere (empty shifts, motif=SINCERE_CONVICTION) --
    lets tests assert on order/skip-when-empty/resolution behavior without
    a live model asserting anything about actual shift content."""

    def __init__(self):
        self.calls: list[list[int]] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        cids = [n["cid"] for n in payload["nominees"]]
        self.calls.append(cids)
        decisions = [{"cid": cid, "shifts": [], "motif": 601} for cid in cids]
        return json.dumps({"decisions": decisions})


def test_decide_campaign_positioning_returns_empty_and_skips_the_client_when_no_nominees():
    config = _config_with_llm_enabled()
    client = FakePositioningLlmClient()
    citizens = _population(5, dims=1)

    outcome = decide_campaign_positioning([], citizens, {}, config, client)

    assert outcome.decisions == []
    assert outcome.platforms == {}
    assert client.calls == []


def test_decide_campaign_positioning_sorts_nominees_by_citizen_id_regardless_of_input_order():
    citizens = _population(5, dims=1)
    nominees = [citizens[3], citizens[0], citizens[4]]  # deliberately out of order
    config = _config_with_llm_enabled()
    client = FakePositioningLlmClient()

    decide_campaign_positioning(nominees, citizens, {}, config, client)

    assert client.calls == [[0, 3, 4]]


def test_decide_campaign_positioning_resolves_platforms_from_shifts():
    citizens = _population(3, dims=2)
    nominees = [citizens[0]]
    config = _config_with_llm_enabled()

    class ShiftingClient:
        def complete_json(self, **kwargs):
            payload = json.loads(kwargs["user_prompt"])
            cid = payload["nominees"][0]["cid"]
            return json.dumps({"decisions": [{"cid": cid, "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 602}]})

    outcome = decide_campaign_positioning(nominees, citizens, {}, config, ShiftingClient())

    expected = apply_shifts(citizens[0].issue_positions, [PositionShift(dimension=0, delta=0.1)])
    assert outcome.platforms[citizens[0].citizen_id] == expected


def test_decide_campaign_positioning_raises_notimplementederror_for_unsupported_provider():
    citizens = _population(2)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm"))
    with pytest.raises(NotImplementedError, match="provider"):
        decide_campaign_positioning(citizens, citizens, {}, config, FakePositioningLlmClient())


def test_decide_campaign_positioning_raises_for_dynamic_batch_sharding():
    citizens = _population(2)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, batch_sharding="dynamic"))
    with pytest.raises(NotImplementedError, match="batch_sharding"):
        decide_campaign_positioning(citizens, citizens, {}, config, FakePositioningLlmClient())


def test_decide_campaign_positioning_raises_for_intra_run_workers_above_one():
    citizens = _population(2)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parallel=dataclasses.replace(config.parallel, intra_run_workers=2))
    with pytest.raises(NotImplementedError, match="intra_run_workers"):
        decide_campaign_positioning(citizens, citizens, {}, config, FakePositioningLlmClient())


def test_decide_campaign_positioning_raises_for_codebook_version_mismatch():
    citizens = _population(2)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, codebook_version="0.9"))
    with pytest.raises(Exception, match="codebook_version"):
        decide_campaign_positioning(citizens, citizens, {}, config, FakePositioningLlmClient())


def test_decide_campaign_positioning_propagates_llm_response_error_on_count_mismatch():
    citizens = _population(2)
    config = _config_with_llm_enabled()

    class ShortClient:
        def complete_json(self, **kwargs):
            return json.dumps({"decisions": [{"cid": 0, "shifts": [], "motif": 601}]})

    with pytest.raises(LlmResponseError, match="misaligned"):
        decide_campaign_positioning(citizens, citizens, {}, config, ShortClient())


# ── validate_response_decision (v4 Lot 6) ────────────────────────────────

def _holder(cid, positions, revealed=None):
    c = _citizen(cid, positions)
    c.pledged_platform = c.issue_positions
    c.revealed_position = revealed if revealed is not None else c.issue_positions
    return c


def _response_decision(**overrides):
    base = {"cid": 1, "shifts": [{"dimension": 0, "delta": 0.1}], "stance": 1, "motif": 301}
    base.update(overrides)
    return ResponseDecision.model_validate(base)


def _response_context(cid, **overrides):
    base = {"cid": cid, "legitimacy": 0.5, "mandate_dev": 0.0, "street": 0.0, "lame_duck": False, "ticks_left": 6}
    base.update(overrides)
    return ResponseContext(**base)


def test_validate_response_decision_accepts_within_bounds():
    config = _config_with_llm_enabled()  # default mandate.max_response_shifts=3, max_response_delta=0.3
    validate_response_decision(_response_decision(), config)  # must not raise


def test_validate_response_decision_rejects_too_many_shifts():
    config = _config_with_llm_enabled()
    decision = _response_decision(shifts=[{"dimension": i, "delta": 0.1} for i in range(4)])
    with pytest.raises(LlmResponseError, match="max_response_shifts"):
        validate_response_decision(decision, config)


def test_validate_response_decision_rejects_delta_exceeding_the_cap():
    config = _config_with_llm_enabled()
    decision = _response_decision(shifts=[{"dimension": 0, "delta": 0.9}])
    with pytest.raises(LlmResponseError, match="max_response_delta"):
        validate_response_decision(decision, config)


def test_validate_response_decision_rejects_out_of_range_dimension():
    config = _config_with_llm_enabled()  # default citizens.issue_count=20
    decision = _response_decision(shifts=[{"dimension": 999, "delta": 0.1}])
    with pytest.raises(LlmResponseError, match="out of range"):
        validate_response_decision(decision, config)


def test_validate_response_decision_uses_mandate_bounds_not_campaign_bounds():
    # mandate.* and campaign.* must stay analytically separable -- a
    # decision within the (loosened) campaign bounds but outside the
    # shipped mandate bounds must still be rejected.
    config = _config_with_llm_enabled()
    config = dataclasses.replace(
        config, campaign=dataclasses.replace(config.campaign, max_positioning_delta=1.0, max_positioning_shifts=5)
    )
    decision = _response_decision(shifts=[{"dimension": 0, "delta": 0.9}])  # exceeds mandate.max_response_delta=0.3
    with pytest.raises(LlmResponseError, match="max_response_delta"):
        validate_response_decision(decision, config)


# ── build_response_system_prompt / build_response_user_prompt ───────────

def test_response_system_prompt_enumerates_every_expected_cid():
    holders = [_holder(0, (0.5,)), _holder(1, (0.5,)), _holder(2, (0.5,))]
    config = _config_with_llm_enabled()
    prompt = build_response_system_prompt(holders, config)
    assert "[0,1,2]" in prompt
    assert "EXACTEMENT ces 3" in prompt


def test_response_system_prompt_states_the_actual_numeric_bounds():
    holders = [_holder(0, (0.5,))]
    config = _config_with_llm_enabled()  # default max_response_shifts=3, max_response_delta=0.3
    prompt = build_response_system_prompt(holders, config)
    assert "3 ajustements" in prompt
    assert "0.3" in prompt


def test_response_system_prompt_carries_the_stance_and_motif_tables():
    holders = [_holder(0, (0.5,))]
    config = _config_with_llm_enabled()
    prompt = build_response_system_prompt(holders, config)
    assert "1 = CONCESSION" in prompt
    assert "301 = MANDATE_DEVIATION_HIGH" in prompt


def test_response_system_prompt_states_the_stance_motif_pairing_rule():
    holders = [_holder(0, (0.5,))]
    config = _config_with_llm_enabled()
    prompt = build_response_system_prompt(holders, config)
    assert "stance=1" in prompt and "301" in prompt
    assert "stance=3" in prompt and "308" in prompt


def test_response_user_prompt_carries_pledged_revealed_and_ctx():
    holder = _holder(0, (0.2, 0.4), revealed=(0.3, 0.4))
    contexts = {0: _response_context(0, legitimacy=0.6, mandate_dev=0.1, street=0.2, lame_duck=True, ticks_left=3)}
    payload = json.loads(build_response_user_prompt([holder], contexts))
    block = payload["holders"][0]
    assert block["cid"] == 0
    assert block["pledged_platform"] == [0.2, 0.4]
    assert block["revealed_position"] == [0.3, 0.4]
    assert block["ctx"] == {"L": 0.6, "mandate_dev": 0.1, "street": 0.2, "lame_duck": 1, "ticks_left": 3}


def test_response_user_prompt_emits_null_for_untracked_ctx_fields():
    holder = _holder(0, (0.5,))
    contexts = {0: _response_context(0, legitimacy=None, street=None, ticks_left=None)}
    payload = json.loads(build_response_user_prompt([holder], contexts))
    ctx = payload["holders"][0]["ctx"]
    assert ctx["L"] is None
    assert ctx["street"] is None
    assert ctx["ticks_left"] is None
    assert ctx["mandate_dev"] == 0.0  # never null -- always tracked whenever this function runs at all


def test_response_user_prompt_is_deterministic_for_the_same_inputs():
    holders = [_holder(0, (0.5,)), _holder(1, (0.5,))]
    contexts = {0: _response_context(0), 1: _response_context(1)}
    assert build_response_user_prompt(holders, contexts) == build_response_user_prompt(holders, contexts)


def test_response_user_prompt_ctx_matches_the_journalled_ctx_payload():
    # One serialization, two consumers (the prompt and the journal write in
    # run_polity_simulation.py) -- both must read from to_payload().
    holder = _holder(0, (0.5,))
    context = _response_context(0, legitimacy=0.7, mandate_dev=0.2, street=1.5, lame_duck=False, ticks_left=9)
    payload = json.loads(build_response_user_prompt([holder], {0: context}))
    assert payload["holders"][0]["ctx"] == context.to_payload()


# ── decide_representative_response (FakeResponseLlmClient, v4 Lot 6) ────

class FakeResponseLlmClient:
    """Always answers silence (empty shifts, motif=STRATEGIC_AMBIGUITY) --
    lets tests assert on order/skip-when-empty/resolution behavior without
    a live model asserting anything about actual shift content."""

    def __init__(self):
        self.calls: list[list[int]] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        cids = [h["cid"] for h in payload["holders"]]
        self.calls.append(cids)
        decisions = [{"cid": cid, "shifts": [], "stance": 3, "motif": 308} for cid in cids]
        return json.dumps({"decisions": decisions})


def test_decide_representative_response_returns_empty_and_skips_the_client_when_no_holders():
    config = _config_with_llm_enabled()
    client = FakeResponseLlmClient()

    outcome = decide_representative_response([], {}, config, client)

    assert outcome.decisions == []
    assert outcome.positions == {}
    assert client.calls == []


def test_decide_representative_response_sorts_holders_by_citizen_id_regardless_of_input_order():
    holders = [_holder(3, (0.5,)), _holder(0, (0.5,)), _holder(4, (0.5,))]
    contexts = {h.citizen_id: _response_context(h.citizen_id) for h in holders}
    config = _config_with_llm_enabled()
    client = FakeResponseLlmClient()

    decide_representative_response(holders, contexts, config, client)

    assert client.calls == [[0, 3, 4]]


def test_decide_representative_response_applies_shifts_on_top_of_revealed_position():
    holder = _holder(0, (0.2, 0.2), revealed=(0.4, 0.2))  # already drifted from the pledge
    contexts = {0: _response_context(0)}
    config = _config_with_llm_enabled()

    class ShiftingClient:
        def complete_json(self, **kwargs):
            payload = json.loads(kwargs["user_prompt"])
            cid = payload["holders"][0]["cid"]
            decision = {"cid": cid, "shifts": [{"dimension": 0, "delta": 0.1}], "stance": 1, "motif": 301}
            return json.dumps({"decisions": [decision]})

    outcome = decide_representative_response([holder], contexts, config, ShiftingClient())

    # base is revealed_position (0.4), NOT pledged_platform (0.2) -- drift accumulates.
    expected = apply_shifts((0.4, 0.2), [PositionShift(dimension=0, delta=0.1)])
    assert outcome.positions[0] == expected


def test_decide_representative_response_leaves_pledged_platform_untouched():
    holder = _holder(0, (0.2,), revealed=(0.2,))
    contexts = {0: _response_context(0)}
    config = _config_with_llm_enabled()

    class ShiftingClient:
        def complete_json(self, **kwargs):
            decision = {"cid": 0, "shifts": [{"dimension": 0, "delta": 0.1}], "stance": 1, "motif": 301}
            return json.dumps({"decisions": [decision]})

    decide_representative_response([holder], contexts, config, ShiftingClient())

    assert holder.pledged_platform == (0.2,)  # decide_representative_response never resolves a pledge


def test_decide_representative_response_raises_notimplementederror_for_unsupported_provider():
    holder = _holder(0, (0.5,))
    contexts = {0: _response_context(0)}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm"))
    with pytest.raises(NotImplementedError, match="provider"):
        decide_representative_response([holder], contexts, config, FakeResponseLlmClient())


def test_decide_representative_response_raises_for_dynamic_batch_sharding():
    holder = _holder(0, (0.5,))
    contexts = {0: _response_context(0)}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, batch_sharding="dynamic"))
    with pytest.raises(NotImplementedError, match="batch_sharding"):
        decide_representative_response([holder], contexts, config, FakeResponseLlmClient())


def test_decide_representative_response_raises_for_intra_run_workers_above_one():
    holder = _holder(0, (0.5,))
    contexts = {0: _response_context(0)}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parallel=dataclasses.replace(config.parallel, intra_run_workers=2))
    with pytest.raises(NotImplementedError, match="intra_run_workers"):
        decide_representative_response([holder], contexts, config, FakeResponseLlmClient())


def test_decide_representative_response_raises_for_codebook_version_mismatch():
    holder = _holder(0, (0.5,))
    contexts = {0: _response_context(0)}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, codebook_version="0.9"))
    with pytest.raises(Exception, match="codebook_version"):
        decide_representative_response([holder], contexts, config, FakeResponseLlmClient())


def test_decide_representative_response_propagates_llm_response_error_on_count_mismatch():
    holders = [_holder(0, (0.5,)), _holder(1, (0.5,))]
    contexts = {h.citizen_id: _response_context(h.citizen_id) for h in holders}
    config = _config_with_llm_enabled()

    class ShortClient:
        def complete_json(self, **kwargs):
            return json.dumps({"decisions": [{"cid": 0, "shifts": [], "stance": 3, "motif": 308}]})

    with pytest.raises(LlmResponseError, match="misaligned"):
        decide_representative_response(holders, contexts, config, ShortClient())


def test_decide_representative_response_ignores_a_later_street_pressure_mutation():
    # The structural half of the one-tick lag: a ResponseContext is an
    # already-frozen snapshot, so mutating holder.street_pressure AFTER
    # contexts are built can never reach the user prompt -- pinned
    # independently of call-site ordering (run_polity_simulation.py's own
    # test pins the call-site half).
    holder = _holder(0, (0.5,))
    holder.street_pressure = 0.3
    contexts = {0: _response_context(0, street=holder.street_pressure)}
    before = build_response_user_prompt([holder], contexts)

    holder.street_pressure = 99.0  # a later, unrelated mutation

    after = build_response_user_prompt([holder], contexts)
    assert before == after


# ── assemble_coalition ────────────────────────────────────────────────────

_TIEBREAK = ("seats", "votes", "party_id")


def _coalition_decision(party_id, action=1, motif=501):
    return CoalitionDecision(party_id=party_id, action=action, motif=motif)


def test_assemble_coalition_unanimous_join_matches_form_coalition():
    # Same fixture as test_polity_simple_rules.py's
    # test_form_coalition_adds_nearest_neighbours_until_majority: initiator
    # 0 needs a partner, party 1 is nearest. Unanimous join should isolate
    # the LLM's contribution to nothing -- byte-identical to the baseline.
    platforms = {0: (0.0, 0.0), 1: (0.1, 0.0), 2: (0.5, 0.5), 3: (1.0, 1.0)}
    seats = {0: 30, 1: 25, 2: 20, 3: 25}
    votes = {0: 30.0, 1: 25.0, 2: 25.0, 3: 20.0}
    baseline = form_coalition(platforms, seats, votes, _TIEBREAK, majority_ratio=0.5)
    decisions = [_coalition_decision(pid) for pid in (1, 2, 3)]  # all join

    result = assemble_coalition(decisions, initiator=0, party_platforms=platforms, seats=seats, majority_ratio=0.5)

    assert result == baseline == [0, 1]


def test_assemble_coalition_adds_joiners_in_ascending_distance():
    platforms = {0: (0.0,), 1: (0.9,), 2: (0.2,), 3: (0.5,)}
    seats = {0: 10, 1: 30, 2: 30, 3: 30}
    decisions = [_coalition_decision(pid) for pid in (1, 2, 3)]
    result = assemble_coalition(decisions, initiator=0, party_platforms=platforms, seats=seats, majority_ratio=0.5)
    assert result == [0, 2, 3]  # nearest (2) then next (3); 10+30+30=70 > 50


def test_assemble_coalition_distance_tie_breaks_on_seats_descending_then_party_id():
    platforms = {0: (0.0,), 1: (0.3,), 2: (0.3,), 3: (0.5,)}
    seats = {0: 40, 1: 20, 2: 15, 3: 25}
    decisions = [_coalition_decision(pid) for pid in (1, 2, 3)]
    result = assemble_coalition(decisions, initiator=0, party_platforms=platforms, seats=seats, majority_ratio=0.5)
    assert result == [0, 1]  # 1/2 equidistant, 1 has more seats, 40+20=60 > 50


def test_assemble_coalition_a_leave_from_the_nearest_party_pushes_the_next_nearest_in():
    platforms = {0: (0.0,), 1: (0.1,), 2: (0.9,)}
    seats = {0: 30, 1: 25, 2: 45}
    decisions = [_coalition_decision(1, action=2, motif=504), _coalition_decision(2)]
    result = assemble_coalition(decisions, initiator=0, party_platforms=platforms, seats=seats, majority_ratio=0.5)
    assert result == [0, 2]  # 1 declined; 2 (the only joiner) is added: 30+45=75 > 50


def test_assemble_coalition_all_decline_with_a_minority_initiator_returns_none():
    platforms = {0: (0.0,), 1: (0.1,), 2: (0.9,)}
    seats = {0: 30, 1: 25, 2: 45}
    decisions = [_coalition_decision(1, action=2, motif=504), _coalition_decision(2, action=2, motif=504)]
    result = assemble_coalition(decisions, initiator=0, party_platforms=platforms, seats=seats, majority_ratio=0.5)
    assert result is None


def test_assemble_coalition_initiator_alone_above_threshold_ignores_decisions():
    platforms = {0: (0.0,), 1: (0.1,)}
    seats = {0: 60, 1: 40}
    # Even a `leave`-only decision list must not matter -- the initiator
    # already clears the majority alone.
    decisions = [_coalition_decision(1, action=2, motif=504)]
    result = assemble_coalition(decisions, initiator=0, party_platforms=platforms, seats=seats, majority_ratio=0.5)
    assert result == [0]


def test_assemble_coalition_returns_none_when_joiners_are_insufficient():
    platforms = {0: (0.0,), 1: (0.1,), 2: (0.9,)}
    seats = {0: 20, 1: 15, 2: 65}
    decisions = [_coalition_decision(1), _coalition_decision(2, action=2, motif=504)]
    result = assemble_coalition(decisions, initiator=0, party_platforms=platforms, seats=seats, majority_ratio=0.5)
    assert result is None  # 20 + 15 = 35, never exceeds 50% of 100


def test_assemble_coalition_boundary_exactly_at_threshold_is_not_a_majority():
    platforms = {0: (0.0,), 1: (0.1,)}
    seats = {0: 50, 1: 50}
    decisions = [_coalition_decision(1)]
    result = assemble_coalition(decisions, initiator=0, party_platforms=platforms, seats=seats, majority_ratio=0.5)
    assert result == [0, 1]  # exactly 50 alone is not >50% of 100; needs both


# ── validate_coalition_decision ──────────────────────────────────────────

def test_validate_coalition_decision_accepts_a_seated_non_initiator():
    seats = {0: 30, 1: 25}
    validate_coalition_decision(_coalition_decision(1), seats, initiator=0)  # must not raise


def test_validate_coalition_decision_rejects_a_zero_seat_party():
    seats = {0: 30, 1: 0}
    with pytest.raises(LlmResponseError, match="does not hold a seat"):
        validate_coalition_decision(_coalition_decision(1), seats, initiator=0)


def test_validate_coalition_decision_rejects_the_initiator():
    seats = {0: 30, 1: 25}
    with pytest.raises(LlmResponseError, match="is the initiator"):
        validate_coalition_decision(_coalition_decision(0), seats, initiator=0)


# ── build_coalition_system_prompt / build_coalition_user_prompt ─────────

def test_coalition_system_prompt_enumerates_every_expected_party_id():
    prompt = build_coalition_system_prompt([1, 2, 3], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0)
    assert "[1,2,3]" in prompt
    assert "EXACTEMENT ces 3 party_id" in prompt


def test_coalition_system_prompt_states_the_actual_institutional_numbers():
    prompt = build_coalition_system_prompt([1], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0)
    assert "100" in prompt
    assert "50.0" in prompt
    assert "30" in prompt


def test_coalition_system_prompt_contains_action_and_motif_tables():
    prompt = build_coalition_system_prompt([1], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0)
    assert "1 = JOIN" in prompt
    assert "2 = LEAVE" in prompt
    assert "501 = IDEOLOGICAL_PROXIMITY" in prompt
    assert "504 = IDEOLOGICAL_DISTANCE_TOO_HIGH" in prompt


def test_coalition_system_prompt_states_the_action_motif_coherence_rule():
    prompt = build_coalition_system_prompt([1], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0)
    assert "501" in prompt and "502" in prompt and "504" in prompt and "505" in prompt


def test_coalition_system_prompt_contains_no_coalition_theory_framing():
    # §3.3: the LLM gets the rules of the game and raw data, never a
    # steering heuristic ("prefer a minimal winning coalition" etc.) --
    # strategic behavior (or its absence) must be genuinely emergent.
    prompt = build_coalition_system_prompt([1, 2], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0)
    forbidden = ["minimal", "minimale", "stable", "small coalition", "petite coalition", "prefer", "privilegie"]
    lowered = prompt.lower()
    for term in forbidden:
        assert term not in lowered


def test_coalition_user_prompt_carries_distance_seats_and_votes_per_responder():
    platforms = {0: (0.0,), 1: (0.3,)}
    seats = {0: 30, 1: 25}
    votes = {0: 300.0, 1: 250.0}
    payload = json.loads(
        build_coalition_user_prompt([1], initiator=0, party_platforms=platforms, seats=seats, votes=votes,
                                     total_seats=100, majority_seats_threshold=50.0)
    )
    responder = payload["responders"][0]
    assert responder["party_id"] == 1
    assert responder["seats"] == 25
    assert responder["votes"] == 250.0
    assert responder["distance_to_initiator"] == pytest.approx(0.3)
    assert payload["initiator"]["party_id"] == 0
    assert payload["assembly"]["total_seats"] == 100


def test_coalition_user_prompt_distance_is_zero_at_the_initiators_platform():
    platforms = {0: (0.5, 0.5), 1: (0.5, 0.5)}
    seats = {0: 30, 1: 25}
    votes = {0: 30.0, 1: 25.0}
    payload = json.loads(
        build_coalition_user_prompt([1], initiator=0, party_platforms=platforms, seats=seats, votes=votes,
                                     total_seats=100, majority_seats_threshold=50.0)
    )
    assert payload["responders"][0]["distance_to_initiator"] == 0.0


def test_coalition_user_prompt_is_deterministic_for_the_same_inputs():
    platforms = {0: (0.0,), 1: (0.3,)}
    seats = {0: 30, 1: 25}
    votes = {0: 30.0, 1: 25.0}
    args = ([1], 0, platforms, seats, votes, 100, 50.0)
    assert build_coalition_user_prompt(*args) == build_coalition_user_prompt(*args)


def test_coalition_user_prompt_is_independent_of_dict_iteration_order():
    platforms_a = {0: (0.0,), 1: (0.3,), 2: (0.6,)}
    platforms_b = {2: (0.6,), 0: (0.0,), 1: (0.3,)}
    seats = {0: 30, 1: 25, 2: 20}
    votes = {0: 30.0, 1: 25.0, 2: 20.0}
    a = build_coalition_user_prompt([1, 2], 0, platforms_a, seats, votes, 100, 50.0)
    b = build_coalition_user_prompt([1, 2], 0, platforms_b, seats, votes, 100, 50.0)
    assert a == b


def test_coalition_user_prompt_top_level_key_is_responders():
    payload = json.loads(
        build_coalition_user_prompt([1], initiator=0, party_platforms={0: (0.0,), 1: (0.1,)}, seats={0: 30, 1: 25},
                                     votes={0: 30.0, 1: 25.0}, total_seats=100, majority_seats_threshold=50.0)
    )
    assert "responders" in payload
    assert "citizens" not in payload
    assert "parties" not in payload
    assert "nominees" not in payload


# ── decide_coalition (FakeCoalitionLlmClient) ────────────────────────────

class FakeCoalitionLlmClient:
    """Always answers `join` with motif=IDEOLOGICAL_PROXIMITY -- lets tests
    assert on skip-the-client / order / resolution behavior without a live
    model asserting anything about actual willingness content."""

    def __init__(self):
        self.calls: list[list[int]] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        party_ids = [r["party_id"] for r in payload["responders"]]
        self.calls.append(party_ids)
        decisions = [{"party_id": pid, "action": 1, "motif": 501} for pid in party_ids]
        return json.dumps({"decisions": decisions})


def _parties_from_seats(seats):
    return [Party(party_id=pid, platform=(round(pid * 0.1, 4),)) for pid in seats]


def test_decide_coalition_skips_the_client_when_no_party_is_seated():
    seats = {0: 0, 1: 0}
    votes = {0: 0.0, 1: 0.0}
    config = _config_with_llm_enabled()
    client = FakeCoalitionLlmClient()

    outcome = decide_coalition(_parties_from_seats(seats), seats, votes, config, client)

    assert outcome.decisions == []
    assert outcome.initiator is None
    assert outcome.coalition is None
    assert client.calls == []


def test_decide_coalition_skips_the_client_when_the_initiator_alone_has_a_majority():
    seats = {0: 60, 1: 40}
    votes = {0: 60.0, 1: 40.0}
    config = _config_with_llm_enabled()
    client = FakeCoalitionLlmClient()

    outcome = decide_coalition(_parties_from_seats(seats), seats, votes, config, client)

    assert outcome.initiator == 0
    assert outcome.coalition == [0]
    assert outcome.decisions == []
    assert client.calls == []


def test_decide_coalition_skips_the_client_when_there_is_exactly_one_seated_party():
    # majority_ratio=1.0 forces this: a lone party's 100% share equals the
    # threshold exactly (strict `>` never satisfied), so there ARE no
    # responders to ask, unlike with the shipped default of 0.5 where a
    # lone seated party always exceeds the threshold and hits the
    # already-a-majority short-circuit instead (see the test above).
    seats = {0: 30}
    votes = {0: 30.0}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parties=dataclasses.replace(config.parties, coalition_majority_ratio=1.0))
    client = FakeCoalitionLlmClient()

    outcome = decide_coalition(_parties_from_seats(seats), seats, votes, config, client)

    assert outcome.initiator == 0
    assert outcome.coalition is None
    assert client.calls == []


def test_decide_coalition_sorts_responders_by_party_id_regardless_of_input_order():
    seats = {3: 10, 0: 30, 1: 25, 2: 20}
    votes = {3: 10.0, 0: 30.0, 1: 25.0, 2: 20.0}
    parties = [Party(party_id=pid, platform=(round(pid * 0.1, 4),)) for pid in (3, 1, 0, 2)]  # deliberately out of order
    config = _config_with_llm_enabled()
    client = FakeCoalitionLlmClient()

    decide_coalition(parties, seats, votes, config, client)

    assert client.calls == [[1, 2, 3]]  # initiator 0 excluded, rest ascending


def test_decide_coalition_resolves_a_mixed_join_leave_batch_into_the_right_coalition():
    seats = {0: 45, 1: 25, 2: 30}  # party 0 has the most seats -- it is the initiator
    votes = {0: 45.0, 1: 25.0, 2: 30.0}
    parties = [Party(party_id=0, platform=(0.0,)), Party(party_id=1, platform=(0.1,)), Party(party_id=2, platform=(0.9,))]
    config = _config_with_llm_enabled()

    class MixedClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"party_id": r["party_id"], "action": 2, "motif": 504} if r["party_id"] == 1
                else {"party_id": r["party_id"], "action": 1, "motif": 501}
                for r in payload["responders"]
            ]
            return json.dumps({"decisions": decisions})

    outcome = decide_coalition(parties, seats, votes, config, MixedClient())

    assert outcome.initiator == 0
    assert outcome.coalition == [0, 2]  # party 1 declined; party 2 (the only joiner) reaches majority
    assert {d.party_id: d.action for d in outcome.decisions} == {1: 2, 2: 1}


def test_decide_coalition_all_decline_returns_none_coalition():
    seats = {0: 45, 1: 25, 2: 30}  # party 0 has the most seats -- it is the initiator, and 45 alone is a minority
    votes = {0: 45.0, 1: 25.0, 2: 30.0}
    parties = [Party(party_id=0, platform=(0.0,)), Party(party_id=1, platform=(0.1,)), Party(party_id=2, platform=(0.9,))]
    config = _config_with_llm_enabled()

    class AllDeclineClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [{"party_id": r["party_id"], "action": 2, "motif": 504} for r in payload["responders"]]
            return json.dumps({"decisions": decisions})

    outcome = decide_coalition(parties, seats, votes, config, AllDeclineClient())

    assert outcome.coalition is None


def test_decide_coalition_raises_notimplementederror_for_unsupported_provider():
    seats = {0: 30, 1: 25}
    votes = {0: 30.0, 1: 25.0}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm"))
    with pytest.raises(NotImplementedError, match="provider"):
        decide_coalition(_parties_from_seats(seats), seats, votes, config, FakeCoalitionLlmClient())


def test_decide_coalition_raises_for_dynamic_batch_sharding():
    seats = {0: 30, 1: 25}
    votes = {0: 30.0, 1: 25.0}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, batch_sharding="dynamic"))
    with pytest.raises(NotImplementedError, match="batch_sharding"):
        decide_coalition(_parties_from_seats(seats), seats, votes, config, FakeCoalitionLlmClient())


def test_decide_coalition_raises_for_intra_run_workers_above_one():
    seats = {0: 30, 1: 25}
    votes = {0: 30.0, 1: 25.0}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parallel=dataclasses.replace(config.parallel, intra_run_workers=2))
    with pytest.raises(NotImplementedError, match="intra_run_workers"):
        decide_coalition(_parties_from_seats(seats), seats, votes, config, FakeCoalitionLlmClient())


def test_decide_coalition_raises_for_codebook_version_mismatch():
    seats = {0: 30, 1: 25}
    votes = {0: 30.0, 1: 25.0}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, codebook_version="0.9"))
    with pytest.raises(Exception, match="codebook_version"):
        decide_coalition(_parties_from_seats(seats), seats, votes, config, FakeCoalitionLlmClient())


def test_decide_coalition_propagates_llm_response_error_on_count_mismatch():
    seats = {0: 30, 1: 25, 2: 20}
    votes = {0: 30.0, 1: 25.0, 2: 20.0}
    parties = _parties_from_seats(seats)
    config = _config_with_llm_enabled()

    class ShortClient:
        def complete_json(self, **kwargs):
            return json.dumps({"decisions": [{"party_id": 1, "action": 1, "motif": 501}]})

    with pytest.raises(LlmResponseError, match="misaligned"):
        decide_coalition(parties, seats, votes, config, ShortClient())


# ── menu_acts (v4 Lot 7) ──────────────────────────────────────────────────

def test_menu_acts_electoral_only_is_just_zero_and_four():
    menu = PressureMenuConfig(petition_enabled=False, mobilization_enabled=False, electoral_only=True)
    assert menu_acts(menu) == (0, 4)


def test_menu_acts_petition_only_adds_sign_and_launch():
    menu = PressureMenuConfig(petition_enabled=True, mobilization_enabled=False, electoral_only=False)
    assert menu_acts(menu) == (0, 1, 2, 4)


def test_menu_acts_mobilization_only_adds_mobilize():
    menu = PressureMenuConfig(petition_enabled=False, mobilization_enabled=True, electoral_only=False)
    assert menu_acts(menu) == (0, 3, 4)


def test_menu_acts_both_levers_reaches_every_act():
    menu = PressureMenuConfig(petition_enabled=True, mobilization_enabled=True, electoral_only=False)
    assert menu_acts(menu) == (0, 1, 2, 3, 4)


# ── validate_pressure_decision (v4 Lot 7) ────────────────────────────────

def _pressure_decision(**overrides):
    base = {"cid": 1, "target": 205, "act": 3, "motif": 301}
    base.update(overrides)
    return PressureDecision.model_validate(base)


def _pressure_context(cid, **overrides):
    base = {
        "cid": cid, "target": 205, "self_gap": 0.5, "mandate_dev": 0.1, "ticks_to_election": 6,
        "available": (0, 3, 4), "petition_open": False, "petition_expires_at_tick": None, "already_signed": False,
    }
    base.update(overrides)
    return PressureContext(**base)


def test_validate_pressure_decision_accepts_an_in_menu_act():
    config = _config_with_llm_enabled()
    config = dataclasses.replace(
        config, pressure_menu=PressureMenuConfig(petition_enabled=False, mobilization_enabled=True, electoral_only=False)
    )
    context = _pressure_context(1)
    validate_pressure_decision(_pressure_decision(act=3), context, config)  # must not raise


def test_validate_pressure_decision_rejects_an_out_of_menu_act():
    config = _config_with_llm_enabled()
    config = dataclasses.replace(
        config, pressure_menu=PressureMenuConfig(petition_enabled=False, mobilization_enabled=False, electoral_only=True)
    )
    context = _pressure_context(1)
    with pytest.raises(LlmResponseError, match="outside the active"):
        validate_pressure_decision(_pressure_decision(act=3), context, config)


def test_validate_pressure_decision_always_accepts_act_0_and_4_under_every_menu():
    config = _config_with_llm_enabled()
    config = dataclasses.replace(
        config, pressure_menu=PressureMenuConfig(petition_enabled=False, mobilization_enabled=False, electoral_only=True)
    )
    context = _pressure_context(1)
    validate_pressure_decision(_pressure_decision(act=0, motif=304), context, config)
    validate_pressure_decision(_pressure_decision(act=4, motif=305), context, config)


def test_validate_pressure_decision_rejects_a_mismatched_target():
    config = _config_with_llm_enabled()
    context = _pressure_context(1, target=205)
    with pytest.raises(LlmResponseError, match="targets"):
        validate_pressure_decision(_pressure_decision(target=999), context, config)


def test_validate_pressure_decision_does_not_reject_an_unavailable_but_in_menu_act():
    # The two-tier split's central proof: `act` is legal under the menu but
    # NOT in this citizen's frozen `available` list (e.g. no petition is
    # open) -- validate_pressure_decision must not care. Live state is
    # resolved later, at application time, via applicable_pressure_act.
    config = _config_with_llm_enabled()
    config = dataclasses.replace(
        config, pressure_menu=PressureMenuConfig(petition_enabled=True, mobilization_enabled=False, electoral_only=False)
    )
    context = _pressure_context(1, available=(0, 4))  # petition not currently available to this citizen
    validate_pressure_decision(_pressure_decision(act=1, motif=301), context, config)  # must not raise


# ── build_pressure_system_prompt / build_pressure_user_prompt (v4 Lot 7) ─

def _pressure_citizen(cid, positions=(0.5,)):
    return _citizen(cid, positions)


def test_pressure_system_prompt_enumerates_every_expected_cid():
    consulted = [_pressure_citizen(0), _pressure_citizen(1), _pressure_citizen(2)]
    config = _config_with_llm_enabled()
    prompt = build_pressure_system_prompt(consulted, config)
    assert "[0,1,2]" in prompt
    assert "EXACTEMENT ces 3" in prompt


def test_pressure_system_prompt_states_the_active_menu_only():
    consulted = [_pressure_citizen(0)]
    config = _config_with_llm_enabled()
    config = dataclasses.replace(
        config, pressure_menu=PressureMenuConfig(petition_enabled=False, mobilization_enabled=False, electoral_only=True)
    )
    prompt = build_pressure_system_prompt(consulted, config)
    assert "[0, 4]" in prompt
    assert "1 = SIGN_PETITION" not in prompt
    assert "3 = MOBILIZE" not in prompt


def test_pressure_system_prompt_carries_the_act_and_motif_tables():
    consulted = [_pressure_citizen(0)]
    config = _config_with_llm_enabled()  # shipped menu has both levers reachable enough to show every act
    prompt = build_pressure_system_prompt(consulted, config)
    assert "301 = MANDATE_DEVIATION_HIGH" in prompt


def test_pressure_user_prompt_carries_ctx_available_and_petition_state():
    citizen = _pressure_citizen(7)
    context = _pressure_context(7, target=205, self_gap=0.61, mandate_dev=0.41, ticks_to_election=9,
                                 available=(0, 1, 4), petition_open=True, petition_expires_at_tick=14, already_signed=False)
    payload = json.loads(build_pressure_user_prompt([citizen], {7: context}))
    block = payload["consulted"][0]
    assert block["cid"] == 7
    assert block["target"] == 205
    assert block["available"] == [0, 1, 4]
    assert block["petition"] == {"open": True, "expires_at_tick": 14, "already_signed": False}
    assert block["ctx"] == {"self_gap": 0.61, "mandate_dev": 0.41, "neighbors_acting": None, "ticks_to_election": 9}


def test_pressure_user_prompt_never_mentions_street_pressure_or_signature_counts():
    citizen = _pressure_citizen(0)
    context = _pressure_context(0, petition_open=True, petition_expires_at_tick=10)
    prompt = build_pressure_user_prompt([citizen], {0: context})
    for forbidden in ("street", "signed_ratio", "signatures", "mobilization_rate"):
        assert forbidden not in prompt


def test_pressure_user_prompt_emits_null_neighbors_acting_for_every_citizen():
    citizens = [_pressure_citizen(0), _pressure_citizen(1)]
    contexts = {0: _pressure_context(0), 1: _pressure_context(1)}
    payload = json.loads(build_pressure_user_prompt(citizens, contexts))
    for block in payload["consulted"]:
        assert block["ctx"]["neighbors_acting"] is None


def test_pressure_user_prompt_is_deterministic_for_the_same_inputs():
    citizens = [_pressure_citizen(0), _pressure_citizen(1)]
    contexts = {0: _pressure_context(0), 1: _pressure_context(1)}
    assert build_pressure_user_prompt(citizens, contexts) == build_pressure_user_prompt(citizens, contexts)


def test_pressure_user_prompt_ctx_matches_the_journalled_ctx_payload():
    # One serialization, two consumers (the prompt and the journal write in
    # run_polity_simulation.py) -- both must read from to_payload().
    citizen = _pressure_citizen(0)
    context = _pressure_context(0, self_gap=0.3, mandate_dev=0.2, ticks_to_election=5)
    payload = json.loads(build_pressure_user_prompt([citizen], {0: context}))
    assert payload["consulted"][0]["ctx"] == context.to_payload()


# ── decide_pressure_actions (FakePressureLlmClient, v4 Lot 7) ───────────

class FakePressureLlmClient:
    """Always mobilizes (act=3, motif=301) -- lets tests assert on
    chunking/order/resolution behavior without a live model."""

    def __init__(self):
        self.calls: list[list[int]] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        cids = [c["cid"] for c in payload["consulted"]]
        self.calls.append(cids)
        decisions = [{"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in payload["consulted"]]
        return json.dumps({"decisions": decisions})


def _pressure_population(n, target=205):
    return [_pressure_citizen(i) for i in range(n)]


def _pressure_contexts(citizens, target=205):
    return {c.citizen_id: _pressure_context(c.citizen_id, target=target) for c in citizens}


def _config_with_pressure_llm_enabled(max_batch_size=25):
    # act=3 (MOBILIZE), the fake client's fixed answer, needs mobilization_enabled.
    config = _config_with_llm_enabled(max_batch_size=max_batch_size)
    return dataclasses.replace(
        config, pressure_menu=PressureMenuConfig(petition_enabled=False, mobilization_enabled=True, electoral_only=False)
    )


def test_decide_pressure_actions_returns_empty_and_skips_the_client_when_no_one_is_consulted():
    config = _config_with_llm_enabled()
    client = FakePressureLlmClient()

    outcome = decide_pressure_actions([], {}, config, client)

    assert outcome.decisions == []
    assert client.calls == []


def test_decide_pressure_actions_sorts_by_citizen_id_regardless_of_input_order():
    citizens = [_pressure_citizen(3), _pressure_citizen(0), _pressure_citizen(4)]
    contexts = _pressure_contexts(citizens)
    config = _config_with_pressure_llm_enabled()
    client = FakePressureLlmClient()

    decide_pressure_actions(citizens, contexts, config, client)

    assert client.calls == [[0, 3, 4]]


def test_decide_pressure_actions_calls_once_for_a_cohort_of_three():
    # The case MIN_SAFE_BATCH_SIZE's default floor would have aborted --
    # the concrete reason decide_pressure_actions passes min_batch_size=1.
    citizens = _pressure_population(3)
    contexts = _pressure_contexts(citizens)
    config = _config_with_pressure_llm_enabled()
    client = FakePressureLlmClient()

    outcome = decide_pressure_actions(citizens, contexts, config, client)

    assert client.calls == [[0, 1, 2]]
    assert [d.cid for d in outcome.decisions] == [0, 1, 2]


def test_decide_pressure_actions_chunks_a_large_cohort_at_max_batch_size():
    citizens = _pressure_population(60)
    contexts = _pressure_contexts(citizens)
    config = _config_with_pressure_llm_enabled(max_batch_size=25)
    client = FakePressureLlmClient()

    outcome = decide_pressure_actions(citizens, contexts, config, client)

    assert len(client.calls) == 3
    assert sorted(cid for call in client.calls for cid in call) == list(range(60))
    assert [d.cid for d in outcome.decisions] == list(range(60))


def test_decide_pressure_actions_raises_notimplementederror_for_unsupported_provider():
    citizens = _pressure_population(3)
    contexts = _pressure_contexts(citizens)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm"))
    with pytest.raises(NotImplementedError, match="provider"):
        decide_pressure_actions(citizens, contexts, config, FakePressureLlmClient())


def test_decide_pressure_actions_raises_for_dynamic_batch_sharding():
    citizens = _pressure_population(3)
    contexts = _pressure_contexts(citizens)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, batch_sharding="dynamic"))
    with pytest.raises(NotImplementedError, match="batch_sharding"):
        decide_pressure_actions(citizens, contexts, config, FakePressureLlmClient())


def test_decide_pressure_actions_raises_for_intra_run_workers_above_one():
    citizens = _pressure_population(3)
    contexts = _pressure_contexts(citizens)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parallel=dataclasses.replace(config.parallel, intra_run_workers=2))
    with pytest.raises(NotImplementedError, match="intra_run_workers"):
        decide_pressure_actions(citizens, contexts, config, FakePressureLlmClient())


def test_decide_pressure_actions_raises_for_codebook_version_mismatch():
    citizens = _pressure_population(3)
    contexts = _pressure_contexts(citizens)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, codebook_version="0.9"))
    with pytest.raises(Exception, match="codebook_version"):
        decide_pressure_actions(citizens, contexts, config, FakePressureLlmClient())


def test_decide_pressure_actions_propagates_llm_response_error_on_count_mismatch():
    citizens = _pressure_population(3)
    contexts = _pressure_contexts(citizens)
    config = _config_with_llm_enabled()

    class ShortClient:
        def complete_json(self, **kwargs):
            return json.dumps({"decisions": [{"cid": 0, "target": 205, "act": 3, "motif": 301}]})

    with pytest.raises(LlmResponseError, match="misaligned"):
        decide_pressure_actions(citizens, contexts, config, ShortClient())


# ── _complete_and_decode_with_replay / llm.max_batch_replays (v4 Lot 8) ──

class _FlakyClient:
    """Answers malformed JSON (an LlmResponseError-raising decode) on its
    first `fail_times` calls, then `good_raw` on every call after --
    exercises _complete_and_decode_with_replay's retry loop without a live
    model. Records every (system_prompt, user_prompt) pair, so a test can
    assert the retried request is byte-identical to the original."""

    def __init__(self, fail_times, good_raw):
        self.fail_times = fail_times
        self.good_raw = good_raw
        self.calls = 0
        self.prompts: list[tuple[str, str]] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        self.calls += 1
        self.prompts.append((system_prompt, user_prompt))
        if self.calls <= self.fail_times:
            return "not valid json"
        return self.good_raw


class _AlwaysTransportFailingClient:
    def __init__(self):
        self.calls = 0

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        self.calls += 1
        raise LlmTransportError("connection refused")


def _replay_cases():
    """One (label, call) per decide_* entry point -- call(config, client) ->
    the decide_* invocation itself, and the single-decision good_raw JSON
    each one needs to succeed. vote_cast/candidacy_considered need >= 20
    citizens (chunk_voters's own MIN_SAFE_BATCH_SIZE floor, not overridden
    by either of those two callers); every other entry point batches a
    handful of officeholders/nominees/parties/consulted citizens and needs
    no such floor."""
    voters = _population(20, dims=1)
    vote_candidates = [_candidate(900, (0.5,))]
    vote_good = json.dumps({"decisions": [{"cid": v.citizen_id, "blank": 1, "ranking": [], "motif": 101} for v in voters]})

    candidacy_citizens = _population(20, dims=1)
    candidacy_good = json.dumps(
        {"decisions": [{"cid": c.citizen_id, "outcome": 0, "motif": 201} for c in candidacy_citizens]}
    )

    nomination_citizens = [_citizen_with_ambition(0, 0.9), _citizen_with_ambition(1, 0.1)]
    for c in nomination_citizens:
        c.party_affiliation = 0
    nomination_parties = [_party(0, (0.5,))]
    nomination_good = json.dumps({"decisions": [{"party_id": 0, "winner_position": 1, "motif": 206}]})

    positioning_nominees = [_citizen(0, (0.5,))]
    positioning_citizens = _population(3, dims=1)
    positioning_good = json.dumps({"decisions": [{"cid": 0, "shifts": [], "motif": 601}]})

    response_holder = _holder(0, (0.5,))
    response_contexts = {0: _response_context(0)}
    response_good = json.dumps({"decisions": [{"cid": 0, "shifts": [], "stance": 3, "motif": 308}]})

    pressure_citizen = _pressure_citizen(0)
    pressure_contexts = _pressure_contexts([pressure_citizen])
    pressure_good = json.dumps({"decisions": [{"cid": 0, "target": 205, "act": 4, "motif": 305}]})

    # party 0 (45 seats) does not clear the majority alone (threshold 50 of
    # 100), so a real client call happens -- unlike a simpler {0: 30, 1: 25}
    # fixture, where the initiator's own seats already exceed the majority
    # of the two-party total and decide_coalition short-circuits with no
    # client call at all.
    coalition_seats = {0: 45, 1: 25, 2: 30}
    coalition_votes = {0: 45.0, 1: 25.0, 2: 30.0}
    coalition_parties = _parties_from_seats(coalition_seats)
    coalition_good = json.dumps(
        {"decisions": [{"party_id": 1, "action": 1, "motif": 501}, {"party_id": 2, "action": 1, "motif": 501}]}
    )

    return [
        ("vote_cast", lambda config, client: cast_votes(voters, vote_candidates, config, client), vote_good),
        ("candidacy_considered", lambda config, client: decide_candidacies(candidacy_citizens, config, client), candidacy_good),
        (
            "party_nomination_choice",
            lambda config, client: decide_party_nominations(nomination_citizens, nomination_parties, {0, 1}, config, client),
            nomination_good,
        ),
        (
            "campaign_positioning",
            lambda config, client: decide_campaign_positioning(positioning_nominees, positioning_citizens, {}, config, client),
            positioning_good,
        ),
        (
            "representative_response",
            lambda config, client: decide_representative_response([response_holder], response_contexts, config, client),
            response_good,
        ),
        (
            "pressure_action",
            lambda config, client: decide_pressure_actions([pressure_citizen], pressure_contexts, config, client),
            pressure_good,
        ),
        (
            "coalition_decision",
            lambda config, client: decide_coalition(coalition_parties, coalition_seats, coalition_votes, config, client),
            coalition_good,
        ),
    ]


@pytest.mark.parametrize("label,call,good_raw", _replay_cases(), ids=[c[0] for c in _replay_cases()])
def test_max_batch_replays_zero_propagates_on_the_first_failure(label, call, good_raw):
    # Today's exact behavior, now explicitly pinned for every entry point --
    # the shipped default (0) must never retry.
    config = _config_with_llm_enabled()
    assert config.llm.max_batch_replays == 0
    client = _FlakyClient(fail_times=1, good_raw=good_raw)
    with pytest.raises(LlmResponseError):
        call(config, client)
    assert client.calls == 1


@pytest.mark.parametrize("label,call,good_raw", _replay_cases(), ids=[c[0] for c in _replay_cases()])
def test_max_batch_replays_recovers_after_failures_within_the_budget(label, call, good_raw):
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=2))
    client = _FlakyClient(fail_times=2, good_raw=good_raw)
    call(config, client)  # must not raise
    assert client.calls == 3
    assert client.prompts[0] == client.prompts[1] == client.prompts[2]  # byte-identical retries


@pytest.mark.parametrize("label,call,good_raw", _replay_cases(), ids=[c[0] for c in _replay_cases()])
def test_max_batch_replays_still_raises_once_the_budget_is_exhausted(label, call, good_raw):
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=2))
    client = _FlakyClient(fail_times=99, good_raw=good_raw)  # never recovers
    with pytest.raises(LlmResponseError):
        call(config, client)
    assert client.calls == 3  # 1 original + 2 replays, then give up


def test_max_batch_replays_never_catches_a_transport_error():
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=2))
    citizen = _pressure_citizen(0)
    contexts = _pressure_contexts([citizen])
    client = _AlwaysTransportFailingClient()
    with pytest.raises(LlmTransportError):
        decide_pressure_actions([citizen], contexts, config, client)
    assert client.calls == 1  # the client itself owns transport-level retries, not this layer
