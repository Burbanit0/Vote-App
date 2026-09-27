"""Response schemas for /api/v2/polity/* — the run explorer.

Every model is `extra="forbid"`: these shapes are generated into the Vote App's
TypeScript types, and a field the frontend was never told about is a contract bug.
Per-citizen codes are typed as `Literal` unions, so the frontend's lenses switch over
exactly the codes the replay can produce (api/domain/polity/run_frames.py).
"""
from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

Scalar = Union[bool, int, float, str, None]
XY = List[float]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── /runs ──────────────────────────────────────────────────────────────────

class PolityRunSummary(_Model):
    key: str = Field(..., description="Stable run key: sha256 of the root label and the run's path inside it, 16 hex characters.")
    label: str = Field(..., description="The run root's label.")
    relative_path: str = Field(..., description="The run's directory inside its root.")
    run_id: str
    generation: str = Field(..., description="Which files the run carries: provenanced, checkpointed or journal_only.")
    engine: Optional[str] = Field(None, description="llm or deterministic.")
    outcome: Optional[str] = Field(None, description="The digest's outcome (completed, crashed, interrupted), when a digest exists.")
    population: Optional[int] = None
    years: Optional[int] = None
    seed: Optional[int] = None
    ticks_reached: Optional[int] = None
    ticks_planned: Optional[int] = None


class PolityRunList(_Model):
    runs: List[PolityRunSummary]


# ── /runs/{run_key} ────────────────────────────────────────────────────────

class PolityIssueWeight(_Model):
    issue: int = Field(..., description="0-indexed issue dimension.")
    weight: float = Field(..., description="Signed loading of the issue on the axis.")


class PolityCensusPositions(_Model):
    year: int
    xy: List[XY] = Field(..., description="One [x, y] per citizen, in citizen_id order.")


class PolityProjection(_Model):
    method: Literal["latent", "pca"] = Field(..., description="latent: the population's own two factors; pca: principal components of the tick-0 census.")
    positions: Literal["static", "yearly"] = Field(..., description="yearly: citizens move once a year, at each census (opinion dynamics).")
    axes: List[List[PolityIssueWeight]] = Field(..., description="For each of the two axes, the issues loading most on it.")
    citizens: List[PolityCensusPositions]


class PolityParty(_Model):
    party_id: int
    xy: XY


class PolityTerm(_Model):
    holder: int
    start_tick: int
    end_tick: int
    ended_by: str = Field(..., description="legitimacy_floor, confidence_vote, election or run_end.")
    lame_duck: bool
    mandate_strength: Optional[float] = None


class PolityTimelineEntry(_Model):
    tick: int
    event_type: str
    citizen_id: Optional[int] = None
    details: Dict[str, Scalar] = Field(..., description="The event payload's scalar fields.")


class PolityStanding(_Model):
    tick: int
    president: Optional[int] = None
    legitimacy: Optional[float] = None
    ecart: Optional[float] = None
    mandate_strength: Optional[float] = None
    acts: List[int] = Field(..., description="Pressure actions journaled this tick, counted by act code 0-4.")


class PolityElection(_Model):
    tick: int
    outcome: Literal["elected", "no_winner", "invalidated"]
    winner: Optional[int] = None
    forced: bool
    turnout: Optional[float] = Field(None, description="Share of the population casting a ballot; null when no vote was held or recorded.")
    blank_share: Optional[float] = None
    blank_source: Optional[Literal["invalidation_check", "ballots", "audit_sample"]] = Field(
        None, description="Where blank_share comes from; null when the journal holds no reading.")


class PolitySeats(_Model):
    party_id: int
    seats: int


class PolityLegislative(_Model):
    tick: int
    seats: List[PolitySeats]
    blank_rate: Optional[float] = None


class PolityMotif(_Model):
    code: int
    label: str


class PolityRunOverview(_Model):
    key: str
    label: str
    run_id: str
    population: int
    ticks_per_year: int
    last_tick: int
    last_checkpoint_tick: Optional[int] = None
    vote_coverage: Literal["all", "audit_sample", "none"] = Field(
        ..., description="all: every ballot journaled; audit_sample: only S4.1's audit ballots; none: no ballot journaled.")
    unknown_event_types: List[str]
    projection: PolityProjection
    parties: List[PolityParty]
    citizen_parties: List[Optional[int]] = Field(..., description="Each citizen's party, in citizen_id order.")
    terms: List[PolityTerm]
    timeline: List[PolityTimelineEntry]
    standings: List[PolityStanding]
    elections: List[PolityElection]
    legislative: List[PolityLegislative]
    motifs: List[PolityMotif]


# ── /runs/{run_key}/frames ─────────────────────────────────────────────────

class PolityPresident(_Model):
    citizen_id: int
    xy: XY = Field(..., description="Where the president's revealed position sits on the map.")
    pledged_xy: Optional[XY] = Field(None, description="Where their pledge sits.")
    legitimacy: Optional[float] = None
    ecart: Optional[float] = None
    mandate_strength: Optional[float] = None
    lame_duck: bool


class PolityFrame(_Model):
    tick: int
    partial: bool = Field(..., description="The tick ran after the last checkpoint: journaled, never confirmed.")
    status: List[Literal[0, 1, 2]] = Field(..., description="Per citizen: 0 elector, 1 candidate, 2 elected.")
    chamber: List[Literal[0, 1]] = Field(..., description="Per citizen: 1 when seated in the sortition chamber.")
    act: List[Literal[-1, 0, 1, 2, 3, 4]] = Field(..., description="Per citizen: the pressure act taken this tick, -1 for none.")
    vote: List[Literal[-1, 0, 1, 2]] = Field(..., description="Per citizen: -1 no journaled ballot, 0 blank, 1 for the winner, 2 for another candidate.")
    candidacy: List[Literal[-1, 0, 1, 2, 3, 4]] = Field(
        ..., description="Per citizen, the furthest stage reached this tick: -1 none, 0 declined, 1 declared, 2 nomination lost, 3 standing, 4 elected.")
    president: Optional[PolityPresident] = None


class PolityFrames(_Model):
    key: str
    from_tick: int
    to_tick: int
    frames: List[PolityFrame]


# ── /runs/{run_key}/citizens/{citizen_id} ──────────────────────────────────

class PolityBiographyEntry(_Model):
    tick: int
    event_type: str
    role: Literal["actor", "target", "listed"]
    motif: Optional[int] = None
    motif_label: Optional[str] = None
    rationale: Optional[str] = Field(None, description="The model's rationale, cut at 280 characters.")
    details: Dict[str, Scalar]


class PolityBiographySections(_Model):
    roles: List[PolityBiographyEntry]
    candidacies: List[PolityBiographyEntry]
    votes: List[PolityBiographyEntry]
    pressure_acts: List[PolityBiographyEntry]
    petitions: List[PolityBiographyEntry]
    other: List[PolityBiographyEntry]


class PolityReceived(_Model):
    tick: int
    event_type: str
    code: Optional[int] = Field(
        None, description="The pressure act, the rank ballots gave the citizen (0 = first choice), or the event reacted to (1 scandal, 2 economic shock); null for a signature.")
    count: int


class PolityCensusYear(_Model):
    year: int
    role: str
    office: str
    party: Optional[int] = None


class PolityCitizen(_Model):
    key: str
    citizen_id: int
    sections: PolityBiographySections
    received: List[PolityReceived]
    census: List[PolityCensusYear]
