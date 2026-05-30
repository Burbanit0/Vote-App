"""Tests for fastapi-users register / login / logout on the async DB layer
(Phase 4.5.b.2). Uses the shared async-DB harness in conftest.py."""
import pytest
from flask_bcrypt import generate_password_hash


@pytest.fixture
def existing_user(seed_user):
    """A user created with the legacy flask-bcrypt hash, so we can verify
    fastapi-users' login path reads existing password hashes."""
    uid = seed_user(
        username="legacy",
        email="legacy@example.com",
        hashed_password=generate_password_hash("legacypw").decode("utf-8"),
    )
    return {"id": uid, "email": "legacy@example.com", "password": "legacypw"}


# ── /api/v2/auth/register ───────────────────────────────────────────────────

class TestRegister:
    def test_register_happy_path(self, client):
        r = client.post("/api/v2/auth/register", json={
            "email": "new@example.com",
            "password": "Strong-Password-1!",
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
        })
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["email"] == "new@example.com"
        assert body["username"] == "newuser"
        assert body["role"] == "User"
        assert body["is_active"] is True
        assert body["is_superuser"] is False
        assert "password" not in body
        assert "hashed_password" not in body

    def test_register_duplicate_email_fails(self, client):
        payload = {"email": "dup@example.com", "password": "Strong-Password-1!", "username": "dup1"}
        assert client.post("/api/v2/auth/register", json=payload).status_code == 201
        second = client.post("/api/v2/auth/register", json={**payload, "username": "dup2"})
        assert second.status_code == 400

    def test_register_rejects_invalid_email(self, client):
        r = client.post("/api/v2/auth/register", json={
            "email": "not-an-email", "password": "Strong-Password-1!", "username": "x",
        })
        assert r.status_code == 422


# ── /api/v2/auth/jwt/login + /logout ───────────────────────────────────────

class TestLogin:
    def test_login_via_fastapi_users(self, client):
        client.post("/api/v2/auth/register", json={
            "email": "loginer@example.com", "password": "Strong-Password-1!", "username": "loginer",
        })
        r = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": "loginer@example.com", "password": "Strong-Password-1!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str)

    def test_login_verifies_legacy_flask_bcrypt_hash(self, client, existing_user):
        """Users created with the old flask-bcrypt path must still log in via
        fastapi-users — its password helper reads our bcrypt hashes."""
        r = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": existing_user["email"], "password": existing_user["password"]},
        )
        assert r.status_code == 200, r.text
        assert "access_token" in r.json()

    def test_login_wrong_password_fails(self, client):
        client.post("/api/v2/auth/register", json={
            "email": "wp@example.com", "password": "Strong-Password-1!", "username": "wp",
        })
        r = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": "wp@example.com", "password": "WrongPassword!"},
        )
        assert r.status_code == 400

    def test_login_unknown_email_fails(self, client):
        r = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": "ghost@example.com", "password": "whatever"},
        )
        assert r.status_code == 400


class TestLogout:
    def test_logout_with_bearer_token_is_204(self, client):
        client.post("/api/v2/auth/register", json={
            "email": "logout@example.com", "password": "Strong-Password-1!", "username": "logout",
        })
        token = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": "logout@example.com", "password": "Strong-Password-1!"},
        ).json()["access_token"]
        r = client.post("/api/v2/auth/jwt/logout", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204


# ── Cross-compat: token issued by fastapi-users authorizes scenarios ───────

class TestTokenInteroperability:
    def test_fastapi_users_token_works_on_scenarios_route(self, client):
        client.post("/api/v2/auth/register", json={
            "email": "cross@example.com", "password": "Strong-Password-1!", "username": "cross",
        })
        token = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": "cross@example.com", "password": "Strong-Password-1!"},
        ).json()["access_token"]

        r = client.get("/api/v2/scenarios", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        assert r.json() == []
