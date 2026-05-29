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
from typing import Any, Callable, Dict

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
from app.schemas import (
    CalculateUtilityRequest,
    ClosestCandidateRequest,
    LegacySimulateRequest,
    SimulateCandidatesRequest,
    SimulateUtilityRequest,
    SimulateVotersRequest,
    UtilityMatrixRequest,
    VoterSegmentsRequest,
)


router = APIRouter(prefix="/api/v2/simulations", tags=["simulations"])


async def _run_passthrough(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
) -> Dict[str, Any]:
    """Run the sync worker off the event loop and lift its (body, status) tuple
    into an HTTPException on error. Same helper as the other routers."""
    body, status_code = await asyncio.to_thread(domain_fn, request.model_dump())
    if status_code == 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=body.get("error", "Bad request"),
        )
    if status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=body.get("error", "Internal error"),
        )
    return body


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
