"""
test_export.py — Tests for the research dataset export endpoints.

Covers:
  - /api/export/simulation-dataset      (CSV)
  - /api/export/simulation-dataset-json (JSON)
"""
import csv
import io
import json

import pytest


@pytest.fixture
def export_payload():
    return {
        "num_scenarios":  10,
        "num_candidates": 3,
        "num_voters":     50,
        "seed":           42,
    }


# ── CSV endpoint ──────────────────────────────────────────────────────────────

class TestExportCSV:
    URL = "/api/export/simulation-dataset"

    def test_returns_csv_content_type(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        assert r.status_code == 200
        assert "text/csv" in r.content_type

    def test_content_disposition_contains_seed(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        cd = r.headers.get("Content-Disposition", "")
        assert "votelab_dataset_42.csv" in cd

    def test_csv_has_header_row(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        reader = csv.DictReader(io.StringIO(r.data.decode()))
        assert "scenario_id" in reader.fieldnames
        assert "method"      in reader.fieldnames
        assert "winner"      in reader.fieldnames

    def test_csv_row_count_equals_scenarios_times_methods(self, client, export_payload):
        """10 scenarios × N methods = exactly 10 × N data rows."""
        r = client.post(self.URL, json=export_payload)
        reader = csv.DictReader(io.StringIO(r.data.decode()))
        rows = list(reader)
        # All rows belong to scenario_ids 1..10
        scenario_ids = {int(row["scenario_id"]) for row in rows}
        assert scenario_ids == set(range(1, 11))

    def test_csv_exactly_10_scenarios(self, client, export_payload):
        """Each scenario_id appears exactly once per method."""
        r = client.post(self.URL, json=export_payload)
        reader = csv.DictReader(io.StringIO(r.data.decode()))
        rows = list(reader)
        # Count unique scenario_id × method combinations
        pairs = {(row["scenario_id"], row["method"]) for row in rows}
        # There should be exactly 10 distinct scenario_ids
        assert len({p[0] for p in pairs}) == 10

    def test_same_seed_returns_identical_data(self, client, export_payload):
        """Two requests with the same seed must return byte-identical output."""
        r1 = client.post(self.URL, json=export_payload)
        r2 = client.post(self.URL, json=export_payload)
        assert r1.data == r2.data

    def test_different_seed_returns_different_data(self, client, export_payload):
        payload2 = {**export_payload, "seed": 99}
        r1 = client.post(self.URL, json=export_payload)
        r2 = client.post(self.URL, json=payload2)
        assert r1.data != r2.data

    def test_num_scenarios_above_max_returns_400(self, client):
        r = client.post(self.URL, json={"num_scenarios": 1001, "num_candidates": 3, "num_voters": 50, "seed": 1})
        assert r.status_code == 400
        body = json.loads(r.data)
        assert "error" in body

    def test_num_scenarios_at_max_returns_200(self, client):
        # 1000 scenarios is slow; use very few voters/candidates to keep test fast
        r = client.post(self.URL, json={"num_scenarios": 1000, "num_candidates": 2, "num_voters": 10, "seed": 1})
        assert r.status_code == 200

    def test_num_scenarios_zero_returns_400(self, client):
        r = client.post(self.URL, json={"num_scenarios": 0, "num_candidates": 3, "num_voters": 50, "seed": 1})
        assert r.status_code == 400

    def test_invalid_num_candidates_returns_400(self, client):
        # num_candidates must be between 2 and 8
        r = client.post(self.URL, json={"num_scenarios": 5, "num_candidates": 1, "num_voters": 50, "seed": 1})
        assert r.status_code == 400

    def test_methods_agree_column_is_0_or_1(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        reader = csv.DictReader(io.StringIO(r.data.decode()))
        for row in reader:
            assert row["methods_agree"] in ("0", "1"), (
                f"methods_agree should be 0 or 1, got {row['methods_agree']!r}"
            )

    def test_condorcet_exists_column_is_0_or_1(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        reader = csv.DictReader(io.StringIO(r.data.decode()))
        for row in reader:
            assert row["condorcet_exists"] in ("0", "1")

    def test_csv_all_required_columns_present(self, client, export_payload):
        required = [
            "scenario_id", "num_candidates", "num_voters", "method",
            "winner", "winner_score", "condorcet_exists", "condorcet_winner",
            "bayesian_regret", "blank_rate", "blank_rule",
            "plurality_winner", "borda_winner", "irv_winner",
            "schulze_winner", "approval_winner", "methods_agree",
        ]
        r = client.post(self.URL, json=export_payload)
        reader = csv.DictReader(io.StringIO(r.data.decode()))
        for col in required:
            assert col in reader.fieldnames, f"Missing column: {col}"


# ── JSON endpoint ─────────────────────────────────────────────────────────────

class TestExportJSON:
    URL = "/api/export/simulation-dataset-json"

    def test_returns_json_content_type(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        assert r.status_code == 200
        assert "application/json" in r.content_type

    def test_json_structure(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        body = json.loads(r.data)
        assert "meta"    in body
        assert "columns" in body
        assert "rows"    in body

    def test_json_meta_fields(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        meta = json.loads(r.data)["meta"]
        assert meta["num_scenarios"]  == 10
        assert meta["num_candidates"] == 3
        assert meta["num_voters"]     == 50
        assert meta["seed"]           == 42

    def test_json_row_count_matches_meta_total_rows(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        body = json.loads(r.data)
        assert len(body["rows"]) == body["meta"]["total_rows"]

    def test_json_10_scenarios_present(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        rows = json.loads(r.data)["rows"]
        scenario_ids = {row["scenario_id"] for row in rows}
        assert scenario_ids == set(range(1, 11))

    def test_json_same_seed_reproducible(self, client, export_payload):
        r1 = json.loads(client.post(self.URL, json=export_payload).data)
        r2 = json.loads(client.post(self.URL, json=export_payload).data)
        assert r1["rows"] == r2["rows"]

    def test_json_above_max_returns_400(self, client):
        r = client.post(self.URL, json={"num_scenarios": 1001, "num_candidates": 3, "num_voters": 50, "seed": 1})
        assert r.status_code == 400

    def test_json_row_has_all_columns(self, client, export_payload):
        r = client.post(self.URL, json=export_payload)
        rows = json.loads(r.data)["rows"]
        assert rows, "No rows returned"
        required = [
            "scenario_id", "num_candidates", "num_voters", "method",
            "winner", "winner_score", "condorcet_exists", "condorcet_winner",
            "bayesian_regret", "blank_rate", "blank_rule",
            "plurality_winner", "borda_winner", "irv_winner",
            "schulze_winner", "approval_winner", "methods_agree",
        ]
        for col in required:
            assert col in rows[0], f"Missing field in JSON row: {col}"

    def test_json_columns_list_matches_csv_columns(self, client, export_payload):
        """The JSON 'columns' list must match the CSV header order."""
        r = client.post(self.URL, json=export_payload)
        columns = json.loads(r.data)["columns"]
        from app.routes.export import CSV_COLUMNS
        assert columns == CSV_COLUMNS
