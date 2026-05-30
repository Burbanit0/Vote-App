"""
api/routes/tech.py — Tech-democracy pedagogical demos.

Three routes ported from app/routes/tech.py via the same passthrough
pattern as the Phase 3 perturbers (Pydantic on the request, Dict on
the response — these endpoints return rich nested structures like
PCA coordinates and per-cluster vote matrices that aren't worth
typing).

    POST /api/v2/tech/e2e-demo          End-to-end verifiable voting demo
    POST /api/v2/tech/polis-simulation  Pol.is consensus clustering
    POST /api/v2/tech/polis             Pol.is + candidate cross-comparison
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.domain.tech import (
    _e2e_demo_worker,
    _polis_simulation_worker,
    _polis_with_candidates_worker,
)
from api.schemas import (
    E2EDemoRequest,
    PolisSimulationRequest,
    PolisWithCandidatesRequest,
)


router = APIRouter(prefix="/api/v2/tech", tags=["tech"])


async def _run_passthrough(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
) -> Dict[str, Any]:
    """Same helper as election + theory routers — runs the sync worker
    in a thread, lifts the (body, status) tuple into HTTPException."""
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
    "/e2e-demo",
    summary="End-to-end verifiable voting pedagogical simulation",
    response_description="Per-voter encrypted ballots + shuffled bulletin "
                         "board + homomorphic aggregate + audit proof.",
)
async def e2e_demo_endpoint(request: E2EDemoRequest) -> Dict[str, Any]:
    return await _run_passthrough(_e2e_demo_worker, request)


@router.post(
    "/polis-simulation",
    summary="Pol.is consensus clustering on a statement set",
    response_description="PCA-2D coords + k-means cluster labels + per-cluster "
                         "vote rates + consensus / polarising statements.",
)
async def polis_simulation_endpoint(
    request: PolisSimulationRequest,
) -> Dict[str, Any]:
    return await _run_passthrough(_polis_simulation_worker, request)


@router.post(
    "/polis",
    summary="Pol.is clustering + classical election cross-comparison",
    response_description="Same outputs as /polis-simulation plus per-candidate "
                         "consensus-alignment scores and the 'Pol.is winner' "
                         "vs the classical election winner.",
)
async def polis_with_candidates_endpoint(
    request: PolisWithCandidatesRequest,
) -> Dict[str, Any]:
    return await _run_passthrough(_polis_with_candidates_worker, request)
