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

import { vi } from 'vitest';
// The same pure kernels the real worker runs. Imported from lib/ rather than
// from the components that re-export them: those components import this very
// mock, and the cycle used to leave the helpers undefined at module init.
import { computeGrid, partialResultsToMatrix } from '../lib/simulationKernels';

// The payload shapes come over the (mocked) worker boundary as unknown; cast the
// pure helpers to unknown-accepting signatures so the mock stays type-loose.
const computeGridLoose = computeGrid as (...args: unknown[]) => Record<string, unknown>;
const partialToMatrixLoose = partialResultsToMatrix as (arg: unknown) => unknown;

function dispatchInline<T>(type: string, payload: unknown): Promise<T> {
  switch (type) {
    case 'COMPUTE_HEATMAP': {
      const p = payload as { voters: unknown[]; candidates: unknown[]; gridN?: number };
      const result = computeGridLoose(p.voters, p.candidates, p.gridN);
      return Promise.resolve({ type: 'COMPUTE_HEATMAP_DONE', ...result } as unknown as T);
    }
    case 'COMPUTE_MATRIX': {
      try {
        const p = payload as { partialResults: unknown };
        const result = partialToMatrixLoose(p.partialResults);
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
    dispatch: vi.fn((type: string, payload: unknown) => dispatchInline(type, payload)),
    isComputing: false,
  };
}
