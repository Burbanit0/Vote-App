"""
Shared primitives used by multiple election/theory schemas.

Each model documents the field with `Field(description=...)` so the
generated OpenAPI spec carries real explanations into the frontend types.
"""
from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class CandidateSpec(BaseModel):
    """A single candidate placed at a 2D ideological position on [-1, 1]²."""
    model_config = ConfigDict(extra="forbid")

    name: str   = Field(..., min_length=1, max_length=64,
                        description="Candidate display name.")
    x:    float = Field(..., ge=-1.0, le=1.0,
                        description="Economy axis. -1 = far left, +1 = far right.")
    y:    float = Field(..., ge=-1.0, le=1.0,
                        description="Social axis. -1 = liberal, +1 = conservative.")


class ContagionConfig(BaseModel):
    """SIS-style blank-vote contagion parameters."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool  = Field(False, description="Whether contagion is applied.")
    beta:    float = Field(0.15, ge=0.0, le=1.0,
                           description="Infection rate β (probability of converting per neighbour).")
    gamma:   float = Field(0.10, ge=0.0, le=1.0,
                           description="Recovery rate γ.")
    network: str   = Field("random",
                           description="Network topology: 'random' | 'watts_strogatz' | 'block'.")


class BlankVoteConfig(BaseModel):
    """Constitutional blank-vote rule + optional contagion."""
    model_config = ConfigDict(extra="forbid")

    enabled:   bool             = Field(False, description="Apply the constitutional rule to the winner.")
    rule:      str              = Field("symbolic",
                                        description="'symbolic' | 'competitive' | 'threshold_30'.")
    contagion: ContagionConfig  = Field(default_factory=ContagionConfig)


class CampaignConfig(BaseModel):
    """Polling-bandwagon dynamics over a few days."""
    model_config = ConfigDict(extra="forbid")

    enabled:        bool  = Field(False, description="Apply campaign dynamics to true utilities.")
    num_days:       int   = Field(30, ge=7, le=60, description="Campaign length in days.")
    polling_effect: float = Field(0.3, ge=0.0, le=1.0,
                                  description="0 = ignore polls, 1 = ballots follow polls.")


class InformationModelConfig(BaseModel):
    """Media bias × voter information level adjustment of perceived utilities."""
    model_config = ConfigDict(extra="forbid")

    enabled:        bool                       = Field(False, description="Apply information asymmetry.")
    media_bias:     Dict[str, float]           = Field(default_factory=dict,
                                                       description="Per-candidate media bias [-1, +1].")
    voter_segments: Dict[str, float]           = Field(
        default_factory=lambda: {"low_info": 0.3, "medium_info": 0.5, "high_info": 0.2},
        description="Share of voters in each information bucket. Sums should be ~1.",
    )


# ── Result-side primitives ──────────────────────────────────────────────────

class MethodResult(BaseModel):
    """Result of a single voting method on one electorate."""
    model_config = ConfigDict(extra="allow")  # allow method-specific extras (mj_scores, ev_distribution, ...)

    winner:               Optional[str]   = Field(None, description="Method winner.")
    bayesian_regret:      Optional[float] = Field(None, description="Lower = better welfare.")
    majority_satisfaction: Optional[float] = Field(None, description="Share of voters satisfied (0..1).")
    condorcet_consistent: Optional[bool]  = Field(None, description="Did the method elect the Condorcet winner?")
    winner_with_blank:    Optional[str]   = Field(None,
                                                  description="Winner after blank-vote rule (if enabled).")
    blank_triggered:      Optional[bool]  = Field(None,
                                                  description="Did the blank-vote rule fire?")


class CandidateSnapshot(BaseModel):
    """Candidate as returned in /simulate (with derived party label)."""
    model_config = ConfigDict(extra="forbid")

    name:  str
    x:     float
    y:     float
    party: str


class VoterSnapshot(BaseModel):
    """One voter row in the ideology map."""
    model_config = ConfigDict(extra="forbid")

    id:                     int
    x:                      float
    y:                      float
    blank_threshold_final:  float
