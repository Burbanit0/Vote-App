import { describe, it, expect } from 'vitest';
import { explainWinner, condorcetOf, headToHead } from './explainWinner';
import type { NamedPt } from './playgroundVoting';
import { buildTraceFromBallots, FAMILY_OF, type VoteTrace, type TraceFamily } from './voteTrace';
import { computeRanks, computeScores, sampleVoters } from './playgroundVoting';
import { LEADER_RULES, hasFixedWinner } from './scorecard';
import { DEFAULT_CONFIG } from '../stores/useElectionStore';
import i18n from '../i18n';
import type { Rule } from './playgroundVoting';

const CANDS: NamedPt[] = [
  { name: 'Alice', x: 0, y: 0 },
  { name: 'Bruno', x: 1, y: 0 },
  { name: 'Carla', x: 0, y: 1 },
];

// Minimal trace: explainWinner reads only family, winner, and the final frame.
const trace = (
  family: TraceFamily,
  winner: number,
  bars: number[],
  rule: Rule = 'plurality'
): VoteTrace => ({
  family,
  rule,
  frames: [{ caption: { key: 'x' }, bars }],
  winner,
  unitKey: 'votes',
  sampleSize: bars.reduce((s, n) => s + n, 0),
});

describe('explainWinner — names the mechanism, never re-derives the winner', () => {
  it('count: highest total, with the runner-up and both scores', () => {
    const e = explainWinner(trace('count', 0, [16, 15, 3]), CANDS);
    expect(e.key).toBe('explain.count');
    expect(e.params).toMatchObject({
      winner: 'Alice',
      runnerUp: 'Bruno',
      winnerVal: 16,
      runnerUpVal: 15,
    });
  });

  it('irv: the last count, whether or not transfers were needed', () => {
    // Bruno (idx 1) leads the last count; Carla (idx 2) is the other finalist.
    const e = explainWinner(trace('elim', 1, [0, 22, 20], 'irv'), CANDS);
    expect(e.key).toBe('explain.irv');
    expect(e.params).toMatchObject({ winner: 'Bruno', runnerUp: 'Carla', winnerVal: 22 });
  });

  it('a rule whose family sentence would be false gets its own, without figures', () => {
    // Nanson's last frame has only the winner alive: "22 to 0" would mean nothing.
    const e = explainWinner(trace('elim', 1, [0, 22, 0], 'nanson'), CANDS);
    expect(e).toEqual({ key: 'explain.rule.nanson', params: { winner: 'Bruno' } });
    expect(explainWinner(trace('twophase', 0, [4, 3, 2], 'majority_judgment'), CANDS).key).toBe(
      'explain.rule.majority_judgment'
    );
  });

  it('maximin speaks in percentages of satisfaction, not totals', () => {
    const e = explainWinner(trace('count', 2, [0.31, 0.12, 0.47], 'maximin'), CANDS);
    expect(e.key).toBe('explain.maximin');
    expect(e.params).toMatchObject({
      winner: 'Carla',
      winnerPct: 47,
      runnerUp: 'Alice',
      runnerUpPct: 31,
    });
  });

  it('an elim trace for a rule without its own sentence says only that the rule elects', () => {
    const e = explainWinner(trace('elim', 1, [0, 22, 20]), CANDS);
    expect(e).toEqual({ key: 'explain.byRule', params: { winner: 'Bruno' } });
  });

  it('a lone candidate has no runner-up: figures for the winner, 0 for nobody', () => {
    const e = explainWinner(trace('count', 0, [0.4], 'maximin'), [CANDS[0]]);
    expect(e).toMatchObject({ key: 'explain.maximin', params: { winnerPct: 40, runnerUpPct: 0 } });
  });

  it('a tie the engine broke is not presented as a lead', () => {
    // Two-round, 50-50 in the runoff: the engine picks Alice, but "50 to 50" is no lead.
    const e = explainWinner(trace('elim', 0, [50, 50, 0], 'two_round'), CANDS);
    expect(e).toEqual({ key: 'explain.byRule', params: { winner: 'Alice' } });
  });

  it('a lead lost to rounding is not shown as figures', () => {
    // Nash: 47.4% against 47.2% would both print as 47%.
    const e = explainWinner(trace('count', 0, [0.474, 0.472, 0.1], 'nash'), CANDS);
    expect(e.key).toBe('explain.byRule');
  });

  it('drops the figures when the bars do not put the winner ahead', () => {
    const e = explainWinner(trace('count', 1, [16, 15, 3]), CANDS);
    expect(e).toEqual({ key: 'explain.byRule', params: { winner: 'Bruno' } });
  });

  it('pairwise: the duel winner (no runner-up score needed)', () => {
    const e = explainWinner(trace('pairwise', 2, [1, 1, 2]), CANDS);
    expect(e.key).toBe('explain.pairwise');
    expect(e.params).toEqual({ winner: 'Carla' });
  });

  it('pairwise in a cycle: nobody wins every duel, so the sentence does not say so', () => {
    // A three-way cycle: each candidate wins one of their two duels.
    const e = explainWinner(trace('pairwise', 0, [1, 1, 1]), CANDS);
    expect(e.key).toBe('explain.pairwiseCycle');
    expect(e.params).toEqual({ winner: 'Alice', wins: 1, duels: 2 });
  });

  it('twophase: the runoff winner over the other finalist', () => {
    const e = explainWinner(trace('twophase', 0, [55, 45, 0]), CANDS);
    expect(e.key).toBe('explain.twophase');
    expect(e.params).toMatchObject({ winner: 'Alice', runnerUp: 'Bruno', winnerVal: 55 });
  });

  it('lottery: drawn, proportional to support', () => {
    const e = explainWinner(trace('lottery', 1, [10, 30, 5]), CANDS);
    expect(e.key).toBe('explain.lottery');
    expect(e.params).toEqual({ winner: 'Bruno' });
  });

  it('rounds fractional bars (real-election transfers)', () => {
    const e = explainWinner(trace('count', 0, [16.4, 14.6, 3]), CANDS);
    expect(e.params).toMatchObject({ winnerVal: 16, runnerUpVal: 15 });
  });

  it('always names the trace’s authoritative winner, not an argmax of the bars', () => {
    // Winner is idx 1 even though idx 0 has the biggest final bar — explainWinner
    // must trust trace.winner (the engine), not recompute from bars.
    const e = explainWinner(trace('pairwise', 1, [99, 1, 1]), CANDS);
    expect(e.params.winner).toBe('Bruno');
  });
});

describe('explainWinner on real traces: every method gets a complete sentence', () => {
  // The default playground electorate, and a three-way cycle (no Condorcet winner).
  const spatial = sampleVoters(300, 42, 'random', 2);
  const ranks = computeRanks(spatial, DEFAULT_CONFIG.candidates);
  const scores = computeScores(spatial, DEFAULT_CONFIG.candidates);
  const cycle = [
    ...Array.from({ length: 40 }, () => [0, 1, 2]),
    ...Array.from({ length: 35 }, () => [1, 2, 0]),
    ...Array.from({ length: 25 }, () => [2, 0, 1]),
  ];
  const cycleScores = cycle.map((r) => r.map((c) => 1 - r.indexOf(c) / 2));

  for (const rule of LEADER_RULES.filter(hasFixedWinner)) {
    it(`${rule}: an existing string, every placeholder filled`, () => {
      for (const [r, s] of [
        [ranks, scores],
        [cycle, cycleScores],
      ] as const) {
        const tr = buildTraceFromBallots(
          DEFAULT_CONFIG.candidates,
          r as number[][],
          s as number[][],
          rule
        );
        if (tr.winner < 0) continue;
        const { key, params } = explainWinner(tr, DEFAULT_CONFIG.candidates);
        expect(i18n.exists(key, { ns: 'playground' }), key).toBe(true);
        const text = i18n.t(key, { ns: 'playground', ...params });
        expect(text).not.toMatch(/\{\{|NaN|undefined/);
        expect(text).toContain(DEFAULT_CONFIG.candidates[tr.winner].name);
      }
    });
  }

  it('a tied duel is a win for neither, so a winner who only tied one does not "win every duel"', () => {
    // Alice and Bruno tie head to head (50-50); both beat Carla.
    const tied = [
      ...Array.from({ length: 50 }, () => [0, 1, 2]),
      ...Array.from({ length: 50 }, () => [1, 0, 2]),
    ];
    const tr = buildTraceFromBallots(
      DEFAULT_CONFIG.candidates,
      tied,
      tied.map(() => [1, 1, 0]),
      'condorcet'
    );
    expect(tr.winner).toBeGreaterThanOrEqual(0);
    const e = explainWinner(tr, DEFAULT_CONFIG.candidates);
    expect(e.key).toBe('explain.pairwiseCycle');
    expect(e.params).toMatchObject({ wins: 1, duels: 2 });
  });

  it('in the cycle, no pairwise method claims its winner won every duel', () => {
    for (const rule of LEADER_RULES.filter((r) => FAMILY_OF[r] === 'pairwise')) {
      const tr = buildTraceFromBallots(DEFAULT_CONFIG.candidates, cycle, cycleScores, rule);
      if (tr.winner < 0) continue;
      expect(explainWinner(tr, DEFAULT_CONFIG.candidates).key, rule).toBe('explain.pairwiseCycle');
    }
  });
});

describe('condorcetOf and headToHead', () => {
  const ballots = (counts: [number[], number][]) =>
    counts.flatMap(([r, n]) => Array.from({ length: n }, () => r));

  it('condorcetOf names who beats every rival, or nobody in a cycle', () => {
    expect(
      condorcetOf(
        ballots([
          [[2, 0, 1], 6],
          [[0, 2, 1], 4],
        ]),
        CANDS
      )
    ).toEqual({ idx: 2, name: 'Carla' });
    const cycle = ballots([
      [[0, 1, 2], 4],
      [[1, 2, 0], 3],
      [[2, 0, 1], 2],
    ]);
    expect(condorcetOf(cycle, CANDS)).toEqual({ idx: -1, name: null });
  });

  it('headToHead puts the duel winner first and says which side lost', () => {
    const r = ballots([
      [[0, 1, 2], 6],
      [[1, 0, 2], 4],
    ]); // Alice beats Bruno 6-4
    expect(headToHead(r, 3, 0, 1)).toEqual({ x: 0, y: 1, xv: 6, yv: 4, loserIsA: false });
    expect(headToHead(r, 3, 1, 0)).toEqual({ x: 0, y: 1, xv: 6, yv: 4, loserIsA: true });
    expect(
      headToHead(
        ballots([
          [[0, 1, 2], 5],
          [[1, 0, 2], 5],
        ]),
        3,
        0,
        1
      )
    ).toBeNull();
  });
});
