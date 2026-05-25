"""
Pydantic request schemas for the "Perturber" election endpoints
(nota / ballot-complexity / shy-voter / electoral-fatigue / cascade /
behavioral-biases / choice-overload / deliberation / ...).

Response schemas are intentionally NOT defined here. The v2 routes return
`Dict[str, Any]` and pass through the worker's output unchanged. The
reasons:

  1. Each perturber's response has 8-15 specific fields plus a curve
     and a method-comparison dict. Typing all of them strictly would
     mean 20 schemas, none of which would catch real bugs (the fields
     are computed values, not contract surfaces).
  2. The frontend already has TypeScript interfaces for these
     responses in the individual panel files — those types document
     the response shape sufficiently for the React side.
  3. Strict request validation (this module) catches the actually
     dangerous class of bug: client-side typos and out-of-range
     parameters that explode inside the worker.

When a panel migrates to TanStack Query (Phase 5 of the strategic
refactor), each response will get its own typed schema generated from
the worker's actual output shape.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import CandidateSpec


# ── /nota ────────────────────────────────────────────────────────────────────

class NotaRequest(BaseModel):
    """NOTA (None Of The Above) as an official ballot option."""
    model_config = ConfigDict(extra="forbid")

    candidates:     List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:     int   = Field(200, ge=50, le=500)
    ideology:       str   = Field("random")
    seed:           int   = Field(42, ge=0)
    nota_threshold: float = Field(0.3, ge=0.0, le=1.0,
                                  description="Minimum max-utility a voter needs for any candidate "
                                              "before they cast NOTA.")
    nota_rule:      str   = Field("invalidate",
                                  description="Constitutional response when NOTA wins: "
                                              "'invalidate' | 'runoff' | 'winner_take_all'.")
    method:         str   = Field("plurality",
                                  description="Primary method to display in the curve "
                                              "('plurality' | 'irv' | 'borda' | 'schulze' | ...).")


# ── /ballot-complexity ──────────────────────────────────────────────────────

class BallotComplexityRequest(BaseModel):
    """Ballot-complexity-driven null vote model."""
    model_config = ConfigDict(extra="forbid")

    candidates:           List[CandidateSpec] = Field(..., min_length=2, max_length=8)
    num_voters:           int   = Field(200, ge=50, le=500)
    ideology:             str   = Field("random")
    seed:                 int   = Field(42, ge=0)
    education_level:      float = Field(0.7, ge=0.0, le=1.0,
                                        description="Higher = lower null-vote rate.")
    first_time_voter_pct: float = Field(0.1, ge=0.0, le=1.0,
                                        description="Higher = higher null-vote rate.")
    methods_to_compare:   Optional[List[str]] = Field(
        None, max_length=8,
        description="Voting methods to compare. If None, uses the server default set.",
    )


# ── /shy-voter ──────────────────────────────────────────────────────────────

class ShyVoterRequest(BaseModel):
    """Bradley / Shy Tory effect: socially-sensitive candidates underpolled."""
    model_config = ConfigDict(extra="forbid")

    candidates:                 List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:                 int   = Field(300, ge=50, le=500)
    ideology:                   str   = Field("random")
    seed:                       int   = Field(42, ge=0)
    shy_candidate_idx:          int   = Field(0, ge=0, le=5,
                                              description="Index of the 'sensitive' candidate.")
    social_desirability_factor: float = Field(0.4, ge=0.0, le=1.0,
                                              description="Fraction of shy voters who lie in polls.")
    num_polls:                  int   = Field(10, ge=3, le=30)


# ── /electoral-fatigue ──────────────────────────────────────────────────────

class ElectoralFatigueRequest(BaseModel):
    """Turnout decay across repeated elections."""
    model_config = ConfigDict(extra="forbid")

    candidates:        List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:        int   = Field(200, ge=50, le=500)
    ideology:          str   = Field("random")
    seed:              int   = Field(42, ge=0)
    num_elections:     int   = Field(6, ge=1, le=12)
    fatigue_rate:      float = Field(0.07, ge=0.0, le=0.15,
                                     description="Per-election turnout drop (0.07 = 7 pp).")
    engaged_voter_pct: float = Field(0.2, ge=0.05, le=0.5,
                                     description="Share of always-voting partisans.")
    method:            str   = Field("plurality")


# ── /cascade ────────────────────────────────────────────────────────────────

class CascadeRequest(BaseModel):
    """Sequential voting with information cascades (Bikhchandani et al., 1992)."""
    model_config = ConfigDict(extra="forbid")

    candidates:         List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:         int   = Field(100, ge=20, le=500)
    ideology:           str   = Field("random")
    seed:               int   = Field(42, ge=0)
    cascade_strength:   float = Field(0.5, ge=0.0, le=1.0,
                                      description="Probability of following the public signal vs. sincere vote.")
    observation_window: int   = Field(10, ge=0, le=50,
                                      description="Number of recent votes each voter observes.")


# ── /behavioral-biases ──────────────────────────────────────────────────────

class BehavioralBiasesRequest(BaseModel):
    """Expressive + bullet voting + primacy effect on approval/plurality outcomes."""
    model_config = ConfigDict(extra="forbid")

    candidates:        List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:        int   = Field(200, ge=50, le=500)
    ideology:          str   = Field("random")
    seed:              int   = Field(42, ge=0)
    expressive_pct:    float = Field(0.2, ge=0.0, le=1.0,
                                     description="Fraction of voters who boost their ideal candidate ×10.")
    bullet_voting_pct: float = Field(0.2, ge=0.0, le=1.0,
                                     description="Approval voters who approve only their top choice.")
    primacy_bonus:     float = Field(0.02, ge=0.0, le=0.2,
                                     description="Vote bonus for the first-listed candidate.")
    candidate_order:   Optional[List[str]] = Field(None,
                                                   description="Optional ballot ordering for primacy effect.")
    method:            str   = Field("plurality")


# ── /choice-overload ────────────────────────────────────────────────────────

class HeuristicWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notoriety: float = Field(0.20, ge=0.0, le=1.0)
    primacy:   float = Field(0.10, ge=0.0, le=1.0)
    partisan:  float = Field(0.20, ge=0.0, le=1.0)


class ChoiceOverloadRequest(BaseModel):
    """Schwartz 2004 paradox: heuristics dominate beyond overload_threshold candidates."""
    model_config = ConfigDict(extra="forbid")

    num_voters:         int   = Field(150, ge=50, le=300)
    ideology:           str   = Field("random")
    seed:               int   = Field(42, ge=0)
    candidate_counts:   List[int] = Field(default_factory=lambda: [2, 3, 5, 7, 10],
                                          min_length=1, max_length=8,
                                          description="Candidate counts to compare. Each clamped to [2, 15].")
    overload_threshold: int   = Field(5, ge=2, le=12,
                                      description="Above this candidate count, voters switch to heuristics.")
    heuristic_weights:  Optional[HeuristicWeights] = Field(default_factory=HeuristicWeights)
    methods:            Optional[List[str]] = Field(None, max_length=5,
                                                    description="Voting methods to compare.")


# ── /deliberation ───────────────────────────────────────────────────────────

class DeliberationRequest(BaseModel):
    """DeGroot deliberation: voters update ideology toward a network-weighted mean."""
    model_config = ConfigDict(extra="forbid")

    candidates:          List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:          int   = Field(200, ge=50, le=500)
    ideology:            str   = Field("random")
    seed:                int   = Field(42, ge=0)
    deliberation_rounds: int   = Field(5, ge=1, le=10)
    influence_weight:    float = Field(0.3, ge=0.0, le=1.0,
                                       description="How strongly the group mean pulls each voter.")
    network_type:        str   = Field("random",
                                       description="'random' | 'echo_chamber' | 'bridge' | 'complete'.")
    group_size:          int   = Field(5, ge=3, le=20)
    argument_quality:    float = Field(0.5, ge=0.0, le=1.0,
                                       description="Higher = updates pull toward better-informed positions.")
    method:              str   = Field("plurality")


# ── /jury ───────────────────────────────────────────────────────────────────

class JuryRequest(BaseModel):
    """Condorcet Jury Theorem: P(majority correct) when each voter is right with p>0.5."""
    model_config = ConfigDict(extra="forbid")

    num_voters:           int   = Field(100, ge=10, le=500)
    num_options:          int   = Field(2, ge=2, le=5)
    correct_option_index: int   = Field(0, ge=0, le=4)
    voter_competence:     float = Field(0.7, ge=0.5, le=1.0,
                                        description="Per-voter probability of picking the correct option.")
    num_simulations:      int   = Field(200, ge=50, le=500)
    seed:                 int   = Field(42, ge=0)


# ── /hotelling ──────────────────────────────────────────────────────────────

class HotellingRequest(BaseModel):
    """Hotelling-Downs iterative best-response: candidates move to maximise votes."""
    model_config = ConfigDict(extra="forbid")

    candidates:     List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:     int   = Field(200, ge=50, le=500)
    ideology:       str   = Field("random")
    seed:           int   = Field(42, ge=0)
    method:         str   = Field("plurality")
    num_iterations: int   = Field(10, ge=1, le=20)
    step_size:      float = Field(0.05, ge=0.01, le=0.15,
                                  description="Per-step distance each candidate moves on the (x, y) grid.")


# ── /polarization ───────────────────────────────────────────────────────────

class PolarizationRequest(BaseModel):
    """Per-ideology distribution: Esteban-Ray index + method robustness scan."""
    model_config = ConfigDict(extra="forbid")

    candidates:      List[CandidateSpec] = Field(..., min_length=2, max_length=4)
    num_voters:      int   = Field(150, ge=50, le=300)
    seed:            int   = Field(42, ge=0)
    num_simulations: int   = Field(20, ge=5, le=50)
    ideology_range:  Optional[List[str]] = Field(
        None,
        description="Voter distributions to compare. Defaults to "
                    "[centrist, random, left_skewed, right_skewed, polarized].",
    )


# ── /sortition ──────────────────────────────────────────────────────────────

class StratificationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age_groups:      Optional[List[float]] = Field(default_factory=lambda: [0.25, 0.45, 0.30])
    gender_parity:   bool = Field(True)
    education_quota: bool = Field(True)


class SortitionRequest(BaseModel):
    """Compare elected vs sortition pure vs sortition stratified assembly selection."""
    model_config = ConfigDict(extra="forbid")

    candidates:           List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:           int   = Field(300, ge=50, le=500)
    assembly_size:        int   = Field(50, ge=5, le=300)
    ideology:             str   = Field("random")
    seed:                 int   = Field(42, ge=0)
    method:               str   = Field("plurality")
    num_simulations:      int   = Field(20, ge=5, le=100)
    realistic_candidates: bool  = Field(True)
    stratification:       Optional[StratificationConfig] = Field(default_factory=StratificationConfig)


# ── /affective-polarization ─────────────────────────────────────────────────

class AffectivePolarizationRequest(BaseModel):
    """Iyengar 2019: voters penalise candidates from the opposing political camp."""
    model_config = ConfigDict(extra="forbid")

    candidates:       List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:       int   = Field(200, ge=50, le=500)
    ideology:         str   = Field("random")
    seed:             int   = Field(42, ge=0)
    affect_hostility: float = Field(0.5, ge=0.0, le=1.0,
                                    description="0 = no hostility, 1 = maximum out-group penalty.")
    camp_threshold:   float = Field(0.1, ge=0.0, le=1.0,
                                    description="x-axis distance defining the in/out-group split.")
    num_simulations:  int   = Field(20, ge=5, le=50)


# ── /demographic-turnout ────────────────────────────────────────────────────

class DemographicProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age_distribution:        Optional[List[float]] = Field(default_factory=lambda: [0.25, 0.45, 0.30])
    turnout_by_age:          Optional[List[float]] = Field(default_factory=lambda: [0.55, 0.70, 0.85])
    ideology_by_age:         Optional[List[float]] = Field(default_factory=lambda: [-0.10, 0.00, 0.15])
    education_distribution:  Optional[List[float]] = None
    turnout_by_education:    Optional[List[float]] = None
    ideology_by_education:   Optional[List[float]] = None


class DemographicTurnoutRequest(BaseModel):
    """Distortion between full population and effective electorate via age × education turnout gaps."""
    model_config = ConfigDict(extra="forbid")

    candidates:           List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:           int   = Field(300, ge=50, le=500)
    seed:                 int   = Field(42, ge=0)
    method:               str   = Field("plurality")
    correct_for_turnout:  bool  = Field(True,
                                        description="Whether to apply the turnout-correction model.")
    demographic_profile:  Optional[DemographicProfile] = Field(default_factory=DemographicProfile)


# ── /compulsory-voting ──────────────────────────────────────────────────────

class CompulsoryVotingRequest(BaseModel):
    """Voluntary vs compulsory turnout: reluctant voters add null/random ballots."""
    model_config = ConfigDict(extra="forbid")

    candidates:           List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:           int   = Field(300, ge=50, le=500)
    ideology:             str   = Field("random")
    seed:                 int   = Field(42, ge=0)
    voluntary_turnout:    float = Field(0.65, ge=0.30, le=0.90)
    compulsory_turnout:   float = Field(0.92, ge=0.70, le=0.99)
    reluctant_null_rate:  float = Field(0.04, ge=0.0, le=0.20,
                                        description="Fraction of reluctant voters who cast null ballots.")
    reluctant_random_pct: float = Field(0.08, ge=0.0, le=1.0,
                                        description="Fraction who vote randomly rather than sincerely.")
    method:               str   = Field("plurality")


# ── /party-dynamics ─────────────────────────────────────────────────────────

class InitialParty(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name:        str   = Field(..., min_length=1, max_length=32)
    x:           float = Field(..., ge=-1.0, le=1.0)
    y:           float = Field(..., ge=-1.0, le=1.0)
    support_pct: float = Field(..., ge=0.0, le=1.0)


class PartyDynamicsRequest(BaseModel):
    """Multi-election party-system evolution (Duverger's Law)."""
    model_config = ConfigDict(extra="forbid")

    num_voters:            int   = Field(500, ge=100, le=1000)
    ideology:              str   = Field("random")
    seed:                  int   = Field(42, ge=0)
    num_elections:         int   = Field(10, ge=1, le=30)
    method:                str   = Field("plurality")
    survival_threshold:    float = Field(0.05, ge=0.01, le=0.20,
                                         description="Vote share below which a party is eliminated.")
    emergence_probability: float = Field(0.10, ge=0.0, le=1.0,
                                         description="Per-election chance of a new party emerging.")
    hotelling_adaptation:  float = Field(0.10, ge=0.0, le=1.0,
                                         description="How strongly parties move toward the centre over time.")
    tactical_voting:       bool  = Field(True,
                                         description="Apply tactical voting (squeezes small parties under FPTP).")
    initial_parties:       Optional[List[InitialParty]] = Field(
        None,
        description="Starting parties. If None, server uses a 7-party default spread across the spectrum.",
    )


# ── /simulate-pipeline ──────────────────────────────────────────────────────

class SimulatePipelineRequest(BaseModel):
    """Step-by-step pipeline animation for the simulation hub."""
    model_config = ConfigDict(extra="forbid")

    candidates:        List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:        int   = Field(150, ge=10, le=200)
    ideology:          str   = Field("random")
    seed:              int   = Field(42, ge=0)
    blank_vote:        Optional[dict] = Field(default_factory=dict)
    campaign:          Optional[dict] = Field(default_factory=dict)
    information_model: Optional[dict] = Field(default_factory=dict)


# ── /districts ──────────────────────────────────────────────────────────────

class DistrictsRequest(BaseModel):
    """N districts with locally shifted ideology, FPTP vs proportional."""
    model_config = ConfigDict(extra="forbid")

    candidates:                 List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_districts:              int   = Field(10, ge=5, le=50)
    voters_per_district:        int   = Field(100, ge=50, le=500)
    district_ideology_variance: float = Field(0.3, ge=0.0, le=1.0)
    seed:                       int   = Field(42, ge=0)


# ── /primary ────────────────────────────────────────────────────────────────

class PrimaryCandidateSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name:              str   = Field(..., min_length=1, max_length=32)
    ideology_position: float = Field(..., ge=-1.0, le=1.0)


class PartySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name:                 str   = Field(..., min_length=1, max_length=32)
    ideology_center:      float = Field(0.0, ge=-1.0, le=1.0)
    primary_voters_pct:   float = Field(0.3, ge=0.05, le=1.0)
    primary_candidates:   List[PrimaryCandidateSpec] = Field(..., min_length=2, max_length=8)


class PrimaryRequest(BaseModel):
    """Internal primaries + general election."""
    model_config = ConfigDict(extra="forbid")

    parties:            List[PartySpec] = Field(..., min_length=2, max_length=6)
    general_num_voters: int             = Field(500, ge=50, le=2000)
    general_ideology:   str             = Field("random")
    primary_method:     str             = Field("plurality")
    general_method:     str             = Field("plurality")
    seed:               int             = Field(42, ge=0)


# ── /stv ────────────────────────────────────────────────────────────────────

class StvRequest(BaseModel):
    """Single Transferable Vote + D'Hondt + FPTP comparison."""
    model_config = ConfigDict(extra="forbid")

    candidates: List[CandidateSpec] = Field(..., min_length=2, max_length=8)
    num_voters: int = Field(300, ge=50, le=1000)
    ideology:   str = Field("random")
    seed:       int = Field(42, ge=0)
    num_seats:  int = Field(5, ge=2, le=10)
    quota_type: str = Field("droop",
                            description="STV quota: 'droop' | 'hare' | 'imperiali'.")


# ── /adaptive ───────────────────────────────────────────────────────────────

class AdaptiveRequest(BaseModel):
    """N rounds of adaptive/tactical voting with poll feedback."""
    model_config = ConfigDict(extra="forbid")

    candidates:          List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:          int   = Field(300, ge=50, le=1000)
    ideology:            str   = Field("random")
    seed:                int   = Field(42, ge=0)
    num_rounds:          int   = Field(5, ge=1, le=10)
    method:              str   = Field("plurality")
    strategic_threshold: float = Field(0.15, ge=0.0, le=1.0,
                                       description="Polling level below which voters become tactical.")


# ── /historical-replay ──────────────────────────────────────────────────────

class CandidateOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str   = Field(..., min_length=1, max_length=64)
    x:    float = Field(..., ge=-1.0, le=1.0)
    y:    float = Field(..., ge=-1.0, le=1.0)


class HistoricalReplayRequest(BaseModel):
    """Day-by-day historical replay with optional candidate-position overrides."""
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field("france2002",
                             description="One of france2002 | usa1992 | germany2021 | condorcet_cycle")
    overrides:   Optional[List[CandidateOverride]] = Field(None)
    num_days:    int = Field(30, ge=1, le=60)
    seed:        int = Field(42, ge=0)


# ── /gerrymander ────────────────────────────────────────────────────────────

class DistrictBounds(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x_min: float = Field(..., ge=-1.0, le=1.0)
    x_max: float = Field(..., ge=-1.0, le=1.0)
    y_min: float = Field(..., ge=-1.0, le=1.0)
    y_max: float = Field(..., ge=-1.0, le=1.0)


class DistrictSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id:     int            = Field(..., ge=0)
    bounds: DistrictBounds


class GerrymanderRequest(BaseModel):
    """Voters assigned to user-drawn rectangular districts."""
    model_config = ConfigDict(extra="forbid")

    candidates: List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    districts:  List[DistrictSpec]  = Field(..., min_length=1, max_length=50)
    num_voters: int = Field(300, ge=50, le=1000)
    ideology:   str = Field("random")
    seed:       int = Field(42, ge=0)


# ── /multiwinner_compare ────────────────────────────────────────────────────

class MultiwinnerCompareRequest(BaseModel):
    """STV / D'Hondt / SPAV / Phragmén / FPTP on the same electorate."""
    model_config = ConfigDict(extra="forbid")

    candidates: List[CandidateSpec] = Field(..., min_length=2, max_length=8)
    num_voters: int = Field(200, ge=50, le=500)
    ideology:   str = Field("random")
    seed:       int = Field(42, ge=0)
    num_seats:  int = Field(5, ge=2, le=10)
