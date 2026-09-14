"""Typed journal events (S3.3): one frozen type per event_type, whose fields are
exactly that event's payload keys, and one registry every event-type set derives from.

Before this, a payload was a dict literal at its write site, and three modules kept
their own hand-grepped lists of event names -- run_digest's ALL_EVENT_TYPES,
viz_export's institutional set, indexer's presidential-election set -- each with a
docstring explaining which grep produced it and what the grep missed. A renamed key
or a new event could drift from all three silently; the golden references caught it
only for the two golden scenarios.

`payload()` produces the same dict the literal did, so journal bytes are unchanged:
- a field left at OMIT is absent from the payload, not null -- several keys exist only
  on one path (LLM provenance on pressure_action, `attempt` on a rerun election), and
  absent and null mean different things to a reader;
- an LlmProvenance field is flattened into its three keys.

`validate_event` checks a journal line against its type: known event_type, no key
missing, no key extra.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar


class _Omit:
    """Marks a payload key this event does not carry on this path."""

    def __repr__(self) -> str:
        return "OMIT"


OMIT: Any = _Omit()


@dataclass(frozen=True)
class LlmProvenance:
    """The three provenance keys LLM decision events carry since S0.3/S0.5."""

    llm_fallback: int
    retry_sampling_varied: int
    llm_call_id: str | None

    KEYS: ClassVar[tuple[str, ...]] = ("llm_fallback", "retry_sampling_varied", "llm_call_id")

    @classmethod
    def for_unit(
        cls, fallback: Mapping[int, bool], sampling_varied: Mapping[int, bool], call_ids: Mapping[int, str | None], unit: int,
    ) -> LlmProvenance:
        """From a decision outcome's per-unit maps (llm_fallback, retry_sampling_varied,
        llm_call_ids); a unit absent from a map is not a fallback, not a retry."""
        return cls(int(fallback.get(unit, False)), int(sampling_varied.get(unit, False)), call_ids.get(unit))


@dataclass(frozen=True, kw_only=True)
class Event:
    EVENT_TYPE: ClassVar[str]
    INSTITUTIONAL: ClassVar[bool] = False
    """An election, coalition, petition, recall or exogenous-shock event: the
    calendar-level story viz_export and the digest's timeline show."""
    PRESIDENT_ELECTION_OUTCOME: ClassVar[bool] = False
    LLM_DECISION: ClassVar[bool] = False
    """Written from a model decision (on the LLM path); carries codebook_version."""

    def payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if value is OMIT:
                continue
            if isinstance(value, LlmProvenance):
                payload.update(dataclasses.asdict(value))
            else:
                payload[field.name] = value
        return payload

    @classmethod
    def payload_keys(cls) -> tuple[frozenset[str], frozenset[str]]:
        """(keys always present, keys present only on some paths)."""
        required: set[str] = set()
        optional: set[str] = set()
        for field in dataclasses.fields(cls):
            keys = LlmProvenance.KEYS if field.name == "provenance" else (field.name,)
            (optional if field.default is OMIT else required).update(keys)
        return frozenset(required), frozenset(optional)


# ── candidacy, nomination, campaign ───────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class CandidacyDeclared(Event):
    EVENT_TYPE = "candidacy_declared"
    path: str
    party_id: int = OMIT  # absent on the rupture path


@dataclass(frozen=True, kw_only=True)
class CandidacyConsidered(Event):
    EVENT_TYPE = "candidacy_considered"
    LLM_DECISION = True
    outcome: int
    path: str
    provenance: LlmProvenance


@dataclass(frozen=True, kw_only=True)
class PartyNominationChoice(Event):
    EVENT_TYPE = "party_nomination_choice"
    LLM_DECISION = True
    party_id: int
    contenders: list[int]
    provenance: LlmProvenance


@dataclass(frozen=True, kw_only=True)
class NominationLost(Event):
    EVENT_TYPE = "nomination_lost"
    party_id: int


@dataclass(frozen=True, kw_only=True)
class CampaignPositioning(Event):
    EVENT_TYPE = "campaign_positioning"
    LLM_DECISION = True
    shifts: list[dict[str, Any]]
    provenance: LlmProvenance


@dataclass(frozen=True, kw_only=True)
class ClampedAtBound(Event):
    EVENT_TYPE = "clamped_at_bound"
    decision_event: str
    dimensions: list[int]


# ── presidential election ─────────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class VoteCast(Event):
    EVENT_TYPE = "vote_cast"
    LLM_DECISION = True
    blank: int
    ranking: list[int]
    provenance: LlmProvenance
    audit: int = OMIT  # 1 on an S4.1 audit ballot: asked of the model beside the utility vote, never counted


@dataclass(frozen=True, kw_only=True)
class ElectionInvalidated(Event):
    EVENT_TYPE = "election_invalidated"
    INSTITUTIONAL = True
    PRESIDENT_ELECTION_OUTCOME = True
    office: str  # Office value, e.g. "president"
    blank_share: float | None
    threshold: float
    attempt: int
    candidate_ids: list[int]
    barred_candidate_ids: list[int]
    next_attempt_tick: int


@dataclass(frozen=True, kw_only=True)
class Elected(Event):
    EVENT_TYPE = "elected"
    INSTITUTIONAL = True
    PRESIDENT_ELECTION_OUTCOME = True
    office: str  # Office value, e.g. "president"
    attempt: int = OMIT  # present when blank_vote_competitive
    forced: int = OMIT
    abstained: int = OMIT  # S4.1: voters who stayed home, present once any did


@dataclass(frozen=True, kw_only=True)
class ElectionNoWinner(Event):
    EVENT_TYPE = "election_no_winner"
    INSTITUTIONAL = True
    PRESIDENT_ELECTION_OUTCOME = True
    office: str  # Office value, e.g. "president"
    attempt: int = OMIT
    forced: int = OMIT
    reason: str = OMIT  # "no_candidates" when the field was empty
    abstained: int = OMIT


@dataclass(frozen=True, kw_only=True)
class MandatePledgeDeclared(Event):
    EVENT_TYPE = "mandate_pledge_declared"
    office: str  # Office value, e.g. "president"
    pledged_platform: list[float]
    mandates_served: int
    lame_duck: bool


@dataclass(frozen=True, kw_only=True)
class SnapElectionTriggered(Event):
    EVENT_TYPE = "snap_election_triggered"
    INSTITUTIONAL = True
    office: str  # Office value, e.g. "president"
    recalled_citizen_id: int | None
    next_attempt_tick: int


# ── legislative, coalition ────────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class LegislativeResult(Event):
    EVENT_TYPE = "legislative_result"
    INSTITUTIONAL = True
    seats: dict[int, int]
    votes: dict[int, float]
    blank_count: int


@dataclass(frozen=True, kw_only=True)
class CoalitionFormed(Event):
    EVENT_TYPE = "coalition_formed"
    INSTITUTIONAL = True
    coalition: list[int]
    seats: dict[int, int]
    rounds_used: int = OMIT  # LLM negotiation only


@dataclass(frozen=True, kw_only=True)
class CoalitionFailed(Event):
    EVENT_TYPE = "coalition_failed"
    INSTITUTIONAL = True
    coalition: None
    seats: dict[int, int]
    rounds_used: int = OMIT  # negotiated to a genuine no-majority
    aborted_at_round: int | None = OMIT  # cut short by an LLM failure
    rounds_completed: int = OMIT


@dataclass(frozen=True, kw_only=True)
class CoalitionDecision(Event):
    EVENT_TYPE = "coalition_decision"
    LLM_DECISION = True
    party_id: int
    action: int
    initiator: int | None
    round: int
    # No llm_fallback: a failed negotiation aborts the round instead of falling back.
    retry_sampling_varied: int
    llm_call_id: str | None


# ── exogenous events ──────────────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class ScandalOccurred(Event):
    EVENT_TYPE = "scandal_occurred"
    INSTITUTIONAL = True
    target: int | None


@dataclass(frozen=True, kw_only=True)
class EconomicShockTick(Event):
    EVENT_TYPE = "economic_shock_tick"
    INSTITUTIONAL = True
    x: float
    threshold: float


@dataclass(frozen=True, kw_only=True)
class ReactionToEvent(Event):
    EVENT_TYPE = "reaction_to_event"
    LLM_DECISION = True
    event_type: int
    target: int | None
    salience_delta: float
    magnitude: float = OMIT  # economic shocks only
    ctx: dict[str, Any] = OMIT  # LLM path only
    provenance: LlmProvenance = OMIT  # LLM path only


# ── accountability, pressure, petitions ───────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class RepresentativeResponse(Event):
    EVENT_TYPE = "representative_response"
    LLM_DECISION = True
    office: str  # Office value, e.g. "president"
    stance: int
    shifts: list[dict[str, Any]]
    ctx: dict[str, Any]
    unified_deviation: float | None
    provenance: LlmProvenance


@dataclass(frozen=True, kw_only=True)
class MandateDeviationRecorded(Event):
    EVENT_TYPE = "mandate_deviation_recorded"
    office: str  # Office value, e.g. "president"
    deviation: float | None
    unified_deviation: float | None


@dataclass(frozen=True, kw_only=True)
class PressureAction(Event):
    EVENT_TYPE = "pressure_action"
    LLM_DECISION = True
    target: int
    act: int
    ctx: dict[str, Any] = OMIT  # LLM path only
    provenance: LlmProvenance = OMIT  # LLM path only


@dataclass(frozen=True, kw_only=True)
class PetitionLaunched(Event):
    EVENT_TYPE = "petition_launched"
    INSTITUTIONAL = True
    target: int
    signatures: int
    signed_ratio: float
    expires_at_tick: int


@dataclass(frozen=True, kw_only=True)
class PetitionSigned(Event):
    EVENT_TYPE = "petition_signed"
    target: int
    signatures: int
    signed_ratio: float


# ── legitimacy, confidence, recall ────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class LegitimacyUpdated(Event):
    EVENT_TYPE = "legitimacy_updated"
    office: str  # Office value, e.g. "president"
    legitimacy: float
    mandate_strength: float
    ecart: float


@dataclass(frozen=True, kw_only=True)
class ConfidenceVoteTriggered(Event):
    EVENT_TYPE = "confidence_vote_triggered"
    INSTITUTIONAL = True
    office: str  # Office value, e.g. "president"
    opened_at_tick: int | None
    signatures: int
    signed_ratio: float


@dataclass(frozen=True, kw_only=True)
class ConfidenceVoteResult(Event):
    EVENT_TYPE = "confidence_vote_result"
    INSTITUTIONAL = True
    office: str  # Office value, e.g. "president"
    bf: int
    ballots: int
    keep: int
    keep_ratio: float
    retained: bool
    averted_recall: bool


@dataclass(frozen=True, kw_only=True)
class PetitionExpired(Event):
    EVENT_TYPE = "petition_expired"
    INSTITUTIONAL = True
    office: str  # Office value, e.g. "president"
    opened_at_tick: int | None
    signatures: int
    signed_ratio: float
    signature_threshold: float


@dataclass(frozen=True, kw_only=True)
class Recalled(Event):
    EVENT_TYPE = "recalled"
    INSTITUTIONAL = True
    office: str  # Office value, e.g. "president"
    legitimacy: float
    recall_floor: float
    trigger: str  # "legitimacy_floor" or "confidence_vote"


# ── sortition chamber ─────────────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class SortitionRotation(Event):
    EVENT_TYPE = "sortition_rotation"
    seated: list[int]
    vacated: list[int]
    pool_relaxed: int


@dataclass(frozen=True, kw_only=True)
class ChamberDeliberation(Event):
    EVENT_TYPE = "chamber_deliberation"
    LLM_DECISION = True
    shifts: list[dict[str, Any]]
    ctx: dict[str, Any]
    chamber_deviation: float | None
    motif_corrected: int
    provenance: LlmProvenance


# ── registry ──────────────────────────────────────────────────────────────

EVENT_CLASSES: tuple[type[Event], ...] = (
    CandidacyDeclared, CandidacyConsidered, PartyNominationChoice, NominationLost, CampaignPositioning,
    ClampedAtBound, VoteCast, ElectionInvalidated, Elected, ElectionNoWinner, MandatePledgeDeclared,
    SnapElectionTriggered, LegislativeResult, CoalitionFormed, CoalitionFailed, CoalitionDecision,
    ScandalOccurred, EconomicShockTick, ReactionToEvent, RepresentativeResponse, MandateDeviationRecorded,
    PressureAction, PetitionLaunched, PetitionSigned, LegitimacyUpdated, ConfidenceVoteTriggered,
    ConfidenceVoteResult, PetitionExpired, Recalled, SortitionRotation, ChamberDeliberation,
)

EVENT_TYPES: dict[str, type[Event]] = {cls.EVENT_TYPE: cls for cls in EVENT_CLASSES}
ALL_EVENT_TYPES: frozenset[str] = frozenset(EVENT_TYPES)
INSTITUTIONAL_EVENT_TYPES: frozenset[str] = frozenset(t for t, cls in EVENT_TYPES.items() if cls.INSTITUTIONAL)
PRESIDENT_ELECTION_OUTCOMES: frozenset[str] = frozenset(
    t for t, cls in EVENT_TYPES.items() if cls.PRESIDENT_ELECTION_OUTCOME
)
LLM_DECISION_EVENT_TYPES: frozenset[str] = frozenset(t for t, cls in EVENT_TYPES.items() if cls.LLM_DECISION)


def validate_event(event: Mapping[str, Any]) -> list[str]:
    """What is wrong with one parsed journal line against its registered type; empty
    when nothing is."""
    event_type = event.get("event_type")
    cls = EVENT_TYPES.get(str(event_type))
    if cls is None:
        return [f"unknown event_type {event_type!r}"]
    required, optional = cls.payload_keys()
    keys = set((event.get("payload") or {}).keys())
    problems = [f"{event_type}: missing payload key {key!r}" for key in sorted(required - keys)]
    problems += [f"{event_type}: unexpected payload key {key!r}" for key in sorted(keys - required - optional)]
    return problems
