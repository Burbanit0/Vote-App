"""The tie lot (api/engine/utils/tie_lot.py). voter-app/src/lib/tieLot.test.ts pins the
same values: the two engines must draw the same candidate from the same tie."""

import pytest

from api.engine.utils.tie_lot import _fnv1a, best, draw, tied


def test_the_hash_is_fnv1a_32():
    assert _fnv1a(b"") == 0x811C9DC5
    assert _fnv1a(b"a") == 0xE40C292C  # the published FNV-1a test vector


@pytest.mark.parametrize(
    "names, seed, drawn",
    [
        (["Ann", "Ben"], 0, "Ben"),
        (["Ann", "Ben"], 7, "Ann"),
        (["Alice", "Bob", "Carol"], 0, "Carol"),
        (["Alice", "Bob", "Carol"], 7, "Alice"),
        (["Zoé", "Émile", "Ana"], 0, "Zoé"),
        (["Zoé", "Émile", "Ana"], 7, "Ana"),
        (["C0", "C1", "C2", "C3"], 0, "C3"),
        (["C0", "C1", "C2", "C3"], 7, "C2"),
        (["Ann", "Anna"], 0, "Ann"),  # one name a prefix of the other
        (["Ann", "Anna"], 7, "Anna"),
    ],
)
def test_draw_pins_the_values_the_client_pins(names, seed, drawn):
    assert draw(names, seed) == drawn
    assert draw(list(reversed(names)), seed) == drawn  # listing order does not matter


def test_best_draws_only_among_the_tied_top():
    values = {"Ann": 3.0, "Ben": 3.0, "Cy": 1.0}
    assert best(["Cy", "Ben", "Ann"], values.__getitem__) == draw(["Ann", "Ben"])
    assert best(["Ann", "Cy"], {"Ann": 1.0, "Cy": 2.0}.__getitem__) == "Cy"


def test_float_noise_is_a_tie_and_a_real_gap_is_not():
    # Nash's logs: Python and the client's Math.log can differ in the last bits.
    assert tied(3.178053830347945, 3.1780538303479458)
    assert tied(float("-inf"), float("-inf"))
    assert not tied(1.0, 1.000001)
    assert not tied(float("inf"), 1e308)
    values = {"Bob": 3.1780538303479458, "Zed": 3.178053830347945, "Mo": 1.0}
    assert best(values, values.__getitem__) == draw(["Bob", "Zed"])

