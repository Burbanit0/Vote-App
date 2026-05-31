"""
api/routes/simulations.py — Core simulation endpoints (Phase 4.5.a.5).

Migrates the `simulation_base` Flask blueprint (the /simulations/* family used
by SimulationPage and its visualisation tabs) to FastAPI. URLs are normalised
under /api/v2/simulations/* (the Flask side keeps /simulations/* and gains an
/api/simulations/* rollback alias — see app/__init__.py).

Same passthrough pattern as the other migrated routers: Pydantic on the request,
Dict on the response (these return full voter/candidate objects, utility matrices
and per-segment breakdowns not worth typing). Compute is unchanged — only the
HTTP adapter moved; the `_*_worker` functions are imported from
app.routes.simulation_base.

    POST /api/v2/simulations                  Legacy form simulation (deprecated)
    POST /api/v2/simulations/simulate_voters
    POST /api/v2/simulations/simulate_candidates
    POST /api/v2/simulations/get_closest_candidate
    POST /api/v2/simulations/simulate_utility
    POST /api/v2/simulations/calculate_utility
    POST /api/v2/simulations/get_utility_matrix
    POST /api/v2/simulations/get_voter_segments
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, TypeVar

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

_ResponseT = TypeVar("_ResponseT", bound=BaseModel)

from api.domain.simulations.base import (
    _calculate_utility_worker,
    _closest_candidate_worker,
    _simulate_candidates_worker,
    _simulate_utility_worker,
    _simulate_voters_worker,
    _simulate_votes_worker,
    _utility_matrix_worker,
    _voter_segments_worker,
)
from api.domain.simulations.advanced import (
    _bandwagon_worker,
    _blank_contagion_worker,
    _blank_history_worker,
    _constitutional_scenario_worker,
    _monte_carlo_worker,
    _multiwinner_worker,
    _real_election_worker,
    _real_elections_list_worker,
)
from api.domain.simulations.campaign import _campaign_worker
from api.domain.simulations.compare import (
    _arrow_criteria_worker,
    _compare_methods_worker,
    _condorcet_matrix_worker,
    _ideology_map_worker,
    _manipulability_worker,
    _scenario_worker,
    _sensitivity_worker,
    _strategic_impact_worker,
    _vote_steps_worker,
)
from api.domain.simulations.whatif import _what_if_worker
from api.schemas import (
    ArrowCriteriaRequest,
    ArrowCriteriaResponse,
    BandwagonRequest,
    BandwagonResponse,
    BlankContagionRequest,
    BlankContagionResponse,
    CalculateUtilityRequest,
    CalculateUtilityResponse,
    CampaignRequest,
    CampaignResponse,
    ClosestCandidateRequest,
    ClosestCandidateResponse,
    CompareMethodsRequest,
    CompareMethodsResponse,
    CondorcetMatrixRequest,
    CondorcetMatrixResponse,
    ConstitutionalScenarioRequest,
    ConstitutionalScenarioResponse,
    IdeologyMapRequest,
    IdeologyMapResponse,
    LegacySimulateRequest,
    LegacySimulateResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    MultiwinnerRequest,
    MultiwinnerResponse,
    RealElectionRequest,
    RealElectionResponse,
    ScenarioRequest,
    ScenarioResponse,
    SensitivityRequest,
    SensitivityResponse,
    SimulateCandidatesRequest,
    SimulateCandidatesResponse,
    SimulateUtilityRequest,
    SimulateUtilityResponse,
    SimulateVotersRequest,
    SimulateVotersResponse,
    StrategicImpactRequest,
    StrategicImpactResponse,
    UtilityMatrixRequest,
    UtilityMatrixResponse,
    VoteStepsRequest,
    VoteStepsResponse,
    VoterSegmentsRequest,
    VoterSegmentsResponse,
    WhatIfRequest,
    WhatIfResponse,
)


router = APIRouter(prefix="/api/v2/simulations", tags=["simulations"])


async def _run_worker(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Run the sync worker off the event loop and lift its (body, status) tuple
    into an HTTPException on error."""
    body, status_code = await asyncio.to_thread(domain_fn, payload)
    if status_code != 200:
        # Propagate the worker's status (400 validation, 404 not-found, 500 …)
        raise HTTPException(
            status_code=status_code,
            detail=body.get("error", "Error"),
        )
    return body


async def _run_passthrough(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
) -> Dict[str, Any]:
    """Same as _run_worker but takes a Pydantic request and dumps it first."""
    return await _run_worker(domain_fn, request.model_dump())


async def _run_typed(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
    response_model: type[_ResponseT],
) -> _ResponseT:
    """Like _run_passthrough but parses the worker body through `response_model`
    (which carries `extra="allow"`, so unmodeled fields still pass through)."""
    body = await _run_worker(domain_fn, request.model_dump())
    return response_model.model_validate(body)


@router.post(
    "",
    response_model=LegacySimulateResponse,
    summary="Legacy form-based vote simulation (deprecated)",
    response_description="Per-method winners + voter samples. Carries an "
                         "X-Deprecation-Warning header — prefer the spatial "
                         "pipeline or /api/v2/election/simulate.",
)
async def legacy_simulate(
    request: LegacySimulateRequest, response: Response
) -> LegacySimulateResponse:
    body = await _run_typed(_simulate_votes_worker, request, LegacySimulateResponse)
    if body.deprecation_warning:
        response.headers["X-Deprecation-Warning"] = body.deprecation_warning
    return body


@router.post(
    "/simulate_voters",
    response_model=SimulateVotersResponse,
    summary="Generate a synthetic voter population",
)
async def simulate_voters(request: SimulateVotersRequest) -> SimulateVotersResponse:
    return await _run_typed(_simulate_voters_worker, request, SimulateVotersResponse)


@router.post(
    "/simulate_candidates",
    response_model=SimulateCandidatesResponse,
    summary="Generate synthetic candidates across parties",
)
async def simulate_candidates(request: SimulateCandidatesRequest) -> SimulateCandidatesResponse:
    return await _run_typed(_simulate_candidates_worker, request, SimulateCandidatesResponse)


@router.post(
    "/get_closest_candidate",
    response_model=ClosestCandidateResponse,
    summary="Assign voters to their nearest candidate (2-D spatial)",
)
async def get_closest_candidate(request: ClosestCandidateRequest) -> ClosestCandidateResponse:
    return await _run_typed(_closest_candidate_worker, request, ClosestCandidateResponse)


@router.post(
    "/simulate_utility",
    response_model=SimulateUtilityResponse,
    summary="Compute utility for every voter × candidate pair",
)
async def simulate_utility(request: SimulateUtilityRequest) -> SimulateUtilityResponse:
    return await _run_typed(_simulate_utility_worker, request, SimulateUtilityResponse)


@router.post(
    "/calculate_utility",
    response_model=CalculateUtilityResponse,
    summary="Compute utility for a single voter × candidate",
)
async def calculate_utility(request: CalculateUtilityRequest) -> CalculateUtilityResponse:
    return await _run_typed(_calculate_utility_worker, request, CalculateUtilityResponse)


@router.post(
    "/get_utility_matrix",
    response_model=UtilityMatrixResponse,
    summary="Full utility matrix + vote-share stats",
)
async def get_utility_matrix(request: UtilityMatrixRequest) -> UtilityMatrixResponse:
    return await _run_typed(_utility_matrix_worker, request, UtilityMatrixResponse)


@router.post(
    "/get_voter_segments",
    response_model=VoterSegmentsResponse,
    summary="Per-demographic-segment utility & top-candidate breakdown",
)
async def get_voter_segments(request: VoterSegmentsRequest) -> VoterSegmentsResponse:
    return await _run_typed(_voter_segments_worker, request, VoterSegmentsResponse)


@router.post(
    "/what-if",
    response_model=WhatIfResponse,
    summary="Vary one parameter and compare method winners across values",
)
async def what_if(request: WhatIfRequest) -> WhatIfResponse:
    return await _run_typed(_what_if_worker, request, WhatIfResponse)


@router.post(
    "/campaign",
    response_model=CampaignResponse,
    summary="Day-by-day electoral campaign simulation",
)
async def campaign(request: CampaignRequest) -> CampaignResponse:
    return await _run_typed(_campaign_worker, request, CampaignResponse)


# ── simulation_compare (Phase 4.5.a.7) ──────────────────────────────────────

@router.post("/compare", response_model=CompareMethodsResponse, summary="Per-method metrics on a fresh population")
async def compare(request: CompareMethodsRequest) -> CompareMethodsResponse:
    return await _run_typed(_compare_methods_worker, request, CompareMethodsResponse)


@router.post("/strategic-impact", response_model=StrategicImpactResponse, summary="Regret vs proportion of strategic voters")
async def strategic_impact(request: StrategicImpactRequest) -> StrategicImpactResponse:
    return await _run_typed(_strategic_impact_worker, request, StrategicImpactResponse)


@router.post("/condorcet-matrix", response_model=CondorcetMatrixResponse, summary="Full pairwise duel matrix")
async def condorcet_matrix(request: CondorcetMatrixRequest) -> CondorcetMatrixResponse:
    return await _run_typed(_condorcet_matrix_worker, request, CondorcetMatrixResponse)


@router.post("/sensitivity", response_model=SensitivityResponse, summary="Vary one parameter, track winners & regret")
async def sensitivity(request: SensitivityRequest) -> SensitivityResponse:
    return await _run_typed(_sensitivity_worker, request, SensitivityResponse)


@router.post("/arrow-criteria", response_model=ArrowCriteriaResponse, summary="Empirically check Arrow's criteria")
async def arrow_criteria(request: ArrowCriteriaRequest) -> ArrowCriteriaResponse:
    return await _run_typed(_arrow_criteria_worker, request, ArrowCriteriaResponse)


@router.post("/scenario", response_model=ScenarioResponse, summary="Citizen-configured scenario, with/without blank vote")
async def scenario(request: ScenarioRequest) -> ScenarioResponse:
    return await _run_typed(_scenario_worker, request, ScenarioResponse)


@router.get("/manipulability", summary="Gibbard-Satterthwaite manipulability index")
async def manipulability(
    num_candidates: int = 4,
    num_voters: int = 500,
    num_trials: int = 200,
    ideology: str = "random",
    methods: str = "all",
) -> Dict[str, Any]:
    return await _run_worker(_manipulability_worker, {
        "num_candidates": num_candidates,
        "num_voters": num_voters,
        "num_trials": num_trials,
        "ideology": ideology,
        "methods": methods,
    })


@router.post("/vote-steps", response_model=VoteStepsResponse, summary="Step-by-step ballot-counting animation data")
async def vote_steps(request: VoteStepsRequest) -> VoteStepsResponse:
    return await _run_typed(_vote_steps_worker, request, VoteStepsResponse)


@router.post("/ideology-map", response_model=IdeologyMapResponse, summary="2-D ideological map of voter preferences")
async def ideology_map(request: IdeologyMapRequest) -> IdeologyMapResponse:
    return await _run_typed(_ideology_map_worker, request, IdeologyMapResponse)


# ── simulation_advanced (Phase 4.5.a.8) ─────────────────────────────────────

@router.post("/bandwagon", response_model=BandwagonResponse, summary="Cascading social-influence simulation")
async def bandwagon(request: BandwagonRequest) -> BandwagonResponse:
    return await _run_typed(_bandwagon_worker, request, BandwagonResponse)


@router.post("/monte-carlo", response_model=MonteCarloResponse, summary="Aggregate Monte Carlo over N runs (sync variant)")
async def monte_carlo(request: MonteCarloRequest) -> MonteCarloResponse:
    return await _run_typed(_monte_carlo_worker, request, MonteCarloResponse)


@router.post("/multiwinner", response_model=MultiwinnerResponse, summary="Compare proportional multi-winner methods")
async def multiwinner(request: MultiwinnerRequest) -> MultiwinnerResponse:
    return await _run_typed(_multiwinner_worker, request, MultiwinnerResponse)


@router.get("/real-elections", summary="List available historical elections")
async def real_elections() -> List[Dict[str, Any]]:
    return await _run_worker(_real_elections_list_worker, {})  # type: ignore[return-value]


@router.get("/blank-history", summary="Blank-vote time series for a country")
async def blank_history(country: str = "") -> Dict[str, Any]:
    return await _run_worker(_blank_history_worker, {"country": country})


@router.post("/real-election", response_model=RealElectionResponse, summary="Analyse a real historical election")
async def real_election(request: RealElectionRequest) -> RealElectionResponse:
    return await _run_typed(_real_election_worker, request, RealElectionResponse)


@router.post("/constitutional-scenario", response_model=ConstitutionalScenarioResponse, summary="Constitutional aftermath of a blank-vote victory")
async def constitutional_scenario(request: ConstitutionalScenarioRequest) -> ConstitutionalScenarioResponse:
    return await _run_typed(_constitutional_scenario_worker, request, ConstitutionalScenarioResponse)


@router.post("/blank-contagion", response_model=BlankContagionResponse, summary="SIS blank-vote contagion simulation")
async def blank_contagion(request: BlankContagionRequest) -> BlankContagionResponse:
    return await _run_typed(_blank_contagion_worker, request, BlankContagionResponse)
