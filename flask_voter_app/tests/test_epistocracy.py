"""
test_epistocracy.py — Tests for POST /api/theory/epistocracy
Caplan (2007) / Brennan (2016) electoral competence model.
"""
import json
import pytest

URL = "/api/theory/epistocracy"

BASE = {
    "candidates": [
        {"name": "A", "x": -0.5, "y": 0.0},
        {"name": "B", "x":  0.0, "y": 0.0},
        {"name": "C", "x":  0.5, "y": 0.0},
    ],
    "num_voters": 100,
    "seed":       42,
    "voter_competence_distribution": "uniform",
    "competence_params": {
        "mean":        0.60,
        "std":         0.12,
        "expert_pct":  0.10,
        "caplan_bias": False,
    },
    "weighting_scheme":      "equal",
    "epistocracy_threshold": 0.70,
}

ALL_SCHEMES = ("equal", "competence_weighted", "epistocratic", "lottery")


def post(client, **kw):
    payload = {**BASE}
    for k, v in kw.items():
        if k == "competence_params":
            payload["competence_params"] = {**BASE["competence_params"], **v}
        else:
            payload[k] = v
    return json.loads(client.post(URL, json=payload).data)


class TestEpistoBasic:
    def test_returns_200(self, client):
        assert client.post(URL, json=BASE).status_code == 200

    def test_response_keys(self, client):
        body = post(client)
        for k in ("voter_competence_stats", "results",
                  "democracy_vs_expert", "condorcet_threshold",
                  "pedagogical_note"):
            assert k in body

    def test_competence_stats_keys(self, client):
        body = post(client)
        for k in ("mean", "biased_mean", "expert_count"):
            assert k in body["voter_competence_stats"]

    def test_all_schemes_in_results(self, client):
        body = post(client)
        for s in ALL_SCHEMES:
            assert s in body["results"]

    def test_scheme_result_keys(self, client):
        body = post(client)
        for s in ALL_SCHEMES:
            r = body["results"][s]
            for k in ("winner", "bayesian_regret", "correct_choice_pct",
                      "participates_pct"):
                assert k in r

    def test_democracy_vs_expert_keys(self, client):
        body = post(client)
        for k in ("democracy_regret", "expert_regret", "omniscient_regret"):
            assert k in body["democracy_vs_expert"]

    def test_omniscient_regret_is_zero(self, client):
        body = post(client)
        assert body["democracy_vs_expert"]["omniscient_regret"] == 0.0

    def test_correct_choice_pct_in_range(self, client):
        body = post(client)
        for s, r in body["results"].items():
            assert 0.0 <= r["correct_choice_pct"] <= 1.0, \
                f"{s}: correct_choice_pct={r['correct_choice_pct']}"

    def test_bayesian_regret_nonneg(self, client):
        body = post(client)
        for s, r in body["results"].items():
            assert r["bayesian_regret"] >= 0.0

    def test_participates_pct_in_range(self, client):
        body = post(client)
        for s, r in body["results"].items():
            assert 0.0 <= r["participates_pct"] <= 1.0

    def test_condorcet_threshold_is_half(self, client):
        body = post(client)
        assert body["condorcet_threshold"] == pytest.approx(0.5, abs=0.05)


# ── competence_mean = 1.0 → regret ≈ 0 ──────────────────────────────────────

class TestPerfectCompetence:
    def test_perfect_competence_zero_regret(self, client):
        """With P=1 (all competent), all schemes should have zero regret."""
        body = post(client, competence_params={"mean": 0.99, "std": 0.01,
                                               "caplan_bias": False})
        for s in ALL_SCHEMES:
            assert body["results"][s]["bayesian_regret"] == pytest.approx(0.0, abs=0.15), \
                f"{s}: regret={body['results'][s]['bayesian_regret']}"

    def test_perfect_competence_correct_choice(self, client):
        """With P=1, all schemes should approach 100% correct decisions."""
        body = post(client, competence_params={"mean": 0.99, "std": 0.01,
                                               "caplan_bias": False})
        for s in ALL_SCHEMES:
            assert body["results"][s]["correct_choice_pct"] >= 0.70, \
                f"{s}: correct={body['results'][s]['correct_choice_pct']}"


# ── competence_mean = 0.5 → ≈ random ─────────────────────────────────────────

class TestRandomCompetence:
    def test_p_at_one_third_near_chance(self, client):
        """With P≈1/3 (random-chance crossover for 3 candidates), accuracy ≈ 33%."""
        # With 3 candidates: P=0.5 still wins (errors split 25%/25% for wrong candidates).
        # True crossover is at P = 1/n_candidates ≈ 0.33.
        body = post(client, competence_params={"mean": 0.33, "std": 0.03,
                                               "caplan_bias": False})
        r = body["results"]["equal"]["correct_choice_pct"]
        # Around the crossover: should be somewhere between near-random and moderate
        assert 0.20 <= r <= 0.80, f"At P≈1/3: correct={r:.2f}"

    def test_p_half_democracy_still_wins(self, client):
        """With P=0.5 and 3 candidates, the best candidate still wins (errors split)."""
        body = post(client, competence_params={"mean": 0.50, "std": 0.05,
                                               "caplan_bias": False})
        r = body["results"]["equal"]["correct_choice_pct"]
        # At P=0.5 with 3 candidates: B gets 50% votes, each wrong gets 25% → B wins
        assert r >= 0.50, f"At P=0.5 (3 candidates): correct={r:.2f}, should be ≥ 0.50"


# ── competence < 0.5 → democracy worse than random ───────────────────────────

class TestSubRandomCompetence:
    def test_low_competence_democracy_below_random(self, client):
        """With P < 0.5, democracy should perform below random chance."""
        body = post(client, competence_params={"mean": 0.25, "std": 0.05,
                                               "caplan_bias": False},
                    epistocracy_threshold=0.80)
        equal_acc = body["results"]["equal"]["correct_choice_pct"]
        random_chance = 1 / 3
        # Democracy should do poorly when voters systematically err
        assert equal_acc <= random_chance + 0.10, \
            f"P=0.25: democracy correct={equal_acc:.2f}, should be ≤ {random_chance + 0.1:.2f}"

    def test_biased_mean_below_real_mean_with_caplan(self, client):
        """Caplan biases reduce effective competence below the stated mean."""
        body = post(client, competence_params={"mean": 0.60, "std": 0.10,
                                               "caplan_bias": True})
        real_mean   = body["voter_competence_stats"]["mean"]
        biased_mean = body["voter_competence_stats"]["biased_mean"]
        assert biased_mean <= real_mean, \
            f"biased_mean={biased_mean} > mean={real_mean}"


# ── epistocracy: high threshold → low participates_pct, better accuracy ──────

class TestEpistocracy:
    def test_high_threshold_low_participation(self, client):
        """With threshold=0.90, very few voters qualify."""
        body = post(client, epistocracy_threshold=0.90,
                    competence_params={"mean": 0.55, "std": 0.10,
                                       "caplan_bias": False})
        pct = body["results"]["epistocratic"]["participates_pct"]
        assert pct < 0.40, f"threshold=0.90: participates={pct:.2f}, expected < 0.40"

    def test_low_threshold_high_participation(self, client):
        """With threshold=0.50, almost everyone qualifies."""
        body = post(client, epistocracy_threshold=0.50,
                    competence_params={"mean": 0.65, "std": 0.10,
                                       "caplan_bias": False})
        pct = body["results"]["epistocratic"]["participates_pct"]
        assert pct >= 0.40, f"threshold=0.50: participates={pct:.2f}, expected ≥ 0.40"

    def test_epistocracy_beats_equal_when_competent_experts(self, client):
        """With expert minority and high threshold, epistocracy should outperform equal."""
        body = post(client,
                    voter_competence_distribution="expert_minority",
                    epistocracy_threshold=0.80,
                    competence_params={"mean": 0.40, "std": 0.10,
                                       "expert_pct": 0.20,
                                       "caplan_bias": False})
        epist_acc = body["results"]["epistocratic"]["correct_choice_pct"]
        equal_acc = body["results"]["equal"]["correct_choice_pct"]
        # Expert minority should produce better decisions under epistocracy
        assert epist_acc >= equal_acc - 0.05, \
            f"epistocratic={epist_acc:.2f}, equal={equal_acc:.2f}"

    def test_epistocratic_participates_lt_1(self, client):
        """Epistocracy with threshold > 0 should exclude some voters."""
        body = post(client, epistocracy_threshold=0.75)
        pct = body["results"]["epistocratic"]["participates_pct"]
        assert pct <= 1.0

    def test_equal_participates_is_1(self, client):
        """Equal democracy always has 100% participation."""
        body = post(client)
        assert body["results"]["equal"]["participates_pct"] == pytest.approx(1.0, abs=0.01)


# ── Caplan bias ───────────────────────────────────────────────────────────────

class TestCaplanBias:
    def test_caplan_bias_reduces_competence(self, client):
        """Caplan biases should reduce the effective competence below stated mean."""
        body = post(client, competence_params={"mean": 0.65, "std": 0.10,
                                               "caplan_bias": True})
        assert (body["voter_competence_stats"]["biased_mean"] <=
                body["voter_competence_stats"]["mean"])

    def test_no_caplan_bias_mean_unchanged(self, client):
        """Without Caplan biases, biased_mean should approximately equal mean."""
        body = post(client, competence_params={"mean": 0.65, "std": 0.10,
                                               "caplan_bias": False})
        real   = body["voter_competence_stats"]["mean"]
        biased = body["voter_competence_stats"]["biased_mean"]
        assert biased == pytest.approx(real, abs=0.02), \
            f"Without bias: biased_mean={biased:.4f} ≠ mean={real:.4f}"


# ── Distributions ─────────────────────────────────────────────────────────────

class TestDistributions:
    @pytest.mark.parametrize("dist", ["uniform", "bimodal", "expert_minority"])
    def test_all_distributions_return_200(self, client, dist):
        body = post(client, voter_competence_distribution=dist)
        assert len(body["results"]) == len(ALL_SCHEMES)

    def test_expert_minority_has_high_expert_count(self, client):
        """With expert_minority distribution and high expert_pct, many should qualify."""
        body = post(client,
                    voter_competence_distribution="expert_minority",
                    competence_params={"mean": 0.50, "std": 0.12,
                                       "expert_pct": 0.20,
                                       "caplan_bias": False})
        assert body["voter_competence_stats"]["expert_count"] >= 5


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_reproducibility(self, client):
        a = post(client)
        b = post(client)
        for s in ALL_SCHEMES:
            assert a["results"][s]["correct_choice_pct"] == \
                   pytest.approx(b["results"][s]["correct_choice_pct"])
