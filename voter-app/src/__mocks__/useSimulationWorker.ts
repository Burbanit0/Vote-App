/**
 * Jest mock for hooks/useSimulationWorker.
 *
 * The real hook uses `new Worker(new URL('...', import.meta.url))` which Jest's
 * default TS module config does not support (TS1343 error). Rather than scatter
 * `jest.mock(...)` calls across every test file that transitively imports a
 * component using this hook, we map the module here via jest.config.js
 * moduleNameMapper.
 *
 * The mock dispatches to the corresponding **pure** function for each message
 * type — components that depend on the worker producing real heatmap/matrix
 * data therefore work as-if the worker ran in the same thread (which, since
 * jsdom is single-threaded anyway, is the only way to test them).
 */

// We import the pure functions from their source modules. They are exported
// alongside the React components that use them, specifically for this case.
function dispatchInline<T>(type: string, payload: unknown): Promise<T> {
  switch (type) {
    case 'COMPUTE_HEATMAP': {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { computeGrid } = require('../components/Simulation/IdeologyHeatmap');
      const p = payload as { voters: unknown[]; candidates: unknown[]; gridN?: number };
      const result = computeGrid(p.voters, p.candidates, p.gridN);
      return Promise.resolve({ type: 'COMPUTE_HEATMAP_DONE', ...result } as unknown as T);
    }
    case 'COMPUTE_MATRIX': {
      try {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const { partialResultsToMatrix } = require('../workers/simulationWorker');
        const p = payload as { partialResults: unknown };
        const result = partialResultsToMatrix(p.partialResults);
        return Promise.resolve({ type: 'COMPUTE_MATRIX_DONE', matrix: result } as unknown as T);
      } catch {
        return Promise.resolve({ type: 'COMPUTE_MATRIX_DONE', matrix: {} } as unknown as T);
      }
    }
    default:
      return Promise.resolve({} as T);
  }
}

export function useSimulationWorker() {
  return {
    dispatch:    jest.fn((type: string, payload: unknown) => dispatchInline(type, payload)),
    isComputing: false,
  };
}
