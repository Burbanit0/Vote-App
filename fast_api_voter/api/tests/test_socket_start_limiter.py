"""api.sockets.limits.StartLimiter: a sliding window of starts per client address."""
from api.sockets import limits
from api.sockets.limits import StartLimiter


def test_allows_up_to_the_limit_then_refuses_and_records_nothing_more():
    lim = StartLimiter(max_starts=3, window=60, max_live=9)
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


def test_the_defaults_are_ten_a_minute_and_two_at_once():
    lim = StartLimiter()
    assert [lim.allow("a", now=0) for _ in range(3)] == [True, True, False]  # two live at once
    for _ in range(3):
        lim.finish("a")  # a third finish, with nothing live, is harmless
    ran = []
    for _ in range(10):  # two starts are already in the window; run-to-end ones from here
        ran.append(lim.allow("a", now=0))
        lim.finish("a")
    assert ran == [True] * 8 + [False] * 2
    assert lim.allow("a", now=60.0) is True


def test_a_finished_run_frees_its_slot_but_not_its_place_in_the_window():
    lim = StartLimiter(max_starts=5, window=60, max_live=1)
    assert lim.allow("a", now=0) is True
    assert lim.allow("a", now=1) is False  # one still going
    lim.finish("a")
    assert lim.allow("a", now=2) is True
    lim.finish("a")
    assert [lim.allow("a", now=3 + i) and lim.finish("a") is None for i in range(5)].count(True) == 3


def test_the_clock_defaults_to_monotonic():
    lim = StartLimiter(max_starts=1)
    assert lim.allow("a") is True
    assert lim.allow("a") is False


def test_clear_forgets_everything():
    lim = StartLimiter(max_starts=1, max_live=1)
    lim.allow("a", now=0)
    lim.clear()
    assert lim.allow("a", now=1) is True


def test_idle_addresses_are_forgotten_once_there_are_very_many(monkeypatch):
    monkeypatch.setattr(limits, "_PRUNE_ABOVE", 3)
    lim = StartLimiter(max_starts=1, window=10, max_live=9)
    for name in "abc":
        lim.allow(name, now=0)
        lim.finish(name)
    lim.allow("d", now=100)  # a, b, c are idle by now, d is new
    assert set(lim._starts) == {"d"}
    # Having pruned, the next pass waits until the table has doubled, not for every start.
    assert lim._prune_at == 3


def test_an_address_with_a_run_going_is_not_forgotten_however_old_its_start():
    lim = StartLimiter(max_starts=1, window=10, max_live=9)
    lim.allow("a", now=0)
    lim.finish("a")
    lim.allow("e", now=0)  # still going
    lim._forget_idle(now=100)
    assert set(lim._starts) == {"e"}
