"""Tests for Phase 4.5.a.2 — research dataset export on FastAPI."""
import csv
import io

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


PAYLOAD = {
    "num_scenarios":  3,
    "num_candidates": 3,
    "num_voters":     50,
    "seed":           42,
    "ideology":       "random",
}


# ── /simulation-dataset (CSV) ──────────────────────────────────────────────

class TestCSV:
    def test_csv_happy_path(self, client):
        r = client.post("/api/v2/export/simulation-dataset", json=PAYLOAD)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/csv")
        assert "attachment" in r.headers["content-disposition"]
        assert "votelab_dataset_42.csv" in r.headers["content-disposition"]

        body = r.text
        reader = csv.DictReader(io.StringIO(body))
        rows = list(reader)
        # 3 scenarios × N methods → > 3 rows guaranteed
        assert len(rows) >= 9
        assert {"scenario_id", "method", "winner", "bayesian_regret"} <= set(reader.fieldnames)
        # Same seed must reproduce the exact same body.
        r2 = client.post("/api/v2/export/simulation-dataset", json=PAYLOAD)
        assert r2.text == body

    def test_rejects_too_many_scenarios(self, client):
        bad = {**PAYLOAD, "num_scenarios": 9_999}
        assert client.post("/api/v2/export/simulation-dataset",
                           json=bad).status_code == 422

    def test_rejects_too_few_voters(self, client):
        bad = {**PAYLOAD, "num_voters": 5}
        assert client.post("/api/v2/export/simulation-dataset",
                           json=bad).status_code == 422

    def test_rejects_too_few_candidates(self, client):
        bad = {**PAYLOAD, "num_candidates": 1}
        assert client.post("/api/v2/export/simulation-dataset",
                           json=bad).status_code == 422


# ── /simulation-dataset-json ───────────────────────────────────────────────

class TestJSON:
    def test_json_happy_path(self, client):
        r = client.post("/api/v2/export/simulation-dataset-json", json=PAYLOAD)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("meta", "columns", "rows"):
            assert k in body
        meta = body["meta"]
        assert meta["num_scenarios"]  == 3
        assert meta["num_candidates"] == 3
        assert meta["num_voters"]     == 50
        assert meta["seed"]           == 42
        assert meta["total_rows"]     == len(body["rows"])
        assert meta["total_rows"]     >= 9   # 3 scenarios × N methods

    def test_reproducibility(self, client):
        a = client.post("/api/v2/export/simulation-dataset-json",
                        json=PAYLOAD).json()
        b = client.post("/api/v2/export/simulation-dataset-json",
                        json=PAYLOAD).json()
        assert a["rows"] == b["rows"]

    def test_rejects_extra_field(self, client):
        bad = {**PAYLOAD, "evil": 1}
        assert client.post("/api/v2/export/simulation-dataset-json",
                           json=bad).status_code == 422
