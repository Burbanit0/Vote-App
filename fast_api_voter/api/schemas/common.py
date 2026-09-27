"""
Shared primitives used by multiple election/theory schemas.

Each model documents the field with `Field(description=...)` so the
generated OpenAPI spec carries real explanations into the frontend types.
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Shape of a domain-level error response.

    `api.core.worker_dispatch.raise_for_status` lifts a domain worker's
    `(body, status_code)` tuple into `HTTPException(detail=body["error"])`
    when `status_code != 200` (400 and 503 keep their code, anything else
    becomes 500); FastAPI serializes that as `{"detail": "<message>"}`.
    `api/main.py`'s catch-all `Exception` handler uses the same shape for any
    uncaught error, so it's also the 500 contract for every route in the app,
    not just the ones that reach for it explicitly. Referenced via each
    router's `responses=` (Schemathesis, Lot 3 of the plan, found these
    codes were reachable but undocumented)."""
    model_config = ConfigDict(extra="forbid")

    detail: str = Field(..., description="Human-readable error message.")


class CandidateSpec(BaseModel):
    """A single candidate placed at a 2D ideological position on [-1, 1]²."""
    model_config = ConfigDict(extra="forbid")

    name: str   = Field(..., min_length=1, max_length=64,
                        description="Candidate display name.")
    x:    float = Field(..., ge=-1.0, le=1.0,
                        description="Economy axis. -1 = far left, +1 = far right.")
    y:    float = Field(..., ge=-1.0, le=1.0,
                        description="Social axis. -1 = liberal, +1 = conservative.")


def reject_duplicate_candidate_names(candidates: List[Any]) -> List[Any]:
    """Two candidates sharing a name is rejected at the boundary.

    Every worker tallies into a `{name: count}` dict, so duplicates silently
    collapse into one key and the other candidate's votes are discarded — the
    same hazard `election.py`'s `_reject_duplicate_names` already documents for
    party lists. `/simulations/vote-steps` was worse than lossy: its Schulze
    branch builds a pairwise dict over distinct names and `combinations()` then
    hands it the pair ('Alice', 'Alice'), raising KeyError as a 500 while the
    other four rules on the same endpoint answered 200.

    Accepts the loose shapes the simulation endpoints take: a bare name string,
    a dict, or a spec model.
    """
    return reject_duplicate_names(candidates, "candidate")


def candidate_name(spec: Any) -> str:
    """The name out of any of the three shapes a spec arrives in: a bare string,
    a dict, or a model."""
    if isinstance(spec, str):
        return spec
    return str(spec.get("name", "") if isinstance(spec, dict) else getattr(spec, "name", ""))


def reject_duplicate_names(specs: List[Any], noun: str) -> List[Any]:
    """`specs` with every name distinct, or a ValueError naming the duplicate."""
    seen: set[str] = set()
    for spec in specs:
        name = candidate_name(spec)
        if name in seen:
            raise ValueError(f"Duplicate {noun} name: {name!r}")
        seen.add(name)
    return specs


#: `List[CandidateSpec]` that also rejects duplicate names. Same field
#: constraints as before apply on top (`Field(..., min_length=2, max_length=8)`).
UniqueCandidates = Annotated[List[CandidateSpec], AfterValidator(reject_duplicate_candidate_names)]

#: For the two simulation endpoints whose `candidates` accept name strings too.
UniqueLooseCandidates = Annotated[List[Any], AfterValidator(reject_duplicate_candidate_names)]


class ContagionConfig(BaseModel):
    """SIS-style blank-vote contagion parameters."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool  = Field(False, description="Whether contagion is applied.")
    beta:    float = Field(0.15, ge=0.0, le=1.0,
                           description="Infection rate β (probability of converting per neighbour).")
    gamma:   float = Field(0.10, ge=0.0, le=1.0,
                           description="Recovery rate γ.")
    network: str   = Field("random",
                           description="Network topology: 'random' | 'watts_strogatz' | 'block'.")


class BlankVoteConfig(BaseModel):
    """Constitutional blank-vote rule + optional contagion."""
    model_config = ConfigDict(extra="forbid")

    enabled:   bool             = Field(False, description="Apply the constitutional rule to the winner.")
    rule:      str              = Field("symbolic",
                                        description="'symbolic' | 'competitive' | 'threshold_30'.")
    # pydantic default_factory=<Model> / omitted-default arg: basedpyright has
    # no pydantic.mypy-equivalent plugin, false positive (see
    # PLAN_SOLIDITE_TECHNIQUE.md Lot 14.5)
    contagion: ContagionConfig  = Field(default_factory=ContagionConfig)  # pyright: ignore[reportArgumentType]


class CampaignConfig(BaseModel):
    """Polling-bandwagon dynamics over a few days."""
    model_config = ConfigDict(extra="forbid")

    enabled:        bool  = Field(False, description="Apply campaign dynamics to true utilities.")
    num_days:       int   = Field(30, ge=7, le=60, description="Campaign length in days.")
    polling_effect: float = Field(0.3, ge=0.0, le=1.0,
                                  description="0 = ignore polls, 1 = ballots follow polls.")


class InformationModelConfig(BaseModel):
    """Media bias × voter information level adjustment of perceived utilities."""
    model_config = ConfigDict(extra="forbid")

    enabled:        bool                       = Field(False, description="Apply information asymmetry.")
    media_bias:     Dict[str, float]           = Field(default_factory=dict,
                                                       description="Per-candidate media bias [-1, +1].")
    voter_segments: Dict[str, float]           = Field(
        default_factory=lambda: {"low_info": 0.3, "medium_info": 0.5, "high_info": 0.2},
        description="Share of voters in each information bucket. Sums should be ~1.",
    )


# ── Result-side primitives ──────────────────────────────────────────────────

class MethodResult(BaseModel):
    """Result of a single voting method on one electorate."""
    model_config = ConfigDict(extra="allow")  # allow method-specific extras (mj_scores, ev_distribution, ...)

    winner:               Optional[str]   = Field(None, description="Method winner.")
    bayesian_regret:      Optional[float] = Field(None, description="Lower = better welfare.")
    majority_satisfaction: Optional[float] = Field(None, description="Share of voters satisfied (0..1).")
    condorcet_consistent: Optional[bool]  = Field(None, description="Did the method elect the Condorcet winner?")
    winner_with_blank:    Optional[str]   = Field(None,
                                                  description="Winner after blank-vote rule (if enabled).")
    blank_triggered:      Optional[bool]  = Field(None,
                                                  description="Did the blank-vote rule fire?")


class CandidateSnapshot(BaseModel):
    """Candidate as returned in /simulate (with derived party label)."""
    model_config = ConfigDict(extra="forbid")

    name:  str
    x:     float
    y:     float
    party: str


class VoterSnapshot(BaseModel):
    """One voter row in the ideology map."""
    model_config = ConfigDict(extra="forbid")

    id:                     int
    x:                      float
    y:                      float
    blank_threshold_final:  float


# The statuses every worker-backed route can return, for its `responses=`.
# 400 is one representative 4xx (`raise_for_status` passes through any 4xx a
# worker returns); 503 is worker_dispatch's timeout; 500 is main.py's
# catch-all. Five routers each carried their own copy of this dict, and
# simulations.py's copy still advertised a 404 from a worker deleted two PRs
# earlier — a route with a genuinely different status set spreads this one and
# adds to it.
WORKER_ERROR_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    400: {"model": ErrorDetail},
    500: {"model": ErrorDetail},
    503: {"model": ErrorDetail},
}
