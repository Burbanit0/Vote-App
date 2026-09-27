"""
api/routes/simulations.py — the /api/v2/simulations/* family.

Workers live in api/domain/simulations/{advanced,compare}.py; PR 2 deleted the
rest of this router (the legacy /simulations form family, what-if, compare,
strategic-impact …) when nothing called them any more.

    GET  /api/v2/simulations/manipulability  Gibbard-Satterthwaite index
    POST /api/v2/simulations/vote-steps      Per-step ballot-counting animation
    POST /api/v2/simulations/monte-carlo     Repeated-run aggregate
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from api.core.ratelimit import check_v2_rate_limit
from api.core.worker_dispatch import run_passthrough, run_typed


from api.domain.simulations.advanced import (
    _monte_carlo_worker,
)
from api.domain.simulations.compare import (
    _manipulability_worker,
    _vote_steps_worker,
)
from api.schemas.common import WORKER_ERROR_RESPONSES
from api.schemas.simulations import (
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
    # See election.py's router for why 400/500/503 apply to every route here.
    # This router also used to declare 404, for a real-election lookup in
    # api/domain/simulations/advanced.py that PR 2 deleted with the endpoint
    # it served; no worker here returns one now.
    responses=WORKER_ERROR_RESPONSES,
)


# ── simulation_compare (Phase 4.5.a.7) ──────────────────────────────────────


@router.get("/manipulability", response_model=ManipulabilityResponse, summary="Gibbard-Satterthwaite manipulability index")
async def manipulability(
    num_candidates: int = 4,
    num_voters: int = 500,
    num_trials: int = 200,
    ideology: str = "random",
    methods: str = "all",
) -> Dict[str, Any]:
    return await run_passthrough(_manipulability_worker, {
        "num_candidates": num_candidates,
        "num_voters": num_voters,
        "num_trials": num_trials,
        "ideology": ideology,
        "methods": methods,
    })


@router.post("/vote-steps", response_model=VoteStepsResponse, summary="Step-by-step ballot-counting animation data")
async def vote_steps(request: VoteStepsRequest) -> VoteStepsResponse:
    return await run_typed(_vote_steps_worker, request, VoteStepsResponse)


# ── simulation_advanced (Phase 4.5.a.8) ─────────────────────────────────────


@router.post("/monte-carlo", response_model=MonteCarloResponse, summary="Aggregate Monte Carlo over N runs (sync variant)")
async def monte_carlo(request: MonteCarloRequest) -> MonteCarloResponse:
    return await run_typed(_monte_carlo_worker, request, MonteCarloResponse)


