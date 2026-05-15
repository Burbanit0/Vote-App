"""
types.py — Shared TypedDicts and type aliases for the Vote Lab backend.

Centralising these definitions avoids circular imports and keeps type
annotations consistent across the simulation pipeline.
"""
from typing import Any, Dict, List, Optional, TypedDict


# ── Candidate & Voter dicts ────────────────────────────────────────────────
# These are open-ended dicts assembled from several sources (demographic
# sampling, ideology model, etc.). Dict[str, Any] is the pragmatic choice;
# more granular TypedDicts can replace them as the codebase matures.

VoterDict = Dict[str, Any]
CandidateDict = Dict[str, Any]


# ── Blank-vote rule result ─────────────────────────────────────────────────

class BlankRuleResult(TypedDict):
    winner: Optional[str]
    blank_triggered: bool
    consequence: str
    blank_pct: float
    rule: str


# ── Per-method simulation metrics ─────────────────────────────────────────

class MethodMetrics(TypedDict, total=False):
    winner: Optional[str]
    bayesian_regret: Optional[float]
    condorcet_consistent: Optional[bool]
    majority_satisfaction: Optional[float]
    strategic_vulnerability: Optional[float]
    blank_rule_applied: BlankRuleResult


# ── Full compare_all_methods result ───────────────────────────────────────

class ComparisonResult(TypedDict, total=False):
    condorcet_winner: Optional[str]
    methods: Dict[str, MethodMetrics]
    blank_pct: Optional[float]


# ── Condorcet matrix duel cell ────────────────────────────────────────────

class DuelResult(TypedDict):
    pct_a: float
    pct_b: float
    winner: Optional[str]


# ── Real-election summary ─────────────────────────────────────────────────

class ElectionSummary(TypedDict):
    key: str
    name: str
    year: int
    country: str


# ── Divergence entry ──────────────────────────────────────────────────────

class DivergenceEntry(TypedDict):
    method: str
    winner: Optional[str]
    differs_from_plurality: bool


# ── Issue-priority return from assign_issue_priorities ───────────────────

class IssuePriorityResult(TypedDict):
    issue_priorities: Dict[str, float]
    political_lean: float
    issue_positions: Dict[str, float]


# ── Candidate config parsed from request body ─────────────────────────────

class CandidateConfig(TypedDict, total=False):
    id: int
    name: str
    party: str
    party_lean: float
    ideology_position: float
    policies: Dict[str, float]
    charisma: float
    scandals: int
    campaign_funds: int
    experience: int
    popularity: float


# ── Monte-Carlo method statistics ─────────────────────────────────────────

class MethodStats(TypedDict, total=False):
    winner_distribution: Dict[str, float]
    most_common_winner: Optional[str]
    winner_stability: float
    bayesian_regret_mean: Optional[float]
    bayesian_regret_std: Optional[float]
    bayesian_regret_ci_95: List[Optional[float]]
    majority_satisfaction_mean: Optional[float]
    majority_satisfaction_ci_95: List[Optional[float]]
    condorcet_compliance_rate: Optional[float]
