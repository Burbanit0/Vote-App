"""
Pydantic schemas for /api/tech/* — Tech-democracy pedagogical demos.

Response shapes are large + heterogeneous (PCA coords, k-means cluster
labels, statement-by-statement consensus matrices, …); same pattern
as the Phase 3 perturbers — pin the request shape with Pydantic,
pass the response through as Dict[str, Any].
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

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


# ── Response models (Phase 6) ─────────────────────────────────────────────────
# Top-level keys taken from each worker's return literal; nested PCA/cluster/
# ballot structures stay loose (`Any`) and winner fields are Optional so
# `model_validate` never raises. `extra="allow"` carries any extra field.


class E2EDemoResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    voters:                    List[Any]
    public_bulletin_board:     Any
    aggregate_result:          Any
    winner:                    Optional[str] = None
    audit_proof:               Any
    num_voters:                int
    candidates:                List[Any]
    encrypted_ballots:         Any
    verification_demonstration: Any
    privacy_guarantee:         Any


class PolisSimulationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    clusters:              Any
    consensus_statements:  Any
    polarizing_statements: Any
    participant_positions: Any
    num_clusters:          int
    num_participants:      int


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
