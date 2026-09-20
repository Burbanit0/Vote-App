"""Tests for Phase 4.5.a.4 — public research API /api/v1 on FastAPI."""

import api.domain.public as public_module
from api.engine.utils.method_registry import PUBLIC_METHOD_ALIASES
from api.engine.utils.simulation_metrics import compare_all_methods


# ── GET /api/v1/methods ─────────────────────────────────────────────────────

class TestMethods:
    def test_returns_200(self, client):
        assert client.get("/api/v1/methods").status_code == 200

    def test_count_16_or_more(self, client):
        assert client.get("/api/v1/methods").json()["count"] >= 16

    def test_structure(self, client):
        data = client.get("/api/v1/methods").json()
        assert {"count", "methods", "families"} <= data.keys()
        for m in data["methods"]:
            assert {"key", "name", "family", "ref"} <= m.keys()

    def test_includes_standard_methods(self, client):
        keys = {m["key"] for m in client.get("/api/v1/methods").json()["methods"]}
        for key in ("plurality", "borda", "schulze", "irv", "approval", "condorcet"):
            assert key in keys, f"Missing method key: {key}"

    def test_includes_the_non_registry_extras(self, client):
        """quadratic, evaluative and random_ballot answer to no RANKED_RULES/
        SCORE_RULES key, but compare_all_methods computes all three (see
        method_registry.test_the_registry_answers_every_rule_the_engine_
        reports) -- they belong in the catalogue like any other real method."""
        keys = {m["key"] for m in client.get("/api/v1/methods").json()["methods"]}
        assert {"quadratic", "evaluative", "random_ballot"} <= keys

    def test_filter_by_family(self, client):
        data = client.get("/api/v1/methods?family=ranked").json()
        assert data["methods"]
        for m in data["methods"]:
            assert m["family"] == "ranked"

    def test_filter_by_the_lottery_family(self, client):
        data = client.get("/api/v1/methods?family=lottery").json()
        assert [m["key"] for m in data["methods"]] == ["random_ballot"]

    def test_methods_catalog_matches_what_compare_all_methods_computes(self):
        """METHODS_CATALOG used to be a third hand-maintained list beside the
        registry, and it drifted both ways: it advertised "positional_score"
        (no compare_all_methods key answers to that name -- filtering
        /simulate or /compare by it silently returned an empty methods dict)
        and stopped listing 16 rules the registry computes. This checks the
        catalogue against compare_all_methods' own real output rather than
        reconstructing an expected set from the registry by hand, so an
        engine addition that isn't a RANKED_RULES/SCORE_RULES entry (like
        "evaluative" and "random_ballot" were, until this test caught them
        missing too) still fails this test instead of passing it by
        construction. The one deliberate rewrite: PUBLIC_METHOD_ALIASES'
        "condorcet" is the catalogue's public name for the "copeland" key
        compare_all_methods actually reports."""
        names = ["A", "B", "C"]
        utils = {
            i: {n: float(u) for n, u in zip(names, row)}
            for i, row in enumerate([(1.0, 0.5, 0.0)] * 4 + [(0.0, 1.0, 0.5)] * 3)
        }
        computed = set(compare_all_methods(
            [{"id": v} for v in utils], [{"name": n} for n in names], [],
            override_utilities=utils,
        )["methods"])
        aliased_engine_names = set(PUBLIC_METHOD_ALIASES.values())  # {"copeland"}
        expected = (computed - aliased_engine_names) | set(PUBLIC_METHOD_ALIASES)
        assert set(public_module.METHODS_CATALOG) == expected


# ── POST /api/v1/simulate ───────────────────────────────────────────────────

class TestSimulate:
    def test_happy_path(self, client):
        r = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 80, "methods": ["plurality", "borda"],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert "methods" in body
        winner = body["methods"]["plurality"]["winner"]
        assert winner in ("Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo")

    def test_filters_requested_methods(self, client):
        body = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["borda", "schulze"],
        }).json()
        keys = set(body["methods"].keys())
        assert "borda" in keys and "schulze" in keys
        assert "plurality" not in keys

    def test_all_methods_when_not_specified(self, client):
        body = client.post("/api/v1/simulate",
                           json={"num_candidates": 3, "num_voters": 60}).json()
        assert len(body["methods"]) >= 10
        # Unfiltered, methods still report under the catalogue's public name
        # -- "condorcet", never the engine-internal "copeland" -- so a caller
        # reading GET /methods and then looking up body["methods"]["condorcet"]
        # on an unfiltered response finds it there too.
        assert "condorcet" in body["methods"]
        assert "copeland" not in body["methods"]

    def test_methods_all_in_a_list_is_not_filtered(self, client):
        """methods is schema-typed Union[Literal["all"], List[str]], so a
        caller can send `["all"]` -- a schema-valid List[str] -- and mean the
        same thing as the bare string "all". It used to filter by literal
        membership in that list, and no engine key is ever named "all", so
        every method was silently dropped."""
        body = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["all"],
        }).json()
        assert len(body["methods"]) >= 10

    def test_returns_condorcet_winner(self, client):
        body = client.post("/api/v1/simulate",
                           json={"num_candidates": 3, "num_voters": 100}).json()
        assert "condorcet_winner" in body

    def test_filtering_by_condorcet_resolves_to_copeland(self, client):
        """"condorcet" is the catalogue's public name for the registry's
        "copeland" rule -- compare_all_methods only ever reports the
        computation under "copeland", so filtering by "condorcet" alone used
        to return an empty methods dict even though GET /methods advertised
        it."""
        body = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["condorcet"],
        }).json()
        assert set(body["methods"]) == {"condorcet"}
        assert "winner" in body["methods"]["condorcet"]

    def test_requesting_both_alias_names_does_not_drop_either(self, client):
        """"condorcet" and "copeland" both resolve to the same engine key, so
        asking for both used to silently keep only whichever name the dict
        comprehension processed last -- dropping the other with no error and
        no signal that anything was lost."""
        body = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["condorcet", "copeland"],
        }).json()
        assert set(body["methods"]) == {"condorcet"}

    def test_returns_metrics(self, client):
        m = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["borda"],
        }).json()["methods"]["borda"]
        for key in ("winner", "bayesian_regret", "majority_satisfaction",
                    "condorcet_consistent"):
            assert key in m

    def test_strategic_vulnerability_is_off_by_default(self, client):
        """strategic_vulnerability re-tallies every ranked rule per sampled
        voter per manipulated permutation -- ~33,000 full re-runs at 8
        candidates, measured taking the whole request past the 180s worker
        timeout at the base num_voters cap with zero contention. It must stay
        opt-in, not silently reappear as a default cost."""
        m = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["borda"],
        }).json()["methods"]["borda"]
        assert m.get("strategic_vulnerability") is None

    def test_compute_strategic_opts_into_the_field(self, client):
        m = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["borda"],
            "compute_strategic": True,
        }).json()["methods"]["borda"]
        assert m.get("strategic_vulnerability") is not None

    def test_compute_strategic_lowers_the_num_voters_cap(self, client, monkeypatch):
        """The expensive metric's cost scales linearly with num_voters (each
        of ~33,000 re-tallies re-tallies the WHOLE electorate), so opting in
        lowers the cap from 2000 to _STRATEGIC_NUM_VOTERS_CAP (500) -- measured
        keeping the worst case (500 voters, 8 candidates) at ~48s, well under
        the 180s timeout, instead of the ~190s the uncapped combination hit.
        compare_all_methods is stubbed: only the capped population SIZE
        reaching _build_simple_population is under test here, not the actual
        metric, so this stays fast regardless of that real cost."""
        captured: dict[str, int] = {}
        real_build = public_module._build_simple_population

        def spy(num_voters, num_candidates, ideology="random"):
            captured["num_voters"] = num_voters
            return real_build(num_voters, num_candidates, ideology)

        monkeypatch.setattr(public_module, "_build_simple_population", spy)
        monkeypatch.setattr(public_module, "compare_all_methods",
                             lambda *a, **kw: {"methods": {"plurality": {"winner": None}}})
        r = client.post("/api/v1/simulate", json={
            "num_candidates": 2, "num_voters": 2000, "methods": ["plurality"],
            "compute_strategic": True,
        })
        assert r.status_code == 200, r.text
        assert captured["num_voters"] == public_module._STRATEGIC_NUM_VOTERS_CAP

    def test_invalid_num_candidates_type_422(self, client):
        # Non-int → Pydantic rejects with 422 (the FastAPI analogue of Flask's 400).
        assert client.post("/api/v1/simulate",
                           json={"num_candidates": "bad"}).status_code == 422

    def test_caps_num_voters_silently(self, client):
        # 99999 is clamped to 2000 by the worker, not rejected — 200 expected.
        r = client.post("/api/v1/simulate", json={
            "num_candidates": 2, "num_voters": 99999, "methods": ["plurality"],
        })
        assert r.status_code == 200, r.text

    def test_500_and_logs_on_compute_failure(self, client, monkeypatch, caplog):
        def _boom(*a, **kw):
            raise RuntimeError("engine exploded")
        monkeypatch.setattr(public_module, "compare_all_methods", _boom)
        with caplog.at_level("WARNING"):
            r = client.post("/api/v1/simulate", json={
                "num_candidates": 3, "num_voters": 60, "methods": ["plurality"],
            })
        assert r.status_code == 500
        assert "engine exploded" in r.json()["detail"]
        assert "public.simulate.failed" in caplog.text


# ── POST /api/v1/compare ────────────────────────────────────────────────────

class TestCompare:
    def test_returns_200(self, client):
        r = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["plurality"],
        })
        assert r.status_code == 200, r.text

    def test_with_blank_rule_exposes_blank_pct(self, client):
        body = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60,
            "blank_rule": "threshold_30", "methods": ["plurality"],
        }).json()
        assert "blank_pct" in body

    def test_blank_rule_applied_in_methods(self, client):
        body = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60,
            "blank_rule": "symbolic", "methods": ["plurality"],
        }).json()
        assert "blank_rule_applied" in body["methods"]["plurality"]

    def test_strategic_vulnerability_is_off_by_default(self, client):
        m = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["borda"],
        }).json()["methods"]["borda"]
        assert m.get("strategic_vulnerability") is None

    def test_compute_strategic_opts_into_the_field(self, client):
        m = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["borda"],
            "compute_strategic": True,
        }).json()["methods"]["borda"]
        assert m.get("strategic_vulnerability") is not None

    def test_compute_strategic_lowers_the_num_voters_cap(self, client, monkeypatch):
        """See TestSimulate's copy of this test for the full rationale (the
        cap, why it's 500, and why compare_all_methods is stubbed here too)."""
        captured: dict[str, int] = {}
        real_build = public_module._build_simple_population

        def spy(num_voters, num_candidates, ideology="random"):
            captured["num_voters"] = num_voters
            return real_build(num_voters, num_candidates, ideology)

        monkeypatch.setattr(public_module, "_build_simple_population", spy)
        monkeypatch.setattr(public_module, "compare_all_methods",
                             lambda *a, **kw: {"methods": {"plurality": {"winner": None}}})
        r = client.post("/api/v1/compare", json={
            "num_candidates": 2, "num_voters": 2000, "methods": ["plurality"],
            "compute_strategic": True,
        })
        assert r.status_code == 200, r.text
        assert captured["num_voters"] == public_module._STRATEGIC_NUM_VOTERS_CAP

    def test_filtering_by_condorcet_resolves_to_copeland(self, client):
        body = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["condorcet"],
        }).json()
        assert set(body["methods"]) == {"condorcet"}
        assert "winner" in body["methods"]["condorcet"]

    def test_blank_rule_applied_survives_the_condorcet_alias(self, client):
        """blank_rule_applied is stamped onto result["methods"]'s values
        before the alias rewrites "copeland" to "condorcet" -- a reordering
        that moved the rewrite first would silently stop stamping it under
        the requested name, with no error to catch it."""
        body = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60,
            "blank_rule": "symbolic", "methods": ["condorcet"],
        }).json()
        assert "blank_rule_applied" in body["methods"]["condorcet"]

    def test_invalid_blank_rule_400(self, client):
        r = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60, "blank_rule": "invalid_rule",
        })
        assert r.status_code == 400, r.text

    def test_500_and_logs_on_compute_failure(self, client, monkeypatch, caplog):
        def _boom(*a, **kw):
            raise RuntimeError("engine exploded")
        monkeypatch.setattr(public_module, "compare_all_methods", _boom)
        with caplog.at_level("WARNING"):
            r = client.post("/api/v1/compare", json={
                "num_candidates": 3, "num_voters": 60, "methods": ["plurality"],
            })
        assert r.status_code == 500
        assert "engine exploded" in r.json()["detail"]
        assert "public.compare.failed" in caplog.text


# ── GET /api/v1/real-elections ──────────────────────────────────────────────

class TestRealElections:
    def test_returns_200(self, client):
        assert client.get("/api/v1/real-elections").status_code == 200

    def test_structure(self, client):
        data = client.get("/api/v1/real-elections").json()
        assert data["count"] >= 4
        for e in data["elections"]:
            assert {"key", "name", "year", "country"} <= e.keys()
            assert isinstance(e["num_candidates"], int) and e["num_candidates"] >= 2


# ── GET /api/v1/openapi.json ────────────────────────────────────────────────

class TestOpenApi:
    def test_returns_200(self, client):
        assert client.get("/api/v1/openapi.json").status_code == 200

    def test_is_3_0_spec_with_paths(self, client):
        data = client.get("/api/v1/openapi.json").json()
        assert data["openapi"] == "3.0.0"
        assert "paths" in data and "info" in data
        for path in ("/api/v1/methods", "/api/v1/simulate", "/api/v1/compare"):
            assert path in data["paths"]


# ── Rate limiting (slowapi) ─────────────────────────────────────────────────

class TestRateLimits:
    def test_simulate_429_after_10(self, client):
        payload = {"num_candidates": 2, "num_voters": 50, "methods": ["plurality"]}
        codes = [client.post("/api/v1/simulate", json=payload).status_code
                 for _ in range(12)]
        assert 429 in codes, f"Expected 429 after 10 requests, got: {codes}"

    def test_compare_429_after_5(self, client):
        payload = {"num_candidates": 2, "num_voters": 50, "methods": ["plurality"]}
        codes = [client.post("/api/v1/compare", json=payload).status_code
                 for _ in range(7)]
        assert 429 in codes, f"Expected 429 after 5 requests, got: {codes}"
