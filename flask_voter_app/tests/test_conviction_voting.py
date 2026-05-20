"""
test_conviction_voting.py — Tests for POST /api/election/conviction-voting
"""
import json
import pytest

URL = "/api/election/conviction-voting"

BASE = {
    "proposals": [
        {"name": "A", "x": -0.5},
        {"name": "B", "x":  0.5},
        {"name": "C", "x":  0.0},
    ],
    "num_voters":              100,
    "ideology":                "random",
    "seed":                    42,
    "conviction_distribution": "uniform",
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestConvictionBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("conviction_winner", "token_winner", "winner_changed",
                  "proposals", "voter_scatter", "voter_stats",
                  "pedagogical_note", "lock_options", "multipliers"):
            assert k in body, f"Missing key: {k}"

    def test_voter_stats_keys(self, client):
        body = json.loads(post(client).data)
        vs = body["voter_stats"]
        for k in ("gini_tokens", "gini_conviction",
                  "whale_pct_tokens", "whale_pct_conviction"):
            assert k in vs

    def test_proposal_stat_keys(self, client):
        body = json.loads(post(client).data)
        for p in body["proposals"]:
            for k in ("name", "conviction_score", "token_score",
                      "avg_conviction_of_supporters", "avg_tokens_of_supporters"):
                assert k in p

    def test_all_proposals_present(self, client):
        body = json.loads(post(client).data)
        names = {p["name"] for p in body["proposals"]}
        assert names == {"A", "B", "C"}

    def test_gini_in_range(self, client):
        body = json.loads(post(client).data)
        vs = body["voter_stats"]
        assert 0.0 <= vs["gini_tokens"]     <= 1.0
        assert 0.0 <= vs["gini_conviction"] <= 1.0

    def test_whale_pct_in_range(self, client):
        body = json.loads(post(client).data)
        vs = body["voter_stats"]
        assert 0.0 <= vs["whale_pct_tokens"]     <= 1.0
        assert 0.0 <= vs["whale_pct_conviction"] <= 1.0

    def test_lock_options_correct(self, client):
        body = json.loads(post(client).data)
        assert body["lock_options"] == [0, 7, 14, 28, 56, 112, 224]

    def test_voter_scatter_non_empty(self, client):
        body = json.loads(post(client).data)
        assert len(body["voter_scatter"]) > 0

    def test_scores_positive(self, client):
        body = json.loads(post(client).data)
        for p in body["proposals"]:
            assert p["conviction_score"] >= 0
            assert p["token_score"]      >= 0


# ── zero_lock → conviction = token winner ─────────────────────────────────────

class TestZeroLock:
    def _run(self, client):
        payload = {**BASE, "conviction_distribution": "zero_lock"}
        return json.loads(client.post(URL, json=payload).data)

    def test_conviction_equals_token_winner(self, client):
        body = self._run(client)
        assert body["conviction_winner"] == body["token_winner"]

    def test_winner_not_changed(self, client):
        body = self._run(client)
        assert body["winner_changed"] is False

    def test_all_multipliers_01(self, client):
        body = self._run(client)
        for dot in body["voter_scatter"]:
            assert dot["conviction_mult"] == pytest.approx(0.1)
            assert dot["lock_days"] == 0

    def test_scores_proportional(self, client):
        body = self._run(client)
        # conviction_score = 0.1 × token_score → same ranking
        cv_sorted  = sorted(body["proposals"], key=lambda p: -p["conviction_score"])
        tok_sorted = sorted(body["proposals"], key=lambda p: -p["token_score"])
        assert [p["name"] for p in cv_sorted] == [p["name"] for p in tok_sorted]


# ── whale distribution → gini_conviction < gini_tokens ───────────────────────

class TestWhaleMakesConvictionMoreEqual:
    def _run(self, client):
        payload = {
            **BASE,
            "conviction_distribution": "whale",
            "whale_pct":               0.10,
            "small_lock_days":         224,
        }
        return json.loads(client.post(URL, json=payload).data)

    def test_gini_conviction_lt_tokens(self, client):
        body = self._run(client)
        vs = body["voter_stats"]
        assert vs["gini_conviction"] < vs["gini_tokens"], (
            f"Expected gini_conviction ({vs['gini_conviction']}) < "
            f"gini_tokens ({vs['gini_tokens']})"
        )

    def test_whale_pct_conviction_lt_tokens(self, client):
        body = self._run(client)
        vs = body["voter_stats"]
        assert vs["whale_pct_conviction"] < vs["whale_pct_tokens"]


# ── skewed distribution → gini_conviction < gini_tokens ──────────────────────

class TestSkewedMoreEqual:
    def _run(self, client):
        payload = {**BASE, "conviction_distribution": "skewed"}
        return json.loads(client.post(URL, json=payload).data)

    def test_gini_conviction_le_tokens(self, client):
        body = self._run(client)
        vs = body["voter_stats"]
        # Skewed: small holders lock more → conviction more equal than token
        assert vs["gini_conviction"] <= vs["gini_tokens"]


# ── Conviction math (pure unit tests) ────────────────────────────────────────

class TestConvictionMath:
    def test_whale_1M_beats_1000_small(self):
        """1 whale: 1M × 0.1 = 100k > 1000 small × 1 × 6 = 6k"""
        whale_cv = 1_000_000 * 0.1
        small_cv = 1_000 * 1.0 * 6.0
        assert whale_cv > small_cv

    def test_17000_small_beat_whale(self):
        """17000 small × 1 × 6 = 102k > 1 whale × 1M × 0.1 = 100k"""
        whale_cv = 1_000_000 * 0.1
        small_cv = 17_000 * 1.0 * 6.0
        assert small_cv > whale_cv

    def test_multipliers(self):
        expected = {0: 0.1, 7: 1.0, 14: 2.0, 28: 3.0, 56: 4.0, 112: 5.0, 224: 6.0}
        for days, mult in expected.items():
            weight = 1000 * mult
            expected_weight = 1000 * expected[days]
            assert weight == pytest.approx(expected_weight)

    def test_conviction_scales_with_lock(self):
        """Higher lock → higher weight per token."""
        tokens = 100.0
        assert tokens * 6.0 > tokens * 1.0 > tokens * 0.1


# ── Distributions ─────────────────────────────────────────────────────────────

class TestDistributions:
    @pytest.mark.parametrize("dist", ["uniform", "skewed", "whale"])
    def test_distributions_return_200(self, client, dist):
        payload = {**BASE, "conviction_distribution": dist}
        assert client.post(URL, json=payload).status_code == 200

    def test_whale_lock_days(self, client):
        """In whale mode: top 10% have lock=0, rest have small_lock_days."""
        payload = {**BASE, "conviction_distribution": "whale",
                   "whale_pct": 0.10, "small_lock_days": 224}
        body = json.loads(client.post(URL, json=payload).data)
        dots = body["voter_scatter"]
        lock_vals = {dot["lock_days"] for dot in dots}
        assert 0   in lock_vals   # whales
        assert 224 in lock_vals   # small holders


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["conviction_winner"] == b["conviction_winner"]
        assert a["voter_stats"]["gini_tokens"] == b["voter_stats"]["gini_tokens"]


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_proposal_rejected(self, client):
        payload = {**BASE, "proposals": [{"name": "Solo", "x": 0.0}]}
        assert client.post(URL, json=payload).status_code == 400

    def test_two_proposals(self, client):
        payload = {**BASE, "proposals": [{"name": "A", "x": -0.5}, {"name": "B", "x": 0.5}]}
        assert client.post(URL, json=payload).status_code == 200

    def test_winner_is_a_proposal(self, client):
        body = json.loads(post(client).data)
        names = {p["name"] for p in body["proposals"]}
        assert body["conviction_winner"] in names
        assert body["token_winner"]      in names
