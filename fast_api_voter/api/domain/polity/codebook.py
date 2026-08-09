"""
api.domain.polity.codebook — the compression tables of design doc §3.7,
vote + candidacy-consideration + party-nomination slices (v2 increments 1-3).

Single source of truth: the `Literal[...]` types used for wire validation
(llm_schemas.py) and the human-readable table injected into the LLM's system
prompt (llm_behavior_engine.py) both derive from these enums, so the two
cannot silently drift apart — exactly the failure mode §3.7.0 calls out
("jamais une édition silencieuse de la version en cours").

`DecisionType` defines VOTE_CAST (1), CANDIDACY_CONSIDERED (2),
PARTY_NOMINATION_CHOICE (4), and CAMPAIGN_POSITIONING (5). CANDIDACY_DECLARED
(3) is deliberately NOT a member yet: `candidacy_declared` already exists as
a journal `event_type` string (run_polity_simulation.py) marking the
institutional outcome (a party's chosen nominee) — it is not itself a second
LLM decision, since a single `candidacy_considered` call's `outcome=1` case
(or, when a party is contested, `party_nomination_choice`'s winner) is what
produces it. Per §3.7.1, codes 6 and 8-10 exist for other decision types not
yet implemented; code 7 (`petition_signature_decision`) is retired and must
never be reassigned — recorded here as a comment, not a member, so nothing
can accidentally reuse it.
"""
from __future__ import annotations

from enum import IntEnum


class PolityCodebookError(ValueError):
    """Raised when a run's configured codebook_version doesn't match the
    one this code was written against — §3.7.0's frozen-artifact contract."""


CODEBOOK_VERSION = "1.0"


class DecisionType(IntEnum):
    """§3.7.1 `decision_type` (`dt`). Only the codes this increment writes
    are defined: 6=representative_response, 8=reaction_to_event,
    9=coalition_decision, 10=pressure_action are reserved for later
    increments. 7 is retired (formerly petition_signature_decision) and
    must never be reused."""

    VOTE_CAST = 1
    CANDIDACY_CONSIDERED = 2
    PARTY_NOMINATION_CHOICE = 4
    CAMPAIGN_POSITIONING = 5


class BallotFormat(IntEnum):
    """§3.7.1 `ballot_format` (`bf`). 2=approval, 3=scores, 4=binary are
    reserved for methods not exercised by this increment's default
    (two_round, a ranking-family method)."""

    RANKING = 1


class VoteMotif(IntEnum):
    """§3.7.2 motif range 100-199 (Vote). 102 (SOCIAL_CONTAGION) and 103
    (RETROSPECTIVE_PUNISHMENT) require infrastructure this increment doesn't
    have yet (the social graph is v6; retrospective memory needs
    memory_window_terms, unused in v0/v1) — kept as valid codes per §3.7.2's
    "liste non figée", but expect 101/104 to dominate in practice. Record
    the observed distribution rather than pruning the enum."""

    NO_MATCHING_PRIORITY = 101
    SOCIAL_CONTAGION = 102
    RETROSPECTIVE_PUNISHMENT = 103
    STRATEGIC_DEFECTION = 104


VOTE_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in VoteMotif)


class CandidacyOutcome(IntEnum):
    """§3.7.1 `outcome` (candidature)."""

    DECLINED = 0
    DECLARED = 1


class CandidacyMotif(IntEnum):
    """§3.7.2 motif range 200-299 (Candidature). 202 (IDEOLOGICAL_RUPTURE) is
    deliberately NOT a member here: it's the rupture path's own motif
    (attempt_rupture_candidacy, simple_rules.py), which stays fully
    deterministic and never calls the LLM — reusing 202 for a dominant-path
    decline would misattribute rupture semantics to a citizen who never took
    that path. 204/205 are new codes (§3.7.2's list is explicitly "non
    figée") for the decline-nuances a bare ambition_score threshold can't
    express — the actual reason this decision is LLM-governed instead of a
    threshold at all."""

    INSUFFICIENT_PERCEIVED_SUPPORT = 201
    AMBITION_THRESHOLD_MET = 203
    AMBITION_INSUFFICIENT = 204
    RISK_AVERSE_DEFERRAL = 205


CANDIDACY_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in CandidacyMotif)


class PartyNominationMotif(IntEnum):
    """§3.7.2 motif range 200-299 (Candidature) — extended, not a new range.
    The design doc's §3.7.2 table never allocated a range to
    party_nomination_choice (dt=4) at all; reusing 200-299 (rather than
    inventing an unallocated block) follows the same precedent as
    CandidacyMotif's own 204/205 additions, and keeps "why did this citizen
    become a candidate" and "why THIS one among several" in one place. Codes
    206-209 map directly to the three signals build_party_nomination_user_prompt
    actually sends (ambition_score, perceived_support, platform_distance),
    plus one holistic catch-all — closed-enum per project convention, never
    free text."""

    HIGHEST_AMBITION = 206
    BROADEST_PERCEIVED_SUPPORT = 207
    CLOSEST_TO_PARTY_PLATFORM = 208
    STRATEGIC_ELECTABILITY = 209


PARTY_NOMINATION_MOTIF_PROMPT_TABLE = "\n".join(
    f"{motif.value} = {motif.name}" for motif in PartyNominationMotif
)


class CampaignMotif(IntEnum):
    """§3.7.2 motif range 600-699 (Campagne) — a NEW range, unlike
    party_nomination_choice's reuse of 200-299. Positioning strategy is a
    distinct concept from candidature itself (whether/who becomes a
    candidate): it's about how a already-confirmed nominee presents
    themselves. Each code maps directly to a signal
    build_positioning_user_prompt actually sends (own position, rival
    nominees, electorate mean) so the observed motif distribution is a real
    read on emergent strategy, not an arbitrary label."""

    SINCERE_CONVICTION = 601
    MEDIAN_VOTER_APPEAL = 602
    BASE_CONSOLIDATION = 603
    DIFFERENTIATION_FROM_RIVALS = 604


CAMPAIGN_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in CampaignMotif)


def check_codebook_version(config_version: str) -> None:
    if config_version != CODEBOOK_VERSION:
        raise PolityCodebookError(
            f"llm.codebook_version {config_version!r} does not match this code's "
            f"codebook version {CODEBOOK_VERSION!r} — regenerate or update one of them"
        )
