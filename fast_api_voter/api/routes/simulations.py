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

from typing import Any, Callable, Dict, TypeVar

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.core.ratelimit import check_v2_rate_limit
from api.core.worker_dispatch import run_worker_bounded

_ResponseT = TypeVar("_ResponseT", bound=BaseModel)

from api.domain.simulations.advanced import (
    _monte_carlo_worker,
)
from api.domain.simulations.compare import (
    _manipulability_worker,
    _vote_steps_worker,
)
from api.schemas import (
    ErrorDetail,
    ManipulabilityResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    VoteStepsRequest,
    VoteStepsResponse,
)


router = APIRouter(
    prefix="/api/v2/simulations",
    tags=["simulations"],
    dependencies=[Depends(check_v2_rate_limit)],
    # See election.py's router for why 400/500 apply to every route here.
    # 404 is specific to this router: api/domain/simulations/advanced.py's
    # real-election lookup returns (body, 404) for an unknown election name.
    # 503: run_bounded's own timeout (Lot 3, api/core/worker_dispatch.py).
    responses={
        400: {"model": ErrorDetail},
        404: {"model": ErrorDetail},
        500: {"model": ErrorDetail},
        503: {"model": ErrorDetail},
    },
)


async def _run_worker(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Run the sync worker off the event loop and lift its (body, status) tuple
    into an HTTPException on error."""
    body, status_code = await run_worker_bounded(domain_fn, payload)
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


# ── simulation_compare (Phase 4.5.a.7) ──────────────────────────────────────



@router.get("/manipulability", response_model=ManipulabilityResponse, summary="Gibbard-Satterthwaite manipulability index")
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


# ── simulation_advanced (Phase 4.5.a.8) ─────────────────────────────────────



@router.post("/monte-carlo", response_model=MonteCarloResponse, summary="Aggregate Monte Carlo over N runs (sync variant)")
async def monte_carlo(request: MonteCarloRequest) -> MonteCarloResponse:
    return await _run_typed(_monte_carlo_worker, request, MonteCarloResponse)


