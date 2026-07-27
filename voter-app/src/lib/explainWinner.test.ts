import { describe, it, expect } from 'vitest';
import { explainWinner } from './explainWinner';
import type { NamedPt } from './playgroundVoting';
import type { VoteTrace, TraceFamily } from './voteTrace';
import type { Rule } from './playgroundVoting';

const CANDS: NamedPt[] = [
  { name: 'Alice', x: 0, y: 0 },
  { name: 'Bruno', x: 1, y: 0 },
  { name: 'Carla', x: 0, y: 1 },
];

// Minimal trace: explainWinner reads only family, winner, and the final frame.
const trace = (family: TraceFamily, winner: number, bars: number[]): VoteTrace => ({
  family,
  rule: 'plurality' as Rule,
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

  it('elim: the transfer survivor beats the other finalist', () => {
    // Bruno (idx 1) wins after transfers; Carla (idx 2) is the other finalist.
    const e = explainWinner(trace('elim', 1, [0, 22, 20]), CANDS);
    expect(e.key).toBe('explain.elim');
    expect(e.params).toMatchObject({ winner: 'Bruno', runnerUp: 'Carla', winnerVal: 22 });
  });

  it('pairwise: the duel winner (no runner-up score needed)', () => {
    const e = explainWinner(trace('pairwise', 2, [1, 1, 2]), CANDS);
    expect(e.key).toBe('explain.pairwise');
    expect(e.params).toEqual({ winner: 'Carla' });
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
