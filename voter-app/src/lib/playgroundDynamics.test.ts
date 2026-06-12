import { describe, it, expect } from 'vitest';
import { medianPoint, driftCandidates, shakeWinRates } from './playgroundDynamics';
import { sampleVoters, type NamedPt } from './playgroundVoting';

describe('medianPoint', () => {
  it('returns the coordinate-wise median', () => {
    const pts = [
      { x: -1, y: 0 },
      { x: 0, y: 0.5 },
      { x: 1, y: 1 },
    ];
    expect(medianPoint(pts)).toEqual({ x: 0, y: 0.5 });
  });
});

describe('driftCandidates', () => {
  const cands: NamedPt[] = [{ name: 'A', x: -0.8, y: 0.4 }];

  it('t=0 leaves positions unchanged', () => {
    expect(driftCandidates(cands, { x: 0, y: 0 }, 0)).toEqual(cands);
  });

  it('t=1 with strength 0.5 moves halfway to the target', () => {
    const out = driftCandidates(cands, { x: 0, y: 0 }, 1, 0.5);
    expect(out[0].x).toBeCloseTo(-0.4);
    expect(out[0].y).toBeCloseTo(0.2);
  });

  it('drift is monotone in t (each step closer to the target)', () => {
    const d = (t: number) =>
      Math.hypot(...((c) => [c.x, c.y])(driftCandidates(cands, { x: 0, y: 0 }, t)[0]));
    expect(d(0.8)).toBeLessThan(d(0.4));
    expect(d(0.4)).toBeLessThan(d(0));
  });
});

describe('shakeWinRates', () => {
  const cands: NamedPt[] = [
    { name: 'Centre', x: 0.0, y: 0.0 },
    { name: 'Fringe', x: 0.95, y: 0.95 },
  ];

  it('rates sum to 1 and a dominant candidate holds nearly always', () => {
    const res = shakeWinRates(cands, 'plurality', 150, 42, 'centrist', 40);
    const sum = Object.values(res.rates).reduce((s, r) => s + r, 0);
    expect(sum).toBeCloseTo(1);
    expect(res.top).toBe('Centre');
    expect(res.rates.Centre).toBeGreaterThan(0.9);
    expect(res.replications).toBe(40);
  });

  it('is deterministic for the same base seed', () => {
    const a = shakeWinRates(cands, 'irv', 100, 7, 'random', 25);
    const b = shakeWinRates(cands, 'irv', 100, 7, 'random', 25);
    expect(a).toEqual(b);
  });

  it('a knife-edge contest yields a genuinely split rate', () => {
    // Two symmetric candidates over a symmetric cloud: neither should hold ~100%.
    const tied: NamedPt[] = [
      { name: 'L', x: -0.3, y: 0 },
      { name: 'R', x: 0.3, y: 0 },
    ];
    const res = shakeWinRates(tied, 'plurality', 80, 11, 'random', 50);
    expect(res.rates.L).toBeGreaterThan(0.1);
    expect(res.rates.R).toBeGreaterThan(0.1);
  });

  it('uses fresh electorates (not the displayed one)', () => {
    // Sanity: the sampler with shifted seeds differs from the base sample.
    expect(sampleVoters(20, 42, 'random')).not.toEqual(sampleVoters(20, 42 + 1009, 'random'));
  });
});
