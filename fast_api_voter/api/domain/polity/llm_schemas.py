"""
api.domain.polity.llm_schemas — Pydantic wire schemas for the LLM's
`vote_cast` (design doc §3.6.1), `candidacy_considered` (§3.6.2),
`party_nomination_choice` (§3.6.2->3.6.8, dt=4), `campaign_positioning`
(§3.6.2->3.6.8, dt=5), `coalition_decision` (§3.6.2->3.6.8, dt=9), v2
increments 1-5, `representative_response` (§3.6.5, dt=6), v4 Lot 6,
`pressure_action` (§3.6.6, dt=10), v4 Lot 7, and `reaction_to_event`
(§8, dt=8), v5 Lot 4.

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
    motif: Literal[101, 102, 103, 104, 105] = Field(
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


class ResponseDecision(BaseModel):
    """One sitting officeholder's reaction to citizen pressure, design doc
    §3.6.5 — the "schéma central de la révision 2". Reuses increment 4's
    PositionShift verbatim: §3.6.5's own example expresses its delta the same
    sparse way (`{"7": -0.15}`), and that dict form is impossible under
    Ollama's strict structured output (see PositionShift). Field named
    `shifts`, not the doc's `delta`, because `delta` is already the name of
    the scalar *inside* PositionShift — `decision.delta[0].delta` would read
    as nothing at all, and one name per concept across dt=5/dt=6 means an
    analyst reads sparse position moves the same way regardless of decision
    type. Documented wire-vs-doc divergence, same register as Lot 3's
    `recalled`-not-`recall_triggered` call.

    `shifts`'s max_length=5 is a loose STRUCTURAL ceiling, exactly like
    PositioningDecision's — the real cap is `mandate.max_response_shifts` (3
    shipped), enforced in `llm_behavior_engine.validate_response_decision`
    together with `mandate.max_response_delta`. Deliberately the `mandate.*`
    bounds and never `campaign.*`: mid-term mandate drift and campaign-time
    strategy are different effects and must stay analytically separable
    (`MandateConfig`'s own docstring, v4 Lot 1).

    Two cross-field rules, both context-independent and therefore here
    rather than in the engine:
    - stance/shifts coherence, §3.6.5's own enum definitions: `3=silence`
      means "aucun ajustement" (empty shifts required) and `1=concession`
      means "ajuste sa position" (non-empty required); `2=defiance`
      ("maintient OU accentue") and `4=counter_mobilization` accept both.
      Same shape and same home as VoteCastDecision's blank/ranking rule.
    - stance/motif coherence, per `ResponseMotif`'s own construction
      (301/302/303 each ground a CONCESSION; 307/308/309 exist precisely
      because defiance, silence and counter-mobilization each need their
      own signal). Same reasoning as `CoalitionDecision`'s action/motif
      rule below: the alternative pairing describes a different decision
      than the one recorded, silently corrupting the motif distribution
      §3.7 exists to produce.

    What is deliberately NOT validated: whether a concession's shifts
    actually move toward the perceived discontent. That is a behavioral
    prescription (§3.3) and a Lot 8 measurement, not an invariant."""

    model_config = ConfigDict(extra="forbid")

    cid: int = Field(..., ge=0, description="citizen_id of the officeholder this decision belongs to.")
    shifts: list[PositionShift] = Field(..., max_length=5)
    stance: Literal[1, 2, 3, 4] = Field(
        ..., description="1=concession, 2=defiance, 3=silence, 4=counter_mobilization (§3.6.5) — voir Stance."
    )
    motif: Literal[301, 302, 303, 307, 308, 309] = Field(
        ..., description="Code court obligatoire (§3.7.2) — voir ResponseMotif."
    )

    @model_validator(mode="after")
    def _check_no_duplicate_dimensions(self) -> ResponseDecision:
        dimensions = [shift.dimension for shift in self.shifts]
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("shifts must not target the same dimension twice")
        return self

    @model_validator(mode="after")
    def _check_stance_coherence(self) -> ResponseDecision:
        if self.stance == 1 and self.motif not in (301, 302, 303):
            raise ValueError("stance=1 (concession) requires motif 301, 302 or 303")
        if self.stance == 2 and self.motif != 307:
            raise ValueError("stance=2 (defiance) requires motif 307")
        if self.stance == 3 and self.motif != 308:
            raise ValueError("stance=3 (silence) requires motif 308")
        if self.stance == 4 and self.motif != 309:
            raise ValueError("stance=4 (counter_mobilization) requires motif 309")
        if self.stance == 1 and not self.shifts:
            raise ValueError("stance=1 (concession) requires at least one shift")
        if self.stance == 3 and self.shifts:
            raise ValueError("stance=3 (silence) requires an empty shifts list")
        return self


class ResponseBatch(BaseModel):
    """§3.6.0's batch envelope, specialized to representative_response — one
    decision per sitting officeholder (0-or-1 today: president only)."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[ResponseDecision] = Field(..., min_length=1)


RESPONSE_JSON_SCHEMA = ResponseBatch.model_json_schema()


class PressureDecision(BaseModel):
    """One consulted citizen's pressure choice, design doc §3.6.6 — the
    citizen-side symmetry of ResponseDecision. Wire shape is §3.6.6's own
    worked example exactly: cid, target, act, motif.

    `act` is Literal[0,1,2,3,4] — the FULL PressureAct enum, never a
    narrowed one: which acts are legal depends on config.pressure_menu (and,
    per citizen, on live petition state), neither of which a schema defined
    at import time can see. §3.6.6's hard constraint ("un act hors menu
    invalide le batch") is therefore enforced in
    llm_behavior_engine.validate_pressure_decision, the same home as every
    other context-dependent bound in this project.

    No `petition_id`: Lot 1's single-open-petition-per-target simplification
    (petition.concurrent_allowed is TRANCHÉ false) exists precisely so act=1
    needs no such field on the wire.

    NO cross-field model_validator, deliberately — a documented divergence
    from ResponseDecision/CoalitionDecision above, not an oversight.
    Through v6 Lot 1, PressureMotif had exactly three members ({301, 304,
    305}: 302 excluded permanently by §7bis.9f, 303 belongs to
    ResponseMotif), and they partitioned act perfectly (304 grounds act=0,
    305 grounds act=4, 301 the only code left for act in {1,2,3}). v6 Lot 3
    wires in the fourth, 306 FOLLOWING_NEIGHBORS (reserved by v6 Lot 1,
    §5) — deliberately NOT partition-preserving: it is a second, genuinely
    informative code available for act in {1,2,3} alongside 301 (was this
    citizen driven by their own perceived mandate deviation, or by seeing
    their neighbors already act?), so motif is no longer a strict function
    of act. The conclusion is unchanged anyway: still no model_validator.
    The rejection-surface argument (a cross-field rule is the one
    constraint constrained decoding cannot enforce, and dt=10 has the
    largest batches and highest call count in the whole project, now with
    v6's own volume added on top) is, if anything, stronger. The intended
    pairing (306 should ground act in {1,2,3}, never 0 or 4) is stated in
    the system prompt as guidance only; the realized act x motif table
    stays a §10 measurement, not an invariant."""

    model_config = ConfigDict(extra="forbid")

    cid: int = Field(..., ge=0, description="citizen_id of the consulted citizen this decision belongs to.")
    target: int = Field(..., ge=0, description="citizen_id of the officeholder this action targets (§3.6.6).")
    act: Literal[0, 1, 2, 3, 4] = Field(
        ..., description="0=rien, 1=signer, 2=lancer, 3=mobiliser, 4=attendre (§3.7.1) — voir PressureAct."
    )
    motif: Literal[301, 304, 305, 306] = Field(
        ..., description="Code court obligatoire (§3.7.2) — voir PressureMotif."
    )


class PressureBatch(BaseModel):
    """§3.6.0's batch envelope, specialized to pressure_action — one decision
    per CONSULTED citizen (the awakening gate's cohort, §7bis.9d), never one
    per citizen in the population."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[PressureDecision] = Field(..., min_length=1)


PRESSURE_JSON_SCHEMA = PressureBatch.model_json_schema()


class ReactionDecision(BaseModel):
    """One citizen's reaction to a single exogenous event (v5 Lot 4, dt=8,
    §8) — scandal OR economic shock, never both in one call:
    decide_reaction_to_event takes exactly ONE event_type per call, and a
    tick where both fire makes two separate calls (run_polity_simulation.py
    _run_reaction_to_event). No §3.6.7 subsection exists anywhere in the
    design doc (the numbering jumps 3.6.6 -> 3.6.9), so this wire shape is
    invented here — and deliberately narrower than an earlier roadmap-level
    sketch ({cid, event_type, target, ctx:{magnitude, self_gap, mandate_dev},
    salience_delta, motif}), corrected during this lot's own planning pass.

    event_type/target are dropped: both are call-level constants, identical
    for every citizen in one call (mirrors why ResponseDecision carries no
    `dt` field) — simple_rules.deterministic_reaction_to_event already
    treats event_type this way. ctx.self_gap/ctx.mandate_dev are dropped
    too: both are officeholder-relative facts (accountability.self_gap/
    mandate_deviation both raise ValueError against a vacancy, and
    current_office_holders returns [] on one — there is no citizen to
    compute either from), yet dt=8 must run population-wide regardless of
    vacancy, and ECONOMIC_SHOCK's own target is ALWAYS null. See
    llm_behavior_engine.ReactionContext for what replaces them
    (event_salience, the one signal that needs no officeholder at all).

    ONE cross-field rule, context-independent and therefore schema-level
    (same home as ResponseDecision's stance/motif rule): salience_delta==0
    iff motif==403 (EVENT_PERSONALLY_IRRELEVANT) — the direct wire analogue
    of ReactionMotif's own construction (401/402 each ground a
    salience_delta>0 reaction to their own EventType; 403 grounds the
    salience_delta==0 branch). What this schema canNOT check (needs to know
    which event_type this call was for): whether `motif` is the CORRECT
    grounding code (401 during a SCANDAL call, 402 during an ECONOMIC_SHOCK
    call) — llm_behavior_engine.validate_reaction_decision's job, the same
    split PressureDecision's own menu-legality check already uses."""

    model_config = ConfigDict(extra="forbid")

    cid: int = Field(..., ge=0, description="citizen_id of the reacting citizen.")
    salience_delta: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Non-negative shift applied to event_salience (§8) — a loose structural "
            "ceiling only; the real cap is events.max_reaction_delta."
        ),
    )
    motif: Literal[401, 402, 403] = Field(
        ..., description="Code court obligatoire (§3.7.2) — voir ReactionMotif."
    )

    @model_validator(mode="after")
    def _check_irrelevance_coherence(self) -> ReactionDecision:
        if (self.salience_delta == 0.0) != (self.motif == 403):
            raise ValueError("salience_delta == 0 iff motif == 403 (EVENT_PERSONALLY_IRRELEVANT)")
        return self


class ReactionBatch(BaseModel):
    """§3.6.0's batch envelope, specialized to reaction_to_event — one
    decision per REACTING citizen, population-wide (§8): unlike
    PressureBatch's awakening-gated `consulted` cohort,
    decide_reaction_to_event is called once per firing event_type over the
    WHOLE citizen list."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[ReactionDecision] = Field(..., min_length=1)


REACTION_JSON_SCHEMA = ReactionBatch.model_json_schema()


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
