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


# ── The map's orientation ──────────────────────────────────────────────────

# numpy's SVD leaves each axis's sign to the LAPACK build: CPython's OpenBLAS and
# Pyodide's build mirrored Polis's second axis on the same votes (EXP-023). An SVD
# answering with the opposite signs must draw the same map.
@pytest.mark.parametrize("flip", [(1.0, -1.0), (-1.0, -1.0)])
def test_polis_map_does_not_take_its_axes_signs_from_lapack(monkeypatch, flip):
    import numpy as np

    from api.domain import tech

    votes = np.random.default_rng(3).integers(-1, 2, size=(40, 12)).astype(float)
    reference = tech._pca_2d(votes)
    svd = np.linalg.svd

    def mirrored(a, full_matrices=True):
        u, s, vt = svd(a, full_matrices=full_matrices)
        signs = np.ones(len(vt))
        signs[:2] = flip
        return u * signs, s, vt * signs[:, None]

    monkeypatch.setattr(np.linalg, "svd", mirrored)
    np.testing.assert_allclose(tech._pca_2d(votes), reference)


# A cluster's label is drawn at its center, on the same map as the participants' dots:
# both must be in the map's PCA frame (center.x used to be the members' mean ideology).
def test_polis_cluster_centers_sit_on_their_members(client):
    body = client.post("/api/v2/tech/polis", json=TestPolisWithCandidates.payload).json()
    for cluster in body["clusters"]:
        members = [p for p in body["participant_positions"] if p["cluster_id"] == cluster["id"]]
        mean_x = sum(p["x_pca"] for p in members) / len(members)
        mean_y = sum(p["y_pca"] for p in members) / len(members)
        assert abs(cluster["center"]["x"] - mean_x) < 2e-3
        assert abs(cluster["center"]["y"] - mean_y) < 2e-3
