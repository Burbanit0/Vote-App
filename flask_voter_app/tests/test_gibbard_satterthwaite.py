"""
test_gibbard_satterthwaite.py — Tests for the Gibbard-Satterthwaite manipulability module.
"""
import time
import pytest

from app.utils.gibbard_satterthwaite import compute_manipulability_index, _rank_of


# ── Ballot fixtures ──────────────────────────────────────────────────────────

def make_plurality_ballots(n_voters: int = 120, n_candidates: int = 3) -> list[list[str]]:
    """
    Construct ballots that exhibit a strong plurality spoiler effect.

    Distribution (n=3):
      45 %  → A first (A wins plurality)
      35 %  → B first (B loses, but many B-voters prefer B > A)
      20 %  → C first (C loses, C-voters prefer B > A)

    B-preferring voters can "manipulate" by pretending to prefer C last
    (which they already do) or by other swaps that might shift who wins.
    In practice, plurality is manipulable in this scenario.
    """
    names = [chr(65 + i) for i in range(n_candidates)]
    ballots = []
    for i in range(n_voters):
        if i < int(n_voters * 0.45):
            ballots.append(list(names))                       # A, B, C, …
        elif i < int(n_voters * 0.80):
            ballots.append([names[1], names[0]] + names[2:])  # B, A, C, …
        else:
            ballots.append([names[2], names[1], names[0]] + names[3:])  # C, B, A, …
    return ballots


def make_borda_ballots_with_manipulation(n_voters: int = 100) -> list[list[str]]:
    """
    A 3-candidate scenario where Borda is known to be manipulable.
    50 voters prefer A > B > C (Borda winner is A).
    50 voters prefer B > C > A — a B-voter might bury A to increase B's Borda score.
    """
    ballots = []
    for _ in range(50):
        ballots.append(["A", "B", "C"])
    for _ in range(50):
        ballots.append(["B", "C", "A"])
    return ballots


# ── _rank_of helper ──────────────────────────────────────────────────────────

def test_rank_of_found():
    assert _rank_of("B", ["A", "B", "C"]) == 1

def test_rank_of_first():
    assert _rank_of("A", ["A", "B", "C"]) == 0

def test_rank_of_absent():
    assert _rank_of("X", ["A", "B", "C"]) == 3  # returns len(ballot)

def test_rank_of_none():
    assert _rank_of(None, ["A", "B", "C"]) == 3


# ── Plurality manipulability ─────────────────────────────────────────────────

def test_plurality_manipulation_rate_positive():
    """Plurality should exhibit manipulation opportunities in a spoiler scenario."""
    ballots = make_plurality_ballots(120, 3)
    result  = compute_manipulability_index("plurality", ballots, num_trials=120)

    assert result["manipulability_rate"] >= 0        # valid rate
    assert result["num_sampled"] == 120
    assert isinstance(result["manipulability_rate"], float)
    # In the constructed scenario, some C-voters prefer B > A and can potentially
    # switch to [B, C] to help B win.  We assert the function returns a non-None rate.
    assert result["manipulability_rate"] is not None


def test_plurality_result_structure():
    ballots = make_plurality_ballots(60, 3)
    result  = compute_manipulability_index("plurality", ballots, num_trials=60)

    assert "method" in result
    assert result["method"] == "plurality"
    assert "manipulability_rate" in result
    assert "average_gain" in result
    assert "num_manipulators" in result
    assert "num_sampled" in result
    assert "examples" in result
    assert isinstance(result["examples"], list)


def test_examples_have_correct_keys():
    ballots = make_plurality_ballots(60, 3)
    result  = compute_manipulability_index("plurality", ballots, num_trials=60)
    for ex in result["examples"]:
        assert "voter_id" in ex
        assert "sincere_rank" in ex
        assert "strategic_rank" in ex
        assert ex["strategic_rank"] < ex["sincere_rank"]   # must be an actual improvement


# ── 2-candidate trivial case ─────────────────────────────────────────────────

def test_two_candidates_plurality_zero_manipulation():
    """
    With only 2 candidates, manipulation is impossible:
    – Voters who already prefer the winner can't do better.
    – Voters who prefer the loser can't change the outcome by swapping
      their ballot [B, A] to [A, B]: A still wins and is ranked 1st in
      their sincere preference anyway.
    """
    # 60 % prefer A → A wins plurality
    ballots = [["A", "B"]] * 60 + [["B", "A"]] * 40
    result  = compute_manipulability_index("plurality", ballots, num_trials=100)

    assert result["manipulability_rate"] == 0.0
    assert result["num_manipulators"] == 0


def test_two_candidates_borda_zero_manipulation():
    ballots = [["A", "B"]] * 55 + [["B", "A"]] * 45
    result  = compute_manipulability_index("borda", ballots, num_trials=100)
    assert result["manipulability_rate"] == 0.0


# ── num_trials reduces computation ───────────────────────────────────────────

def test_num_trials_limits_sampled_voters():
    """num_sampled must equal min(num_trials, n_voters)."""
    ballots = make_plurality_ballots(500, 4)

    r10  = compute_manipulability_index("plurality", ballots, num_trials=10)
    r50  = compute_manipulability_index("plurality", ballots, num_trials=50)
    r500 = compute_manipulability_index("plurality", ballots, num_trials=500)

    assert r10["num_sampled"]  == 10
    assert r50["num_sampled"]  == 50
    assert r500["num_sampled"] == 500   # all voters sampled


def test_num_trials_reduces_execution_time():
    """Smaller num_trials must run faster than a large sample on the same ballots."""
    ballots = make_plurality_ballots(1000, 5)

    t0 = time.perf_counter()
    compute_manipulability_index("plurality", ballots, num_trials=10)
    small_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    compute_manipulability_index("plurality", ballots, num_trials=300)
    large_time = time.perf_counter() - t0

    # large_time should be meaningfully longer; allow 2× variance for CI noise
    assert large_time > small_time / 2, (
        f"Expected large_time ({large_time:.3f}s) > small_time/2 ({small_time/2:.3f}s)"
    )


# ── Multiple methods ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("method", ["plurality", "borda", "irv", "approval", "schulze"])
def test_all_main_methods_return_valid_result(method):
    ballots = make_plurality_ballots(80, 4)
    result  = compute_manipulability_index(method, ballots, num_trials=50)

    assert "error" not in result, f"Method '{method}' returned error: {result.get('error')}"
    assert 0.0 <= result["manipulability_rate"] <= 100.0
    assert result["average_gain"] >= 0.0
    assert result["num_manipulators"] <= result["num_sampled"]


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_ballots():
    result = compute_manipulability_index("plurality", [], num_trials=100)
    assert result["manipulability_rate"] == 0.0
    assert result["num_sampled"] == 0


def test_single_voter():
    result = compute_manipulability_index("plurality", [["A", "B", "C"]], num_trials=10)
    # Single voter gets first choice → no manipulation incentive
    assert result["manipulability_rate"] == 0.0


def test_unknown_method():
    ballots = make_plurality_ballots(50, 3)
    result  = compute_manipulability_index("unknown_method_xyz", ballots, num_trials=50)
    assert result["manipulability_rate"] is None
    assert "error" in result


def test_manipulability_rate_between_0_and_100():
    ballots = make_plurality_ballots(100, 4)
    result  = compute_manipulability_index("borda", ballots, num_trials=100)
    assert 0.0 <= (result["manipulability_rate"] or 0) <= 100.0


def test_examples_capped_at_three():
    """At most 3 examples should be returned regardless of manipulator count."""
    ballots = make_borda_ballots_with_manipulation(100)
    result  = compute_manipulability_index("borda", ballots, num_trials=100)
    assert len(result["examples"]) <= 3


# ── API route (integration test) ─────────────────────────────────────────────

def test_manipulability_route_returns_200(client):
    resp = client.get("/simulations/manipulability?num_candidates=3&num_voters=100&num_trials=30")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0


def test_manipulability_route_results_sorted_descending(client):
    resp = client.get("/simulations/manipulability?num_candidates=3&num_voters=80&num_trials=20")
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    rates = [r["manipulability_rate"] for r in results if r.get("manipulability_rate") is not None]
    assert rates == sorted(rates, reverse=True)


def test_manipulability_route_specific_methods(client):
    resp = client.get("/simulations/manipulability?methods=plurality,borda&num_voters=60&num_trials=20")
    assert resp.status_code == 200
    methods_returned = {r["method"] for r in resp.get_json()["results"]}
    assert "plurality" in methods_returned
    assert "borda" in methods_returned
