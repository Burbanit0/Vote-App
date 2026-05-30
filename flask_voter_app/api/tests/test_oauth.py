"""Tests for OAuth Google + GitHub on the async DB layer (Phase 4.5.b.2).

We don't hit the real Google/GitHub APIs:
  - Google: monkeypatch google.oauth2.id_token.verify_oauth2_token.
  - GitHub: monkeypatch httpx.AsyncClient used by the callback route.
"""
import pytest

from api.core.config import get_settings


@pytest.fixture
def client(db, seed_user, monkeypatch):
    """TestClient on the async-DB harness, with OAuth settings configured.
    (`db` wires the engine; `seed_user` is re-exported so tests can seed.)"""
    s = get_settings()
    monkeypatch.setattr(s, "google_client_id",     "google-client-id-for-tests")
    monkeypatch.setattr(s, "github_client_id",     "gh-client-id")
    monkeypatch.setattr(s, "github_client_secret", "gh-client-secret")
    monkeypatch.setattr(s, "base_url",     "http://localhost:4434")
    monkeypatch.setattr(s, "frontend_url", "http://localhost:3000")
    from fastapi.testclient import TestClient
    from api.main import app
    with TestClient(app) as c:
        yield c


# ── /auth/google ───────────────────────────────────────────────────────────

class TestGoogle:
    def test_creates_user_on_first_login(self, client, fetch_user, monkeypatch):
        from google.oauth2 import id_token as google_id_token

        def fake_verify(token, request, client_id):
            assert token == "fake-google-id-token"
            return {"sub": "google-user-123", "email": "gogo@example.com",
                    "given_name": "Go", "family_name": "Ogle"}
        monkeypatch.setattr(google_id_token, "verify_oauth2_token", fake_verify)

        r = client.post("/api/v2/auth/google", json={"token": "fake-google-id-token"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["username"] == "gogo"
        assert body["first_name"] == "Go"
        assert isinstance(body["access_token"], str)

        u = fetch_user("gogo@example.com")
        assert u is not None and u["google_id"] == "google-user-123"

    def test_links_to_existing_user_by_email(self, client, seed_user, fetch_user, monkeypatch):
        seed_id = seed_user(username="seed", email="seed@example.com")

        from google.oauth2 import id_token as google_id_token
        monkeypatch.setattr(google_id_token, "verify_oauth2_token",
                            lambda *a, **kw: {"sub": "google-seed", "email": "seed@example.com",
                                              "given_name": "Seed", "family_name": "User"})
        r = client.post("/api/v2/auth/google", json={"token": "t"})
        assert r.status_code == 200
        assert r.json()["user_id"] == seed_id
        assert fetch_user("seed@example.com")["google_id"] == "google-seed"

    def test_rejects_invalid_google_token(self, client, monkeypatch):
        from google.oauth2 import id_token as google_id_token

        def boom(*a, **kw):
            raise ValueError("bad token")
        monkeypatch.setattr(google_id_token, "verify_oauth2_token", boom)
        assert client.post("/api/v2/auth/google", json={"token": "x"}).status_code == 401

    def test_missing_token_is_422(self, client):
        assert client.post("/api/v2/auth/google", json={}).status_code == 422

    def test_unconfigured_returns_501(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "google_client_id", "")
        assert client.post("/api/v2/auth/google", json={"token": "x"}).status_code == 501


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
        assert client.get("/api/v2/auth/github",
                          follow_redirects=False).status_code == 501


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
    """Drop-in for httpx.AsyncClient used by github_callback."""
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
            return _FakeResponse({"id": 98765, "name": "Octo Cat", "email": "octo@example.com"})
        if url.endswith("/user/emails"):
            return _FakeResponse([{"primary": True, "email": "octo@example.com"}])
        raise AssertionError(f"unexpected URL: {url}")


class TestGitHubCallback:
    def test_callback_creates_user_and_redirects(self, client, fetch_user, monkeypatch):
        import api.routes.oauth as oauth_module
        monkeypatch.setattr(oauth_module.httpx, "AsyncClient", _FakeAsyncClient)

        r = client.get("/api/v2/auth/github/callback?code=fake-code", follow_redirects=False)
        assert r.status_code == 307, r.text
        assert r.headers["location"].startswith("http://localhost:3000/oauth/callback?token=")

        u = fetch_user("octo@example.com")
        assert u is not None and u["github_id"] == "98765"

    def test_callback_without_code_is_400(self, client):
        assert client.get("/api/v2/auth/github/callback",
                          follow_redirects=False).status_code == 400

    def test_callback_unconfigured_returns_501(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "github_client_id", "")
        assert client.get("/api/v2/auth/github/callback?code=x",
                          follow_redirects=False).status_code == 501
