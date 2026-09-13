"""Tests for GET /api/v2/metrics (Lot 10, PLAN_SOLIDITE_TECHNIQUE.md)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.core.config import get_settings
from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """get_settings() is lru_cache'd (api/core/config.py) -- clear it around
    each test so a monkeypatched METRICS_AUTH_TOKEN actually takes effect
    instead of returning a Settings instance built before the env var was set."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestMetricsExposition:
    def test_metrics_returns_200_with_prometheus_content_type(self, client):
        r = client.get("/api/v2/metrics")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]
        assert len(r.text) > 0

    def test_metrics_reflects_real_traffic(self, client):
        """Hit a route, then confirm its counter incremented -- not just that
        the endpoint exists and returns *some* text."""
        client.get("/api/v2/health/live")
        client.get("/api/v2/health/live")
        body = client.get("/api/v2/metrics").text
        assert 'handler="/api/v2/health/live"' in body
        assert "http_requests_total" in body

    def test_metrics_endpoint_itself_is_excluded_from_its_own_counters(self, client):
        """excluded_handlers=[METRICS_PATH] in api/routes/metrics.py -- a
        scrape must not also observe itself."""
        client.get("/api/v2/metrics")
        client.get("/api/v2/metrics")
        body = client.get("/api/v2/metrics").text
        assert 'handler="/api/v2/metrics"' not in body


class TestMetricsAuth:
    def test_open_when_no_token_configured(self, client, monkeypatch):
        monkeypatch.delenv("METRICS_AUTH_TOKEN", raising=False)
        r = client.get("/api/v2/metrics")
        assert r.status_code == 200

    def test_401_without_authorization_header_when_token_configured(
        self, client, monkeypatch
    ):
        monkeypatch.setenv("METRICS_AUTH_TOKEN", "s3cr3t")
        r = client.get("/api/v2/metrics")
        assert r.status_code == 401

    def test_401_with_wrong_token(self, client, monkeypatch):
        monkeypatch.setenv("METRICS_AUTH_TOKEN", "s3cr3t")
        r = client.get(
            "/api/v2/metrics", headers={"Authorization": "Bearer wrong"}
        )
        assert r.status_code == 401

    def test_200_with_correct_bearer_token(self, client, monkeypatch):
        monkeypatch.setenv("METRICS_AUTH_TOKEN", "s3cr3t")
        r = client.get(
            "/api/v2/metrics", headers={"Authorization": "Bearer s3cr3t"}
        )
        assert r.status_code == 200

    def test_other_routes_unaffected_by_metrics_token(self, client, monkeypatch):
        monkeypatch.setenv("METRICS_AUTH_TOKEN", "s3cr3t")
        r = client.get("/api/v2/health/live")
        assert r.status_code == 200
