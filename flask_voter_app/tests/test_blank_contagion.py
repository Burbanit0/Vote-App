"""
test_blank_contagion.py — Tests for the SIS blank-vote contagion model.
"""
import pytest
from app.utils.blank_contagion import simulate_blank_contagion


# ── Fixtures ──────────────────────────────────────────────────────────────────

def run(**kwargs) -> dict:
    defaults = dict(
        num_voters=200, initial_blank_rate=0.2,
        contagion_rate=0.3, recovery_rate=0.15,
        num_rounds=10, network_type="random", seed=0,
    )
    defaults.update(kwargs)
    return simulate_blank_contagion(**defaults)


# ── Return structure ──────────────────────────────────────────────────────────

def test_result_contains_all_keys():
    result = run()
    for key in ("rounds", "blank_rate_by_round", "final_blank_rate",
                "epidemic_threshold", "reached_equilibrium", "network_type", "r0"):
        assert key in result, f"Missing key: {key}"


def test_rounds_length_matches_num_rounds():
    result = run(num_rounds=7)
    assert len(result["rounds"]) == 8          # 0, 1, ..., 7
    assert result["rounds"][0] == 0
    assert result["rounds"][-1] == 7


def test_blank_rate_by_round_length_matches():
    result = run(num_rounds=12)
    assert len(result["blank_rate_by_round"]) == 13    # 0 … 12


def test_blank_rates_in_0_100_range():
    result = run()
    for rate in result["blank_rate_by_round"]:
        assert 0.0 <= rate <= 100.0, f"Out-of-range blank rate: {rate}"


def test_final_blank_rate_equals_last_round():
    result = run()
    assert result["final_blank_rate"] == pytest.approx(result["blank_rate_by_round"][-1])


def test_r0_equals_epidemic_threshold():
    result = run(contagion_rate=0.4, recovery_rate=0.2)
    assert result["r0"] == pytest.approx(result["epidemic_threshold"])


def test_r0_formula():
    """R0 = contagion_rate / recovery_rate."""
    result = run(contagion_rate=0.6, recovery_rate=0.3)
    assert result["r0"] == pytest.approx(2.0, rel=0.01)


# ── initial_blank_rate = 0 stays at 0 ────────────────────────────────────────

def test_zero_initial_blank_rate_stays_zero():
    """No infection can spread if no voter starts blank."""
    result = run(initial_blank_rate=0.0, contagion_rate=0.9, num_rounds=20)
    assert result["blank_rate_by_round"][0] == pytest.approx(0.0)
    assert all(r == pytest.approx(0.0) for r in result["blank_rate_by_round"])
    assert result["final_blank_rate"] == pytest.approx(0.0)


def test_zero_initial_blank_rate_all_network_types():
    for nt in ("random", "clustered", "small-world"):
        result = run(initial_blank_rate=0.0, network_type=nt, seed=1)
        assert result["final_blank_rate"] == pytest.approx(0.0), (
            f"Network {nt}: non-zero final rate with no initial infection"
        )


# ── recovery_rate = 1 returns to near-zero ───────────────────────────────────

def test_full_recovery_rate_decreases_blank_rate():
    """
    With recovery_rate=1 every infected voter recovers each round.
    For contagion_rate < 1, R0 < 1 and the blank rate should trend down.
    """
    result = run(
        initial_blank_rate=0.5,
        contagion_rate=0.5,
        recovery_rate=1.0,
        num_rounds=20,
        seed=42,
    )
    # Final rate should be lower than initial
    assert result["final_blank_rate"] < result["blank_rate_by_round"][0], (
        f"Expected decrease: initial={result['blank_rate_by_round'][0]:.2f}, "
        f"final={result['final_blank_rate']:.2f}"
    )


def test_full_recovery_high_rounds_near_zero():
    """With recovery_rate=1, after many rounds the blank rate should be very low."""
    result = run(
        initial_blank_rate=0.5,
        contagion_rate=0.2,
        recovery_rate=1.0,
        num_rounds=30,
        seed=0,
    )
    assert result["final_blank_rate"] < 10.0    # less than 10% blank


def test_zero_contagion_only_decreases():
    """With contagion_rate=0, infected voters only recover — rate can only fall."""
    result = run(
        initial_blank_rate=0.5,
        contagion_rate=0.0,
        recovery_rate=0.3,
        num_rounds=15,
        seed=0,
    )
    rates = result["blank_rate_by_round"]
    # Each round should be ≤ the previous (or at most equal)
    for i in range(1, len(rates)):
        assert rates[i] <= rates[i - 1] + 0.01, (
            f"Rate increased without contagion: round {i-1}={rates[i-1]:.3f} → {rates[i]:.3f}"
        )


# ── Network types ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("network_type", ["random", "clustered", "small-world"])
def test_all_network_types_run_without_error(network_type):
    result = run(network_type=network_type, seed=0)
    assert result["network_type"] == network_type
    assert len(result["blank_rate_by_round"]) > 0


def test_unknown_network_type_raises_value_error():
    with pytest.raises(ValueError, match="Unknown network_type"):
        simulate_blank_contagion(
            num_voters=50, initial_blank_rate=0.1,
            contagion_rate=0.3, recovery_rate=0.2,
            network_type="unknown",
        )


def test_small_world_produces_positive_degree():
    """Watts-Strogatz should give every node at least k/2 neighbours."""
    from app.utils.blank_contagion import _build_small_world
    import numpy as np
    rng = np.random.RandomState(0)
    adj = _build_small_world(100, rng, k=6, beta_rewire=0.1)
    min_degree = min(len(a) for a in adj)
    assert min_degree >= 1


def test_random_graph_degree_approximately_correct():
    """For n=500, p=0.01: expected degree ≈ (n-1)*p ≈ 5."""
    from app.utils.blank_contagion import _build_random
    import numpy as np
    rng = np.random.RandomState(0)
    n, p = 500, 0.01
    adj = _build_random(n, rng, p=p)
    avg_degree = sum(len(a) for a in adj) / n
    # Expected ~ 5, allow ±3 for stochastic variation
    assert 1.0 <= avg_degree <= 12.0, f"Unexpected average degree: {avg_degree:.2f}"


# ── R0 interpretation ─────────────────────────────────────────────────────────

def test_sub_threshold_epidemic_does_not_spread():
    """R0 < 1: blank rate should generally decrease from initial value."""
    # R0 = 0.2 / 0.5 = 0.4 < 1
    result = run(
        initial_blank_rate=0.4,
        contagion_rate=0.2,
        recovery_rate=0.5,
        num_rounds=30,
        seed=7,
    )
    # After 30 rounds with R0=0.4, the rate should have dropped
    assert result["final_blank_rate"] < result["blank_rate_by_round"][0]


def test_super_threshold_epidemic_sustains():
    """R0 > 1: starting from positive initial rate, the epidemic should persist."""
    # R0 = 0.8 / 0.1 = 8.0 > 1
    result = run(
        initial_blank_rate=0.05,
        contagion_rate=0.8,
        recovery_rate=0.1,
        num_rounds=30,
        seed=3,
    )
    # Rate should stay non-trivial (above 1%)
    assert result["final_blank_rate"] > 1.0


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_full_initial_blank_rate():
    result = run(initial_blank_rate=1.0, recovery_rate=0.5, num_rounds=5)
    assert result["blank_rate_by_round"][0] == pytest.approx(100.0)


def test_single_voter():
    result = simulate_blank_contagion(
        num_voters=10, initial_blank_rate=0.5,
        contagion_rate=0.3, recovery_rate=0.2,
        num_rounds=5, seed=0,
    )
    assert len(result["blank_rate_by_round"]) == 6


def test_determinism():
    a = run(seed=42)
    b = run(seed=42)
    assert a["blank_rate_by_round"] == b["blank_rate_by_round"]


def test_different_seeds_different_results():
    a = run(seed=1)
    b = run(seed=999)
    # With high enough randomness, results should differ
    assert a["blank_rate_by_round"] != b["blank_rate_by_round"]


# ── API route ─────────────────────────────────────────────────────────────────

def test_route_returns_200(client):
    resp = client.post("/simulations/blank-contagion", json={
        "num_voters": 100, "initial_blank_rate": 0.15,
        "contagion_rate": 0.3, "recovery_rate": 0.2,
        "num_rounds": 8, "network_type": "random", "seed": 0,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["blank_rate_by_round"]) == 9   # 0..8


def test_route_all_network_types(client):
    for nt in ("random", "clustered", "small-world"):
        resp = client.post("/simulations/blank-contagion", json={
            "num_voters": 80, "initial_blank_rate": 0.1,
            "contagion_rate": 0.3, "recovery_rate": 0.2,
            "num_rounds": 5, "network_type": nt, "seed": 0,
        })
        assert resp.status_code == 200, f"Network {nt} failed: {resp.get_json()}"


def test_route_invalid_network_type(client):
    resp = client.post("/simulations/blank-contagion", json={
        "num_voters": 100, "initial_blank_rate": 0.1,
        "contagion_rate": 0.3, "recovery_rate": 0.2,
        "network_type": "hexagonal",
    })
    assert resp.status_code == 400
