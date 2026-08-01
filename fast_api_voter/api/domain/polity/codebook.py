"""
api.domain.polity.codebook — the compression tables of design doc §3.7,
vote-decision slice only (v2 increment 1).

Single source of truth: the `Literal[...]` types used for wire validation
(llm_schemas.py) and the human-readable table injected into the LLM's system
prompt (llm_behavior_engine.py) both derive from these enums, so the two
cannot silently drift apart — exactly the failure mode §3.7.0 calls out
("jamais une édition silencieuse de la version en cours").

`DecisionType` intentionally only defines VOTE_CAST (1). Per §3.7.1, codes
2-6 and 8-10 exist for other decision types not yet implemented; code 7
(`petition_signature_decision`) is retired and must never be reassigned —
recorded here as a comment, not a member, so nothing can accidentally reuse
it.
"""
from __future__ import annotations

from enum import IntEnum


class PolityCodebookError(ValueError):
    """Raised when a run's configured codebook_version doesn't match the
    one this code was written against — §3.7.0's frozen-artifact contract."""


CODEBOOK_VERSION = "1.0"


class DecisionType(IntEnum):
    """§3.7.1 `decision_type` (`dt`). Only the codes this increment writes
    are defined: 2=candidacy_considered, 3=candidacy_declared,
    4=party_nomination_choice, 5=campaign_positioning,
    6=representative_response, 8=reaction_to_event, 9=coalition_decision,
    10=pressure_action are reserved for later increments. 7 is retired
    (formerly petition_signature_decision) and must never be reused."""

    VOTE_CAST = 1


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


def check_codebook_version(config_version: str) -> None:
    if config_version != CODEBOOK_VERSION:
        raise PolityCodebookError(
            f"llm.codebook_version {config_version!r} does not match this code's "
            f"codebook version {CODEBOOK_VERSION!r} — regenerate or update one of them"
        )
