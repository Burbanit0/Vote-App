"""
api.domain.polity.llm_behavior_engine — v2 increment 1: the LLM replacement
for build_ranking (simple_rules.py), voting only. Every other decision
(candidacy, party nomination, coalition) stays on simple_rules.py.

Design doc §11.4's baseline-vs-LLM comparison depends on simple_rules.py
staying untouched and always available -- this module is additive, never a
modification of it. See simple_rules.py's own module docstring.

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
from dataclasses import dataclass
from typing import Sequence

from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import VOTE_MOTIF_PROMPT_TABLE, check_codebook_version
from api.domain.polity.config import PolityConfig
from api.domain.polity.llm_client import LlmClientProtocol, LlmResponseError, decode_vote_batch
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA, VoteCastDecision
from api.domain.polity.simple_rules import BLANK_LABEL, candidate_label

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


def build_system_prompt(citizens: Sequence[Citizen], candidate_count: int) -> str:
    """Enumerates the full expected cid list verbatim, not just a count --
    ollama_structured_output_results.md Finding B: a bare 'return exactly
    N decisions' instruction was empirically insufficient, the model
    dropped the last citizen of a 25-item batch despite it. The explicit
    list + self-check instruction fixed it on the first try."""
    truncate_at = truncation_limit(candidate_count)
    truncate_note = "" if truncate_at is None else f" (classer au plus les {truncate_at} meilleurs)"
    cid_list = ",".join(str(c.citizen_id) for c in citizens)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen recu, decide son "
        f"vote parmi les candidats.\nClasse les candidats du meilleur au "
        f"moins bon{truncate_note}, ou vote blanc (blank=1, ranking vide) si "
        "aucun candidat n'est acceptable.\nMotifs valides (code court "
        f"obligatoire) :\n{VOTE_MOTIF_PROMPT_TABLE}\nIMPORTANT : la liste "
        f"decisions doit contenir EXACTEMENT ces {len(citizens)} cid, chacun "
        f"une seule fois, dans cet ordre : [{cid_list}]. Verifie ta reponse "
        "avant de la finaliser : chaque cid de cette liste doit apparaitre "
        "exactement une fois.\nReponds UNIQUEMENT avec un objet JSON "
        "conforme au schema fourni."
    )


def build_user_prompt(voters: Sequence[Citizen], candidates: Sequence[Citizen]) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats) so
    the prompt is a pure function of the candidate *set* and voter *set*,
    never of iteration order -- required for the byte-for-byte
    reproducibility test (Lot 8). Candidates sorted by citizen_id (D-5):
    _declare_nominees assembles party nominees in party-iteration order
    then rupture candidates by citizen_id, and get_two_round_winner's
    Counter.most_common(2) tie-breaks by insertion order, so the prompt
    itself must not depend on that assembly order."""
    candidate_blocks = [
        {"cid": c.citizen_id, "platform": [round(x, 4) for x in _platform(c)], "party": c.party_affiliation}
        for c in sorted(candidates, key=lambda c: c.citizen_id)
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


def validate_decision(decision: VoteCastDecision, candidate_ids: set[int], truncate_at: int | None) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without knowing this batch's candidate set and truncation rule."""
    unknown = [cid for cid in decision.ranking if cid not in candidate_ids]
    if unknown:
        raise LlmResponseError(f"decision for cid={decision.cid} ranks unknown candidate cid(s) {unknown}")
    if truncate_at is not None and len(decision.ranking) > truncate_at:
        raise LlmResponseError(
            f"decision for cid={decision.cid} ranks {len(decision.ranking)} candidates, "
            f"exceeding the truncation limit of {truncate_at}"
        )
    if len(decision.ranking) > len(candidate_ids):
        raise LlmResponseError(
            f"decision for cid={decision.cid} ranks more candidates ({len(decision.ranking)}) "
            f"than exist in this batch ({len(candidate_ids)})"
        )


def ballot_from_decision(decision: VoteCastDecision, candidates_by_id: dict[int, Citizen]) -> list[str]:
    """Mirrors build_ranking's contract (Blank always present in the
    returned list) so ballot_and_aggregation.get_presidential_winner needs
    zero changes. blank=1 collapses to just [BLANK_LABEL] -- see the
    module docstring's note on this divergence from build_ranking, which
    ranks every candidate even for a voter beyond their own tolerance."""
    if decision.blank == 1:
        return [BLANK_LABEL]
    return [candidate_label(candidates_by_id[cid]) for cid in decision.ranking] + [BLANK_LABEL]


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

    candidate_ids = {c.citizen_id for c in candidates}
    candidates_by_id = {c.citizen_id: c for c in candidates}
    truncate_at = truncation_limit(len(candidates))

    ballots: list[list[str]] = []
    decisions: list[VoteCastDecision] = []
    for chunk in chunk_voters(voters, config.llm.max_batch_size):
        expected_cids = [voter.citizen_id for voter in chunk]
        max_tokens = max(len(chunk) * 60 + 256, 512)
        raw = client.complete_json(
            system_prompt=build_system_prompt(chunk, len(candidates)),
            user_prompt=build_user_prompt(chunk, candidates),
            json_schema=VOTE_CAST_JSON_SCHEMA,
            max_tokens=max_tokens,
        )
        chunk_decisions = decode_vote_batch(raw, expected_cids)
        for decision in chunk_decisions:
            validate_decision(decision, candidate_ids, truncate_at)
            ballots.append(ballot_from_decision(decision, candidates_by_id))
        decisions.extend(chunk_decisions)

    return VoteBatchOutcome(ballots=ballots, decisions=decisions)
