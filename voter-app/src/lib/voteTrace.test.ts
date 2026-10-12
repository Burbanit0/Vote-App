import { describe, it, expect } from 'vitest';
import { buildTrace, buildTraceFromBallots, sampleVoters, FAMILY_OF } from './voteTrace';
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

/** Caption key + named candidate of every frame, in order. */
const beats = (trace: ReturnType<typeof buildTraceFromBallots>) =>
  trace.frames.map((f) => [f.caption.key, f.caption.params?.cand]);

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

  it('smith_irv shows the Smith-set restriction when a Condorcet winner exists', () => {
    // A beats B (3–1) and C (3–1): the Smith set is {A}, smaller than the field,
    // so the replay opens with the restriction beat before any IRV round.
    const abc = cands.slice(0, 3);
    const ranks = [
      [0, 1, 2],
      [0, 2, 1],
      [1, 0, 2],
      [2, 0, 1],
    ];
    const trace = buildTraceFromBallots(abc, ranks, [], 'smith_irv');
    expect(beats(trace)).toEqual([
      ['replay.smith.set', 'A'],
      ['replay.elim.done', 'A'],
    ]);
    expect(trace.frames[0].bars).toEqual([2, 1, 1]);
    expect(trace.winner).toBe(0);
  });

  it('smith_irv runs IRV rounds inside a Condorcet cycle', () => {
    // A>B 3–2, B>C 4–1, C>A 3–2: no Condorcet winner, the Smith set is the whole
    // field. First preferences 2/2/1 eliminate C, then A beats B 3–2.
    const abc = cands.slice(0, 3);
    const ranks = [
      [0, 1, 2],
      [0, 1, 2],
      [1, 2, 0],
      [1, 2, 0],
      [2, 0, 1],
    ];
    const trace = buildTraceFromBallots(abc, ranks, [], 'smith_irv');
    expect(beats(trace)).toEqual([
      ['replay.smith.irv', 'C'],
      ['replay.smith.irv', 'B'],
      ['replay.elim.done', 'A'],
    ]);
    expect(trace.frames[0].bars).toEqual([2, 2, 1]);
    expect(trace.winner).toBe(0);
  });
});

describe('traces agree with the engine on a tie (tie lot, #667)', () => {
  const pair = [
    { name: 'Ann', x: -0.5, y: 0 },
    { name: 'Ben', x: 0.5, y: 0 },
  ];

  it('the last caption names the drawn winner, not the first-listed one', () => {
    // Ann and Ben tie on score; the lot draws Ben (tieLot.test.ts), the tally's argmax Ann.
    const tr = buildTraceFromBallots(
      pair,
      [
        [0, 1],
        [1, 0],
      ],
      [
        [1, 0],
        [0, 1],
      ],
      'score'
    );
    expect(tr.winner).toBe(1);
    const last = tr.frames[tr.frames.length - 1];
    expect(last.highlight).toEqual([1]);
    expect(last.caption.params?.cand).toBe('Ben');
  });

  it('STAR picks its finalists as the engine does', () => {
    const three = [
      { name: 'Alice', x: -0.5, y: 0 },
      { name: 'Bob', x: 0.5, y: 0 },
      { name: 'Carol', x: 0, y: 0.5 },
    ];
    // Each candidate tops one voter, so all three tie on score and the lot picks the
    // finalists: Carol, then Alice (tie_lot's pinned draws). Carol takes the runoff 2-1.
    // Listing order would have sent Alice and Bob through and eliminated Carol.
    const scores = [
      [1, 0.5, 0],
      [0, 1, 0.5],
      [0.5, 0, 1],
    ];
    const ranks = scores.map((s) => [0, 1, 2].sort((a, b) => s[b] - s[a]));
    const tr = buildTraceFromBallots(three, ranks, scores, 'star');
    expect(tr.winner).toBe(2);
    const last = tr.frames[tr.frames.length - 1];
    expect(last.caption.params?.cand).toBe('Carol');
    expect(last.eliminated?.[2]).toBe(false);
  });
});
