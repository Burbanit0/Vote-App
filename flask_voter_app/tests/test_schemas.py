"""
Tests for app.schemas — the Pydantic contracts introduced in Phase 1 of
the strategic refactor.

These tests freeze the API contract so we catch any unintended drift when
the routes themselves are refactored in Phase 3 (extraction to FastAPI).
"""
import pytest
from pydantic import ValidationError

from app.schemas import (
    AbstentionRequest,
    CampaignSensitivityRequest,
    CoalitionRequest,
    CombinedEffectsRequest,
    SimulateRequest,
    SimulateResponse,
)
from app.schemas.common import (
    BlankVoteConfig,
    CandidateSpec,
    ContagionConfig,
)


# ── CandidateSpec ────────────────────────────────────────────────────────────

class TestCandidateSpec:
    def test_minimum_valid(self):
        c = CandidateSpec(name="Alice", x=0.0, y=0.0)
        assert c.name == "Alice"

    def test_rejects_x_out_of_range(self):
        with pytest.raises(ValidationError):
            CandidateSpec(name="X", x=1.5, y=0.0)

    def test_rejects_y_out_of_range(self):
        with pytest.raises(ValidationError):
            CandidateSpec(name="X", x=0.0, y=-2.0)

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            CandidateSpec(name="", x=0.0, y=0.0)

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            CandidateSpec(name="X", x=0.0, y=0.0, party="Liberal")


# ── BlankVoteConfig + ContagionConfig defaults ──────────────────────────────

class TestBlankVoteConfig:
    def test_default_disabled(self):
        c = BlankVoteConfig()
        assert c.enabled is False
        assert c.rule == "symbolic"
        assert c.contagion.enabled is False

    def test_contagion_clamps_via_validation(self):
        with pytest.raises(ValidationError):
            ContagionConfig(beta=1.5)
        with pytest.raises(ValidationError):
            ContagionConfig(gamma=-0.1)


# ── SimulateRequest ──────────────────────────────────────────────────────────

BASE_CANDS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.3},
]


class TestSimulateRequest:
    def test_minimum_valid_payload(self):
        req = SimulateRequest(candidates=BASE_CANDS)
        assert req.num_voters == 300
        assert req.ideology == "random"
        assert req.seed == 42
        assert req.blank_vote.enabled is False

    def test_rejects_single_candidate(self):
        with pytest.raises(ValidationError) as exc:
            SimulateRequest(candidates=[BASE_CANDS[0]])
        assert "at least 2" in str(exc.value).lower()

    def test_rejects_more_than_8_candidates(self):
        many = [{"name": f"C{i}", "x": 0.0, "y": 0.0} for i in range(9)]
        with pytest.raises(ValidationError):
            SimulateRequest(candidates=many)

    def test_clamps_num_voters_via_validation(self):
        with pytest.raises(ValidationError):
            SimulateRequest(candidates=BASE_CANDS, num_voters=99_999)
        with pytest.raises(ValidationError):
            SimulateRequest(candidates=BASE_CANDS, num_voters=5)

    def test_accepts_full_payload(self):
        req = SimulateRequest(
            candidates=BASE_CANDS,
            num_voters=200,
            ideology="centrist",
            seed=7,
            blank_vote={"enabled": True, "rule": "competitive",
                        "contagion": {"enabled": True, "beta": 0.2, "gamma": 0.05, "network": "watts_strogatz"}},
            campaign={"enabled": True, "num_days": 14, "polling_effect": 0.5},
            information_model={"enabled": True, "media_bias": {"Alice": 0.3}},
        )
        assert req.blank_vote.contagion.beta == 0.2
        assert req.campaign.num_days == 14


# ── CombinedEffects / CampaignSensitivity / Abstention / Coalition ──────────

class TestOtherRequests:
    def test_combined_effects_caps_at_200_voters(self):
        with pytest.raises(ValidationError):
            CombinedEffectsRequest(candidates=BASE_CANDS, num_voters=201)
        ok = CombinedEffectsRequest(candidates=BASE_CANDS, num_voters=200)
        assert ok.num_voters == 200

    def test_campaign_sensitivity_accepts_mixed_snapshot_days(self):
        req = CampaignSensitivityRequest(
            candidates=BASE_CANDS,
            snapshot_days=[0, 7, 14, 21, 28, "final"],
        )
        assert req.snapshot_days == [0, 7, 14, 21, 28, "final"]

    def test_abstention_rejects_negative_factors(self):
        with pytest.raises(ValidationError):
            AbstentionRequest(candidates=BASE_CANDS, demobilization_factor=-0.1)
        with pytest.raises(ValidationError):
            AbstentionRequest(candidates=BASE_CANDS, poll_influence=1.5)

    def test_coalition_government_threshold_bounds(self):
        # government_threshold must be in [0, 1] — values outside that range
        # are rejected at the schema level.
        with pytest.raises(ValidationError):
            CoalitionRequest(candidates=BASE_CANDS, government_threshold=1.5)
        with pytest.raises(ValidationError):
            CoalitionRequest(candidates=BASE_CANDS, government_threshold=-0.1)
        ok = CoalitionRequest(candidates=BASE_CANDS, government_threshold=0.66)
        assert ok.government_threshold == 0.66

    def test_coalition_total_seats_default(self):
        req = CoalitionRequest(candidates=BASE_CANDS)
        assert req.total_seats == 100
        assert req.government_threshold == 0.5


# ── SimulateResponse round-trip ─────────────────────────────────────────────

class TestSimulateResponse:
    def test_parses_a_realistic_payload(self):
        payload = {
            "config": {"foo": "bar"},
            "voters_snapshot": [
                {"id": 0, "x": 0.1, "y": -0.2, "blank_threshold_final": 0.5}
            ],
            "candidates": [
                {"name": "Alice", "x": -0.5, "y": -0.2, "party": "Liberal"}
            ],
            "methods": {
                "plurality": {
                    "winner": "Alice",
                    "bayesian_regret": 0.18,
                    "majority_satisfaction": 0.72,
                    "condorcet_consistent": True,
                }
            },
            "condorcet_winner": "Alice",
            "blank_rate": 0.05,
            "campaign_trajectory": None,
            "inter_method_agreement": 0.85,
            "condorcet_exists": True,
        }
        resp = SimulateResponse.model_validate(payload)
        assert resp.condorcet_winner == "Alice"
        assert resp.methods["plurality"].winner == "Alice"
