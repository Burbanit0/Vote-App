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
    """Per-method D'Hondt seat allocation + greedy coalition formation."""
    model_config = ConfigDict(extra="forbid")

    candidates:           List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:           int   = Field(300, ge=10, le=1000)
    ideology:             str   = Field("random")
    seed:                 int   = Field(42, ge=0)
    total_seats:          int   = Field(100, ge=10, le=1000,
                                        description="Size of the parliament.")
    government_threshold: float = Field(0.5, ge=0.0, le=1.0,
                                        description="Share of seats needed to form a government.")


class CoalitionMethodResult(BaseModel):
    """Coalition analysis for one voting method."""
    model_config = ConfigDict(extra="allow")

    method:              str
    winner:              str
    seats:               Dict[str, int]
    vote_shares:         Dict[str, float]
    coalition_parties:   List[str]
    coalition_seats:     int
    coalition_spread:    float = Field(..., description="Ideological variance of coalition (0 = monolithic).")
    government_possible: bool


class CoalitionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    x:    float


class CoalitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    methods:                List[CoalitionMethodResult]
    candidates:             List[CoalitionCandidate]
    total_seats:            int
    seat_threshold:         int = Field(..., description="ceil(total_seats * government_threshold).")
    most_centrist_method:   Optional[str]
    most_divergent_method:  Optional[str]
    inter_method_agreement: float


# ── /jury ─────────────────────────────────────────────────────────────────────

class JuryMethodResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    accuracy:       float
    beats_majority: bool
    beats_theory:   bool


class JuryResponse(BaseModel):
    """Condorcet Jury Theorem — per-method accuracy + competence-curve scan."""
    model_config = ConfigDict(extra="allow")

    theoretical_accuracy: float
    methods:              Dict[str, JuryMethodResult]
    best_method:          str
    worst_method:         str
    voter_competence:     float
    num_voters:           int
    # Curve points carry dynamic per-method keys alongside competence/theoretical,
    # so a permissive float map is the right shape.
    competence_curve:     List[Dict[str, float]]
    pedagogical_note:     str
    pedagogical_note_en:  str


# ── /nota ─────────────────────────────────────────────────────────────────────

class NotaResponse(BaseModel):
    """None-Of-The-Above: validity + per-method comparison + threshold curve."""
    model_config = ConfigDict(extra="allow")

    nota_pct:          float
    election_valid:    bool
    winner:            Optional[str]
    nota_curve:        List[Dict[str, Any]]
    method_comparison: Dict[str, Any]
    pedagogical_note:  str
    nota_rule:         str
    nota_threshold:    float


# ── /cascade ──────────────────────────────────────────────────────────────────

class CascadeResponse(BaseModel):
    """Information cascade: sequential voting where later voters follow the herd."""
    model_config = ConfigDict(extra="allow")

    sincere_winner:         Optional[str]
    cascade_winner:         Optional[str]
    cascade_occurred:       bool
    vote_sequence:          List[Dict[str, Any]]
    cascade_start_at:       Optional[int]
    cascade_strength_curve: List[Dict[str, Any]]
    comparison_runs:        List[Dict[str, Any]]
    candidates:             List[str]


# ── /electoral-fatigue ────────────────────────────────────────────────────────

class ElectoralFatigueResponse(BaseModel):
    """Repeated elections: turnout decay + ideological drift of the electorate."""
    model_config = ConfigDict(extra="allow")

    elections:          List[Dict[str, Any]]
    winner_drift:       List[str]
    winner_changed_at:  Optional[int]
    ideology_drift:     float
    representation_gap: float
    full_mean_ideology: float
    pedagogical_note:   str


# ── /deliberation ─────────────────────────────────────────────────────────────

class DeliberationResponse(BaseModel):
    """Pre/post deliberation comparison under a social-influence network."""
    model_config = ConfigDict(extra="allow")

    pre_deliberation:    Dict[str, Any]
    post_deliberation:   Dict[str, Any]
    winner_changed:      bool
    deliberation_effect: Dict[str, Any]
    per_round:           List[Dict[str, Any]]
    network_effect:      str
    pedagogical_note:    str


# ── /ballot-complexity ────────────────────────────────────────────────────────

class BallotComplexityResponse(BaseModel):
    """Null-vote rate per method as ballot complexity (candidate count) grows."""
    model_config = ConfigDict(extra="allow")

    results:                List[Dict[str, Any]]
    candidate_count_curve:  List[Dict[str, Any]]
    most_inclusive_method:  Optional[str]
    least_inclusive_method: Optional[str]
    pedagogical_note:       str


# ── /shy-voter ────────────────────────────────────────────────────────────────

class ShyVoterResponse(BaseModel):
    """Shy-voter effect: poll vs real winner under social-desirability bias."""
    model_config = ConfigDict(extra="allow")

    real_winner:               Optional[str]
    poll_winner:               Optional[str]
    polls_wrong:               bool
    shy_candidate:             Optional[str]
    poll_results:              List[Dict[str, Any]]
    systematic_error:          Dict[str, float]
    real_results:              Dict[str, float]
    avg_poll_results:          Dict[str, float]
    social_desirability_curve: List[Dict[str, Any]]
    pedagogical_note:          str


# ── /behavioral-biases ────────────────────────────────────────────────────────

class BehavioralBiasesResponse(BaseModel):
    """Expressive + bullet + primacy biases vs sincere voting."""
    model_config = ConfigDict(extra="allow")

    sincere_winner:        Optional[str]
    biased_winner:         Optional[str]
    winner_changed:        bool
    vote_breakdown:        Dict[str, Any]
    method_sensitivity:    Dict[str, Any]
    bullet_immune_methods: List[str]
    pedagogical_note:      str


# ── /choice-overload ──────────────────────────────────────────────────────────

class ChoiceOverloadResponse(BaseModel):
    """Heuristic voting beyond an overload threshold of candidates."""
    model_config = ConfigDict(extra="allow")

    results_by_n:        List[Dict[str, Any]]
    regret_curve:        List[Dict[str, Any]]
    most_robust_method:  Optional[str]
    least_robust_method: Optional[str]
    overload_threshold:  int
    heuristic_weights:   Dict[str, float]
    pedagogical_note:    str


# ── /compulsory-voting ────────────────────────────────────────────────────────

class CompulsoryVotingResponse(BaseModel):
    """Voluntary vs compulsory turnout and the quality/representation trade-off."""
    model_config = ConfigDict(extra="allow")

    voluntary:                  Dict[str, Any]
    compulsory:                 Dict[str, Any]
    winner_changed:             bool
    representation_improvement: float
    quality_degradation:        float
    pedagogical_note:           str


# ── /conviction-voting ────────────────────────────────────────────────────────

class ConvictionVotingResponse(BaseModel):
    """Conviction voting: tokens × lock-multiplier vs plain token weight."""
    model_config = ConfigDict(extra="allow")

    conviction_winner: Optional[str]
    token_winner:      Optional[str]
    winner_changed:    bool
    proposals:         List[Dict[str, Any]]
    voter_scatter:     List[Dict[str, Any]]
    voter_stats:       Dict[str, Any]
    pedagogical_note:  str
    lock_options:      List[int]
    multipliers:       Dict[str, float]


# ── /liquid-democracy ─────────────────────────────────────────────────────────

class LiquidDemocracyResponse(BaseModel):
    """Transitive delegation: super-voters, cycles, and Gini of voting weight."""
    model_config = ConfigDict(extra="allow")

    weighted_results:   Dict[str, int]
    direct_voters:      int
    delegators:         int
    super_voters:       List[Dict[str, Any]]
    delegation_graph:   List[Dict[str, Any]]
    cycles_detected:    int
    cycle_voter_ids:    List[int]
    chain_stats:        Dict[str, Any]
    gini_curve:         List[Dict[str, Any]]
    comparison:         Dict[str, Any]
    gini_voting_weight: float
    pedagogical_note:   str


# ── /demographic-turnout ──────────────────────────────────────────────────────

class DemographicTurnoutResponse(BaseModel):
    """Distortion between full population and effective (turnout-weighted) electorate."""
    model_config = ConfigDict(extra="allow")

    biased_result:         Dict[str, Any]
    corrected_result:      Dict[str, Any]
    winner_changed:        bool
    representation_gap:    Dict[str, Any]
    demographic_breakdown: List[Dict[str, Any]]
    pedagogical_note:      str


# ── /sortition ────────────────────────────────────────────────────────────────

class SortitionResponse(BaseModel):
    """Elected vs sortition (pure / stratified) assembly representativeness."""
    model_config = ConfigDict(extra="allow")

    population:         Dict[str, Any]
    assemblies:         Dict[str, Any]
    variance:           Dict[str, Any]
    winner_by_method:   Dict[str, Any]
    consensus_possible: bool
    pedagogical_note:   str
