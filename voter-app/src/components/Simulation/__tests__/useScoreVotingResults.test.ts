import { renderHook } from '@testing-library/react';
import { useScoreVotingResults } from '../useScoreVotingResults';
import { ScoreVote } from '../../../types';

const candidates = ['Alice', 'Bob', 'Charlie'];

const basicScores: ScoreVote[] = [
  { voter_id: 1, scores: { Alice: 5, Bob: 3, Charlie: 1 } },
  { voter_id: 2, scores: { Alice: 4, Bob: 4, Charlie: 2 } },
  { voter_id: 3, scores: { Alice: 3, Bob: 5, Charlie: 4 } },
];

const tieScores: ScoreVote[] = [
  { voter_id: 1, scores: { Alice: 5, Bob: 5, Charlie: 1 } },
  { voter_id: 2, scores: { Alice: 5, Bob: 5, Charlie: 2 } },
];

const emptyScores: ScoreVote[] = [];

describe('useScoreVotingResults', () => {
  it('computes simple score voting', () => {
    const { result } = renderHook(() => useScoreVotingResults(basicScores, candidates));
    const simple = result.current.simple_score;
    expect(simple.method).toBe('Simple Score');
    expect(simple.winner).toBe('Alice');
    expect(simple.details).toEqual({ Alice: 4, Bob: 4, Charlie: 7 / 3 });
  });

  it('computes STAR voting', () => {
    const { result } = renderHook(() => useScoreVotingResults(basicScores, candidates));
    const star = result.current.star_voting;
    expect(star.method).toBe('STAR Voting');
    expect(star.details.first_round).toEqual({ Alice: 4, Bob: 4, Charlie: 7 / 3 });
    expect(star.details.runoff).toBeTruthy();
    expect(star.details.runoff.candidate1).toBe('Alice');
    expect(star.details.runoff.candidate2).toBe('Bob');
  });

  it('computes median voting', () => {
    const { result } = renderHook(() => useScoreVotingResults(basicScores, candidates));
    const median = result.current.median_voting;
    expect(median.method).toBe('Median Voting');
    expect(median.winner).toBe('Alice');
  });

  it('computes mean-median hybrid', () => {
    const { result } = renderHook(() => useScoreVotingResults(basicScores, candidates));
    const hybrid = result.current.mean_median_hybrid;
    expect(hybrid.method).toBe('Mean-Median Hybrid');
    expect(hybrid.details[0].candidate).toBe('Alice');
    expect(hybrid.details[0].mean).toBe(4);
    expect(hybrid.details[0].median).toBe(4);
  });

  it('computes variance-based', () => {
    const { result } = renderHook(() => useScoreVotingResults(basicScores, candidates));
    const variance = result.current.variance_based;
    expect(variance.method).toBe('Variance-Based');
    expect(variance.details[0].candidate).toBe('Alice');
    expect(variance.details[0].variance).toBeGreaterThanOrEqual(0);
  });

  it('computes score distribution analysis', () => {
    const { result } = renderHook(() => useScoreVotingResults(basicScores, candidates));
    const dist = result.current.score_distribution;
    expect(dist.method).toBe('Score Distribution Analysis');
    expect(dist.details[0].candidate).toBe('Alice');
    expect(dist.details[0].total).toBe(2);
    expect(dist.details[0].distribution.length).toBe(10);
  });

  it('computes bayesian regret', () => {
    const { result } = renderHook(() => useScoreVotingResults(basicScores, candidates));
    const regret = result.current.bayesian_regret;
    expect(regret.method).toBe('Bayesian Regret');
    expect(regret.winner).toBe('Alice');
    expect(regret.details[0].candidate).toBe('Alice');
  });

  it('handles tied candidates in STAR runoff', () => {
    const { result } = renderHook(() => useScoreVotingResults(tieScores, candidates));
    const star = result.current.star_voting;
    expect(star.details.runoff.tied).toBe(2);
  });

  it('handles empty scores', () => {
    const { result } = renderHook(() => useScoreVotingResults(emptyScores, candidates));
    expect(result.current.simple_score.winner).toBe('Alice');
    expect(result.current.median_voting.winner).toBe('Alice');
  });

  it('handles single candidate', () => {
    const { result } = renderHook(() => useScoreVotingResults(basicScores, ['Alice']));
    expect(result.current.simple_score.winner).toBe('Alice');
    expect(result.current.star_voting.winner).toBe('Alice');
  });
});
