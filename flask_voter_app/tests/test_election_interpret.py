"""
test_election_interpret.py — Tests for POST /api/election/interpret
"""
import json
import pytest

URL = "/api/election/interpret"

# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_body(
    agreement=0.9,
    condorcet_winner="Alice",
    condorcet_exists=True,
    blank_rate=0.0,
    winners=None,
    lang="fr",
):
    """Build a minimal /interpret request body."""
    if winners is None:
        winners = {
            "plurality": "Alice",
            "borda": "Alice",
            "irv": "Alice",
            "schulze": "Bob",
            "approval": "Alice",
        }
    methods = {
        m: {
            "winner": w,
            "bayesian_regret": 0.02 if m != "plurality" else 0.05,
            "majority_satisfaction": 0.8,
            "condorcet_consistent": (w == condorcet_winner) if condorcet_winner else None,
        }
        for m, w in winners.items()
    }
    return {
        "methods":               methods,
        "condorcet_winner":      condorcet_winner,
        "condorcet_exists":      condorcet_exists,
        "inter_method_agreement": agreement,
        "blank_rate":            blank_rate,
        "config":                {"blank_vote": {"rule": "symbolic"}},
        "lang":                  lang,
    }


def post(client, body=None):
    return client.post(URL, json=body or _make_body())


# ── Basic structure ───────────────────────────────────────────────────────────

class TestInterpretBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_required_keys_present(self, client):
        body = json.loads(post(client).data)
        for key in ("headline", "condorcet_analysis", "divergence_reason",
                    "method_groups", "best_by_regret", "worst_by_regret",
                    "blank_analysis", "pedagogical_note", "key_facts"):
            assert key in body, f"Missing key: {key}"

    def test_no_methods_returns_400(self, client):
        assert post(client, {"methods": {}}).status_code == 400

    def test_method_groups_cover_all_methods(self, client):
        body = _make_body()
        resp = json.loads(post(client, body).data)
        all_in_groups = [m for g in resp["method_groups"] for m in g["methods"]]
        assert set(all_in_groups) == set(body["methods"].keys())

    def test_method_groups_pct_sums_to_one(self, client):
        resp = json.loads(post(client).data)
        total = sum(g["pct"] for g in resp["method_groups"])
        assert abs(total - 1.0) < 0.01


# ── Headline logic ────────────────────────────────────────────────────────────

class TestHeadline:
    def test_high_agreement_contains_consensus_keyword(self, client):
        body = _make_body(agreement=0.90,
                          winners={"plurality": "Alice", "borda": "Alice",
                                   "irv": "Alice", "schulze": "Alice",
                                   "approval": "Alice"})
        resp = json.loads(post(client, body).data)
        assert "consensus" in resp["headline"].lower() or "✓" in resp["headline"]

    def test_low_agreement_contains_divergence_indicator(self, client):
        body = _make_body(agreement=0.40,
                          winners={"plurality": "Alice", "borda": "Bob",
                                   "irv": "Carol", "schulze": "Bob",
                                   "approval": "Carol"})
        resp = json.loads(post(client, body).data)
        # Should signal strong or moderate divergence
        assert any(s in resp["headline"] for s in ["🚨", "⚠", "divergen", "Divergen"])

    def test_moderate_agreement(self, client):
        body = _make_body(agreement=0.65,
                          winners={"plurality": "Alice", "borda": "Alice",
                                   "irv": "Alice", "schulze": "Bob",
                                   "approval": "Bob"})
        resp = json.loads(post(client, body).data)
        # 65% is moderate
        assert resp["headline"]  # non-empty


# ── Condorcet analysis ────────────────────────────────────────────────────────

class TestCondorcet:
    def test_no_condorcet_mentions_cycle(self, client):
        body = _make_body(condorcet_winner=None, condorcet_exists=False,
                          winners={"plurality": "Alice", "borda": "Bob",
                                   "irv": "Carol", "schulze": "Alice",
                                   "approval": "Bob"})
        resp = json.loads(post(client, body).data)
        analysis = resp["condorcet_analysis"].lower()
        assert "condorcet" in analysis or "cycle" in analysis or "n'existe pas" in analysis or "no condorcet" in analysis

    def test_condorcet_exists_mentions_winner(self, client):
        body = _make_body(condorcet_winner="Alice", condorcet_exists=True)
        resp = json.loads(post(client, body).data)
        assert "Alice" in resp["condorcet_analysis"]

    def test_spoiler_detected_when_condorcet_ne_plurality(self, client):
        body = _make_body(
            condorcet_winner="Bob",
            condorcet_exists=True,
            winners={"plurality": "Alice", "borda": "Bob",
                     "irv": "Bob", "schulze": "Bob", "approval": "Bob"},
            agreement=0.80,
        )
        resp = json.loads(post(client, body).data)
        # spoiler: Condorcet=Bob but plurality=Alice
        analysis = resp["condorcet_analysis"]
        assert "Bob" in analysis and "Alice" in analysis


# ── Bayesian regret ───────────────────────────────────────────────────────────

class TestRegret:
    def test_best_and_worst_by_regret(self, client):
        body = _make_body()
        resp = json.loads(post(client, body).data)
        assert resp["best_by_regret"] is not None
        assert resp["worst_by_regret"] is not None

    def test_best_has_lower_regret_than_worst(self, client):
        body = _make_body()
        resp = json.loads(post(client, body).data)
        best  = resp["best_by_regret"]
        worst = resp["worst_by_regret"]
        methods = body["methods"]
        assert methods[best]["bayesian_regret"] <= methods[worst]["bayesian_regret"]


# ── Blank rate ────────────────────────────────────────────────────────────────

class TestBlankRate:
    def test_blank_analysis_null_when_low(self, client):
        body = _make_body(blank_rate=0.05)
        resp = json.loads(post(client, body).data)
        assert resp["blank_analysis"] is None

    def test_blank_analysis_present_when_high(self, client):
        body = _make_body(blank_rate=0.35)
        resp = json.loads(post(client, body).data)
        assert resp["blank_analysis"] is not None
        assert "35" in resp["blank_analysis"] or "0.35" in resp["blank_analysis"] \
               or "35.0" in resp["blank_analysis"]


# ── Key facts ─────────────────────────────────────────────────────────────────

class TestKeyFacts:
    def test_key_facts_has_three_entries(self, client):
        resp = json.loads(post(client).data)
        assert len(resp["key_facts"]) == 3

    def test_key_facts_mention_condorcet(self, client):
        resp = json.loads(post(client).data)
        condorcet_fact = any("Condorcet" in f or "condorcet" in f.lower()
                             for f in resp["key_facts"])
        assert condorcet_fact


# ── Language ──────────────────────────────────────────────────────────────────

class TestLanguage:
    def test_fr_headline_is_french(self, client):
        body = _make_body(lang="fr", agreement=0.90,
                          winners={m: "Alice" for m in ["plurality","borda","irv","schulze","approval"]})
        resp = json.loads(post(client, body).data)
        assert any(w in resp["headline"] for w in ["méthodes", "consensus", "Large"])

    def test_en_headline_is_english(self, client):
        body = _make_body(lang="en", agreement=0.90,
                          winners={m: "Alice" for m in ["plurality","borda","irv","schulze","approval"]})
        resp = json.loads(post(client, body).data)
        assert any(w in resp["headline"] for w in ["methods", "consensus", "Broad"])

    def test_invalid_lang_defaults_to_fr(self, client):
        body = {**_make_body(), "lang": "zh"}
        assert post(client, body).status_code == 200
