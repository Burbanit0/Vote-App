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
from .scenarios import (
    ScenarioCreateRequest,
    ScenarioDetail,
    ScenarioSummary,
)
from .theory import (
    AgendaManipulationRequest,
    AgendaManipulationResponse,
    ApportionmentRequest,
    ApportionmentResponse,
    ArrowRequest,
    ArrowResponse,
    AssumptionTestingRequest,
    AssumptionTestingResponse,
    CollectiveWillRequest,
    CollectiveWillResponse,
    DemocraticBacksliddingRequest,
    DemocraticBacksliddingResponse,
    EpistocracyRequest,
    EpistocracyResponse,
    IdentityVotingRequest,
    IdentityVotingResponse,
    IIARateRequest,
    IIARateResponse,
    IntergenerationalRequest,
    IntergenerationalResponse,
    JudgmentAggregationRequest,
    JudgmentAggregationResponse,
    MajorityTyrannyRequest,
    MajorityTyrannyResponse,
    ManipulationAnalysisRequest,
    ManipulationAnalysisResponse,
    PlottChaosRequest,
    PlottChaosResponse,
    SenParadoxRequest,
    SenParadoxResponse,
)
from .perturbers import (
    AdaptiveRequest,
    AffectivePolarizationRequest,
    BallotComplexityRequest,
    BehavioralBiasesRequest,
    CascadeRequest,
    ChoiceOverloadRequest,
    CompulsoryVotingRequest,
    ConvictionVotingRequest,
    DeliberationRequest,
    DemographicTurnoutRequest,
    DistrictsRequest,
    DivergenceRequest,
    ElectoralFatigueRequest,
    GerrymanderRequest,
    HistoricalReplayRequest,
    HotellingRequest,
    InterpretRequest,
    JuryRequest,
    LiquidDemocracyRequest,
    MultiwinnerCompareRequest,
    NotaRequest,
    PartyDynamicsRequest,
    PolarizationRequest,
    PowerIndicesRequest,
    PrimaryRequest,
    QuadraticFundingRequest,
    ShyVoterRequest,
    SimulatePipelineRequest,
    SortitionRequest,
    StvRequest,
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
    "AdaptiveRequest",
    "AffectivePolarizationRequest", "BallotComplexityRequest",
    "BehavioralBiasesRequest", "CascadeRequest",
    "ChoiceOverloadRequest", "CompulsoryVotingRequest",
    "ConvictionVotingRequest",
    "DeliberationRequest", "DemographicTurnoutRequest",
    "DistrictsRequest", "DivergenceRequest",
    "ElectoralFatigueRequest", "GerrymanderRequest",
    "HistoricalReplayRequest", "HotellingRequest",
    "InterpretRequest", "JuryRequest",
    "LiquidDemocracyRequest", "MultiwinnerCompareRequest",
    "NotaRequest", "PartyDynamicsRequest", "PolarizationRequest",
    "PowerIndicesRequest", "PrimaryRequest",
    "QuadraticFundingRequest",
    "ShyVoterRequest", "SimulatePipelineRequest",
    "SortitionRequest", "StvRequest",
    # scenarios CRUD (Phase 4.2)
    "ScenarioCreateRequest", "ScenarioDetail", "ScenarioSummary",
    # theory (Phase 4 complete, all 15 endpoints)
    "AgendaManipulationRequest", "AgendaManipulationResponse",
    "ApportionmentRequest", "ApportionmentResponse",
    "ArrowRequest", "ArrowResponse",
    "AssumptionTestingRequest", "AssumptionTestingResponse",
    "CollectiveWillRequest", "CollectiveWillResponse",
    "DemocraticBacksliddingRequest", "DemocraticBacksliddingResponse",
    "EpistocracyRequest", "EpistocracyResponse",
    "IdentityVotingRequest", "IdentityVotingResponse",
    "IIARateRequest", "IIARateResponse",
    "IntergenerationalRequest", "IntergenerationalResponse",
    "JudgmentAggregationRequest", "JudgmentAggregationResponse",
    "MajorityTyrannyRequest", "MajorityTyrannyResponse",
    "ManipulationAnalysisRequest", "ManipulationAnalysisResponse",
    "PlottChaosRequest", "PlottChaosResponse",
    "SenParadoxRequest", "SenParadoxResponse",
]
