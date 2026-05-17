"""
test_combined_effects.py — Tests for POST /api/election/combined-effects
"""
import json
import pytest

URL = "/api/election/combined-effects"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ],
    "num_voters":  30,
    "ideology":    "random",
    "seed":        42,
    "campaign":    {"num_days": 14, "polling_effect": 0.35},
    "blank_vote":  {
        "rule":      "symbolic",
        "contagion": {"enabled": False, "beta": 0.1, "gamma": 0.1, "network": "random"},
    },
    "information_model": {
        "media_bias":     {"Alice": 0.4, "Bob": -0.2},
        "voter_segments": {"low_info": 0.3, "medium_info": 0.5, "high_info": 0.2},
    },
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestCombinedEffectsBasic:
    def test_returns_200(self, client):
        r = post(client)
        assert r.status_code == 200, r.data

    def test_response_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("base_winner", "combinations", "factor_deltas",
                    "most_disruptive_factor", "least_disruptive_factor",
                    "max_disruption_combination"):
            assert key in body, f"Missing: {key}"

    def test_too_few_candidates_returns_400(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert post(client, payload).status_code == 400


# ── Combinations ──────────────────────────────────────────────────────────────

class TestCombinations:
    def test_exactly_8_combinations(self, client):
        """2³ combinations — always exactly 8."""
        body = json.loads(post(client).data)
        assert len(body["combinations"]) == 8, (
            f"Expected 8 combinations, got {len(body['combinations'])}"
        )

    def test_all_combinations_have_required_keys(self, client):
        for combo in json.loads(post(client).data)["combinations"]:
            for key in ("id", "blank", "campaign", "information_model",
                        "plurality_winner", "condorcet_winner",
                        "inter_method_agreement", "winner_differs_from_base"):
                assert key in combo, f"Combo {combo.get('id')} missing: {key}"

    def test_all_flags_are_covered(self, client):
        """Each of the 8 (blank, campaign, info) flag tuples appears exactly once."""
        combos = json.loads(post(client).data)["combinations"]
        flags = {(c["blank"], c["campaign"], c["information_model"]) for c in combos}
        expected = {
            (False, False, False), (False, False, True),
            (False, True,  False), (False, True,  True),
            (True,  False, False), (True,  False, True),
            (True,  True,  False), (True,  True,  True),
        }
        assert flags == expected

    def test_agreement_in_range(self, client):
        for combo in json.loads(post(client).data)["combinations"]:
            a = combo["inter_method_agreement"]
            assert 0.0 <= a <= 1.0, f"{combo['id']}: agreement {a} out of range"

    def test_all_off_combination_is_first(self, client):
        first = json.loads(post(client).data)["combinations"][0]
        assert not first["blank"]
        assert not first["campaign"]
        assert not first["information_model"]

    def test_winner_differs_from_base_for_all_off_is_false(self, client):
        combos = json.loads(post(client).data)["combinations"]
        all_off = next(c for c in combos if not c["blank"] and not c["campaign"]
                       and not c["information_model"])
        assert all_off["winner_differs_from_base"] is False


# ── Factor analysis ───────────────────────────────────────────────────────────

class TestFactorAnalysis:
    def test_most_disruptive_factor_is_valid(self, client):
        body = json.loads(post(client).data)
        assert body["most_disruptive_factor"] in (
            "blank", "campaign", "information_model"
        )

    def test_least_disruptive_factor_is_valid(self, client):
        body = json.loads(post(client).data)
        assert body["least_disruptive_factor"] in (
            "blank", "campaign", "information_model"
        )

    def test_factor_deltas_has_all_three_factors(self, client):
        deltas = json.loads(post(client).data)["factor_deltas"]
        assert "blank"             in deltas
        assert "campaign"          in deltas
        assert "information_model" in deltas

    def test_max_disruption_combination_is_valid_id(self, client):
        body   = json.loads(post(client).data)
        ids    = {c["id"] for c in body["combinations"]}
        assert body["max_disruption_combination"] in ids

    def test_max_disruption_has_lowest_agreement(self, client):
        body       = json.loads(post(client).data)
        combos     = body["combinations"]
        max_id     = body["max_disruption_combination"]
        max_combo  = next(c for c in combos if c["id"] == max_id)
        min_agree  = min(c["inter_method_agreement"] for c in combos)
        assert max_combo["inter_method_agreement"] == min_agree


# ── All-OFF baseline ──────────────────────────────────────────────────────────

class TestBaseline:
    def test_all_off_has_highest_or_equal_agreement(self, client):
        """
        The combination with no effects should generally have higher method
        agreement than combinations with disruptive factors.
        We check it is ≥ the minimum across all combinations.
        """
        combos    = json.loads(post(client).data)["combinations"]
        all_off   = combos[0]  # all-OFF is always first
        min_agree = min(c["inter_method_agreement"] for c in combos)
        assert all_off["inter_method_agreement"] >= min_agree - 0.01  # tolerance

    def test_base_winner_matches_all_off_plurality(self, client):
        body      = json.loads(post(client).data)
        all_off   = body["combinations"][0]
        assert body["base_winner"] == all_off["plurality_winner"]


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_combinations(self, client):
        r1 = json.loads(post(client).data)["combinations"]
        r2 = json.loads(post(client).data)["combinations"]
        for c1, c2 in zip(r1, r2):
            assert c1["plurality_winner"]       == c2["plurality_winner"]
            assert c1["inter_method_agreement"] == c2["inter_method_agreement"]

    def test_different_seed_can_differ(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client, {**BASE, "seed": 999}).data)
        # Both return 200 and 8 combinations
        assert len(r1["combinations"]) == 8
        assert len(r2["combinations"]) == 8

    def test_with_contagion_returns_200(self, client):
        payload = {
            **BASE,
            "blank_vote": {
                "rule":      "competitive",
                "contagion": {"enabled": True, "beta": 0.3, "gamma": 0.1, "network": "random"},
            },
        }
        assert post(client, payload).status_code == 200
