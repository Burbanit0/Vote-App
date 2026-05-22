"""
test_power_indices.py — Tests for POST /api/election/power-indices
Shapley-Shubik (1954) and Banzhaf (1965) power indices.
"""
import json
import pytest

URL = "/api/election/power-indices"


def post(client, **kw):
    payload = {
        "parties": [
            {"name": "A", "seats": 40, "pariah": False},
            {"name": "B", "seats": 35, "pariah": False},
            {"name": "C", "seats": 25, "pariah": False},
        ],
        "majority_threshold": 51,
        "coalition_constraints": [],
        "calculate_shapley": True,
        "calculate_banzhaf": True,
        **kw,
    }
    return json.loads(client.post(URL, json=payload).data)


class TestPowerIndicesBasic:
    def test_returns_200(self, client):
        assert client.post(URL, json={
            "parties": [{"name": "A", "seats": 50}],
            "majority_threshold": 51,
        }).status_code == 200

    def test_response_keys(self, client):
        body = post(client)
        for k in ("total_seats", "majority_threshold", "parties",
                  "viable_coalitions", "power_surprises", "pedagogical_note"):
            assert k in body

    def test_party_result_keys(self, client):
        body = post(client)
        for p in body["parties"]:
            for k in ("name", "seats", "seat_pct", "shapley_index",
                      "banzhaf_index", "power_ratio", "critical_count",
                      "pivot_count", "is_pariah"):
                assert k in p, f"Missing key {k} in party {p['name']}"

    def test_total_seats_correct(self, client):
        body = post(client)
        assert body["total_seats"] == 100

    def test_majority_threshold_echo(self, client):
        body = post(client)
        assert body["majority_threshold"] == 51


# ── Shapley axiom: sum = 1.0 ─────────────────────────────────────────────────

class TestShapleySum:
    def test_shapley_sums_to_one(self, client):
        body = post(client)
        total = sum(p["shapley_index"] for p in body["parties"])
        assert total == pytest.approx(1.0, abs=1e-4)

    def test_shapley_sums_to_one_five_parties(self, client):
        body = post(client, parties=[
            {"name": "A", "seats": 30, "pariah": False},
            {"name": "B", "seats": 25, "pariah": False},
            {"name": "C", "seats": 20, "pariah": False},
            {"name": "D", "seats": 15, "pariah": False},
            {"name": "E", "seats": 10, "pariah": False},
        ], majority_threshold=51)
        total = sum(p["shapley_index"] for p in body["parties"])
        assert total == pytest.approx(1.0, abs=1e-4)

    def test_shapley_nonnegative(self, client):
        body = post(client)
        for p in body["parties"]:
            assert p["shapley_index"] >= 0.0


# ── Banzhaf axiom: sum = 1.0 ─────────────────────────────────────────────────

class TestBanzhafSum:
    def test_banzhaf_sums_to_one(self, client):
        body = post(client)
        total = sum(p["banzhaf_index"] for p in body["parties"])
        assert total == pytest.approx(1.0, abs=1e-4)

    def test_banzhaf_nonnegative(self, client):
        body = post(client)
        for p in body["parties"]:
            assert p["banzhaf_index"] >= 0.0


# ── Pariah: power = 0 ─────────────────────────────────────────────────────────

class TestPariahPower:
    def test_pariah_shapley_is_zero(self, client):
        """A pariah party cannot enter any coalition → Shapley = 0."""
        body = post(client, parties=[
            {"name": "A", "seats": 40, "pariah": False},
            {"name": "B", "seats": 35, "pariah": False},
            {"name": "C", "seats": 25, "pariah": True},   # pariah
        ], majority_threshold=51)
        c_result = next(p for p in body["parties"] if p["name"] == "C")
        assert c_result["shapley_index"] == pytest.approx(0.0)

    def test_pariah_banzhaf_is_zero(self, client):
        body = post(client, parties=[
            {"name": "A", "seats": 40, "pariah": False},
            {"name": "B", "seats": 35, "pariah": False},
            {"name": "C", "seats": 25, "pariah": True},
        ], majority_threshold=51)
        c_result = next(p for p in body["parties"] if p["name"] == "C")
        assert c_result["banzhaf_index"] == pytest.approx(0.0)

    def test_pariah_is_pariah_flag(self, client):
        body = post(client, parties=[
            {"name": "A", "seats": 40, "pariah": False},
            {"name": "B", "seats": 40, "pariah": False},
            {"name": "RN", "seats": 20, "pariah": True},
        ], majority_threshold=51)
        rn = next(p for p in body["parties"] if p["name"] == "RN")
        assert rn["is_pariah"] is True

    def test_pariah_not_in_viable_coalitions(self, client):
        """A pariah party with enough seats but excluded by all others."""
        body = post(client, parties=[
            {"name": "A", "seats": 40, "pariah": False},
            {"name": "B", "seats": 35, "pariah": False},
            {"name": "P", "seats": 30, "pariah": True},
        ], majority_threshold=51)
        for coalition in body["viable_coalitions"]:
            assert "P" not in coalition["parties"], \
                f"Pariah P found in coalition {coalition['parties']}"


# ── Dictator: Shapley = 1.0 ───────────────────────────────────────────────────

class TestDictator:
    def test_dictator_shapley_is_one(self, client):
        """A party with >50% of seats alone is a dictator → Shapley = 1."""
        body = post(client, parties=[
            {"name": "Big",   "seats": 60, "pariah": False},
            {"name": "Small", "seats": 40, "pariah": False},
        ], majority_threshold=51)
        big = next(p for p in body["parties"] if p["name"] == "Big")
        assert big["shapley_index"] == pytest.approx(1.0, abs=1e-4)

    def test_dictator_banzhaf_is_one(self, client):
        body = post(client, parties=[
            {"name": "Big",   "seats": 60, "pariah": False},
            {"name": "Small", "seats": 40, "pariah": False},
        ], majority_threshold=51)
        big = next(p for p in body["parties"] if p["name"] == "Big")
        assert big["banzhaf_index"] == pytest.approx(1.0, abs=1e-4)

    def test_minority_under_dictator_has_zero_power(self, client):
        body = post(client, parties=[
            {"name": "Big",   "seats": 60, "pariah": False},
            {"name": "Small", "seats": 40, "pariah": False},
        ], majority_threshold=51)
        small = next(p for p in body["parties"] if p["name"] == "Small")
        assert small["shapley_index"] == pytest.approx(0.0, abs=1e-4)


# ── critical_count ≤ total viable coalitions ──────────────────────────────────

class TestCriticalCount:
    def test_critical_count_le_viable_coalitions(self, client):
        body = post(client)
        n_viable = len(body["viable_coalitions"])
        for p in body["parties"]:
            assert p["critical_count"] <= n_viable, (
                f"{p['name']}: critical_count={p['critical_count']} > "
                f"viable_coalitions={n_viable}"
            )

    def test_pivot_count_nonnegative(self, client):
        body = post(client)
        for p in body["parties"]:
            assert p["pivot_count"] >= 0


# ── Viable coalitions ─────────────────────────────────────────────────────────

class TestViableCoalitions:
    def test_viable_coalitions_all_above_threshold(self, client):
        body = post(client)
        thr = body["majority_threshold"]
        for c in body["viable_coalitions"]:
            assert c["seats"] >= thr, \
                f"Coalition {c['parties']} has {c['seats']} < threshold {thr}"

    def test_minimal_coalition_no_superfluous_member(self, client):
        """Minimal coalitions: removing any member drops below threshold."""
        body = post(client)
        thr = body["majority_threshold"]
        seat_map = {p["name"]: p["seats"] for p in body["parties"]}
        for c in body["viable_coalitions"]:
            if not c["minimal"]:
                continue
            for member in c["parties"]:
                without = sum(seat_map[m] for m in c["parties"] if m != member)
                assert without < thr, (
                    f"Member {member} in 'minimal' coalition {c['parties']} "
                    f"is superfluous: {without} >= {thr}"
                )

    def test_auto_threshold_is_majority(self, client):
        """When threshold=0, it should default to total/2+1."""
        body = post(client, majority_threshold=0)
        assert body["majority_threshold"] == 51  # 100/2+1


# ── Coalition constraints ─────────────────────────────────────────────────────

class TestCoalitionConstraints:
    def test_constraint_excludes_pair(self, client):
        """Explicit constraint: A and B cannot coalesce."""
        body = post(client,
                    parties=[
                        {"name": "A", "seats": 40, "pariah": False},
                        {"name": "B", "seats": 35, "pariah": False},
                        {"name": "C", "seats": 25, "pariah": False},
                    ],
                    coalition_constraints=[{"party_a": "A", "party_b": "B"}],
                    majority_threshold=51)
        for coalition in body["viable_coalitions"]:
            parties = set(coalition["parties"])
            assert not ({"A", "B"}.issubset(parties)), \
                f"Constraint violated: A+B appear in {coalition['parties']}"


# ── Symmetry / equal parties ──────────────────────────────────────────────────

class TestSymmetry:
    def test_equal_parties_equal_power(self, client):
        """Three parties with equal seats have equal Shapley indices."""
        body = post(client, parties=[
            {"name": "X", "seats": 33, "pariah": False},
            {"name": "Y", "seats": 33, "pariah": False},
            {"name": "Z", "seats": 34, "pariah": False},
        ], majority_threshold=51)
        indices = [p["shapley_index"] for p in body["parties"]]
        # All should be close to 1/3
        for idx in indices:
            assert idx == pytest.approx(1 / 3, abs=0.02)

    def test_seat_pct_sums_to_one(self, client):
        body = post(client)
        total = sum(p["seat_pct"] for p in body["parties"])
        assert total == pytest.approx(1.0, abs=1e-4)


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_empty_parties_returns_400(self, client):
        r = client.post(URL, json={"parties": [], "majority_threshold": 51})
        assert r.status_code == 400

    def test_missing_body_defaults_gracefully(self, client):
        r = client.post(URL, json={"majority_threshold": 51})
        assert r.status_code == 400
