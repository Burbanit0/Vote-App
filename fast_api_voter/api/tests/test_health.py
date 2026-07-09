"""Tests for /api/v2/health and the root endpoint."""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestHealth:
    def test_health_returns_200_or_503(self, client):
        """Healthcheck always responds — never crashes.
        No REDIS_URL configured (stateless deploy / typical test env) → 200 'ok'
        (Redis is an optional cache). REDIS_URL set but unreachable → 503
        'degraded'. Assert on the union so both environments pass.
        """
        r = client.get("/api/v2/health")
        assert r.status_code in (200, 503)
        body = r.json()
        assert body["backend"] == "fastapi"
        assert body["status"] in ("ok", "degraded")
        assert "checks" in body
        assert "redis" in body["checks"]

    def test_health_payload_has_version_and_uptime(self, client):
        body = client.get("/api/v2/health").json()
        assert "version" in body
        assert isinstance(body["uptime_s"], (int, float))
        assert body["uptime_s"] >= 0


class TestRoot:
    def test_root_endpoint(self, client):
        r = client.get("/api/v2")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Vote Lab API v2"
        assert body["version"].startswith("2.")
        assert body["docs"] == "/api/v2/docs"

    def test_openapi_spec_is_published(self, client):
        """FastAPI exposes the OpenAPI 3 spec at /api/v2/openapi.json."""
        r = client.get("/api/v2/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert spec["info"]["title"] == "Vote Lab API v2"
        assert "/api/v2/election/simulate" in spec["paths"]
        assert "/api/v2/health" in spec["paths"]

    def test_swagger_docs_render(self, client):
        r = client.get("/api/v2/docs")
        assert r.status_code == 200
        assert b"swagger-ui" in r.content.lower() or b"openapi" in r.content.lower()
