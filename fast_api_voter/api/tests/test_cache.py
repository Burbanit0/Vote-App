"""Tests for api.engine.utils.cache — the Redis result-cache helper."""
import json

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


class FakeRedis:
    """Enough of redis-py for cache_result: get/setex over a dict."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.gets = 0

    def get(self, key: str):
        self.gets += 1
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value


def _with_fake_redis(monkeypatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(cache_module, "_redis_client", fake)
    monkeypatch.setattr(cache_module, "_redis_tried", True)
    return fake


def test_a_repeated_call_is_served_from_the_cache(monkeypatch):
    """The regression this file did not catch: /election/simulate carried
    `@cache_result` on a worker nothing called, so every identical request paid
    full compute. Nothing tested `cache_result` end-to-end, which is how it went
    inert unnoticed."""
    fake = _with_fake_redis(monkeypatch)
    calls = []

    @cache_module.cache_result("test:prefix", ttl_seconds=60)
    def worker(data):
        calls.append(data)
        return {"winner": "Alice"}, 200

    first = worker({"seed": 42, "num_voters": 300})
    second = worker({"seed": 42, "num_voters": 300})

    assert first == second == ({"winner": "Alice"}, 200)
    assert len(calls) == 1, "second identical call should not have recomputed"
    assert len(fake.store) == 1


def test_key_is_the_input_not_its_dict_order(monkeypatch):
    fake = _with_fake_redis(monkeypatch)
    calls = []

    @cache_module.cache_result("test:prefix")
    def worker(data):
        calls.append(data)
        return {"ok": True}, 200

    worker({"a": 1, "b": 2})
    worker({"b": 2, "a": 1})          # same request, keys written the other way
    assert len(calls) == 1

    worker({"a": 1, "b": 3})          # genuinely different input
    assert len(calls) == 2
    assert len(fake.store) == 2


def test_error_results_are_never_cached(monkeypatch):
    """A 400 is a property of the request, but caching it would pin the error
    for an hour even after the cause is fixed elsewhere."""
    fake = _with_fake_redis(monkeypatch)
    calls = []

    @cache_module.cache_result("test:prefix")
    def worker(data):
        calls.append(data)
        return {"error": "At least 2 candidates required"}, 400

    worker({"candidates": []})
    worker({"candidates": []})

    assert len(calls) == 2
    assert fake.store == {}


def test_a_redis_outage_falls_through_to_the_real_worker(monkeypatch, caplog):
    class BrokenRedis(FakeRedis):
        def get(self, key):
            raise ConnectionError("redis went away mid-request")

    monkeypatch.setattr(cache_module, "_redis_client", BrokenRedis())
    monkeypatch.setattr(cache_module, "_redis_tried", True)

    @cache_module.cache_result("test:prefix")
    def worker(data):
        return {"winner": "Alice"}, 200

    with caplog.at_level("WARNING"):
        assert worker({"seed": 1}) == ({"winner": "Alice"}, 200)
    assert "cache read failed" in caplog.text


def test_simulate_is_the_cached_entry_point(monkeypatch):
    """The decorator belongs on the name the route actually reaches. It used to
    sit on `workers._simulate_worker`, which nothing imported.

    Asserting `second == first` would prove nothing -- simulate is
    deterministic, so a full recompute returns the same body. The second call
    has to be shown to come from the store, so the stored value is replaced
    with a marker first."""
    from api.domain.election import simulate

    fake = _with_fake_redis(monkeypatch)
    data = {
        "candidates": [{"name": "Alice", "x": -0.5, "y": 0.0},
                       {"name": "Bob", "x": 0.4, "y": 0.0}],
        "num_voters": 50, "seed": 42,
    }
    _, status = simulate(dict(data))
    assert status == 200
    assert len(fake.store) == 1, "a 200 from /simulate should have been cached"

    key = next(iter(fake.store))
    assert key.startswith("election:simulate:")
    fake.store[key] = json.dumps({"winner": "served-from-cache"})

    second, status = simulate(dict(data))
    assert (second, status) == ({"winner": "served-from-cache"}, 200)


def test_election_service_simulate_stays_uncached(monkeypatch):
    """The pure function keeps its own identity: `test_seeded_rng_isolation`
    calls it twice with identical input to inject interference mid-run, which a
    cache hit would skip entirely."""
    from api.domain.election import election_service

    fake = _with_fake_redis(monkeypatch)
    data = {
        "candidates": [{"name": "Alice", "x": -0.5, "y": 0.0},
                       {"name": "Bob", "x": 0.4, "y": 0.0}],
        "num_voters": 50, "seed": 42,
    }
    election_service.simulate(dict(data))
    election_service.simulate(dict(data))
    assert fake.store == {}, "the pure function must not touch Redis"


def test_a_cached_value_that_is_not_an_object_is_recomputed(monkeypatch):
    """A JSON value that decodes to a list or null used to be returned AS the
    body with a hardcoded 200, so `SimulateResponse.model_validate` raised and
    the route 500'd -- and since the read succeeded nothing rewrote the key, so
    it stayed poisoned for the whole hour."""
    fake = _with_fake_redis(monkeypatch)
    calls = []

    @cache_module.cache_result("test:prefix")
    def worker(data):
        calls.append(data)
        return {"winner": "Alice"}, 200

    worker({"seed": 1})                       # populate
    key = next(iter(fake.store))
    for poison in ("[1, 2, 3]", "null", "12", '"a string"'):
        fake.store[key] = poison
        assert worker({"seed": 1}) == ({"winner": "Alice"}, 200)
        assert fake.store[key] != poison, "the poisoned key should be overwritten"
