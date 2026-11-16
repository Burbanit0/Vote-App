"""api.sockets.limits.StartLimiter: a sliding window of starts per client address."""
from api.sockets import limits
from api.sockets.limits import StartLimiter


def test_allows_up_to_the_limit_then_refuses_and_records_nothing_more():
    lim = StartLimiter(max_starts=3, window=60)
    assert [lim.allow("a", now=t) for t in (0, 1, 2)] == [True, True, True]
    assert lim.allow("a", now=3) is False
    assert lim.allow("a", now=59) is False
    # A refusal is not a start: the window opens when the first start leaves it.
    assert lim.allow("a", now=60) is True


def test_addresses_are_counted_apart():
    lim = StartLimiter(max_starts=1, window=60)
    assert lim.allow("a", now=0) is True
    assert lim.allow("b", now=0) is True
    assert lim.allow("a", now=1) is False


def test_the_defaults_are_ten_a_minute():
    lim = StartLimiter()
    assert [lim.allow("a", now=0) for _ in range(11)] == [True] * 10 + [False]
    assert lim.allow("a", now=60.0) is True


def test_the_clock_defaults_to_monotonic():
    lim = StartLimiter(max_starts=1)
    assert lim.allow("a") is True
    assert lim.allow("a") is False


def test_clear_forgets_everything():
    lim = StartLimiter(max_starts=1)
    lim.allow("a", now=0)
    lim.clear()
    assert lim.allow("a", now=1) is True


def test_idle_addresses_are_forgotten_once_there_are_very_many(monkeypatch):
    monkeypatch.setattr(limits, "_PRUNE_ABOVE", 3)
    lim = StartLimiter(max_starts=1, window=10)
    for name in "abc":
        lim.allow(name, now=0)
    lim.allow("d", now=100)  # a, b, c are idle by now, d is not
    assert set(lim._starts) == {"d"}
