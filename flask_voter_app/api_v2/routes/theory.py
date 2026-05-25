"""
api_v2/routes/theory.py — FastAPI routes for /api/v2/theory/*.

Phase 4 batch 1: arrow / iia-rate / plott-chaos / judgment-aggregation.

Theory endpoints return TYPED responses (unlike most perturbers in
Phase 3): the frontend pedagogical text depends on stable shapes, and
the schemas are not too large. Deeply heterogeneous sub-objects (axiom
counterexamples, resolution-method dicts) stay `Dict[str, Any]`.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.schemas import (
    ArrowRequest,
    ArrowResponse,
    IIARateRequest,
    IIARateResponse,
    JudgmentAggregationRequest,
    JudgmentAggregationResponse,
    PlottChaosRequest,
    PlottChaosResponse,
)

from api_v2.domain.theory import (
    arrow as arrow_domain,
    iia_rate as iia_rate_domain,
    judgment_aggregation as judgment_aggregation_domain,
    plott_chaos as plott_chaos_domain,
)

router = APIRouter(prefix="/api/v2/theory", tags=["theory"])


# ── Shared helper ───────────────────────────────────────────────────────────

async def _run_typed(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
    response_model: type[BaseModel],
) -> BaseModel:
    """Adapt (body, status) contract to FastAPI's exception-based model."""
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


# ── /arrow ──────────────────────────────────────────────────────────────────

@router.post(
    "/arrow",
    response_model=ArrowResponse,
    summary="Per-method Arrow axiom violation analysis",
    response_description="Per-axiom violation flag + minimal counterexamples + "
                         "human-readable summary + tradeoff type.",
)
async def arrow_endpoint(request: ArrowRequest) -> ArrowResponse:
    """For a voting method, lists which Arrow axioms it violates with a
    minimal counterexample for each. Pure lookup + boilerplate text;
    `seed` reserved for future randomized counterexamples."""
    return await _run_typed(arrow_domain, request, ArrowResponse)


# ── /iia-rate ───────────────────────────────────────────────────────────────

@router.post(
    "/iia-rate",
    response_model=IIARateResponse,
    summary="Empirical IIA violation rate vs number of candidates",
    response_description="Curve of (n_candidates, violation_rate) for "
                         "n in [2, max_candidates].",
)
async def iia_rate_endpoint(request: IIARateRequest) -> IIARateResponse:
    """Monte-Carlo simulation: for each n, generate `num_trials` random
    profiles, run plurality on the full profile then on the profile
    with one random candidate removed, count winner changes. Other
    methods are scaled from the plurality baseline."""
    return await _run_typed(iia_rate_domain, request, IIARateResponse)


# ── /plott-chaos ────────────────────────────────────────────────────────────

@router.post(
    "/plott-chaos",
    response_model=PlottChaosResponse,
    summary="Plott's Chaos Theorem in 2-D policy space",
    response_description="Condorcet-winner flag, top cycle (Smith set), and "
                         "two BFS paths showing the agenda-setter can reach "
                         "diametrically opposite outcomes from the same start.",
)
async def plott_chaos_endpoint(request: PlottChaosRequest) -> PlottChaosResponse:
    """In ≥2-D policy space with ≥3 voters, a Condorcet winner almost
    never exists, and from any starting point the agenda-setter can
    reach ANY other point via a sequence of majority votes."""
    return await _run_typed(plott_chaos_domain, request, PlottChaosResponse)


# ── /judgment-aggregation ──────────────────────────────────────────────────

@router.post(
    "/judgment-aggregation",
    response_model=JudgmentAggregationResponse,
    summary="Discursive dilemma (List & Pettit 2002)",
    response_description="Per-proposition collective vote + coherence "
                         "diagnosis + premise-based vs conclusion-based "
                         "resolution.",
)
async def judgment_aggregation_endpoint(
    request: JudgmentAggregationRequest,
) -> JudgmentAggregationResponse:
    """Majority rule on propositions can produce collectively incoherent
    results even when every individual voter is perfectly coherent.
    Pre-defined scenarios: legal liability, fiscal trilemma, climate."""
    return await _run_typed(
        judgment_aggregation_domain, request, JudgmentAggregationResponse,
    )
