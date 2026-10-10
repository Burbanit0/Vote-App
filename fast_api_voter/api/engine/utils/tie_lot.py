"""Exact ties in a voting rule are drawn by lot, never by the order the candidates
were listed in (docs/plan/vote-app/LISTING_ORDER_TIES.md: decided 2026-10-09).

The lot is a seeded hash of the tied names, sorted: reproducible, the same whatever
the listing order, and computed the same way by the client engine
(voter-app/src/lib/tieLot.ts). Keep the two in step: FNV-1a (32-bit) over the UTF-8
bytes of the seed and the sorted names, joined by U+001F; the index is that hash
modulo the number of tied names. test_tie_lot.py pins values the client test pins too.
"""

import math
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")

_FNV_OFFSET = 0x811C9DC5
_FNV_PRIME = 0x01000193
_SEP = "\x1f"


def _fnv1a(data: bytes) -> int:
    h = _FNV_OFFSET
    for byte in data:
        h = ((h ^ byte) * _FNV_PRIME) & 0xFFFFFFFF
    return h


def draw(tied: Iterable[T], seed: int = 0) -> T:
    """One of `tied`, drawn by the seeded lot over their names in code-point order."""
    names = sorted(tied, key=str)
    key = _SEP.join([str(seed), *map(str, names)]).encode("utf-8")
    return names[_fnv1a(key) % len(names)]


def tied(a: float, b: float) -> bool:
    """Equal up to float noise: 1e-9 relative (1e-12 absolute), as `break_tie` reads a
    tie. Sums and logarithms computed in another order, or by the client's Math.log, can
    differ in the last bits; exact equality would make the two engines disagree."""
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def best(candidates: Iterable[T], value: Callable[[T], float], seed: int = 0) -> T:
    """The candidate with the highest value; a tie for it (see `tied`) is drawn by lot."""
    pool = list(candidates)
    top = max(value(c) for c in pool)
    return draw([c for c in pool if tied(value(c), top)], seed)
