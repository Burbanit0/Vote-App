import { describe, expect, it } from 'vitest';
import { CANDIDATES, RULES, RUNOFF_CHOICE, TALLY, VOTERS, lcg } from './scenario';

describe('the homepage electorate', () => {
  it('has 100 voters, each approving at least their first choice', () => {
    expect(VOTERS).toHaveLength(100);
    VOTERS.forEach((v) => expect(v.approves).toContain(v.first));
  });

  it('elects a different candidate under each rule — the thesis', () => {
    const winners = RULES.map((r) => CANDIDATES[TALLY[r].winner].name);
    expect(winners).toEqual(['Bob', 'Alice', 'Carol']);
  });

  it('wins each rule outright, never on a tie', () => {
    RULES.forEach((r) => {
      const sorted = [...TALLY[r].counts].sort((a, b) => b - a);
      expect(sorted[0]).toBeGreaterThan(sorted[1]);
    });
  });

  it('counts every voter once in plurality and in the runoff', () => {
    const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
    expect(sum(TALLY.plurality.counts)).toBe(100);
    expect(sum(TALLY.runoff.counts)).toBe(100);
    expect(TALLY.runoff.counts[TALLY.runoff.out!]).toBe(0);
  });

  it('moves only the eliminated candidate’s voters in the runoff', () => {
    VOTERS.forEach((v, i) => {
      if (v.first === TALLY.runoff.out) expect(RUNOFF_CHOICE[i]).not.toBe(v.first);
      else expect(RUNOFF_CHOICE[i]).toBe(v.first);
    });
  });

  it('draws the same sequence from the same seed', () => {
    const a = lcg(3);
    const b = lcg(3);
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
  });
});
