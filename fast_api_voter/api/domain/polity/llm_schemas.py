"""
api.domain.polity.llm_schemas — Pydantic wire schemas for the LLM's
`vote_cast` (design doc §3.6.1), `candidacy_considered` (§3.6.2), and
`party_nomination_choice` (§3.6.2->3.6.8, dt=4) decisions, v2 increments 1-3.

Lives in api/domain/polity/, not api/schemas/ — that package is the public
HTTP/OpenAPI surface (see voter-api skill); these are internal LLM wire
models that must never leak into openapi.gen.json. Follows the same
validation idiom as api/schemas/*.py (`extra="forbid"`, `Field(...)`,
`Literal[...]` for closed enums) so the strictness is familiar, but uses
this package's `X | None` style rather than `Optional[X]`.

Context-independent validation only (blank/ranking consistency, duplicate
positions) lives here, on the model itself. Context-dependent validation
(is a ranked position actually within this batch's candidate count? is the
ranking within this batch's truncation limit?) needs the caller's state and
belongs in llm_behavior_engine.py as plain functions, not here.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VoteCastDecision(BaseModel):
    """One citizen's ballot, design doc §3.6.1. `ranking` is required (no
    default) so JSON-Schema `strict` mode keeps it in `required` — an
    optional field with a default is silently dropped from `required` by
    Pydantic's schema generation, which would let a constrained-decoding
    grammar omit it entirely.

    `ranking` holds candidate *positions* (1..N, this batch's candidate
    list order), never candidate cids. A live consolidation run found the
    model conflates a cid-based ranking with `cid` above: a candidate is
    also a citizen, so candidate cids and voter cids draw from the same
    number space and can collide (e.g. citizen 11 both votes and is a
    candidate) -- the model started filling `cid` with candidate cids
    instead of the voter's own cid. Positions are a disjoint, always-small
    (1..N) number space, structurally incapable of that collision."""

    model_config = ConfigDict(extra="forbid")

    cid: int = Field(..., ge=0, description="citizen_id of the voter this decision belongs to.")
    blank: Literal[0, 1] = Field(
        ..., description="1 = bulletin blanc. Si 1, ranking doit être vide (§3.6.1)."
    )
    ranking: list[Annotated[int, Field(ge=1)]] = Field(
        ...,
        description="Positions (1..N, PAS des cid) des candidats classés, meilleur d'abord. Vide si blank=1.",
    )
    motif: Literal[101, 102, 103, 104] = Field(
        ..., description="Code court obligatoire (§3.6.9) — voir VoteMotif."
    )

    @model_validator(mode="after")
    def _check_blank_consistency(self) -> VoteCastDecision:
        if self.blank == 1 and self.ranking:
            raise ValueError("blank=1 requires an empty ranking (§3.6.1 hard rule)")
        if self.blank == 0 and not self.ranking:
            raise ValueError("blank=0 requires a non-empty ranking")
        if len(set(self.ranking)) != len(self.ranking):
            raise ValueError("ranking must not contain duplicate positions")
        return self


class VoteCastBatch(BaseModel):
    """§3.6.0's batch envelope, specialized to vote_cast."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[VoteCastDecision] = Field(..., min_length=1)


VOTE_CAST_JSON_SCHEMA = VoteCastBatch.model_json_schema()


class CandidacyDecision(BaseModel):
    """One citizen's dominant-path candidacy judgment, design doc §3.6.2 /
    §3.7.1. No `path` field: every citizen sent through this batch is by
    construction on the dominant path (the rupture path,
    attempt_rupture_candidacy in simple_rules.py, stays fully deterministic
    and never reaches the LLM), so it would be redundant context rather than
    a real distinction.

    No cross-field model_validator, unlike VoteCastDecision — `outcome` and
    `motif` are independent fields with nothing to keep consistent."""

    model_config = ConfigDict(extra="forbid")

    cid: int = Field(..., ge=0, description="citizen_id of the citizen this decision belongs to.")
    outcome: Literal[0, 1] = Field(..., description="0 = decline, 1 = declare (§3.7.1).")
    motif: Literal[201, 203, 204, 205] = Field(
        ..., description="Code court obligatoire (§3.7.2) — voir CandidacyMotif. 202 est réservé au chemin de rupture."
    )


class CandidacyBatch(BaseModel):
    """§3.6.0's batch envelope, specialized to candidacy_considered."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[CandidacyDecision] = Field(..., min_length=1)


CANDIDACY_JSON_SCHEMA = CandidacyBatch.model_json_schema()


class PartyNominationDecision(BaseModel):
    """One party's arbitration among its own declared/eligible members,
    design doc §2.3 / dt=4. Unlike VoteCastDecision/CandidacyDecision, the
    decision unit here is a *party*, not a citizen -- `party_id` is the
    alignment key decode_party_nomination_batch checks, not `cid`.

    `winner_position` is a 1-indexed position into THAT party's own
    candidate sub-list (as sent in build_party_nomination_user_prompt),
    never a raw cid -- same collision reasoning as VoteCastDecision.ranking
    (a candidate is also a citizen; cids are not a safe wire reference).
    Position numbering restarts at 1 for each party in the batch.

    No cross-field model_validator, mirroring CandidacyDecision: `motif` is
    an independent field, nothing to keep consistent with `winner_position`."""

    model_config = ConfigDict(extra="forbid")

    party_id: int = Field(..., ge=0, description="party_id this arbitration decision belongs to.")
    winner_position: int = Field(
        ..., ge=1, description="1-indexed position (PAS un cid) into this party's own candidate list."
    )
    motif: Literal[206, 207, 208, 209] = Field(
        ..., description="Code court obligatoire (§3.7.2) — voir PartyNominationMotif."
    )


class PartyNominationBatch(BaseModel):
    """§3.6.0's batch envelope, specialized to party_nomination_choice —
    one decision per *contested* party (2+ declared candidates), never one
    per citizen."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[PartyNominationDecision] = Field(..., min_length=1)


PARTY_NOMINATION_JSON_SCHEMA = PartyNominationBatch.model_json_schema()
