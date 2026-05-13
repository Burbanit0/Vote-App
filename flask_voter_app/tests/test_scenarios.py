"""Integration tests for JWT-protected scenario CRUD endpoints."""

import pytest


def _create_scenario(client, headers, name="test", config=None):
    """Helper — POST a scenario and return the response."""
    return client.post(
        "/api/scenarios/",
        json={"name": name, "config": config or {"num_voters": 100}},
        headers=headers,
    )


class TestScenariosUnauthenticated:
    """All endpoints require JWT — expect 401 without auth."""

    def test_list_unauthorized(self, client):
        assert client.get("/api/scenarios/").status_code == 401

    def test_create_unauthorized(self, client):
        assert client.post("/api/scenarios/", json={"name": "x"}).status_code == 401

    def test_get_detail_unauthorized(self, client):
        assert client.get("/api/scenarios/1").status_code == 401

    def test_delete_unauthorized(self, client):
        assert client.delete("/api/scenarios/1").status_code == 401


class TestScenariosCRUD:
    """Happy-path CRUD with valid auth."""

    def test_create_scenario(self, client, init_db, auth_header):
        resp = _create_scenario(client, auth_header, name="test")
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "test"
        assert data["config"] == {"num_voters": 100}
        assert "id" in data
        assert "created_at" in data

    def test_create_scenario_missing_name(self, client, init_db, auth_header):
        resp = client.post("/api/scenarios/", json={}, headers=auth_header)
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Name is required"

    def test_create_scenario_blank_name(self, client, init_db, auth_header):
        resp = client.post(
            "/api/scenarios/", json={"name": "   "}, headers=auth_header
        )
        assert resp.status_code == 400

    def test_get_scenarios(self, client, init_db, auth_header):
        _create_scenario(client, auth_header, name="first")
        _create_scenario(client, auth_header, name="second")

        resp = client.get("/api/scenarios/", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        names = [s["name"] for s in data]
        assert "first" in names
        assert "second" in names

    def test_get_scenarios_empty(self, client, init_db, auth_header):
        resp = client.get("/api/scenarios/", headers=auth_header)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_get_scenario_detail(self, client, init_db, auth_header):
        create_resp = _create_scenario(client, auth_header, name="detail-test")
        scenario_id = create_resp.get_json()["id"]

        resp = client.get(f"/api/scenarios/{scenario_id}", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "detail-test"
        assert data["config"] == {"num_voters": 100}
        assert "results" in data
        assert data["results"] is None

    def test_get_scenario_not_found(self, client, init_db, auth_header):
        resp = client.get("/api/scenarios/9999", headers=auth_header)
        assert resp.status_code == 404

    def test_delete_scenario(self, client, init_db, auth_header):
        create_resp = _create_scenario(client, auth_header)
        scenario_id = create_resp.get_json()["id"]

        resp = client.delete(f"/api/scenarios/{scenario_id}", headers=auth_header)
        assert resp.status_code == 200
        assert resp.get_json()["message"] == "Deleted"

        resp = client.get(f"/api/scenarios/{scenario_id}", headers=auth_header)
        assert resp.status_code == 404

    def test_delete_scenario_not_found(self, client, init_db, auth_header):
        resp = client.delete("/api/scenarios/9999", headers=auth_header)
        assert resp.status_code == 404

    def test_scenario_ownership(self, client, init_db, auth_header, admin_auth_header):
        """User A cannot access a scenario created by User B."""
        # Create scenario as adminA
        create_resp = _create_scenario(client, admin_auth_header, name="admin-only")
        scenario_id = create_resp.get_json()["id"]

        # testuserA tries to access it — should be 404 (filtered by user_id)
        resp = client.get(f"/api/scenarios/{scenario_id}", headers=auth_header)
        assert resp.status_code == 404

        # testuserA tries to delete it — should be 404
        resp = client.delete(f"/api/scenarios/{scenario_id}", headers=auth_header)
        assert resp.status_code == 404

        # adminA can still access it
        resp = client.get(f"/api/scenarios/{scenario_id}", headers=admin_auth_header)
        assert resp.status_code == 200

    def test_list_respects_ownership(self, client, init_db, auth_header, admin_auth_header):
        """Each user only sees their own scenarios in the list."""
        _create_scenario(client, auth_header, name="user-scenario")
        _create_scenario(client, admin_auth_header, name="admin-scenario")

        user_list = client.get("/api/scenarios/", headers=auth_header).get_json()
        admin_list = client.get("/api/scenarios/", headers=admin_auth_header).get_json()

        assert len(user_list) == 1
        assert user_list[0]["name"] == "user-scenario"

        assert len(admin_list) == 1
        assert admin_list[0]["name"] == "admin-scenario"
