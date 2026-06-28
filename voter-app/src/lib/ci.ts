// ci.ts — confidence intervals for the playground's Monte-Carlo readouts.
//
// Several readouts report a PROPORTION estimated by random sampling (a candidate's
// win rate over re-rolled electorates, a paradox rate, a temptation rate). A bare
// "62%" hides how much of that is sampling noise. This gives the honest version:
// a 95% interval and the sample size, so a wide bar on few draws reads as the
// uncertain estimate it is.
//
// Wilson score interval — chosen over the textbook normal approximation because it
// stays inside [0,1] and behaves correctly at the extremes (p near 0 or 1) and on
// small n, exactly where win rates live. Pure.

export interface Interval {
  /** Observed proportion k/n (the point estimate the bar shows). */
  p: number;
  lo: number;
  hi: number;
  /** Half-width (hi-lo)/2 — the "± x" annotation. */
  half: number;
  n: number;
}

/** 95% Wilson score interval for k successes in n Bernoulli trials. */
export function wilson(k: number, n: number, z = 1.96): Interval {
  if (n <= 0) return { p: 0, lo: 0, hi: 1, half: 0.5, n: 0 };
  const p = k / n;
  const z2 = z * z;
  const denom = 1 + z2 / n;
  const center = (p + z2 / (2 * n)) / denom;
  const margin = (z / denom) * Math.sqrt((p * (1 - p)) / n + z2 / (4 * n * n));
  const lo = Math.max(0, center - margin);
  const hi = Math.min(1, center + margin);
  return { p, lo, hi, half: (hi - lo) / 2, n };
}

/** Wilson interval from a proportion already divided (recovers k = round(rate·n)). */
export function wilsonFromRate(rate: number, n: number, z = 1.96): Interval {
  return wilson(Math.round(rate * n), n, z);
}

/** "62% ± 7%" — a compact point-estimate-with-margin for a label. */
export function pctPm(iv: Interval): string {
  return `${Math.round(iv.p * 100)}% ± ${Math.round(iv.half * 100)}%`;
}
