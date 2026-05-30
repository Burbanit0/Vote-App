"""
api/routes/scenarios.py — Saved-simulation CRUD (async, Phase 4.5.b.2).

JWT auth is validated by `api.core.auth.current_user_id` (accepts tokens from
both Flask-JWT-Extended and fastapi-users). Persistence uses the Flask-independent
async SQLAlchemy layer in `api.db` — no more `run_in_flask_db` bridge.
"""
from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.auth import CurrentUserId
from api.db import SimulationScenario
from api.db.session import get_async_session
from api.schemas import (
    ScenarioCreateRequest,
    ScenarioDetail,
    ScenarioSummary,
)

router = APIRouter(prefix="/api/v2/scenarios", tags=["scenarios"])

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


@router.get(
    "",
    response_model=List[ScenarioSummary],
    summary="List the current user's saved scenarios",
    response_description="Most recently created first.",
)
async def list_scenarios(user_id: CurrentUserId, db: DbSession) -> List[ScenarioSummary]:
    """Returns the user's saved scenarios, newest first. Empty list for new accounts."""
    result = await db.execute(
        select(SimulationScenario)
        .where(SimulationScenario.user_id == user_id)
        .order_by(SimulationScenario.created_at.desc())
    )
    return [ScenarioSummary.model_validate(s.to_summary()) for s in result.scalars()]


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
    db: DbSession,
) -> ScenarioDetail:
    """Persists a config snapshot (and optionally cached results) under the user's account."""
    scenario = SimulationScenario(
        user_id=user_id,
        name=request.name,
        config=request.config,
        results=request.results,
    )
    db.add(scenario)
    await db.commit()
    return ScenarioDetail.model_validate(scenario.to_detail())


@router.get(
    "/{scenario_id}",
    response_model=ScenarioDetail,
    summary="Fetch a single scenario by id",
    response_description="404 if the scenario doesn't exist or belongs to another user.",
)
async def get_scenario(
    scenario_id: int,
    user_id: CurrentUserId,
    db: DbSession,
) -> ScenarioDetail:
    """Per-user scoping is enforced in the WHERE clause — asking for someone
    else's scenario gets 404, not 403, to avoid leaking foreign ids."""
    scenario = await _owned_scenario(db, scenario_id, user_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ScenarioDetail.model_validate(scenario.to_detail())


@router.delete(
    "/{scenario_id}",
    summary="Delete one of the current user's scenarios",
    response_description="`{message: 'Deleted'}` on success, 404 otherwise.",
)
async def delete_scenario(
    scenario_id: int,
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Hard-deletes the row — same behaviour as the Flask side."""
    scenario = await _owned_scenario(db, scenario_id, user_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await db.delete(scenario)
    await db.commit()
    return {"message": "Deleted"}


async def _owned_scenario(
    db: AsyncSession, scenario_id: int, user_id: int
) -> Optional[SimulationScenario]:
    result = await db.execute(
        select(SimulationScenario).where(
            SimulationScenario.id == scenario_id,
            SimulationScenario.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()
