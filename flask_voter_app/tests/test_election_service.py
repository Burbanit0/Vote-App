"""Direct unit tests for ElectionService — proves the service is decoupled
from Flask and callable from any entry point (CLI, batch, test, future
WebSocket handlers, etc.) without an app context."""
from app.services.election_service import ElectionService


def _baseline_payload() -> dict:
    """A minimal valid input that exercises the happy path."""
    return {
        "num_voters": 30,
        "ideology":   "random",
        "seed":       42,
        "candidates": [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
            {"name": "Carol", "x":  0.0, "y":  0.3},
        ],
    }


# ── Contract checks (no Flask, no app context) ──────────────────────────────

def test_simulate_returns_body_and_status():
    body, status = ElectionService.simulate(_baseline_payload())
    assert status == 200
    assert isinstance(body, dict)


def test_simulate_response_has_expected_top_level_keys():
    body, _ = ElectionService.simulate(_baseline_payload())
    for key in (
        "config", "voters_snapshot", "candidates", "methods",
        "condorcet_winner", "blank_rate", "campaign_trajectory",
        "inter_method_agreement", "condorcet_exists",
    ):
        assert key in body, f"missing key: {key}"


def test_simulate_runs_all_voting_methods():
    body, _ = ElectionService.simulate(_baseline_payload())
    methods = body["methods"]
    assert len(methods) >= 5, f"expected ≥5 methods, got {list(methods)}"
    for md in methods.values():
        assert "winner" in md


def test_simulate_is_deterministic_for_same_seed():
    a, _ = ElectionService.simulate(_baseline_payload())
    b, _ = ElectionService.simulate(_baseline_payload())
    assert a["methods"] == b["methods"]
    assert a["voters_snapshot"] == b["voters_snapshot"]


def test_simulate_returns_400_for_one_candidate():
    payload = _baseline_payload()
    payload["candidates"] = [{"name": "Solo", "x": 0.0, "y": 0.0}]
    body, status = ElectionService.simulate(payload)
    assert status == 400
    assert "error" in body


def test_simulate_caps_candidates_at_single_winner_cap():
    """Should silently truncate the input list to SINGLE_WINNER_CAP (8).
    Sends 12 candidates with the SAME positions used by the existing France 2002
    scenario (which test_election_simulate exercises in the route suite)."""
    payload = _baseline_payload()
    payload["candidates"] = [
        {"name": "Chirac",      "x":  0.3, "y":  0.4},
        {"name": "Jospin",      "x": -0.4, "y": -0.3},
        {"name": "Le Pen",      "x":  0.8, "y":  0.8},
        {"name": "Bayrou",      "x":  0.1, "y":  0.1},
        {"name": "Chevènement", "x": -0.2, "y":  0.1},
        {"name": "Mégret",      "x":  0.9, "y":  0.9},
        {"name": "Taubira",     "x": -0.7, "y": -0.6},
        {"name": "Hue",         "x": -0.5, "y": -0.4},
        # Extras that should be truncated (beyond cap=8)
        {"name": "X1",          "x":  0.1, "y": -0.1},
        {"name": "X2",          "x": -0.1, "y":  0.2},
        {"name": "X3",          "x":  0.6, "y": -0.3},
        {"name": "X4",          "x": -0.3, "y":  0.5},
    ]
    body, status = ElectionService.simulate(payload)
    assert status == 200
    assert len(body["candidates"]) == 8


def test_simulate_clamps_num_voters_to_max():
    payload = _baseline_payload()
    payload["num_voters"] = 99_999
    body, status = ElectionService.simulate(payload)
    assert status == 200
    assert len(body["voters_snapshot"]) == 1000  # clamped


def test_simulate_with_blank_vote_enabled_returns_winner_with_blank():
    payload = _baseline_payload()
    payload["blank_vote"] = {"enabled": True, "rule": "symbolic"}
    body, _ = ElectionService.simulate(payload)
    for md in body["methods"].values():
        assert "winner_with_blank" in md
        assert "blank_triggered" in md


def test_simulate_with_campaign_returns_trajectory():
    payload = _baseline_payload()
    payload["campaign"] = {"enabled": True, "num_days": 14, "polling_effect": 0.3}
    body, _ = ElectionService.simulate(payload)
    assert body["campaign_trajectory"] is not None


def test_inter_method_agreement_is_between_0_and_1():
    body, _ = ElectionService.simulate(_baseline_payload())
    a = body["inter_method_agreement"]
    assert 0.0 <= a <= 1.0
