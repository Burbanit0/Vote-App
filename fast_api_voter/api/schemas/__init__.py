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
    ErrorDetail,
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
    AdaptiveResponse,
    AffectivePolarizationResponse,
    BallotComplexityResponse,
    BehavioralBiasesResponse,
    CascadeResponse,
    ChoiceOverloadResponse,
    CompulsoryVotingResponse,
    ConvictionVotingResponse,
    DeliberationResponse,
    DemographicTurnoutResponse,
    DistrictsResponse,
    DivergenceResponse,
    ElectoralFatigueResponse,
    GerrymanderResponse,
    HistoricalReplayResponse,
    HotellingResponse,
    InterpretResponse,
    JuryResponse,
    LiquidDemocracyResponse,
    MultiwinnerCompareResponse,
    NotaResponse,
    PartyDynamicsResponse,
    PolarizationResponse,
    PowerIndicesResponse,
    PrimaryResponse,
    ShyVoterResponse,
    SimulatePipelineResponse,
    SortitionResponse,
    StvResponse,
    SimulateRequest,
    SimulateResponse,
    ProfileSimulateRequest,
    ProfileSimulateResponse,
    AssemblyRequest,
    AssemblyResponse,
    AssemblyScorecardRequest,
    AssemblyScorecardResponse,
    IssueVotingRequest,
    IssueVotingResponse,
    StructuralFairnessRequest,
    StructuralFairnessResponse,
)
from .public_api import (
    PublicCompareRequest,
    PublicCompareResponse,
    PublicMethodsResponse,
    PublicRealElectionsResponse,
    PublicSimulateRequest,
    PublicSimulateResponse,
)
from .simulations import (
    ManipulabilityResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    VoteStepsRequest,
    VoteStepsResponse,
)
from .tech import (
    PolisWithCandidatesRequest,
    PolisWithCandidatesResponse,
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
    ShyVoterRequest,
    SimulatePipelineRequest,
    SortitionRequest,
    StvRequest,
)

__all__ = [
    # common
    "BlankVoteConfig", "CampaignConfig", "CandidateSpec",
    "ContagionConfig", "ErrorDetail", "InformationModelConfig", "MethodResult",
    "VoterSnapshot",
    # election
    "AbstentionRequest", "AbstentionResponse",
    "CampaignSensitivityRequest", "CampaignSensitivityResponse",
    "CoalitionRequest", "CoalitionResponse",
    "CombinedEffectsRequest", "CombinedEffectsResponse",
    "CascadeResponse", "DeliberationResponse", "ElectoralFatigueResponse",
    "JuryResponse", "NotaResponse",
    "BallotComplexityResponse", "BehavioralBiasesResponse", "ChoiceOverloadResponse",
    "CompulsoryVotingResponse", "ConvictionVotingResponse", "DemographicTurnoutResponse",
    "LiquidDemocracyResponse", "ShyVoterResponse", "SortitionResponse",
    "AdaptiveResponse", "AffectivePolarizationResponse", "DistrictsResponse",
    "DivergenceResponse", "GerrymanderResponse", "HistoricalReplayResponse",
    "HotellingResponse", "InterpretResponse", "MultiwinnerCompareResponse",
    "PartyDynamicsResponse", "PolarizationResponse", "PowerIndicesResponse",
    "PrimaryResponse", "SimulatePipelineResponse",
    "StvResponse",
    "SimulateRequest", "SimulateResponse",
    "ProfileSimulateRequest", "ProfileSimulateResponse",
    "AssemblyRequest", "AssemblyResponse",
    "AssemblyScorecardRequest", "AssemblyScorecardResponse",
    "IssueVotingRequest", "IssueVotingResponse",
    "StructuralFairnessRequest", "StructuralFairnessResponse",
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
    "ShyVoterRequest", "SimulatePipelineRequest",
    "SortitionRequest", "StvRequest",
    # export (Phase 4.5.a.2)
    # tech demos (Phase 4.5.a.3)
    "PolisWithCandidatesRequest",
    # tech demos response_models (Phase 6)
    "PolisWithCandidatesResponse",
    # public research API v1 (Phase 4.5.a.4)
    "PublicCompareRequest", "PublicSimulateRequest",
    # public research API v1 response_models (Phase 6)
    "PublicMethodsResponse", "PublicSimulateResponse",
    "PublicCompareResponse", "PublicRealElectionsResponse",
    # simulations base (Phase 4.5.a.5)
    # simulations base response_models (Phase 6)
    # simulations whatif + campaign (Phase 4.5.a.6)
    # simulation_compare (Phase 4.5.a.7)
    "VoteStepsRequest",
    # simulation_compare response_models (Phase 6)
    "VoteStepsResponse",
    # simulation_advanced + campaign response_models (Phase 6)
    "MonteCarloResponse",
    # simulations GET response_models (Phase 6)
    "ManipulabilityResponse",
    # simulation_advanced (Phase 4.5.a.8)
    "MonteCarloRequest",
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
    "SenParadoxRequest", "SenParadoxResponse",
]
