"""Tests for Phase 4.5.a.8 — simulation_advanced on FastAPI (/api/v2/simulations)."""
import pytest
from fastapi.testclient import TestClient

from api.main import app

CANDS = ["Alice", "Bob", "Charlie"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestBandwagon:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/bandwagon",
                        json={"num_voters": 60, "candidates": CANDS, "num_rounds": 3, "seed": 1})
        assert r.status_code == 200, r.text

    def test_too_few_candidates_400(self, client):
        r = client.post("/api/v2/simulations/bandwagon",
                        json={"num_voters": 60, "candidates": ["Solo"]})
        assert r.status_code == 400, r.text

    def test_same_seed_reproducible_end_to_end(self, client):
        """Complement (2026-09-12, second `/code-review ultra` pass): this is
        the test that catches the live-path gap that
        `run_bandwagon_simulation()`-only tests (test_seeded_rng_isolation.py)
        cannot — `_bandwagon_worker` used to call `_build_population
        (candidate_configs, 0, ideology_dist)` with no `rng`/`np_rng`, then
        pass the resulting, already-built `candidates` list into
        `run_bandwagon_simulation(candidates=candidates, ...)`. Because
        `candidates` was not `None`, `run_bandwagon_simulation`'s own
        `if candidates is None:` branch — where its `rng`/`np_rng` threading
        for candidate creation lives — was skipped entirely on this, the only
        real call path (POST /simulations/bandwagon). Voters were unaffected
        (built unconditionally, with `rng`/`np_rng`, regardless of that
        branch), so calling `run_bandwagon_simulation` directly with
        `candidates=None` (as every existing test does) could never surface
        this: only a caller that pre-builds candidates the way
        `_bandwagon_worker` does can.

        Goes through the real HTTP endpoint (not just `_bandwagon_worker`
        directly) with `num_rounds >= 1` and explicit `candidates`, matching
        the exact request shape `POST /simulations/bandwagon` sends
        (`BandwagonRequest`'s fields) — the two rounds also exercise the
        `apply_social_influence()` reproducibility fix from the same pass.

        Confirmed red against the pre-fix `_bandwagon_worker` (no `rng`/
        `np_rng` passed to `_build_population`): injecting a simulated
        concurrent caller's draws on the shared `random`/`np.random`
        singletons between the two requests changed the response body every
        time. Green after threading `rng`/`np_rng` through.
        """
        payload = {
            "num_voters": 40,
            "num_rounds": 2,
            "influence_strength": 0.3,
            "ideology_distribution": "random",
            "seed": 13,
            "candidates": CANDS,
        }
        first = client.post("/api/v2/simulations/bandwagon", json=payload)
        second = client.post("/api/v2/simulations/bandwagon", json=payload)

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert second.json() == first.json()

    def test_candidate_and_voter_streams_share_one_rng_pair(self, client, monkeypatch):
        """MUST FIX (third `/code-review ultra` pass, 2026-09-12; essentially
        all 7 independent review agents converged on this): before this fix,
        `_bandwagon_worker` built its own `(rng, np_rng)` pair from
        `seed_int` to seed candidate creation via `_build_population(...)`,
        then called `run_bandwagon_simulation(candidates=candidates,
        seed=seed_int, ...)` — passing the bare *seed integer*, not the RNG
        instances. `run_bandwagon_simulation` unconditionally derived its OWN
        SECOND `(rng, np_rng)` pair from that same seed value for voter
        creation. `random.Random(N)` instantiated twice produces
        byte-identical draw sequences (verified directly:
        `random.Random(13)` built twice yields the same first three
        `.random()` values), so the live endpoint's candidate-draw stream and
        voter-draw stream were two clones of the same sequence restarted from
        position zero, not independent — invisible to every reproducibility
        test (same seed -> same result held either way, including the test
        directly above this one) but a real bug for anything assuming
        candidate/voter randomness is independent (e.g. a seed-sweep
        sensitivity analysis).

        This targets the root cause directly rather than trying to prove the
        statistical independence property indirectly: `_seeded_rng_pair` is
        imported separately into both `api.domain.simulations.advanced` (for
        candidates) and `api.engine.utils.simulation_voting_utils` (for
        voters, when not given a pre-built pair) — this test spies on both
        bindings and asserts the combined call count is exactly ONE per
        request when a seed is supplied, i.e. one continuous pair is built
        and threaded through both candidate and voter creation, not two
        independently-constructed clones.

        Confirmed red against the pre-fix code (2 calls: one in
        `_bandwagon_worker`, one inside `run_bandwagon_simulation`); green
        after (1 call — `_bandwagon_worker` builds it once and passes
        `rng=`/`np_rng=` into `run_bandwagon_simulation`, which then skips
        deriving its own).
        """
        import api.domain.simulations.advanced as advanced_mod
        import api.engine.utils.simulation_voting_utils as svu_mod
        from api.engine.utils.demographic_data import _seeded_rng_pair as real_seeded_rng_pair

        calls = {"count": 0}

        def _counting_wrapper(seed):
            calls["count"] += 1
            return real_seeded_rng_pair(seed)

        monkeypatch.setattr(advanced_mod, "_seeded_rng_pair", _counting_wrapper)
        monkeypatch.setattr(svu_mod, "_seeded_rng_pair", _counting_wrapper)

        r = client.post("/api/v2/simulations/bandwagon",
                        json={"num_voters": 40, "candidates": CANDS, "num_rounds": 1, "seed": 13})

        assert r.status_code == 200, r.text
        assert calls["count"] == 1


class TestMonteCarlo:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/monte-carlo",
                        json={"num_runs": 5, "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["num_runs"] == 5 and "methods" in body

    def test_too_few_candidates_400(self, client):
        r = client.post("/api/v2/simulations/monte-carlo",
                        json={"num_runs": 5, "candidates": ["Solo"]})
        assert r.status_code == 400, r.text


class TestMultiwinner:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/multiwinner",
                        json={"party_votes": {"A": 40, "B": 35, "C": 25}, "num_seats": 10})
        assert r.status_code == 200, r.text
        assert r.json()["num_seats"] == 10

    def test_empty_party_votes_400(self, client):
        r = client.post("/api/v2/simulations/multiwinner", json={"party_votes": {}, "num_seats": 10})
        assert r.status_code == 400, r.text

    def test_stv_mode_runs_single_transferable_vote(self, client):
        """mode='stv' synthesizes ranked ballots and elects via STV, in
        addition to the party-list methods run for every mode."""
        r = client.post("/api/v2/simulations/multiwinner",
                        json={"party_votes": {"A": 40, "B": 35, "C": 25}, "num_seats": 3, "mode": "stv"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "stv" in body
        assert len(body["stv"]["winners"]) == 3
        assert set(body["stv"]["winners"]) <= {"A", "B", "C"}


class TestRealElections:
    def test_list(self, client):
        r = client.get("/api/v2/simulations/real-elections")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list) and r.json()


class TestBlankHistory:
    def test_france(self, client):
        r = client.get("/api/v2/simulations/blank-history", params={"country": "france"})
        assert r.status_code == 200, r.text
        assert "series" in r.json()

    def test_missing_country_400(self, client):
        r = client.get("/api/v2/simulations/blank-history")
        assert r.status_code == 400, r.text

    def test_unknown_country_404(self, client):
        r = client.get("/api/v2/simulations/blank-history", params={"country": "atlantis"})
        assert r.status_code == 404, r.text


class TestRealElection:
    def test_happy_path(self, client):
        key = client.get("/api/v2/simulations/real-elections").json()[0]["key"]
        r = client.post("/api/v2/simulations/real-election",
                        json={"election_name": key, "num_voters": 200})
        assert r.status_code == 200, r.text

    def test_missing_name_400(self, client):
        r = client.post("/api/v2/simulations/real-election", json={"num_voters": 200})
        assert r.status_code == 400, r.text

    def test_unknown_election_404(self, client):
        r = client.post("/api/v2/simulations/real-election",
                        json={"election_name": "no_such_election", "num_voters": 200})
        assert r.status_code == 404, r.text

    def test_blank_vote_adds_symbolic_rule_interpretation(self, client):
        key = client.get("/api/v2/simulations/real-elections").json()[0]["key"]
        r = client.post("/api/v2/simulations/real-election",
                        json={"election_name": key, "num_voters": 200, "blank_vote": True})
        assert r.status_code == 200, r.text
        body = r.json()

        methods_with_blank = body["methods_with_blank"]
        methods_with_blank_rule = body["methods_with_blank_rule"]
        assert methods_with_blank is not None
        assert methods_with_blank_rule is not None
        assert set(methods_with_blank_rule) == set(methods_with_blank)

        for method, raw_winner in methods_with_blank.items():
            entry = methods_with_blank_rule[method]
            assert entry["rule"] == "symbolic"
            if raw_winner == "Blank":
                # SYMBOLIC: blank cannot be elected, regardless of raw winner.
                assert entry["winner"] is None
                assert entry["blank_triggered"] is True
            else:
                assert entry["winner"] == raw_winner
                assert entry["blank_triggered"] is False

    def test_no_blank_vote_leaves_blank_fields_none(self, client):
        key = client.get("/api/v2/simulations/real-elections").json()[0]["key"]
        r = client.post("/api/v2/simulations/real-election",
                        json={"election_name": key, "num_voters": 200})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["methods_with_blank"] is None
        assert body["methods_with_blank_rule"] is None

    def test_blank_rule_is_caller_selectable(self, client):
        key = client.get("/api/v2/simulations/real-elections").json()[0]["key"]
        r = client.post("/api/v2/simulations/real-election",
                        json={"election_name": key, "num_voters": 200,
                              "blank_vote": True, "blank_rule": "competitive"})
        assert r.status_code == 200, r.text
        body = r.json()

        methods_with_blank = body["methods_with_blank"]
        methods_with_blank_rule = body["methods_with_blank_rule"]

        for method, raw_winner in methods_with_blank.items():
            entry = methods_with_blank_rule[method]
            assert entry["rule"] == "competitive"
            # COMPETITIVE never overrides the raw winner (blank may win outright).
            assert entry["winner"] == raw_winner
            assert entry["blank_triggered"] == (raw_winner == "Blank")


class TestConstitutionalScenario:
    initial = {
        "candidates": [
            {"name": "A", "ideology": -0.5, "positions": {"economy": 0.3}},
            {"name": "B", "ideology": 0.5, "positions": {"economy": 0.7}},
        ],
        "electorate": {"num_voters": 60, "ideology_preset": "random"},
        "blank_rule": "competitive",
    }

    def test_new_election(self, client):
        r = client.post("/api/v2/simulations/constitutional-scenario",
                        json={"initial_election": self.initial, "scenario_type": "new_election"})
        assert r.status_code == 200, r.text
        assert r.json()["scenario_type"] == "new_election"

    def test_unknown_scenario_type_400(self, client):
        r = client.post("/api/v2/simulations/constitutional-scenario",
                        json={"initial_election": self.initial, "scenario_type": "bogus"})
        assert r.status_code == 400, r.text

    def test_too_few_candidates_400(self, client):
        bad = {**self.initial, "candidates": [self.initial["candidates"][0]]}
        r = client.post("/api/v2/simulations/constitutional-scenario",
                        json={"initial_election": bad, "scenario_type": "new_election"})
        assert r.status_code == 400, r.text

    def test_dissolution(self, client):
        """Dissolution derives party votes from first-choice utilities, runs the
        multiwinner comparison, and writes a conclusion naming the most
        proportional method and the uninominal (plurality) winner."""
        r = client.post("/api/v2/simulations/constitutional-scenario",
                        json={"initial_election": self.initial, "scenario_type": "dissolution"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["scenario_type"] == "dissolution"
        assert body["uninominal_winner"] in {"A", "B"}
        assert body["uninominal_winner"] in body["conclusion"]
        assert str(body["num_seats"]) in body["conclusion"]


class TestBlankContagion:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/blank-contagion",
                        json={"num_voters": 60, "num_rounds": 5, "seed": 1})
        assert r.status_code == 200, r.text
