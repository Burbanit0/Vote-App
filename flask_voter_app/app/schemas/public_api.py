"""
Pydantic request schemas for the Vote Lab Public Research API (/api/v1).

The public API keeps its `/api/v1` product-version URL even though it's
now served by FastAPI — external consumers depend on that path. Response
bodies stay loosely typed (Dict) because they expose the full
compare_all_methods output; the request shape is what we pin here.

Contract notes (mirror the legacy Flask behaviour exactly so we don't
break external clients):
  * `extra="ignore"` — unknown fields are tolerated, not rejected.
  * `num_voters` / `num_candidates` are NOT range-constrained here: the
    worker clamps them silently (50–2000 / 2–8) just like Flask did, so a
    huge value returns 200 with a capped run instead of a 422.
  * `methods` accepts the literal "all" string OR a list of method keys.
"""
from __future__ import annotations

from typing import List, Literal, Union

from pydantic import BaseModel, ConfigDict


class PublicSimulateRequest(BaseModel):
    """POST /api/v1/simulate."""
    model_config = ConfigDict(extra="ignore")

    num_candidates:        int = 4
    num_voters:            int = 500
    ideology_distribution: str = "random"
    methods:               Union[Literal["all"], List[str]] = "all"


class PublicCompareRequest(BaseModel):
    """POST /api/v1/compare."""
    model_config = ConfigDict(extra="ignore")

    num_candidates:        int = 4
    num_voters:            int = 500
    ideology_distribution: str = "random"
    blank_rule:            str = ""   # "" → blank vote disabled
    methods:               Union[Literal["all"], List[str]] = "all"
