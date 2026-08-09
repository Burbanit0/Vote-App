"""
api.domain.polity.llm_behavior_engine — v2 increments 1-4: the LLM
replacement for build_ranking (voting), decide_candidacy (dominant-path
candidacy eligibility only), select_party_nominee_from_declared's tiebreak
when a party is contested (2+ declared candidates), and declare_candidacy's
sincere-platform pin for dominant nominees (campaign_positioning). The
rupture candidacy path and coalition formation stay on simple_rules.py.

Design doc §11.4's baseline-vs-LLM comparison depends on simple_rules.py
staying untouched and always available -- this module is additive, never a
modification of it. See simple_rules.py's own module docstring.

decide_candidacies (increment 2) only ever evaluates party-affiliated
citizens along the dominant path -- the rupture path
(attempt_rupture_candidacy, simple_rules.py) is explicitly "independent of
perceived support by design" (a probability mechanic, not a judgment call)
and never reaches the LLM.

decide_party_nominations (increment 3) only arbitrates parties with 2+
declared candidates this tick -- a party with 0 or 1 never needs a judgment
call, and select_party_nominee_from_declared keeps handling those trivially
(and remains the full baseline when llm.enabled=False). Its batching is
deliberately NOT chunk_voters/MIN_SAFE_BATCH_SIZE-shaped: it batches
*contested parties* (a handful at most, most ticks zero), not citizens --
forcing it through the citizen-batch guard would make the feature
permanently unreachable. See its own docstring.

decide_campaign_positioning (increment 4) only ever positions dominant
nominees, the same set decide_party_nominations/select_party_nominee(_from_declared)
already resolves -- rupture candidates keep running on their sincere
position (attempt_rupture_candidacy's whole point is an unstrategized
protest candidacy) and never reach this function. Unlike every prior
decision type, this one changes an actual vote input (pledged_platform),
not just who's eligible or how a ballot is cast -- the first increment
where the LLM's choice can change who wins. Also deliberately NOT
chunk_voters-shaped, same reasoning as decide_party_nominations: it batches
this tick's *nominees* (a handful), not citizens.

Deliberate simplifications versus the full design doc, documented rather
than silently made:
- No persona library (§9) yet: citizens are described to the LLM by their
  existing raw fields (issue_positions/issue_priorities/blank_threshold),
  not an archetype. §3.5's "group by archetype_id" batching criterion is
  therefore not literally implementable; chunk_voters() below uses a
  near-equal split by citizen_id instead.
- No cache (§4.2) yet: correctness comes from temperature=0 + a pinned
  model + serialized calls (llm_batching_determinism_results.md), not a
  cache. Deferred to a later increment.
- Blank ballots lose v0/v1's "still ranks every candidate below Blank"
  information (§3.6.1's hard rule: blank=1 means every other field is
  empty) -- a real, documented divergence from the deterministic baseline
  that partially confounds §11.4's "any deviation is attributable to the
  LLM" claim for blank voters specifically. See ballot_from_decision.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import (
    CAMPAIGN_MOTIF_PROMPT_TABLE,
    CANDIDACY_MOTIF_PROMPT_TABLE,
    PARTY_NOMINATION_MOTIF_PROMPT_TABLE,
    VOTE_MOTIF_PROMPT_TABLE,
    check_codebook_version,
)
from api.domain.polity.config import PolityConfig
from api.domain.polity.llm_client import (
    LlmClientProtocol,
    LlmResponseError,
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
    CandidacyDecision,
    PartyNominationDecision,
    PositioningDecision,
    PositionShift,
    VoteCastDecision,
)
from api.domain.polity.parties import Party
from api.domain.polity.simple_rules import BLANK_LABEL, candidate_label, sympathizer_ratio

# Empirical threshold from ollama_structured_output_results.md's root-cause
# investigation: batches of <=12 citizens (holding dims/candidates fixed at
# the values used there) reliably produced zero visible output regardless
# of token budget; 15 worked reliably. This is a safety margin above that
# boundary, not the boundary itself -- real citizen data may shift it.
MIN_SAFE_BATCH_SIZE = 20

_TRUNCATION_THRESHOLD = 6
_TRUNCATE_TO = 5


@dataclass(frozen=True)
class VoteBatchOutcome:
    ballots: list[list[str]]
    decisions: list[VoteCastDecision]


def _check_supported(config: PolityConfig) -> None:
    """Fail before any network call, mirroring run_simulation's existing
    top-of-function guard style -- never do partial work on a config this
    module can't actually honor."""
    if config.llm.provider != "ollama":
        raise NotImplementedError(f"llm.provider {config.llm.provider!r} is not supported before v4 (§15bis.6)")
    if config.llm.batch_sharding != "static":
        raise NotImplementedError(
            f"llm.batch_sharding {config.llm.batch_sharding!r} is not supported -- "
            "dynamic sharding breaks reproducibility (§15bis.4a)"
        )
    if config.llm.rationale_mode != "codes":
        raise NotImplementedError(f"llm.rationale_mode {config.llm.rationale_mode!r} is not supported yet (§16.5)")
    if config.parallel.intra_run_workers != 1:
        raise NotImplementedError(
            "parallel.intra_run_workers > 1 is not supported -- concurrent batching breaks "
            "reproducibility (llm_batching_determinism_results.md)"
        )
    check_codebook_version(config.llm.codebook_version)


def chunk_voters(voters: Sequence[Citizen], max_batch_size: int) -> list[list[Citizen]]:
    """Near-equal chunks by citizen_id, never a small fixed-size remainder.
    A pure function of (voter set, max_batch_size) -- independent of
    arrival order or timing, which is what config's `batch_sharding:
    static` actually needs to guarantee (§15bis.4a).

    Raises if the population is too small to chunk safely (see
    MIN_SAFE_BATCH_SIZE) rather than silently producing a chunk in
    territory this project has observed the model fail on."""
    n = len(voters)
    if n == 0:
        return []
    num_chunks = -(-n // max_batch_size)  # ceil division
    base_size, remainder = divmod(n, num_chunks)
    if base_size < MIN_SAFE_BATCH_SIZE:
        raise NotImplementedError(
            f"population_size={n} with llm.max_batch_size={max_batch_size} would produce a "
            f"chunk of {base_size} citizens, below MIN_SAFE_BATCH_SIZE={MIN_SAFE_BATCH_SIZE} "
            "(ollama_structured_output_results.md: small batches reliably fail regardless of "
            "token budget) -- increase population_size or max_batch_size"
        )
    chunks = []
    start = 0
    for i in range(num_chunks):
        size = base_size + (1 if i < remainder else 0)
        chunks.append(list(voters[start:start + size]))
        start += size
    return chunks


def truncation_limit(candidate_count: int) -> int | None:
    """Design doc §3.6.1: full ranking if <=6 candidates, else top-5."""
    return None if candidate_count <= _TRUNCATION_THRESHOLD else _TRUNCATE_TO


def compute_max_tokens(chunk_size: int) -> int:
    """The addend is a flat reasoning allowance, not scaled by chunk size.
    A live consolidation run hit finish_reason='length' on a 20-citizen
    batch under the old `chunk_size*60+256` formula: Qwen3's internal
    <think> reasoning consumes the same completion budget as the visible
    JSON answer (ollama_structured_output_results.md's toy-batch failure
    showed a 512-token budget spent entirely on invisible reasoning), and
    that reasoning length is unpredictable, not proportional to the number
    of decisions to emit. 1536 gives real headroom above what the one
    successful full-size (25-citizen) live call actually used (1026
    completion tokens)."""
    return max(chunk_size * 60 + 1536, 1536)


def sorted_candidates(candidates: Sequence[Citizen]) -> list[Citizen]:
    """The single canonical candidate order every prompt/position-mapping
    must agree on (D-5): position N in build_user_prompt's candidate list
    must be the same candidate as position N when mapping the model's
    response back to a cid in cast_votes."""
    return sorted(candidates, key=lambda c: c.citizen_id)


def build_system_prompt(citizens: Sequence[Citizen], candidates: Sequence[Citizen]) -> str:
    """Enumerates the full expected voter cid list verbatim, not just a
    count -- ollama_structured_output_results.md Finding B: a bare 'return
    exactly N decisions' instruction was empirically insufficient, the
    model dropped the last citizen of a 25-item batch despite it. The
    explicit list + self-check instruction fixed it on the first try.

    `ranking` uses candidate *positions* (1..N), never candidate cids: a
    live consolidation run found the model conflates a candidate-cid-based
    ranking with the voter cid list above, because a candidate is also a
    citizen -- candidate and voter cids draw from the same number space
    and can collide (citizen 11 both votes and is a candidate). Telling
    the model to use positions instead removes the collision structurally
    rather than relying on wording alone to disambiguate two overlapping
    lists of raw cids."""
    candidate_count = len(candidates)
    truncate_at = truncation_limit(candidate_count)
    truncate_note = "" if truncate_at is None else f" (classer au plus les {truncate_at} meilleurs)"
    cid_list = ",".join(str(c.citizen_id) for c in citizens)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen recu, decide son "
        f"vote parmi les candidats.\nIl y a {candidate_count} candidats. "
        "Chaque candidat est identifie par son champ 'position' (1 a "
        f"{candidate_count}) dans la liste 'candidates' du message "
        "utilisateur -- PAS par son cid.\nClasse les POSITIONS des "
        f"candidats du meilleur au moins bon{truncate_note}, ou vote blanc "
        "(blank=1, ranking vide) si aucun candidat n'est acceptable.\n"
        f"Motifs valides (code court obligatoire) :\n{VOTE_MOTIF_PROMPT_TABLE}"
        "\nIMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(citizens)} cid de CITOYENS-ELECTEURS (jamais un cid de "
        f"candidat), chacun une seule fois, dans cet ordre : [{cid_list}]. "
        "Verifie ta reponse avant de la finaliser : chaque cid de cette "
        "liste doit apparaitre exactement une fois dans le champ "
        f"'cid' des decisions, et chaque ranking ne doit contenir que des "
        f"entiers entre 1 et {candidate_count} (des positions, jamais un "
        "cid).\nReponds UNIQUEMENT avec un objet JSON conforme au schema "
        "fourni."
    )


def build_user_prompt(voters: Sequence[Citizen], candidates: Sequence[Citizen]) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats) so
    the prompt is a pure function of the candidate *set* and voter *set*,
    never of iteration order -- required for the byte-for-byte
    reproducibility test (Lot 8). Candidates sorted by citizen_id (D-5):
    _declare_nominees assembles party nominees in party-iteration order
    then rupture candidates by citizen_id, and get_two_round_winner's
    Counter.most_common(2) tie-breaks by insertion order, so the prompt
    itself must not depend on that assembly order.

    Each candidate block carries its `position` (1-indexed, this sorted
    order) alongside its `cid` -- `ranking` in the response refers to
    `position`, `cid` here is informational context only (party/platform
    are still meaningful to the model per-candidate)."""
    candidate_blocks = [
        {
            "position": i,
            "cid": c.citizen_id,
            "platform": [round(x, 4) for x in _platform(c)],
            "party": c.party_affiliation,
        }
        for i, c in enumerate(sorted_candidates(candidates), start=1)
    ]
    voter_blocks = [
        {
            "cid": v.citizen_id,
            "positions": [round(x, 4) for x in v.issue_positions],
            "priorities": [round(x, 4) for x in v.issue_priorities],
            "blank_threshold": round(v.blank_threshold, 4),
        }
        for v in voters
    ]
    return json.dumps(
        {"candidates": candidate_blocks, "voters": voter_blocks}, sort_keys=True, separators=(",", ":")
    )


def _platform(candidate: Citizen) -> tuple[float, ...]:
    if candidate.pledged_platform is None:
        raise ValueError(f"citizen {candidate.citizen_id} has not declared a candidacy")
    return candidate.pledged_platform


def validate_decision(decision: VoteCastDecision, candidate_count: int, truncate_at: int | None) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without knowing this batch's candidate count and truncation rule.
    `decision.ranking` holds 1-indexed positions into this batch's sorted
    candidate list (see build_user_prompt/sorted_candidates), not cids."""
    out_of_range = [p for p in decision.ranking if p > candidate_count]
    if out_of_range:
        raise LlmResponseError(
            f"decision for cid={decision.cid} ranks out-of-range position(s) {out_of_range} "
            f"(this batch has {candidate_count} candidates, positions 1..{candidate_count})"
        )
    if truncate_at is not None and len(decision.ranking) > truncate_at:
        raise LlmResponseError(
            f"decision for cid={decision.cid} ranks {len(decision.ranking)} candidates, "
            f"exceeding the truncation limit of {truncate_at}"
        )
    if len(decision.ranking) > candidate_count:
        raise LlmResponseError(
            f"decision for cid={decision.cid} ranks more candidates ({len(decision.ranking)}) "
            f"than exist in this batch ({candidate_count})"
        )


def ballot_from_decision(decision: VoteCastDecision, position_to_candidate: dict[int, Citizen]) -> list[str]:
    """Mirrors build_ranking's contract (Blank always present in the
    returned list) so ballot_and_aggregation.get_presidential_winner needs
    zero changes. blank=1 collapses to just [BLANK_LABEL] -- see the
    module docstring's note on this divergence from build_ranking, which
    ranks every candidate even for a voter beyond their own tolerance.
    `decision.ranking` holds positions (validate_decision has already
    checked they're in range); `position_to_candidate` is the same
    1-indexed, citizen_id-sorted mapping build_user_prompt presented."""
    if decision.blank == 1:
        return [BLANK_LABEL]
    return [candidate_label(position_to_candidate[p]) for p in decision.ranking] + [BLANK_LABEL]


def resolve_ranking_cids(decision: VoteCastDecision, candidates: Sequence[Citizen]) -> list[int]:
    """Translates decision.ranking (1-indexed positions into `candidates`
    sorted by citizen_id) back to real candidate cids -- for the journal,
    which must stay a self-contained, human-readable record. Positions are
    a wire-protocol-only device to dodge the voter/candidate cid collision
    (see build_system_prompt's docstring); they must never leak into a
    persisted event, where a reader has no reason to know a batch's
    internal candidate ordering."""
    ordered = sorted_candidates(candidates)
    return [ordered[p - 1].citizen_id for p in decision.ranking]


def cast_votes(
    voters: Sequence[Citizen],
    candidates: Sequence[Citizen],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> VoteBatchOutcome:
    """v2 increment 1's replacement for `[build_ranking(voter, candidates)
    for voter in voters]`. Pure aside from the injected client -- no
    journal writes here, matching this repo's pure-worker convention;
    run_polity_simulation.py owns every journal write."""
    _check_supported(config)

    candidate_count = len(candidates)
    position_to_candidate = {i: c for i, c in enumerate(sorted_candidates(candidates), start=1)}
    truncate_at = truncation_limit(candidate_count)

    ballots: list[list[str]] = []
    decisions: list[VoteCastDecision] = []
    for chunk in chunk_voters(voters, config.llm.max_batch_size):
        expected_cids = [voter.citizen_id for voter in chunk]
        raw = client.complete_json(
            system_prompt=build_system_prompt(chunk, candidates),
            user_prompt=build_user_prompt(chunk, candidates),
            json_schema=VOTE_CAST_JSON_SCHEMA,
            max_tokens=compute_max_tokens(len(chunk)),
        )
        chunk_decisions = decode_vote_batch(raw, expected_cids)
        for decision in chunk_decisions:
            validate_decision(decision, candidate_count, truncate_at)
            ballots.append(ballot_from_decision(decision, position_to_candidate))
        decisions.extend(chunk_decisions)

    return VoteBatchOutcome(ballots=ballots, decisions=decisions)


@dataclass(frozen=True)
class CandidacyBatchOutcome:
    decisions: list[CandidacyDecision]


def build_candidacy_system_prompt(citizens: Sequence[Citizen]) -> str:
    """Mirrors build_system_prompt's "enumerate the full expected cid list
    verbatim" fix (Finding B, ollama_structured_output_results.md) -- a bare
    'return exactly N decisions' instruction was empirically insufficient
    for vote_cast, and there's no reason to assume a shorter boolean+motif
    decision is immune to the same failure mode without live evidence to the
    contrary (see this module's own docstring on live-verifying increment
    2)."""
    cid_list = ",".join(str(c.citizen_id) for c in citizens)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen recu, decide "
        "s'il se presente comme candidat (outcome=1) ou renonce "
        "(outcome=0), a partir de son ambition et du soutien qu'il "
        "percoit.\nMotifs valides (code court obligatoire) :\n"
        f"{CANDIDACY_MOTIF_PROMPT_TABLE}\nIMPORTANT : la liste decisions "
        f"doit contenir EXACTEMENT ces {len(citizens)} cid, chacun une "
        f"seule fois, dans cet ordre : [{cid_list}]. Verifie ta reponse "
        "avant de la finaliser : chaque cid de cette liste doit apparaitre "
        "exactement une fois.\nReponds UNIQUEMENT avec un objet JSON "
        "conforme au schema fourni."
    )


def build_candidacy_user_prompt(chunk: Sequence[Citizen], support: dict[int, float]) -> str:
    """`support` is precomputed once against the full population, before
    chunking (see decide_candidacies) -- never recomputed per-chunk, or the
    "perceived support" signal would become an artifact of
    llm.max_batch_size/chunk boundaries instead of a stable, population-wide
    value. Canonical JSON (sort_keys, compact separators, rounded floats),
    same reproducibility discipline as build_user_prompt."""
    citizen_blocks = [
        {
            "cid": c.citizen_id,
            "ambition_score": round(c.ambition_score, 4),
            "perceived_support": round(support[c.citizen_id], 4),
        }
        for c in chunk
    ]
    return json.dumps({"citizens": citizen_blocks}, sort_keys=True, separators=(",", ":"))


def decide_candidacies(
    citizens: Sequence[Citizen],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> CandidacyBatchOutcome:
    """v2 increment 2's replacement for `decide_candidacy`'s bare
    ambition_score threshold, dominant path only (see this module's
    docstring for what stays out of scope). Pure aside from the injected
    client -- no journal writes here, matching cast_votes's convention;
    run_polity_simulation.py owns every journal write.

    `citizens` is expected to already be filtered to party-affiliated
    citizens by the caller (mirrors select_party_nominee's existing filter,
    unchanged) -- this function itself doesn't re-filter by party, it just
    batches whatever population it's given.

    Calls the client with think=False: a live investigation found this
    task's shorter, more subjective prompt ("should this citizen run?")
    makes qwen3:8b burn its entire completion budget on invisible <think>
    reasoning with zero visible output, regardless of budget size --
    unrelated to vote_cast's own reasoning-budget accounting
    (compute_max_tokens's flat allowance), which stays unaffected since
    cast_votes never sets this flag. See OllamaJsonClient's class docstring
    for why this needs an entirely different transport, not just a body
    flag."""
    _check_supported(config)

    population = list(citizens)
    support = {c.citizen_id: sympathizer_ratio(c, population) for c in population}

    decisions: list[CandidacyDecision] = []
    for chunk in chunk_voters(citizens, config.llm.max_batch_size):
        expected_cids = [c.citizen_id for c in chunk]
        raw = client.complete_json(
            system_prompt=build_candidacy_system_prompt(chunk),
            user_prompt=build_candidacy_user_prompt(chunk, support),
            json_schema=CANDIDACY_JSON_SCHEMA,
            max_tokens=compute_max_tokens(len(chunk)),
            think=False,
        )
        decisions.extend(decode_candidacy_batch(raw, expected_cids))

    return CandidacyBatchOutcome(decisions=decisions)


@dataclass(frozen=True)
class PartyNominationBatchOutcome:
    decisions: list[PartyNominationDecision]
    winners: dict[int, int]
    """party_id -> winning citizen_id, already resolved from winner_position
    -- only this module has the position<->candidate mapping (contested's
    per-party sub-list order), so resolution happens here, not in the
    caller, mirroring how cast_votes resolves positions into ballots
    internally rather than exposing raw positions."""


def build_party_nomination_system_prompt(contested: dict[int, list[Citizen]]) -> str:
    """Mirrors build_candidacy_system_prompt's "enumerate the full expected
    id list verbatim + self-check" fix (Finding B) -- keyed on party_id,
    since the decision unit here is a contested party, not a citizen."""
    party_id_list = ",".join(str(party_id) for party_id in contested)
    return (
        "Tu es un moteur de simulation. Pour chaque parti recu, plusieurs "
        "de ses membres veulent se presenter mais le parti ne peut "
        "designer qu'un seul candidat officiel. Choisis lequel, a partir "
        "de son ambition, du soutien qu'il percoit, et de sa proximite "
        "avec la plateforme du parti. Chaque candidat est identifie par "
        "son champ 'position' (1 a N) dans la liste 'candidates' de CE "
        "parti -- PAS par son cid.\nMotifs valides (code court "
        f"obligatoire) :\n{PARTY_NOMINATION_MOTIF_PROMPT_TABLE}\nIMPORTANT "
        f": la liste decisions doit contenir EXACTEMENT ces {len(contested)} "
        f"party_id, chacun une seule fois, dans cet ordre : [{party_id_list}]. "
        "Verifie ta reponse avant de la finaliser : chaque party_id de "
        "cette liste doit apparaitre exactement une fois, et chaque "
        "winner_position doit etre une position valide (jamais un cid) "
        "parmi les candidats de ce parti.\nReponds UNIQUEMENT avec un "
        "objet JSON conforme au schema fourni."
    )


def build_party_nomination_user_prompt(
    contested: dict[int, list[Citizen]], parties_by_id: dict[int, Party], support: dict[int, float]
) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats), same
    reproducibility discipline as build_user_prompt/build_candidacy_user_prompt.
    `support` is precomputed once by the caller against the full population
    (decide_party_nominations), same discipline as decide_candidacies'
    `support` -- never recomputed here. `platform_distance` reuses
    assign_party_affiliation's unweighted math.dist convention (simple_rules.py),
    not the voter-tolerance-specific _weighted_distance."""
    party_blocks = [
        {
            "party_id": party_id,
            "candidates": [
                {
                    "position": i,
                    "cid": c.citizen_id,
                    "ambition_score": round(c.ambition_score, 4),
                    "perceived_support": round(support[c.citizen_id], 4),
                    "platform_distance": round(math.dist(c.issue_positions, parties_by_id[party_id].platform), 4),
                }
                for i, c in enumerate(sorted_candidates(members), start=1)
            ],
        }
        for party_id, members in contested.items()
    ]
    return json.dumps({"parties": party_blocks}, sort_keys=True, separators=(",", ":"))


def resolve_party_nomination_cid(decision: PartyNominationDecision, members: Sequence[Citizen]) -> int:
    """Translates decision.winner_position (1-indexed position into
    `members`, sorted by citizen_id) back to a real cid -- same purpose as
    resolve_ranking_cids, scoped to one contested party's own candidate
    sub-list instead of the full candidate list."""
    ordered = sorted_candidates(members)
    return ordered[decision.winner_position - 1].citizen_id


def decide_party_nominations(
    citizens: Sequence[Citizen],
    parties: Sequence[Party],
    declared_cids: set[int],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> PartyNominationBatchOutcome:
    """v2 increment 3's replacement for select_party_nominee_from_declared's
    deterministic tiebreak, contested parties only (design doc §2.3, dt=4).
    Pure aside from the injected client -- no journal writes here, matching
    cast_votes/decide_candidacies's convention.

    Deliberately does NOT use chunk_voters/MIN_SAFE_BATCH_SIZE: those guard
    *citizen* batches (tens to hundreds per call); this batches *contested
    parties* (a handful at most, `parties.initial_count` in the shipped
    config is 5, and most ticks have zero). One call for the whole tick,
    skipped entirely if no party is contested -- calling the client with an
    empty batch would violate PartyNominationBatch's own min_length=1 and is
    wasted work regardless.

    Calls the client with think=False, same as decide_candidacies. A live
    run initially tried think=True (the hypothesis was that this call's
    small batches -- a handful of parties, not tens of citizens -- would
    dodge candidacy_considered's reasoning-budget bug even without the
    flag). That hypothesis was wrong: think=True reliably hit the identical
    failure (finish_reason='length', zero visible content) regardless of
    batch size -- the bug tracks the *subjective, comparative-judgment*
    prompt shape ("which of these is best"), not batch size. See
    ollama_structured_output_results.md's Finding E."""
    _check_supported(config)

    parties_by_id = {party.party_id: party for party in parties}
    contested: dict[int, list[Citizen]] = {}
    for party in sorted(parties, key=lambda p: p.party_id):
        members = [c for c in citizens if c.party_affiliation == party.party_id and c.citizen_id in declared_cids]
        if len(members) >= 2:
            contested[party.party_id] = members

    if not contested:
        return PartyNominationBatchOutcome(decisions=[], winners={})

    all_contenders = [c for members in contested.values() for c in members]
    support = {c.citizen_id: sympathizer_ratio(c, list(citizens)) for c in all_contenders}

    expected_party_ids = list(contested.keys())
    raw = client.complete_json(
        system_prompt=build_party_nomination_system_prompt(contested),
        user_prompt=build_party_nomination_user_prompt(contested, parties_by_id, support),
        json_schema=PARTY_NOMINATION_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(contested)),
        think=False,
    )
    decisions = decode_party_nomination_batch(raw, expected_party_ids)
    winners = {decision.party_id: resolve_party_nomination_cid(decision, contested[decision.party_id])
               for decision in decisions}

    return PartyNominationBatchOutcome(decisions=decisions, winners=winners)


@dataclass(frozen=True)
class PositioningBatchOutcome:
    decisions: list[PositioningDecision]
    platforms: dict[int, tuple[float, ...]]
    """cid -> resolved new pledged_platform (sincere position with validated
    shifts applied), ready to assign directly -- only this function has the
    sincere-position context needed to resolve a decision's sparse shifts
    into a full position tuple, mirroring how cast_votes resolves positions
    into ballots internally rather than exposing raw wire values."""


def apply_shifts(sincere: tuple[float, ...], shifts: Sequence[PositionShift]) -> tuple[float, ...]:
    """Applies a sparse set of validated shifts to a sincere position,
    clamping each shifted dimension to [0, 1] (positions must stay valid);
    dimensions with no shift are untouched. Pure -- bounds are already
    enforced by validate_positioning_decision before this is called."""
    positions = list(sincere)
    for shift in shifts:
        positions[shift.dimension] = min(1.0, max(0.0, positions[shift.dimension] + shift.delta))
    return tuple(positions)


def validate_positioning_decision(decision: PositioningDecision, config: PolityConfig) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without the caller's config: the real shift-count and per-shift
    delta-magnitude caps (campaign.max_positioning_shifts/max_positioning_delta
    -- tighter than PositioningDecision's own structural ceiling), and that
    a targeted dimension actually exists in this run's issue space."""
    if len(decision.shifts) > config.campaign.max_positioning_shifts:
        raise LlmResponseError(
            f"decision for cid={decision.cid} shifts {len(decision.shifts)} dimension(s), "
            f"exceeding campaign.max_positioning_shifts={config.campaign.max_positioning_shifts}"
        )
    issue_count = config.citizens.issue_count
    for shift in decision.shifts:
        if shift.dimension >= issue_count:
            raise LlmResponseError(
                f"decision for cid={decision.cid} targets dimension {shift.dimension}, "
                f"out of range for issue_count={issue_count}"
            )
        if abs(shift.delta) > config.campaign.max_positioning_delta:
            raise LlmResponseError(
                f"decision for cid={decision.cid} shifts dimension {shift.dimension} by "
                f"{shift.delta}, exceeding campaign.max_positioning_delta="
                f"{config.campaign.max_positioning_delta}"
            )


def build_positioning_system_prompt(nominees: Sequence[Citizen], config: PolityConfig) -> str:
    """Same "enumerate the full expected cid list verbatim + self-check"
    discipline as every prior decision type (Finding B precedent). Also
    states the ACTUAL numeric bounds (campaign.max_positioning_shifts/
    max_positioning_delta), not just the word "borne" -- the JSON schema
    itself only enforces a loose structural ceiling (max 5 shifts, delta in
    [-1,1]; see PositionShift/PositioningDecision), since the real,
    tighter, config-driven bound can't be baked into a schema defined at
    import time. Without stating the real numbers here, the model has no
    way to know what it's actually being validated against in
    validate_positioning_decision -- an omission that would make rejections
    common rather than a validated guardrail against rare cases."""
    cid_list = ",".join(str(n.citizen_id) for n in nominees)
    return (
        "Tu es un moteur de simulation. Pour chaque candidat nomme, decide "
        "s'il ajuste sa position affichee par rapport a sa position "
        "sincere (strategie de campagne), a partir de sa propre position, "
        "son ambition, la plateforme de son parti, les positions des "
        "autres candidats de ce scrutin, et la position moyenne de "
        "l'electorat.\nChaque ajustement (shifts) cible une dimension "
        "precise (0-indexee) avec un delta signe ; une liste vide signifie "
        "que le candidat reste sur sa position sincere.\nCONTRAINTES "
        f"STRICTES : au plus {config.campaign.max_positioning_shifts} "
        f"ajustements par decision, chaque delta strictement compris entre "
        f"-{config.campaign.max_positioning_delta} et "
        f"{config.campaign.max_positioning_delta} inclus. Toute decision "
        "hors de ces bornes sera rejetee.\n"
        f"Motifs valides (code court obligatoire) :\n{CAMPAIGN_MOTIF_PROMPT_TABLE}\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(nominees)} cid, chacun une seule fois, dans cet ordre : "
        f"[{cid_list}]. Verifie ta reponse avant de la finaliser : chaque "
        "cid de cette liste doit apparaitre exactement une fois.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_positioning_user_prompt(
    nominees: Sequence[Citizen],
    parties_by_id: dict[int, Party],
    electorate_mean: tuple[float, ...],
) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats), same
    reproducibility discipline as every prior prompt builder. `nominees` is
    expected to already be in the canonical order the caller (decide_
    campaign_positioning) enforces (sorted by citizen_id) -- this function
    doesn't re-sort, since the system prompt's verbatim expected-cid list
    must describe the exact same order shown here, not a second one. `rivals`
    is only the OTHER dominant nominees standing this tick -- rupture
    candidates (a separate, rare, deliberately unstrategized path) are not
    part of the rival-context signal, consistent with this function never
    being called for them. `electorate_mean` is computed once by the
    caller against the full population, not per-nominee."""
    nominee_blocks = []
    for nominee in nominees:
        party = parties_by_id.get(nominee.party_affiliation) if nominee.party_affiliation is not None else None
        rivals = [
            {"cid": other.citizen_id, "position": [round(x, 4) for x in other.issue_positions]}
            for other in nominees
            if other.citizen_id != nominee.citizen_id
        ]
        nominee_blocks.append(
            {
                "cid": nominee.citizen_id,
                "position": [round(x, 4) for x in nominee.issue_positions],
                "priorities": [round(x, 4) for x in nominee.issue_priorities],
                "ambition_score": round(nominee.ambition_score, 4),
                "party_platform": [round(x, 4) for x in party.platform] if party is not None else None,
                "rivals": rivals,
            }
        )
    return json.dumps(
        {"nominees": nominee_blocks, "electorate_mean": [round(x, 4) for x in electorate_mean]},
        sort_keys=True,
        separators=(",", ":"),
    )


def decide_campaign_positioning(
    nominees: Sequence[Citizen],
    citizens: Sequence[Citizen],
    parties_by_id: dict[int, Party],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> PositioningBatchOutcome:
    """v2 increment 4's replacement for declare_candidacy's sincere-platform
    pin, dominant nominees only (see this module's docstring for what stays
    out of scope). Pure aside from the injected client -- no journal writes
    here, matching every prior decide_* function's convention.

    Deliberately does NOT use chunk_voters/MIN_SAFE_BATCH_SIZE, same
    reasoning as decide_party_nominations: this batches this tick's
    *nominees* (a handful, `parties.initial_count` in the shipped config),
    not citizens.

    Calls the client with think=False, same guess as decide_party_nominations
    and the same reasoning: this is a comparative/strategic judgment against
    rivals and the electorate, closer to that decision's failure-prone shape
    than vote_cast's. Flagged for live verification, not assumed --
    see test_polity_llm_live.py."""
    _check_supported(config)

    if not nominees:
        return PositioningBatchOutcome(decisions=[], platforms={})

    # Sorted once, here, so system prompt / user prompt / expected_cids all
    # agree on the same order regardless of the caller's (party-iteration)
    # order -- never rely on an incidental insertion order (D-5 precedent).
    nominees = sorted(nominees, key=lambda n: n.citizen_id)
    electorate_mean = tuple(float(x) for x in np.mean([c.issue_positions for c in citizens], axis=0))
    expected_cids = [n.citizen_id for n in nominees]
    raw = client.complete_json(
        system_prompt=build_positioning_system_prompt(nominees, config),
        user_prompt=build_positioning_user_prompt(nominees, parties_by_id, electorate_mean),
        json_schema=POSITIONING_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(nominees)),
        think=False,
    )
    decisions = decode_positioning_batch(raw, expected_cids)

    nominees_by_id = {n.citizen_id: n for n in nominees}
    platforms: dict[int, tuple[float, ...]] = {}
    for decision in decisions:
        validate_positioning_decision(decision, config)
        platforms[decision.cid] = apply_shifts(nominees_by_id[decision.cid].issue_positions, decision.shifts)

    return PositioningBatchOutcome(decisions=decisions, platforms=platforms)
