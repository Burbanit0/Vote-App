import { describe, it, expect } from 'vitest';
import {
  leaderScorecard,
  paretoSplit,
  spotlight,
  dominates,
  compressRanks,
  condorcetFromRanks,
  LEADER_AXES_KEYS,
  LEADER_RULES,
  type LensItem,
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
