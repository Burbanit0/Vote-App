"""Tests for the admin_required decorator."""

import pytest


class TestAdminRequiredDecorator:

    def test_admin_can_access_admin_endpoint(self, client, init_db, admin_auth_header):
        response = client.get("/api/auth/", headers=admin_auth_header)
        assert response.status_code == 200

    def test_regular_user_rejected_from_admin_endpoint(self, client, init_db, auth_header):
        response = client.get("/api/auth/", headers=auth_header)
        assert response.status_code == 403
        body = response.get_json()
        assert "Admin access required" in body.get("error", "")

    def test_no_token_rejected_from_admin_endpoint(self, client, init_db):
        response = client.get("/api/auth/")
        assert response.status_code == 401

    def test_admin_can_update_user(self, client, init_db, admin_auth_header):
        response = client.put("/api/auth/1", json={"first_name": "Updated"}, headers=admin_auth_header)
        assert response.status_code == 200

    def test_regular_user_cannot_update_user(self, client, init_db, auth_header):
        response = client.put("/api/auth/1", json={"first_name": "Updated"}, headers=auth_header)
        assert response.status_code == 403
