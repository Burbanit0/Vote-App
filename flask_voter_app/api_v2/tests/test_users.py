"""Tests for Phase 4.3.c — fastapi-users profile + admin CRUD.

Same fixture pattern as test_auth.py: in-memory SQLite + monkeypatched
v2 DB bridge + shared JWT secret.
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


def _register_and_login(client, email: str, *, is_admin: bool = False) -> str:
    """Helper: register a user, optionally promote to admin, return JWT."""
    client.post("/api/v2/auth/register", json={
        "email": email,
        "password": "Strong-Password-1!",
        "username": email.split("@")[0],
    })
    if is_admin:
        # Direct DB poke — there's no admin-creation route by design.
        from app.models import User as UserModel
        from app import db as _db
        u = UserModel.query.filter_by(email=email).first()
        u.is_superuser = True
        u.role = "Admin"
        _db.session.commit()
    login = client.post(
        "/api/v2/auth/jwt/login",
        data={"username": email, "password": "Strong-Password-1!"},
    )
    return login.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── /users/me ──────────────────────────────────────────────────────────────

class TestGetMe:
    def test_returns_current_user(self, client):
        token = _register_and_login(client, "me@example.com")
        r = client.get("/api/v2/users/me", headers=_auth(token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["email"] == "me@example.com"
        assert body["username"] == "me"
        assert body["is_superuser"] is False

    def test_without_token_is_401(self, client):
        r = client.get("/api/v2/users/me")
        assert r.status_code == 401

    def test_with_invalid_token_is_401(self, client):
        r = client.get("/api/v2/users/me",
                       headers={"Authorization": "Bearer nope"})
        assert r.status_code == 401


class TestPatchMe:
    def test_update_own_first_name(self, client, flask_app):
        token = _register_and_login(client, "patch@example.com")
        r = client.patch("/api/v2/users/me",
                         headers=_auth(token),
                         json={"first_name": "Alice"})
        assert r.status_code == 200, r.text
        assert r.json()["first_name"] == "Alice"

        # Confirm it round-trips through the DB.
        with flask_app.app_context():
            u = User.query.filter_by(email="patch@example.com").first()
            assert u.first_name == "Alice"

    def test_cannot_self_promote_to_superuser(self, client, flask_app):
        token = _register_and_login(client, "selfadmin@example.com")
        r = client.patch("/api/v2/users/me",
                         headers=_auth(token),
                         json={"is_superuser": True})
        # fastapi-users silently ignores is_superuser on /me — body returns
        # the unchanged value.
        assert r.status_code == 200, r.text
        assert r.json()["is_superuser"] is False
        with flask_app.app_context():
            assert (
                User.query.filter_by(email="selfadmin@example.com").first()
                .is_superuser
                is False
            )


# ── /users/{id} — admin only ───────────────────────────────────────────────

class TestAdminGetUser:
    def test_admin_can_fetch_any_user(self, client, flask_app):
        admin_token = _register_and_login(client, "admin@example.com",
                                          is_admin=True)
        _register_and_login(client, "alice@example.com")
        with flask_app.app_context():
            alice_id = User.query.filter_by(email="alice@example.com").first().id
        r = client.get(f"/api/v2/users/{alice_id}", headers=_auth(admin_token))
        assert r.status_code == 200, r.text
        assert r.json()["email"] == "alice@example.com"

    def test_non_admin_cannot_fetch_other_user(self, client, flask_app):
        bob_token = _register_and_login(client, "bob@example.com")
        _register_and_login(client, "alice@example.com")
        with flask_app.app_context():
            alice_id = User.query.filter_by(email="alice@example.com").first().id
        r = client.get(f"/api/v2/users/{alice_id}", headers=_auth(bob_token))
        assert r.status_code == 403


class TestAdminPatchUser:
    def test_admin_can_promote_user(self, client, flask_app):
        admin_token = _register_and_login(client, "boss@example.com",
                                          is_admin=True)
        _register_and_login(client, "promote@example.com")
        with flask_app.app_context():
            uid = User.query.filter_by(email="promote@example.com").first().id

        r = client.patch(
            f"/api/v2/users/{uid}",
            headers=_auth(admin_token),
            json={"is_superuser": True},
        )
        assert r.status_code == 200, r.text
        assert r.json()["is_superuser"] is True

        # Legacy `role` column must be kept in sync by FlaskUserDatabase.update().
        with flask_app.app_context():
            u = User.query.filter_by(email="promote@example.com").first()
            assert u.is_superuser is True
            assert u.role == "Admin"


class TestAdminDeleteUser:
    def test_admin_can_delete_user(self, client, flask_app):
        admin_token = _register_and_login(client, "deleter@example.com",
                                          is_admin=True)
        _register_and_login(client, "victim@example.com")
        with flask_app.app_context():
            uid = User.query.filter_by(email="victim@example.com").first().id

        r = client.delete(f"/api/v2/users/{uid}", headers=_auth(admin_token))
        assert r.status_code == 204

        with flask_app.app_context():
            assert (
                User.query.filter_by(email="victim@example.com").first()
                is None
            )

    def test_non_admin_cannot_delete(self, client, flask_app):
        bob_token = _register_and_login(client, "innocent@example.com")
        _register_and_login(client, "target@example.com")
        with flask_app.app_context():
            uid = User.query.filter_by(email="target@example.com").first().id
        r = client.delete(f"/api/v2/users/{uid}", headers=_auth(bob_token))
        assert r.status_code == 403
