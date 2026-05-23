"""Tests for app.utils.cache.cache_result Redis memoisation decorator."""
import json
from unittest.mock import MagicMock, patch

import pytest


# ── _stable_hash determinism ─────────────────────────────────────────────────

def test_stable_hash_is_deterministic():
    from app.utils.cache import _stable_hash
    a = {"foo": 1, "bar": [1, 2, 3]}
    b = {"bar": [1, 2, 3], "foo": 1}  # different insertion order
    assert _stable_hash(a) == _stable_hash(b)


def test_stable_hash_differs_for_different_inputs():
    from app.utils.cache import _stable_hash
    assert _stable_hash({"x": 1}) != _stable_hash({"x": 2})


def test_stable_hash_is_64_hex_chars():
    from app.utils.cache import _stable_hash
    h = _stable_hash({"x": 1})
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ── cache_result behaviour ──────────────────────────────────────────────────

@pytest.fixture
def app_context():
    from app import create_app
    app = create_app("config.TestingConfig")
    with app.app_context():
        yield app


def test_cache_miss_runs_worker_and_stores_result(app_context):
    """First call should miss the cache, run the worker, and SETEX the body."""
    from app.utils import cache as cache_mod

    fake_redis = MagicMock()
    fake_redis.get.return_value = None  # miss

    worker = MagicMock(return_value=({"winner": "Alice"}, 200))
    decorated = cache_mod.cache_result("test", ttl_seconds=60)(worker)

    with patch.object(cache_mod, "__getattr__", create=True):
        with patch("app.redis_client", fake_redis):
            body, status = decorated({"seed": 42})

    assert body == {"winner": "Alice"}
    assert status == 200
    worker.assert_called_once_with({"seed": 42})
    fake_redis.setex.assert_called_once()
    args = fake_redis.setex.call_args[0]
    assert args[0].startswith("test:")           # key prefix
    assert args[1] == 60                          # TTL
    assert json.loads(args[2]) == {"winner": "Alice"}


def test_cache_hit_returns_cached_body_without_running_worker(app_context):
    from app.utils import cache as cache_mod

    fake_redis = MagicMock()
    fake_redis.get.return_value = json.dumps({"winner": "Bob"}).encode()

    worker = MagicMock(return_value=({"winner": "FRESH"}, 200))
    decorated = cache_mod.cache_result("test", ttl_seconds=60)(worker)

    with patch("app.redis_client", fake_redis):
        body, status = decorated({"seed": 42})

    assert body == {"winner": "Bob"}
    assert status == 200
    worker.assert_not_called()
    fake_redis.setex.assert_not_called()


def test_non_200_results_are_not_cached(app_context):
    from app.utils import cache as cache_mod

    fake_redis = MagicMock()
    fake_redis.get.return_value = None

    worker = MagicMock(return_value=({"error": "bad"}, 400))
    decorated = cache_mod.cache_result("test")(worker)

    with patch("app.redis_client", fake_redis):
        body, status = decorated({"seed": 42})

    assert status == 400
    worker.assert_called_once()
    fake_redis.setex.assert_not_called()


def test_redis_read_failure_falls_through_to_worker(app_context):
    from app.utils import cache as cache_mod

    fake_redis = MagicMock()
    fake_redis.get.side_effect = ConnectionError("redis down")

    worker = MagicMock(return_value=({"winner": "Alice"}, 200))
    decorated = cache_mod.cache_result("test")(worker)

    with patch("app.redis_client", fake_redis):
        body, status = decorated({"seed": 42})

    assert body == {"winner": "Alice"}
    assert status == 200
    worker.assert_called_once()


def test_redis_write_failure_does_not_crash_request(app_context):
    from app.utils import cache as cache_mod

    fake_redis = MagicMock()
    fake_redis.get.return_value = None
    fake_redis.setex.side_effect = ConnectionError("redis down")

    worker = MagicMock(return_value=({"winner": "Alice"}, 200))
    decorated = cache_mod.cache_result("test")(worker)

    with patch("app.redis_client", fake_redis):
        body, status = decorated({"seed": 42})

    assert body == {"winner": "Alice"}
    assert status == 200


def test_different_inputs_get_different_cache_keys(app_context):
    from app.utils import cache as cache_mod

    fake_redis = MagicMock()
    fake_redis.get.return_value = None

    worker = MagicMock(side_effect=[({"x": 1}, 200), ({"x": 2}, 200)])
    decorated = cache_mod.cache_result("test")(worker)

    with patch("app.redis_client", fake_redis):
        decorated({"seed": 1})
        decorated({"seed": 2})

    assert fake_redis.setex.call_count == 2
    keys = [c.args[0] for c in fake_redis.setex.call_args_list]
    assert keys[0] != keys[1]


def test_input_order_does_not_change_cache_key(app_context):
    """{a:1, b:2} and {b:2, a:1} should hit the same cache key."""
    from app.utils import cache as cache_mod

    fake_redis = MagicMock()
    fake_redis.get.return_value = None

    worker = MagicMock(return_value=({"winner": "Alice"}, 200))
    decorated = cache_mod.cache_result("test")(worker)

    with patch("app.redis_client", fake_redis):
        decorated({"a": 1, "b": 2})
        # Second call with different insertion order — should read the prior set
        fake_redis.get.return_value = json.dumps({"winner": "Alice"}).encode()
        decorated({"b": 2, "a": 1})

    keys_written = [c.args[0] for c in fake_redis.setex.call_args_list]
    keys_read    = [c.args[0] for c in fake_redis.get.call_args_list]
    assert keys_written[0] == keys_read[1]
