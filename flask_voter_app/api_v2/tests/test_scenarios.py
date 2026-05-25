"""Tests for /api/v2/scenarios CRUD.

Shares the in-memory SQLite + JWT-secret setup used by the Flask
test suite, so the same token format is round-tripped through both
sides of the strangler-fig.
"""
import pytest
from datetime import datetime, timezone

from flask_bcrypt import generate_password_hash
from flask_jwt_extended import create_access_token
from fastapi.testclient import TestClient

from app import db, create_app
from app.models import SimulationScenario, User
from api_v2.core import db as v2_db
from api_v2.core.config import get_settings


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def flask_app():
    """Test Flask app with in-memory SQLite, drained between tests."""
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
def test_user(flask_app):
    with flask_app.app_context():
        u = User(
            username="scenarios_user",
            email="scenarios_user@vote-app.local",
            password_hash=generate_password_hash("pw").decode("utf-8"),
            role="User",
            first_name="Test",
            last_name="User",
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(u)
        db.session.commit()
        # Refresh so id is populated, then return a snapshot — the
        # session detaches after this fixture ends.
        return {"id": u.id, "username": u.username}


@pytest.fixture(scope="function")
def auth_token(flask_app, test_user):
    with flask_app.app_context():
        return create_access_token(identity=str(test_user["id"]))


@pytest.fixture(scope="function")
def client(flask_app, monkeypatch):
    """FastAPI TestClient with the api_v2 DB bridge pointed at our
    in-memory Flask app, and the JWT secret aligned with it."""
    # Point the api_v2 DB bridge at our test Flask app.
    monkeypatch.setattr(v2_db, "_app", flask_app)

    # Make the v2 JWT verifier use the same secret the test token was signed with.
    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-key")

    # Import here so the monkeypatches above land before FastAPI builds
    # its dependency graph.
    from api_v2.main import app
    with TestClient(app) as c:
        yield c


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth — 401 paths ───────────────────────────────────────────────────────

class TestAuth:
    def test_list_without_token_is_401(self, client):
        r = client.get("/api/v2/scenarios")
        assert r.status_code == 401, r.text

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
        r = client.post("/api/v2/scenarios", headers=_auth(auth_token),
                        json=payload)
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
        # Summary view never carries results
        assert "results" not in rows[0]

    def test_get_then_delete(self, client, auth_token):
        created = client.post("/api/v2/scenarios", headers=_auth(auth_token),
                              json={"name": "test", "config": {}}).json()
        sid = created["id"]

        r = client.get(f"/api/v2/scenarios/{sid}", headers=_auth(auth_token))
        assert r.status_code == 200, r.text
        assert r.json()["id"] == sid

        deleted = client.delete(f"/api/v2/scenarios/{sid}",
                                headers=_auth(auth_token))
        assert deleted.status_code == 200, deleted.text
        assert deleted.json() == {"message": "Deleted"}

        gone = client.get(f"/api/v2/scenarios/{sid}", headers=_auth(auth_token))
        assert gone.status_code == 404

    def test_get_nonexistent_is_404(self, client, auth_token):
        r = client.get("/api/v2/scenarios/99999", headers=_auth(auth_token))
        assert r.status_code == 404

    def test_delete_nonexistent_is_404(self, client, auth_token):
        r = client.delete("/api/v2/scenarios/99999", headers=_auth(auth_token))
        assert r.status_code == 404


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
    def test_users_cannot_see_each_others_scenarios(self, client, flask_app,
                                                    auth_token, test_user):
        # First user creates one
        client.post("/api/v2/scenarios", headers=_auth(auth_token),
                    json={"name": "mine", "config": {}})

        # Second user signs in
        with flask_app.app_context():
            other = User(
                username="other_user",
                email="other_user@vote-app.local",
                password_hash=generate_password_hash("pw").decode("utf-8"),
                role="User",
                first_name="Other",
                last_name="User",
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(other)
            db.session.commit()
            other_token = create_access_token(identity=str(other.id))

        r = client.get("/api/v2/scenarios", headers=_auth(other_token))
        assert r.status_code == 200
        assert r.json() == []
