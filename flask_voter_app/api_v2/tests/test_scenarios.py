"""Tests for /api/v2/scenarios CRUD (async DB layer, Phase 4.5.b.2).

Uses the shared async-DB harness in conftest.py (file-backed aiosqlite). Tokens
are minted directly in the Flask-JWT-Extended-compatible shape (sub=str(id)).
"""
import pytest

from api_v2.tests.conftest import make_token


@pytest.fixture
def auth_token(seed_user) -> str:
    uid = seed_user(username="scenarios_user")
    return make_token(uid)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth — 401 paths ───────────────────────────────────────────────────────

class TestAuth:
    def test_list_without_token_is_401(self, client):
        assert client.get("/api/v2/scenarios").status_code == 401

    def test_invalid_token_is_401(self, client):
        r = client.get("/api/v2/scenarios",
                       headers={"Authorization": "Bearer not.a.real.jwt"})
        assert r.status_code == 401, r.text

    def test_wrong_scheme_is_401(self, client, auth_token):
        r = client.get("/api/v2/scenarios",
                       headers={"Authorization": f"Token {auth_token}"})
        assert r.status_code == 401, r.text


# ── CRUD happy path ─────────────────────────────────────────────────────────

class TestCRUD:
    def test_list_empty_for_new_user(self, client, auth_token):
        r = client.get("/api/v2/scenarios", headers=_auth(auth_token))
        assert r.status_code == 200, r.text
        assert r.json() == []

    def test_create_then_list(self, client, auth_token):
        payload = {
            "name": "France 2002 — 1er tour",
            "config": {"num_voters": 200, "ideology": "polarized"},
            "results": {"winner": "Chirac"},
        }
        r = client.post("/api/v2/scenarios", headers=_auth(auth_token), json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == payload["name"]
        assert body["config"] == payload["config"]
        assert body["results"] == payload["results"]
        assert "id" in body

        listed = client.get("/api/v2/scenarios", headers=_auth(auth_token))
        assert listed.status_code == 200
        rows = listed.json()
        assert len(rows) == 1
        assert rows[0]["id"] == body["id"]
        assert "results" not in rows[0]    # summary view never carries results

    def test_get_then_delete(self, client, auth_token):
        created = client.post("/api/v2/scenarios", headers=_auth(auth_token),
                              json={"name": "test", "config": {}}).json()
        sid = created["id"]

        r = client.get(f"/api/v2/scenarios/{sid}", headers=_auth(auth_token))
        assert r.status_code == 200, r.text
        assert r.json()["id"] == sid

        deleted = client.delete(f"/api/v2/scenarios/{sid}", headers=_auth(auth_token))
        assert deleted.status_code == 200, deleted.text
        assert deleted.json() == {"message": "Deleted"}

        gone = client.get(f"/api/v2/scenarios/{sid}", headers=_auth(auth_token))
        assert gone.status_code == 404

    def test_get_nonexistent_is_404(self, client, auth_token):
        assert client.get("/api/v2/scenarios/99999",
                          headers=_auth(auth_token)).status_code == 404

    def test_delete_nonexistent_is_404(self, client, auth_token):
        assert client.delete("/api/v2/scenarios/99999",
                             headers=_auth(auth_token)).status_code == 404


# ── Validation ─────────────────────────────────────────────────────────────

class TestValidation:
    def test_create_rejects_empty_name(self, client, auth_token):
        r = client.post("/api/v2/scenarios", headers=_auth(auth_token),
                        json={"name": "", "config": {}})
        assert r.status_code == 422

    def test_create_rejects_extra_fields(self, client, auth_token):
        r = client.post("/api/v2/scenarios", headers=_auth(auth_token),
                        json={"name": "x", "config": {}, "evil": 1})
        assert r.status_code == 422


# ── Per-user scoping ───────────────────────────────────────────────────────

class TestUserScoping:
    def test_users_cannot_see_each_others_scenarios(self, client, seed_user, auth_token):
        client.post("/api/v2/scenarios", headers=_auth(auth_token),
                    json={"name": "mine", "config": {}})

        other_token = make_token(seed_user(username="other_user"))
        r = client.get("/api/v2/scenarios", headers=_auth(other_token))
        assert r.status_code == 200
        assert r.json() == []
