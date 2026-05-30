"""
Pydantic schemas for /api/tech/* — Tech-democracy pedagogical demos.

Response shapes are large + heterogeneous (PCA coords, k-means cluster
labels, statement-by-statement consensus matrices, …); same pattern
as the Phase 3 perturbers — pin the request shape with Pydantic,
pass the response through as Dict[str, Any].
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import CandidateSpec


class E2EDemoRequest(BaseModel):
    """End-to-end verifiable voting pedagogical demo."""
    model_config = ConfigDict(extra="forbid")

    candidates:      List[str] = Field(default_factory=lambda: ["Alice", "Bob", "Carol"],
                                       min_length=2, max_length=8)
    # Both default to None so the worker's `num_demo_voters or num_voters or 10`
    # resolution sees whichever the client actually sent (the frontend sends
    # num_voters; older callers send num_demo_voters).
    num_voters:      Optional[int] = Field(None, ge=5, le=20)
    num_demo_voters: Optional[int] = Field(None, ge=5, le=20)
    seed:            int   = Field(42, ge=0)
    user_vote:       str   = Field("",
                                   description="If non-empty and present in candidates, voter #1's vote.")


class PolisSimulationRequest(BaseModel):
    """Pol.is consensus clustering on a fresh statement set."""
    model_config = ConfigDict(extra="forbid")

    statements:       Optional[List[str]] = Field(None, max_length=15,
                                                  description="Defaults to the built-in 10-statement battery.")
    num_participants: int = Field(100, ge=20, le=500)
    ideology:         str = Field("random")
    seed:             int = Field(42, ge=0)
    num_clusters:     int = Field(3, ge=1, le=5)


class PolisWithCandidatesRequest(BaseModel):
    """Pol.is clustering + classical election cross-comparison."""
    model_config = ConfigDict(extra="forbid")

    candidates:              List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    statements:              Optional[List[str]] = Field(None, max_length=15)
    num_participants:        int   = Field(100, ge=20, le=500)
    ideology:                str   = Field("random")
    seed:                    int   = Field(42, ge=0)
    num_clusters:            int   = Field(3, ge=1, le=5)
    method_to_compare:       str   = Field("plurality")
    min_consensus_threshold: float = Field(0.80, ge=0.0, le=1.0)
