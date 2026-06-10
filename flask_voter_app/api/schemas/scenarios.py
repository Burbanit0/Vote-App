"""
Pydantic schemas for /api/scenarios CRUD.

These mirror the existing `SimulationScenario.to_summary()` /
`to_detail()` shapes so the v2 routes return exactly what the v1
routes return — no frontend changes beyond the URL switch.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScenarioCreateRequest(BaseModel):
    """Body for POST /scenarios — name + config + optional results."""
    model_config = ConfigDict(extra="forbid")

    name:    str            = Field(..., min_length=1, max_length=100)
    config:  Dict[str, Any] = Field(default_factory=dict,
                                    description="Election config snapshot — "
                                                "candidates, num_voters, ideology, "
                                                "blank_vote, campaign, etc.")
    results: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional cached results from the last simulation run on "
                    "this config. Null means 'never simulated yet'.",
    )


class ScenarioSummary(BaseModel):
    """List view — matches `SimulationScenario.to_summary()`."""
    id:         int
    name:       str
    created_at: Optional[datetime] = None
    config:     Dict[str, Any]


class ScenarioDetail(ScenarioSummary):
    """Single view — adds the results blob."""
    results: Optional[Dict[str, Any]] = None
