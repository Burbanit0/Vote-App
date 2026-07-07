"""
Pydantic schemas for /api/export — research dataset CSV / JSON generation.
"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class ExportDatasetRequest(BaseModel):
    """Shared body for both /simulation-dataset and /simulation-dataset-json."""
    model_config = ConfigDict(extra="forbid")

    num_scenarios:  int = Field(100, ge=1,  le=1_000)
    num_candidates: int = Field(4,   ge=2,  le=8)
    num_voters:     int = Field(500, ge=10, le=2_000)
    seed:           int = Field(42,  ge=0)
    ideology:       str = Field("random")


class ExportDatasetMeta(BaseModel):
    num_scenarios:  int
    num_candidates: int
    num_voters:     int
    seed:           int
    ideology:       str
    total_rows:     int


class ExportDatasetJSON(BaseModel):
    """Body of the JSON export endpoint."""
    meta:    ExportDatasetMeta
    columns: List[str]
    rows:    List[Dict[str, Any]]
