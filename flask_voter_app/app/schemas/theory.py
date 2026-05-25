"""
Pydantic schemas for /api/theory/* endpoints.

Phase 4 batch 1: arrow / iia-rate / plott-chaos / judgment-aggregation.

Responses ARE typed (unlike most perturbers in Phase 3) because the
theory endpoints have stable, well-defined output shapes that the
frontend pedagogical text depends on. Where a sub-object is deeply
heterogeneous (e.g. axiom counterexamples), we keep it as
`Dict[str, Any]` — strict request validation is still the main win.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── /arrow ──────────────────────────────────────────────────────────────────

class ArrowRequest(BaseModel):
    """Per-method Arrow axiom violation analysis."""
    model_config = ConfigDict(extra="forbid")

    method: str = Field("plurality",
                        description="One of plurality | borda | irv | schulze | "
                                    "condorcet | approval | majority_judgment | "
                                    "kemeny_young | minimax | star_voting | two_round.")
    seed:   int = Field(42, ge=0)


class ArrowViolation(BaseModel):
    """One axiom: was it violated, and if so what's the counterexample."""
    violated:       bool
    counterexample: Optional[Dict[str, Any]] = None


class ArrowViolations(BaseModel):
    iia:               ArrowViolation
    pareto:            ArrowViolation
    transitivity:      ArrowViolation
    non_dictatorship:  ArrowViolation


class ArrowResponse(BaseModel):
    method:        str
    violations:    ArrowViolations
    arrow_summary: str
    tradeoff_type: str = Field(
        description="majority_focus | utility_focus | condorcet_focus.",
    )


# ── /iia-rate ───────────────────────────────────────────────────────────────

class IIARateRequest(BaseModel):
    """Empirical IIA violation rate vs number of candidates."""
    model_config = ConfigDict(extra="forbid")

    method:         str = Field("plurality")
    max_candidates: int = Field(8, ge=2, le=8)
    num_trials:     int = Field(100, ge=20, le=500)
    seed:           int = Field(42, ge=0)


class IIARatePoint(BaseModel):
    n_candidates:   int
    violation_rate: float = Field(..., ge=0.0, le=1.0)


class IIARateResponse(BaseModel):
    method: str
    curve:  List[IIARatePoint]


# ── /plott-chaos ────────────────────────────────────────────────────────────

class PlottChaosRequest(BaseModel):
    """Plott's Chaos Theorem in 2-D policy space."""
    model_config = ConfigDict(extra="forbid")

    num_voters:     int   = Field(5, ge=3, le=21)
    num_dimensions: int   = Field(2, ge=1, le=2)
    seed:           int   = Field(42, ge=0)
    target_policy:  List[float] = Field(default_factory=lambda: [0.6, 0.6],
                                        min_length=1, max_length=2)
    start_policy:   List[float] = Field(default_factory=lambda: [-0.6, -0.6],
                                        min_length=1, max_length=2)
    max_steps:      int   = Field(15, ge=1, le=30)


class TopCycle(BaseModel):
    size:   int
    center: List[float]


class ChaosPath(BaseModel):
    from_:     List[float] = Field(..., alias="from")
    to:        List[float]
    steps:     List[List[float]]
    num_steps: int

    model_config = ConfigDict(populate_by_name=True)


class AlternativePath(BaseModel):
    to:    List[float]
    steps: List[List[float]]


class PlottChaosResponse(BaseModel):
    condorcet_winner_exists: bool
    top_cycle:               TopCycle
    chaos_path:              ChaosPath
    alternative_path:        AlternativePath
    voter_ideal_points:      List[List[float]]
    pedagogical_note:        str


# ── /judgment-aggregation ──────────────────────────────────────────────────

class JudgmentAggregationRequest(BaseModel):
    """Discursive dilemma (List & Pettit 2002)."""
    model_config = ConfigDict(extra="forbid")

    num_voters: int = Field(12, ge=1, le=100)
    seed:       int = Field(42, ge=0)
    scenario:   str = Field("legal",
                            description="One of legal | budget | climate.")


class JAProposition(BaseModel):
    text:            str
    type:            str = Field(description="'premise' | 'conclusion'.")
    id:              str
    yes_pct:         float = Field(..., ge=0.0, le=1.0)
    collective_vote: bool


class JAIncoherence(BaseModel):
    premises:   List[str]
    conclusion: str
    problem:    str


class JAResolutionMethods(BaseModel):
    premise_based:    Dict[str, Any] = Field(default_factory=dict)
    conclusion_based: Dict[str, Any] = Field(default_factory=dict)


class JudgmentAggregationResponse(BaseModel):
    scenario:               str
    scenario_name:          str
    propositions:           List[JAProposition]
    collective_coherent:    bool
    incoherences:           List[JAIncoherence]
    voter_coherence_rate:   float = Field(..., ge=0.0, le=1.0)
    paradox_severity:       float = Field(..., ge=0.0, le=1.0)
    resolution_methods:     JAResolutionMethods
    pedagogical_note:       str
