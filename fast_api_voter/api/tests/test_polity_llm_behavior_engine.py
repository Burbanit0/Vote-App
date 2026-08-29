"""llm_behavior_engine.py — v2 increment 1's LLM replacement for build_ranking.
Offline only: a FakeLlmClient stands in for OllamaJsonClient, no network.
"""
import dataclasses
import json
import math

import pytest

from api.domain.polity.ballot_and_aggregation import get_presidential_winner
from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import EventType, VoteMotif
from api.domain.polity.config import PressureMenuConfig, load_config
from api.domain.polity.llm_behavior_engine import (
    MIN_SAFE_BATCH_SIZE,
    _VOTE_CAST_RETRY_TEMPERATURE,
    ChamberContext,
    PressureContext,
    ReactionContext,
    ResponseContext,
    VoteBatchOutcome,
    apply_shifts,
    assemble_coalition,
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
    build_reaction_system_prompt,
    build_reaction_user_prompt,
    build_response_system_prompt,
    build_response_user_prompt,
    build_system_prompt,
    build_user_prompt,
    cast_votes,
    chunk_voters,
    clamped_dimensions,
    compute_max_tokens,
    decide_campaign_positioning,
    decide_candidacies,
    decide_chamber_deliberation,
    decide_coalition,
    decide_party_nominations,
    decide_pressure_actions,
    decide_reaction_to_event,
    decide_representative_response,
    menu_acts,
    resolve_party_nomination_cid,
    truncation_limit,
    validate_chamber_decision,
    validate_coalition_decision,
    validate_decision,
    validate_positioning_decision,
    validate_pressure_decision,
    validate_reaction_decision,
    validate_response_decision,
)
from api.domain.polity.llm_client import LlmResponseError, LlmTransportError
from api.domain.polity.llm_schemas import (
    ChamberDecision,
    CoalitionDecision,
    PartyNominationDecision,
    PositioningDecision,
    PositionShift,
    PressureDecision,
    ReactionDecision,
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


def test_system_prompt_requires_every_acceptable_candidate_in_the_ranking():
    # The REGLE above this sentence is genuinely ambiguous between "rank the
    # acceptable ones" and "rank (i.e. pick) the closest acceptable one", and
    # that ambiguity was the root cause of a Mode A reasoning loop that
    # aborted two v6b acceptance runs under position_dist: factor_structure
    # -- the model solved the vote, then burned its whole 13 596-token budget
    # re-quoting this prompt without resolving the format question. See
    # build_system_prompt's docstring for the live diagnosis and the 25-call
    # verification. Pinned so a later prompt tidy-up cannot silently drop it.
    citizens = _population(2)
    candidates = [_candidate(10, (0.1,)), _candidate(11, (0.9,))]
    prompt = build_system_prompt(citizens, candidates)
    assert "CHAQUE candidat" in prompt
    assert "Ne te limite " in prompt


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
    # cast_votes chunks at its own dedicated _VOTE_CAST_MAX_CHUNK_SIZE (1),
    # never config.llm.max_batch_size (a real v6b acceptance run found
    # multi-voter batches collapse the model's per-voter distance reasoning,
    # and even chunk_size=3 kept hitting finish_reason='length' under a
    # widened token budget -- see cast_votes's own docstring). 7 voters at
    # chunk size 1: 7 chunks of exactly 1 voter each, one client call per
    # voter, in order.
    voters = _population(7, dims=1)
    candidates = [_candidate(100, (0.5,))]
    config = _config_with_llm_enabled(max_batch_size=25)
    client = FakeLlmClient({v.citizen_id: v for v in voters}, candidates)

    outcome = cast_votes(voters, candidates, config, client)

    assert client.calls == [[0], [1], [2], [3], [4], [5], [6]]
    assert len(outcome.ballots) == 7
    for ballot in outcome.ballots:
        assert BLANK_LABEL in ballot


def test_cast_votes_ballot_from_decision_blank_is_always_just_blank():
    voters = _population(20, dims=1, )
    candidates = [_candidate(100, (0.9,))]
    config = _config_with_llm_enabled()
    # blank_threshold=1.0 on every voter means nobody actually goes blank
    # in this fixture; force it via a client that always answers blank.
    # cast_votes now chunks at its own _VOTE_CAST_MAX_CHUNK_SIZE (1), so
    # the fake must answer only the cids in each chunk's own user_prompt,
    # not the whole population every time.
    client = FakeLlmClient({v.citizen_id: v for v in voters}, candidates)

    def _always_blank(*, user_prompt, **kwargs):  # type: ignore[no-untyped-def]
        cids = [v["cid"] for v in json.loads(user_prompt)["voters"]]
        return json.dumps({"decisions": [{"cid": cid, "blank": 1, "ranking": [], "motif": 101} for cid in cids]})

    client.complete_json = _always_blank  # type: ignore[method-assign]

    outcome = cast_votes(voters, candidates, config, client)
    assert all(ballot == [BLANK_LABEL] for ballot in outcome.ballots)


def test_cast_votes_raises_notimplementederror_for_unsupported_provider():
    voters = _population(20)
    candidates = [_candidate(100, (0.5,))]
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="api"))
    with pytest.raises(NotImplementedError, match="provider"):
        cast_votes(voters, candidates, config, FakeLlmClient({}, candidates))


def test_cast_votes_accepts_the_vllm_provider_with_identical_output():
    # v4 vLLM switch (§15bis.6): the engine never touches the concrete
    # client class, only LlmClientProtocol -- provider is a pure config
    # value from _check_supported's perspective, so the SAME FakeLlmClient
    # against the SAME inputs must produce identical output regardless of
    # which supported provider the config names.
    voters = _population(20, dims=1)
    candidates = [_candidate(100, (0.1,)), _candidate(101, (0.9,))]
    ollama_config = _config_with_llm_enabled()
    vllm_config = dataclasses.replace(ollama_config, llm=dataclasses.replace(ollama_config.llm, provider="vllm"))

    ollama_outcome = cast_votes(voters, candidates, ollama_config, FakeLlmClient({v.citizen_id: v for v in voters}, candidates))
    vllm_outcome = cast_votes(voters, candidates, vllm_config, FakeLlmClient({v.citizen_id: v for v in voters}, candidates))

    assert vllm_outcome.ballots == ollama_outcome.ballots


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
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="api"))
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
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="api"))
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


# ── clamped_dimensions ───────────────────────────────────────────────────────

def test_clamped_dimensions_detects_the_upper_bound():
    base = (0.9,)
    shifts = [PositionShift(dimension=0, delta=0.5)]
    result = apply_shifts(base, shifts)
    assert clamped_dimensions(base, shifts, result) == frozenset({0})


def test_clamped_dimensions_detects_the_lower_bound():
    base = (0.1,)
    shifts = [PositionShift(dimension=0, delta=-0.5)]
    result = apply_shifts(base, shifts)
    assert clamped_dimensions(base, shifts, result) == frozenset({0})


def test_clamped_dimensions_detects_multiple_dimensions_independently():
    base = (0.9, 0.5, 0.1)
    shifts = [
        PositionShift(dimension=0, delta=0.5),   # clamps (upper)
        PositionShift(dimension=1, delta=0.2),   # does not clamp
        PositionShift(dimension=2, delta=-0.5),  # clamps (lower)
    ]
    result = apply_shifts(base, shifts)
    assert clamped_dimensions(base, shifts, result) == frozenset({0, 2})


def test_clamped_dimensions_is_empty_when_nothing_clamps():
    base = (0.5, 0.5)
    shifts = [PositionShift(dimension=0, delta=0.2), PositionShift(dimension=1, delta=-0.2)]
    result = apply_shifts(base, shifts)
    assert clamped_dimensions(base, shifts, result) == frozenset()


def test_clamped_dimensions_is_empty_with_no_shifts():
    base = (0.5,)
    result = apply_shifts(base, [])
    assert clamped_dimensions(base, [], result) == frozenset()


def test_clamped_dimensions_landing_exactly_on_a_bound_is_not_clamped():
    # A shift whose raw target lands EXACTLY on 0.0 or 1.0 -- not beyond it --
    # is not a clamp: apply_shifts's own min/max is a no-op at the boundary,
    # so result == base + delta exactly, and clamped_dimensions must not
    # count it. This is the one case worth pinning explicitly, since a
    # naive "result == 0.0 or result == 1.0" check would get this backwards.
    base = (0.5,)
    shifts = [PositionShift(dimension=0, delta=0.5)]
    result = apply_shifts(base, shifts)
    assert result == (1.0,)
    assert clamped_dimensions(base, shifts, result) == frozenset()


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
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="api"))
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
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="api"))
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


# ── validate_chamber_decision (v6b Lot 3, §6bis.3) ───────────────────────

def _member(cid, positions, chamber=None, seat_until=16):
    c = _citizen(cid, positions)
    c.sortition_seat_until_tick = seat_until
    c.sortition_terms_served = 1
    c.chamber_position = chamber if chamber is not None else c.issue_positions
    return c


def _chamber_decision(**overrides):
    base = {"cid": 1, "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 702}
    base.update(overrides)
    return ChamberDecision.model_validate(base)


def _chamber_context(cid, **overrides):
    base = {"cid": cid, "ticks_left": 12}
    base.update(overrides)
    return ChamberContext(**base)


def test_validate_chamber_decision_accepts_within_bounds():
    config = _config_with_llm_enabled()  # default max_deliberation_shifts=3, max_deliberation_delta=0.3
    validate_chamber_decision(_chamber_decision(), config)  # must not raise


def test_validate_chamber_decision_rejects_too_many_shifts():
    config = _config_with_llm_enabled()
    decision = _chamber_decision(shifts=[{"dimension": i, "delta": 0.1} for i in range(4)])
    with pytest.raises(LlmResponseError, match="max_deliberation_shifts"):
        validate_chamber_decision(decision, config)


def test_validate_chamber_decision_rejects_delta_exceeding_the_cap():
    config = _config_with_llm_enabled()
    decision = _chamber_decision(shifts=[{"dimension": 0, "delta": 0.9}])
    with pytest.raises(LlmResponseError, match="max_deliberation_delta"):
        validate_chamber_decision(decision, config)


def test_validate_chamber_decision_rejects_out_of_range_dimension():
    config = _config_with_llm_enabled()  # default citizens.issue_count=20
    decision = _chamber_decision(shifts=[{"dimension": 999, "delta": 0.1}])
    with pytest.raises(LlmResponseError, match="out of range"):
        validate_chamber_decision(decision, config)


def test_validate_chamber_decision_uses_sortition_bounds_not_mandate_bounds():
    # sortition_chamber.* and mandate.* must stay analytically separable --
    # a decision within the (loosened) mandate bounds but outside the
    # shipped sortition_chamber bounds must still be rejected.
    config = _config_with_llm_enabled()
    config = dataclasses.replace(
        config, mandate=dataclasses.replace(config.mandate, max_response_delta=1.0, max_response_shifts=5)
    )
    decision = _chamber_decision(shifts=[{"dimension": 0, "delta": 0.9}])  # exceeds sortition_chamber.max_deliberation_delta=0.3
    with pytest.raises(LlmResponseError, match="max_deliberation_delta"):
        validate_chamber_decision(decision, config)


# ── build_chamber_system_prompt / build_chamber_user_prompt ─────────────

def test_chamber_system_prompt_enumerates_every_expected_cid():
    members = [_member(0, (0.5,)), _member(1, (0.5,)), _member(2, (0.5,))]
    config = _config_with_llm_enabled()
    prompt = build_chamber_system_prompt(members, config)
    assert "[0,1,2]" in prompt
    assert "EXACTEMENT ces 3" in prompt


def test_chamber_system_prompt_states_the_actual_numeric_bounds():
    members = [_member(0, (0.5,))]
    config = _config_with_llm_enabled()  # default max_deliberation_shifts=3, max_deliberation_delta=0.3
    prompt = build_chamber_system_prompt(members, config)
    assert "3 ajustements" in prompt
    assert "0.3" in prompt


def test_chamber_system_prompt_carries_the_motif_table():
    members = [_member(0, (0.5,))]
    config = _config_with_llm_enabled()
    prompt = build_chamber_system_prompt(members, config)
    assert "701 = SINCERE_POSITION" in prompt
    assert "702 = DELIBERATIVE_SHIFT" in prompt


def test_chamber_system_prompt_disambiguates_the_identical_position_case():
    # v6b Lot 5 correction: a live 270-call sweep found chamber_position==
    # sincere_position (true at seating time and for as long as a member
    # never picks motif=702) reliably triggers the model's own Mode A
    # (unbounded reasoning, 7/270 landed exactly on the token ceiling,
    # ~70-140x repeated "wait, maybe they differ" paragraphs) when left
    # unaddressed. Regression guard for the disambiguating sentence itself,
    # not the live behavior (see scripts/lot3_chamber_reliability_results.md
    # for the live verification that resolved all 7 failing cases).
    members = [_member(0, (0.5,))]
    config = _config_with_llm_enabled()
    prompt = build_chamber_system_prompt(members, config)
    assert "identique a sincere_position" in prompt


def test_chamber_user_prompt_carries_sincere_and_chamber_positions_and_ctx():
    member = _member(0, (0.2, 0.4), chamber=(0.3, 0.4))
    contexts = {0: _chamber_context(0, ticks_left=3)}
    payload = json.loads(build_chamber_user_prompt([member], contexts))
    block = payload["members"][0]
    assert block["cid"] == 0
    assert block["sincere_position"] == [0.2, 0.4]
    assert block["chamber_position"] == [0.3, 0.4]
    assert block["ctx"] == {"ticks_left": 3}


def test_chamber_user_prompt_is_deterministic_for_the_same_inputs():
    members = [_member(0, (0.5,)), _member(1, (0.5,))]
    contexts = {0: _chamber_context(0), 1: _chamber_context(1)}
    assert build_chamber_user_prompt(members, contexts) == build_chamber_user_prompt(members, contexts)


def test_chamber_user_prompt_ctx_matches_the_journalled_ctx_payload():
    # One serialization, two consumers (the prompt and the journal write in
    # run_polity_simulation.py) -- both must read from to_payload().
    member = _member(0, (0.5,))
    context = _chamber_context(0, ticks_left=9)
    payload = json.loads(build_chamber_user_prompt([member], {0: context}))
    assert payload["members"][0]["ctx"] == context.to_payload()


# ── decide_chamber_deliberation (FakeChamberLlmClient, v6b Lot 3) ───────

class FakeChamberLlmClient:
    """Always answers sincere (empty shifts, motif=SINCERE_POSITION) --
    lets tests assert on order/skip-when-empty/resolution behavior without
    a live model asserting anything about actual shift content."""

    def __init__(self):
        self.calls: list[list[int]] = []
        self.think_values: list[bool] = []
        self.max_tokens_values: list[int] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        cids = [m["cid"] for m in payload["members"]]
        self.calls.append(cids)
        self.think_values.append(think)
        self.max_tokens_values.append(max_tokens)
        decisions = [{"cid": cid, "shifts": [], "motif": 701} for cid in cids]
        return json.dumps({"decisions": decisions})


def test_decide_chamber_deliberation_returns_empty_and_skips_the_client_when_no_members():
    config = _config_with_llm_enabled()
    client = FakeChamberLlmClient()

    outcome = decide_chamber_deliberation([], {}, config, client)

    assert outcome.decisions == []
    assert outcome.positions == {}
    assert client.calls == []


def test_decide_chamber_deliberation_sorts_members_by_citizen_id_regardless_of_input_order():
    # _CHAMBER_MAX_CHUNK_SIZE=1 means each member reaches the client as its
    # own call -- the ordering guarantee (D-5) is now about CALL ORDER, not
    # grouping within one call.
    members = [_member(3, (0.5,)), _member(0, (0.5,)), _member(4, (0.5,))]
    contexts = {m.citizen_id: _chamber_context(m.citizen_id) for m in members}
    config = _config_with_llm_enabled()
    client = FakeChamberLlmClient()

    decide_chamber_deliberation(members, contexts, config, client)

    assert client.calls == [[0], [3], [4]]


def test_decide_chamber_deliberation_chunks_a_full_seats_sized_cohort_at_one():
    # A 30-member cohort (sortition_chamber.seats shipped) must reach the
    # client as THIRTY calls of 1 -- this lot's own pre-flight spike found
    # one call of 30 (and even a chunk of 15) silently drops all but the
    # last 6 decisions, so decide_chamber_deliberation chunks at its own
    # measured ceiling (_CHAMBER_MAX_CHUNK_SIZE), not config.llm.max_batch_
    # size (25). Cut from an original 10 -- via a tried-and-DISPROVEN
    # intermediate of 5 -- to 1 (vote_cast's own endpoint) after a real v6b
    # acceptance run (2026-08-21/22, GPU) hit finish_reason='length' on a
    # chunk_size=10 call, 3/3 attempts, all landing exactly on
    # n_decoded=10136 -- the deterministic "hits the configured ceiling"
    # signature (Mode B), not unbounded reasoning collapse (Mode A) --
    # fixed the same way _VOTE_CAST_MAX_CHUNK_SIZE's own history fixed an
    # analogous overflow: cut the chunk size, not the budget. Halving to 5
    # was tried first and reproduced the identical overflow on a different
    # sub-chunk with zero margin; chunk_size=1 was validated directly
    # against that same failing group before shipping -- see this
    # constant's own docstring / scripts/lot3_chamber_reliability_results.md.
    members = [_member(i, (0.5,)) for i in range(30)]
    contexts = {m.citizen_id: _chamber_context(m.citizen_id) for m in members}
    config = _config_with_llm_enabled()
    client = FakeChamberLlmClient()

    decide_chamber_deliberation(members, contexts, config, client)

    assert len(client.calls) == 30
    assert [len(c) for c in client.calls] == [1] * 30
    assert sorted(cid for call in client.calls for cid in call) == list(range(30))


def test_decide_chamber_deliberation_uses_think_true_and_the_reasoning_token_allowance():
    # v6b Lot 4 correction: a real acceptance run (2026-08-17, GPU) found a
    # specific 10-cid chunk that think=False reproducibly (8/8) dropped to
    # 4/10, well-formed JSON, not a truncation; think=True fixed that exact
    # chunk 6/6 direct against the real content. Mirrors decide_campaign_
    # positioning's own already-shipped think=False->True fix for an
    # analogous duplicate/drop failure. 8000 here mirrors the module's own
    # _CHAMBER_THINK_TOKEN_ALLOWANCE constant (llm_behavior_engine.py) --
    # corrected from an original 4000 after a real v6b acceptance run
    # (2026-08-20) hit finish_reason='length' on a chunk_size=10 call, 3/3,
    # deterministic budget exhaustion (not context truncation). 1 member
    # (not 10) since _CHAMBER_MAX_CHUNK_SIZE was itself later cut to 1
    # (via a disproven intermediate of 5) for the identical reason, two
    # calls up.
    members = [_member(0, (0.5,))]
    contexts = {m.citizen_id: _chamber_context(m.citizen_id) for m in members}
    config = _config_with_llm_enabled()
    client = FakeChamberLlmClient()

    decide_chamber_deliberation(members, contexts, config, client)

    assert client.think_values == [True]
    assert client.max_tokens_values == [compute_max_tokens(1) + 8000]


def test_decide_chamber_deliberation_applies_shifts_on_top_of_chamber_position():
    member = _member(0, (0.2, 0.2), chamber=(0.4, 0.2))  # already drifted from the sincere position
    contexts = {0: _chamber_context(0)}
    config = _config_with_llm_enabled()

    class ShiftingClient:
        def complete_json(self, **kwargs):
            payload = json.loads(kwargs["user_prompt"])
            cid = payload["members"][0]["cid"]
            decision = {"cid": cid, "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 702}
            return json.dumps({"decisions": [decision]})

    outcome = decide_chamber_deliberation([member], contexts, config, ShiftingClient())

    # base is chamber_position (0.4), NOT issue_positions (0.2) -- drift accumulates.
    expected = apply_shifts((0.4, 0.2), [PositionShift(dimension=0, delta=0.1)])
    assert outcome.positions[0] == expected


def test_decide_chamber_deliberation_leaves_issue_positions_untouched():
    member = _member(0, (0.2,), chamber=(0.2,))
    contexts = {0: _chamber_context(0)}
    config = _config_with_llm_enabled()

    class ShiftingClient:
        def complete_json(self, **kwargs):
            decision = {"cid": 0, "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 702}
            return json.dumps({"decisions": [decision]})

    decide_chamber_deliberation([member], contexts, config, ShiftingClient())

    assert member.issue_positions == (0.2,)  # decide_chamber_deliberation never resolves the sincere anchor


def test_decide_chamber_deliberation_raises_notimplementederror_for_unsupported_provider():
    member = _member(0, (0.5,))
    contexts = {0: _chamber_context(0)}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="api"))
    with pytest.raises(NotImplementedError, match="provider"):
        decide_chamber_deliberation([member], contexts, config, FakeChamberLlmClient())


def test_decide_chamber_deliberation_raises_for_dynamic_batch_sharding():
    member = _member(0, (0.5,))
    contexts = {0: _chamber_context(0)}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, batch_sharding="dynamic"))
    with pytest.raises(NotImplementedError, match="batch_sharding"):
        decide_chamber_deliberation([member], contexts, config, FakeChamberLlmClient())


def test_decide_chamber_deliberation_raises_for_intra_run_workers_above_one():
    member = _member(0, (0.5,))
    contexts = {0: _chamber_context(0)}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parallel=dataclasses.replace(config.parallel, intra_run_workers=2))
    with pytest.raises(NotImplementedError, match="intra_run_workers"):
        decide_chamber_deliberation([member], contexts, config, FakeChamberLlmClient())


def test_decide_chamber_deliberation_raises_for_codebook_version_mismatch():
    member = _member(0, (0.5,))
    contexts = {0: _chamber_context(0)}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, codebook_version="0.9"))
    with pytest.raises(Exception, match="codebook_version"):
        decide_chamber_deliberation([member], contexts, config, FakeChamberLlmClient())


def test_decide_chamber_deliberation_propagates_llm_response_error_on_count_mismatch():
    members = [_member(0, (0.5,)), _member(1, (0.5,))]
    contexts = {m.citizen_id: _chamber_context(m.citizen_id) for m in members}
    config = _config_with_llm_enabled()

    class ShortClient:
        def complete_json(self, **kwargs):
            return json.dumps({"decisions": [{"cid": 0, "shifts": [], "motif": 701}]})

    with pytest.raises(LlmResponseError, match="misaligned"):
        decide_chamber_deliberation(members, contexts, config, ShortClient())


def test_decide_chamber_deliberation_uses_replay():
    member = _member(0, (0.5,))
    contexts = {0: _chamber_context(0)}
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=1))

    class FlakyThenGoodClient:
        def __init__(self):
            self.attempts = 0

        def complete_json(self, **kwargs):
            self.attempts += 1
            if self.attempts == 1:
                return json.dumps({"decisions": [{"cid": 999, "shifts": [], "motif": 701}]})  # wrong cid
            return json.dumps({"decisions": [{"cid": 0, "shifts": [], "motif": 701}]})

    client = FlakyThenGoodClient()
    outcome = decide_chamber_deliberation([member], contexts, config, client)
    assert client.attempts == 2
    assert outcome.decisions[0].cid == 0


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


def test_coalition_system_prompt_round_one_is_byte_identical_to_omitting_round_number():
    # v7 Lot 2's own parity requirement (plan-coalition-negotiation-v7.md
    # §3): round 1 must reproduce the pre-v7 prompt exactly.
    args = ([1, 2], 0, 30, 100, 50.0)
    assert build_coalition_system_prompt(*args, round_number=1) == build_coalition_system_prompt(*args)


def test_coalition_system_prompt_round_two_names_it_a_revision_round():
    prompt = build_coalition_system_prompt([1], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0, round_number=2)
    assert "tour 2" in prompt


def test_coalition_user_prompt_round_one_is_byte_identical_to_omitting_prior_state():
    platforms = {0: (0.0,), 1: (0.3,)}
    seats = {0: 30, 1: 25}
    votes = {0: 30.0, 1: 25.0}
    args = ([1], 0, platforms, seats, votes, 100, 50.0)
    assert build_coalition_user_prompt(*args, prior_decisions=None, provisional_coalition_seats=None) == build_coalition_user_prompt(*args)


def test_coalition_user_prompt_round_two_carries_prior_decision_and_provisional_seats():
    platforms = {0: (0.0,), 1: (0.3,), 2: (0.6,)}
    seats = {0: 30, 1: 25, 2: 20}
    votes = {0: 30.0, 1: 25.0, 2: 20.0}
    prior = {1: _coalition_decision(1, action=2, motif=504), 2: _coalition_decision(2, action=1, motif=501)}
    payload = json.loads(
        build_coalition_user_prompt(
            [1, 2], 0, platforms, seats, votes, 100, 50.0,
            prior_decisions=prior, provisional_coalition_seats=50,
        )
    )
    assert payload["assembly"]["provisional_coalition_seats"] == 50
    responders_by_id = {r["party_id"]: r for r in payload["responders"]}
    assert responders_by_id[1]["prior_decision"] == {"action": 2, "motif": 504}
    assert responders_by_id[2]["prior_decision"] == {"action": 1, "motif": 501}


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
    # Pinned to one round -- this test is about ordering, not negotiation;
    # see the coalition_decision _replay_cases entry for the same reasoning.
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parties=dataclasses.replace(config.parties, coalition_max_negotiation_rounds=1))
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
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="api"))
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


def test_decide_coalition_round_one_llm_error_propagates_like_the_pre_v7_single_call():
    # Round 1's failure behavior must not change -- no new resilience claimed
    # for a path nothing about v7 touches (see decide_coalition's own
    # docstring). ShortClient above already covers a decode-time failure;
    # this covers complete_json raising directly, the other source
    # _complete_and_decode_with_replay's own docstring names.
    seats = {0: 45, 1: 25, 2: 30}
    votes = {0: 45.0, 1: 25.0, 2: 30.0}
    parties = [Party(party_id=0, platform=(0.0,)), Party(party_id=1, platform=(0.1,)), Party(party_id=2, platform=(0.9,))]
    config = _config_with_llm_enabled()

    class AlwaysFailsClient:
        def complete_json(self, **kwargs):
            raise LlmResponseError("generation did not finish cleanly: done_reason='length'")

    with pytest.raises(LlmResponseError, match="did not finish cleanly"):
        decide_coalition(parties, seats, votes, config, AlwaysFailsClient())


def test_decide_coalition_aborts_gracefully_on_a_round_two_failure():
    # Round >= 2 is the asymmetric case: caught, not propagated -- see
    # decide_coalition's own docstring for why this is a deliberate
    # divergence from round 1's (and every other decide_*'s) behavior.
    seats = {0: 45, 1: 25, 2: 30}
    votes = {0: 45.0, 1: 25.0, 2: 30.0}
    parties = [Party(party_id=0, platform=(0.0,)), Party(party_id=1, platform=(0.1,)), Party(party_id=2, platform=(0.9,))]
    config = _config_with_llm_enabled()

    class FailsFromRoundTwoClient:
        def __init__(self):
            self.calls = 0

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            self.calls += 1
            if self.calls > 1:
                raise LlmResponseError("generation did not finish cleanly: done_reason='length'")
            payload = json.loads(user_prompt)
            decisions = [{"party_id": r["party_id"], "action": 1, "motif": 501} for r in payload["responders"]]
            return json.dumps({"decisions": decisions})

    client = FailsFromRoundTwoClient()
    outcome = decide_coalition(parties, seats, votes, config, client)

    assert outcome.coalition is None
    assert outcome.aborted_at_round == 2
    assert len(outcome.rounds) == 1  # round 1's decisions were kept, not discarded
    assert outcome.decisions == outcome.rounds[0]
    assert client.calls == 2


def test_decide_coalition_stops_early_on_a_fixed_point_before_the_hard_cap():
    seats = {0: 45, 1: 25, 2: 30}
    votes = {0: 45.0, 1: 25.0, 2: 30.0}
    parties = [Party(party_id=0, platform=(0.0,)), Party(party_id=1, platform=(0.1,)), Party(party_id=2, platform=(0.9,))]
    config = _config_with_llm_enabled()
    # Cap well above what convergence actually needs, so an early stop here
    # is unambiguously the fixed-point check firing, not the hard cap.
    config = dataclasses.replace(config, parties=dataclasses.replace(config.parties, coalition_max_negotiation_rounds=5))

    class ConvergesAtRoundThreeClient:
        """Round 1 (no prior_decision yet): party 1 declines. Round >= 2
        (prior_decision now present): everyone joins, including party 1
        reconsidering -- exactly the conditional-reasoning case v7 exists
        for. Round 3 repeats round 2's answer, so round 3 is a fixed point
        even though round 1 != round 2."""

        def __init__(self):
            self.calls = 0

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            self.calls += 1
            payload = json.loads(user_prompt)
            decisions = []
            for r in payload["responders"]:
                if r.get("prior_decision") is None:
                    action, motif = (2, 504) if r["party_id"] == 1 else (1, 501)
                else:
                    action, motif = 1, 501
                decisions.append({"party_id": r["party_id"], "action": action, "motif": motif})
            return json.dumps({"decisions": decisions})

    client = ConvergesAtRoundThreeClient()
    outcome = decide_coalition(parties, seats, votes, config, client)

    assert client.calls == 3
    assert len(outcome.rounds) == 3
    assert outcome.aborted_at_round is None
    # both responders end up joining by round 3, but assemble_coalition's own
    # short-circuit (ascending distance to initiator, stop once majority is
    # cleared) never needs party 2 once party 1's 25 seats alone push the
    # 45-seat initiator past the 50-seat threshold (45+25=70>50) -- this
    # assertion is about that existing, unchanged assembly logic, not v7.
    assert outcome.coalition == [0, 1]
    # round 1's own outcome is still visible in the transcript, distinct from the final answer
    assert {d.party_id: d.action for d in outcome.rounds[0]} == {1: 2, 2: 1}


def test_decide_coalition_stops_at_the_hard_cap_when_never_converging():
    seats = {0: 45, 1: 25, 2: 30}
    votes = {0: 45.0, 1: 25.0, 2: 30.0}
    parties = [Party(party_id=0, platform=(0.0,)), Party(party_id=1, platform=(0.1,)), Party(party_id=2, platform=(0.9,))]
    config = _config_with_llm_enabled()  # shipped default: coalition_max_negotiation_rounds=3

    class NeverConvergesClient:
        """Flips every responder's action relative to their own prior round
        -- can never reach a fixed point by construction."""

        def __init__(self):
            self.calls = 0

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            self.calls += 1
            payload = json.loads(user_prompt)
            decisions = []
            for r in payload["responders"]:
                prior = r.get("prior_decision")
                action, motif = (1, 501) if prior is None or prior["action"] == 2 else (2, 504)
                decisions.append({"party_id": r["party_id"], "action": action, "motif": motif})
            return json.dumps({"decisions": decisions})

    client = NeverConvergesClient()
    outcome = decide_coalition(parties, seats, votes, config, client)

    assert client.calls == config.parties.coalition_max_negotiation_rounds == 3
    assert len(outcome.rounds) == 3
    assert outcome.aborted_at_round is None  # exhausting the cap is not a failure
    # rounds alternate JOIN/LEAVE/JOIN by construction -- round 1 and round 3 agree, round 2 differs from both
    assert outcome.rounds[0] != outcome.rounds[1]
    assert outcome.rounds[1] != outcome.rounds[2]


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


def test_pressure_system_prompt_states_toujours_null_when_the_graph_is_off():
    # v6 Lot 3 regression pin: the shipped default (social_graph.enabled
    # false, v4/v5's own atomized regime) must keep the exact pre-Lot-3
    # sentence. Note PRESSURE_MOTIF_PROMPT_TABLE always lists 306 (it
    # renders the full enum unconditionally) -- the pairing GUIDANCE
    # sentence is what's conditional, not the table itself.
    consulted = [_pressure_citizen(0)]
    config = _config_with_llm_enabled()
    assert config.social_graph.enabled is False
    prompt = build_pressure_system_prompt(consulted, config)
    assert "toujours null" in prompt
    assert "voisinage social qui a deja mobilise" not in prompt


def test_pressure_system_prompt_explains_the_real_fraction_when_the_graph_is_on():
    consulted = [_pressure_citizen(0)]
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, social_graph=dataclasses.replace(config.social_graph, enabled=True))
    prompt = build_pressure_system_prompt(consulted, config)
    assert "toujours null" not in prompt
    assert "voisinage social qui a deja mobilise" in prompt


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


def test_pressure_context_to_payload_rounds_a_real_neighbors_acting_fraction():
    context = _pressure_context(0, neighbors_acting=0.33333333)
    assert context.to_payload()["neighbors_acting"] == 0.3333


def test_pressure_context_to_payload_keeps_neighbors_acting_none():
    context = _pressure_context(0, neighbors_acting=None)
    assert context.to_payload()["neighbors_acting"] is None


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
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="api"))
    with pytest.raises(NotImplementedError, match="provider"):
        decide_pressure_actions(citizens, contexts, config, FakePressureLlmClient())


def test_decide_pressure_actions_accepts_the_vllm_provider():
    # The think=False side of the provider-acceptance pin above --
    # decide_pressure_actions is one of the six decision types that never
    # switch endpoints on Ollama (think=False throughout); vLLM has no
    # endpoint switch at all, so this just needs to not raise.
    citizens = _pressure_population(3)
    contexts = _pressure_contexts(citizens)
    config = _config_with_pressure_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm"))

    outcome = decide_pressure_actions(citizens, contexts, config, FakePressureLlmClient())

    assert [d.cid for d in outcome.decisions] == [0, 1, 2]


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


# ── validate_reaction_decision (v5 Lot 4, §8) ────────────────────────────

def _reaction_decision(**overrides):
    base = {"cid": 1, "salience_delta": 0.1, "motif": 401}
    base.update(overrides)
    return ReactionDecision.model_validate(base)


def test_validate_reaction_decision_accepts_the_grounding_motif_for_scandal():
    config = _config_with_llm_enabled()
    validate_reaction_decision(_reaction_decision(motif=401), EventType.SCANDAL, config)  # must not raise


def test_validate_reaction_decision_accepts_the_grounding_motif_for_economic_shock():
    config = _config_with_llm_enabled()
    decision = _reaction_decision(motif=402)
    validate_reaction_decision(decision, EventType.ECONOMIC_SHOCK, config)  # must not raise


def test_validate_reaction_decision_rejects_the_other_events_grounding_motif():
    config = _config_with_llm_enabled()
    with pytest.raises(LlmResponseError, match="not valid for"):
        validate_reaction_decision(_reaction_decision(motif=402), EventType.SCANDAL, config)
    with pytest.raises(LlmResponseError, match="not valid for"):
        validate_reaction_decision(_reaction_decision(salience_delta=0.1, motif=401), EventType.ECONOMIC_SHOCK, config)


def test_validate_reaction_decision_accepts_403_regardless_of_event_type():
    config = _config_with_llm_enabled()
    decision = _reaction_decision(salience_delta=0.0, motif=403)
    validate_reaction_decision(decision, EventType.SCANDAL, config)  # must not raise
    validate_reaction_decision(decision, EventType.ECONOMIC_SHOCK, config)  # must not raise


def test_validate_reaction_decision_rejects_a_delta_above_max_reaction_delta():
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, events=dataclasses.replace(config.events, max_reaction_delta=0.05))
    with pytest.raises(LlmResponseError, match="max_reaction_delta"):
        validate_reaction_decision(_reaction_decision(salience_delta=0.1, motif=401), EventType.SCANDAL, config)


# ── build_reaction_system_prompt / build_reaction_user_prompt (v5 Lot 4) ─

def _reaction_citizen(cid, event_salience=0.0):
    c = _citizen(cid, (0.5,))
    c.event_salience = event_salience
    return c


def _reaction_context(cid, event_salience=0.0):
    return ReactionContext(cid=cid, event_salience=event_salience)


def test_reaction_system_prompt_enumerates_every_expected_cid():
    citizens = [_reaction_citizen(0), _reaction_citizen(1), _reaction_citizen(2)]
    config = _config_with_llm_enabled()
    prompt = build_reaction_system_prompt(citizens, EventType.SCANDAL, config)
    assert "[0,1,2]" in prompt
    assert "EXACTEMENT ces 3" in prompt


def test_reaction_system_prompt_states_the_real_max_reaction_delta():
    citizens = [_reaction_citizen(0)]
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, events=dataclasses.replace(config.events, max_reaction_delta=0.42))
    prompt = build_reaction_system_prompt(citizens, EventType.SCANDAL, config)
    assert "0.42" in prompt


def test_reaction_system_prompt_shows_only_this_calls_legal_motifs():
    citizens = [_reaction_citizen(0)]
    config = _config_with_llm_enabled()
    scandal_prompt = build_reaction_system_prompt(citizens, EventType.SCANDAL, config)
    assert "401 = SCANDAL_TRUST_EROSION" in scandal_prompt
    assert "402 = ECONOMIC_SHOCK_REACTION" not in scandal_prompt
    shock_prompt = build_reaction_system_prompt(citizens, EventType.ECONOMIC_SHOCK, config)
    assert "402 = ECONOMIC_SHOCK_REACTION" in shock_prompt
    assert "401 = SCANDAL_TRUST_EROSION" not in shock_prompt


def test_reaction_user_prompt_carries_a_single_shared_event_block_not_duplicated_per_citizen():
    citizens = [_reaction_citizen(0), _reaction_citizen(1)]
    contexts = {0: _reaction_context(0), 1: _reaction_context(1)}
    payload = json.loads(
        build_reaction_user_prompt(citizens, contexts, event_type=EventType.SCANDAL, target=205, magnitude=0.0)
    )
    assert payload["event"] == {"event_type": int(EventType.SCANDAL), "target": 205}
    assert len(payload["reactors"]) == 2
    for block in payload["reactors"]:
        assert "event_type" not in block
        assert "target" not in block


def test_reaction_user_prompt_omits_magnitude_for_a_scandal_call():
    citizen = _reaction_citizen(0)
    contexts = {0: _reaction_context(0)}
    payload = json.loads(
        build_reaction_user_prompt([citizen], contexts, event_type=EventType.SCANDAL, target=205, magnitude=0.0)
    )
    assert "magnitude" not in payload["event"]


def test_reaction_user_prompt_carries_magnitude_for_an_economic_shock_call():
    citizen = _reaction_citizen(0)
    contexts = {0: _reaction_context(0)}
    payload = json.loads(
        build_reaction_user_prompt([citizen], contexts, event_type=EventType.ECONOMIC_SHOCK, target=None, magnitude=0.73)
    )
    assert payload["event"]["target"] is None
    assert payload["event"]["magnitude"] == 0.73


def test_reaction_user_prompt_is_deterministic_for_the_same_inputs():
    citizens = [_reaction_citizen(0), _reaction_citizen(1)]
    contexts = {0: _reaction_context(0), 1: _reaction_context(1)}
    args = (citizens, contexts)
    kwargs = {"event_type": EventType.SCANDAL, "target": 205, "magnitude": 0.0}
    assert build_reaction_user_prompt(*args, **kwargs) == build_reaction_user_prompt(*args, **kwargs)


def test_reaction_user_prompt_ctx_matches_the_journalled_ctx_payload():
    # One serialization, two consumers (the prompt and the journal write in
    # run_polity_simulation.py) -- both must read from to_payload().
    citizen = _reaction_citizen(7)
    context = _reaction_context(7, event_salience=0.33)
    payload = json.loads(
        build_reaction_user_prompt([citizen], {7: context}, event_type=EventType.SCANDAL, target=205, magnitude=0.0)
    )
    assert payload["reactors"][0]["ctx"] == context.to_payload()
    assert context.to_payload() == {"event_salience": 0.33}


# ── decide_reaction_to_event (FakeReactionLlmClient, v5 Lot 4) ───────────

class FakeReactionLlmClient:
    """Always answers with a nonzero salience_delta and the call's own
    grounding motif -- lets tests assert on chunking/order/resolution
    behavior without a live model."""

    def __init__(self):
        self.calls: list[list[int]] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        cids = [r["cid"] for r in payload["reactors"]]
        self.calls.append(cids)
        grounding = 401 if payload["event"]["event_type"] == int(EventType.SCANDAL) else 402
        decisions = [{"cid": cid, "salience_delta": 0.1, "motif": grounding} for cid in cids]
        return json.dumps({"decisions": decisions})


def _reaction_population(n):
    return [_reaction_citizen(i) for i in range(n)]


def _reaction_contexts(citizens):
    return {c.citizen_id: _reaction_context(c.citizen_id, event_salience=c.event_salience) for c in citizens}


def test_decide_reaction_to_event_returns_empty_and_skips_the_client_when_no_citizens():
    config = _config_with_llm_enabled()
    client = FakeReactionLlmClient()

    outcome = decide_reaction_to_event(
        [], {}, EventType.SCANDAL, config, client, target=None
    )

    assert outcome.decisions == []
    assert client.calls == []


def test_decide_reaction_to_event_sorts_by_citizen_id_regardless_of_input_order():
    # >= MIN_SAFE_BATCH_SIZE citizens: dt=8 does not override the default
    # floor (unlike decide_pressure_actions's min_batch_size=1).
    citizens = _reaction_population(20)
    citizens = [citizens[3], citizens[0]] + citizens[4:] + [citizens[1], citizens[2]]
    contexts = _reaction_contexts(citizens)
    config = _config_with_llm_enabled()
    client = FakeReactionLlmClient()

    decide_reaction_to_event(citizens, contexts, EventType.SCANDAL, config, client, target=205)

    assert client.calls == [list(range(20))]


def test_decide_reaction_to_event_uses_the_default_min_batch_size_floor():
    # Unlike decide_pressure_actions (min_batch_size=1), dt=8 batches the
    # WHOLE population -- a static, run-level quantity that never shrinks
    # the way a consulted cohort does -- so a cohort below
    # MIN_SAFE_BATCH_SIZE is deliberately still rejected by chunk_voters's
    # own default floor.
    citizens = _reaction_population(3)
    contexts = _reaction_contexts(citizens)
    config = _config_with_llm_enabled()
    with pytest.raises(NotImplementedError, match="min_batch_size"):
        decide_reaction_to_event(citizens, contexts, EventType.SCANDAL, config, FakeReactionLlmClient(), target=205)


def test_decide_reaction_to_event_chunks_a_full_population_at_max_batch_size():
    citizens = _reaction_population(100)
    contexts = _reaction_contexts(citizens)
    config = _config_with_llm_enabled(max_batch_size=25)
    client = FakeReactionLlmClient()

    outcome = decide_reaction_to_event(citizens, contexts, EventType.SCANDAL, config, client, target=205)

    assert len(client.calls) == 4
    assert [len(call) for call in client.calls] == [25, 25, 25, 25]
    assert sorted(cid for call in client.calls for cid in call) == list(range(100))
    assert [d.cid for d in outcome.decisions] == list(range(100))


def test_decide_reaction_to_event_raises_notimplementederror_for_unsupported_provider():
    citizens = _reaction_population(25)
    contexts = _reaction_contexts(citizens)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="api"))
    with pytest.raises(NotImplementedError, match="provider"):
        decide_reaction_to_event(citizens, contexts, EventType.SCANDAL, config, FakeReactionLlmClient(), target=205)


def test_decide_reaction_to_event_accepts_the_vllm_provider():
    citizens = _reaction_population(25)
    contexts = _reaction_contexts(citizens)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm"))

    outcome = decide_reaction_to_event(citizens, contexts, EventType.SCANDAL, config, FakeReactionLlmClient(), target=205)

    assert [d.cid for d in outcome.decisions] == list(range(25))


def test_decide_reaction_to_event_raises_for_dynamic_batch_sharding():
    citizens = _reaction_population(25)
    contexts = _reaction_contexts(citizens)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, batch_sharding="dynamic"))
    with pytest.raises(NotImplementedError, match="batch_sharding"):
        decide_reaction_to_event(citizens, contexts, EventType.SCANDAL, config, FakeReactionLlmClient(), target=205)


def test_decide_reaction_to_event_raises_for_intra_run_workers_above_one():
    citizens = _reaction_population(25)
    contexts = _reaction_contexts(citizens)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, parallel=dataclasses.replace(config.parallel, intra_run_workers=2))
    with pytest.raises(NotImplementedError, match="intra_run_workers"):
        decide_reaction_to_event(citizens, contexts, EventType.SCANDAL, config, FakeReactionLlmClient(), target=205)


def test_decide_reaction_to_event_raises_for_codebook_version_mismatch():
    citizens = _reaction_population(25)
    contexts = _reaction_contexts(citizens)
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, codebook_version="0.9"))
    with pytest.raises(Exception, match="codebook_version"):
        decide_reaction_to_event(citizens, contexts, EventType.SCANDAL, config, FakeReactionLlmClient(), target=205)


def test_decide_reaction_to_event_propagates_llm_response_error_on_count_mismatch():
    citizens = _reaction_population(25)
    contexts = _reaction_contexts(citizens)
    config = _config_with_llm_enabled()

    class ShortClient:
        def complete_json(self, **kwargs):
            return json.dumps({"decisions": [{"cid": 0, "salience_delta": 0.1, "motif": 401}]})

    with pytest.raises(LlmResponseError, match="misaligned"):
        decide_reaction_to_event(citizens, contexts, EventType.SCANDAL, config, ShortClient(), target=205)


# ── _complete_and_decode_with_replay / llm.max_batch_replays (v4 Lot 8) ──

class _FlakyClient:
    """Answers malformed JSON (an LlmResponseError-raising decode) on its
    first `fail_times` calls, then `good_raw` on every call after --
    exercises _complete_and_decode_with_replay's retry loop without a live
    model. Records every (system_prompt, user_prompt) pair, so a test can
    assert the retried request is byte-identical to the original --
    "byte-identical" refers to the PROMPTS specifically; cast_votes's own
    retry_temperature (a local, deliberate exception, see llm_behavior_
    engine._VOTE_CAST_RETRY_TEMPERATURE) means the full request is not
    byte-identical for that one entry point, covered by its own dedicated
    test below. Also accepts and records `temperature` (defaulting like
    the real client's own `complete_json`) so a caller opting into
    retry_temperature doesn't raise a TypeError against this fake."""

    def __init__(self, fail_times, good_raw):
        self.fail_times = fail_times
        self.good_raw = good_raw
        self.calls = 0
        self.prompts: list[tuple[str, str]] = []
        self.temperatures: list[float | None] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True, temperature=None):
        self.calls += 1
        self.prompts.append((system_prompt, user_prompt))
        self.temperatures.append(temperature)
        if self.calls <= self.fail_times:
            return "not valid json"
        return self.good_raw


class _FlakyResponseClient:
    """Raises LlmResponseError directly from complete_json itself (never
    returns malformed content for decode() to reject) on its first
    `fail_times` calls, then `good_raw` after -- the branch _FlakyClient
    above never exercises. This is the real shape of a truncated
    generation (done_reason != "stop", raised by llm_client.py's own
    _extract_content/_extract_native_content): the caller never sees a raw
    string to decode at all. Pins the fix for the bug this exact gap left
    uncovered until a live v6b Lot 4 acceptance run hit it."""

    def __init__(self, fail_times, good_raw):
        self.fail_times = fail_times
        self.good_raw = good_raw
        self.calls = 0
        self.prompts: list[tuple[str, str]] = []
        self.temperatures: list[float | None] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True, temperature=None):
        self.calls += 1
        self.prompts.append((system_prompt, user_prompt))
        self.temperatures.append(temperature)
        if self.calls <= self.fail_times:
            raise LlmResponseError("generation did not finish cleanly: done_reason='length'")
        return self.good_raw


class _AlwaysTransportFailingClient:
    def __init__(self):
        self.calls = 0

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True, temperature=None):
        self.calls += 1
        raise LlmTransportError("connection refused")


def _replay_cases():
    """One (label, call) per decide_* entry point -- call(config, client) ->
    the decide_* invocation itself, and the single-decision good_raw JSON
    each one needs to succeed. candidacy_considered needs >= 20 citizens
    (chunk_voters's own MIN_SAFE_BATCH_SIZE floor, not overridden by that
    caller); every other entry point batches a handful of
    officeholders/nominees/parties/consulted citizens and needs no such
    floor. vote_cast now chunks at its own dedicated
    _VOTE_CAST_MAX_CHUNK_SIZE=1 (min_batch_size=1) -- exactly 1 voter here
    so this fixture produces exactly one chunk/one client call, matching
    every other single-call good_raw fixture below."""
    voters = _population(1, dims=1)
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

    # dt=8 batches the WHOLE population like vote_cast/candidacy_considered
    # (not a handful like pressure_action's consulted cohort), so it needs
    # >= MIN_SAFE_BATCH_SIZE citizens too -- decide_reaction_to_event does
    # not override chunk_voters's default floor (see this lot's own
    # test_decide_reaction_to_event_uses_the_default_min_batch_size_floor).
    reaction_citizens = _reaction_population(20)
    reaction_contexts_ = _reaction_contexts(reaction_citizens)
    reaction_good = json.dumps(
        {"decisions": [{"cid": c.citizen_id, "salience_delta": 0.1, "motif": 401} for c in reaction_citizens]}
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
            # Pinned to a single round: this test is about
            # _complete_and_decode_with_replay's generic retry behavior,
            # not v7's multi-round negotiation -- at the shipped default
            # (3 rounds), a converged FlakyClient would trigger a SECOND
            # round (to check for a fixed point) and inflate client.calls
            # beyond what this shared, parametrized test expects.
            lambda config, client: decide_coalition(
                coalition_parties, coalition_seats, coalition_votes,
                dataclasses.replace(config, parties=dataclasses.replace(config.parties, coalition_max_negotiation_rounds=1)),
                client,
            ),
            coalition_good,
        ),
        (
            "reaction_to_event",
            lambda config, client: decide_reaction_to_event(
                reaction_citizens, reaction_contexts_, EventType.SCANDAL, config, client, target=205
            ),
            reaction_good,
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
    # Byte-identical PROMPTS on every retry, for every entry point including
    # vote_cast -- retry_temperature (cast_votes's own local exception, see
    # test_cast_votes_retries_at_a_varied_temperature_and_marks_it below)
    # changes what temperature accompanies the prompt, never the prompt
    # itself.
    assert client.prompts[0] == client.prompts[1] == client.prompts[2]


@pytest.mark.parametrize("label,call,good_raw", _replay_cases(), ids=[c[0] for c in _replay_cases()])
def test_max_batch_replays_still_raises_once_the_budget_is_exhausted(label, call, good_raw):
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=2))
    client = _FlakyClient(fail_times=99, good_raw=good_raw)  # never recovers
    with pytest.raises(LlmResponseError):
        call(config, client)
    assert client.calls == 3  # 1 original + 2 replays, then give up


@pytest.mark.parametrize("label,call,good_raw", _replay_cases(), ids=[c[0] for c in _replay_cases()])
def test_max_batch_replays_recovers_from_a_complete_json_raised_error(label, call, good_raw):
    # Pins the actual bug: an LlmResponseError raised by complete_json
    # itself (truncated generation) must be retried exactly like a
    # decode-time one -- the branch _FlakyClient never covers.
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=2))
    client = _FlakyResponseClient(fail_times=2, good_raw=good_raw)
    call(config, client)  # must not raise
    assert client.calls == 3
    # Byte-identical PROMPTS on every retry, for every entry point including
    # vote_cast -- retry_temperature (cast_votes's own local exception, see
    # test_cast_votes_retries_at_a_varied_temperature_and_marks_it below)
    # changes what temperature accompanies the prompt, never the prompt
    # itself.
    assert client.prompts[0] == client.prompts[1] == client.prompts[2]


@pytest.mark.parametrize("label,call,good_raw", _replay_cases(), ids=[c[0] for c in _replay_cases()])
def test_max_batch_replays_zero_propagates_a_complete_json_raised_error_on_the_first_attempt(label, call, good_raw):
    # Before the fix, this error skipped the retry loop entirely and
    # propagated silently (no WARNING logged) regardless of `replays` --
    # this pins the shipped default's own behavior post-fix.
    config = _config_with_llm_enabled()
    assert config.llm.max_batch_replays == 0
    client = _FlakyResponseClient(fail_times=1, good_raw=good_raw)
    with pytest.raises(LlmResponseError):
        call(config, client)
    assert client.calls == 1


def test_max_batch_replays_never_catches_a_transport_error():
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=2))
    citizen = _pressure_citizen(0)
    contexts = _pressure_contexts([citizen])
    client = _AlwaysTransportFailingClient()
    with pytest.raises(LlmTransportError):
        decide_pressure_actions([citizen], contexts, config, client)
    assert client.calls == 1  # the client itself owns transport-level retries, not this layer


# ── retry_temperature / retry_sampling_varied -- cast_votes's own local,
# deliberate exception to temperature=0 determinism (see
# cache_recycle_chunk_size_tension_findings.md and _VOTE_CAST_RETRY_
# TEMPERATURE's own comment). No other decide_* entry point opts into this.

def test_cast_votes_first_attempt_never_overrides_temperature():
    # The common, successful-first-try path: no retry ever happens, so no
    # temperature override is ever sent, regardless of max_batch_replays.
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=2))
    voters = _population(1, dims=1)
    candidates = [_candidate(900, (0.5,))]
    good_raw = json.dumps({"decisions": [{"cid": 0, "blank": 1, "ranking": [], "motif": 101}]})
    client = _FlakyClient(fail_times=0, good_raw=good_raw)

    cast_votes(voters, candidates, config, client)

    assert client.calls == 1
    assert client.temperatures == [None]


def test_cast_votes_retries_at_a_varied_temperature_and_marks_it():
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=1))
    voters = _population(1, dims=1)
    candidates = [_candidate(900, (0.5,))]
    good_raw = json.dumps({"decisions": [{"cid": 0, "blank": 1, "ranking": [], "motif": 101}]})
    client = _FlakyClient(fail_times=1, good_raw=good_raw)

    outcome = cast_votes(voters, candidates, config, client)

    assert client.calls == 2
    # First attempt: no override (preserves determinism). Retry: the local
    # exception's own temperature, never None.
    assert client.temperatures == [None, _VOTE_CAST_RETRY_TEMPERATURE]
    assert outcome.retry_sampling_varied == {0: True}


def test_cast_votes_retry_sampling_varied_is_false_when_the_first_attempt_succeeds():
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=2))
    voters = _population(1, dims=1)
    candidates = [_candidate(900, (0.5,))]
    good_raw = json.dumps({"decisions": [{"cid": 0, "blank": 1, "ranking": [], "motif": 101}]})
    client = _FlakyClient(fail_times=0, good_raw=good_raw)

    outcome = cast_votes(voters, candidates, config, client)

    assert outcome.retry_sampling_varied == {0: False}


def test_cast_votes_retry_sampling_varied_defaults_to_an_empty_dict_when_unset():
    # A plain VoteBatchOutcome(ballots=..., decisions=...) construction --
    # every pre-existing call site in this codebase's own tests -- still
    # compiles, and reading a missing cid reads as False, not a KeyError.
    outcome = VoteBatchOutcome(ballots=[], decisions=[])
    assert outcome.retry_sampling_varied == {}
    assert outcome.retry_sampling_varied.get(999, False) is False


def test_other_decide_entry_points_never_send_a_temperature_override_even_when_replayed():
    # The negative case for every OTHER decision type: retry_temperature
    # defaults to None at every call site except cast_votes's own, so a
    # replay never sends a temperature override for them -- byte-identical
    # retries, unchanged since v4 Lot 8.
    config = _config_with_llm_enabled()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=1))
    citizen = _pressure_citizen(0)
    contexts = _pressure_contexts([citizen])
    good_raw = json.dumps({"decisions": [{"cid": 0, "target": 205, "act": 4, "motif": 305}]})
    client = _FlakyClient(fail_times=1, good_raw=good_raw)

    decide_pressure_actions([citizen], contexts, config, client)

    assert client.calls == 2
    assert client.temperatures == [None, None]
