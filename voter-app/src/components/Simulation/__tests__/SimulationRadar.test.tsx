import preprocessRankingsForRadar from '../SimulationRadar';

const rankings = [
  { voter_id: 1, ranking: ['Alice', 'Bob', 'Carol'] },
  { voter_id: 2, ranking: ['Alice', 'Carol', 'Bob'] },
  { voter_id: 3, ranking: ['Bob', 'Alice', 'Carol'] },
];

describe('preprocessRankingsForRadar', () => {
  it('returns labels for each rank', () => {
    const result = preprocessRankingsForRadar(rankings);
    expect(result.labels).toEqual(['Rank 1', 'Rank 2', 'Rank 3']);
  });

  it('returns a dataset for each candidate', () => {
    const result = preprocessRankingsForRadar(rankings);
    expect(result.datasets).toHaveLength(3);
    expect(result.datasets.map((d: any) => d.label).sort()).toEqual(['Alice', 'Bob', 'Carol']);
  });

  it('normalizes data so values sum to 1 per candidate', () => {
    const result = preprocessRankingsForRadar(rankings);
    result.datasets.forEach((ds: any) => {
      const sum = ds.data.reduce((a: number, b: number) => a + b, 0);
      expect(sum).toBeCloseTo(1, 5);
    });
  });

  it('returns empty labels and datasets for empty input', () => {
    const result = preprocessRankingsForRadar([]);
    expect(result.labels).toEqual([]);
    expect(result.datasets).toEqual([]);
  });

  it('handles single-candidate input', () => {
    const result = preprocessRankingsForRadar([{ voter_id: 1, ranking: ['Alice'] }]);
    expect(result.labels).toEqual(['Rank 1']);
    expect(result.datasets).toHaveLength(1);
    expect(result.datasets[0].data).toEqual([1]);
  });
});
