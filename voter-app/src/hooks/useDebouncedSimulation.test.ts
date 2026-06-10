import { act, renderHook, waitFor } from '@testing-library/react';
import { useDebouncedSimulation } from './useDebouncedSimulation';

vi.mock('../services/simulationCompareApi', () => ({
  runComparisonSimulation: vi.fn(),
}));

const { runComparisonSimulation } = (await import(
  '../services/simulationCompareApi'
)) as unknown as {
  runComparisonSimulation: jest.Mock;
};

const MOCK_RESULT = {
  condorcet_winner: 'Alice',
  methods: {
    plurality: {
      winner: 'Alice',
      bayesian_regret: 0.01,
      majority_satisfaction: 0.8,
      strategic_vulnerability: 0.1,
      condorcet_consistent: true,
    },
  },
};

const BASE_PARAMS = {
  num_voters: 100,
  candidates: ['Alice', 'Bob'],
  ideology_distribution: 'random' as const,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
  runComparisonSimulation.mockResolvedValue(MOCK_RESULT);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useDebouncedSimulation', () => {
  it('fires immediately on first render without debounce', async () => {
    const { result } = renderHook(() => useDebouncedSimulation(BASE_PARAMS, 1));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(runComparisonSimulation).toHaveBeenCalledTimes(1);
    expect(result.current.results).toHaveLength(1);
  });

  it('debounces subsequent param changes and does not fire immediately', async () => {
    const { result, rerender } = renderHook(
      ({ voters }) => useDebouncedSimulation({ ...BASE_PARAMS, num_voters: voters }, 1),
      { initialProps: { voters: 100 } }
    );

    // Wait for first render to complete
    await waitFor(() => expect(result.current.loading).toBe(false));
    runComparisonSimulation.mockClear();

    // Change a param
    rerender({ voters: 200 });

    // Should NOT have fired yet (debounce pending)
    expect(runComparisonSimulation).not.toHaveBeenCalled();

    // Advance past debounce window
    act(() => {
      vi.advanceTimersByTime(700);
    });

    await waitFor(() => expect(runComparisonSimulation).toHaveBeenCalledTimes(1));
  });

  it('cancels the previous debounce when params change rapidly', async () => {
    const { result, rerender } = renderHook(
      ({ voters }) => useDebouncedSimulation({ ...BASE_PARAMS, num_voters: voters }, 1),
      { initialProps: { voters: 100 } }
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    runComparisonSimulation.mockClear();

    // Rapid successive changes
    rerender({ voters: 200 });
    act(() => {
      vi.advanceTimersByTime(300);
    });
    rerender({ voters: 300 });
    act(() => {
      vi.advanceTimersByTime(300);
    });
    rerender({ voters: 400 });

    // No call yet
    expect(runComparisonSimulation).not.toHaveBeenCalled();

    // One more advance to trigger final debounce
    act(() => {
      vi.advanceTimersByTime(700);
    });
    await waitFor(() => expect(runComparisonSimulation).toHaveBeenCalledTimes(1));
  });

  it('clears results immediately when candidate count changes', async () => {
    const { result, rerender } = renderHook(
      ({ candidates }) => useDebouncedSimulation({ ...BASE_PARAMS, candidates }, 1),
      { initialProps: { candidates: ['Alice', 'Bob'] } }
    );

    await waitFor(() => expect(result.current.results).toHaveLength(1));

    // Add a candidate → results should clear immediately
    rerender({ candidates: ['Alice', 'Bob', 'Carol'] });

    expect(result.current.results).toHaveLength(0);
  });

  it('runNow() triggers immediately without waiting for debounce', async () => {
    const { result, rerender } = renderHook(
      ({ voters }) => useDebouncedSimulation({ ...BASE_PARAMS, num_voters: voters }, 1),
      { initialProps: { voters: 100 } }
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    runComparisonSimulation.mockClear();

    // Change param (starts debounce)
    rerender({ voters: 200 });
    expect(runComparisonSimulation).not.toHaveBeenCalled();

    // runNow should bypass the debounce
    act(() => {
      result.current.runNow();
    });
    await waitFor(() => expect(runComparisonSimulation).toHaveBeenCalledTimes(1));
  });

  it('discards stale results when a newer run starts before previous completes', async () => {
    let resolveFirst: (v: any) => void;
    let resolveSecond: (v: any) => void;

    runComparisonSimulation
      .mockImplementationOnce(
        () =>
          new Promise((res) => {
            resolveFirst = res;
          })
      )
      .mockImplementationOnce(
        () =>
          new Promise((res) => {
            resolveSecond = res;
          })
      );

    const { result, rerender } = renderHook(
      ({ voters }) => useDebouncedSimulation({ ...BASE_PARAMS, num_voters: voters }, 1, 0),
      { initialProps: { voters: 100 } }
    );

    // First run started (loading)
    await waitFor(() => expect(result.current.loading).toBe(true));

    // Trigger second run immediately (runId increments)
    rerender({ voters: 200 });
    act(() => {
      result.current.runNow();
    });

    // Resolve second run first
    act(() => {
      resolveSecond!({ ...MOCK_RESULT, methods: { plurality: { winner: 'Bob' } } });
    });
    await waitFor(() => expect(result.current.results[0]?.methods.plurality?.winner).toBe('Bob'));

    // Resolve first run — should be discarded (stale)
    act(() => {
      resolveFirst!({ ...MOCK_RESULT, methods: { plurality: { winner: 'Alice' } } });
    });

    // Winner should still be Bob (first result was discarded)
    await waitFor(() => expect(result.current.results[0]?.methods.plurality?.winner).toBe('Bob'));
  });
});
