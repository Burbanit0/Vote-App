"""Tests for Phase 4.5.a.3 — tech-democracy demos on FastAPI."""

import pytest



# ── /tech/e2e-demo ─────────────────────────────────────────────────────────


# ── /tech/polis-simulation ─────────────────────────────────────────────────


# ── /tech/polis ────────────────────────────────────────────────────────────

class TestPolisWithCandidates:
    payload = {
        "candidates": [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
            {"name": "Carol", "x":  0.0, "y":  0.1},
        ],
        "num_participants": 60,
        "ideology": "random",
        "seed": 42,
        "num_clusters": 3,
        "method_to_compare": "plurality",
    }

    @pytest.mark.parametrize("ideology", ["polarized", "centrist", "random"])
    def test_each_ideology_draws_its_own_participant_axis(self, client, ideology):
        """One branch per distribution, each drawing from the call's own RNG."""
        r = client.post("/api/v2/tech/polis", json={**self.payload, "ideology": ideology})
        assert r.status_code == 200, r.text

    def test_happy_path(self, client):
        r = client.post("/api/v2/tech/polis", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("clusters", "statements", "participant_positions",
                  "polis_winner", "election_winner", "winners_agree",
                  "candidate_scores", "pedagogical_note"):
            assert k in body

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [self.payload["candidates"][0]]}
        assert client.post("/api/v2/tech/polis", json=bad).status_code == 422

    def test_rejects_extra_field(self, client):
        bad = {**self.payload, "evil": 1}
        assert client.post("/api/v2/tech/polis", json=bad).status_code == 422

    def test_accepts_plain_string_statements(self, client):
        # The schema promises List[str] (not the internal default's
        # {"text", "category"} dict shape) — a plain string statement falls
        # back to the "default" category instead of crashing.
        req = {**self.payload, "statements": ["Statement A", "Statement B"]}
        r = client.post("/api/v2/tech/polis", json=req)
        assert r.status_code == 200, r.text
        texts = [s["text"] for s in r.json()["statements"]]
        assert texts == ["Statement A", "Statement B"]
