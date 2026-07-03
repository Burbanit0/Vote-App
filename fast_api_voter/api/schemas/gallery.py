"""
Pydantic schemas for the public scenario gallery (/api/scenarios/gallery).

Mirrors GalleryScenario.to_dict() so the v2 routes return exactly what the
v1 routes return — no frontend changes beyond the URL switch.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GalleryItem(BaseModel):
    """Summary view — what `/featured` and `/list` items look like."""
    id:              int
    title:           str
    description:     str
    tags:            List[str] = Field(default_factory=list)
    views:           int
    is_featured:     bool
    created_at:      Optional[datetime] = None
    results_summary: Dict[str, Any]     = Field(default_factory=dict)


class GalleryDetail(GalleryItem):
    """Detail view — adds the raw `params` blob."""
    params: Dict[str, Any] = Field(default_factory=dict)


class GalleryPage(BaseModel):
    """Pagination envelope returned by `GET /api/v2/scenarios/gallery`."""
    items:    List[GalleryItem]
    total:    int
    page:     int
    per_page: int
    pages:    int


class GalleryCreateRequest(BaseModel):
    """Body for `POST /api/v2/scenarios/gallery`."""
    model_config = ConfigDict(extra="forbid")

    title:           str            = Field(..., min_length=1, max_length=200)
    description:     str            = Field(..., min_length=1)
    params:          Dict[str, Any] = Field(default_factory=dict)
    results_summary: Dict[str, Any] = Field(default_factory=dict)
    tags:            List[str]      = Field(default_factory=list, max_length=10)
