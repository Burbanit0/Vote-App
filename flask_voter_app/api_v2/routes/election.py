"""
api_v2/routes/election.py — FastAPI routes for the Election Lab.

Phase 2 coverage:
    POST /api/v2/election/simulate

The remaining 34 election routes will be migrated incrementally during
Phase 3. Each migration follows the same template:
    1. Validate input via existing Pydantic schemas (app/schemas/election.py).
    2. Hand the dict to the appropriate domain function.
    3. Format the (body, status) tuple as a typed response.

Backend layering (top to bottom):
    routes (this file)            ─── HTTP adapter: validate + call service
        ↓
    api_v2.domain.election        ─── pure-Python compute (no Flask/FastAPI/DB)
        ↓
    app.utils.simulation_*        ─── primitives (voting methods, electorate, ...)
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, status

# Re-uses the Pydantic models defined in Phase 1. Single source of truth
# shared with the Flask side via the openapi-typescript pipeline.
from app.schemas import SimulateRequest, SimulateResponse

from api_v2.domain.election import simulate as simulate_domain

router = APIRouter(prefix="/api/v2/election", tags=["election"])


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    summary="Run the unified election simulation",
    response_description="Simulation result with all 17 voting methods, "
                         "Condorcet winner, blank rate, and inter-method agreement.",
)
async def simulate_endpoint(request: SimulateRequest) -> SimulateResponse:
    """Pure-compute election. Same seed = same result.

    The heavy simulation runs in a real OS thread (`asyncio.to_thread`)
    so it doesn't block the FastAPI event loop. That replaces the
    `eventlet.tpool.execute(...)` pattern from the Flask side — no more
    eventlet anywhere on the v2 path.

    Errors:
      * 400 — fewer than 2 candidates, or any Pydantic validation failure
      * 500 — internal compute error (logged with structlog)
    """
    body, status_code = await asyncio.to_thread(
        simulate_domain,
        request.model_dump(),
    )
    if status_code == 400:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=body.get("error", "Bad request"))
    if status_code != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=body.get("error", "Internal error"))
    return SimulateResponse.model_validate(body)
