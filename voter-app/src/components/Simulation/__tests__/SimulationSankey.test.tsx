import preprocessRankingsForSankey from '../SimulationSankey';

const rankings = [
  { voter_id: 1, ranking: ['Alice', 'Bob', 'Carol'] },
  { voter_id: 2, ranking: ['Alice', 'Carol', 'Bob'] },
  { voter_id: 3, ranking: ['Bob', 'Alice', 'Carol'] },
  { voter_id: 4, ranking: ['Bob', 'Carol', 'Alice'] },
  { voter_id: 5, ranking: ['Carol', 'Alice', 'Bob'] },
];

describe('preprocessRankingsForSankey', () => {
  it('returns an array with header row', () => {
    const result = preprocessRankingsForSankey(rankings);
    expect(result[0]).toEqual(['From', 'To', 'Weight']);
  });

  it('contains at least one transition from Start', () => {
    const result = preprocessRankingsForSankey(rankings);
    const startTransitions = result.filter((r: any) => r[0] === 'Start');
    expect(startTransitions.length).toBeGreaterThan(0);
  });

  it('ends with a Winner node when one candidate wins', () => {
    const result = preprocessRankingsForSankey(rankings);
    const winnerRow = result.find((r: any) => r[1] && (r[1] as string).startsWith('Winner'));
    expect(winnerRow).toBeDefined();
  });

  it('returns empty transitions for empty rankings', () => {
    const result = preprocessRankingsForSankey([]);
    expect(result).toEqual([['From', 'To', 'Weight']]);
  });

  it('handles single-candidate rankings', () => {
    const result = preprocessRankingsForSankey([{ voter_id: 1, ranking: ['Alice'] }]);
    expect(result.length).toBeGreaterThanOrEqual(2);
  });
});
