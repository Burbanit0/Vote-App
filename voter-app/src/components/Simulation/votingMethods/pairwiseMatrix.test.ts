import { describe, it, expect } from 'vitest';
import { pairwiseCounts } from './pairwiseMatrix';

describe('pairwiseCounts', () => {
  it('counts ballots ranking a before b, both directions independently', () => {
    // 3 ballots: A>B>C, A>B>C, C>A>B — A beats B on all 3, B beats C on 2/3.
    const rankings = [
      { voter_id: 1, ranking: ['A', 'B', 'C'] },
      { voter_id: 2, ranking: ['A', 'B', 'C'] },
      { voter_id: 3, ranking: ['C', 'A', 'B'] },
    ];
    const counts = pairwiseCounts(rankings, ['A', 'B', 'C']);

    expect(counts.A.B).toBe(3);
    expect(counts.B.A).toBe(0);
    expect(counts.B.C).toBe(2);
    expect(counts.C.B).toBe(1);
    expect(counts.A.C).toBe(2);
    expect(counts.C.A).toBe(1);
  });

  it('is antisymmetric: counts[a][b] + counts[b][a] == total ballots (no ties)', () => {
    const rankings = [
      { voter_id: 1, ranking: ['B', 'A'] },
      { voter_id: 2, ranking: ['A', 'B'] },
      { voter_id: 3, ranking: ['A', 'B'] },
    ];
    const counts = pairwiseCounts(rankings, ['A', 'B']);
    expect(counts.A.B + counts.B.A).toBe(rankings.length);
  });

  it('the diagonal is left undefined, not zero', () => {
    const counts = pairwiseCounts([{ voter_id: 1, ranking: ['A', 'B'] }], ['A', 'B']);
    expect(counts.A.A).toBeUndefined();
  });

  it('returns an empty matrix for no candidates', () => {
    expect(pairwiseCounts([], [])).toEqual({});
  });
});
