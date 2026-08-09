"""
api.domain.polity.llm_schemas — Pydantic wire schemas for the LLM's
`vote_cast` (design doc §3.6.1), `candidacy_considered` (§3.6.2),
`party_nomination_choice` (§3.6.2->3.6.8, dt=4), `campaign_positioning`
(§3.6.2->3.6.8, dt=5), and `coalition_decision` (§3.6.2->3.6.8, dt=9)
decisions, v2 increments 1-5.

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


class PositionShift(BaseModel):
    """One sparse move along a single issue dimension, design doc
    §3.6.2->3.6.8's "delta borné" (never a full issue_count-length vector —
    §3.6.5's own example represents a delta the same sparse way,
    `{"7": -0.15}`). `delta`'s Field bound here is a loose structural
    ceiling only, NOT the real cap — Ollama's structured-output "strict"
    mode requires a closed schema (no dynamic dict keys), so a Pydantic
    `dict[str, float]` isn't an option; a bounded list of this fixed
    sub-model is the strict-mode-compatible equivalent. The actual
    campaign.max_positioning_delta bound is enforced in
    llm_behavior_engine.validate_positioning_decision, which has the config
    this schema (defined at import time) can't see."""

    model_config = ConfigDict(extra="forbid")

    dimension: int = Field(..., ge=0, description="0-indexed issue dimension this shift applies to.")
    delta: float = Field(..., ge=-1.0, le=1.0, description="Signed shift; the real bound is campaign.max_positioning_delta.")


class PositioningDecision(BaseModel):
    """One nominee's campaign-positioning judgment, design doc §3.6.2->3.6.8
    / dt=5. `shifts` is capped at a generous structural ceiling here
    (max_length=5) — campaign.max_positioning_shifts is the real, tighter
    cap, enforced in llm_behavior_engine.py alongside per-shift delta
    magnitude. An empty list means the nominee runs on their sincere
    position (motif=SINCERE_CONVICTION)."""

    model_config = ConfigDict(extra="forbid")

    cid: int = Field(..., ge=0, description="citizen_id of the nominee this decision belongs to.")
    shifts: list[PositionShift] = Field(..., max_length=5)
    motif: Literal[601, 602, 603, 604] = Field(
        ..., description="Code court obligatoire (§3.7.2) — voir CampaignMotif."
    )

    @model_validator(mode="after")
    def _check_no_duplicate_dimensions(self) -> PositioningDecision:
        dimensions = [shift.dimension for shift in self.shifts]
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("shifts must not target the same dimension twice")
        return self


class PositioningBatch(BaseModel):
    """§3.6.0's batch envelope, specialized to campaign_positioning — one
    decision per nominee standing in this tick's presidential election."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[PositioningDecision] = Field(..., min_length=1)


POSITIONING_JSON_SCHEMA = PositioningBatch.model_json_schema()


class CoalitionDecision(BaseModel):
    """One seated, non-initiator party's answer to the designated
    formateur's coalition, design doc §3.7.1 / dt=9. Party-keyed like
    PartyNominationDecision, not citizen-keyed — `party_id` is the
    alignment key decode_coalition_batch checks.

    `action` is restricted to JOIN/LEAVE (1/2): 3 (maintain) belongs to the
    deferred maintenance-across-ticks palier, 4 (propose) to the initiator,
    which stays a deterministic institutional designation and is never
    asked (see CoalitionAction, codebook.py).

    Unlike CandidacyDecision/PartyNominationDecision, `motif` is NOT
    independent of `action` here: 501/502 are join-reasons, 504/505 are
    decline-reasons (CoalitionMotif, codebook.py). Pairing them the other
    way would describe a different decision than the one actually recorded,
    silently corrupting the motif distribution that's the whole
    observability point of §3.7 — so the coherence is enforced here,
    context-independently, the same way VoteCastDecision enforces its own
    blank/ranking rule."""

    model_config = ConfigDict(extra="forbid")

    party_id: int = Field(..., ge=0, description="party_id this coalition answer belongs to.")
    action: Literal[1, 2] = Field(..., description="1 = join, 2 = leave (§3.7.1) — voir CoalitionAction.")
    motif: Literal[501, 502, 504, 505] = Field(
        ..., description="Code court obligatoire (§3.7.2) — voir CoalitionMotif."
    )

    @model_validator(mode="after")
    def _check_action_motif_coherence(self) -> CoalitionDecision:
        if self.action == 1 and self.motif not in (501, 502):
            raise ValueError("action=1 (join) requires motif 501 or 502")
        if self.action == 2 and self.motif not in (504, 505):
            raise ValueError("action=2 (leave) requires motif 504 or 505")
        return self


class CoalitionBatch(BaseModel):
    """§3.6.0's batch envelope, specialized to coalition_decision — one
    decision per seated, non-initiator party."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[CoalitionDecision] = Field(..., min_length=1)


COALITION_JSON_SCHEMA = CoalitionBatch.model_json_schema()
