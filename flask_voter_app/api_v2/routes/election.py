"""
api_v2/routes/election.py — FastAPI routes for the Election Lab.

Phase 2 coverage:
    POST /api/v2/election/simulate

Phase 3 batch 1 (this file):
    POST /api/v2/election/combined-effects
    POST /api/v2/election/campaign-sensitivity

Each route follows the same template:
    1. Validate input via existing Pydantic schemas (app/schemas/election.py).
    2. Hand the dict to the appropriate domain function via asyncio.to_thread
       (compute-bound code released from the event loop, no eventlet anywhere).
    3. Format the (body, status) tuple as a typed response or HTTPException.

Backend layering (top to bottom):
    routes (this file)            ─── HTTP adapter: validate + call service
        ↓
    api_v2.domain.election        ─── pure-Python compute (no Flask/FastAPI/DB)
        ↓
    app.utils.simulation_*        ─── primitives (voting methods, electorate, ...)
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

# Re-uses the Pydantic models defined in Phase 1. Single source of truth
# shared with the Flask side via the openapi-typescript pipeline.
from app.schemas import (
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

from api_v2.domain.election import (
    abstention as abstention_domain,
    campaign_sensitivity as campaign_sensitivity_domain,
    coalition as coalition_domain,
    combined_effects as combined_effects_domain,
    simulate as simulate_domain,
)

router = APIRouter(prefix="/api/v2/election", tags=["election"])


# ── Shared helper ───────────────────────────────────────────────────────────

async def _run_typed(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
    response_model: type[BaseModel],
) -> BaseModel:
    """Run a domain compute function in a worker thread and adapt its
    (body, status) contract to FastAPI's exception-based error model.

    - 200 → parse body through `response_model` and return it.
    - 400 → raise HTTPException(400) (domain-level validation, distinct from
            Pydantic 422 which fires BEFORE the worker is even called).
    - other → raise HTTPException(500).
    """
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
    return response_model.model_validate(body)


# ── /simulate ───────────────────────────────────────────────────────────────

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
    """
    return await _run_typed(simulate_domain, request, SimulateResponse)


# ── /combined-effects ───────────────────────────────────────────────────────

@router.post(
    "/combined-effects",
    response_model=CombinedEffectsResponse,
    summary="2³ factorial — isolate each model's contribution to divergence",
    response_description="One row per combination (blank × campaign × info), "
                         "plus per-factor agreement delta and disruptive ranking.",
)
async def combined_effects_endpoint(
    request: CombinedEffectsRequest,
) -> CombinedEffectsResponse:
    """8 simulations on the same electorate, with each model factor toggled
    independently. Identifies which factor disrupts inter-method agreement
    the most. Heaviest single endpoint (8 × full election pipeline)."""
    return await _run_typed(
        combined_effects_domain, request, CombinedEffectsResponse,
    )


# ── /campaign-sensitivity ───────────────────────────────────────────────────

@router.post(
    "/campaign-sensitivity",
    response_model=CampaignSensitivityResponse,
    summary="Snapshot the election at multiple campaign days",
    response_description="Per-method stability score over the campaign timeline.",
)
async def campaign_sensitivity_endpoint(
    request: CampaignSensitivityRequest,
) -> CampaignSensitivityResponse:
    """Runs the same electorate at multiple campaign snapshots (days 0, 7,
    14, 21, 28, 'final' by default) to measure how each voting method's
    winner changes over the campaign."""
    return await _run_typed(
        campaign_sensitivity_domain, request, CampaignSensitivityResponse,
    )


# ── /coalition ──────────────────────────────────────────────────────────────

@router.post(
    "/coalition",
    response_model=CoalitionResponse,
    summary="Per-method D'Hondt + greedy coalition formation",
    response_description="One coalition analysis per voting method, with "
                         "coalition_spread (ideological variance) and "
                         "most_centrist / most_divergent method rankings.",
)
async def coalition_endpoint(request: CoalitionRequest) -> CoalitionResponse:
    """For each voting method, allocates `total_seats` proportionally via
    D'Hondt then greedily picks the smallest ideologically-coherent
    coalition that crosses `government_threshold * total_seats`."""
    return await _run_typed(coalition_domain, request, CoalitionResponse)


# ── /abstention ─────────────────────────────────────────────────────────────

@router.post(
    "/abstention",
    response_model=AbstentionResponse,
    summary="Iterated abstention model with poll feedback",
    response_description="Round-by-round turnout, vote shares, and winner. "
                         "Includes per-method comparison (sincere vs final) "
                         "so the Lab matrix can show how abstention shifts "
                         "winners across all methods.",
)
async def abstention_endpoint(request: AbstentionRequest) -> AbstentionResponse:
    """Round 0 is sincere. From round 1 onwards, voters whose preferred
    candidate is trailing in the previous round's polls abstain with
    probability ∝ demobilization_factor × poll_influence."""
    return await _run_typed(abstention_domain, request, AbstentionResponse)
