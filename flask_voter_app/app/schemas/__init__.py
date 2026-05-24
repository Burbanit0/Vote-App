"""
app.schemas — Pydantic models that define the HTTP contract for every
endpoint that wants typed validation.

This is **Phase 1 of the strategic refactor** (see STRATEGIC_REFACTOR_PLAN.md):
the goal is to make the API self-describing so the frontend can generate
TypeScript types from a single source of truth, and so the backend rejects
malformed requests at the parser level instead of mid-compute.

Once a route uses one of these schemas, the `int(data.get(...))` defensive
litter in the route can go away.

Organisation:
  common.py    Shared primitives (Candidate, Voter, BlankVoteConfig, ...)
  election.py  Schemas for /api/election/* (simulate, combined-effects, ...)

Future phases will add `theory.py`, `auth.py`, `scenarios.py` and move
the rest of the routes to typed schemas.
"""
from .common import (
    BlankVoteConfig,
    CampaignConfig,
    CandidateSpec,
    ContagionConfig,
    InformationModelConfig,
    MethodResult,
    VoterSnapshot,
)
from .election import (
    AbstentionRequest,
    AbstentionResponse,
    CampaignSensitivityRequest,
    CampaignSensitivityResponse,
    CoalitionRequest,
    CoalitionResponse,
    CombinedEffectsRequest,
    CombinedEffectsResponse,
    SimulateRequest,
    SimulateResponse,
)
from .perturbers import (
    BallotComplexityRequest,
    ElectoralFatigueRequest,
    NotaRequest,
    ShyVoterRequest,
)

__all__ = [
    # common
    "BlankVoteConfig", "CampaignConfig", "CandidateSpec",
    "ContagionConfig", "InformationModelConfig", "MethodResult",
    "VoterSnapshot",
    # election
    "AbstentionRequest", "AbstentionResponse",
    "CampaignSensitivityRequest", "CampaignSensitivityResponse",
    "CoalitionRequest", "CoalitionResponse",
    "CombinedEffectsRequest", "CombinedEffectsResponse",
    "SimulateRequest", "SimulateResponse",
    # perturbers (request-only — see perturbers.py)
    "BallotComplexityRequest", "ElectoralFatigueRequest",
    "NotaRequest", "ShyVoterRequest",
]
