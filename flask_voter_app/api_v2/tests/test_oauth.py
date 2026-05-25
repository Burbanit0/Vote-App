"""Tests for Phase 4.3.d — OAuth Google + GitHub.

We don't hit the real Google/GitHub APIs. Instead:
  - Google: monkeypatch google.oauth2.id_token.verify_oauth2_token
            to return a synthetic profile.
  - GitHub: monkeypatch httpx.AsyncClient.post + .get to return
            synthetic token + user payloads.
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
    s = get_settings()
    monkeypatch.setattr(s, "jwt_secret_key",     "test-secret-key")
    monkeypatch.setattr(s, "google_client_id",   "google-client-id-for-tests")
    monkeypatch.setattr(s, "github_client_id",   "gh-client-id")
    monkeypatch.setattr(s, "github_client_secret", "gh-client-secret")
    monkeypatch.setattr(s, "base_url",     "http://localhost:4434")
    monkeypatch.setattr(s, "frontend_url", "http://localhost:3000")
    from api_v2.main import app
    with TestClient(app) as c:
        yield c


# ── /auth/google ───────────────────────────────────────────────────────────

class TestGoogle:
    def test_creates_user_on_first_login(self, client, flask_app, monkeypatch):
        from google.oauth2 import id_token as google_id_token

        def fake_verify(token, request, client_id):
            assert token == "fake-google-id-token"
            return {
                "sub":          "google-user-123",
                "email":        "gogo@example.com",
                "given_name":   "Go",
                "family_name":  "Ogle",
            }
        monkeypatch.setattr(google_id_token, "verify_oauth2_token", fake_verify)

        r = client.post("/api/v2/auth/google",
                        json={"token": "fake-google-id-token"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["username"] == "gogo"
        assert body["first_name"] == "Go"
        assert isinstance(body["access_token"], str)

        with flask_app.app_context():
            u = User.query.filter_by(google_id="google-user-123").first()
            assert u is not None
            assert u.email == "gogo@example.com"

    def test_links_to_existing_user_by_email(self, client, flask_app, monkeypatch):
        # Pre-seed a user with the same email but no google_id.
        with flask_app.app_context():
            from flask_bcrypt import generate_password_hash
            u = User(
                username="seed",
                email="seed@example.com",
                password_hash=generate_password_hash("x").decode("utf-8"),
                role="User",
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(u)
            db.session.commit()
            seed_id = u.id

        from google.oauth2 import id_token as google_id_token
        monkeypatch.setattr(google_id_token, "verify_oauth2_token",
                            lambda *a, **kw: {
                                "sub": "google-seed",
                                "email": "seed@example.com",
                                "given_name": "Seed",
                                "family_name": "User",
                            })
        r = client.post("/api/v2/auth/google", json={"token": "t"})
        assert r.status_code == 200
        assert r.json()["user_id"] == seed_id
        with flask_app.app_context():
            assert User.query.get(seed_id).google_id == "google-seed"

    def test_rejects_invalid_google_token(self, client, monkeypatch):
        from google.oauth2 import id_token as google_id_token
        def boom(*a, **kw):
            raise ValueError("bad token")
        monkeypatch.setattr(google_id_token, "verify_oauth2_token", boom)

        r = client.post("/api/v2/auth/google", json={"token": "x"})
        assert r.status_code == 401

    def test_missing_token_is_422(self, client):
        r = client.post("/api/v2/auth/google", json={})
        assert r.status_code == 422

    def test_unconfigured_returns_501(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "google_client_id", "")
        r = client.post("/api/v2/auth/google", json={"token": "x"})
        assert r.status_code == 501


# ── /auth/github ───────────────────────────────────────────────────────────

class TestGitHubRedirect:
    def test_redirects_to_consent_page(self, client):
        r = client.get("/api/v2/auth/github", follow_redirects=False)
        assert r.status_code == 307
        loc = r.headers["location"]
        assert loc.startswith("https://github.com/login/oauth/authorize")
        assert "client_id=gh-client-id" in loc
        assert "redirect_uri=http://localhost:4434/api/v2/auth/github/callback" in loc

    def test_unconfigured_returns_501(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "github_client_id", "")
        r = client.get("/api/v2/auth/github", follow_redirects=False)
        assert r.status_code == 501


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
    def json(self):
        return self._payload


class _FakeAsyncClient:
    """Drop-in for httpx.AsyncClient used by the github_callback route.

    Routes POST → access_token, GET /user → profile, GET /user/emails → list.
    """
    def __init__(self, *args, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return None
    async def post(self, url, **kwargs):
        assert "github.com/login/oauth/access_token" in url
        return _FakeResponse({"access_token": "gh-access-token"})
    async def get(self, url, **kwargs):
        if url.endswith("/user"):
            return _FakeResponse({
                "id":    98765,
                "name":  "Octo Cat",
                "email": "octo@example.com",
            })
        if url.endswith("/user/emails"):
            return _FakeResponse([{"primary": True, "email": "octo@example.com"}])
        raise AssertionError(f"unexpected URL: {url}")


class TestGitHubCallback:
    def test_callback_creates_user_and_redirects(self, client, flask_app, monkeypatch):
        import api_v2.routes.oauth as oauth_module
        monkeypatch.setattr(oauth_module.httpx, "AsyncClient", _FakeAsyncClient)

        r = client.get("/api/v2/auth/github/callback?code=fake-code",
                       follow_redirects=False)
        assert r.status_code == 307, r.text
        loc = r.headers["location"]
        assert loc.startswith("http://localhost:3000/oauth/callback?token=")

        with flask_app.app_context():
            u = User.query.filter_by(github_id="98765").first()
            assert u is not None
            assert u.email == "octo@example.com"

    def test_callback_without_code_is_400(self, client):
        r = client.get("/api/v2/auth/github/callback",
                       follow_redirects=False)
        assert r.status_code == 400

    def test_callback_unconfigured_returns_501(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "github_client_id", "")
        r = client.get("/api/v2/auth/github/callback?code=x",
                       follow_redirects=False)
        assert r.status_code == 501
