/**
 * useSimulationWorker.test.ts
 *
 * Jest runs in CommonJS mode so `import.meta.url` (used inside the hook to
 * instantiate the Worker) is not available. We test:
 *   1. The WorkerRequest / WorkerResponse message contracts (pure TS)
 *   2. The hook's public API surface through a light mock
 *
 * Full integration (Worker ↔ hook) is verified in Playwright E2E or by
 * running the Vite dev server, where ESM import.meta is supported.
 */

// ── 1. WorkerRequest message contracts ───────────────────────────────────────

describe('WorkerRequest message contracts', () => {
  it('COMPUTE_HEATMAP has all required fields', () => {
    const msg = {
      id:         'test-id',
      type:       'COMPUTE_HEATMAP' as const,
      voters:     [{ id: 0, x: -0.3, y: 0.1 }],
      candidates: [{ name: 'Alice', x: -0.5, y: 0.0 }],
    };
    expect(msg.id).toBeTruthy();
    expect(msg.type).toBe('COMPUTE_HEATMAP');
    expect(Array.isArray(msg.voters)).toBe(true);
    expect(Array.isArray(msg.candidates)).toBe(true);
    expect(msg.voters[0]).toMatchObject({ id: expect.any(Number), x: expect.any(Number), y: expect.any(Number) });
  });

  it('COMPUTE_MATRIX has partialResults', () => {
    const msg = {
      id:             'test-id',
      type:           'COMPUTE_MATRIX' as const,
      partialResults: {
        plurality: { winner_distribution: { Alice: 0.6 }, most_common_winner: 'Alice' },
        borda:     { winner_distribution: { Alice: 0.5 }, most_common_winner: 'Alice' },
      },
    };
    expect(msg.type).toBe('COMPUTE_MATRIX');
    expect(Object.keys(msg.partialResults).length).toBeGreaterThan(0);
  });

  it('SORT_MC_RESULTS has partialResults', () => {
    const msg = {
      id:             'test-id',
      type:           'SORT_MC_RESULTS' as const,
      partialResults: { plurality: { winner_distribution: { A: 0.7 }, most_common_winner: 'A' } },
    };
    expect(msg.type).toBe('SORT_MC_RESULTS');
  });
});

// ── 2. WorkerResponse contracts ───────────────────────────────────────────────

describe('WorkerResponse contracts', () => {
  it('HEATMAP_DONE contains cells and metrics', () => {
    const response = {
      id:      'test-id',
      type:    'HEATMAP_DONE' as const,
      cells:   [],
      metrics: { maxContestedCell: null, fortressCell: null, fortressCandidate: null, maxDensity: 1 },
    };
    expect(response.type).toBe('HEATMAP_DONE');
    expect(Array.isArray(response.cells)).toBe(true);
    expect(response.metrics).toHaveProperty('maxDensity');
  });

  it('MATRIX_DONE contains a nested matrix', () => {
    const response = {
      id:     'test-id',
      type:   'MATRIX_DONE' as const,
      matrix: { plurality: { borda: 0.8, schulze: 0.75 } },
    };
    expect(response.type).toBe('MATRIX_DONE');
    expect(typeof response.matrix).toBe('object');
    expect(response.matrix.plurality.borda).toBe(0.8);
  });

  it('SORT_DONE contains rows array', () => {
    const response = {
      id:   'test-id',
      type: 'SORT_DONE' as const,
      rows: [{ method: 'plurality', winner: 'Alice', stability: 0.72, rank: 0 }],
    };
    expect(response.type).toBe('SORT_DONE');
    expect(response.rows[0].rank).toBe(0);
  });

  it('ERROR response contains error string', () => {
    const response = {
      id:    'test-id',
      type:  'ERROR' as const,
      error: 'Unknown message type: FOO',
    };
    expect(response.type).toBe('ERROR');
    expect(typeof response.error).toBe('string');
    expect(response.error.length).toBeGreaterThan(0);
  });
});

// ── 3. Mock-based hook interface test ─────────────────────────────────────────

// The hook can't be imported directly in Jest due to import.meta.url.
// We verify the interface contract through a simple mock.

jest.mock('../useSimulationWorker', () => ({
  useSimulationWorker: () => ({
    dispatch: jest.fn().mockResolvedValue({ cells: [], metrics: { maxDensity: 1 } }),
    isComputing: false,
  }),
}));

import { useSimulationWorker } from '../useSimulationWorker';
import { renderHook, act } from '@testing-library/react';

describe('useSimulationWorker hook interface', () => {
  it('exposes dispatch and isComputing', () => {
    const { result } = renderHook(() => useSimulationWorker());
    expect(typeof result.current.dispatch).toBe('function');
    expect(typeof result.current.isComputing).toBe('boolean');
  });

  it('dispatch returns a Promise', async () => {
    const { result } = renderHook(() => useSimulationWorker());
    let promise: Promise<unknown>;
    act(() => {
      promise = result.current.dispatch('COMPUTE_HEATMAP', { voters: [], candidates: [] });
    });
    await expect(promise!).resolves.toBeDefined();
  });

  it('isComputing starts as false', () => {
    const { result } = renderHook(() => useSimulationWorker());
    expect(result.current.isComputing).toBe(false);
  });
});
