"""
api/routes/polity.py — FastAPI routes for /api/v2/polity/*, the run explorer.

Read-only views of finished polity simulation runs: the runs under the configured roots,
one run's overview, its per-tick frames in chunks, and a citizen's biography. The work
is in api/domain/polity/explorer_workers.py; a run's files are read off the event loop.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any, Callable, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from api.core.config import get_settings
from api.core.ratelimit import check_v2_rate_limit
from api.core.worker_dispatch import run_bounded
from api.domain.polity.explorer_workers import (
    MAX_FRAME_SPAN,
    ExplorerContext,
    explorer_roots,
    list_polity_runs,
    polity_citizen,
    polity_run_frames,
    polity_run_overview,
)
from api.domain.polity.run_catalog import RunCache
from api.schemas.common import ErrorDetail
from api.schemas.polity import PolityCitizen, PolityFrames, PolityRunList, PolityRunOverview

router = APIRouter(
    prefix="/api/v2/polity",
    tags=["polity"],
    dependencies=[Depends(check_v2_rate_limit)],
    # 400: a run that cannot be explored or a frame range out of bounds; 404: an
    # unknown run key or citizen; 503: run_bounded's timeout.
    responses={
        400: {"model": ErrorDetail},
        404: {"model": ErrorDetail},
        500: {"model": ErrorDetail},
        503: {"model": ErrorDetail},
    },
)

RunKey = Annotated[str, Path(pattern=r"^[0-9a-f]{16}$", description="A run key from GET /runs.")]
MAX_TICK = 100_000


@lru_cache(maxsize=4)
def _cache(capacity: int) -> RunCache:
    return RunCache(capacity)


def _context() -> ExplorerContext:
    settings = get_settings()
    return ExplorerContext(
        roots=explorer_roots(settings.polity_run_roots),
        max_journal_bytes=settings.polity_explorer_max_journal_bytes,
        cache=_cache(settings.polity_explorer_cache_runs),
    )


async def _run(worker: Callable[..., tuple[Dict[str, Any], int]], *args: Any) -> Dict[str, Any]:
    try:
        body, status_code = await run_bounded(worker, _context(), *args)
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail="Request took too long to process") from exc
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=body.get("error", "Error"))
    return body


@router.get("/runs", response_model=PolityRunList, summary="Finished simulation runs the explorer can open")
async def polity_runs() -> Dict[str, Any]:
    return await _run(list_polity_runs)


@router.get("/runs/{run_key}", response_model=PolityRunOverview, summary="A run's map, institutional story and curves")
async def polity_run(run_key: RunKey) -> Dict[str, Any]:
    return await _run(polity_run_overview, run_key)


@router.get("/runs/{run_key}/frames", response_model=PolityFrames, summary=f"A run's per-tick frames, at most {MAX_FRAME_SPAN} ticks at a time")
async def polity_frames(
    run_key: RunKey,
    from_tick: Annotated[int, Query(ge=0, le=MAX_TICK)] = 0,
    to_tick: Annotated[Optional[int], Query(ge=0, le=MAX_TICK, description=f"Inclusive; defaults to {MAX_FRAME_SPAN} ticks from from_tick.")] = None,
) -> Dict[str, Any]:
    return await _run(polity_run_frames, run_key, from_tick, to_tick)


@router.get("/runs/{run_key}/citizens/{citizen_id}", response_model=PolityCitizen, summary="One citizen's biography in a run")
async def polity_citizen_biography(run_key: RunKey, citizen_id: Annotated[int, Path(ge=0, le=1_000_000)]) -> Dict[str, Any]:
    return await _run(polity_citizen, run_key, citizen_id)
