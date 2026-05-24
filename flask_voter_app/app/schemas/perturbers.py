"""
Pydantic request schemas for the "Perturber" election endpoints
(nota / ballot-complexity / shy-voter / electoral-fatigue / cascade /
behavioral-biases / choice-overload / deliberation / ...).

Response schemas are intentionally NOT defined here. The v2 routes return
`Dict[str, Any]` and pass through the worker's output unchanged. The
reasons:

  1. Each perturber's response has 8-15 specific fields plus a curve
     and a method-comparison dict. Typing all of them strictly would
     mean 20 schemas, none of which would catch real bugs (the fields
     are computed values, not contract surfaces).
  2. The frontend already has TypeScript interfaces for these
     responses in the individual panel files — those types document
     the response shape sufficiently for the React side.
  3. Strict request validation (this module) catches the actually
     dangerous class of bug: client-side typos and out-of-range
     parameters that explode inside the worker.

When a panel migrates to TanStack Query (Phase 5 of the strategic
refactor), each response will get its own typed schema generated from
the worker's actual output shape.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import CandidateSpec


# ── /nota ────────────────────────────────────────────────────────────────────

class NotaRequest(BaseModel):
    """NOTA (None Of The Above) as an official ballot option."""
    model_config = ConfigDict(extra="forbid")

    candidates:     List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:     int   = Field(200, ge=50, le=500)
    ideology:       str   = Field("random")
    seed:           int   = Field(42, ge=0)
    nota_threshold: float = Field(0.3, ge=0.0, le=1.0,
                                  description="Minimum max-utility a voter needs for any candidate "
                                              "before they cast NOTA.")
    nota_rule:      str   = Field("invalidate",
                                  description="Constitutional response when NOTA wins: "
                                              "'invalidate' | 'runoff' | 'winner_take_all'.")
    method:         str   = Field("plurality",
                                  description="Primary method to display in the curve "
                                              "('plurality' | 'irv' | 'borda' | 'schulze' | ...).")


# ── /ballot-complexity ──────────────────────────────────────────────────────

class BallotComplexityRequest(BaseModel):
    """Ballot-complexity-driven null vote model."""
    model_config = ConfigDict(extra="forbid")

    candidates:           List[CandidateSpec] = Field(..., min_length=2, max_length=8)
    num_voters:           int   = Field(200, ge=50, le=500)
    ideology:             str   = Field("random")
    seed:                 int   = Field(42, ge=0)
    education_level:      float = Field(0.7, ge=0.0, le=1.0,
                                        description="Higher = lower null-vote rate.")
    first_time_voter_pct: float = Field(0.1, ge=0.0, le=1.0,
                                        description="Higher = higher null-vote rate.")
    methods_to_compare:   Optional[List[str]] = Field(
        None, max_length=8,
        description="Voting methods to compare. If None, uses the server default set.",
    )


# ── /shy-voter ──────────────────────────────────────────────────────────────

class ShyVoterRequest(BaseModel):
    """Bradley / Shy Tory effect: socially-sensitive candidates underpolled."""
    model_config = ConfigDict(extra="forbid")

    candidates:                 List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:                 int   = Field(300, ge=50, le=500)
    ideology:                   str   = Field("random")
    seed:                       int   = Field(42, ge=0)
    shy_candidate_idx:          int   = Field(0, ge=0, le=5,
                                              description="Index of the 'sensitive' candidate.")
    social_desirability_factor: float = Field(0.4, ge=0.0, le=1.0,
                                              description="Fraction of shy voters who lie in polls.")
    num_polls:                  int   = Field(10, ge=3, le=30)


# ── /electoral-fatigue ──────────────────────────────────────────────────────

class ElectoralFatigueRequest(BaseModel):
    """Turnout decay across repeated elections."""
    model_config = ConfigDict(extra="forbid")

    candidates:        List[CandidateSpec] = Field(..., min_length=2, max_length=6)
    num_voters:        int   = Field(200, ge=50, le=500)
    ideology:          str   = Field("random")
    seed:              int   = Field(42, ge=0)
    num_elections:     int   = Field(6, ge=1, le=12)
    fatigue_rate:      float = Field(0.07, ge=0.0, le=0.15,
                                     description="Per-election turnout drop (0.07 = 7 pp).")
    engaged_voter_pct: float = Field(0.2, ge=0.05, le=0.5,
                                     description="Share of always-voting partisans.")
    method:            str   = Field("plurality")
