// playgroundDynamics.ts — pure helpers for the playground's dynamic layer
// (Lab reshape P4): the campaign time scrubber and the "shake the assumptions"
// Monte-Carlo robustness read-out. Both are explicit, documented models — knobs,
// not smuggled assumptions.

import {
  ruleWinner,
  sampleVoters,
  type Dims,
  type NamedPt,
  type Pt,
  type Rule,
} from './playgroundVoting';

/** Coordinate-wise median of a point cloud (the median voter), all 3 axes. */
export function medianPoint(voters: Pt[]): Pt {
  if (!voters.length) return { x: 0, y: 0, z: 0 };
  const med = (xs: number[]): number => {
    const s = [...xs].sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };
  return {
    x: med(voters.map((v) => v.x)),
    y: med(voters.map((v) => v.y)),
    z: med(voters.map((v) => v.z ?? 0)),
  };
}

/**
 * Campaign drift (the time scrubber's model): vote-seeking candidates drift
 * toward the median voter — Hotelling/Downs convergence. `t` ∈ [0,1] is campaign
 * progress, `strength` how far a candidate travels by the end (0.6 = 60% of the
 * way). Deliberately simple and stated; the deep campaign workers stay the
 * source of truth for the detailed model.
 */
export function driftCandidates(
  candidates: NamedPt[],
  target: Pt,
  t: number,
  strength = 0.6
): NamedPt[] {
  const k = Math.max(0, Math.min(1, t)) * strength;
  return candidates.map((c) => ({
    name: c.name,
    x: c.x + (target.x - c.x) * k,
    y: c.y + (target.y - c.y) * k,
    z: (c.z ?? 0) + ((target.z ?? 0) - (c.z ?? 0)) * k,
  }));
}

export interface ShakeResult {
  /** Win rate per candidate name over the re-rolled electorates, in [0,1]. */
  rates: Record<string, number>;
  /** Name with the highest win rate. */
  top: string | null;
  replications: number;
}

/**
 * "Shake the assumptions": re-roll the voter cloud `n` times (same ideology
 * family, fresh seeds) and measure how often each candidate wins under `rule`.
 * "This winner holds X% of the time" separates a structural property from a
 * hand-picked artifact.
 */
export function shakeWinRates(
  candidates: NamedPt[],
  rule: Rule,
  numVoters: number,
  baseSeed: number,
  ideology: string,
  n = 60,
  dims: Dims = 2
): ShakeResult {
  const wins: Record<string, number> = {};
  candidates.forEach((c) => {
    wins[c.name] = 0;
  });
  for (let i = 0; i < n; i++) {
    const voters = sampleVoters(numVoters, baseSeed + 1009 + i * 17, ideology, dims);
    const w = ruleWinner(voters, candidates, rule);
    if (w >= 0) wins[candidates[w].name] += 1;
  }
  const rates: Record<string, number> = {};
  let top: string | null = null;
  for (const name of Object.keys(wins)) {
    rates[name] = wins[name] / n;
    if (top === null || rates[name] > rates[top]) top = name;
  }
  return { rates, top, replications: n };
}
