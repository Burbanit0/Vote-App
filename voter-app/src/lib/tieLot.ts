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

/** One of `tied`, drawn by the seeded lot over their names. */
export function drawName(tied: readonly string[], seed = 0): string {
  const names = [...tied].sort(byCodePoint);
  const key = new TextEncoder().encode([String(seed), ...names].join(SEP));
  return names[fnv1a(key) % names.length];
}

/** The index with the highest value; an exact tie for it is drawn by lot over `names`. */
export function bestIndex(values: readonly number[], names: readonly string[], seed = 0): number {
  const top = Math.max(...values);
  const tied = values.flatMap((v, i) => (v === top ? [i] : []));
  if (tied.length === 1) return tied[0];
  return names.indexOf(
    drawName(
      tied.map((i) => names[i]),
      seed
    )
  );
}

/** The index among `pool` drawn by lot over their names. */
export function drawIndex(pool: readonly number[], names: readonly string[], seed = 0): number {
  return names.indexOf(
    drawName(
      pool.map((i) => names[i]),
      seed
    )
  );
}
