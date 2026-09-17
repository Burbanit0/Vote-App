"""
Pydantic schemas for /api/tech/* — Tech-democracy pedagogical demos.

Response shapes are large + heterogeneous (PCA coords, k-means cluster
labels, statement-by-statement consensus matrices, …); same pattern
as the Phase 3 perturbers — pin the request shape with Pydantic,
pass the response through as Dict[str, Any].
"""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import CandidateSpec


class PolisWithCandidatesRequest(BaseModel):
    """Pol.is clustering + classical election cross-comparison."""
    model_config = ConfigDict(extra="forbid")

    candidates:              List[CandidateSpec] = Field(..., min_length=2, max_length=8)
    statements:              Optional[List[str]] = Field(None, max_length=15)
    num_participants:        int   = Field(100, ge=20, le=500)
    ideology:                str   = Field("random")
    seed:                    int   = Field(42, ge=0)
    num_clusters:            int   = Field(3, ge=1, le=5)
    method_to_compare:       str   = Field("plurality")
    min_consensus_threshold: float = Field(0.80, ge=0.0, le=1.0)


# ── Response models (Phase 6) ─────────────────────────────────────────────────
# Top-level keys taken from each worker's return literal; nested PCA/cluster/
# ballot structures stay loose (`Any`) and winner fields are Optional so
# `model_validate` never raises. `extra="allow"` carries any extra field.


class PolisWithCandidatesResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    clusters:               Any
    statements:             Any
    participant_positions:  Any
    polis_winner:           Optional[str] = None
    election_winner:        Optional[str] = None
    winners_agree:          bool
    consensus_count:        int
    polarizing_count:       int
    silent_majority_count:  int
    candidate_scores:       Any
    pedagogical_note:       str
