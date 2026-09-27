"""Tests for POST /api/v2/election/simulate — the first endpoint migrated
from Flask to FastAPI in Phase 2 of the strategic refactor.

These tests pin behavioural parity with the Flask /api/election/simulate
endpoint, so the frontend can switch from v1 to v2 transparently.
"""
from api.domain.election import election_service



# ── Minimal valid payload reused across tests ───────────────────────────────

def _payload(**overrides) -> dict:
    base = {
        "candidates": [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
            {"name": "Carol", "x":  0.0, "y":  0.3},
        ],
        "num_voters": 30,
        "ideology":   "random",
        "seed":       42,
    }
    base.update(overrides)
    return base


# ── Happy path ───────────────────────────────────────────────────────────────

class TestSimulateHappyPath:
    def test_returns_200_with_top_level_keys(self, client):
        r = client.post("/api/v2/election/simulate", json=_payload())
        assert r.status_code == 200
        body = r.json()
        for key in (
            "config", "voters_snapshot", "candidates", "methods",
            "condorcet_winner", "blank_rate", "campaign_trajectory",
            "inter_method_agreement", "condorcet_exists",
        ):
            assert key in body, f"missing key: {key}"

    def test_runs_at_least_5_methods(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload()).json()
        assert len(body["methods"]) >= 5
        for md in body["methods"].values():
            assert "winner" in md

    def test_voter_snapshot_count_matches_num_voters(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload(num_voters=80)).json()
        assert len(body["voters_snapshot"]) == 80

    def test_inter_method_agreement_in_range(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload()).json()
        assert 0.0 <= body["inter_method_agreement"] <= 1.0


# ── Determinism — same seed = same result ──────────────────────────────────

class TestDeterminism:
    def test_same_seed_yields_identical_methods(self, client):
        r1 = client.post("/api/v2/election/simulate", json=_payload(seed=7)).json()
        r2 = client.post("/api/v2/election/simulate", json=_payload(seed=7)).json()
        assert r1["methods"] == r2["methods"]
        assert r1["voters_snapshot"] == r2["voters_snapshot"]

    def test_different_seed_may_differ(self, client):
        r1 = client.post("/api/v2/election/simulate", json=_payload(seed=1)).json()
        r2 = client.post("/api/v2/election/simulate", json=_payload(seed=999)).json()
        # Voters always differ on a different seed, methods often do too.
        assert r1["voters_snapshot"] != r2["voters_snapshot"]


# ── Validation rejected at the FastAPI boundary ─────────────────────────────

class TestValidation:
    def test_rejects_single_candidate_with_422(self, client):
        """Pydantic min_length=2 → FastAPI returns 422 (unprocessable entity)
        BEFORE the worker runs. That's stricter than the Flask side (which
        returned 400 from inside the worker)."""
        r = client.post("/api/v2/election/simulate", json=_payload(candidates=[
            {"name": "Solo", "x": 0.0, "y": 0.0},
        ]))
        assert r.status_code == 422
        assert "detail" in r.json()

    def test_rejects_x_out_of_range(self, client):
        r = client.post("/api/v2/election/simulate", json=_payload(candidates=[
            {"name": "A", "x":  2.0, "y": 0.0},
            {"name": "B", "x": -0.5, "y": 0.0},
        ]))
        assert r.status_code == 422

    def test_rejects_extra_fields(self, client):
        """extra='forbid' on the schema catches typos."""
        r = client.post("/api/v2/election/simulate", json={**_payload(), "Seed": 99})
        assert r.status_code == 422

    def test_rejects_too_many_candidates(self, client):
        many = [{"name": f"C{i}", "x": 0.0, "y": 0.0} for i in range(9)]
        r = client.post("/api/v2/election/simulate", json=_payload(candidates=many))
        assert r.status_code == 422

    def test_rejects_num_voters_above_cap(self, client):
        r = client.post("/api/v2/election/simulate", json=_payload(num_voters=99_999))
        assert r.status_code == 422


# ── Blank vote / campaign / information_model ──────────────────────────────

class TestPipelineOptions:
    def test_blank_vote_enables_winner_with_blank(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload(
            blank_vote={"enabled": True, "rule": "symbolic",
                        "contagion": {"enabled": False, "beta": 0.15,
                                      "gamma": 0.10, "network": "random"}}
        )).json()
        for md in body["methods"].values():
            assert "winner_with_blank" in md
            assert "blank_triggered" in md

    def test_blank_vote_contagion_enabled_still_returns_200(self, client):
        # simulate's own _apply_blank_contagion call only
        # runs when both blank_vote.enabled and contagion.enabled are set
        # (unlike the test above, which pins contagion off).
        r = client.post("/api/v2/election/simulate", json=_payload(
            blank_vote={"enabled": True, "rule": "symbolic",
                        "contagion": {"enabled": True, "beta": 0.15,
                                      "gamma": 0.10, "network": "random"}}
        ))
        assert r.status_code == 200, r.text
        body = r.json()
        for md in body["methods"].values():
            assert "winner_with_blank" in md

    def test_campaign_enabled_returns_trajectory(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload(
            campaign={"enabled": True, "num_days": 14, "polling_effect": 0.3}
        )).json()
        assert body["campaign_trajectory"] is not None


# ── election_service.simulate: branches the dedent exposed ────────────────────
# Flattening ElectionService to a module function re-indented the whole body, so
# diff-cover asked for every line. These three branches turned out to be real
# gaps in the main simulation entry point. They call the pure
# `election_service.simulate`, not the memoised `api.domain.election.simulate`.


class TestSimulateOptionalBranches:
    def _base(self, **over):
        return _payload(num_voters=120, **over)

    def test_one_candidate_is_a_400(self):
        """Defensive only: `SimulateRequest.candidates` has min_length=2, so
        over HTTP this is a 422 and the worker's own guard is unreachable. It
        still matters for the direct callers the module docstring advertises."""
        body, status = election_service.simulate(self._base(candidates=[]))
        assert status == 400
        assert "2 candidates" in body["error"]

    def test_media_bias_reaches_the_ballots(self):
        """The whole `info_enabled` branch was unreachable from any test.

        Comparing biased against plain would prove nothing: the information
        model adds seeded per-segment noise whenever it is enabled, so that
        assertion passes with `media_bias={}`. Both runs here have it enabled
        with identical segments, so the noise is held fixed and only the bias
        differs."""
        segments = {"low_info": 0.8, "medium_info": 0.15, "high_info": 0.05}

        def _winners(bias):
            body, status = election_service.simulate(self._base(information_model={
                "enabled": True, "media_bias": bias, "voter_segments": segments,
            }))
            assert status == 200
            return {m: r["winner"] for m, r in body["methods"].items()}

        pro_carol = _winners({"Carol": 0.9, "Alice": -0.9})
        pro_alice = _winners({"Carol": -0.9, "Alice": 0.9})
        assert pro_carol != pro_alice, (
            "flipping the media bias changed no method's winner -- media_bias "
            "is not reaching the ballots"
        )

    def test_an_unknown_blank_rule_does_not_500(self):
        """`BlankVoteRule(blank_rule_str)` raises on a name it does not know.
        The worker answers with SYMBOLIC rather than propagating.

        This pins the `except ValueError` path, not which rule was chosen: at
        any blank rate this electorate produces, no rule's trigger fires, so
        every BlankVoteRule member returns an identical body and no assertion
        here could tell them apart."""
        body, status = election_service.simulate(self._base(blank_vote={
            "enabled": True, "rule": "not_a_rule",
        }))
        assert status == 200
        assert body["methods"]
