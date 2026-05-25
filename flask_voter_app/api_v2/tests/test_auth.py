"""Tests for Phase 4.3.b — fastapi-users register / login / logout.

Same conftest pattern as test_scenarios.py: in-memory SQLite, JWT secret
overridden so tokens issued by both sides are interchangeable.
"""
import pytest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import db, create_app
from app.models import User
from api_v2.core import db as v2_db
from api_v2.core.config import get_settings


@pytest.fixture(scope="function")
def flask_app():
    app = create_app(config_object="config.TestingConfig")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["JWT_SECRET_KEY"] = "test-secret-key"
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def client(flask_app, monkeypatch):
    monkeypatch.setattr(v2_db, "_app", flask_app)
    monkeypatch.setattr(get_settings(), "jwt_secret_key", "test-secret-key")
    from api_v2.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def existing_user(flask_app):
    """A user created via the legacy flask-bcrypt path, so we can verify
    fastapi-users' login path verifies the existing password hashes."""
    from flask_bcrypt import generate_password_hash
    with flask_app.app_context():
        u = User(
            username="legacy",
            email="legacy@example.com",
            password_hash=generate_password_hash("legacypw").decode("utf-8"),
            role="User",
            first_name="Legacy",
            last_name="User",
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(u)
        db.session.commit()
        return {"id": u.id, "email": u.email, "password": "legacypw"}


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
        assert body["role"] == "User"        # default
        assert body["is_active"] is True
        assert body["is_superuser"] is False
        # Password never echoed.
        assert "password" not in body
        assert "hashed_password" not in body

    def test_register_duplicate_email_fails(self, client):
        payload = {
            "email": "dup@example.com",
            "password": "Strong-Password-1!",
            "username": "dup1",
        }
        first = client.post("/api/v2/auth/register", json=payload)
        assert first.status_code == 201
        second = client.post("/api/v2/auth/register",
                             json={**payload, "username": "dup2"})
        assert second.status_code == 400

    def test_register_rejects_invalid_email(self, client):
        r = client.post("/api/v2/auth/register", json={
            "email": "not-an-email",
            "password": "Strong-Password-1!",
            "username": "x",
        })
        assert r.status_code == 422


# ── /api/v2/auth/jwt/login + /logout ───────────────────────────────────────

class TestLogin:
    def test_login_via_fastapi_users(self, client):
        client.post("/api/v2/auth/register", json={
            "email": "loginer@example.com",
            "password": "Strong-Password-1!",
            "username": "loginer",
        })
        r = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": "loginer@example.com",
                  "password": "Strong-Password-1!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str)

    def test_login_verifies_legacy_flask_bcrypt_hash(
        self, client, existing_user,
    ):
        """Users created with the old flask-bcrypt path must still be
        able to log in via fastapi-users — passlib reads our bcrypt hashes."""
        r = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": existing_user["email"],
                  "password": existing_user["password"]},
        )
        assert r.status_code == 200, r.text
        assert "access_token" in r.json()

    def test_login_wrong_password_fails(self, client):
        client.post("/api/v2/auth/register", json={
            "email": "wp@example.com",
            "password": "Strong-Password-1!",
            "username": "wp",
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
            "email": "logout@example.com",
            "password": "Strong-Password-1!",
            "username": "logout",
        })
        login = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": "logout@example.com",
                  "password": "Strong-Password-1!"},
        )
        token = login.json()["access_token"]
        r = client.post(
            "/api/v2/auth/jwt/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Default JWT strategy is stateless → 204 with no actual server-side
        # revocation. Future enhancement: redis-backed denylist.
        assert r.status_code == 204


# ── Cross-compat: token issued by fastapi-users authorizes scenarios ───────

class TestTokenInteroperability:
    def test_fastapi_users_token_works_on_scenarios_route(self, client):
        client.post("/api/v2/auth/register", json={
            "email": "cross@example.com",
            "password": "Strong-Password-1!",
            "username": "cross",
        })
        login = client.post(
            "/api/v2/auth/jwt/login",
            data={"username": "cross@example.com",
                  "password": "Strong-Password-1!"},
        )
        token = login.json()["access_token"]

        r = client.get(
            "/api/v2/scenarios",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should authorize and return an empty list for a fresh user.
        assert r.status_code == 200, r.text
        assert r.json() == []
