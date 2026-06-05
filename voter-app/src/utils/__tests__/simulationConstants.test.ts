import { mostCommonWinner } from '../../components/Simulation/simulationConstants';

describe('mostCommonWinner', () => {
  it('returns the most common winner', () => {
    const results = [
      { methods: { plurality: { winner: 'Alice' } } },
      { methods: { plurality: { winner: 'Alice' } } },
      { methods: { plurality: { winner: 'Bob' } } },
    ] as any;
    expect(mostCommonWinner(results, 'plurality')).toBe('Alice');
  });

  it('returns null when no results have winners', () => {
    const results = [{ methods: { plurality: {} } }, { methods: { plurality: {} } }] as any;
    expect(mostCommonWinner(results, 'plurality')).toBeNull();
  });

  it('returns null for empty results array', () => {
    expect(mostCommonWinner([], 'plurality')).toBeNull();
  });

  it('handles single result', () => {
    const results = [{ methods: { borda: { winner: 'Charlie' } } }] as any;
    expect(mostCommonWinner(results, 'borda')).toBe('Charlie');
  });
});
