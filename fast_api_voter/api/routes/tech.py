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

from typing import Any, Callable, Dict, TypeVar

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.core.ratelimit import check_v2_rate_limit
from api.core.worker_dispatch import raise_for_status, run_worker_bounded
from api.domain.tech import (
    _polis_with_candidates_worker,
)
from api.schemas import (
    ErrorDetail,
    PolisWithCandidatesRequest,
    PolisWithCandidatesResponse,
)


router = APIRouter(
    prefix="/api/v2/tech",
    tags=["tech"],
    dependencies=[Depends(check_v2_rate_limit)],
    # See election.py's router for why 400/500/503 apply to every route here.
    responses={
        400: {"model": ErrorDetail},
        500: {"model": ErrorDetail},
        503: {"model": ErrorDetail},
    },
)

_ResponseT = TypeVar("_ResponseT", bound=BaseModel)


async def _run_passthrough(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
) -> Dict[str, Any]:
    """Same helper as election + theory routers — runs the sync worker
    in a thread, lifts the (body, status) tuple into HTTPException."""
    body, status_code = await run_worker_bounded(domain_fn, request.model_dump())
    return raise_for_status(body, status_code)


async def _run_typed(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
    response_model: type[_ResponseT],
) -> _ResponseT:
    """Like _run_passthrough but parses the worker body through `response_model`
    (which carries `extra="allow"`, so unmodeled fields still pass through)."""
    body = await _run_passthrough(domain_fn, request)
    return response_model.model_validate(body)


@router.post(
    "/polis",
    response_model=PolisWithCandidatesResponse,
    summary="Pol.is clustering + classical election cross-comparison",
    response_description="Same outputs as /polis-simulation plus per-candidate "
                         "consensus-alignment scores and the 'Pol.is winner' "
                         "vs the classical election winner.",
)
async def polis_with_candidates_endpoint(
    request: PolisWithCandidatesRequest,
) -> PolisWithCandidatesResponse:
    return await _run_typed(_polis_with_candidates_worker, request, PolisWithCandidatesResponse)
