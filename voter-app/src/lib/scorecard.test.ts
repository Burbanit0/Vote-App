import { describe, it, expect } from 'vitest';
import {
  leaderScorecard,
  paretoSplit,
  spotlight,
  dominates,
  compressRanks,
  condorcetFromRanks,
  consensusIndex,
  dialWeights,
  lijphartTo01,
  LIJPHART_REFERENCE,
  LEADER_AXES_KEYS,
  LEADER_RULES,
  type LensItem,
  type AxisScores,
} from './scorecard';
import type { NamedPt } from './playgroundVoting';

const CANDS: NamedPt[] = [
  { name: 'L', x: -0.6, y: 0 },
  { name: 'M', x: 0.0, y: 0.05 },
  { name: 'R', x: 0.6, y: 0 },
];

describe('condorcetFromRanks / compressRanks', () => {
  it('finds the Condorcet winner and detects cycles', () => {
    // 3 voters, cycle: 0>1>2, 1>2>0, 2>0>1
    expect(condorcetFromRanks([[0, 1, 2], [1, 2, 0], [2, 0, 1]], 3)).toBe(-1);
    // Clear winner 1 (majority puts it above both others)
    expect(condorcetFromRanks([[1, 0, 2], [1, 2, 0], [0, 1, 2]], 3)).toBe(1);
  });

  it('compression pushes the preferred frontrunner first and the other last', () => {
    // Frontrunners by firsts: 0 and 2 (one first each + tie-break by order).
    const { ranks } = compressRanks([[0, 1, 2], [2, 1, 0], [0, 2, 1]], 3);
    for (const r of ranks) {
      expect([0, 2]).toContain(r[0]);
      expect([0, 2]).toContain(r[r.length - 1]);
    }
  });
});

describe('leaderScorecard', () => {
  const sc = leaderScorecard(CANDS, 120, 42, 'random', 16);

  it('covers every rule and every axis with bands in [0,1], lo ≤ mean ≤ hi', () => {
    for (const rule of LEADER_RULES) {
      for (const key of LEADER_AXES_KEYS) {
        const b = sc[rule][key];
        expect(b.lo).toBeLessThanOrEqual(b.mean + 1e-9);
        expect(b.mean).toBeLessThanOrEqual(b.hi + 1e-9);
        expect(b.lo).toBeGreaterThanOrEqual(0);
        expect(b.hi).toBeLessThanOrEqual(1);
      }
    }
  });

  it('the Condorcet rule has perfect Condorcet efficiency', () => {
    expect(sc.condorcet.condorcet_efficiency.mean).toBe(1);
  });

  it('is deterministic for the same seed', () => {
    expect(leaderScorecard(CANDS, 120, 42, 'random', 16)).toEqual(sc);
  });

  it('simplicity is a zero-width stated convention', () => {
    expect(sc.plurality.simplicity).toEqual({ mean: 1, lo: 1, hi: 1 });
  });
});

describe('values lens (Pareto + spotlight)', () => {
  const mk = (id: string, a: number, b: number): LensItem => ({
    id,
    axes: {
      ax1: { mean: a, lo: a, hi: a },
      ax2: { mean: b, lo: b, hi: b },
    },
  });
  const keys = ['ax1', 'ax2'];

  it('eliminates strictly dominated items, keeps the trade-off frontier', () => {
    const items = [mk('good-a', 0.9, 0.2), mk('good-b', 0.2, 0.9), mk('bad', 0.1, 0.1)];
    const { frontier, dominated } = paretoSplit(items, keys);
    expect(frontier.map((i) => i.id).sort()).toEqual(['good-a', 'good-b']);
    expect(dominated.map((i) => i.id)).toEqual(['bad']);
  });

  it('equal items are NOT dominated (no strict improvement)', () => {
    const items = [mk('x', 0.5, 0.5), mk('y', 0.5, 0.5)];
    expect(paretoSplit(items, keys).dominated).toHaveLength(0);
    expect(dominates(items[0].axes, items[1].axes, keys)).toBe(false);
  });

  it('weights move the spotlight along the frontier — never a ranking', () => {
    const items = [mk('good-a', 0.9, 0.2), mk('good-b', 0.2, 0.9)];
    const { frontier } = paretoSplit(items, keys);
    expect(spotlight(frontier, { ax1: 1, ax2: 0 }, keys)).toBe('good-a');
    expect(spotlight(frontier, { ax1: 0, ax2: 1 }, keys)).toBe('good-b');
  });

  it('the spotlight never lands on a dominated item', () => {
    const items = [mk('good-a', 0.9, 0.2), mk('good-b', 0.2, 0.9), mk('bad', 0.1, 0.1)];
    const { frontier } = paretoSplit(items, keys);
    // Even with weights that would favour bad's profile, it was eliminated first.
    expect(spotlight(frontier, { ax1: 0.1, ax2: 0.1 }, keys)).not.toBe('bad');
  });
});

// ── Lijphart lens (FA-2) ──────────────────────────────────────────────────────

const axScores = (p: number, pl: number, mr: number, g: number): AxisScores => ({
  proportionality: { mean: p, lo: p - 0.05, hi: p + 0.05 },
  pluralism: { mean: pl, lo: pl - 0.05, hi: pl + 0.05 },
  minority_representation: { mean: mr, lo: mr - 0.05, hi: mr + 0.05 },
  governability: { mean: g, lo: g - 0.05, hi: g + 0.05 },
});

describe('consensusIndex (FA-2)', () => {
  // Typical scorecard shapes: PR proportional/plural but coalition-bound;
  // FPTP disproportional but governable.
  const pr = consensusIndex(axScores(0.9, 0.9, 1.0, 0.4));
  const fptp = consensusIndex(axScores(0.45, 0.5, 0.5, 0.9));

  it('a PR-shaped scorecard lands consensus-side, FPTP majoritarian-side', () => {
    expect(pr.mean).toBeGreaterThan(fptp.mean);
    // Acceptance: nearest reference neighbours are on the right sides.
    const nl = lijphartTo01(1.2); // Pays-Bas (consensus)
    const uk = lijphartTo01(-1.2); // Royaume-Uni (majoritarian)
    expect(Math.abs(pr.mean - nl)).toBeLessThan(Math.abs(pr.mean - uk));
    expect(Math.abs(fptp.mean - uk)).toBeLessThan(Math.abs(fptp.mean - nl));
  });

  it('bands propagate (lo ≤ mean ≤ hi)', () => {
    for (const b of [pr, fptp]) {
      expect(b.lo).toBeLessThanOrEqual(b.mean);
      expect(b.mean).toBeLessThanOrEqual(b.hi);
    }
  });

  it('reference data is on the stated scale and includes both poles', () => {
    expect(LIJPHART_REFERENCE.some((c) => c.score < -1)).toBe(true);
    expect(LIJPHART_REFERENCE.some((c) => c.score > 1)).toBe(true);
    for (const c of LIJPHART_REFERENCE) {
      const x = lijphartTo01(c.score);
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(1);
    }
  });
});

describe('dialWeights (FA-2)', () => {
  it('the consensualist end weighs proportionality, the majoritarian end governability', () => {
    const consensual = dialWeights(1, 'parliament');
    const majoritarian = dialWeights(0, 'parliament');
    expect(consensual.proportionality).toBe(1);
    expect(consensual.governability).toBe(0);
    expect(majoritarian.proportionality).toBe(0);
    expect(majoritarian.governability).toBe(1);
  });

  it('leader-mode mapping trades consensus quality against simplicity/stability', () => {
    const consensual = dialWeights(1, 'leader');
    expect(consensual.condorcet_efficiency).toBe(1);
    expect(consensual.simplicity).toBe(0);
    const majoritarian = dialWeights(0, 'leader');
    expect(majoritarian.simplicity).toBe(1);
    expect(majoritarian.condorcet_efficiency).toBe(0);
  });
});
