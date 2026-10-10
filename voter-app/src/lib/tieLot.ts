// tieLot — exact ties in a voting rule are drawn by lot, never by the order the
// candidates were listed in (docs/plan/vote-app/LISTING_ORDER_TIES.md: decided
// 2026-10-09).
//
// The twin of fast_api_voter/api/engine/utils/tie_lot.py: FNV-1a (32-bit) over the UTF-8
// bytes of the seed and the tied names in code-point order, joined by U+001F; the index
// is that hash modulo the number of tied names. Keep the two in step: tieLot.test.ts and
// test_tie_lot.py pin the same values.

const SEP = '\u001f';

function fnv1a(bytes: Uint8Array): number {
  let h = 0x811c9dc5;
  for (const b of bytes) h = Math.imul(h ^ b, 0x01000193) >>> 0;
  return h;
}

/** Code-point order, as Python's `sorted` on str (UTF-16 order differs past U+FFFF). */
function byCodePoint(a: string, b: string): number {
  const x = Array.from(a, (c) => c.codePointAt(0)!);
  const y = Array.from(b, (c) => c.codePointAt(0)!);
  for (let i = 0; i < Math.min(x.length, y.length); i++) if (x[i] !== y[i]) return x[i] - y[i];
  return x.length - y.length;
}

const ENCODER = new TextEncoder();

/** One of `tied`, drawn by the seeded lot over their names. */
export function drawName(tied: readonly string[], seed = 0): string {
  const names = [...tied].sort(byCodePoint);
  return names[fnv1a(ENCODER.encode([String(seed), ...names].join(SEP))) % names.length];
}

/** The index among `pool` drawn by lot over their names, mapped back within `pool` (so
 * a name two candidates share cannot pick one outside it). */
export function drawIndex(pool: readonly number[], names: readonly string[], seed = 0): number {
  const drawn = drawName(
    pool.map((i) => names[i]),
    seed
  );
  return pool.find((i) => names[i] === drawn)!;
}

/** Equal up to float noise, as tie_lot.py's `tied` (Python's math.isclose with 1e-9
 * relative, 1e-12 absolute): the engines' logs and sums can differ in the last bits. */
export function isTied(a: number, b: number): boolean {
  // An infinity is close only to itself, as in Python (Infinity - x is not finite).
  const gap = a - b;
  return (
    a === b ||
    (Number.isFinite(gap) &&
      Math.abs(gap) <= Math.max(1e-9 * Math.max(Math.abs(a), Math.abs(b)), 1e-12))
  );
}

/** The index with the highest value; a tie for it (see `isTied`) is drawn by lot over `names`. */
export function bestIndex(values: readonly number[], names: readonly string[], seed = 0): number {
  let top = -Infinity;
  for (const v of values) if (v > top) top = v;
  const tied = values.flatMap((v, i) => (isTied(v, top) ? [i] : []));
  // Every value NaN: none ranks, so the first index, as argmax always answered.
  if (tied.length === 0) return 0;
  return tied.length === 1 ? tied[0] : drawIndex(tied, names, seed);
}
