import { describe, it, expect } from 'vitest';
import { buildTrace, sampleVoters, FAMILY_OF } from './voteTrace';
import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  CARDINAL_RULES,
  RULE_LABELS,
  type Rule,
  type Pt,
  type NamedPt,
} from './playgroundVoting';

// A deterministic spatial electorate: 60 voters on a jittered grid, 4 candidates.
const cands: NamedPt[] = [
  { name: 'A', x: -0.6, y: -0.2 },
  { name: 'B', x: -0.1, y: 0.1 },
  { name: 'C', x: 0.4, y: -0.1 },
  { name: 'D', x: 0.7, y: 0.5 },
];
const voters: Pt[] = Array.from({ length: 60 }, (_, i) => ({
  x: Math.cos(i * 2.4) * 0.8,
  y: Math.sin(i * 1.7) * 0.8,
}));

const RULES = Object.keys(RULE_LABELS) as Rule[];

describe('voteTrace', () => {
  it('covers all 17 rules with a family', () => {
    for (const r of RULES) expect(FAMILY_OF[r]).toBeTruthy();
  });

  it('sampleVoters is deterministic per seed and caps size', () => {
    const a = sampleVoters(voters, 21, 7);
    const b = sampleVoters(voters, 21, 7);
    const c = sampleVoters(voters, 21, 8);
    expect(a).toEqual(b);
    expect(a).not.toEqual(c);
    expect(a.length).toBe(21);
    expect(sampleVoters(voters.slice(0, 5), 21, 1).length).toBe(5);
  });

  // The core invariant: a trace can never disagree with the engine on the winner.
  it.each(RULES)('trace winner matches the engine for %s', (rule) => {
    const sample = sampleVoters(voters, 21, 42);
    const trace = buildTrace(sample, cands, rule);
    const ranks = computeRanks(sample, cands);
    const scores = CARDINAL_RULES.has(rule) ? computeScores(sample, cands) : undefined;
    const engine = ruleWinnerFromRanks(ranks, cands.length, rule, scores);

    expect(trace.winner).toBe(engine);
    expect(trace.frames.length).toBeGreaterThan(0);
    // Final frame emphasises the winner (unless the engine reports an exact tie).
    if (engine >= 0) expect(trace.frames[trace.frames.length - 1].highlight).toContain(engine);
  });

  it('count-family final bars peak on the winner', () => {
    const sample = sampleVoters(voters, 21, 3);
    for (const rule of RULES.filter((r) => FAMILY_OF[r] === 'count')) {
      const trace = buildTrace(sample, cands, rule);
      const last = trace.frames[trace.frames.length - 1].bars;
      const peak = last.indexOf(Math.max(...last));
      expect(peak).toBe(trace.winner);
    }
  });
});
