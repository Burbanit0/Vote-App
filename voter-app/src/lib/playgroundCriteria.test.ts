import { describe, it, expect } from 'vitest';
import { criteriaMatrix, CRITERIA, type CriterionId } from './playgroundCriteria';
import { LEADER_RULES } from './scorecard';
import type { NamedPt, Pt } from './playgroundVoting';

// 1-D: centrist M is the Condorcet winner but nobody's plurality lead.
const CANDS: NamedPt[] = [
  { name: 'L', x: -0.8, y: 0 },
  { name: 'M', x: 0.0, y: 0 },
  { name: 'R', x: 0.8, y: 0 },
];
const VOTERS: Pt[] = [
  ...Array.from({ length: 40 }, () => ({ x: -0.7, y: 0 })),
  ...Array.from({ length: 25 }, () => ({ x: 0.0, y: 0 })),
  ...Array.from({ length: 40 }, () => ({ x: 0.7, y: 0 })),
];

const byRule = () => Object.fromEntries(criteriaMatrix(VOTERS, CANDS).map((r) => [r.rule, r]));

describe('criteriaMatrix', () => {
  it('returns one row per leader rule, each with every criterion key', () => {
    const rows = criteriaMatrix(VOTERS, CANDS);
    expect(rows).toHaveLength(LEADER_RULES.length);
    const ids = CRITERIA.map((c) => c.id);
    for (const row of rows) {
      for (const id of ids) expect(id in row.results).toBe(true);
    }
  });

  it('is deterministic', () => {
    expect(criteriaMatrix(VOTERS, CANDS)).toEqual(criteriaMatrix(VOTERS, CANDS));
  });

  it('Condorcet methods honour the Condorcet criterion here; plurality does not', () => {
    const r = byRule();
    expect(r.schulze.results.condorcet).toBe(true);
    expect(r.condorcet.results.condorcet).toBe(true);
    expect(r.ranked_pairs.results.condorcet).toBe(true);
    expect(r.plurality.results.condorcet).toBe(false);
    // M (centrist) is the Condorcet winner; plurality elects a flank.
    expect(r.schulze.winner).toBe('M');
    expect(r.plurality.winner).not.toBe('M');
  });

  it('random ballot carries its known ex-post properties (not a plurality clone)', () => {
    const rb = byRule().random_ballot.results;
    expect(rb.condorcet).toBe(false);
    expect(rb.monotonic).toBe(true);
    expect(rb.pareto).toBe(true);
    expect(rb.reversal).toBeNull(); // reversal not meaningful for a lottery
  });

  it('marks criteria not triggered on this electorate as null', () => {
    // No candidate is a first-choice majority here → majority criterion untested.
    const r = byRule();
    expect(r.plurality.results.majority).toBeNull();
  });

  it('a first-choice majority is respected by plurality (majority criterion)', () => {
    const cands: NamedPt[] = [
      { name: 'A', x: -0.6, y: 0 },
      { name: 'B', x: 0.2, y: 0 },
      { name: 'C', x: 0.8, y: 0 },
    ];
    const voters: Pt[] = [
      ...Array.from({ length: 60 }, () => ({ x: -0.6, y: 0 })), // A is a 60% favourite
      ...Array.from({ length: 25 }, () => ({ x: 0.25, y: 0 })),
      ...Array.from({ length: 15 }, () => ({ x: 0.8, y: 0 })),
    ];
    const r = Object.fromEntries(criteriaMatrix(voters, cands).map((x) => [x.rule, x]));
    expect(r.plurality.results.majority).toBe(true);
    expect(r.plurality.winner).toBe('A');
  });

  it('handles an empty electorate without throwing', () => {
    const rows = criteriaMatrix([], CANDS);
    expect(rows).toHaveLength(LEADER_RULES.length);
    expect(rows.every((row) => row.winner === null)).toBe(true);
  });
});

describe('CRITERIA metadata', () => {
  it('every criterion is bilingual with a short header', () => {
    for (const c of CRITERIA) {
      expect(c.short).toBeTruthy();
      expect(c.fr.label && c.fr.desc).toBeTruthy();
      expect(c.en.label && c.en.desc).toBeTruthy();
    }
  });

  it('all matrix result keys are covered by CRITERIA metadata', () => {
    const metaIds = new Set<CriterionId>(CRITERIA.map((c) => c.id));
    const resultIds = Object.keys(criteriaMatrix(VOTERS, CANDS)[0].results) as CriterionId[];
    for (const id of resultIds) expect(metaIds.has(id)).toBe(true);
  });
});
