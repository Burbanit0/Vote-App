"""
api_v2/routes/gallery.py — Public scenario gallery.

Mirrors app/routes/gallery.py route-for-route. No auth (gallery is public);
all DB work goes through `run_in_flask_db` so the existing
`GalleryScenario` ORM model is reused as-is.

Routes:
    GET  /api/v2/scenarios/gallery/featured     6 highest-views featured scenarios
    GET  /api/v2/scenarios/gallery/{id}         detail view (increments views)
    GET  /api/v2/scenarios/gallery              paginated list
    POST /api/v2/scenarios/gallery              save a new scenario (no auth)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from api_v2.schemas import (
    GalleryCreateRequest,
    GalleryDetail,
    GalleryItem,
    GalleryPage,
)
from api_v2.core.db import run_in_flask_db


router = APIRouter(prefix="/api/v2/scenarios/gallery", tags=["gallery"])


# ── GET /featured ──────────────────────────────────────────────────────────

@router.get(
    "/featured",
    response_model=list[GalleryItem],
    summary="Top featured scenarios by view count",
)
async def get_featured(
    limit: int = Query(6, ge=1, le=20),
) -> list[GalleryItem]:
    def _q() -> list[dict]:
        from app.models import GalleryScenario
        rows = (
            GalleryScenario.query
            .filter(GalleryScenario.is_featured.is_(True))
            .order_by(GalleryScenario.views.desc())
            .limit(limit)
            .all()
        )
        return [s.to_dict() for s in rows]
    rows = await run_in_flask_db(_q)
    return [GalleryItem.model_validate(r) for r in rows]


# ── GET /{id} ──────────────────────────────────────────────────────────────

@router.get(
    "/{scenario_id}",
    response_model=GalleryDetail,
    summary="Fetch a single scenario (increments the view counter)",
)
async def get_scenario(scenario_id: int) -> GalleryDetail:
    def _q() -> dict | None:
        from app import db
        from app.models import GalleryScenario
        scenario = db.session.get(GalleryScenario, scenario_id)
        if scenario is None:
            return None
        scenario.views += 1
        db.session.commit()
        return scenario.to_dict(include_params=True)
    row = await run_in_flask_db(_q)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    return GalleryDetail.model_validate(row)


# ── GET / ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=GalleryPage,
    summary="Paginated gallery list",
    response_description="Items + total + page metadata.",
)
async def list_gallery(
    page:     int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    sort:     str = Query("recent",
                          description="'recent' | 'popular' | 'featured'"),
    tag:      str = Query("",
                          description="Filter by exact tag (case-sensitive)."),
) -> GalleryPage:
    def _q() -> dict:
        from sqlalchemy import cast, Text
        from app.models import GalleryScenario

        query = GalleryScenario.query
        if tag:
            safe = tag.replace('"', '').replace("'", "")[:50]
            query = query.filter(
                cast(GalleryScenario.tags, Text).like(f'%"{safe}"%')
            )

        if sort == "popular":
            query = query.order_by(
                GalleryScenario.views.desc(),
                GalleryScenario.created_at.desc(),
            )
        elif sort == "featured":
            query = (query
                     .filter(GalleryScenario.is_featured.is_(True))
                     .order_by(GalleryScenario.views.desc()))
        else:
            query = query.order_by(GalleryScenario.created_at.desc())

        total = query.count()
        rows  = query.offset((page - 1) * per_page).limit(per_page).all()
        pages = max(1, (total + per_page - 1) // per_page)
        return {
            "items":    [s.to_dict() for s in rows],
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "pages":    pages,
        }

    payload = await run_in_flask_db(_q)
    return GalleryPage.model_validate(payload)


# ── POST / ─────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=GalleryDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a scenario to the public gallery",
    response_description="The freshly created scenario including its id.",
)
async def create_gallery_scenario(
    request: GalleryCreateRequest,
) -> GalleryDetail:
    """No auth — the gallery is public. Featured flag stays False until
    an admin promotes the scenario directly in the database."""
    # Sanitise tags: cap at 10 entries × 50 chars; drop empty.
    clean_tags = [str(t)[:50] for t in request.tags if str(t).strip()][:10]

    def _create() -> dict:
        from app import db
        from app.models import GalleryScenario
        scenario = GalleryScenario(
            title=request.title,
            description=request.description,
            params=request.params,
            results_summary=request.results_summary,
            tags=clean_tags,
            is_featured=False,
        )
        db.session.add(scenario)
        db.session.commit()
        return scenario.to_dict(include_params=True)

    row = await run_in_flask_db(_create)
    return GalleryDetail.model_validate(row)
