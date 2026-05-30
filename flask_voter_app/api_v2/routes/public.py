"""
api_v2/routes/public.py — Vote Lab Public Research API v1.

Phase 4.5.a.4 of the strangler-fig migration. Unlike every other migrated
router, this one keeps the product-version URL `/api/v1/*` (external
researchers depend on it) rather than moving to `/api/v2/*`. The compute is
identical to Flask — only the HTTP adapter changed; the `_*_worker` /
`_*_payload` functions are imported straight from `app.routes.api_public`.

    GET  /api/v1/methods         Voting-method catalogue
    POST /api/v1/simulate        Multi-method simulation        (10 req/min/IP)
    POST /api/v1/compare         Comparison + blank-vote rule    (5 req/min/IP)
    GET  /api/v1/real-elections  Historical election dataset
    GET  /api/v1/openapi.json    Hand-written OpenAPI 3.0 spec

The two POST routes preserve the documented per-IP rate limits via slowapi
(see api_v2/core/ratelimit.py). slowapi requires a `Request` parameter on any
decorated route, hence the `request: Request` arg.

NOTE — no `from __future__ import annotations` here on purpose. slowapi's
`@limiter.limit` wraps the endpoint with `functools.wraps`, so FastAPI reads
the signature through the wrapper whose `__globals__` belong to slowapi's
module. With stringized (PEP 563) annotations FastAPI can't resolve the
Pydantic body type there and silently demotes it to a query param (→ 422
"field required"). Keeping real annotation objects sidesteps that entirely.
"""
import asyncio
from typing import Any, Callable, Dict, Tuple

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.routes.api_public import (
    OPENAPI_SPEC,
    _compare_worker,
    _methods_payload,
    _real_elections_payload,
    _simulate_worker,
)
from api_v2.core.ratelimit import limiter
from api_v2.schemas import PublicCompareRequest, PublicSimulateRequest


router = APIRouter(prefix="/api/v1", tags=["public-v1"])


async def _run_passthrough(
    domain_fn: Callable[[Dict[str, Any]], Tuple[Dict[str, Any], int]],
    request_model: BaseModel,
) -> Dict[str, Any]:
    """Run the sync worker off the event loop and lift its (body, status)
    tuple into an HTTPException on error. Same helper as the other routers."""
    body, status_code = await asyncio.to_thread(domain_fn, request_model.model_dump())
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


@router.get(
    "/methods",
    summary="List the voting methods supported by the engine",
    response_description="Catalogue of 16+ methods with name, family, and ref.",
)
async def list_methods(family: str = "") -> Dict[str, Any]:
    return _methods_payload(family)


@router.post(
    "/simulate",
    summary="Run a multi-method simulation on a synthetic population",
    response_description="condorcet_winner + per-method winner & metrics.",
)
@limiter.limit("10/minute")
async def simulate(request: Request, body: PublicSimulateRequest) -> Dict[str, Any]:
    return await _run_passthrough(_simulate_worker, body)


@router.post(
    "/compare",
    summary="Multi-method comparison with optional blank-vote rule",
    response_description="Same shape as /simulate, plus blank_pct & "
                         "per-method blank_rule_applied when a rule is set.",
)
@limiter.limit("5/minute")
async def compare(request: Request, body: PublicCompareRequest) -> Dict[str, Any]:
    return await _run_passthrough(_compare_worker, body)


@router.get(
    "/real-elections",
    summary="List the historical elections in the dataset",
    response_description="Per-election metadata + estimated blank-vote pct.",
)
async def real_elections() -> Dict[str, Any]:
    return _real_elections_payload()


@router.get(
    "/openapi.json",
    summary="Hand-written OpenAPI 3.0 specification for /api/v1",
    response_description="The public API contract (kept hand-written so the "
                         "external surface stays stable across the migration).",
)
async def openapi_spec() -> Dict[str, Any]:
    return OPENAPI_SPEC
