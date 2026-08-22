"""
Pydantic request schemas for the core simulation endpoints (/simulations/*),
served by FastAPI as of Phase 4.5.a.5.

Responses stay loosely typed (Dict) because these routes return deeply nested,
heterogeneous structures (full voter/candidate objects, utility matrices,
per-segment breakdowns) that aren't worth pinning. We type the request shape.

List defaults use `default_factory` (never `None`) so `model_dump()` always
carries a concrete list — this avoids the Pydantic-None pitfall where a worker's
`data.get("issues", DEFAULT)` would receive an explicit `None` instead of the
default. `extra="ignore"` mirrors the lenient `data.get(...)` parsing the Flask
routes used.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from api.engine.constants import DEFAULT_ISSUES

_DEFAULT_PARTIES = ["Green", "Conservative", "Liberal", "Independent"]
_DEFAULT_SEGMENTS = [
    "young_female", "old_male", "high_edu", "low_income", "urban", "rural",
]


class LegacySimulateRequest(BaseModel):
    """POST /simulations (legacy form-based simulation)."""
    model_config = ConfigDict(extra="ignore")

    formData: Dict[str, Any]


class SimulateVotersRequest(BaseModel):
    """POST /simulations/simulate_voters."""
    model_config = ConfigDict(extra="ignore")

    num_voters: int = 1000


class SimulateCandidatesRequest(BaseModel):
    """POST /simulations/simulate_candidates."""
    model_config = ConfigDict(extra="ignore")

    num_candidates: int = 4
    issues:  List[str] = Field(default_factory=lambda: list(DEFAULT_ISSUES))
    parties: List[str] = Field(default_factory=lambda: list(_DEFAULT_PARTIES))


class ClosestCandidateRequest(BaseModel):
    """POST /simulations/get_closest_candidate (2-D spatial assignment)."""
    model_config = ConfigDict(extra="ignore")

    voters:     List[Any] = Field(default_factory=list)
    candidates: List[Any] = Field(default_factory=list)


class SimulateUtilityRequest(BaseModel):
    """POST /simulations/simulate_utility."""
    model_config = ConfigDict(extra="ignore")

    voters:     List[Dict[str, Any]] = Field(default_factory=list)
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    issues:     List[str] = Field(default_factory=lambda: list(DEFAULT_ISSUES))


class CalculateUtilityRequest(BaseModel):
    """POST /simulations/calculate_utility (single voter × candidate)."""
    model_config = ConfigDict(extra="ignore")

    voter:     Dict[str, Any] = Field(default_factory=dict)
    candidate: Dict[str, Any] = Field(default_factory=dict)
    issues:    List[str] = Field(default_factory=lambda: list(DEFAULT_ISSUES))


class UtilityMatrixRequest(BaseModel):
    """POST /simulations/get_utility_matrix."""
    model_config = ConfigDict(extra="ignore")

    voters:     List[Dict[str, Any]] = Field(default_factory=list)
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    issues:     List[str] = Field(default_factory=lambda: list(DEFAULT_ISSUES))


class VoterSegmentsRequest(BaseModel):
    """POST /simulations/get_voter_segments."""
    model_config = ConfigDict(extra="ignore")

    voters:     List[Dict[str, Any]] = Field(default_factory=list)
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    issues:     List[str] = Field(default_factory=lambda: list(DEFAULT_ISSUES))
    segments:   List[str] = Field(default_factory=lambda: list(_DEFAULT_SEGMENTS))


class WhatIfRequest(BaseModel):
    """POST /simulations/what-if (vary one parameter, compare methods)."""
    model_config = ConfigDict(extra="ignore")

    base:           Dict[str, Any] = Field(default_factory=dict)
    variant_param:  str = "num_voters"
    variant_values: List[Any] = Field(default_factory=list)


class CampaignRequest(BaseModel):
    """POST /simulations/campaign (day-by-day campaign simulation)."""
    model_config = ConfigDict(extra="ignore")

    num_candidates: int = 4
    num_voters:     int = 500
    num_days:       int = 30
    method:         str = "plurality"
    events:         List[Dict[str, Any]] = Field(default_factory=list)
    seed:           Optional[int] = None


# ── simulation_compare (Phase 4.5.a.7) ──────────────────────────────────────
# Responses stay Dict (passthrough). `candidates` is a union of name strings and
# {name,x,y,…} dicts depending on the tab, so we keep it List[Any] + extra=ignore.

_DEFAULT_CANDIDATES = ["Alice", "Bob", "Charlie"]


class CompareMethodsRequest(BaseModel):
    """POST /simulations/compare."""
    model_config = ConfigDict(extra="ignore")

    num_voters:            int = 500
    ideology_distribution: str = "random"
    candidates:            List[Any] = Field(default_factory=lambda: list(_DEFAULT_CANDIDATES))
    blank_vote:            bool = False
    blank_rule:            str = "symbolic"
    information_model:     Dict[str, Any] = Field(default_factory=dict)


class StrategicImpactRequest(BaseModel):
    """POST /simulations/strategic-impact."""
    model_config = ConfigDict(extra="ignore")

    num_voters:            int = 500
    ideology_distribution: str = "random"
    candidates:            List[Any] = Field(default_factory=lambda: list(_DEFAULT_CANDIDATES))
    strategic_percentages: List[Any] = Field(default_factory=lambda: [0, 10, 20, 30, 40, 50])


class CondorcetMatrixRequest(BaseModel):
    """POST /simulations/condorcet-matrix."""
    model_config = ConfigDict(extra="ignore")

    num_voters:            int = 500
    ideology_distribution: str = "random"
    candidates:            List[Any] = Field(default_factory=lambda: list(_DEFAULT_CANDIDATES))


class SensitivityRequest(BaseModel):
    """POST /simulations/sensitivity."""
    model_config = ConfigDict(extra="ignore")

    base_config: Dict[str, Any] = Field(default_factory=dict)
    variable:    str = "ideology_distribution"
    values:      List[Any] = Field(default_factory=list)


class ArrowCriteriaRequest(BaseModel):
    """POST /simulations/arrow-criteria."""
    model_config = ConfigDict(extra="ignore")

    num_voters:            int = 300
    ideology_distribution: str = "random"
    candidates:            List[Any] = Field(default_factory=lambda: list(_DEFAULT_CANDIDATES))


class ScenarioRequest(BaseModel):
    """POST /simulations/scenario."""
    model_config = ConfigDict(extra="ignore")

    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    electorate: Dict[str, Any] = Field(default_factory=dict)
    blank_rule: str = "symbolic"
    methods:    Optional[List[str]] = None


class VoteStepsRequest(BaseModel):
    """POST /simulations/vote-steps."""
    model_config = ConfigDict(extra="ignore")

    method:     str = "plurality"
    num_voters: int = 100
    candidates: List[Any] = Field(default_factory=lambda: list(_DEFAULT_CANDIDATES))
    ideology:   str = "random"
    seed:       int = 42


class IdeologyMapRequest(BaseModel):
    """POST /simulations/ideology-map."""
    model_config = ConfigDict(extra="ignore")

    num_voters: int = 200
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    ideology:   str = "random"
    seed:       int = 42
    method_a:   str = "plurality"
    method_b:   str = "schulze"


# ── simulation_advanced (Phase 4.5.a.8) ─────────────────────────────────────

class BandwagonRequest(BaseModel):
    """POST /simulations/bandwagon."""
    model_config = ConfigDict(extra="ignore")

    num_voters:            int = 300
    num_rounds:            int = 5
    influence_strength:    float = 0.3
    ideology_distribution: str = "random"
    seed:                  Optional[int] = None
    candidates:            List[Any] = Field(default_factory=lambda: list(_DEFAULT_CANDIDATES))


class MonteCarloRequest(BaseModel):
    """POST /simulations/monte-carlo (synchronous aggregation variant)."""
    model_config = ConfigDict(extra="ignore")

    num_runs:              int = 100
    num_voters:            int = 150
    ideology_distribution: str = "random"
    candidates:            List[Any] = Field(default_factory=lambda: list(_DEFAULT_CANDIDATES))


class MultiwinnerRequest(BaseModel):
    """POST /simulations/multiwinner."""
    model_config = ConfigDict(extra="ignore")

    party_votes: Dict[str, Any] = Field(default_factory=dict)
    num_seats:   int = 10
    mode:        str = "proportional"


class RealElectionRequest(BaseModel):
    """POST /simulations/real-election."""
    model_config = ConfigDict(extra="ignore")

    election_name: str = ""
    num_voters:    int = 1000
    blank_vote:    bool = False
    blank_rule:    str = "symbolic"


class ConstitutionalScenarioRequest(BaseModel):
    """POST /simulations/constitutional-scenario."""
    model_config = ConfigDict(extra="ignore")

    initial_election: Dict[str, Any] = Field(default_factory=dict)
    scenario_type:    str = "new_election"
    params:           Dict[str, Any] = Field(default_factory=dict)


class BlankContagionRequest(BaseModel):
    """POST /simulations/blank-contagion."""
    model_config = ConfigDict(extra="ignore")

    num_voters:         int = 300
    initial_blank_rate: float = 0.10
    contagion_rate:     float = 0.30
    recovery_rate:      float = 0.15
    num_rounds:         int = 15
    network_type:       str = "random"
    seed:               Optional[int] = None


# ── Response models (Phase 6) ─────────────────────────────────────────────────
#
# Only the cleanly-shaped endpoints (those whose worker ends in an explicit
# `return {…}` literal) are typed here. Each carries `extra="allow"` so any
# unmodeled field still passes through untouched (cannot drop data / break the
# frontend), and value types stay loose (`Any` / `Dict[str, Any]` / `Optional`)
# so `model_validate` never raises on a heterogeneous payload. The remaining
# endpoints whose workers return an engine-helper dict directly (compare,
# condorcet-matrix, arrow-criteria, scenario, monte-carlo, multiwinner,
# bandwagon, real-election, constitutional-scenario, blank-contagion, campaign)
# stay on the loose Dict passthrough until their helper shapes are traced.


class LegacySimulateResponse(BaseModel):
    """POST /simulations (legacy). Conditional vote/ranked/score blocks +
    dynamic per-method winners ride through on `extra="allow"`."""
    model_config = ConfigDict(extra="allow")

    simulation_type:     str
    deprecation_warning: str
    metadata:            Dict[str, Any]


class SimulateVotersResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    voters: List[Dict[str, Any]]


class SimulateCandidatesResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success:    bool
    candidates: List[Dict[str, Any]]
    message:    str


class ClosestCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    result: Any


class SimulateUtilityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success:         bool
    utility_results: List[Dict[str, Any]]


class CalculateUtilityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool
    result:  Dict[str, Any]
    message: str


class UtilityMatrixResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool
    matrix:  Dict[str, Any]
    stats:   Dict[str, Any]
    message: str


class VoterSegmentsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success:  bool
    segments: Dict[str, Any]
    message:  str


class StrategicImpactResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    results: List[Dict[str, Any]]


class SensitivityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    variable: str
    values:   List[Any]
    results:  List[Dict[str, Any]]


class WhatIfResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    variant_param: str
    results:       List[Dict[str, Any]]


class IdeologyMapResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    voters:                  List[Dict[str, Any]]
    candidates:              List[Dict[str, Any]]
    winner_a:                Optional[str] = None
    winner_b:                Optional[str] = None
    method_a:                str
    method_b:                str
    condorcet_winner:        Optional[str] = None
    pct_better_off_with_a:   float
    pct_better_off_with_b:   float


class VoteStepsResponse(BaseModel):
    """POST /simulations/vote-steps. Shape is polymorphic by `method`
    (irv/borda/plurality/schulze/approval); only `method` is guaranteed."""
    model_config = ConfigDict(extra="allow")

    method: str


# ── Engine-helper-backed endpoints (Phase 6, batch 2) ─────────────────────────
#
# These workers return an engine helper's dict (compare_all_methods,
# get_condorcet_matrix, check_all_criteria, …). Top-level keys are confirmed
# from each helper's return literal; nested values stay `Dict[str, Any]`/`Any`
# and presence-uncertain keys are `Optional[...] = None` so `model_validate`
# never raises. `extra="allow"` carries any worker-added field (e.g. blank_pct).


class CompareMethodsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    methods:            Dict[str, Any]
    information_model:  Dict[str, Any]
    condorcet_winner:   Optional[str] = None


class CondorcetMatrixResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    candidates:       List[Any]
    matrix:           Any
    condorcet_winner: Optional[str] = None
    condorcet_cycles: Any = None


class ArrowCriteriaResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    methods: Dict[str, Any]
    summary: Dict[str, Any]


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    without_blank: Dict[str, Any]
    with_blank:    Dict[str, Any]


class MonteCarloResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    num_runs:                     int
    num_voters_per_run:           int
    config:                       Dict[str, Any]
    methods:                      Dict[str, Any]
    condorcet_winner_exists_rate: float
    inter_method_agreement:       Any = None


class MultiwinnerResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    comparison:              Dict[str, Any]
    dhondt:                  Optional[Dict[str, Any]] = None
    sainte_lague:            Optional[Dict[str, Any]] = None
    largest_remainder_hare:  Optional[Dict[str, Any]] = None
    largest_remainder_droop: Optional[Dict[str, Any]] = None
    stv:                     Optional[Dict[str, Any]] = None


class BandwagonResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    num_rounds:              int
    influence_strength:      Any = None
    rounds:                  List[Any]
    convergence_round:       Optional[int] = None
    amplification_by_method: Dict[str, Any]


class RealElectionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    election:            Any
    plurality_winner:    Optional[str] = None
    first_round_results: Any = None
    methods:             Dict[str, Any]
    methods_with_blank:  Optional[Dict[str, Any]] = None
    methods_with_blank_rule: Optional[Dict[str, Any]] = None
    divergences:         Any = None
    summary:             Any = None
    blank_vote_analysis: Any = None


class ConstitutionalScenarioResponse(BaseModel):
    """Polymorphic by scenario_type (new_election/provisional/dissolution);
    `scenario_type` + `conclusion` are common to every branch."""
    model_config = ConfigDict(extra="allow")

    scenario_type: str
    conclusion:    str


class BlankContagionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    rounds:             List[Any]
    blank_rate_by_round: List[Any]
    final_blank_rate:   float
    epidemic_threshold: Any = None
    reached_equilibrium: bool
    network_type:       str
    r0:                 Any = None


class CampaignEventResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    day:             int
    type:            str
    candidate:       int
    magnitude:       float
    measured_impact: float


class CampaignResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    days:         List[int]
    daily_leader: List[str]
    daily_scores: Dict[str, List[float]]
    events:       List[CampaignEventResult]
    final_winner: Optional[str] = None
    lead_changes: int
    candidates:   List[str]


# ── GET endpoints (Phase 6, batch 3) ──────────────────────────────────────────
# FastAPI validates the returned dict/list against `response_model` on the way
# out, so these keep their `_run_worker` dict return + query-param signature.


class ManipulabilityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    num_candidates: int
    num_voters:     int
    ideology:       str
    num_trials:     int
    results:        Any


class BlankHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    country:      str
    display_name: str
    note:         str
    series:       Any


class RealElectionSummary(BaseModel):
    """One item of GET /simulations/real-elections (a list)."""
    model_config = ConfigDict(extra="allow")

    key:     str
    name:    str
    year:    Any
    country: str
