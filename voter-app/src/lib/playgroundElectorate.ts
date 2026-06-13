// playgroundElectorate.ts — a richer, composable electorate generator.
//
// Instead of one Gaussian blob, the electorate is a MIXTURE of communities
// (blocs), each with a centre, spread, relative size and turnout propensity,
// plus an axis correlation. This produces multimodal, realistic-or-bespoke
// electorates. Pure + deterministic (seed); the dimension collapses unused axes
// like sampleVoters. Returns the voters who turn out, tagged by community for
// colouring on the maps.

import type { Dims, Pt } from './playgroundVoting';

export interface Community {
  id: string;
  label: string;
  x: number;
  y: number;
  /** 3rd-axis centre (only used when dims === 3); optional, defaults to 0. */
  z?: number;
  /** Standard deviation of the bloc cloud. */
  spread: number;
  /** Relative size (sampling weight). */
  weight: number;
  /** Participation propensity in [0,1] — the bloc's turnout. */
  turnout: number;
}

export interface ComposedElectorate {
  voters: Pt[];
  /** Community index per voter (aligned with `voters`), for colouring. */
  community: number[];
}

// Muted palette for voter blocs — distinct from the saturated candidate palette.
export const COMMUNITY_PALETTE = [
  '#60a5fa',
  '#f87171',
  '#34d399',
  '#c084fc',
  '#fb923c',
  '#22d3ee',
  '#facc15',
  '#f472b6',
];

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gauss(rng: () => number, mu: number, sigma: number): number {
  const u = Math.max(rng(), 1e-9);
  const v = rng();
  return mu + sigma * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

const clamp = (v: number): number => Math.max(-1, Math.min(1, v));

/**
 * Sample an electorate of (up to) `n` voters from the community mixture.
 * `correlation` ∈ [-1,1] couples the x and y deviations within each bloc.
 * Per-community `turnout` thins that bloc (Bernoulli) — abstainers are dropped,
 * so the result is the *voting* electorate. `noise` ∈ [0,1] adds a global
 * measurement/polling jitter on every active axis — distinct from each bloc's
 * (real) `spread`: it blurs the observed positions uniformly, the way a survey
 * measures the electorate with error. Always returns ≥ 2 voters.
 */
export function composeElectorate(
  communities: Community[],
  correlation: number,
  n: number,
  seed: number,
  dims: Dims = 2,
  noise = 0
): ComposedElectorate {
  const live = communities.filter((c) => c.weight > 0);
  if (!live.length) return { voters: [], community: [] };
  const rng = mulberry32(seed);
  const total = live.reduce((s, c) => s + c.weight, 0);
  const cum: number[] = [];
  let acc = 0;
  for (const c of live) {
    acc += c.weight / total;
    cum.push(acc);
  }
  const rho = Math.max(-1, Math.min(1, correlation));
  const coShare = Math.sqrt(Math.max(0, 1 - rho * rho));
  // Measurement jitter: a modest absolute σ so the slider stays legible.
  const nSigma = Math.max(0, Math.min(1, noise)) * 0.3;

  const voters: Pt[] = [];
  const community: number[] = [];
  for (let i = 0; i < n; i++) {
    const r = rng();
    let ci = cum.findIndex((c) => r <= c);
    if (ci < 0) ci = live.length - 1;
    const bloc = live[ci];
    // Draw all 3 axis deviations (constant RNG use → stable across dims).
    const ex = gauss(rng, 0, bloc.spread);
    const ey = gauss(rng, 0, bloc.spread);
    const ez = gauss(rng, 0, bloc.spread);
    // Measurement noise draws (always consumed → determinism across noise=0).
    const nx = gauss(rng, 0, nSigma);
    const ny = gauss(rng, 0, nSigma);
    const nz = gauss(rng, 0, nSigma);
    const turn = rng(); // turnout draw (always consumed for determinism)
    if (turn > bloc.turnout) continue; // abstains
    voters.push({
      x: clamp(bloc.x + ex + nx),
      y: dims >= 2 ? clamp(bloc.y + (rho * ex + coShare * ey) + ny) : 0,
      z: dims >= 3 ? clamp((bloc.z ?? 0) + ez + nz) : 0,
    });
    // Map back to the original community index (for stable colours).
    community.push(communities.indexOf(bloc));
  }
  // Never hand back an empty electorate — fall back to bloc centres.
  if (voters.length < 2) {
    return {
      voters: live.map((c) => ({
        x: clamp(c.x),
        y: dims >= 2 ? clamp(c.y) : 0,
        z: dims >= 3 ? clamp(c.z ?? 0) : 0,
      })),
      community: live.map((c) => communities.indexOf(c)),
    };
  }
  return { voters, community };
}
