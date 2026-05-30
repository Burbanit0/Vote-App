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

from api_v2.engine.constants import DEFAULT_ISSUES

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
