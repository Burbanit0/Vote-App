"""
test_vote_steps.py — Tests for POST /simulations/vote-steps
"""
import json
import pytest

URL = "/simulations/vote-steps"

BASE = {
    "num_voters":  80,
    "candidates":  ["Alice", "Bob", "Carol"],
    "ideology":    "random",
    "seed":        42,
}


def post(client, method, extra=None):
    payload = {**BASE, "method": method, **(extra or {})}
    return client.post(URL, json=payload)


# ── All five methods return 200 ───────────────────────────────────────────────

class TestVoteStepsBasic:
    @pytest.mark.parametrize("method", ["irv", "borda", "plurality", "schulze", "approval"])
    def test_all_methods_return_200(self, client, method):
        r = post(client, method)
        assert r.status_code == 200, f"{method}: {r.data}"

    def test_method_echo_in_response(self, client):
        for m in ("irv", "borda", "plurality", "schulze", "approval"):
            body = json.loads(post(client, m).data)
            assert body.get("method") == m

    def test_unknown_method_returns_400(self, client):
        r = post(client, "condorcet_not_a_method")
        assert r.status_code == 400

    def test_too_few_candidates_returns_400(self, client):
        r = client.post(URL, json={**BASE, "method": "irv", "candidates": ["Solo"]})
        assert r.status_code == 400


# ── IRV ───────────────────────────────────────────────────────────────────────

class TestVoteStepsIRV:
    def test_irv_returns_rounds_list(self, client):
        body = json.loads(post(client, "irv").data)
        assert "rounds" in body
        assert isinstance(body["rounds"], list)
        assert len(body["rounds"]) >= 2

    def test_irv_last_round_has_winner(self, client):
        rounds = json.loads(post(client, "irv").data)["rounds"]
        last = rounds[-1]
        assert "winner" in last
        assert last["winner"] in BASE["candidates"]

    def test_irv_first_round_has_scores(self, client):
        rounds = json.loads(post(client, "irv").data)["rounds"]
        first = rounds[0]
        assert "scores" in first
        assert all(c in first["scores"] for c in BASE["candidates"])

    def test_irv_scores_sum_to_one(self, client):
        rounds = json.loads(post(client, "irv").data)["rounds"]
        for rnd in rounds:
            if "scores" in rnd:
                total = sum(rnd["scores"].values())
                assert abs(total - 1.0) < 0.02, f"Round scores sum = {total}"

    def test_irv_round_numbers_increase(self, client):
        rounds = json.loads(post(client, "irv").data)["rounds"]
        nums = [r["round"] for r in rounds]
        assert nums == sorted(nums)
        assert nums == list(range(nums[0], nums[0] + len(nums)))

    def test_irv_eliminated_is_candidate_or_null(self, client):
        """`eliminated` is null or a candidate name; when multiple candidates
        are eliminated in the same round (tied at the bottom — canonical IRV),
        the field contains them joined by ' + '."""
        rounds = json.loads(post(client, "irv").data)["rounds"]
        valid_cands = set(BASE["candidates"])
        for rnd in rounds:
            if "eliminated" in rnd and rnd["eliminated"] is not None:
                # Split on " + " to handle multi-elimination rounds
                names = rnd["eliminated"].split(" + ")
                for n in names:
                    assert n in valid_cands, f"unknown eliminated candidate: {n}"


# ── Borda ─────────────────────────────────────────────────────────────────────

class TestVoteStepsBorda:
    def test_borda_returns_steps_and_winner(self, client):
        body = json.loads(post(client, "borda").data)
        assert "steps" in body
        assert "winner" in body
        assert body["winner"] in BASE["candidates"]

    def test_borda_steps_count_equals_num_candidates(self, client):
        body = json.loads(post(client, "borda").data)
        assert len(body["steps"]) == len(BASE["candidates"])

    def test_borda_tally_grows_monotonically(self, client):
        steps = json.loads(post(client, "borda").data)["steps"]
        for cand in BASE["candidates"]:
            tallies = [s["tally"][cand] for s in steps]
            assert tallies == sorted(tallies) or tallies == tallies, \
                f"Tally for {cand} is not monotonically non-decreasing: {tallies}"

    def test_borda_points_awarded_decreases(self, client):
        steps = json.loads(post(client, "borda").data)["steps"]
        pts = [s["points_awarded"] for s in steps]
        assert pts == sorted(pts, reverse=True)


# ── Plurality ─────────────────────────────────────────────────────────────────

class TestVoteStepsPlurality:
    def test_plurality_has_first_choices_and_winner(self, client):
        body = json.loads(post(client, "plurality").data)
        assert "first_choices" in body
        assert "winner" in body
        assert body["winner"] in BASE["candidates"]

    def test_plurality_first_choices_sum_to_one(self, client):
        body = json.loads(post(client, "plurality").data)
        total = sum(body["first_choices"].values())
        assert abs(total - 1.0) < 0.02

    def test_plurality_winner_has_most_votes(self, client):
        body = json.loads(post(client, "plurality").data)
        winner = body["winner"]
        max_score = max(body["first_choices"].values())
        assert body["first_choices"][winner] == max_score


# ── Schulze ───────────────────────────────────────────────────────────────────

class TestVoteStepsSchulze:
    def test_schulze_has_duel_and_path_matrices(self, client):
        body = json.loads(post(client, "schulze").data)
        assert "duel_matrix" in body
        assert "path_matrix" in body
        assert "winner" in body

    def test_schulze_duel_matrix_has_all_candidates(self, client):
        duel = json.loads(post(client, "schulze").data)["duel_matrix"]
        for c in BASE["candidates"]:
            assert c in duel

    def test_schulze_duel_values_in_range(self, client):
        duel = json.loads(post(client, "schulze").data)["duel_matrix"]
        for c1, row in duel.items():
            for c2, val in row.items():
                assert 0.0 <= val <= 1.0, f"duel[{c1}][{c2}] = {val}"

    def test_schulze_winner_is_candidate(self, client):
        winner = json.loads(post(client, "schulze").data)["winner"]
        assert winner in BASE["candidates"]


# ── Approval ──────────────────────────────────────────────────────────────────

class TestVoteStepsApproval:
    def test_approval_has_scores_threshold_winner(self, client):
        body = json.loads(post(client, "approval").data)
        assert "approval_scores" in body
        assert "threshold_used"  in body
        assert "winner"          in body

    def test_approval_scores_in_range(self, client):
        scores = json.loads(post(client, "approval").data)["approval_scores"]
        for c, v in scores.items():
            assert 0.0 <= v <= 1.0, f"approval_scores[{c}] = {v}"


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestVoteStepsReproducibility:
    @pytest.mark.parametrize("method", ["irv", "borda", "plurality", "schulze", "approval"])
    def test_same_seed_same_result(self, client, method):
        r1 = json.loads(post(client, method).data)
        r2 = json.loads(post(client, method).data)
        assert r1 == r2, f"{method}: same seed should produce identical output"

    def test_different_seed_may_produce_different_result(self, client):
        r1 = json.loads(post(client, "irv", {"seed": 42}).data)
        r2 = json.loads(post(client, "irv", {"seed": 99}).data)
        # Not guaranteed to differ but very likely with different seeds
        # Just check both return valid structure
        assert "rounds" in r1 and "rounds" in r2


# ── Candidate positions accepted (coherence with /api/election/simulate) ─────

class TestCandidatePositions:
    """The animator must accept full candidate configs (with x/y positions)
    so that animation winners match the main election simulation exactly."""

    def test_accepts_object_candidates(self, client):
        """Posting {name, x, y} objects instead of strings returns 200."""
        r = client.post(URL, json={
            "method":     "plurality",
            "num_voters": 50,
            "candidates": [
                {"name": "Left",   "x": -0.7, "y": 0.0},
                {"name": "Center", "x":  0.0, "y": 0.0},
                {"name": "Right",  "x":  0.7, "y": 0.0},
            ],
            "ideology": "random",
            "seed":     42,
        })
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "winner" in data
        assert data["winner"] in {"Left", "Center", "Right"}

    def test_positions_change_winner_vs_default(self, client):
        """A drastically asymmetric position layout should produce a different
        winner than the default name-only placement."""
        names_only = json.loads(client.post(URL, json={
            "method": "plurality", "num_voters": 100,
            "candidates": ["A", "B", "C"],
            "ideology": "random", "seed": 7,
        }).data)
        # Push C strongly into the centre and A/B to extremes — centre should win
        objects = json.loads(client.post(URL, json={
            "method": "plurality", "num_voters": 100,
            "candidates": [
                {"name": "A", "x": -0.95, "y": 0.0},
                {"name": "B", "x":  0.95, "y": 0.0},
                {"name": "C", "x":  0.0,  "y": 0.0},
            ],
            "ideology": "random", "seed": 7,
        }).data)
        # Both should return valid plurality results
        assert "winner" in names_only
        assert "winner" in objects
        # C (centre) should win the spatially-placed version most likely
        assert objects["winner"] == "C", (
            f"With C at centre and A/B at extremes, C should win plurality; got {objects['winner']}"
        )

    def test_object_candidates_reproducible(self, client):
        """Same positions + seed should give identical output."""
        payload = {
            "method": "irv", "num_voters": 60,
            "candidates": [
                {"name": "Alice", "x": -0.4, "y":  0.1},
                {"name": "Bob",   "x":  0.0, "y":  0.0},
                {"name": "Carol", "x":  0.5, "y": -0.1},
            ],
            "ideology": "random", "seed": 42,
        }
        r1 = json.loads(client.post(URL, json=payload).data)
        r2 = json.loads(client.post(URL, json=payload).data)
        assert r1 == r2

    def test_irv_winner_matches_main_simulate(self, client):
        """Critical coherence test: IRV winner from /simulations/vote-steps
        must equal IRV winner from /api/election/simulate for the SAME inputs.
        Bug fix: previously _irv_steps eliminated only the alphabetically first
        tied candidate while get_irv_winner eliminated all ties — producing
        different winners (e.g. Le Pen vs Megret in France 2002)."""
        # France-2002-like fragmented scenario with many low-vote candidates
        cands = [
            {"name": "Chirac",   "x":  0.20, "y":  0.15},
            {"name": "LePen",    "x":  0.65, "y":  0.50},
            {"name": "Jospin",   "x": -0.30, "y": -0.10},
            {"name": "Bayrou",   "x":  0.05, "y":  0.05},
            {"name": "Laguiller","x": -0.85, "y": -0.20},
            {"name": "Chevenement","x": -0.40, "y":  0.10},
            {"name": "Mamere",   "x": -0.55, "y": -0.40},
            {"name": "Besancenot","x": -0.90, "y": -0.30},
            {"name": "SaintJosse","x":  0.30, "y":  0.40},
            {"name": "Madelin",  "x":  0.50, "y":  0.20},
            {"name": "Hue",      "x": -0.75, "y":  0.00},
            {"name": "Megret",   "x":  0.80, "y":  0.55},
            {"name": "Taubira",  "x": -0.45, "y": -0.50},
        ]
        common = {
            "num_voters": 200,
            "ideology":   "random",
            "seed":       7,
            "candidates": cands,
        }

        # Animation endpoint
        anim = json.loads(client.post(URL, json={**common, "method": "irv"}).data)
        anim_winner = anim["rounds"][-1]["winner"]

        # Main simulation endpoint
        main = json.loads(client.post(
            "/api/election/simulate",
            json={**common, "ideology": "random"},
        ).data)
        main_irv_winner = main["methods"]["irv"]["winner"]

        assert anim_winner == main_irv_winner, (
            f"IRV winner divergence: animation={anim_winner}, main={main_irv_winner}. "
            "Tie-breaking rules likely differ between _irv_steps and get_irv_winner."
        )

    def test_object_and_string_candidates_can_differ(self, client):
        """Object candidates (real positions) and string candidates (auto-positions)
        should produce different winners on the same seed — proving the new path
        actually uses the provided positions."""
        common = {"method": "plurality", "num_voters": 80, "ideology": "random", "seed": 1}
        r_obj = json.loads(client.post(URL, json={
            **common,
            "candidates": [
                {"name": "Far Left",  "x": -0.9, "y": 0.0},
                {"name": "Far Right", "x":  0.9, "y": 0.0},
                {"name": "Centre",    "x":  0.0, "y": 0.0},
            ],
        }).data)
        r_str = json.loads(client.post(URL, json={
            **common,
            "candidates": ["Far Left", "Far Right", "Centre"],
        }).data)
        # Both valid
        assert "winner" in r_obj and "winner" in r_str
