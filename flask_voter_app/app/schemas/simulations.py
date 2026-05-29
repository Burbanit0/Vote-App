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

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from app.constants import DEFAULT_ISSUES

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
