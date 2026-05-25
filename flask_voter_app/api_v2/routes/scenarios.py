"""
api_v2/routes/scenarios.py — Saved-simulation CRUD.

Mirrors the Flask blueprint in `app/routes/scenarios.py` route-for-route.
JWT auth is validated by `api_v2.core.auth.current_user_id`, which
accepts the same Bearer tokens issued by Flask-JWT-Extended on the
Flask side. DB access goes through `api_v2.core.db.run_in_flask_db`
so we reuse the existing `SimulationScenario` model.

When Phase 4.3 migrates auth to fastapi-users and Phase 4.5 retires
Flask, this file's imports change but the route shapes stay identical.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from typing import List

from app.schemas import (
    ScenarioCreateRequest,
    ScenarioDetail,
    ScenarioSummary,
)
from api_v2.core.auth import CurrentUserId
from api_v2.core.db import run_in_flask_db

router = APIRouter(prefix="/api/v2/scenarios", tags=["scenarios"])


# ── GET / ───────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[ScenarioSummary],
    summary="List the current user's saved scenarios",
    response_description="Most recently created first.",
)
async def list_scenarios(user_id: CurrentUserId) -> List[ScenarioSummary]:
    """Returns the user's saved scenarios, newest first. Empty list for
    new accounts."""
    def _query() -> List[dict]:
        from app import db                          # noqa: F401  (kept for clarity)
        from app.models import SimulationScenario
        scenarios = (
            SimulationScenario.query
            .filter_by(user_id=user_id)
            .order_by(SimulationScenario.created_at.desc())
            .all()
        )
        return [s.to_summary() for s in scenarios]

    rows = await run_in_flask_db(_query)
    return [ScenarioSummary.model_validate(r) for r in rows]


# ── POST / ──────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ScenarioDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Save a new scenario for the current user",
    response_description="The freshly created scenario including its server-assigned id.",
)
async def create_scenario(
    request: ScenarioCreateRequest,
    user_id: CurrentUserId,
) -> ScenarioDetail:
    """Persists a config snapshot (and optionally cached results) under
    the user's account."""
    def _create() -> dict:
        from app import db
        from app.models import SimulationScenario
        scenario = SimulationScenario(
            user_id=user_id,
            name=request.name,
            config=request.config,
            results=request.results,
        )
        db.session.add(scenario)
        db.session.commit()
        return scenario.to_detail()

    row = await run_in_flask_db(_create)
    return ScenarioDetail.model_validate(row)


# ── GET /{scenario_id} ──────────────────────────────────────────────────────

@router.get(
    "/{scenario_id}",
    response_model=ScenarioDetail,
    summary="Fetch a single scenario by id",
    response_description="404 if the scenario doesn't exist or belongs to another user.",
)
async def get_scenario(
    scenario_id: int,
    user_id: CurrentUserId,
) -> ScenarioDetail:
    """Per-user scoping is enforced in the WHERE clause — a user
    asking for someone else's scenario gets 404, not 403, to avoid
    leaking the existence of foreign ids."""
    def _query() -> dict | None:
        from app.models import SimulationScenario
        scenario = SimulationScenario.query.filter_by(
            id=scenario_id, user_id=user_id
        ).first()
        return scenario.to_detail() if scenario else None

    row = await run_in_flask_db(_query)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    return ScenarioDetail.model_validate(row)


# ── DELETE /{scenario_id} ───────────────────────────────────────────────────

@router.delete(
    "/{scenario_id}",
    summary="Delete one of the current user's scenarios",
    response_description="`{message: 'Deleted'}` on success, 404 otherwise.",
)
async def delete_scenario(
    scenario_id: int,
    user_id: CurrentUserId,
) -> dict:
    """Hard-deletes the row — same behaviour as the Flask side."""
    def _delete() -> bool:
        from app import db
        from app.models import SimulationScenario
        scenario = SimulationScenario.query.filter_by(
            id=scenario_id, user_id=user_id
        ).first()
        if not scenario:
            return False
        db.session.delete(scenario)
        db.session.commit()
        return True

    deleted = await run_in_flask_db(_delete)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    return {"message": "Deleted"}
