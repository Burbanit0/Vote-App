"""
Pydantic schemas for /api/theory/* endpoints.

Phase 4 batch 1: arrow / iia-rate / plott-chaos / judgment-aggregation.

Responses ARE typed (unlike most perturbers in Phase 3) because the
theory endpoints have stable, well-defined output shapes that the
frontend pedagogical text depends on. Where a sub-object is deeply
heterogeneous (e.g. axiom counterexamples), we keep it as
`Dict[str, Any]` — strict request validation is still the main win.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── /arrow ──────────────────────────────────────────────────────────────────

class ArrowRequest(BaseModel):
    """Per-method Arrow axiom violation analysis."""
    model_config = ConfigDict(extra="forbid")

    method: str = Field("plurality",
                        description="One of plurality | borda | irv | schulze | "
                                    "condorcet | approval | majority_judgment | "
                                    "kemeny_young | minimax | star_voting | two_round.")
    seed:   int = Field(42, ge=0)


class ArrowViolation(BaseModel):
    """One axiom: was it violated, and if so what's the counterexample."""
    violated:       bool
    counterexample: Optional[Dict[str, Any]] = None


class ArrowViolations(BaseModel):
    iia:               ArrowViolation
    pareto:            ArrowViolation
    transitivity:      ArrowViolation
    non_dictatorship:  ArrowViolation


class ArrowResponse(BaseModel):
    method:        str
    violations:    ArrowViolations
    arrow_summary: str
    tradeoff_type: str = Field(
        description="majority_focus | utility_focus | condorcet_focus.",
    )


# ── /iia-rate ───────────────────────────────────────────────────────────────

class IIARateRequest(BaseModel):
    """Empirical IIA violation rate vs number of candidates."""
    model_config = ConfigDict(extra="forbid")

    method:         str = Field("plurality")
    max_candidates: int = Field(8, ge=2, le=8)
    num_trials:     int = Field(100, ge=20, le=500)
    seed:           int = Field(42, ge=0)


class IIARatePoint(BaseModel):
    n_candidates:   int
    violation_rate: float = Field(..., ge=0.0, le=1.0)


class IIARateResponse(BaseModel):
    method: str
    curve:  List[IIARatePoint]


# ── /plott-chaos ────────────────────────────────────────────────────────────

class PlottChaosRequest(BaseModel):
    """Plott's Chaos Theorem in 2-D policy space."""
    model_config = ConfigDict(extra="forbid")

    num_voters:     int   = Field(5, ge=3, le=21)
    num_dimensions: int   = Field(2, ge=1, le=2)
    seed:           int   = Field(42, ge=0)
    target_policy:  List[float] = Field(default_factory=lambda: [0.6, 0.6],
                                        min_length=1, max_length=2)
    start_policy:   List[float] = Field(default_factory=lambda: [-0.6, -0.6],
                                        min_length=1, max_length=2)
    max_steps:      int   = Field(15, ge=1, le=30)


class TopCycle(BaseModel):
    size:   int
    center: List[float]


class ChaosPath(BaseModel):
    from_:     List[float] = Field(..., alias="from")
    to:        List[float]
    steps:     List[List[float]]
    num_steps: int

    model_config = ConfigDict(populate_by_name=True)


class AlternativePath(BaseModel):
    to:    List[float]
    steps: List[List[float]]


class PlottChaosResponse(BaseModel):
    condorcet_winner_exists: bool
    top_cycle:               TopCycle
    chaos_path:              ChaosPath
    alternative_path:        AlternativePath
    voter_ideal_points:      List[List[float]]
    pedagogical_note:        str


# ── /judgment-aggregation ──────────────────────────────────────────────────

class JudgmentAggregationRequest(BaseModel):
    """Discursive dilemma (List & Pettit 2002)."""
    model_config = ConfigDict(extra="forbid")

    num_voters: int = Field(12, ge=1, le=100)
    seed:       int = Field(42, ge=0)
    scenario:   str = Field("legal",
                            description="One of legal | budget | climate.")


class JAProposition(BaseModel):
    text:            str
    type:            str = Field(description="'premise' | 'conclusion'.")
    id:              str
    yes_pct:         float = Field(..., ge=0.0, le=1.0)
    collective_vote: bool


class JAIncoherence(BaseModel):
    premises:   List[str]
    conclusion: str
    problem:    str


class JAResolutionMethods(BaseModel):
    premise_based:    Dict[str, Any] = Field(default_factory=dict)
    conclusion_based: Dict[str, Any] = Field(default_factory=dict)


class JudgmentAggregationResponse(BaseModel):
    scenario:               str
    scenario_name:          str
    propositions:           List[JAProposition]
    collective_coherent:    bool
    incoherences:           List[JAIncoherence]
    voter_coherence_rate:   float = Field(..., ge=0.0, le=1.0)
    paradox_severity:       float = Field(..., ge=0.0, le=1.0)
    resolution_methods:     JAResolutionMethods
    pedagogical_note:       str


# ── /agenda-manipulation ────────────────────────────────────────────────────

class AgendaManipulationRequest(BaseModel):
    """McKelvey-style agenda manipulation under binary elimination."""
    model_config = ConfigDict(extra="forbid")

    alternatives:    List[str] = Field(default_factory=lambda: ["Alice", "Bob", "Carol"],
                                       min_length=2, max_length=6)
    num_voters:      int = Field(21, ge=3, le=101)
    seed:            int = Field(42, ge=0)
    target_outcome:  Optional[str] = Field(None,
                                           description="Outcome the agenda-setter wants. "
                                                       "Falls back to first alternative.")
    constraint_type: str = Field("binary_elimination",
                                 description="Currently only binary_elimination is supported.")


class OptimalAgenda(BaseModel):
    for_target:  List[str]
    neutral:     List[str]
    worst_case:  List[str]


class AgendaManipulationResponse(BaseModel):
    pairwise_matrix:     Dict[str, Dict[str, float]]
    condorcet_winner:    Optional[str] = None
    all_outcomes:        Dict[str, Any]
    achievable_outcomes: List[str]
    optimal_agenda:      OptimalAgenda
    manipulation_power:  float = Field(..., ge=0.0, le=1.0)
    pedagogical_note:    str


# ── /apportionment ──────────────────────────────────────────────────────────

class ApportionmentParty(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name:  str = Field(..., min_length=1, max_length=32)
    votes: int = Field(..., ge=0)


class ApportionmentRequest(BaseModel):
    """Compare apportionment methods + Balinski-Young paradoxes."""
    model_config = ConfigDict(extra="forbid")

    parties:        List[ApportionmentParty] = Field(..., min_length=1, max_length=10)
    num_seats:      int = Field(10, ge=2, le=1000)
    methods:        Optional[List[str]] = Field(None,
                                                description="Defaults to all 5 methods.")
    find_paradoxes: bool = Field(True,
                                 description="Run alabama/population/quota paradox checks "
                                             "(costlier).")


class ApportionmentMethodResult(BaseModel):
    seats:              Dict[str, int]
    quota_violation:    bool
    alabama_paradox:    bool
    population_paradox: bool
    new_state_paradox:  bool
    favors:             str
    description:        str


class ApportionmentResponse(BaseModel):
    results:                Dict[str, ApportionmentMethodResult]
    balinski_young_summary: str
    impossible_to_avoid:    List[str]
    pedagogical_note:       str


# ── /sen-paradox ────────────────────────────────────────────────────────────

class SenParadoxRequest(BaseModel):
    """Sen's Impossibility of a Paretian Liberal (always uses 2 voters)."""
    model_config = ConfigDict(extra="forbid")

    num_voters:        int = Field(2, ge=2, le=2,
                                   description="Fixed at 2 for the canonical formulation.")
    seed:              int = Field(42, ge=0)
    rights_definition: str = Field("liberal")


class SenExample(BaseModel):
    name:                str
    voters_preferences:  List[List[str]]
    private_spheres:     Dict[str, List[str]]
    liberal_outcome:     str
    pareto_outcome:      str
    conflict:            bool
    explanation:         str


class SenResolutionOption(BaseModel):
    name:     str
    outcome:  str
    cost:     str
    theorist: str


class SenParadoxResponse(BaseModel):
    paradox_exists:     bool
    paradox_examples:   List[SenExample]
    paradox_frequency:  float = Field(..., ge=0.0, le=1.0)
    alternative_names:  Dict[str, str]
    resolution_options: List[SenResolutionOption]
    real_world_analogy: str
    pedagogical_note:   str


# ── /manipulation-analysis ─────────────────────────────────────────────────

class ManipulationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str   = Field(..., min_length=1, max_length=32)
    x:    float = Field(..., ge=-1.0, le=1.0)
    y:    float = Field(..., ge=-1.0, le=1.0)


class ManipulationAnalysisRequest(BaseModel):
    """Gibbard-Satterthwaite manipulator identification."""
    model_config = ConfigDict(extra="forbid")

    candidates:               List[ManipulationCandidate] = Field(
        default_factory=lambda: [
            ManipulationCandidate(name="Alice", x=-0.5, y=-0.2),
            ManipulationCandidate(name="Bob",   x= 0.5, y= 0.2),
            ManipulationCandidate(name="Carol", x= 0.0, y= 0.1),
        ],
        min_length=2, max_length=6,
    )
    num_voters:               int = Field(30, ge=10, le=100)
    ideology:                 str = Field("random")
    seed:                     int = Field(42, ge=0)
    method:                   str = Field("plurality")
    manipulation_strategies:  List[str] = Field(
        default_factory=lambda: ["compromising", "burying", "pushover", "truncating"],
    )


class Manipulator(BaseModel):
    voter_id:         int
    voter_ideology:   List[float]
    sincere_vote:     List[str]
    strategic_vote:   List[str]
    strategy_type:    str
    sincere_result:   Optional[str]
    strategic_result: Optional[str]
    utility_gain:     float


class KeyManipulator(BaseModel):
    voter_id: int
    strategy: str
    gain:     float


class ManipulationAnalysisResponse(BaseModel):
    sincere_winner:     Optional[str]
    manipulable:        bool
    manipulation_count: int
    manipulators:       List[Manipulator]
    strategy_breakdown: Dict[str, int]
    key_manipulator:    Optional[KeyManipulator] = None
    pedagogical_note:   str


# ── /majority-tyranny ──────────────────────────────────────────────────────

class MajorityTyrannyRequest(BaseModel):
    """Tocqueville's tyranny of the majority across decision rules."""
    model_config = ConfigDict(extra="forbid")

    num_voters:         int   = Field(100, ge=10, le=500)
    majority_pct:       float = Field(0.60, ge=0.51, le=0.95)
    minority_intensity: float = Field(3.0, ge=1.0, le=10.0)
    num_decisions:      int   = Field(50, ge=10, le=200)
    seed:               int   = Field(42, ge=0)
    decision_rules:     Optional[List[str]] = Field(None,
                                                    description="Defaults to all 6 rules.")


class MajorityTyrannyRuleResult(BaseModel):
    minority_win_rate:     float
    minority_satisfaction: float
    majority_satisfaction: float
    total_welfare:         float
    efficiency_loss:       float
    tyranny_index:         float


class TyrannyCurvePoint(BaseModel):
    majority_pct:    float
    tyranny_by_rule: Dict[str, float]


class MajorityTyrannyResponse(BaseModel):
    results:          Dict[str, MajorityTyrannyRuleResult]
    tyranny_curve:    List[TyrannyCurvePoint]
    best_protector:   str
    least_efficient:  str
    pedagogical_note: str


# ── /democratic-backsliding ────────────────────────────────────────────────

class BacksliddingCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str   = Field(..., min_length=1, max_length=64)
    x:    float = Field(..., ge=-1.0, le=1.0)
    y:    float = Field(0.0,  ge=-1.0, le=1.0)


class Guardrails(BaseModel):
    model_config = ConfigDict(extra="forbid")
    constitutional_court:   bool = Field(False)
    opposition_media:       bool = Field(False)
    international_pressure: bool = Field(False)
    supermajority_required: bool = Field(False)


class DemocraticBacksliddingRequest(BaseModel):
    """Path toward autocracy across successive elections."""
    model_config = ConfigDict(extra="forbid")

    candidates:             List[BacksliddingCandidate] = Field(
        default_factory=lambda: [
            BacksliddingCandidate(name="Incumbent",  x=0.2),
            BacksliddingCandidate(name="Opposition", x=-0.4),
        ],
        min_length=2, max_length=6,
    )
    num_voters:             int   = Field(100, ge=20, le=1000)
    ideology:               str   = Field("random")
    seed:                   int   = Field(42, ge=0)
    num_elections:          int   = Field(8, ge=2, le=15)
    backsliding_method:     str   = Field("gerrymandering",
                                          description="gerrymandering | media_capture | voter_suppression.")
    backsliding_intensity:  float = Field(0.5, ge=0.0, le=1.0)
    guardrails:             Optional[Guardrails] = Field(default_factory=Guardrails)


class BacksliddingElection(BaseModel):
    election_n:           int
    winner:               str
    vote_shares:          Dict[str, float]
    democratic_quality:   float
    advantages:           Dict[str, float]
    guardrails_triggered: List[str]
    point_of_no_return:   bool


class DemocraticBacksliddingResponse(BaseModel):
    elections:                List[BacksliddingElection]
    autocracy_reached:        bool
    autocracy_at_election:    Optional[int] = None
    guardrails_effectiveness: Dict[str, float]
    tipping_points:           List[float]
    pedagogical_note:         str


# ── /intergenerational ─────────────────────────────────────────────────────

class IGDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name:                str   = Field(..., min_length=1, max_length=64)
    cost_present:        float = Field(..., ge=-1.0, le=1.0)
    benefit_future:      float = Field(..., ge=-1.0, le=1.0)
    time_horizon_years:  int   = Field(..., ge=1, le=50)


class IntergenerationalRequest(BaseModel):
    """How future-gen representation changes long-horizon decisions."""
    model_config = ConfigDict(extra="forbid")

    decisions:                       Optional[List[IGDecision]] = Field(
        None, max_length=8,
        description="Defaults to a 5-decision battery (retirement, "
                    "education, debt, insulation, sovereign-fund).",
    )
    num_voters:                      int   = Field(100, ge=20, le=1000)
    age_distribution:                Optional[List[float]] = Field(
        default_factory=lambda: [0.30, 0.45, 0.25],
        min_length=3, max_length=3,
        description="[young, adult, senior] fractions; renormalized server-side.",
    )
    seed:                            int   = Field(42, ge=0)
    future_generations_mechanism:    str   = Field("none",
                                                   description="none | proxy | age_weighted | veto.")


class IGDecisionResult(BaseModel):
    decision_name: str
    by_mechanism:  Dict[str, Dict[str, Any]]


class IntergenerationalResponse(BaseModel):
    decisions_results:    List[IGDecisionResult]
    mechanism_comparison: Dict[str, Dict[str, float]]
    pedagogical_note:     str


# ── /epistocracy ──────────────────────────────────────────────────────────

class EpistCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str   = Field(..., min_length=1, max_length=64)
    x:    float = Field(..., ge=-1.0, le=1.0)
    y:    float = Field(0.0,  ge=-1.0, le=1.0)


class CompetenceParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mean:        float = Field(0.55, ge=0.1, le=0.99)
    std:         float = Field(0.15, ge=0.01, le=0.40)
    expert_pct:  float = Field(0.10, ge=0.0, le=0.50)
    caplan_bias: bool  = Field(True)


class EpistocracyRequest(BaseModel):
    """Epistocratic voting vs standard democracy (Caplan / Brennan)."""
    model_config = ConfigDict(extra="forbid")

    candidates:                      List[EpistCandidate] = Field(
        default_factory=lambda: [
            EpistCandidate(name="A", x=-0.5),
            EpistCandidate(name="B", x= 0.0),
            EpistCandidate(name="C", x= 0.5),
        ],
        min_length=2, max_length=6,
    )
    num_voters:                      int = Field(100, ge=10, le=1000)
    seed:                            int = Field(42, ge=0)
    voter_competence_distribution:   str = Field("uniform",
                                                 description="uniform | bimodal | expert_minority.")
    weighting_scheme:                str = Field("equal",
                                                 description="Currently always reports all 4 schemes "
                                                             "(equal/competence_weighted/epistocratic/lottery).")
    epistocracy_threshold:           float = Field(0.7, ge=0.1, le=0.99)
    competence_params:               Optional[CompetenceParams] = Field(default_factory=CompetenceParams)


class EpistocracySchemeResult(BaseModel):
    winner:             str
    bayesian_regret:    float
    correct_choice_pct: float
    participates_pct:   float


class VoterCompetenceStats(BaseModel):
    mean:         float
    biased_mean:  float
    expert_count: int


class DemocracyVsExpert(BaseModel):
    democracy_regret:  float
    expert_regret:     float
    omniscient_regret: float


class EpistocracyResponse(BaseModel):
    voter_competence_stats: VoterCompetenceStats
    results:                Dict[str, EpistocracySchemeResult]
    democracy_vs_expert:    DemocracyVsExpert
    condorcet_threshold:    float
    pedagogical_note:       str
