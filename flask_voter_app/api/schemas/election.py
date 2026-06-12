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

from typing import Any, Dict, List, Literal, Optional

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


# ── /profile-simulate (Lab reshape P1) ────────────────────────────────────────

class ProfileCandidateSpec(BaseModel):
    """A candidate/party for the profile engine. Adds an optional 3rd axis and a
    valence (off-ideology quality) term over the plain 2D CandidateSpec."""
    model_config = ConfigDict(extra="forbid")

    name:    str   = Field(..., min_length=1, max_length=64)
    x:       float = Field(0.0, ge=-1.0, le=1.0, description="Axis 1 position.")
    y:       float = Field(0.0, ge=-1.0, le=1.0, description="Axis 2 position.")
    z:       float = Field(0.0, ge=-1.0, le=1.0, description="Axis 3 position (dims=3).")
    valence: float = Field(0.0, ge=-1.0, le=1.0, description="Off-ideology quality bonus.")


class BallotConfig(BaseModel):
    """How voters may EXPRESS their preference (frontier FA-1) — half the design
    space, separate from the counting rule. Information is lost on purpose."""
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "full", "choose_one", "approve", "rank_full", "rank_truncated",
        "score", "grade", "cumulative",
    ] = Field("full")
    truncate_at: Optional[int] = Field(None, ge=1, le=8,
                                       description="Top-k for rank_truncated.")
    score_levels: int = Field(6, ge=2, le=10, description="Levels for score ballots.")


class ProfileSimulateRequest(BaseModel):
    """POST /api/v2/election/profile-simulate — the profile-as-interface core.

    Every assumption is an explicit knob: the preference source and its params, the
    dimensionality, valence, the voter behaviour, and the ballot. Nothing is smuggled in.
    """
    model_config = ConfigDict(extra="forbid")

    source: Literal["spatial", "impartial", "mallows", "urn", "handcrafted"] = Field("spatial")
    candidates: List[ProfileCandidateSpec] = Field(..., min_length=2, max_length=8)
    num_voters: int = Field(300, ge=10, le=1000)
    dims:       int = Field(2, ge=1, le=3)
    valence:    bool = Field(False)
    behavior: Literal["sincere", "strategic", "mixed"] = Field("sincere")
    source_params: Dict[str, float] = Field(
        default_factory=dict,
        description="Source knobs: Mallows {phi}, Pólya urn {alpha}.",
    )
    handcrafted_matrix: Optional[List[List[float]]] = Field(
        None, description="Rows = voters, cols = candidates (aligned), for source=handcrafted."
    )
    ballot: BallotConfig = Field(default_factory=BallotConfig)
    seed: int = Field(42, ge=0)


class ProfileSimulateResponse(BaseModel):
    """Per-method winners over the built profile + its 2D embedding + the
    paradox/cycle rate read-out."""
    model_config = ConfigDict(extra="forbid")

    methods:                Dict[str, MethodResult] = Field(..., description="Keyed by method slug.")
    condorcet_winner:       Optional[str]           = Field(None)
    inter_method_agreement: float                   = Field(..., ge=0.0, le=1.0)
    cycle_rate:             float                   = Field(..., ge=0.0, le=1.0,
                                                            description="Share of resampled profiles with no Condorcet winner.")
    candidate_names:        List[str]               = Field(...)
    display_points:         List[List[float]]       = Field(..., description="Per-voter 2D embedding for the map.")
    candidate_points:       Optional[List[List[float]]] = Field(None, description="Candidate 2D points (spatial source only).")
    num_voters:             int                     = Field(..., ge=1)
    ballot_type:            str                     = Field("full")
    ballot_expressiveness:  float                   = Field(..., ge=0.0, le=1.0,
                                                            description="Bits the ballot can carry (normalised convention).")
    ballot_cognitive_load:  float                   = Field(..., ge=0.0, le=1.0,
                                                            description="Decisions the ballot demands (normalised convention).")
    sample_ballot:          Dict[str, float]        = Field(..., description="Voter #0's projected ballot.")
    winner_flips:           List[str]               = Field(..., description="Methods whose winner differs from the full-information ballot.")
    incompatible_methods:   List[str]               = Field(..., description="Methods that cannot honestly run on this ballot (excluded).")


# ── /assembly (Lab reshape P3) ────────────────────────────────────────────────

class AssemblyPartySpec(BaseModel):
    """A party placed on the ideological plane (the shared electorate's points
    in parliament mode)."""
    model_config = ConfigDict(extra="forbid")

    name: str   = Field(..., min_length=1, max_length=64)
    x:    float = Field(0.0, ge=-1.0, le=1.0)
    y:    float = Field(0.0, ge=-1.0, le=1.0)


class AssemblyRequest(BaseModel):
    """POST /api/v2/election/assembly — votes → seats under PR / FPTP / MMP.

    FPTP draws one single-member district per seat as equal-population bands
    along the x axis (geography correlates with ideology). MMP allocates half
    the seats in districts and tops up proportionally (overhang kept).
    """
    model_config = ConfigDict(extra="forbid")

    parties: List[AssemblyPartySpec] = Field(..., min_length=2, max_length=8)
    num_voters: int = Field(400, ge=10, le=1000)
    ideology:   str = Field("random")
    seed:       int = Field(42, ge=0)
    structure: Literal["pr", "fptp", "mmp"] = Field("pr")
    seats:     int   = Field(100, ge=10, le=500)
    threshold: float = Field(0.05, ge=0.0, le=0.15,
                             description="National vote-share threshold (PR/MMP lists).")
    apportionment: Literal["dhondt", "sainte_lague"] = Field("dhondt")
    strategic_desertion: bool = Field(
        False,
        description="Duverger demo: voters iteratively desert non-viable parties "
                    "(FPTP: outside the district top-2; PR/MMP: below the threshold) "
                    "for their nearest viable party.",
    )


class AssemblyPartyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name:           str
    x:              float
    y:              float
    votes:          int
    vote_share:     float = Field(..., ge=0.0, le=1.0)
    seats:          int
    seat_share:     float = Field(..., ge=0.0, le=1.0)
    district_seats: int   = Field(0, description="District wins (MMP only; 0 otherwise).")
    excluded_by_threshold: bool


class AssemblyCoalition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parties: List[str]
    seats:   int
    span:    float = Field(..., description="Max pairwise ideological distance inside the coalition.")


class AssemblyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structure:        str
    assembly_size:    int = Field(..., description="Actual size (MMP overhang can exceed the nominal seats).")
    majority:         int
    threshold_waived: bool = Field(..., description="True if no party passed the threshold and it was waived.")
    parties:          List[AssemblyPartyResult]
    gallagher_index:          Optional[float] = Field(None)
    effective_parties_votes:  Optional[float] = Field(None)
    effective_parties_seats:  Optional[float] = Field(None)
    wasted_vote_share:        float = Field(..., ge=0.0, le=1.0)
    coalitions:               List[AssemblyCoalition] = Field(..., description="Minimal winning coalitions, most cohesive first.")


# ── /assembly-scorecard (Lab reshape P5) ──────────────────────────────────────

class AxisBand(BaseModel):
    """A scorecard number with its Monte-Carlo band (mean, p10, p90), all in [0,1]."""
    model_config = ConfigDict(extra="forbid")

    mean: float = Field(..., ge=0.0, le=1.0)
    lo:   float = Field(..., ge=0.0, le=1.0)
    hi:   float = Field(..., ge=0.0, le=1.0)


class AssemblyScorecardRequest(BaseModel):
    """POST /api/v2/election/assembly-scorecard — six axes × all three structures
    over `replications` re-rolled electorates. Axis orientations are stated in the
    endpoint docs; every number carries a band."""
    model_config = ConfigDict(extra="forbid")

    parties: List[AssemblyPartySpec] = Field(..., min_length=2, max_length=8)
    num_voters: int = Field(400, ge=10, le=1000)
    ideology:   str = Field("random")
    seed:       int = Field(42, ge=0)
    seats:     int   = Field(100, ge=10, le=500)
    threshold: float = Field(0.05, ge=0.0, le=0.15)
    apportionment: Literal["dhondt", "sainte_lague"] = Field("dhondt")
    strategic_desertion: bool = Field(False)
    replications: int = Field(24, ge=8, le=40)


class AssemblyScorecardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replications: int
    structures: Dict[str, Dict[str, AxisBand]] = Field(
        ..., description="structure (pr|fptp|mmp) → axis → band."
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

    candidates: List[CandidateSpec] = Field(..., min_length=2, max_length=8)
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

    candidates: List[CandidateSpec] = Field(..., min_length=2, max_length=8)
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
    num_voters: int   = Field(200, ge=10, le=1000)
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

    candidates:           List[CandidateSpec] = Field(..., min_length=2, max_length=8)
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


# ── /hotelling ────────────────────────────────────────────────────────────────

class HotellingCandPos(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    x:    float
    y:    float


class HotellingIteration(BaseModel):
    model_config = ConfigDict(extra="allow")

    step:                 int
    candidates:           List[HotellingCandPos]
    scores:               Dict[str, float]
    converged_candidates: List[str]


class HotellingVoter(BaseModel):
    model_config = ConfigDict(extra="allow")

    x: float
    y: float


class HotellingResponse(BaseModel):
    """Hotelling-Downs convergence: candidates chasing the median voter."""
    model_config = ConfigDict(extra="allow")

    iterations:       List[HotellingIteration]
    converged:        bool
    convergence_step: Optional[int] = None
    final_positions:  List[HotellingCandPos]
    equilibrium_type: str
    voters:           List[HotellingVoter]
    candidates:       List[str]
    method:           str


# ── /polarization ─────────────────────────────────────────────────────────────

class PolarizationResponse(BaseModel):
    """Effect of electorate polarization on method outcomes."""
    model_config = ConfigDict(extra="allow")

    results:      Any
    key_findings: Any


# ── /affective-polarization ───────────────────────────────────────────────────

class AffectivePolarizationResponse(BaseModel):
    """Sincere vs affect-driven (in-group/out-group) voting outcomes."""
    model_config = ConfigDict(extra="allow")

    sincere_results:     Dict[str, Any]
    affective_results:   Dict[str, Any]
    winner_changed:      bool
    condorcet_violation: bool
    sincere_cw:          Optional[str] = None
    affective_cw:        Optional[str] = None
    method_sensitivity:  Dict[str, Any]
    affect_curve:        List[Dict[str, Any]]
    candidate_camps:     Dict[str, Any]
    voters:              List[Dict[str, Any]]
    candidates:          List[Dict[str, Any]]
    pedagogical_note:    str


# ── /party-dynamics ───────────────────────────────────────────────────────────

class PartySnap(BaseModel):
    model_config = ConfigDict(extra="allow")

    name:     str
    x:        float
    y:        float
    vote_pct: float
    seats:    int
    survived: bool


class ElectionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    election_n:        int
    active_parties:    int
    parties:           List[PartySnap]
    effective_parties: float
    winner:            str
    new_entrants:      List[str]
    eliminated:        List[str]


class IdeologyDrift(BaseModel):
    model_config = ConfigDict(extra="allow")

    party:     str
    initial_x: float
    final_x:   float


class PartyDynamicsResponse(BaseModel):
    """Multi-election party system evolution (Duverger's law)."""
    model_config = ConfigDict(extra="allow")

    elections:               List[ElectionRecord]
    final_system:            str
    effective_parties_curve: List[float]
    duverger_confirmed:      bool
    convergence_speed:       Optional[int] = None
    ideology_drift:          List[IdeologyDrift]
    pedagogical_note:        str


# ── /districts ────────────────────────────────────────────────────────────────

class DistrictResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    id:              int
    ideology_center: float
    winner_fptp:     str
    vote_shares:     Dict[str, float]


class DistrictsResponse(BaseModel):
    """N single-member districts: FPTP parliament vs proportional."""
    model_config = ConfigDict(extra="allow")

    districts:                  List[DistrictResult]
    parliament_fptp:            Dict[str, int]
    parliament_proportional:    Dict[str, int]
    national_vote_share:        Dict[str, float]
    distortion:                 float
    condorcet_winner_national:  Optional[str] = None
    fptp_winner:                str
    proportional_winner:        str
    num_districts:              int


# ── /primary ──────────────────────────────────────────────────────────────────

class PrimaryResponse(BaseModel):
    """Internal party primaries followed by a general election."""
    model_config = ConfigDict(extra="allow")

    primaries:                Any
    general_ballot:           List[str]
    general_winner:           Optional[str] = None
    general_runner_up:        Optional[str] = None
    general_vote_shares:      Dict[str, Any]
    median_voter_distance:    Any
    without_primaries_winner: Optional[str] = None


# ── /stv ──────────────────────────────────────────────────────────────────────

class StvResponse(BaseModel):
    """STV vs D'Hondt vs FPTP multiwinner comparison."""
    model_config = ConfigDict(extra="allow")

    stv:                   Dict[str, Any]
    dhondt:                Dict[str, Any]
    fptp:                  Dict[str, Any]
    vote_shares:           Dict[str, float]
    num_seats:             int
    quota:                 Any
    quota_type:            str
    distortion_stv_dhondt: float
    distortion_stv_fptp:   float
    candidates:            List[str]


# ── /adaptive ─────────────────────────────────────────────────────────────────

class AdaptiveVoterSnap(BaseModel):
    model_config = ConfigDict(extra="allow")

    id:             int
    x:              float
    y:              float
    sincere_vote:   str
    effective_vote: str
    tactical:       bool


class AdaptiveRound(BaseModel):
    model_config = ConfigDict(extra="allow")

    round:                int
    vote_shares:          Dict[str, float]
    sincere_shares:       Dict[str, float]
    winner:               Optional[str] = None
    sincere_winner:       Optional[str] = None
    strategic_voters_pct: float
    voter_snapshot:       List[AdaptiveVoterSnap]


class AdaptiveCandPos(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    x:    float


class AdaptiveResponse(BaseModel):
    """Iterated adaptive (tactical) voting rounds until convergence."""
    model_config = ConfigDict(extra="allow")

    rounds:            List[AdaptiveRound]
    converged:         bool
    convergence_round: Optional[int] = None
    final_winner:      Optional[str] = None
    sincere_winner:    Optional[str] = None
    strategic_drift:   float
    candidates:        List[AdaptiveCandPos]


# ── /historical-replay ────────────────────────────────────────────────────────

class ReplayScenario(BaseModel):
    model_config = ConfigDict(extra="allow")

    id:          str
    name:        str
    real_winner: str


class ReplayCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    name:     str
    x:        float
    y:        float
    modified: bool


class ReplayDay(BaseModel):
    model_config = ConfigDict(extra="allow")

    day:              int
    vote_shares:      Dict[str, float]
    winner_fptp:      str
    winner_condorcet: Optional[str] = None
    winner_borda:     str


class ReplayFinal(BaseModel):
    model_config = ConfigDict(extra="allow")

    winner_fptp:         str
    winner_condorcet:    Optional[str] = None
    winner_borda:        str
    differs_from_real:   bool
    pedagogical_note:    str
    pedagogical_note_en: str


class HistoricalReplayResponse(BaseModel):
    """Brownian replay of a historical election day-by-day."""
    model_config = ConfigDict(extra="allow")

    scenario:   ReplayScenario
    candidates: List[ReplayCandidate]
    days:       List[ReplayDay]
    final:      ReplayFinal


# ── /gerrymander ──────────────────────────────────────────────────────────────

class GerrymanderResponse(BaseModel):
    """Editable-boundary districts: gerrymandered parliament vs proportional."""
    model_config = ConfigDict(extra="allow")

    districts:               List[Dict[str, Any]]
    voters:                  List[Dict[str, Any]]
    parliament_gerrymander:  Dict[str, Any]
    parliament_proportional: Dict[str, Any]
    national_vote_share:     Dict[str, Any]
    distortion:              float
    gerrymander_index:       float
    winner:                  Optional[str] = None
    candidates:              List[str]
    num_seats:               int


# ── /multiwinner-compare ──────────────────────────────────────────────────────

class MultiwinnerCompareResponse(BaseModel):
    """Several multiwinner methods scored against a proportional reference."""
    model_config = ConfigDict(extra="allow")

    methods:                Dict[str, Any]
    vote_shares:            Dict[str, float]
    proportional_reference: Dict[str, Any]
    num_seats:              int
    candidates:             List[str]
    best_method:            str
    worst_method:           str


# ── /divergence ───────────────────────────────────────────────────────────────

class DivergenceResponse(BaseModel):
    """Inter-method agreement with vs without the blank-vote rule."""
    model_config = ConfigDict(extra="allow")

    without_blank:       Dict[str, Any]
    with_blank:          Dict[str, Any]
    delta_agreement:     float
    methods_changed:     List[Any]
    pct_methods_changed: float
    blank_rule:          str


# ── /quadratic-funding ────────────────────────────────────────────────────────

class QuadraticFundingResponse(BaseModel):
    """Quadratic funding vs 1p1v/plutocracy with Gini inequality metrics."""
    model_config = ConfigDict(extra="allow")

    projects:             List[Dict[str, Any]]
    winner:               Optional[str] = None
    mechanism_comparison: Dict[str, Any]
    gini_coefficients:    Dict[str, Any]
    vote_shares:          Dict[str, float]
    matching_pool:        Any
    budget_per_voter:     Any
    pedagogical_note:     str


# ── /power-indices ────────────────────────────────────────────────────────────

class PowerIndicesResponse(BaseModel):
    """Banzhaf/Shapley-Shubik coalition power vs raw seat share."""
    model_config = ConfigDict(extra="allow")

    total_seats:        int
    majority_threshold: int
    parties:            Any
    viable_coalitions:  List[Any]
    power_surprises:    List[Any]
    pedagogical_note:   str


# ── /simulate-pipeline ────────────────────────────────────────────────────────

class SimulatePipelineResponse(BaseModel):
    """Step-by-step pipeline of model stages for animation."""
    model_config = ConfigDict(extra="allow")

    steps:      List[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
    num_steps:  int


# ── /interpret ────────────────────────────────────────────────────────────────

class InterpretResponse(BaseModel):
    """Deterministic textual interpretation of a simulation result."""
    model_config = ConfigDict(extra="allow")

    headline:           str
    condorcet_analysis: Any
    divergence_reason:  Any
    method_groups:      Any
    best_by_regret:     Any
    worst_by_regret:    Any
    blank_analysis:     Any
    pedagogical_note:   str
    key_facts:          Any
