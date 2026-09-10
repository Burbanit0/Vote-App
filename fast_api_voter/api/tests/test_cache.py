"""Tests for api.engine.utils.cache — the Redis result-cache helper."""
import api.engine.utils.cache as cache_module


def test_get_redis_client_logs_and_returns_none_on_connection_failure(monkeypatch, caplog):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr(cache_module, "_redis_client", None)
    monkeypatch.setattr(cache_module, "_redis_tried", False)

    def _boom(*a, **kw):
        raise ConnectionError("no redis here")

    monkeypatch.setattr("redis.from_url", _boom)

    with caplog.at_level("WARNING"):
        client = cache_module._get_redis_client()

    assert client is None
    assert "cache.redis_client_init_failed" in caplog.text
