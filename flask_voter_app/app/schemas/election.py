"""
Pydantic request/response models for /api/election/* endpoints.

Coverage in Phase 1:
  - /simulate              SimulateRequest / SimulateResponse
  - /combined-effects      CombinedEffectsRequest / CombinedEffectsResponse
  - /campaign-sensitivity  CampaignSensitivityRequest / CampaignSensitivityResponse
  - /abstention            AbstentionRequest / AbstentionResponse
  - /coalition             CoalitionRequest / CoalitionResponse

The remaining ~30 endpoints will be migrated incrementally during Phase 3
when the routes themselves move to FastAPI.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import (
    BlankVoteConfig,
    CampaignConfig,
    CandidateSnapshot,
    CandidateSpec,
    InformationModelConfig,
    MethodResult,
    VoterSnapshot,
)


# ── /simulate ───────────────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    """POST /api/election/simulate — full pipeline run."""
    model_config = ConfigDict(extra="forbid")

    candidates: List[CandidateSpec] = Field(
        ...,
        min_length=2,
        max_length=8,
        description="2 to 8 candidates. Beyond that, Kemeny-Young falls back to KwikSort approximation.",
    )
    num_voters: int   = Field(300, ge=10, le=1000)
    ideology:   str   = Field("random",
                              description="Voter distribution: 'random' | 'centrist' | 'polarized' | 'left_skewed' | 'right_skewed'.")
    seed:       int   = Field(42, ge=0, description="PRNG seed for reproducibility.")

    blank_vote:        BlankVoteConfig         = Field(default_factory=BlankVoteConfig)
    information_model: InformationModelConfig  = Field(default_factory=InformationModelConfig)
    campaign:          CampaignConfig          = Field(default_factory=CampaignConfig)


class SimulateResponse(BaseModel):
    """Result of /simulate — keys read by LabCentralView, IdeologyMap, MethodMatrix."""
    model_config = ConfigDict(extra="forbid")

    config:                 Dict[str, Any]            = Field(..., description="Echo of the original request.")
    voters_snapshot:        List[VoterSnapshot]       = Field(...)
    candidates:             List[CandidateSnapshot]   = Field(...)
    methods:                Dict[str, MethodResult]   = Field(..., description="Keyed by method slug.")
    condorcet_winner:       Optional[str]             = Field(None)
    blank_rate:             float                     = Field(..., ge=0.0, le=1.0)
    campaign_trajectory:    Optional[Dict[str, Any]]  = Field(None)
    inter_method_agreement: float                     = Field(..., ge=0.0, le=1.0)
    condorcet_exists:       bool


# ── /combined-effects ───────────────────────────────────────────────────────

class CombinedEffectsRequest(BaseModel):
    """Same shape as SimulateRequest but with a tighter num_voters cap (2³=8 simulations)."""
    model_config = ConfigDict(extra="forbid")

    candidates: List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters: int = Field(150, ge=10, le=200)
    ideology:   str = Field("random")
    seed:       int = Field(42, ge=0)

    blank_vote:        BlankVoteConfig         = Field(default_factory=BlankVoteConfig)
    information_model: InformationModelConfig  = Field(default_factory=InformationModelConfig)
    campaign:          CampaignConfig          = Field(default_factory=CampaignConfig)


class CombinedEffectsCombination(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id:                       str
    blank:                    bool
    campaign:                 bool
    information_model:        bool
    plurality_winner:         Optional[str]
    condorcet_winner:         Optional[str]
    inter_method_agreement:   float
    winner_differs_from_base: bool


class CombinedEffectsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_winner:                Optional[str]
    combinations:               List[CombinedEffectsCombination]
    factor_deltas:              Dict[str, float] = Field(
        ...,
        description="Agreement delta per factor (in %). Negative = factor disrupts agreement.",
    )
    most_disruptive_factor:     str
    least_disruptive_factor:    str
    max_disruption_combination: str


# ── /campaign-sensitivity ───────────────────────────────────────────────────

class CampaignSensitivityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters: int = Field(150, ge=10, le=200)
    ideology:   str = Field("random")
    seed:       int = Field(42, ge=0)
    snapshot_days: List[Any] = Field(
        default_factory=lambda: [0, 7, 14, 21, 28, "final"],
        description="Days at which to snapshot — strings ('final') and ints are both accepted.",
    )

    blank_vote: BlankVoteConfig = Field(default_factory=BlankVoteConfig)
    campaign:   CampaignConfig  = Field(default_factory=CampaignConfig)


class CampaignSnapshot(BaseModel):
    """Tolerant of extra fields the worker emits per-snapshot (vote shares,
    method-specific scores, ...). Only the strictly-required fields are
    typed; the rest pass through unchanged."""
    model_config = ConfigDict(extra="allow")

    day:               Any                       = Field(..., description="Day index or 'final'.")
    methods:           Dict[str, MethodResult]   = Field(default_factory=dict)
    condorcet_winner:  Optional[str]             = None


class CampaignSensitivityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshots:           List[CampaignSnapshot]
    method_stability:    Dict[str, Dict[str, Any]] = Field(
        ..., description="Per-method: winner_changes count, final_winner, stability_score [0..1]."
    )
    most_stable_method:  Optional[str]
    least_stable_method: Optional[str]


# ── /abstention ─────────────────────────────────────────────────────────────

class AbstentionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: List[CandidateSpec] = Field(..., min_length=2, max_length=8)
    num_voters: int   = Field(200, ge=10, le=500)
    ideology:   str   = Field("random")
    seed:       int   = Field(42, ge=0)
    demobilization_factor: float = Field(0.5, ge=0.0, le=1.0,
                                         description="0 = no abstention, 1 = aggressive demobilisation.")
    poll_influence:        float = Field(0.8, ge=0.0, le=1.0,
                                         description="How much polls affect abstention probability.")
    num_rounds:            int   = Field(3, ge=1, le=10)


class AbstentionVoter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id:               int
    x:                float
    y:                float
    preferred:        str
    abstained:        bool
    prob_abstention:  float


class AbstentionRound(BaseModel):
    model_config = ConfigDict(extra="allow")

    round:            int
    turnout:          float
    vote_shares:      Dict[str, float]
    winner_fptp:      Optional[str]
    winner_condorcet: Optional[str]
    abstention_map:   List[AbstentionVoter]


class AbstentionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    rounds:          List[AbstentionRound]
    sincere_winner:  Optional[str]
    final_winner:    Optional[str]
    winner_changed:  bool
    turnout_by_camp: Dict[str, float]
    candidates:      List[Dict[str, Any]]
    winners_by_method: Optional[Dict[str, Optional[str]]] = None


# ── /coalition ──────────────────────────────────────────────────────────────

class CoalitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates:    List[CandidateSpec] = Field(..., min_length=2, max_length=8)
    num_voters:    int                 = Field(300, ge=10, le=1000)
    ideology:      str                 = Field("random")
    seed:          int                 = Field(42, ge=0)
    total_seats:   int                 = Field(100, ge=10, le=577)
    threshold_pct: float               = Field(0.05, ge=0.0, le=0.2,
                                                description="Electoral threshold (5 % default).")


class SeatAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: str
    seats:     int
    pct:       float


class Coalition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    members:       List[str]
    total_seats:   int
    has_majority:  bool


class CoalitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allocations:       List[SeatAllocation]
    majority_threshold: int
    formed_coalition:  Optional[Coalition]
    runner_up_coalition: Optional[Coalition] = None
