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
    build_system_prompt,
    build_user_prompt,
    cast_votes,
    chunk_voters,
    compute_max_tokens,
    truncation_limit,
    validate_decision,
)
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.llm_schemas import VoteCastDecision
from api.domain.polity.simple_rules import BLANK_LABEL, build_ranking, declare_candidacy


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
