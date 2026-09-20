"""
Pydantic schemas for the /simulations/* endpoints still served: vote-steps,
monte-carlo and manipulability.

List defaults use `default_factory` (never `None`) so `model_dump()` always
carries a concrete list — this avoids the Pydantic-None pitfall where a worker's
`data.get("issues", DEFAULT)` would receive an explicit `None` instead of the
default. `extra="ignore"` mirrors the lenient `data.get(...)` parsing the Flask
routes used.
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import UniqueLooseCandidates


# Shared request bounds. Ranges mirror api/schemas/election.py and
# api/schemas/perturbers.py (num_voters: ge=10, le=1000); NumRuns matches the
# cap previously enforced only inside _monte_carlo_worker (min(..., 500)).
NumVoters = Annotated[int, Field(ge=10, le=1000)]
NumRuns = Annotated[int, Field(ge=1, le=500)]

# ── simulation_compare (Phase 4.5.a.7) ──────────────────────────────────────
# Responses stay Dict (passthrough). `candidates` is a union of name strings and
# {name,x,y,…} dicts depending on the tab, so we keep it List[Any] + extra=ignore.

_DEFAULT_CANDIDATES = ("Alice", "Bob", "Charlie")


class VoteStepsRequest(BaseModel):
    """POST /simulations/vote-steps."""
    model_config = ConfigDict(extra="ignore")

    # The five branches the worker animates. The worker already rejected anything
    # else with a 400; declaring the Literal moves that to a 422 at the boundary,
    # matching the seven endpoints #611 converted and putting the list in the
    # OpenAPI contract instead of only in an error string.
    method:     Literal["plurality", "borda", "irv", "schulze", "approval"] = "plurality"
    num_voters: NumVoters = 100
    candidates: UniqueLooseCandidates = Field(
        default_factory=lambda: list(_DEFAULT_CANDIDATES), max_length=8)
    ideology:   str = "random"
    seed:       int = 42


# ── simulation_advanced (Phase 4.5.a.8) ─────────────────────────────────────



class MonteCarloRequest(BaseModel):
    """POST /simulations/monte-carlo (synchronous aggregation variant)."""
    model_config = ConfigDict(extra="ignore")

    num_runs:              NumRuns = 100
    num_voters:            NumVoters = 150
    ideology_distribution: str = "random"
    candidates:            UniqueLooseCandidates = Field(
        default_factory=lambda: list(_DEFAULT_CANDIDATES), max_length=8)


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


class MonteCarloResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    num_runs:                     int
    num_voters_per_run:           int
    config:                       Dict[str, Any]
    methods:                      Dict[str, Any]
    condorcet_winner_exists_rate: float
    inter_method_agreement:       Any = None


# ── GET endpoints (Phase 6, batch 3) ──────────────────────────────────────────
# FastAPI validates the returned dict against `response_model` on the way out,
# so a query-param route needs no request model of its own: it hands
# `run_passthrough` a plain payload and returns the dict.


class ManipulabilityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    num_candidates: int
    num_voters:     int
    ideology:       str
    num_trials:     int
    results:        Any


