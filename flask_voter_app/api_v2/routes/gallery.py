"""
api_v2/routes/gallery.py — Public scenario gallery (async, Phase 4.5.b.2).

No auth (gallery is public). Persistence uses the Flask-independent async layer
in `api_v2.db` — no more `run_in_flask_db` bridge.

Routes:
    GET  /api/v2/scenarios/gallery/featured     6 highest-views featured scenarios
    GET  /api/v2/scenarios/gallery/{id}         detail view (increments views)
    GET  /api/v2/scenarios/gallery              paginated list
    POST /api/v2/scenarios/gallery              save a new scenario (no auth)
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Text, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api_v2.db import GalleryScenario
from api_v2.db.session import get_async_session
from api_v2.schemas import (
    GalleryCreateRequest,
    GalleryDetail,
    GalleryItem,
    GalleryPage,
)


router = APIRouter(prefix="/api/v2/scenarios/gallery", tags=["gallery"])

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


@router.get(
    "/featured",
    response_model=list[GalleryItem],
    summary="Top featured scenarios by view count",
)
async def get_featured(db: DbSession, limit: int = Query(6, ge=1, le=20)) -> list[GalleryItem]:
    result = await db.execute(
        select(GalleryScenario)
        .where(GalleryScenario.is_featured.is_(True))
        .order_by(GalleryScenario.views.desc())
        .limit(limit)
    )
    return [GalleryItem.model_validate(s.to_dict()) for s in result.scalars()]


@router.get(
    "/{scenario_id}",
    response_model=GalleryDetail,
    summary="Fetch a single scenario (increments the view counter)",
)
async def get_scenario(scenario_id: int, db: DbSession) -> GalleryDetail:
    scenario = await db.get(GalleryScenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    scenario.views += 1
    await db.commit()
    return GalleryDetail.model_validate(scenario.to_dict(include_params=True))


@router.get(
    "",
    response_model=GalleryPage,
    summary="Paginated gallery list",
    response_description="Items + total + page metadata.",
)
async def list_gallery(
    db: DbSession,
    page:     int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    sort:     str = Query("recent", description="'recent' | 'popular' | 'featured'"),
    tag:      str = Query("", description="Filter by exact tag (case-sensitive)."),
) -> GalleryPage:
    query = select(GalleryScenario)
    count_q = select(func.count()).select_from(GalleryScenario)

    if tag:
        safe = tag.replace('"', '').replace("'", "")[:50]
        cond = cast(GalleryScenario.tags, Text).like(f'%"{safe}"%')
        query = query.where(cond)
        count_q = count_q.where(cond)

    if sort == "popular":
        query = query.order_by(GalleryScenario.views.desc(), GalleryScenario.created_at.desc())
    elif sort == "featured":
        query = query.where(GalleryScenario.is_featured.is_(True)).order_by(
            GalleryScenario.views.desc()
        )
        count_q = count_q.where(GalleryScenario.is_featured.is_(True))
    else:
        query = query.order_by(GalleryScenario.created_at.desc())

    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(
        query.offset((page - 1) * per_page).limit(per_page)
    )).scalars().all()
    pages = max(1, (total + per_page - 1) // per_page)

    return GalleryPage.model_validate({
        "items":    [s.to_dict() for s in rows],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    pages,
    })


@router.post(
    "",
    response_model=GalleryDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a scenario to the public gallery",
    response_description="The freshly created scenario including its id.",
)
async def create_gallery_scenario(
    request: GalleryCreateRequest, db: DbSession
) -> GalleryDetail:
    """No auth — the gallery is public. Featured flag stays False until an admin
    promotes the scenario directly in the database."""
    clean_tags = [str(t)[:50] for t in request.tags if str(t).strip()][:10]

    scenario = GalleryScenario(
        title=request.title,
        description=request.description,
        params=request.params,
        results_summary=request.results_summary,
        tags=clean_tags,
        is_featured=False,
    )
    db.add(scenario)
    await db.commit()
    return GalleryDetail.model_validate(scenario.to_dict(include_params=True))
