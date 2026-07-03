"""Tests for fastapi-users profile + admin CRUD on the async DB layer
(Phase 4.5.b.2). Uses the shared async-DB harness in conftest.py."""


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client, email: str, *, promote=None) -> str:
    """Register a user, optionally promote to admin (via the `promote_admin`
    fixture passed in), and return a JWT."""
    client.post("/api/v2/auth/register", json={
        "email": email,
        "password": "Strong-Password-1!",
        "username": email.split("@")[0],
    })
    if promote is not None:
        promote(email)
    login = client.post(
        "/api/v2/auth/jwt/login",
        data={"username": email, "password": "Strong-Password-1!"},
    )
    return login.json()["access_token"]


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
        assert client.get("/api/v2/users/me").status_code == 401

    def test_with_invalid_token_is_401(self, client):
        assert client.get("/api/v2/users/me",
                          headers={"Authorization": "Bearer nope"}).status_code == 401


class TestPatchMe:
    def test_update_own_first_name(self, client, fetch_user):
        token = _register_and_login(client, "patch@example.com")
        r = client.patch("/api/v2/users/me", headers=_auth(token), json={"first_name": "Alice"})
        assert r.status_code == 200, r.text
        assert r.json()["first_name"] == "Alice"
        assert fetch_user("patch@example.com")["first_name"] == "Alice"

    def test_cannot_self_promote_to_superuser(self, client, fetch_user):
        token = _register_and_login(client, "selfadmin@example.com")
        r = client.patch("/api/v2/users/me", headers=_auth(token), json={"is_superuser": True})
        assert r.status_code == 200, r.text
        assert r.json()["is_superuser"] is False
        assert fetch_user("selfadmin@example.com")["is_superuser"] is False


# ── /users/{id} — admin only ───────────────────────────────────────────────

class TestAdminGetUser:
    def test_admin_can_fetch_any_user(self, client, fetch_user, promote_admin):
        admin_token = _register_and_login(client, "admin@example.com", promote=promote_admin)
        _register_and_login(client, "alice@example.com")
        alice_id = fetch_user("alice@example.com")["id"]
        r = client.get(f"/api/v2/users/{alice_id}", headers=_auth(admin_token))
        assert r.status_code == 200, r.text
        assert r.json()["email"] == "alice@example.com"

    def test_non_admin_cannot_fetch_other_user(self, client, fetch_user):
        bob_token = _register_and_login(client, "bob@example.com")
        _register_and_login(client, "alice@example.com")
        alice_id = fetch_user("alice@example.com")["id"]
        r = client.get(f"/api/v2/users/{alice_id}", headers=_auth(bob_token))
        assert r.status_code == 403


class TestAdminPatchUser:
    def test_admin_can_promote_user(self, client, fetch_user, promote_admin):
        admin_token = _register_and_login(client, "boss@example.com", promote=promote_admin)
        _register_and_login(client, "promote@example.com")
        uid = fetch_user("promote@example.com")["id"]

        r = client.patch(f"/api/v2/users/{uid}", headers=_auth(admin_token),
                         json={"is_superuser": True})
        assert r.status_code == 200, r.text
        assert r.json()["is_superuser"] is True

        # Legacy `role` column kept in sync by AsyncUserDatabase.update().
        u = fetch_user("promote@example.com")
        assert u["is_superuser"] is True
        assert u["role"] == "Admin"


class TestAdminDeleteUser:
    def test_admin_can_delete_user(self, client, fetch_user, promote_admin):
        admin_token = _register_and_login(client, "deleter@example.com", promote=promote_admin)
        _register_and_login(client, "victim@example.com")
        uid = fetch_user("victim@example.com")["id"]

        r = client.delete(f"/api/v2/users/{uid}", headers=_auth(admin_token))
        assert r.status_code == 204
        assert fetch_user("victim@example.com") is None

    def test_non_admin_cannot_delete(self, client, fetch_user):
        bob_token = _register_and_login(client, "innocent@example.com")
        _register_and_login(client, "target@example.com")
        uid = fetch_user("target@example.com")["id"]
        r = client.delete(f"/api/v2/users/{uid}", headers=_auth(bob_token))
        assert r.status_code == 403
