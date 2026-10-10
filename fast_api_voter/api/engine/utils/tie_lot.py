"""Exact ties in a voting rule are drawn by lot, never by the order the candidates
were listed in (docs/plan/vote-app/LISTING_ORDER_TIES.md: decided 2026-10-09).

The lot is a seeded hash of the tied names, sorted: reproducible, the same whatever
the listing order, and computed the same way by the client engine
(voter-app/src/lib/tieLot.ts). Keep the two in step: FNV-1a (32-bit) over the UTF-8
bytes of the seed and the sorted names, joined by U+001F; the index is that hash
modulo the number of tied names. test_tie_lot.py pins values the client test pins too.

`ranking` and `nearest` (a voter's own ranking and nearest option, backend only) order a
tie differently: by one finalised hash per name (`_voter_lot`), of the seed and that name,
so a tie falls like a fair coin from one voter to the next.
"""

import math
import re
from typing import Any, Callable, Iterable, List, Sequence, TypeVar

import numpy as np

T = TypeVar("T")

_FNV_OFFSET = 0x811C9DC5
_FNV_PRIME = 0x01000193
_SEP = "\x1f"
# A lone surrogate (JSON allows one) hashes as U+FFFD, as the client's TextEncoder does.
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def _fnv1a(data: bytes) -> int:
    h = _FNV_OFFSET
    for byte in data:
        h = ((h ^ byte) * _FNV_PRIME) & 0xFFFFFFFF
    return h


def _hash(*parts: object) -> int:
    key = _LONE_SURROGATE.sub("\ufffd", _SEP.join(map(str, parts)))
    return _fnv1a(key.encode("utf-8"))


def _voter_lot(seed: object, name: object) -> int:
    """A per-voter lot key: FNV-1a finalised with murmur3's fmix32. FNV-1a's low bit is
    only the parity of its input bytes, so names differing in their last byte would
    alternate with the voter's index; the finaliser mixes every bit into every other.
    Backend only (`ranking`, `nearest`): `draw`, which the client mirrors, is unchanged."""
    h = _hash(seed, name)
    h = ((h ^ (h >> 16)) * 0x85EBCA6B) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 0xC2B2AE35) & 0xFFFFFFFF
    return h ^ (h >> 16)


def draw(tied: Iterable[T], seed: object = 0) -> T:
    """One of `tied`, drawn by the seeded lot over their names in code-point order."""
    names = sorted(tied, key=str)
    return names[_hash(seed, *names) % len(names)]


def ranking(names: Iterable[T], value: Callable[[T], float], seed: object = 0) -> List[T]:
    """`names` by value, highest first. A tie (see `tied`) is ordered by a hash of the
    seed and each name, never by the listing order; seed it per voter (their id), so a
    tie falls differently from one voter to the next. Only a tie is hashed: a ranking
    without one costs a plain sort. Backend only: no twin in tieLot.ts."""
    out: List[T] = []
    run: List[T] = []
    for n in sorted(names, key=lambda n: -value(n)):
        if run and not tied(value(n), value(run[0])):
            out += _lot_order(run, seed)
            run = []
        run.append(n)
    return out + _lot_order(run, seed)


def _lot_order(run: List[T], seed: object) -> List[T]:
    return run if len(run) < 2 else sorted(run, key=lambda n: (_voter_lot(seed, n), str(n)))


def tied(a: float, b: float) -> bool:
    """Equal up to float noise: 1e-9 relative (1e-12 absolute), as `break_tie` reads a
    tie. Sums and logarithms computed in another order, or by the client's Math.log, can
    differ in the last bits; exact equality would make the two engines disagree."""
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def best(candidates: Iterable[T], value: Callable[[T], float], seed: object = 0) -> T:
    """The candidate with the highest value; a tie for it (see `tied`) is drawn by lot."""
    pool = list(candidates)
    values = [value(c) for c in pool]
    ranked = [v for v in values if not math.isnan(v)]
    # Every value NaN: none ranks, so the first, as the client's bestIndex answers.
    if not ranked:
        return pool[0]
    top = max(ranked)
    return draw([c for c, v in zip(pool, values) if tied(v, top)], seed)


def nearest(
    dist: Any, names: Sequence[str], seed: object = 0, rows: Any = None
) -> "np.ndarray[Any, Any]":
    """Per row of `dist` (voters x options), the column with the smallest value, as
    `dist.argmin(axis=1)`; a tie (see `tied`) is drawn by lot among the tied options'
    names (the lowest `_voter_lot` of `seed` and the row: `rows[r]`, else `r`), so it
    falls differently from one voter to the next and never by listing order. For an
    argmax, pass `-scores`."""
    d = np.asarray(dist, dtype=float)
    low = d.min(axis=1, keepdims=True)
    with np.errstate(invalid="ignore"):
        gap = np.abs(d - low)
        tie = (d == low) | (gap <= np.maximum(1e-9 * np.maximum(np.abs(d), np.abs(low)), 1e-12))
    out = d.argmin(axis=1)
    for r in np.flatnonzero(tie.sum(axis=1) > 1).tolist():
        cols = np.flatnonzero(tie[r]).tolist()
        key = f"{seed}:{r if rows is None else rows[r]}"
        out[r] = min(cols, key=lambda c: (_voter_lot(key, names[c]), str(names[c])))
    return out

