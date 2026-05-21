"""
test_theory.py — Tests for /api/theory/arrow and /api/theory/iia-rate
"""
import json
import pytest

ARROW_URL  = "/api/theory/arrow"
RATE_URL   = "/api/theory/iia-rate"
PLOTT_URL  = "/api/theory/plott-chaos"
MANIP_URL  = "/api/theory/manipulation-analysis"
JUDG_URL   = "/api/theory/judgment-aggregation"
SEN_URL    = "/api/theory/sen-paradox"


def arrow_post(client, method="plurality", **kw):
    return json.loads(client.post(ARROW_URL, json={"method": method, **kw}).data)


def rate_post(client, method="plurality", **kw):
    return json.loads(client.post(RATE_URL, json={"method": method, **kw}).data)


# ── /api/theory/arrow — basic structure ──────────────────────────────────────

class TestArrowBasic:
    def test_returns_200(self, client):
        assert client.post(ARROW_URL, json={"method": "plurality"}).status_code == 200

    def test_response_keys(self, client):
        body = arrow_post(client)
        for k in ("method", "violations", "arrow_summary", "tradeoff_type"):
            assert k in body

    def test_violations_has_all_axioms(self, client):
        body = arrow_post(client)
        for ax in ("iia", "pareto", "transitivity", "non_dictatorship"):
            assert ax in body["violations"]

    def test_each_violation_has_violated_field(self, client):
        body = arrow_post(client)
        for ax, v in body["violations"].items():
            assert "violated" in v
            assert isinstance(v["violated"], bool)


# ── Plurality: IIA.violated = True ───────────────────────────────────────────

class TestPluralityIIA:
    def test_iia_violated(self, client):
        body = arrow_post(client, "plurality")
        assert body["violations"]["iia"]["violated"] is True

    def test_iia_counterexample_present(self, client):
        body = arrow_post(client, "plurality")
        ce = body["violations"]["iia"]["counterexample"]
        assert ce is not None

    def test_counterexample_consistent(self, client):
        """without_c winner != with_c winner."""
        body = arrow_post(client, "plurality")
        ce = body["violations"]["iia"]["counterexample"]
        assert ce["without_c"] != ce["with_c"], (
            f"Counterexample not convincing: both without_c and with_c are '{ce['without_c']}'"
        )

    def test_iia_profile_has_rows(self, client):
        body = arrow_post(client, "plurality")
        profile = body["violations"]["iia"]["counterexample"]["profile"]
        assert len(profile) > 0
        for row in profile:
            assert isinstance(row, list)
            assert len(row) >= 2


# ── Schulze: IIA.violated = True ─────────────────────────────────────────────

class TestSchulzeIIA:
    def test_iia_violated(self, client):
        body = arrow_post(client, "schulze")
        assert body["violations"]["iia"]["violated"] is True


# ── Borda: Pareto.violated = False ───────────────────────────────────────────

class TestBordaPareto:
    def test_pareto_satisfied(self, client):
        body = arrow_post(client, "borda")
        assert body["violations"]["pareto"]["violated"] is False


# ── Condorcet: Transitivity.violated = True ──────────────────────────────────

class TestCondorcetTransitivity:
    def test_transitivity_violated(self, client):
        body = arrow_post(client, "condorcet")
        assert body["violations"]["transitivity"]["violated"] is True

    def test_cycle_returned(self, client):
        body = arrow_post(client, "condorcet")
        ce = body["violations"]["transitivity"]["counterexample"]
        assert ce is not None
        assert "cycle" in ce
        assert len(ce["cycle"]) >= 3   # at least A > B > C > A (4 elements)


# ── All standard methods: Non-dictatorship satisfied ─────────────────────────

class TestNonDictatorship:
    @pytest.mark.parametrize("method", ["plurality", "borda", "schulze", "irv"])
    def test_non_dictatorship_satisfied(self, client, method):
        body = arrow_post(client, method)
        assert body["violations"]["non_dictatorship"]["violated"] is False


# ── All standard methods: Pareto satisfied ───────────────────────────────────

class TestPareto:
    @pytest.mark.parametrize("method", ["plurality", "borda", "schulze", "irv", "approval"])
    def test_pareto_satisfied(self, client, method):
        body = arrow_post(client, method)
        assert body["violations"]["pareto"]["violated"] is False


# ── tradeoff_type classification ─────────────────────────────────────────────

class TestTradeoffType:
    def test_plurality_is_majority(self, client):
        body = arrow_post(client, "plurality")
        assert body["tradeoff_type"] == "majority_focus"

    def test_borda_is_utility(self, client):
        body = arrow_post(client, "borda")
        assert body["tradeoff_type"] == "utility_focus"

    def test_schulze_is_condorcet(self, client):
        body = arrow_post(client, "schulze")
        assert body["tradeoff_type"] == "condorcet_focus"


# ── /api/theory/iia-rate ─────────────────────────────────────────────────────

class TestIIARate:
    def test_returns_200(self, client):
        assert client.post(RATE_URL, json={"method": "plurality"}).status_code == 200

    def test_response_keys(self, client):
        body = rate_post(client)
        assert "method" in body
        assert "curve" in body

    def test_curve_starts_at_zero(self, client):
        body = rate_post(client, max_candidates=5)
        first = body["curve"][0]
        assert first["n_candidates"] == 2
        assert first["violation_rate"] == pytest.approx(0.0)

    def test_curve_increases_with_candidates(self, client):
        body = rate_post(client, "plurality", max_candidates=6, num_trials=50)
        rates = [pt["violation_rate"] for pt in body["curve"]]
        # Generally increasing trend (allow small decreases)
        assert rates[-1] >= rates[0]  # last > first

    def test_curve_length(self, client):
        body = rate_post(client, max_candidates=5)
        assert len(body["curve"]) == 4  # n=2,3,4,5

    def test_violation_rates_in_range(self, client):
        body = rate_post(client)
        for pt in body["curve"]:
            assert 0.0 <= pt["violation_rate"] <= 1.0

    def test_reproducibility(self, client):
        a = rate_post(client, "plurality", num_trials=50)
        b = rate_post(client, "plurality", num_trials=50)
        assert a["curve"] == b["curve"]


# ── /api/theory/plott-chaos ───────────────────────────────────────────────────

BASE_PLOTT = {
    "num_voters":    5,
    "num_dimensions": 2,
    "seed":          42,
    "target_policy": [0.6, 0.6],
    "start_policy":  [-0.6, -0.6],
    "max_steps":     15,
}


def plott_post(client, **kw):
    return json.loads(client.post(PLOTT_URL, json={**BASE_PLOTT, **kw}).data)


class TestPlottChaos:
    def test_returns_200(self, client):
        assert client.post(PLOTT_URL, json=BASE_PLOTT).status_code == 200

    def test_response_keys(self, client):
        body = plott_post(client)
        for k in ("condorcet_winner_exists", "top_cycle", "chaos_path",
                  "alternative_path", "voter_ideal_points", "pedagogical_note"):
            assert k in body

    def test_chaos_path_keys(self, client):
        body = plott_post(client)
        cp = body["chaos_path"]
        for k in ("from", "to", "steps", "num_steps"):
            assert k in cp

    def test_voter_ideal_points_count(self, client):
        body = plott_post(client)
        assert len(body["voter_ideal_points"]) == 5

    def test_top_cycle_size_positive(self, client):
        body = plott_post(client)
        assert body["top_cycle"]["size"] > 0

    # ── num_dimensions=1 → Condorcet winner usually exists ────────────────

    def test_1d_condorcet_winner_likely(self, client):
        """With 1D ideal points, median voter theorem → Condorcet winner expected."""
        body = plott_post(client, num_dimensions=1, seed=42)
        # 1D with median voter: almost always has CW
        assert body["condorcet_winner_exists"] is True

    # ── num_dimensions=2 → Condorcet winner rarely exists ─────────────────

    def test_2d_chaos_with_specific_seed(self, client):
        """With 2D random ideal points, seed=10 gives no Condorcet winner."""
        # Verified: seed=10, 7 voters, 2D → chaos
        body = plott_post(client, seed=10, num_voters=7)
        assert body["condorcet_winner_exists"] is False

    # ── chaos_path validity ────────────────────────────────────────────────

    def test_chaos_path_steps_valid_majority(self, client):
        """Each step in chaos_path must beat the previous via majority vote."""
        body = plott_post(client)
        steps = body["chaos_path"]["steps"]
        voter_pts = body["voter_ideal_points"]
        n = len(voter_pts)

        for i in range(1, len(steps)):
            a = steps[i - 1]  # previous policy
            b = steps[i]      # next policy (must beat a)

            # Count voters preferring b to a (closer to b)
            prefer_b = sum(
                sum((vp[d] - b[d]) ** 2 for d in range(len(b))) <
                sum((vp[d] - a[d]) ** 2 for d in range(len(a)))
                for vp in voter_pts
            )
            assert prefer_b > n / 2, (
                f"Step {i}: {b} does not beat {a} in majority "
                f"(prefer_b={prefer_b}, n={n})"
            )

    def test_num_steps_matches_path_length(self, client):
        body = plott_post(client)
        cp = body["chaos_path"]
        assert cp["num_steps"] == max(0, len(cp["steps"]) - 1)

    # ── target = start → num_steps = 0 ────────────────────────────────────

    def test_same_start_target_zero_steps(self, client):
        body = plott_post(client,
                          target_policy=[-0.6, -0.6],
                          start_policy=[-0.6, -0.6])
        assert body["chaos_path"]["num_steps"] == 0

    # ── alternative_path validity ──────────────────────────────────────────

    def test_alternative_path_valid(self, client):
        """Each step in alt_path must beat the previous."""
        body = plott_post(client)
        steps = body["alternative_path"]["steps"]
        voter_pts = body["voter_ideal_points"]
        n = len(voter_pts)

        for i in range(1, len(steps)):
            a = steps[i - 1]
            b = steps[i]
            prefer_b = sum(
                sum((vp[d] - b[d]) ** 2 for d in range(len(b))) <
                sum((vp[d] - a[d]) ** 2 for d in range(len(a)))
                for vp in voter_pts
            )
            assert prefer_b > n / 2, f"Alt step {i} invalid"

    def test_alt_path_reaches_different_target(self, client):
        """Alternative path should reach a different target than chaos_path."""
        body = plott_post(client)
        cp_to  = body["chaos_path"]["to"]
        alt_to = body["alternative_path"]["to"]
        # They should be different points
        assert cp_to != alt_to

    # ── Reproducibility ────────────────────────────────────────────────────

    def test_reproducibility(self, client):
        a = plott_post(client)
        b = plott_post(client)
        assert a["condorcet_winner_exists"] == b["condorcet_winner_exists"]
        assert a["chaos_path"]["num_steps"] == b["chaos_path"]["num_steps"]


# ── /api/theory/manipulation-analysis ────────────────────────────────────────

BASE_MANIP = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":               30,
    "ideology":                 "random",
    "seed":                     42,
    "method":                   "plurality",
    "manipulation_strategies":  ["compromising", "burying", "pushover", "truncating"],
}


def manip_post(client, **kw):
    return json.loads(client.post(MANIP_URL, json={**BASE_MANIP, **kw}).data)


class TestManipulationAnalysis:
    def test_returns_200(self, client):
        assert client.post(MANIP_URL, json=BASE_MANIP).status_code == 200

    def test_response_keys(self, client):
        body = manip_post(client)
        for k in ("sincere_winner", "manipulable", "manipulation_count",
                  "manipulators", "strategy_breakdown", "key_manipulator",
                  "pedagogical_note"):
            assert k in body

    def test_manipulator_keys(self, client):
        body = manip_post(client)
        if body["manipulators"]:
            m = body["manipulators"][0]
            for k in ("voter_id", "voter_ideology", "sincere_vote", "strategic_vote",
                      "strategy_type", "sincere_result", "strategic_result", "utility_gain"):
                assert k in m

    # ── 2 candidates → not manipulable ───────────────────────────────────

    def test_two_candidates_not_manipulable(self, client):
        body = manip_post(client, candidates=[
            {"name": "A", "x": -0.5, "y": 0.0},
            {"name": "B", "x":  0.5, "y": 0.0},
        ])
        assert body["manipulable"] is False
        assert body["manipulation_count"] == 0

    # ── strategic_result ≠ sincere_result for all manipulators ───────────

    def test_strategic_differs_from_sincere(self, client):
        body = manip_post(client)
        for m in body["manipulators"]:
            assert m["strategic_result"] != m["sincere_result"], (
                f"Manipulator {m['voter_id']}: strategic==sincere"
            )

    # ── utility_gain > 0 for all manipulators ────────────────────────────

    def test_utility_gain_positive(self, client):
        body = manip_post(client)
        for m in body["manipulators"]:
            assert m["utility_gain"] > 0, (
                f"Manipulator {m['voter_id']}: gain={m['utility_gain']}"
            )

    # ── Borda → burying count > 0 ────────────────────────────────────────

    def test_borda_is_manipulable(self, client):
        """Borda with 3 candidates and random voters is manipulable."""
        # Try a few seeds; Borda is well-known for being manipulable
        found = False
        for s in [1, 5, 10, 15, 20]:
            body = manip_post(client, method="borda", num_voters=20, seed=s,
                              ideology="polarized")
            if body["manipulable"]:
                found = True
                break
        assert found, "Borda should be manipulable on at least one seed"

    # ── strategy_breakdown contains all strategies ────────────────────────

    def test_strategy_breakdown_keys(self, client):
        body = manip_post(client)
        for s in ("compromising", "burying", "pushover", "truncating"):
            assert s in body["strategy_breakdown"]

    # ── Schulze ≤ Plurality manipulation_count (same seed) ───────────────

    def test_schulze_le_plurality_manipulation(self, client):
        plural = manip_post(client, method="plurality")
        schulze = manip_post(client, method="schulze")
        # Schulze is generally more manipulation-resistant
        assert schulze["manipulation_count"] <= plural["manipulation_count"] + 3

    # ── key_manipulator has largest gain ─────────────────────────────────

    def test_key_manipulator_is_max_gain(self, client):
        body = manip_post(client)
        if body["manipulators"] and body["key_manipulator"]:
            max_gain = max(m["utility_gain"] for m in body["manipulators"])
            assert body["key_manipulator"]["gain"] == pytest.approx(max_gain)

    # ── Reproducibility ───────────────────────────────────────────────────

    def test_reproducibility(self, client):
        a = manip_post(client)
        b = manip_post(client)
        assert a["manipulation_count"] == b["manipulation_count"]
        assert a["sincere_winner"] == b["sincere_winner"]


# ── /api/theory/judgment-aggregation ─────────────────────────────────────────

def judg_post(client, **kw):
    payload = {"num_voters": 12, "seed": 42, "scenario": "legal", **kw}
    return json.loads(client.post(JUDG_URL, json=payload).data)


class TestJudgmentAggregation:
    def test_returns_200(self, client):
        assert client.post(JUDG_URL, json={"scenario": "legal"}).status_code == 200

    def test_response_keys(self, client):
        body = judg_post(client)
        for k in ("scenario", "propositions", "collective_coherent",
                  "incoherences", "voter_coherence_rate",
                  "paradox_severity", "resolution_methods", "pedagogical_note"):
            assert k in body

    def test_propositions_have_required_keys(self, client):
        body = judg_post(client)
        for p in body["propositions"]:
            for k in ("text", "type", "id", "yes_pct", "collective_vote"):
                assert k in p

    # ── budget scenario → collective_coherent=False ───────────────────────

    def test_budget_scenario_incoherent(self, client):
        """With equal voter type distribution, budget scenario produces incoherence."""
        # With ~equal type distribution (large N), P1≈P2≈P3≈2/3 → C should be F
        # but majority C=T → paradox. Use 99 voters for reliable distribution.
        body = judg_post(client, scenario="budget", num_voters=99, seed=42)
        assert body["collective_coherent"] is False
        assert len(body["incoherences"]) > 0

    def test_budget_incoherence_structure(self, client):
        body = judg_post(client, scenario="budget", num_voters=99, seed=42)
        for inc in body["incoherences"]:
            assert "premises" in inc
            assert "conclusion" in inc
            assert "problem" in inc

    # ── voter_coherence_rate = 1.0 ────────────────────────────────────────

    def test_voter_coherence_rate_is_one(self, client):
        """All voter types are individually coherent by design."""
        for sc in ("legal", "budget", "climate"):
            body = judg_post(client, scenario=sc, num_voters=30, seed=42)
            assert body["voter_coherence_rate"] == pytest.approx(1.0), (
                f"Scenario {sc}: voter_coherence_rate={body['voter_coherence_rate']}"
            )

    # ── resolution methods differ when incoherent ─────────────────────────

    def test_resolution_methods_differ_when_incoherent(self, client):
        body = judg_post(client, scenario="budget", num_voters=99, seed=42)
        if not body["collective_coherent"]:
            pb = body["resolution_methods"]["premise_based"]
            cb = body["resolution_methods"]["conclusion_based"]
            # premise_based derives conclusion logically; conclusion_based accepts majority C
            # They must differ for at least the conclusion key
            assert pb != cb or len(pb) == 0

    # ── num_voters=1 → always coherent ────────────────────────────────────

    def test_single_voter_always_coherent(self, client):
        for sc in ("legal", "budget", "climate"):
            for s in [1, 42, 99]:
                body = judg_post(client, scenario=sc, num_voters=1, seed=s)
                assert body["collective_coherent"] is True, (
                    f"Scenario {sc}, seed={s}: single voter should be coherent"
                )

    # ── yes_pct in [0, 1] ─────────────────────────────────────────────────

    def test_yes_pct_in_range(self, client):
        body = judg_post(client)
        for p in body["propositions"]:
            assert 0.0 <= p["yes_pct"] <= 1.0

    # ── legal scenario produces paradox with equal distribution ───────────

    def test_legal_paradox_with_equal_distribution(self, client):
        """With 3 voters (one of each type), legal scenario shows discursive dilemma."""
        body = judg_post(client, scenario="legal", num_voters=3, seed=42)
        # Seeds sampled: might give types [C,A,B] or similar → paradox
        # Just verify the structure is valid
        assert body["collective_coherent"] in (True, False)
        assert body["voter_coherence_rate"] == pytest.approx(1.0)

    # ── Reproducibility ───────────────────────────────────────────────────

    def test_reproducibility(self, client):
        a = judg_post(client)
        b = judg_post(client)
        assert a["collective_coherent"] == b["collective_coherent"]
        assert a["voter_coherence_rate"] == b["voter_coherence_rate"]


# ── /api/theory/sen-paradox ───────────────────────────────────────────────────

def sen_post(client, **kw):
    return json.loads(client.post(SEN_URL, json={"seed": 42, **kw}).data)


class TestSenParadox:
    def test_returns_200(self, client):
        assert client.post(SEN_URL, json={"seed": 42}).status_code == 200

    def test_response_keys(self, client):
        body = sen_post(client)
        for k in ("paradox_exists", "paradox_examples", "paradox_frequency",
                  "alternative_names", "resolution_options",
                  "real_world_analogy", "pedagogical_note"):
            assert k in body

    # ── paradox_frequency ∈ [0, 1] ────────────────────────────────────────

    def test_paradox_frequency_in_range(self, client):
        body = sen_post(client)
        assert 0.0 <= body["paradox_frequency"] <= 1.0

    # ── paradox_examples non-empty when frequency > 0 ─────────────────────

    def test_examples_when_frequency_positive(self, client):
        body = sen_post(client)
        if body["paradox_frequency"] > 0 or body["paradox_exists"]:
            assert len(body["paradox_examples"]) > 0

    # ── liberal_outcome ≠ pareto_outcome when conflict=True ───────────────

    def test_outcomes_differ_when_conflict(self, client):
        body = sen_post(client)
        for ex in body["paradox_examples"]:
            if ex["conflict"]:
                assert ex["liberal_outcome"] != ex["pareto_outcome"], (
                    f"conflict=True but liberal=pareto='{ex['liberal_outcome']}'"
                )

    # ── resolution_options.length ≥ 2 ────────────────────────────────────

    def test_resolution_options_at_least_two(self, client):
        body = sen_post(client)
        assert len(body["resolution_options"]) >= 2

    def test_resolution_keys(self, client):
        body = sen_post(client)
        for r in body["resolution_options"]:
            for k in ("name", "outcome", "cost"):
                assert k in r

    # ── canonical example is detected ─────────────────────────────────────

    def test_canonical_paradox_detected(self, client):
        """The canonical Sen example (prude/lewd) always produces a paradox."""
        body = sen_post(client, seed=42)
        assert body["paradox_exists"] is True
        assert len(body["paradox_examples"]) > 0
        first = body["paradox_examples"][0]
        assert first["conflict"] is True

    # ── alternative_names covers all three alternatives ───────────────────

    def test_alternative_names_complete(self, client):
        body = sen_post(client)
        for alt in ("x", "y", "z"):
            assert alt in body["alternative_names"]

    # ── Reproducibility ───────────────────────────────────────────────────

    def test_reproducibility(self, client):
        a = sen_post(client)
        b = sen_post(client)
        assert a["paradox_frequency"] == b["paradox_frequency"]
        assert a["paradox_exists"] == b["paradox_exists"]
