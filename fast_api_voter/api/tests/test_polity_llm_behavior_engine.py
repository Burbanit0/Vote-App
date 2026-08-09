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
from api.domain.polity.config import load_config
from api.domain.polity.llm_behavior_engine import (
    MIN_SAFE_BATCH_SIZE,
    apply_shifts,
    build_candidacy_system_prompt,
    build_candidacy_user_prompt,
    build_party_nomination_system_prompt,
    build_party_nomination_user_prompt,
    build_positioning_system_prompt,
    build_positioning_user_prompt,
    build_system_prompt,
    build_user_prompt,
    cast_votes,
    chunk_voters,
    compute_max_tokens,
    decide_campaign_positioning,
    decide_candidacies,
    decide_party_nominations,
    resolve_party_nomination_cid,
    truncation_limit,
    validate_decision,
    validate_positioning_decision,
)
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.llm_schemas import PartyNominationDecision, PositioningDecision, PositionShift, VoteCastDecision
from api.domain.polity.parties import Party
from api.domain.polity.simple_rules import BLANK_LABEL, build_ranking, declare_candidacy, sympathizer_ratio


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
    with pytest.raises(NotImplementedError, match="MIN_SAFE_BATCH_SIZE"):
        chunk_voters(voters, 25)


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

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens):
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
