"""
test_campaign_dynamics.py — Tests for the campaign simulation utility and route.
"""
import pytest
from app.utils.campaign_dynamics import simulate_campaign, _apply_event, _softmax


# ── _apply_event ──────────────────────────────────────────────────────────────

def test_scandal_lowers_utility():
    assert _apply_event(0.6, "scandal", 0.3) == pytest.approx(0.3)

def test_gaffe_applies_fixed_penalty():
    assert _apply_event(0.5, "gaffe", 0.99) == pytest.approx(0.4)

def test_good_debate_raises_utility():
    assert _apply_event(0.5, "good_debate", 0.2) == pytest.approx(0.7)

def test_utility_capped_at_095():
    assert _apply_event(0.9, "good_debate", 0.5) == pytest.approx(0.95)

def test_utility_floor_at_005():
    assert _apply_event(0.1, "scandal", 0.9) == pytest.approx(0.05)


# ── _softmax ──────────────────────────────────────────────────────────────────

def test_softmax_sums_to_one():
    result = _softmax([0.3, 0.5, 0.2])
    assert sum(result) == pytest.approx(1.0)

def test_softmax_preserves_order():
    result = _softmax([0.1, 0.8, 0.5])
    assert result[1] > result[2] > result[0]


# ── simulate_campaign — structure ─────────────────────────────────────────────

def test_returns_all_required_keys():
    result = simulate_campaign(3, 100, 5, [], seed=0)
    for key in ("days", "daily_leader", "daily_scores", "events", "final_winner", "lead_changes", "candidates"):
        assert key in result, f"Missing key: {key}"

def test_days_list_length():
    result = simulate_campaign(3, 100, 7, [], seed=1)
    assert len(result["days"]) == 8          # 0 … 7  (num_days + 1 entries)
    assert result["days"][0] == 0
    assert result["days"][-1] == 7

def test_daily_scores_length_matches_days():
    result = simulate_campaign(3, 100, 10, [], seed=2)
    for name in result["candidates"]:
        assert len(result["daily_scores"][name]) == len(result["days"])

def test_daily_leader_length_matches_days():
    result = simulate_campaign(4, 100, 10, [], seed=3)
    assert len(result["daily_leader"]) == len(result["days"])

def test_lead_changes_non_negative():
    result = simulate_campaign(3, 100, 20, [], seed=4)
    assert result["lead_changes"] >= 0

def test_final_winner_is_last_daily_leader():
    result = simulate_campaign(3, 100, 10, [], seed=5)
    assert result["final_winner"] == result["daily_leader"][-1]

def test_all_leaders_are_valid_candidates():
    result = simulate_campaign(4, 100, 15, [], seed=6)
    candidates = set(result["candidates"])
    for leader in result["daily_leader"]:
        assert leader in candidates

def test_scores_sum_approximately_100_each_day():
    result = simulate_campaign(4, 100, 5, [], seed=7)
    for day_idx in range(len(result["days"])):
        total = sum(result["daily_scores"][n][day_idx] for n in result["candidates"])
        assert total == pytest.approx(100.0, abs=0.5)


# ── num_days edge cases ───────────────────────────────────────────────────────

def test_num_days_1_returns_two_data_points():
    """num_days=1 → days=[0, 1] → 2 data points (start + end)."""
    result = simulate_campaign(2, 100, 1, [], seed=0)
    assert len(result["days"]) == 2
    assert result["days"] == [0, 1]

def test_num_days_1_has_valid_structure():
    result = simulate_campaign(2, 100, 1, [], seed=0)
    assert result["final_winner"] in result["candidates"]
    assert len(result["daily_leader"]) == 2

def test_num_days_capped_at_90():
    result = simulate_campaign(2, 50, 200, [], seed=0)   # 200 > cap of 90
    assert len(result["days"]) == 91   # 0 … 90


# ── 2-candidate case ──────────────────────────────────────────────────────────

def test_two_candidates_works():
    result = simulate_campaign(2, 100, 10, [], seed=0)
    assert len(result["candidates"]) == 2

def test_two_candidates_scores_sum_to_100():
    result = simulate_campaign(2, 50, 5, [], seed=0)
    for i in range(len(result["days"])):
        total = sum(result["daily_scores"][n][i] for n in result["candidates"])
        assert total == pytest.approx(100.0, abs=0.5)

def test_two_candidates_correct_names():
    result = simulate_campaign(2, 50, 5, [], seed=0)
    assert set(result["candidates"]) == {"Alice", "Bob"}


# ── Events affect scores in the correct direction ────────────────────────────

def test_scandal_lowers_candidate_score_on_event_day():
    """A scandal on Alice at day 0 must lower her score vs. the no-event baseline."""
    base    = simulate_campaign(3, 200, 10, [],                                      seed=42)
    scandal = simulate_campaign(3, 200, 10,
                                [{"day": 0, "type": "scandal", "candidate": 0, "magnitude": 0.4}],
                                seed=42)
    assert scandal["daily_scores"]["Alice"][0] < base["daily_scores"]["Alice"][0]

def test_good_debate_raises_candidate_score_on_event_day():
    """A good debate for Bob at day 0 must raise his score vs. the baseline."""
    base  = simulate_campaign(3, 200, 10, [],                                         seed=42)
    boost = simulate_campaign(3, 200, 10,
                              [{"day": 0, "type": "good_debate", "candidate": 1, "magnitude": 0.4}],
                              seed=42)
    assert boost["daily_scores"]["Bob"][0] > base["daily_scores"]["Bob"][0]

def test_gaffe_lowers_candidate_score():
    """A gaffe has a fixed negative effect."""
    base  = simulate_campaign(2, 200, 10, [],                           seed=10)
    gaffe = simulate_campaign(2, 200, 10,
                              [{"day": 0, "type": "gaffe", "candidate": 0, "magnitude": 0.0}],
                              seed=10)
    assert gaffe["daily_scores"]["Alice"][0] < base["daily_scores"]["Alice"][0]

def test_events_later_in_campaign_dont_affect_earlier_days():
    """An event at day 5 must not change scores at days 0–4."""
    base   = simulate_campaign(3, 200, 10, [],                                          seed=42)
    event5 = simulate_campaign(3, 200, 10,
                               [{"day": 5, "type": "scandal", "candidate": 0, "magnitude": 0.3}],
                               seed=42)
    for day_idx in range(5):
        assert event5["daily_scores"]["Alice"][day_idx] == pytest.approx(
            base["daily_scores"]["Alice"][day_idx], abs=1e-9
        )

def test_events_annotated_with_measured_impact():
    events = [{"day": 0, "type": "scandal", "candidate": 0, "magnitude": 0.3}]
    result = simulate_campaign(2, 50, 5, events, seed=0)
    assert "measured_impact" in result["events"][0]
    assert result["events"][0]["measured_impact"] < 0   # scandal → negative impact


# ── Multiple events ───────────────────────────────────────────────────────────

def test_multiple_events_on_same_day():
    events = [
        {"day": 2, "type": "scandal",    "candidate": 0, "magnitude": 0.2},
        {"day": 2, "type": "good_debate","candidate": 1, "magnitude": 0.2},
    ]
    result = simulate_campaign(3, 100, 10, events, seed=0)
    assert len(result["days"]) == 11
    assert result["events"] == [
        {**events[0], "measured_impact": pytest.approx(-0.2)},
        {**events[1], "measured_impact": pytest.approx(+0.2)},
    ]

def test_event_outside_num_days_is_clamped():
    """Event scheduled beyond num_days should be clamped to num_days."""
    events = [{"day": 999, "type": "scandal", "candidate": 0, "magnitude": 0.3}]
    result = simulate_campaign(2, 50, 5, events, seed=0)
    assert result is not None   # no error


# ── Different methods ────────────────────────────────────────────────────────

@pytest.mark.parametrize("method", ["plurality", "borda", "irv", "approval"])
def test_all_methods_return_valid_result(method):
    result = simulate_campaign(3, 100, 7, [], method=method, seed=0)
    assert result["final_winner"] in result["candidates"]
    assert len(result["daily_leader"]) == 8


# ── API route ─────────────────────────────────────────────────────────────────

def test_campaign_route_returns_200(client):
    resp = client.post("/simulations/campaign", json={
        "num_candidates": 3,
        "num_voters":     100,
        "num_days":       5,
        "method":         "plurality",
        "events":         [],
        "seed":           0,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "days" in data
    assert "daily_scores" in data
    assert "final_winner" in data

def test_campaign_route_with_events(client):
    events = [{"day": 2, "type": "scandal", "candidate": 0, "magnitude": 0.3}]
    resp = client.post("/simulations/campaign", json={
        "num_candidates": 3,
        "num_days":       10,
        "events":         events,
        "seed":           42,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["days"]) == 11

def test_campaign_route_invalid_events(client):
    resp = client.post("/simulations/campaign", json={"events": "not-a-list"})
    assert resp.status_code == 400

def test_campaign_route_num_days_capped(client):
    resp = client.post("/simulations/campaign", json={
        "num_days": 200,    # exceeds cap of 90
        "events":   [],
        "seed":     0,
    })
    assert resp.status_code == 200
    assert len(resp.get_json()["days"]) == 91
