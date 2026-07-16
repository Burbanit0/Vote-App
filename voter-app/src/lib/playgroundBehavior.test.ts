import { describe, it, expect } from 'vitest';
import {
  ballotsAtShare,
  vseAt,
  vseOfWinner,
  vseSweep,
  VSE_RULES,
  VSE_SHARES,
} from './playgroundBehavior';
import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  sampleVoters,
  type NamedPt,
} from './playgroundVoting';
import { LEADER_RULES } from './scorecard';

// A 1-D centre-squeeze field on a bimodal electorate: two blocs, a centrist who is
// the compromise, and the two flanks that split the vote. The classic setting where
// strategy bites plurality hardest.
const SQUEEZE: NamedPt[] = [
  { name: 'Gauche', x: -0.55, y: 0 },
  { name: 'Centre', x: 0, y: 0 },
  { name: 'Droite', x: 0.55, y: 0 },
];
const voters = sampleVoters(400, 11, 'polarized', 1);
const sampler = (seed: number) => sampleVoters(400, seed, 'polarized', 1);

describe('playgroundBehavior — ballots', () => {
  it('share 0 leaves the sincere ballots untouched (the regression guard)', () => {
    const ranks = computeRanks(voters, SQUEEZE);
    const scores = computeScores(voters, SQUEEZE);
    const out = ballotsAtShare(ranks, scores, 3, 0);
    expect(out.ranks).toBe(ranks);
    expect(out.scores).toBe(scores);
  });

  it('at share 0 every rule elects exactly its sincere winner', () => {
    const ranks = computeRanks(voters, SQUEEZE);
    const scores = computeScores(voters, SQUEEZE);
    for (const rule of LEADER_RULES) {
      const sincere = ruleWinnerFromRanks(ranks, 3, rule, scores);
      const b = ballotsAtShare(ranks, scores, 3, 0);
      expect(ruleWinnerFromRanks(b.ranks, 3, rule, b.scores), rule).toBe(sincere);
    }
  });

  it('the strategic share is honoured, and is spread across the electorate', () => {
    const ranks = computeRanks(voters, SQUEEZE);
    const scores = computeScores(voters, SQUEEZE);
    const changed = (share: number) =>
      ballotsAtShare(ranks, scores, 3, share).ranks.reduce(
        (n, r, i) => n + (r === ranks[i] ? 0 : 1),
        0
      );
    // ~share of the electorate votes strategically (low-discrepancy ⇒ tight).
    expect(changed(0.5) / voters.length).toBeGreaterThan(0.45);
    expect(changed(0.5) / voters.length).toBeLessThan(0.55);
    expect(changed(1)).toBe(voters.length);
    // Spread, not a prefix: strategic voters appear in the first AND last decile.
    const strat = ballotsAtShare(ranks, scores, 3, 0.3).ranks.map((r, i) => r !== ranks[i]);
    const n = voters.length;
    expect(strat.slice(0, n / 10).some(Boolean)).toBe(true);
    expect(strat.slice(-n / 10).some(Boolean)).toBe(true);
  });
});

describe('playgroundBehavior — VSE', () => {
  it('is 1 when the winner is the utilitarian best and 0 at the random baseline', () => {
    // meanU = [0.2, 0.8, 0.5] → best 0.8, random 0.5.
    expect(vseOfWinner([0.2, 0.8, 0.5], 1)).toBeCloseTo(1);
    expect(vseOfWinner([0.2, 0.8, 0.5], 2)).toBeCloseTo(0); // exactly the random baseline
    expect(vseOfWinner([0.2, 0.8, 0.5], 0)).toBeLessThan(0); // worse than random
  });

  it('treats an all-equal field as fully efficient', () => {
    expect(vseOfWinner([0.5, 0.5, 0.5], 0)).toBe(1);
  });

  it('reads utility from TRUE preferences even when ballots are strategic', () => {
    // The electorate's truth never changes — only the ballots do. Condorcet elects
    // the centrist compromise from sincere ballots (VSE ≈ 1), and loses them once
    // every voter compresses to a frontrunner: no method can recover a compromise
    // that no ballot mentions. Utility is still measured against what voters
    // actually want, which is exactly why the second number is bad.
    expect(vseAt(voters, SQUEEZE, 'condorcet', 0)).toBeGreaterThan(0.9);
    expect(vseAt(voters, SQUEEZE, 'condorcet', 1)).toBeLessThan(0);
  });

  it('is deterministic for a given sampler + seed', () => {
    const one = vseSweep(sampler, 42, SQUEEZE, { replications: 4 });
    const two = vseSweep(sampler, 42, SQUEEZE, { replications: 4 });
    expect(one).toEqual(two);
  });
});

describe('playgroundBehavior — the sweep', () => {
  const curves = vseSweep(sampler, 42, SQUEEZE, { replications: 8 });
  const byRule = (r: string) => curves.find((c) => c.rule === r)!;

  it('returns one banded curve per rule over the full 0→100% sweep', () => {
    expect(curves.map((c) => c.rule)).toEqual(VSE_RULES);
    for (const c of curves) {
      expect(c.points.map((p) => p.share)).toEqual(VSE_SHARES);
      for (const p of c.points) {
        expect(p.vse.lo).toBeLessThanOrEqual(p.vse.mean);
        expect(p.vse.hi).toBeGreaterThanOrEqual(p.vse.mean);
      }
    }
  });

  it('sincere: the expressive methods find the compromise, the crude ones never do', () => {
    // On a centre squeeze the centrist IS the utilitarian best. Borda/approval/
    // STAR/Condorcet elect them; plurality & friends elect a flank — which is
    // *worse than drawing a candidate at random* (VSE < 0). The crude methods do
    // not "degrade under strategy" here: they start at the floor.
    for (const r of ['borda', 'approval', 'star', 'condorcet']) {
      expect(byRule(r).points[0].vse.mean, r).toBeGreaterThan(0.9);
    }
    for (const r of ['plurality', 'two_round', 'irv']) {
      expect(byRule(r).points[0].vse.mean, r).toBeLessThan(0);
    }
  });

  it('at 100% strategic every method collapses to the same outcome (Duverger)', () => {
    // Full compression means every voter backs one of the two frontrunners, so the
    // field degenerates to a two-horse race and the method stops mattering. This is
    // the headline: strategy destroys precisely what the good methods were buying.
    const finals = curves.map((c) => c.points[c.points.length - 1].vse.mean);
    expect(Math.max(...finals) - Math.min(...finals)).toBeLessThan(0.1);
    for (const v of finals) expect(v).toBeLessThan(0);
  });

  it('only the methods with something to lose degrade', () => {
    for (const r of ['borda', 'approval', 'star', 'condorcet']) {
      expect(byRule(r).degradation, r).toBeGreaterThan(0.5);
    }
    expect(Math.abs(byRule('plurality').degradation)).toBeLessThan(0.1);
  });
});
