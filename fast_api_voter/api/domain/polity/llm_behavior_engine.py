"""
api.domain.polity.llm_behavior_engine — v2 increments 1-5: the LLM
replacement for build_ranking (voting), decide_candidacy (dominant-path
candidacy eligibility only), select_party_nominee_from_declared's tiebreak
when a party is contested (2+ declared candidates), declare_candidacy's
sincere-platform pin for dominant nominees (campaign_positioning), and
form_coalition's willingness-to-join step (coalition_decision). The rupture
candidacy path, the coalition initiator designation, and coalition
maintenance/rupture across ticks all stay on simple_rules.py / out of
scope — see decide_coalition's own docstring.

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

decide_coalition (increment 5) only asks each seated, non-initiator party
whether it joins the designated formateur's coalition -- the initiator
itself is a deterministic institutional designation (tiebreak_key,
simple_rules.py), never an LLM output, and assemble_coalition resolves the
willing subset into a coalition using form_coalition's own distance-based
ordering, so the LLM's causal contribution is isolated to willingness only.
Formation only: coalition maintenance/rupture across subsequent ticks
(design doc §3.1's "maintien et rupture") is out of scope for this
increment -- see decide_coalition's own docstring for why.

decide_representative_response (v4 Lot 6, dt=6) is the first decision type
in this module that runs EVERY tick, not just at an election, and the first
one that mutates a sitting officeholder (revealed_position) rather than a
candidate. It is handed an already-frozen `Mapping[int, ResponseContext]`
built by its caller (run_polity_simulation._run_representative_responses)
and must never read a Citizen's live `street_pressure` itself -- the
one-tick lag §7bis.7 requires is a property of when that context was
captured, not of anything this function does, and this function has no way
to violate it by construction (it only sees the frozen snapshot).

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
from typing import Mapping, Sequence

import numpy as np

from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import (
    CAMPAIGN_MOTIF_PROMPT_TABLE,
    CANDIDACY_MOTIF_PROMPT_TABLE,
    COALITION_ACTION_PROMPT_TABLE,
    COALITION_MOTIF_PROMPT_TABLE,
    PARTY_NOMINATION_MOTIF_PROMPT_TABLE,
    RESPONSE_MOTIF_PROMPT_TABLE,
    STANCE_PROMPT_TABLE,
    VOTE_MOTIF_PROMPT_TABLE,
    CoalitionAction,
    check_codebook_version,
)
from api.domain.polity.config import PolityConfig
from api.domain.polity.llm_client import (
    LlmClientProtocol,
    LlmResponseError,
    decode_candidacy_batch,
    decode_coalition_batch,
    decode_party_nomination_batch,
    decode_positioning_batch,
    decode_response_batch,
    decode_vote_batch,
)
from api.domain.polity.llm_schemas import (
    CANDIDACY_JSON_SCHEMA,
    COALITION_JSON_SCHEMA,
    PARTY_NOMINATION_JSON_SCHEMA,
    POSITIONING_JSON_SCHEMA,
    RESPONSE_JSON_SCHEMA,
    VOTE_CAST_JSON_SCHEMA,
    CandidacyDecision,
    CoalitionDecision,
    PartyNominationDecision,
    PositioningDecision,
    PositionShift,
    ResponseDecision,
    VoteCastDecision,
)
from api.domain.polity.parties import Party
from api.domain.polity.simple_rules import BLANK_LABEL, candidate_label, sympathizer_ratio, tiebreak_key

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


@dataclass(frozen=True)
class ResponseContext:
    """§3.6.5's `ctx` block, frozen at the moment the caller reads it -- the
    structural half of §7bis.7's one-tick lag (v4 Lot 6). `street` is
    street_pressure as of the END of the previous tick; the caller
    (run_polity_simulation._run_accountability_phase, via
    _run_representative_responses) captures it before this tick's step-2/3
    mutations, and this module never touches the live field -- it only ever
    reads what it's handed here. A None field means "this polity does not
    track that quantity" (legitimacy disabled, street pressure disabled or
    invisible, no term end) -- never 0.0, which would be a false claim
    about the polity's state (§3.6.6's own neighbors_acting=null
    precedent)."""

    cid: int
    legitimacy: float | None
    mandate_dev: float
    street: float | None
    lame_duck: bool
    ticks_left: int | None

    def to_payload(self) -> dict[str, float | int | None]:
        """§3.6.5's exact key names, rounded like every other prompt
        builder. Used by BOTH build_response_user_prompt and the journal
        write (run_polity_simulation.py), so the ctx an analyst reads is
        provably the ctx the model saw -- not a reconstruction that can
        drift from it."""
        return {
            "L": round(self.legitimacy, 4) if self.legitimacy is not None else None,
            "mandate_dev": round(self.mandate_dev, 4),
            "street": round(self.street, 4) if self.street is not None else None,
            "lame_duck": int(self.lame_duck),
            "ticks_left": self.ticks_left,
        }


@dataclass(frozen=True)
class ResponseBatchOutcome:
    decisions: list[ResponseDecision]
    positions: dict[int, tuple[float, ...]]
    """cid -> resolved new revealed_position (the holder's CURRENT
    revealed_position with validated shifts applied, so drift accumulates
    across ticks -- see validate_response_decision/apply_shifts). Unlike
    PositioningBatchOutcome's `platforms`, pledged_platform is never
    resolved here: the promise is immutable for the term, which is the
    only reason mandate_deviation means anything (§7bis.5)."""


def validate_response_decision(decision: ResponseDecision, config: PolityConfig) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without the caller's config: the real shift-count and per-shift
    delta-magnitude caps -- mandate.max_response_shifts/max_response_delta
    (v4 Lot 1), deliberately NOT campaign.max_positioning_shifts/
    max_positioning_delta -- mid-term mandate drift and campaign-time
    strategy must stay analytically separable (MandateConfig's own
    docstring) -- and that a targeted dimension actually exists in this
    run's issue space. Structurally identical to
    validate_positioning_decision, reading a different config section."""
    if len(decision.shifts) > config.mandate.max_response_shifts:
        raise LlmResponseError(
            f"decision for cid={decision.cid} shifts {len(decision.shifts)} dimension(s), "
            f"exceeding mandate.max_response_shifts={config.mandate.max_response_shifts}"
        )
    issue_count = config.citizens.issue_count
    for shift in decision.shifts:
        if shift.dimension >= issue_count:
            raise LlmResponseError(
                f"decision for cid={decision.cid} targets dimension {shift.dimension}, "
                f"out of range for issue_count={issue_count}"
            )
        if abs(shift.delta) > config.mandate.max_response_delta:
            raise LlmResponseError(
                f"decision for cid={decision.cid} shifts dimension {shift.dimension} by "
                f"{shift.delta}, exceeding mandate.max_response_delta="
                f"{config.mandate.max_response_delta}"
            )


def build_response_system_prompt(holders: Sequence[Citizen], config: PolityConfig) -> str:
    """Same "enumerate the full expected cid list verbatim + self-check"
    discipline as every prior decision type (Finding B precedent). States
    the ACTUAL numeric bounds (mandate.max_response_shifts/
    max_response_delta), not just the schema's loose structural ceiling --
    same reasoning as build_positioning_system_prompt. Also states the
    stance<->shifts and stance<->motif pairing rules explicitly: these are
    cross-field rules constrained decoding cannot enforce on its own (the
    prompt is the only prevention; llm_schemas.py's model validators are
    the guardrail behind it), and explains ctx's scale for each field --
    L in [0,1], mandate_dev a weighted distance from the pledge, street an
    UNBOUNDED mobilization accumulator (0=none, >=1=sustained, deliberately
    not normalized -- écart(t) consumes the same unnormalized number),
    lame_duck 0/1, ticks_left ticks to the next presidential election, and
    that a null ctx field means "not tracked in this polity", never
    zero."""
    cid_list = ",".join(str(h.citizen_id) for h in holders)
    return (
        "Tu es un moteur de simulation. Pour chaque elu recu "
        "(representative_response), decide sa reaction a la pression "
        "citoyenne et institutionnelle percue, a partir de sa promesse "
        "electorale, de sa position actuelle, et du contexte ctx.\n"
        "ctx.L : legitimite actuelle dans [0,1], null si non suivie.\n"
        "ctx.mandate_dev : ecart pondere entre la promesse et la position "
        "actuelle, deja accumule.\n"
        "ctx.street : pression de rue, un accumulateur NON BORNE (0 = "
        "aucune mobilisation, >=1 = mobilisation soutenue), null si non "
        "suivie ou non visible.\n"
        "ctx.lame_duck : 1 si l'elu a atteint la limite de mandats, "
        "sinon 0.\nctx.ticks_left : nombre de ticks avant la prochaine "
        "election presidentielle, null si aucune election prevue.\n"
        "Un champ ctx a null signifie que cette grandeur n'est pas suivie "
        "dans cette simulation, jamais qu'elle vaut zero.\n"
        f"stance : {STANCE_PROMPT_TABLE}\n"
        "shifts : au plus "
        f"{config.mandate.max_response_shifts} ajustements de position, "
        f"chaque delta strictement compris entre "
        f"-{config.mandate.max_response_delta} et "
        f"{config.mandate.max_response_delta} inclus. stance=1 "
        "(concession) exige au moins un ajustement ; stance=3 (silence) "
        "exige une liste vide.\n"
        f"Motifs valides (code court obligatoire) :\n{RESPONSE_MOTIF_PROMPT_TABLE}\n"
        "REGLE DE COHERENCE stance/motif obligatoire : stance=1 (concession) "
        "exige motif 301, 302 ou 303 ; stance=2 (defiance) exige motif "
        "307 ; stance=3 (silence) exige motif 308 ; stance=4 "
        "(counter_mobilization) exige motif 309. Toute decision hors de "
        "ces regles sera rejetee.\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(holders)} cid, chacun une seule fois, dans cet ordre : "
        f"[{cid_list}]. Verifie ta reponse avant de la finaliser : chaque "
        "cid de cette liste doit apparaitre exactement une fois.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_response_user_prompt(holders: Sequence[Citizen], contexts: Mapping[int, ResponseContext]) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats), same
    reproducibility discipline as every prior prompt builder. `holders` is
    expected to already be in the canonical order the caller (decide_
    representative_response) enforces (sorted by citizen_id) -- this
    function doesn't re-sort, since the system prompt's verbatim
    expected-cid list must describe the exact same order shown here.
    Top-level key "holders" -- a sixth decision type needs a sixth
    unambiguous key so a fake/stub client can dispatch on it unambiguously
    (see _FakeLlmClient, test_polity_run_simulation.py)."""
    holder_blocks = []
    for holder in holders:
        assert holder.pledged_platform is not None and holder.revealed_position is not None
        holder_blocks.append(
            {
                "cid": holder.citizen_id,
                "office": 1,  # Office.PRESIDENT, §3.7.1
                "pledged_platform": [round(x, 4) for x in holder.pledged_platform],
                "revealed_position": [round(x, 4) for x in holder.revealed_position],
                "priorities": [round(x, 4) for x in holder.issue_priorities],
                "ctx": contexts[holder.citizen_id].to_payload(),
            }
        )
    return json.dumps({"holders": holder_blocks}, sort_keys=True, separators=(",", ":"))


def decide_representative_response(
    holders: Sequence[Citizen],
    contexts: Mapping[int, ResponseContext],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> ResponseBatchOutcome:
    """v4 Lot 6's dt=6 replacement for the status-quo deterministic fallback
    (see run_polity_simulation._run_representative_responses's own
    docstring for why there is no simple_rules.py baseline function to
    replace -- "no delta, stance=silence" is already true by construction
    without this module ever running).

    Deliberately does NOT use chunk_voters/MIN_SAFE_BATCH_SIZE, same
    reasoning as decide_party_nominations/decide_campaign_positioning:
    this batches this tick's sitting OFFICEHOLDERS (0-or-1 today, president
    only -- Office.DEPUTY is never assigned), not citizens.

    Calls the client with think=False -- no longer a guess for this
    decision type: scripts/lot6_batch_reliability_results.md measured
    16/16 clean responses for this exact schema at batch sizes 1/3/5/10
    through Ollama's native /api/chat think=false path (with its own
    documented caveat: not a guarantee, see that file)."""
    _check_supported(config)

    if not holders:
        return ResponseBatchOutcome(decisions=[], positions={})

    # Sorted once, here, so system prompt / user prompt / expected_cids all
    # agree on the same order regardless of the caller's order -- never
    # rely on an incidental insertion order (D-5 precedent).
    holders = sorted(holders, key=lambda h: h.citizen_id)
    expected_cids = [h.citizen_id for h in holders]
    raw = client.complete_json(
        system_prompt=build_response_system_prompt(holders, config),
        user_prompt=build_response_user_prompt(holders, contexts),
        json_schema=RESPONSE_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(holders)),
        think=False,
    )
    decisions = decode_response_batch(raw, expected_cids)

    holders_by_id = {h.citizen_id: h for h in holders}
    positions: dict[int, tuple[float, ...]] = {}
    for decision in decisions:
        validate_response_decision(decision, config)
        holder = holders_by_id[decision.cid]
        assert holder.revealed_position is not None  # guaranteed by the caller's own filter
        positions[decision.cid] = apply_shifts(holder.revealed_position, decision.shifts)

    return ResponseBatchOutcome(decisions=decisions, positions=positions)


@dataclass(frozen=True)
class CoalitionBatchOutcome:
    decisions: list[CoalitionDecision]
    initiator: int | None
    coalition: list[int] | None
    """Already assembled into form_coalition's exact return shape
    (list[int] | None) -- only this module has the platform/seat context the
    assembly needs, mirroring how cast_votes resolves positions into ballots
    internally rather than exposing raw wire values. metrics.py consumes
    this unchanged."""


def build_coalition_system_prompt(
    responder_party_ids: Sequence[int],
    initiator: int,
    initiator_seats: int,
    total_seats: int,
    majority_seats_threshold: float,
) -> str:
    """Mirrors build_party_nomination_system_prompt's "enumerate the full
    expected id list verbatim + self-check" discipline (Finding B), keyed on
    party_id -- the decision unit here is a seated party, not a citizen.
    States the ACTUAL institutional numbers (total_seats,
    majority_seats_threshold, the initiator's own party_id/seats), not just
    the word "majorite" -- the increment 4 lesson (a prompt/validator bound
    mismatch shipped as a real bug) applies here too: every number the code
    later compares against is stated explicitly. States the action<->motif
    coherence rule explicitly, since CoalitionDecision's model_validator
    enforces it strictly. No coalition-theory framing anywhere in this
    prompt (§3.3 -- no "prefer a minimal winning coalition", no strategy
    hint of any kind): only the rules of the game and the closed code
    tables."""
    party_id_list = ",".join(str(pid) for pid in responder_party_ids)
    return (
        f"Tu es un moteur de simulation. Le parti {initiator} (avec "
        f"{initiator_seats} sieges) vient d'etre designe formateur et "
        "cherche a former une coalition gouvernementale. Pour chaque parti "
        "recu, decide s'il rejoint cette coalition (action=1) ou refuse "
        "(action=2), a partir de sa propre position, de sa proximite avec "
        "le formateur, de son nombre de sieges, et de ce qu'il manque au "
        f"formateur pour la majorite.\nL'assemblee compte {total_seats} "
        "sieges au total ; la coalition doit depasser strictement "
        f"{majority_seats_threshold} sieges pour atteindre la majorite.\n"
        f"Actions valides :\n{COALITION_ACTION_PROMPT_TABLE}\nMotifs "
        f"valides (code court obligatoire) :\n{COALITION_MOTIF_PROMPT_TABLE}\n"
        "CONTRAINTE STRICTE : le motif doit correspondre a l'action -- 501 "
        "ou 502 si action=1, 504 ou 505 si action=2. Toute autre "
        "combinaison sera rejetee.\nIMPORTANT : la liste decisions doit "
        f"contenir EXACTEMENT ces {len(responder_party_ids)} party_id, "
        f"chacun une seule fois, dans cet ordre : [{party_id_list}]. "
        "Verifie ta reponse avant de la finaliser : chaque party_id de "
        "cette liste doit apparaitre exactement une fois.\nReponds "
        "UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_coalition_user_prompt(
    responder_party_ids: Sequence[int],
    initiator: int,
    party_platforms: dict[int, tuple[float, ...]],
    seats: dict[int, int],
    votes: dict[int, float],
    total_seats: int,
    majority_seats_threshold: float,
) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats), same
    reproducibility discipline as every prior prompt builder.
    `responder_party_ids` is expected already sorted by the caller (D-5
    precedent) -- this function does not re-sort, so the system prompt's
    verbatim id list and this user prompt describe one order, not two.
    `distance_to_initiator` reuses form_coalition's own unweighted
    math.dist convention, not the voter-tolerance-specific
    _weighted_distance. Deliberately does NOT include a roster of the other
    responders' own context (§3.3 -- a single-shot call cannot express "I
    join iff party X joins"; that conditional-coalition reasoning is what
    the deferred v7 multi-turn negotiation palier, §3.4 Cas 2, exists
    for)."""
    initiator_shortfall = max(0.0, majority_seats_threshold - seats[initiator])
    responder_blocks = [
        {
            "party_id": pid,
            "seats": seats[pid],
            "votes": round(votes.get(pid, 0.0), 4),
            "distance_to_initiator": round(math.dist(party_platforms[pid], party_platforms[initiator]), 4),
        }
        for pid in responder_party_ids
    ]
    return json.dumps(
        {
            "assembly": {
                "total_seats": total_seats,
                "majority_seats_threshold": round(majority_seats_threshold, 4),
                "initiator_shortfall": round(initiator_shortfall, 4),
            },
            "initiator": {
                "party_id": initiator,
                "platform": [round(x, 4) for x in party_platforms[initiator]],
                "seats": seats[initiator],
                "votes": round(votes.get(initiator, 0.0), 4),
            },
            "responders": responder_blocks,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_coalition_decision(decision: CoalitionDecision, seats: dict[int, int], initiator: int) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without the caller's seats/initiator state. coalition_decision emits
    a closed enum, so unlike validate_positioning_decision there is no
    config-driven numeric bound to enforce here -- what remains are the two
    preconditions assemble_coalition relies on that the wire cannot know on
    its own: the deciding party actually holds a seat, and it isn't the
    initiator (whose own action is never asked -- see decide_coalition)."""
    if decision.party_id == initiator:
        raise LlmResponseError(
            f"decision for party_id={decision.party_id} is the initiator -- its own action is never asked"
        )
    if seats.get(decision.party_id, 0) <= 0:
        raise LlmResponseError(f"decision for party_id={decision.party_id} does not hold a seat in this assembly")


def assemble_coalition(
    decisions: Sequence[CoalitionDecision],
    initiator: int,
    party_platforms: dict[int, tuple[float, ...]],
    seats: dict[int, int],
    majority_ratio: float,
) -> list[int] | None:
    """Turns a validated batch of join/leave decisions into the exact
    `list[int] | None` shape simple_rules.form_coalition already returns,
    so metrics.py needs zero changes. Deliberately reuses form_coalition's
    OWN ordering (ascending distance from the initiator, tie-broken by seats
    descending then party_id) over just the `join`-voting subset -- this
    isolates the LLM's causal contribution to willingness only, and buys a
    directly testable invariant: unanimous join produces byte-identical
    output to what form_coalition would return on the same inputs (see
    test_polity_llm_behavior_engine.py's parity test)."""
    total_seats = sum(seats.values())
    threshold = majority_ratio * total_seats

    coalition = [initiator]
    coalition_seats = seats[initiator]
    if coalition_seats > threshold:
        return coalition

    joiners = [d.party_id for d in decisions if d.action == CoalitionAction.JOIN.value]
    joiners.sort(
        key=lambda pid: (
            math.dist(party_platforms[pid], party_platforms[initiator]),
            -seats[pid],
            pid,
        )
    )
    for pid in joiners:
        coalition.append(pid)
        coalition_seats += seats[pid]
        if coalition_seats > threshold:
            return coalition

    return None


def decide_coalition(
    parties: Sequence[Party],
    seats: dict[int, int],
    votes: dict[int, float],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> CoalitionBatchOutcome:
    """v2 increment 5's replacement for form_coalition's nearest-neighbour
    greedy aggregation -- the initiator designation, the majority rule, and
    the ordering in which willing partners are added all stay deterministic
    (see assemble_coalition); the LLM contributes only each seated,
    non-initiator party's willingness to join. Pure aside from the injected
    client -- no journal writes here, matching every prior decide_*
    function's convention; run_polity_simulation.py owns every journal
    write.

    Formation only: design doc §3.1's "maintien et rupture" of a coalition
    across subsequent ticks is out of scope for this increment. Reasons: no
    tick hook exists for it today (this module only touches coalitions
    inside `election in (LEGISLATIVE, BOTH)`); it would need new cross-tick
    state (a standing `current_coalition`) this increment deliberately
    doesn't introduce; the design doc gives it no consequence model (what
    happens when a coalition ruptures mid-term has no mechanic anywhere);
    and a mid-term rupture would break metrics.coalition_lifespans' "until
    the next legislative election" assumption -- exactly the metrics
    compatibility this increment promises to preserve.

    Deliberately does NOT use chunk_voters/MIN_SAFE_BATCH_SIZE, same
    reasoning as decide_party_nominations/decide_campaign_positioning: this
    batches seated parties (a handful at most, parties.initial_count in the
    shipped config), not citizens.

    Skips the client entirely (no network call) when no party holds a seat,
    when the initiator alone already clears the majority, or when there are
    no non-initiator seated parties to ask -- mirrors form_coalition's own
    short-circuits and avoids violating CoalitionBatch's min_length=1.

    Calls the client with think=False, the same guess as increments 3/4's
    comparative-judgment prompt shape ("do you join THIS coalition"),
    flagged for live verification rather than assumed -- see
    test_polity_llm_live.py."""
    _check_supported(config)

    party_platforms = {party.party_id: party.platform for party in parties}
    seated = sorted(pid for pid, s in seats.items() if s > 0)
    if not seated:
        return CoalitionBatchOutcome(decisions=[], initiator=None, coalition=None)

    total_seats = sum(seats.values())
    majority_ratio = config.parties.coalition_majority_ratio
    threshold = majority_ratio * total_seats

    initiator = min(seated, key=lambda pid: tiebreak_key(pid, seats, votes, config.parties.coalition_tiebreak))
    if seats[initiator] > threshold:
        return CoalitionBatchOutcome(decisions=[], initiator=initiator, coalition=[initiator])

    responders = [pid for pid in seated if pid != initiator]
    if not responders:
        return CoalitionBatchOutcome(decisions=[], initiator=initiator, coalition=None)

    raw = client.complete_json(
        system_prompt=build_coalition_system_prompt(
            responders, initiator, seats[initiator], total_seats, threshold
        ),
        user_prompt=build_coalition_user_prompt(
            responders, initiator, party_platforms, seats, votes, total_seats, threshold
        ),
        json_schema=COALITION_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(responders)),
        think=False,
    )
    decisions = decode_coalition_batch(raw, responders)
    for decision in decisions:
        validate_coalition_decision(decision, seats, initiator)

    coalition = assemble_coalition(decisions, initiator, party_platforms, seats, majority_ratio)
    return CoalitionBatchOutcome(decisions=decisions, initiator=initiator, coalition=coalition)
