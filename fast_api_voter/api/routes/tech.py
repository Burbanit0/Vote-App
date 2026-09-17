"""
api/routes/tech.py — Tech-democracy pedagogical demos.

Pydantic on the request, Dict on the response — this endpoint returns rich
nested structures (PCA coordinates, per-cluster vote matrices) not worth
typing. PR 2 deleted its two siblings (/e2e-demo, /polis-simulation) when
nothing called them any more.

    POST /api/v2/tech/polis             Pol.is + candidate cross-comparison
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.core.ratelimit import check_v2_rate_limit
from api.core.worker_dispatch import run_typed
from api.domain.tech import (
    _polis_with_candidates_worker,
)
from api.schemas import (
    WORKER_ERROR_RESPONSES,
    PolisWithCandidatesRequest,
    PolisWithCandidatesResponse,
)


router = APIRouter(
    prefix="/api/v2/tech",
    tags=["tech"],
    dependencies=[Depends(check_v2_rate_limit)],
    # See election.py's router for why 400/500/503 apply to every route here.
    responses=WORKER_ERROR_RESPONSES,
)


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
    return await run_typed(_polis_with_candidates_worker, request, PolisWithCandidatesResponse)
