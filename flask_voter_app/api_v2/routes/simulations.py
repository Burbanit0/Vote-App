"""
api_v2/routes/simulations.py — Core simulation endpoints (Phase 4.5.a.5).

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
from typing import Any, Callable, Dict, List

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.routes.simulation_base import (
    _calculate_utility_worker,
    _closest_candidate_worker,
    _simulate_candidates_worker,
    _simulate_utility_worker,
    _simulate_voters_worker,
    _simulate_votes_worker,
    _utility_matrix_worker,
    _voter_segments_worker,
)
from app.routes.simulation_advanced import (
    _bandwagon_worker,
    _blank_contagion_worker,
    _blank_history_worker,
    _constitutional_scenario_worker,
    _monte_carlo_worker,
    _multiwinner_worker,
    _real_election_worker,
    _real_elections_list_worker,
)
from api_v2.domain.simulations.campaign import _campaign_worker
from app.routes.simulation_compare import (
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
from api_v2.domain.simulations.whatif import _what_if_worker
from api_v2.schemas import (
    ArrowCriteriaRequest,
    BandwagonRequest,
    BlankContagionRequest,
    CalculateUtilityRequest,
    CampaignRequest,
    ClosestCandidateRequest,
    CompareMethodsRequest,
    CondorcetMatrixRequest,
    ConstitutionalScenarioRequest,
    IdeologyMapRequest,
    LegacySimulateRequest,
    MonteCarloRequest,
    MultiwinnerRequest,
    RealElectionRequest,
    ScenarioRequest,
    SensitivityRequest,
    SimulateCandidatesRequest,
    SimulateUtilityRequest,
    SimulateVotersRequest,
    StrategicImpactRequest,
    UtilityMatrixRequest,
    VoteStepsRequest,
    VoterSegmentsRequest,
    WhatIfRequest,
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


@router.post(
    "",
    summary="Legacy form-based vote simulation (deprecated)",
    response_description="Per-method winners + voter samples. Carries an "
                         "X-Deprecation-Warning header — prefer the spatial "
                         "pipeline or /api/v2/election/simulate.",
)
async def legacy_simulate(
    request: LegacySimulateRequest, response: Response
) -> Dict[str, Any]:
    body = await _run_passthrough(_simulate_votes_worker, request)
    warning = body.get("deprecation_warning")
    if warning:
        response.headers["X-Deprecation-Warning"] = warning
    return body


@router.post(
    "/simulate_voters",
    summary="Generate a synthetic voter population",
)
async def simulate_voters(request: SimulateVotersRequest) -> Dict[str, Any]:
    return await _run_passthrough(_simulate_voters_worker, request)


@router.post(
    "/simulate_candidates",
    summary="Generate synthetic candidates across parties",
)
async def simulate_candidates(request: SimulateCandidatesRequest) -> Dict[str, Any]:
    return await _run_passthrough(_simulate_candidates_worker, request)


@router.post(
    "/get_closest_candidate",
    summary="Assign voters to their nearest candidate (2-D spatial)",
)
async def get_closest_candidate(request: ClosestCandidateRequest) -> Dict[str, Any]:
    return await _run_passthrough(_closest_candidate_worker, request)


@router.post(
    "/simulate_utility",
    summary="Compute utility for every voter × candidate pair",
)
async def simulate_utility(request: SimulateUtilityRequest) -> Dict[str, Any]:
    return await _run_passthrough(_simulate_utility_worker, request)


@router.post(
    "/calculate_utility",
    summary="Compute utility for a single voter × candidate",
)
async def calculate_utility(request: CalculateUtilityRequest) -> Dict[str, Any]:
    return await _run_passthrough(_calculate_utility_worker, request)


@router.post(
    "/get_utility_matrix",
    summary="Full utility matrix + vote-share stats",
)
async def get_utility_matrix(request: UtilityMatrixRequest) -> Dict[str, Any]:
    return await _run_passthrough(_utility_matrix_worker, request)


@router.post(
    "/get_voter_segments",
    summary="Per-demographic-segment utility & top-candidate breakdown",
)
async def get_voter_segments(request: VoterSegmentsRequest) -> Dict[str, Any]:
    return await _run_passthrough(_voter_segments_worker, request)


@router.post(
    "/what-if",
    summary="Vary one parameter and compare method winners across values",
)
async def what_if(request: WhatIfRequest) -> Dict[str, Any]:
    return await _run_passthrough(_what_if_worker, request)


@router.post(
    "/campaign",
    summary="Day-by-day electoral campaign simulation",
)
async def campaign(request: CampaignRequest) -> Dict[str, Any]:
    return await _run_passthrough(_campaign_worker, request)


# ── simulation_compare (Phase 4.5.a.7) ──────────────────────────────────────

@router.post("/compare", summary="Per-method metrics on a fresh population")
async def compare(request: CompareMethodsRequest) -> Dict[str, Any]:
    return await _run_passthrough(_compare_methods_worker, request)


@router.post("/strategic-impact", summary="Regret vs proportion of strategic voters")
async def strategic_impact(request: StrategicImpactRequest) -> Dict[str, Any]:
    return await _run_passthrough(_strategic_impact_worker, request)


@router.post("/condorcet-matrix", summary="Full pairwise duel matrix")
async def condorcet_matrix(request: CondorcetMatrixRequest) -> Dict[str, Any]:
    return await _run_passthrough(_condorcet_matrix_worker, request)


@router.post("/sensitivity", summary="Vary one parameter, track winners & regret")
async def sensitivity(request: SensitivityRequest) -> Dict[str, Any]:
    return await _run_passthrough(_sensitivity_worker, request)


@router.post("/arrow-criteria", summary="Empirically check Arrow's criteria")
async def arrow_criteria(request: ArrowCriteriaRequest) -> Dict[str, Any]:
    return await _run_passthrough(_arrow_criteria_worker, request)


@router.post("/scenario", summary="Citizen-configured scenario, with/without blank vote")
async def scenario(request: ScenarioRequest) -> Dict[str, Any]:
    return await _run_passthrough(_scenario_worker, request)


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


@router.post("/vote-steps", summary="Step-by-step ballot-counting animation data")
async def vote_steps(request: VoteStepsRequest) -> Dict[str, Any]:
    return await _run_passthrough(_vote_steps_worker, request)


@router.post("/ideology-map", summary="2-D ideological map of voter preferences")
async def ideology_map(request: IdeologyMapRequest) -> Dict[str, Any]:
    return await _run_passthrough(_ideology_map_worker, request)


# ── simulation_advanced (Phase 4.5.a.8) ─────────────────────────────────────

@router.post("/bandwagon", summary="Cascading social-influence simulation")
async def bandwagon(request: BandwagonRequest) -> Dict[str, Any]:
    return await _run_passthrough(_bandwagon_worker, request)


@router.post("/monte-carlo", summary="Aggregate Monte Carlo over N runs (sync variant)")
async def monte_carlo(request: MonteCarloRequest) -> Dict[str, Any]:
    return await _run_passthrough(_monte_carlo_worker, request)


@router.post("/multiwinner", summary="Compare proportional multi-winner methods")
async def multiwinner(request: MultiwinnerRequest) -> Dict[str, Any]:
    return await _run_passthrough(_multiwinner_worker, request)


@router.get("/real-elections", summary="List available historical elections")
async def real_elections() -> List[Dict[str, Any]]:
    return await _run_worker(_real_elections_list_worker, {})  # type: ignore[return-value]


@router.get("/blank-history", summary="Blank-vote time series for a country")
async def blank_history(country: str = "") -> Dict[str, Any]:
    return await _run_worker(_blank_history_worker, {"country": country})


@router.post("/real-election", summary="Analyse a real historical election")
async def real_election(request: RealElectionRequest) -> Dict[str, Any]:
    return await _run_passthrough(_real_election_worker, request)


@router.post("/constitutional-scenario", summary="Constitutional aftermath of a blank-vote victory")
async def constitutional_scenario(request: ConstitutionalScenarioRequest) -> Dict[str, Any]:
    return await _run_passthrough(_constitutional_scenario_worker, request)


@router.post("/blank-contagion", summary="SIS blank-vote contagion simulation")
async def blank_contagion(request: BlankContagionRequest) -> Dict[str, Any]:
    return await _run_passthrough(_blank_contagion_worker, request)
